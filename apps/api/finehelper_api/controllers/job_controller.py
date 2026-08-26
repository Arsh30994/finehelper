from __future__ import annotations

import asyncio
import json

from fastapi import Request
from sse_starlette.sse import EventSourceResponse

from finehelper_api.deps import AuthContext
from finehelper_api.schemas import EvalIn, HeartbeatIn, TrainIn, doc_to_dict
from finehelper_api.services import job_service
from finehelper_core.db.mongo import Mongo
from finehelper_core.storage import ObjectStore


async def start_train(db: Mongo, auth: AuthContext, body: TrainIn) -> dict:
    return await job_service.start_train(db, auth, body)


async def start_eval(db: Mongo, auth: AuthContext, store: ObjectStore, body: EvalIn) -> dict:
    return await job_service.start_eval(db, auth, store, body)


async def list_jobs(db: Mongo, auth: AuthContext, project_id: str | None = None, limit: int = 50) -> list[dict]:
    return await job_service.list_jobs(db, auth, project_id, limit)


async def get_job(db: Mongo, auth: AuthContext, job_id: str) -> dict:
    return await job_service.get_job(db, auth, job_id)


async def cancel(db: Mongo, auth: AuthContext, job_id: str) -> dict:
    return await job_service.cancel(db, auth, job_id)


async def heartbeat(db: Mongo, auth: AuthContext, job_id: str, body: HeartbeatIn) -> dict:
    return await job_service.heartbeat(db, auth, job_id, body)


async def event_log(db: Mongo, auth: AuthContext, job_id: str) -> list[dict]:
    return await job_service.event_log(db, auth, job_id)


async def job_events(db: Mongo, auth: AuthContext, job_id: str, request: Request) -> EventSourceResponse:
    await job_service.require_job(db, auth, job_id)

    async def gen():
        last_seen = None
        while True:
            if await request.is_disconnected():
                break
            events, current = await job_service.events_since(request.app.state.db, job_id, last_seen)
            for ev in events:
                last_seen = ev.created_at
                yield {"event": ev.kind, "data": json.dumps(doc_to_dict(ev))}
            if current and current.status in {"succeeded", "failed", "cancelled"}:
                yield {"event": "done", "data": json.dumps({"status": current.status})}
                break
            await asyncio.sleep(0.8)

    return EventSourceResponse(gen())


async def list_runs(db: Mongo, auth: AuthContext, project_id: str | None = None) -> list[dict]:
    return await job_service.list_runs(db, auth, project_id)


async def get_run(db: Mongo, auth: AuthContext, run_id: str) -> dict:
    return await job_service.get_run(db, auth, run_id)


async def compare_runs(db: Mongo, auth: AuthContext, run_id: str, other: str) -> dict:
    return await job_service.compare_runs(db, auth, run_id, other)
