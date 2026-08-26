from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException

from finehelper_api.deps import AuthContext
from finehelper_api.schemas import EvalIn, HeartbeatIn, TrainIn, doc_to_dict
from finehelper_core.db.mongo import Mongo
from finehelper_core.enums import EventKind, JobType
from finehelper_core.jobs.queue import append_event, cancel_job, enqueue_job, persist_job
from finehelper_core.models import DatasetVersion, EvalReport, Job, JobEvent, Project, Run
from finehelper_core.recipe import parse_recipe
from finehelper_core.storage import ObjectStore, object_key


def _recipe_from_train(body: TrainIn, project: Project) -> dict:
    if body.yaml_source:
        doc = parse_recipe(body.yaml_source)
        data = doc.model_dump(mode="json")
    elif body.recipe:
        data = parse_recipe(body.recipe).model_dump(mode="json")
    else:
        data = parse_recipe(
            {
                "project": project.slug,
                "train": {
                    "backend": body.backend or project.default_backend,
                    "base_model": project.default_base_model,
                },
            }
        ).model_dump(mode="json")
    if body.backend:
        data["train"]["backend"] = body.backend
    return data


async def start_train(db: Mongo, auth: AuthContext, body: TrainIn) -> dict:
    project = Project.from_mongo(await db.projects.find_one({"_id": str(body.project_id)}))
    if not project or project.org_id != auth.org_id:
        raise HTTPException(404, "project not found")
    version = DatasetVersion.from_mongo(await db.dataset_versions.find_one({"_id": str(body.dataset_version_id)}))
    if not version or version.org_id != auth.org_id:
        raise HTTPException(404, "dataset version not found")
    if version.status != "ready":
        raise HTTPException(409, "dataset version is not ready")
    recipe = _recipe_from_train(body, project)
    job = await enqueue_job(
        db,
        org_id=auth.org_id,
        project_id=project.id,
        job_type=JobType.train.value,
        payload={
            "dataset_version_id": version.id,
            "backend": recipe["train"]["backend"],
            "recipe": recipe,
            "git_sha": body.git_sha,
        },
        idempotency_key=body.idempotency_key,
    )
    return {"job_id": job.id, "status": job.status}


async def start_eval(db: Mongo, auth: AuthContext, store: ObjectStore, body: EvalIn) -> dict:
    run = Run.from_mongo(await db.runs.find_one({"_id": str(body.run_id)}))
    if not run or run.org_id != auth.org_id:
        raise HTTPException(404, "run not found")
    if body.suite_inline is not None:
        raw = ("\n".join(json.dumps(x) for x in body.suite_inline) + "\n").encode()
        key = object_key("evals", str(auth.org_id), str(run.id), "suite.jsonl")
        uri = store.put(key, raw, "application/jsonl")
    elif body.suite_key:
        uri = store.uri(body.suite_key)
    else:
        raise HTTPException(400, "suite_inline or suite_key required")
    job = await enqueue_job(
        db,
        org_id=auth.org_id,
        project_id=run.project_id,
        job_type=JobType.eval.value,
        payload={
            "run_id": run.id,
            "suite_uri": uri,
            "metrics": body.metrics,
            "gate": body.gate,
            "judge_model": body.judge_model,
        },
        idempotency_key=body.idempotency_key,
    )
    return {"job_id": job.id, "status": job.status}


async def list_jobs(db: Mongo, auth: AuthContext, project_id: str | None = None, limit: int = 50) -> list[dict]:
    query: dict[str, Any] = {"org_id": auth.org_id}
    if project_id:
        query["project_id"] = project_id
    rows = await db.jobs.find(query).sort("created_at", -1).to_list(max(1, min(limit, 200)))
    return [doc_to_dict(Job.from_mongo(r)) for r in rows if r]


async def get_job(db: Mongo, auth: AuthContext, job_id: str) -> dict:
    job = Job.from_mongo(await db.jobs.find_one({"_id": job_id}))
    if not job or job.org_id != auth.org_id:
        raise HTTPException(404, "job not found")
    return doc_to_dict(job)


async def cancel(db: Mongo, auth: AuthContext, job_id: str) -> dict:
    job = Job.from_mongo(await db.jobs.find_one({"_id": job_id}))
    if not job or job.org_id != auth.org_id:
        raise HTTPException(404, "job not found")
    await cancel_job(db, job)
    return doc_to_dict(job)


async def heartbeat(db: Mongo, auth: AuthContext, job_id: str, body: HeartbeatIn) -> dict:
    job = Job.from_mongo(await db.jobs.find_one({"_id": job_id}))
    if not job or job.org_id != auth.org_id:
        raise HTTPException(404, "job not found")
    payload = dict(job.payload or {})
    local = dict(payload.get("local") or {})
    if body.metrics:
        local["metrics"] = {**(local.get("metrics") or {}), **body.metrics}
    if body.succeeded:
        local["succeeded"] = True
    if body.failed:
        local["failed"] = True
        local["error"] = body.error
    if body.adapter_uri:
        local["adapter_uri"] = body.adapter_uri
    payload["local"] = local
    job.payload = payload
    await persist_job(db, job)
    await append_event(db, job, EventKind.log.value, body.message or "heartbeat", body.metrics)
    return {"ok": True}


async def event_log(db: Mongo, auth: AuthContext, job_id: str) -> list[dict]:
    job = Job.from_mongo(await db.jobs.find_one({"_id": job_id}))
    if not job or job.org_id != auth.org_id:
        raise HTTPException(404, "job not found")
    events = await db.job_events.find({"job_id": job_id}).sort("created_at", 1).to_list(2000)
    return [doc_to_dict(JobEvent.from_mongo(e)) for e in events if e]


async def require_job(db: Mongo, auth: AuthContext, job_id: str) -> Job:
    job = Job.from_mongo(await db.jobs.find_one({"_id": job_id}))
    if not job or job.org_id != auth.org_id:
        raise HTTPException(404, "job not found")
    return job


async def events_since(db: Mongo, job_id: str, after: Any | None) -> tuple[list[JobEvent], Job | None]:
    query: dict[str, Any] = {"job_id": job_id}
    if after is not None:
        query["created_at"] = {"$gt": after}
    rows = await db.job_events.find(query).sort("created_at", 1).to_list(200)
    events = [JobEvent.from_mongo(e) for e in rows if e]
    current = Job.from_mongo(await db.jobs.find_one({"_id": job_id}))
    return ([e for e in events if e], current)


async def list_runs(db: Mongo, auth: AuthContext, project_id: str | None = None) -> list[dict]:
    query: dict[str, Any] = {"org_id": auth.org_id}
    if project_id:
        query["project_id"] = project_id
    rows = await db.runs.find(query).sort("created_at", -1).to_list(200)
    return [doc_to_dict(Run.from_mongo(r)) for r in rows if r]


async def get_run(db: Mongo, auth: AuthContext, run_id: str) -> dict:
    run = Run.from_mongo(await db.runs.find_one({"_id": run_id}))
    if not run or run.org_id != auth.org_id:
        raise HTTPException(404, "run not found")
    evals = await db.eval_reports.find({"run_id": run.id}).to_list(100)
    return {**doc_to_dict(run), "evals": [doc_to_dict(EvalReport.from_mongo(e)) for e in evals if e]}


async def compare_runs(db: Mongo, auth: AuthContext, run_id: str, other: str) -> dict:
    a = Run.from_mongo(await db.runs.find_one({"_id": run_id}))
    b = Run.from_mongo(await db.runs.find_one({"_id": other}))
    if not a or not b or a.org_id != auth.org_id or b.org_id != auth.org_id:
        raise HTTPException(404, "run not found")
    evals_a = await db.eval_reports.find({"run_id": a.id}).to_list(100)
    evals_b = await db.eval_reports.find({"run_id": b.id}).to_list(100)
    return {
        "a": {**doc_to_dict(a), "evals": [doc_to_dict(EvalReport.from_mongo(e)) for e in evals_a if e]},
        "b": {**doc_to_dict(b), "evals": [doc_to_dict(EvalReport.from_mongo(e)) for e in evals_b if e]},
    }
