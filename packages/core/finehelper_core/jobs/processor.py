from __future__ import annotations

import json
import logging
import traceback

from finehelper_core.backends.openai_backend import (
    DryRunTrainingBackend,
    LocalLoraBackend,
    ModalLoraBackend,
    OpenAITrainingBackend,
)
from finehelper_core.crypto import decrypt_secret
from finehelper_core.dataset.prepare import prepare_dataset, scrub_log
from finehelper_core.db.mongo import Mongo
from finehelper_core.enums import DatasetFormat, EventKind, JobStatus, JobType
from finehelper_core.eval.metrics import METRIC_FNS, gate_passed, llm_judge, parse_suite, suite_digest
from finehelper_core.jobs.queue import append_event, claim_next_job, enqueue_job, persist_job, set_status
from finehelper_core.models import Artifact, Credential, DatasetVersion, Deployment, EvalReport, Job, Run, UsageEvent
from finehelper_core.recipe import parse_recipe
from finehelper_core.settings import Settings
from finehelper_core.storage import ObjectStore, key_from_uri, object_key

log = logging.getLogger("finehelper.worker")


class JobProcessor:
    def __init__(self, settings: Settings, store: ObjectStore, db: Mongo, worker_id: str):
        self.settings = settings
        self.store = store
        self.db = db
        self.worker_id = worker_id

    async def tick(self) -> bool:
        job = await claim_next_job(self.db, self.worker_id)
        if not job:
            return False
        try:
            fresh = Job.from_mongo(await self.db.jobs.find_one({"_id": job.id}))
            assert fresh is not None
            await self._run(fresh)
        except Exception as exc:
            log.exception("job %s failed", job.id)
            fresh = Job.from_mongo(await self.db.jobs.find_one({"_id": job.id}))
            if fresh and fresh.status not in {JobStatus.succeeded.value, JobStatus.cancelled.value}:
                await set_status(self.db, fresh, JobStatus.failed.value, scrub_log(str(exc)))
                await append_event(self.db, fresh, EventKind.failed.value, traceback.format_exc()[-2000:])
        return True

    async def _run(self, job: Job) -> None:
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
        await handler(job)

    async def _credential(self, org_id: str, provider: str) -> str | None:
        cred = Credential.from_mongo(
            await self.db.credentials.find_one({"org_id": org_id, "provider": provider})
        )
        if not cred:
            return None
        return decrypt_secret(cred.encrypted_secret, self.settings.master_key)

    async def _ingest(self, job: Job) -> None:
        payload = job.payload
        dataset_id = payload["dataset_id"]
        version = DatasetVersion(
            org_id=job.org_id,
            dataset_id=dataset_id,
            content_digest=payload.get("digest") or "pending",
            uri=payload["uri"],
            status="uploaded",
            prepare_config=payload.get("prepare") or {},
        )
        await self.db.insert(self.db.dataset_versions, version)
        job.result = {"dataset_version_id": version.id}
        await set_status(self.db, job, JobStatus.succeeded.value)
        if payload.get("auto_prepare", True):
            child = await enqueue_job(
                self.db,
                org_id=job.org_id,
                project_id=job.project_id,
                job_type=JobType.prepare.value,
                payload={
                    "dataset_id": str(dataset_id),
                    "dataset_version_id": version.id,
                    "filename": payload.get("filename") or "upload.jsonl",
                    "format": payload.get("format"),
                    "prepare": payload.get("prepare") or {},
                },
                parent_job_id=job.id,
            )
            job.result["prepare_job_id"] = child.id
            await persist_job(self.db, job)

    async def _prepare(self, job: Job) -> None:
        version = DatasetVersion.from_mongo(
            await self.db.dataset_versions.find_one({"_id": job.payload["dataset_version_id"]})
        )
        if not version:
            raise RuntimeError("dataset version not found")
        raw = self.store.get(key_from_uri(version.uri))
        filename = job.payload.get("filename") or "upload.jsonl"
        declared = job.payload.get("format")
        fmt = DatasetFormat(declared) if declared else None
        prepare_cfg = job.payload.get("prepare") or version.prepare_config or {}
        await append_event(self.db, job, EventKind.log.value, f"preparing {filename} ({len(raw)} bytes)")
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
        await self.db.save(self.db.dataset_versions, version)
        job.result = {
            "dataset_version_id": version.id,
            "digest": result["digest"],
            "row_count": result["row_count"],
            "stats": result["stats"],
            "error_count": result["error_count"],
            "error_rate": result["error_rate"],
            "dropped_dedupe": result["dropped_dedupe"],
            "dropped_length": result["dropped_length"],
        }
        if result["failed"]:
            await set_status(self.db, job, JobStatus.failed.value, "prepare failed: too many invalid rows or empty output")
            return
        await append_event(
            self.db,
            job,
            EventKind.log.value,
            f"ready {result['row_count']} rows digest={result['digest'][:12]}",
            result["stats"],
        )
        await set_status(self.db, job, JobStatus.succeeded.value)

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

    async def _train(self, job: Job) -> None:
        payload = job.payload
        version = DatasetVersion.from_mongo(
            await self.db.dataset_versions.find_one({"_id": payload["dataset_version_id"]})
        )
        if not version or version.status != "ready":
            raise RuntimeError("dataset version is not ready")
        recipe = parse_recipe(payload["recipe"] if isinstance(payload.get("recipe"), (str, dict)) else payload)
        backend_name = payload.get("backend") or recipe.train.backend
        api_key = await self._credential(job.org_id, "openai") if backend_name == "openai" else None
        backend = self._backend(backend_name, api_key)
        validation = backend.validate(recipe, version.stats)
        if not validation.ok:
            raise RuntimeError("; ".join(validation.errors))
        dataset_bytes = self.store.get(key_from_uri(version.uri))
        await append_event(self.db, job, EventKind.log.value, f"submitting {backend_name} job for {recipe.train.base_model}")
        ref = await backend.submit(str(job.id), recipe, dataset_bytes, version.content_digest, version.uri)
        job.external_ref = json.dumps({"backend": ref.backend, "ref": ref.ref, "extra": ref.extra})
        await persist_job(self.db, job)

        from finehelper_core.backends.base import ExternalRef

        ext = ExternalRef(backend=ref.backend, ref=ref.ref, extra=ref.extra)
        while True:
            fresh = Job.from_mongo(await self.db.jobs.find_one({"_id": job.id}))
            if fresh and fresh.status == JobStatus.cancelled.value:
                await backend.cancel(ext)
                return
            if backend_name == "lora_local" and fresh:
                extra = (fresh.payload or {}).get("local") or {}
                ext.extra.update(extra)
            status = await backend.poll(ext)
            if status.metrics:
                await append_event(self.db, job, EventKind.metric.value, status.message or "metrics", status.metrics)
            else:
                await append_event(self.db, job, EventKind.log.value, status.message or status.state)
            if status.state in {"succeeded", "failed", "cancelled"}:
                break
            import asyncio

            await asyncio.sleep(3 if backend_name == "openai" else 1)

        if status.state != "succeeded":
            await set_status(
                self.db,
                job,
                JobStatus.failed.value if status.state == "failed" else JobStatus.cancelled.value,
                status.message,
            )
            return

        await set_status(self.db, job, JobStatus.uploading.value)
        artifacts = await backend.collect(ext)
        if not job.project_id:
            raise RuntimeError("train job missing project_id")
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
        await self.db.insert(self.db.runs, run)
        for art in artifacts:
            artifact = Artifact(
                org_id=job.org_id,
                run_id=run.id,
                job_id=job.id,
                kind=art.kind,
                uri=art.uri,
                size_bytes=art.size_bytes,
                content_type=art.content_type,
            )
            await self.db.insert(self.db.artifacts, artifact)
            await append_event(self.db, job, EventKind.artifact_ready.value, art.uri, {"kind": art.kind})
        await self.db.insert(
            self.db.usage_events,
            UsageEvent(
                org_id=job.org_id,
                job_id=job.id,
                kind="train",
                quantity=float((status.metrics or {}).get("step") or version.row_count or 0),
                unit="step",
            ),
        )
        job.result = {"run_id": run.id, "provider_model_id": status.provider_model_id, "metrics": status.metrics}
        await set_status(self.db, job, JobStatus.succeeded.value)

    async def _eval(self, job: Job) -> None:
        payload = job.payload
        run = Run.from_mongo(await self.db.runs.find_one({"_id": payload["run_id"]}))
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
        api_key = await self._credential(job.org_id, "openai")
        traces = []
        scores: dict[str, list[float]] = {m: [] for m in metrics_wanted}

        for item in items:
            pred = await self._predict(run, item["messages"], api_key)
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
            await append_event(self.db, job, EventKind.log.value, f"eval {item['id']}", row_scores)

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
        await self.db.insert(self.db.eval_reports, report)
        job.result = {"eval_report_id": report.id, "metrics": summary, "passed": passed}
        if not passed:
            await set_status(self.db, job, JobStatus.succeeded.value)
            await append_event(self.db, job, EventKind.log.value, "quality gate failed", summary)
            return
        await set_status(self.db, job, JobStatus.succeeded.value)

    async def _predict(self, run: Run, messages: list[dict[str, str]], api_key: str | None) -> str:
        if run.backend in {"openai"} and run.provider_model_id and api_key:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key)
            resp = await client.chat.completions.create(model=run.provider_model_id, messages=messages, temperature=0)
            return resp.choices[0].message.content or ""
        if run.backend == "dry_run":
            last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
            return f"[dry-run:{run.base_model}] {last_user[:200]}"
        dep = Deployment.from_mongo(
            await self.db.deployments.find_one({"run_id": run.id, "deleted_at": None})
        )
        if dep and dep.backend == "openai" and api_key:
            from openai import AsyncOpenAI

            model = (dep.target or {}).get("model") or run.provider_model_id
            client = AsyncOpenAI(api_key=api_key)
            resp = await client.chat.completions.create(model=model, messages=messages, temperature=0)
            return resp.choices[0].message.content or ""
        return ""

    async def _export(self, job: Job) -> None:
        await append_event(self.db, job, EventKind.log.value, "export is handled by Modal export_gguf")
        job.result = {"hint": "call workers/gpu export_gguf with the run adapter uri"}
        await set_status(self.db, job, JobStatus.succeeded.value)

    async def _deploy(self, job: Job) -> None:
        payload = job.payload
        run = Run.from_mongo(await self.db.runs.find_one({"_id": payload["run_id"]}))
        if not run:
            raise RuntimeError("run not found")
        override = bool(payload.get("override_gate"))
        report = None
        if payload.get("eval_report_id"):
            report = EvalReport.from_mongo(await self.db.eval_reports.find_one({"_id": payload["eval_report_id"]}))
        else:
            report = EvalReport.from_mongo(
                await self.db.eval_reports.find_one({"run_id": run.id}, sort=[("created_at", -1)])
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
        await self.db.insert(self.db.deployments, dep)
        job.result = {"deployment_id": dep.id, "target": target}
        await set_status(self.db, job, JobStatus.succeeded.value)
