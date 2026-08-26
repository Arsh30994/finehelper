from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from finehelper_api.deps import AuthDep, SessionDep
from finehelper_api.schemas import EvalIn, HeartbeatIn, TrainIn, orm_to_dict
from finehelper_core.db.models import DatasetVersion, EvalReport, Job, JobEvent, Project, Run
from finehelper_core.enums import JobType
from finehelper_core.jobs.queue import cancel_job, enqueue_job
from finehelper_core.recipe import parse_recipe
from finehelper_core.storage import object_key

router = APIRouter(prefix="/v1", tags=["jobs"])


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


@router.post("/jobs/train", status_code=202)
async def start_train(body: TrainIn, auth: AuthDep, session: SessionDep):
    project = await session.get(Project, body.project_id)
    if not project or project.org_id != auth.org_id:
        raise HTTPException(404, "project not found")
    version = await session.get(DatasetVersion, body.dataset_version_id)
    if not version or version.org_id != auth.org_id:
        raise HTTPException(404, "dataset version not found")
    if version.status != "ready":
        raise HTTPException(409, "dataset version is not ready")
    recipe = _recipe_from_train(body, project)
    job = await enqueue_job(
        session,
        org_id=auth.org_id,
        project_id=project.id,
        job_type=JobType.train.value,
        payload={
            "dataset_version_id": str(version.id),
            "backend": recipe["train"]["backend"],
            "recipe": recipe,
            "git_sha": body.git_sha,
        },
        idempotency_key=body.idempotency_key,
    )
    await session.flush()
    return {"job_id": str(job.id), "status": job.status}


@router.post("/evals", status_code=202)
async def start_eval(body: EvalIn, auth: AuthDep, session: SessionDep, request: Request):
    run = await session.get(Run, body.run_id)
    if not run or run.org_id != auth.org_id:
        raise HTTPException(404, "run not found")
    store = request.app.state.store
    if body.suite_inline is not None:
        raw = ("\n".join(json.dumps(x) for x in body.suite_inline) + "\n").encode()
        key = object_key("evals", str(auth.org_id), str(run.id), "suite.jsonl")
        uri = store.put(key, raw, "application/jsonl")
    elif body.suite_key:
        uri = store.uri(body.suite_key)
    else:
        raise HTTPException(400, "suite_inline or suite_key required")
    job = await enqueue_job(
        session,
        org_id=auth.org_id,
        project_id=run.project_id,
        job_type=JobType.eval.value,
        payload={
            "run_id": str(run.id),
            "suite_uri": uri,
            "metrics": body.metrics,
            "gate": body.gate,
            "judge_model": body.judge_model,
        },
        idempotency_key=body.idempotency_key,
    )
    await session.flush()
    return {"job_id": str(job.id), "status": job.status}


@router.get("/jobs")
async def list_jobs(auth: AuthDep, session: SessionDep, project_id: UUID | None = None, limit: int = 50):
    stmt = select(Job).where(Job.org_id == auth.org_id).order_by(Job.created_at.desc()).limit(limit)
    if project_id:
        stmt = stmt.where(Job.project_id == project_id)
    rows = (await session.scalars(stmt)).all()
    return [orm_to_dict(r) for r in rows]


@router.get("/jobs/{job_id}")
async def get_job(job_id: UUID, auth: AuthDep, session: SessionDep):
    job = await session.get(Job, job_id)
    if not job or job.org_id != auth.org_id:
        raise HTTPException(404, "job not found")
    return orm_to_dict(job)


@router.post("/jobs/{job_id}/cancel")
async def cancel(job_id: UUID, auth: AuthDep, session: SessionDep):
    job = await session.get(Job, job_id)
    if not job or job.org_id != auth.org_id:
        raise HTTPException(404, "job not found")
    await cancel_job(session, job)
    return orm_to_dict(job)


@router.post("/jobs/{job_id}/heartbeat")
async def heartbeat(job_id: UUID, body: HeartbeatIn, auth: AuthDep, session: SessionDep):
    """Local LoRA runner reports progress back into the control plane."""
    job = await session.get(Job, job_id)
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
    from finehelper_core.jobs.queue import append_event
    from finehelper_core.enums import EventKind

    await append_event(session, job, EventKind.log.value, body.message or "heartbeat", body.metrics)
    return {"ok": True}


@router.get("/jobs/{job_id}/event-log")
async def event_log(job_id: UUID, auth: AuthDep, session: SessionDep):
    job = await session.get(Job, job_id)
    if not job or job.org_id != auth.org_id:
        raise HTTPException(404, "job not found")
    events = (
        await session.scalars(select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.created_at))
    ).all()
    return [orm_to_dict(e) for e in events]


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: UUID, auth: AuthDep, session: SessionDep, request: Request):
    job = await session.get(Job, job_id)
    if not job or job.org_id != auth.org_id:
        raise HTTPException(404, "job not found")

    async def gen():
        last_seen = None
        factory = request.app.state.session_factory
        while True:
            if await request.is_disconnected():
                break
            async with factory() as s:
                stmt = select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.created_at)
                if last_seen is not None:
                    stmt = stmt.where(JobEvent.created_at > last_seen)
                events = (await s.scalars(stmt)).all()
                current = await s.get(Job, job_id)
            for ev in events:
                last_seen = ev.created_at
                yield {"event": ev.kind, "data": json.dumps(orm_to_dict(ev))}
            if current and current.status in {"succeeded", "failed", "cancelled"}:
                yield {"event": "done", "data": json.dumps({"status": current.status})}
                break
            import asyncio

            await asyncio.sleep(0.8)

    return EventSourceResponse(gen())


@router.get("/runs")
async def list_runs(auth: AuthDep, session: SessionDep, project_id: UUID | None = None):
    stmt = select(Run).where(Run.org_id == auth.org_id).order_by(Run.created_at.desc())
    if project_id:
        stmt = stmt.where(Run.project_id == project_id)
    rows = (await session.scalars(stmt)).all()
    return [orm_to_dict(r) for r in rows]


@router.get("/runs/{run_id}")
async def get_run(run_id: UUID, auth: AuthDep, session: SessionDep):
    run = await session.get(Run, run_id)
    if not run or run.org_id != auth.org_id:
        raise HTTPException(404, "run not found")
    evals = (await session.scalars(select(EvalReport).where(EvalReport.run_id == run.id))).all()
    return {**orm_to_dict(run), "evals": [orm_to_dict(e) for e in evals]}


@router.get("/runs/{run_id}/compare")
async def compare_runs(run_id: UUID, other: UUID, auth: AuthDep, session: SessionDep):
    a = await session.get(Run, run_id)
    b = await session.get(Run, other)
    if not a or not b or a.org_id != auth.org_id or b.org_id != auth.org_id:
        raise HTTPException(404, "run not found")
    evals_a = (await session.scalars(select(EvalReport).where(EvalReport.run_id == a.id))).all()
    evals_b = (await session.scalars(select(EvalReport).where(EvalReport.run_id == b.id))).all()
    return {"a": {**orm_to_dict(a), "evals": [orm_to_dict(e) for e in evals_a]}, "b": {**orm_to_dict(b), "evals": [orm_to_dict(e) for e in evals_b]}}
