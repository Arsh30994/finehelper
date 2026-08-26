from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request

from finehelper_api.controllers import job_controller
from finehelper_api.deps import AuthDep, DbDep
from finehelper_api.schemas import EvalIn, HeartbeatIn, TrainIn

router = APIRouter(prefix="/v1", tags=["jobs"])


@router.post("/jobs/train", status_code=202)
async def start_train(body: TrainIn, auth: AuthDep, db: DbDep):
    return await job_controller.start_train(db, auth, body)


@router.post("/evals", status_code=202)
async def start_eval(body: EvalIn, auth: AuthDep, db: DbDep, request: Request):
    return await job_controller.start_eval(db, auth, request.app.state.store, body)


@router.get("/jobs")
async def list_jobs(auth: AuthDep, db: DbDep, project_id: UUID | None = None, limit: int = 50):
    return await job_controller.list_jobs(db, auth, str(project_id) if project_id else None, limit)


@router.get("/jobs/{job_id}")
async def get_job(job_id: UUID, auth: AuthDep, db: DbDep):
    return await job_controller.get_job(db, auth, str(job_id))


@router.post("/jobs/{job_id}/cancel")
async def cancel(job_id: UUID, auth: AuthDep, db: DbDep):
    return await job_controller.cancel(db, auth, str(job_id))


@router.post("/jobs/{job_id}/heartbeat")
async def heartbeat(job_id: UUID, body: HeartbeatIn, auth: AuthDep, db: DbDep):
    return await job_controller.heartbeat(db, auth, str(job_id), body)


@router.get("/jobs/{job_id}/event-log")
async def event_log(job_id: UUID, auth: AuthDep, db: DbDep):
    return await job_controller.event_log(db, auth, str(job_id))


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: UUID, auth: AuthDep, db: DbDep, request: Request):
    return await job_controller.job_events(db, auth, str(job_id), request)


@router.get("/runs")
async def list_runs(auth: AuthDep, db: DbDep, project_id: UUID | None = None):
    return await job_controller.list_runs(db, auth, str(project_id) if project_id else None)


@router.get("/runs/{run_id}")
async def get_run(run_id: UUID, auth: AuthDep, db: DbDep):
    return await job_controller.get_run(db, auth, str(run_id))


@router.get("/runs/{run_id}/compare")
async def compare_runs(run_id: UUID, other: UUID, auth: AuthDep, db: DbDep):
    return await job_controller.compare_runs(db, auth, str(run_id), str(other))
