from __future__ import annotations

import json
import logging
import traceback
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from finehelper_core.backends.openai_backend import (
    DryRunTrainingBackend,
    LocalLoraBackend,
    ModalLoraBackend,
    OpenAITrainingBackend,
)
from finehelper_core.crypto import decrypt_secret
from finehelper_core.dataset.prepare import prepare_dataset, scrub_log
from finehelper_core.db.models import (
    Artifact,
    Credential,
    DatasetVersion,
    Deployment,
    EvalReport,
    Job,
    Run,
    UsageEvent,
)
from finehelper_core.enums import DatasetFormat, EventKind, JobStatus, JobType
from finehelper_core.eval.metrics import METRIC_FNS, gate_passed, llm_judge, parse_suite, suite_digest
from finehelper_core.jobs.queue import append_event, claim_next_job, set_status
from finehelper_core.recipe import parse_recipe
from finehelper_core.settings import Settings
from finehelper_core.storage import ObjectStore, key_from_uri, object_key

log = logging.getLogger("finehelper.worker")


class JobProcessor:
    def __init__(self, settings: Settings, store: ObjectStore, sessions: async_sessionmaker[AsyncSession], worker_id: str):
        self.settings = settings
        self.store = store
        self.sessions = sessions
        self.worker_id = worker_id

    async def tick(self) -> bool:
        async with self.sessions() as session:
            job = await claim_next_job(session, self.worker_id)
            if not job:
                await session.commit()
                return False
            await session.commit()
            job_id = job.id
        try:
            async with self.sessions() as session:
                job = await session.get(Job, job_id)
                assert job is not None
                await self._run(session, job)
                await session.commit()
        except Exception as exc:
            log.exception("job %s failed", job_id)
            async with self.sessions() as session:
                job = await session.get(Job, job_id)
                if job and job.status not in {JobStatus.succeeded.value, JobStatus.cancelled.value}:
                    await set_status(session, job, JobStatus.failed.value, scrub_log(str(exc)))
                    await append_event(session, job, EventKind.failed.value, traceback.format_exc()[-2000:])
                    await session.commit()
        return True

    async def _run(self, session: AsyncSession, job: Job) -> None:
        dispatch = {
            JobType.ingest.value: self._ingest,
            JobType.prepare.value: self._prepare,
            JobType.train.value: self._train,
            JobType.eval.value: self._eval,
            JobType.export.value: self._export,
            JobType.deploy.value: self._deploy,
        }
        handler = dispatch.get(job.type)
        if not handler:
            raise RuntimeError(f"unknown job type {job.type}")
        await handler(session, job)

    async def _credential(self, session: AsyncSession, org_id: UUID, provider: str) -> str | None:
        cred = await session.scalar(
            select(Credential).where(Credential.org_id == org_id, Credential.provider == provider)
        )
        if not cred:
            return None
        return decrypt_secret(cred.encrypted_secret, self.settings.master_key)

    async def _ingest(self, session: AsyncSession, job: Job) -> None:
        """Ingest is usually just a pointer to an uploaded object; prepare does the real work."""
        payload = job.payload
        dataset_id = UUID(payload["dataset_id"])
        version = DatasetVersion(
            org_id=job.org_id,
            dataset_id=dataset_id,
            content_digest=payload.get("digest") or "pending",
            uri=payload["uri"],
            status="uploaded",
            prepare_config=payload.get("prepare") or {},
        )
        session.add(version)
        await session.flush()
        job.result = {"dataset_version_id": str(version.id)}
        await set_status(session, job, JobStatus.succeeded.value)
        if payload.get("auto_prepare", True):
            from finehelper_core.jobs.queue import enqueue_job

            child = await enqueue_job(
                session,
                org_id=job.org_id,
                project_id=job.project_id,
                job_type=JobType.prepare.value,
                payload={
                    "dataset_id": str(dataset_id),
                    "dataset_version_id": str(version.id),
                    "filename": payload.get("filename") or "upload.jsonl",
                    "format": payload.get("format"),
                    "prepare": payload.get("prepare") or {},
                },
                parent_job_id=job.id,
            )
            job.result["prepare_job_id"] = str(child.id)

    async def _prepare(self, session: AsyncSession, job: Job) -> None:
        version = await session.get(DatasetVersion, UUID(job.payload["dataset_version_id"]))
        if not version:
            raise RuntimeError("dataset version not found")
        raw = self.store.get(key_from_uri(version.uri))
        filename = job.payload.get("filename") or "upload.jsonl"
        declared = job.payload.get("format")
        fmt = DatasetFormat(declared) if declared else None
        prepare_cfg = job.payload.get("prepare") or version.prepare_config or {}
        await append_event(session, job, EventKind.log.value, f"preparing {filename} ({len(raw)} bytes)")
        result = prepare_dataset(
            raw,
            filename,
            declared_format=fmt,
            source=filename,
            dedupe=bool(prepare_cfg.get("dedupe", True)),
            max_seq_len=prepare_cfg.get("max_seq_len", 4096),
            split=prepare_cfg.get("split"),
        )
        org = str(job.org_id)
        canon_key = object_key("datasets", org, str(version.dataset_id), f"{result['digest']}.jsonl.gz")
        uri = self.store.put(canon_key, result["blob"], "application/gzip")
        error_uri = None
        if result["errors"]:
            err_key = object_key("datasets", org, str(version.dataset_id), f"{result['digest']}.errors.json")
            error_uri = self.store.put(
                err_key,
                json.dumps(result["errors"], indent=2).encode(),
                "application/json",
            )
        version.content_digest = result["digest"]
        version.uri = uri
        version.row_count = result["row_count"]
        version.stats = result["stats"]
        version.split_map = result["split_map"]
        version.prepare_config = result["prepare_config"]
        version.error_report_uri = error_uri
        version.status = "failed" if result["failed"] else "ready"
        job.result = {
            "dataset_version_id": str(version.id),
            "digest": result["digest"],
            "row_count": result["row_count"],
            "stats": result["stats"],
            "error_count": result["error_count"],
            "error_rate": result["error_rate"],
            "dropped_dedupe": result["dropped_dedupe"],
            "dropped_length": result["dropped_length"],
        }
        if result["failed"]:
            await set_status(session, job, JobStatus.failed.value, "prepare failed: too many invalid rows or empty output")
            return
        await append_event(
            session,
            job,
            EventKind.log.value,
            f"ready {result['row_count']} rows digest={result['digest'][:12]}",
            result["stats"],
        )
        await set_status(session, job, JobStatus.succeeded.value)

    def _backend(self, name: str, api_key: str | None):
        if name == "openai":
            if not api_key:
                raise RuntimeError("no OpenAI credential stored for this org")
            return OpenAITrainingBackend(api_key)
        if name == "dry_run":
            return DryRunTrainingBackend()
        if name == "lora_modal":
            return ModalLoraBackend()
        if name == "lora_local":
            return LocalLoraBackend()
        raise RuntimeError(f"backend {name} is not implemented in this worker")

    async def _train(self, session: AsyncSession, job: Job) -> None:
        payload = job.payload
        version = await session.get(DatasetVersion, UUID(payload["dataset_version_id"]))
        if not version or version.status != "ready":
            raise RuntimeError("dataset version is not ready")
        recipe = parse_recipe(payload["recipe"] if isinstance(payload.get("recipe"), (str, dict)) else payload)
        backend_name = payload.get("backend") or recipe.train.backend
        api_key = await self._credential(session, job.org_id, "openai") if backend_name == "openai" else None
        backend = self._backend(backend_name, api_key)
        validation = backend.validate(recipe, version.stats)
        if not validation.ok:
            raise RuntimeError("; ".join(validation.errors))
        dataset_bytes = self.store.get(key_from_uri(version.uri))
        await append_event(session, job, EventKind.log.value, f"submitting {backend_name} job for {recipe.train.base_model}")
        ref = await backend.submit(str(job.id), recipe, dataset_bytes, version.content_digest, version.uri)
        job.external_ref = json.dumps({"backend": ref.backend, "ref": ref.ref, "extra": ref.extra})
        await session.flush()

        # Poll until terminal. Local LoRA waits for CLI heartbeats stored on the job payload.
        from finehelper_core.backends.base import ExternalRef

        ext = ExternalRef(backend=ref.backend, ref=ref.ref, extra=ref.extra)
        while True:
            fresh = await session.get(Job, job.id)
            if fresh and fresh.status == JobStatus.cancelled.value:
                await backend.cancel(ext)
                return
            if backend_name == "lora_local":
                extra = (fresh.payload or {}).get("local") or {}
                ext.extra.update(extra)
            status = await backend.poll(ext)
            if status.metrics:
                await append_event(session, job, EventKind.metric.value, status.message or "metrics", status.metrics)
            else:
                await append_event(session, job, EventKind.log.value, status.message or status.state)
            await session.commit()
            if status.state in {"succeeded", "failed", "cancelled"}:
                break
            import asyncio

            await asyncio.sleep(3 if backend_name == "openai" else 1)

        if status.state != "succeeded":
            await set_status(session, job, JobStatus.failed.value if status.state == "failed" else JobStatus.cancelled.value, status.message)
            return

        await set_status(session, job, JobStatus.uploading.value)
        artifacts = await backend.collect(ext)
        run = Run(
            org_id=job.org_id,
            project_id=job.project_id,
            job_id=job.id,
            dataset_version_id=version.id,
            backend=backend_name,
            base_model=recipe.train.base_model,
            hyperparams=recipe.train.hyperparams,
            metrics=status.metrics,
            provider_model_id=status.provider_model_id,
            adapter_uri=next((a.uri for a in artifacts if a.kind == "adapter"), None),
            git_sha=payload.get("git_sha"),
        )
        session.add(run)
        await session.flush()
        for art in artifacts:
            session.add(
                Artifact(
                    org_id=job.org_id,
                    run_id=run.id,
                    job_id=job.id,
                    kind=art.kind,
                    uri=art.uri,
                    size_bytes=art.size_bytes,
                    content_type=art.content_type,
                )
            )
            await append_event(session, job, EventKind.artifact_ready.value, art.uri, {"kind": art.kind})
        session.add(
            UsageEvent(
                org_id=job.org_id,
                job_id=job.id,
                kind="train",
                quantity=float((status.metrics or {}).get("step") or version.row_count or 0),
                unit="step",
            )
        )
        job.result = {"run_id": str(run.id), "provider_model_id": status.provider_model_id, "metrics": status.metrics}
        await set_status(session, job, JobStatus.succeeded.value)

    async def _eval(self, session: AsyncSession, job: Job) -> None:
        payload = job.payload
        run = await session.get(Run, UUID(payload["run_id"]))
        if not run:
            raise RuntimeError("run not found")
        suite_uri = payload.get("suite_uri")
        if not suite_uri:
            raise RuntimeError("eval suite_uri required")
        raw = self.store.get(key_from_uri(suite_uri))
        items = parse_suite(raw)
        digest = suite_digest(raw)
        metrics_wanted = payload.get("metrics") or ["exact_match"]
        judge_model = payload.get("judge_model") or "gpt-4.1-mini"
        api_key = await self._credential(session, job.org_id, "openai")
        traces = []
        scores: dict[str, list[float]] = {m: [] for m in metrics_wanted}

        for item in items:
            pred = await self._predict(session, run, item["messages"], api_key)
            row_scores = {}
            for metric in metrics_wanted:
                if metric == "llm_judge":
                    val = await llm_judge(pred, item.get("expected"), api_key, judge_model)
                else:
                    fn = METRIC_FNS.get(metric)
                    val = fn(pred, item.get("expected")) if fn else 0.0
                scores.setdefault(metric, []).append(val)
                row_scores[metric] = val
            traces.append({"id": item["id"], "pred": pred, "expected": item.get("expected"), "scores": row_scores})
            await append_event(session, job, EventKind.log.value, f"eval {item['id']}", row_scores)

        summary = {k: (sum(v) / len(v) if v else 0.0) for k, v in scores.items()}
        gate = payload.get("gate")
        passed = gate_passed(summary, gate)
        traces_key = object_key("evals", str(job.org_id), str(run.id), f"{digest[:12]}.json")
        traces_uri = self.store.put(traces_key, json.dumps(traces, ensure_ascii=False, indent=2).encode(), "application/json")
        report = EvalReport(
            org_id=job.org_id,
            project_id=job.project_id or run.project_id,
            run_id=run.id,
            job_id=job.id,
            suite_digest=digest,
            metrics=summary,
            passed=passed,
            gate=gate,
            traces_uri=traces_uri,
            judge_model=judge_model if "llm_judge" in metrics_wanted else None,
        )
        session.add(report)
        await session.flush()
        job.result = {"eval_report_id": str(report.id), "metrics": summary, "passed": passed}
        if not passed:
            await set_status(session, job, JobStatus.succeeded.value)
            await append_event(session, job, EventKind.log.value, "quality gate failed", summary)
            return
        await set_status(session, job, JobStatus.succeeded.value)

    async def _predict(self, session: AsyncSession, run: Run, messages: list[dict[str, str]], api_key: str | None) -> str:
        if run.backend in {"openai"} and run.provider_model_id and api_key:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key)
            resp = await client.chat.completions.create(model=run.provider_model_id, messages=messages, temperature=0)
            return resp.choices[0].message.content or ""
        if run.backend == "dry_run":
            last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
            return f"[dry-run:{run.base_model}] {last_user[:200]}"
        # Local / modal adapters: no live server in v1 eval unless a deployment exists.
        dep = await session.scalar(
            select(Deployment).where(Deployment.run_id == run.id, Deployment.deleted_at.is_(None))
        )
        if dep and dep.backend == "openai" and api_key:
            from openai import AsyncOpenAI

            model = (dep.target or {}).get("model") or run.provider_model_id
            client = AsyncOpenAI(api_key=api_key)
            resp = await client.chat.completions.create(model=model, messages=messages, temperature=0)
            return resp.choices[0].message.content or ""
        return ""

    async def _export(self, session: AsyncSession, job: Job) -> None:
        await append_event(session, job, EventKind.log.value, "export is handled by Modal export_gguf")
        job.result = {"hint": "call workers/gpu export_gguf with the run adapter uri"}
        await set_status(session, job, JobStatus.succeeded.value)

    async def _deploy(self, session: AsyncSession, job: Job) -> None:
        payload = job.payload
        run = await session.get(Run, UUID(payload["run_id"]))
        if not run:
            raise RuntimeError("run not found")
        override = bool(payload.get("override_gate"))
        report = None
        if payload.get("eval_report_id"):
            report = await session.get(EvalReport, UUID(payload["eval_report_id"]))
        else:
            report = await session.scalar(
                select(EvalReport).where(EvalReport.run_id == run.id).order_by(EvalReport.created_at.desc())
            )
        if report is None:
            raise RuntimeError("deploy requires an eval report (eval-before-promote)")
        if not report.passed and not override:
            raise RuntimeError("quality gate failed; pass override_gate=true to force deploy")
        target = {"model": run.provider_model_id, "adapter_uri": run.adapter_uri, "backend": run.backend}
        dep = Deployment(
            org_id=job.org_id,
            project_id=job.project_id or run.project_id,
            run_id=run.id,
            eval_report_id=report.id,
            name=payload.get("name") or "prod",
            backend=run.backend,
            target=target,
            override_gate=override,
        )
        session.add(dep)
        await session.flush()
        job.result = {"deployment_id": str(dep.id), "target": target}
        await set_status(session, job, JobStatus.succeeded.value)
