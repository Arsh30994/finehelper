from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import ReturnDocument

from finehelper_core.dataset.prepare import scrub_log
from finehelper_core.db.mongo import Mongo
from finehelper_core.enums import EventKind, JobStatus
from finehelper_core.models import Job, JobEvent

TERMINAL = {JobStatus.succeeded, JobStatus.failed, JobStatus.cancelled}


async def enqueue_job(
    db: Mongo,
    *,
    org_id: str,
    project_id: str | None,
    job_type: str,
    payload: dict[str, Any],
    parent_job_id: str | None = None,
    idempotency_key: str | None = None,
) -> Job:
    if idempotency_key:
        existing = Job.from_mongo(
            await db.jobs.find_one({"org_id": org_id, "idempotency_key": idempotency_key})
        )
        if existing:
            return existing
    job = Job(
        org_id=org_id,
        project_id=project_id,
        type=job_type,
        status=JobStatus.queued.value,
        payload=payload,
        parent_job_id=parent_job_id,
        idempotency_key=idempotency_key,
    )
    await db.insert(db.jobs, job)
    await append_event(db, job, EventKind.queued.value, f"{job_type} queued")
    return job


async def append_event(
    db: Mongo,
    job: Job,
    kind: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> JobEvent:
    ev = JobEvent(org_id=job.org_id, job_id=job.id, kind=kind, message=scrub_log(message), data=data)
    await db.insert(db.job_events, ev)
    return ev


async def persist_job(db: Mongo, job: Job) -> None:
    await db.save(db.jobs, job)


async def set_status(db: Mongo, job: Job, status: str, error: str | None = None) -> None:
    job.status = status
    if status == JobStatus.running.value and job.started_at is None:
        job.started_at = datetime.now(timezone.utc)
    if status in {s.value for s in TERMINAL}:
        job.finished_at = datetime.now(timezone.utc)
        if error:
            job.error = scrub_log(error)
    await persist_job(db, job)
    await append_event(db, job, EventKind.status.value, f"status={status}", {"status": status, "error": error})


async def claim_next_job(db: Mongo, worker_id: str) -> Job | None:
    now = datetime.now(timezone.utc)
    doc = await db.jobs.find_one_and_update(
        {"status": JobStatus.queued.value},
        {
            "$set": {
                "status": JobStatus.running.value,
                "worker_id": worker_id,
                "claimed_at": now,
                "started_at": now,
                "updated_at": now,
            }
        },
        sort=[("created_at", 1)],
        return_document=ReturnDocument.AFTER,
    )
    job = Job.from_mongo(doc)
    if not job:
        return None
    await append_event(db, job, EventKind.status.value, f"claimed by {worker_id}", {"worker_id": worker_id})
    return job


async def cancel_job(db: Mongo, job: Job) -> Job:
    if job.status in {s.value for s in TERMINAL}:
        return job
    await set_status(db, job, JobStatus.cancelled.value)
    return job
