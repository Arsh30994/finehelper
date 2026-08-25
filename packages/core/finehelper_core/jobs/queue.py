from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from finehelper_core.dataset.prepare import scrub_log
from finehelper_core.db.models import Job, JobEvent
from finehelper_core.enums import EventKind, JobStatus


TERMINAL = {JobStatus.succeeded, JobStatus.failed, JobStatus.cancelled}


async def enqueue_job(
    session: AsyncSession,
    *,
    org_id: UUID,
    project_id: UUID | None,
    job_type: str,
    payload: dict[str, Any],
    parent_job_id: UUID | None = None,
    idempotency_key: str | None = None,
) -> Job:
    if idempotency_key:
        existing = await session.scalar(
            select(Job).where(Job.org_id == org_id, Job.idempotency_key == idempotency_key)
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
    session.add(job)
    await session.flush()
    session.add(
        JobEvent(
            org_id=org_id,
            job_id=job.id,
            kind=EventKind.queued.value,
            message=f"{job_type} queued",
        )
    )
    return job


async def append_event(
    session: AsyncSession,
    job: Job,
    kind: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> JobEvent:
    ev = JobEvent(org_id=job.org_id, job_id=job.id, kind=kind, message=scrub_log(message), data=data)
    session.add(ev)
    await session.flush()
    return ev


async def set_status(session: AsyncSession, job: Job, status: str, error: str | None = None) -> None:
    job.status = status
    if status == JobStatus.running.value and job.started_at is None:
        job.started_at = datetime.now(timezone.utc)
    if status in {s.value for s in TERMINAL}:
        job.finished_at = datetime.now(timezone.utc)
        if error:
            job.error = scrub_log(error)
    await append_event(session, job, EventKind.status.value, f"status={status}", {"status": status, "error": error})


async def claim_next_job(session: AsyncSession, worker_id: str) -> Job | None:
    bind = session.bind or session.get_bind()
    dialect = bind.dialect.name if bind is not None else "sqlite"
    stmt = (
        select(Job)
        .where(Job.status == JobStatus.queued.value)
        .order_by(Job.created_at)
        .limit(1)
    )
    if dialect == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)
    job = await session.scalar(stmt)
    if not job:
        return None
    now = datetime.now(timezone.utc)
    job.status = JobStatus.running.value
    job.worker_id = worker_id
    job.claimed_at = now
    job.started_at = now
    await append_event(session, job, EventKind.status.value, f"claimed by {worker_id}", {"worker_id": worker_id})
    return job


async def cancel_job(session: AsyncSession, job: Job) -> Job:
    if job.status in {s.value for s in TERMINAL}:
        return job
    await set_status(session, job, JobStatus.cancelled.value)
    return job
