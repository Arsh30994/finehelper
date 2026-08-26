"""Job / run Mongo repositories."""

from __future__ import annotations

from typing import Any

from finehelper_core.db.mongo import Mongo
from finehelper_core.models import DatasetVersion, EvalReport, Job, JobEvent, Project, Run


async def find_project(db: Mongo, project_id: str) -> Project | None:
    return Project.from_mongo(await db.projects.find_one({"_id": project_id}))


async def find_version(db: Mongo, version_id: str) -> DatasetVersion | None:
    return DatasetVersion.from_mongo(await db.dataset_versions.find_one({"_id": version_id}))


async def find_job(db: Mongo, job_id: str) -> Job | None:
    return Job.from_mongo(await db.jobs.find_one({"_id": job_id}))


async def list_jobs(db: Mongo, org_id: str, project_id: str | None = None, limit: int = 50) -> list[Job]:
    query: dict[str, Any] = {"org_id": org_id}
    if project_id:
        query["project_id"] = project_id
    rows = await db.jobs.find(query).sort("created_at", -1).to_list(max(1, min(limit, 200)))
    return [j for j in (Job.from_mongo(r) for r in rows) if j]


async def list_events(db: Mongo, job_id: str) -> list[JobEvent]:
    rows = await db.job_events.find({"job_id": job_id}).sort("created_at", 1).to_list(2000)
    return [e for e in (JobEvent.from_mongo(r) for r in rows) if e]


async def events_since(db: Mongo, job_id: str, after: Any | None) -> list[JobEvent]:
    query: dict[str, Any] = {"job_id": job_id}
    if after is not None:
        query["created_at"] = {"$gt": after}
    rows = await db.job_events.find(query).sort("created_at", 1).to_list(200)
    return [e for e in (JobEvent.from_mongo(r) for r in rows) if e]


async def find_run(db: Mongo, run_id: str) -> Run | None:
    return Run.from_mongo(await db.runs.find_one({"_id": run_id}))


async def list_runs(db: Mongo, org_id: str, project_id: str | None = None) -> list[Run]:
    query: dict[str, Any] = {"org_id": org_id}
    if project_id:
        query["project_id"] = project_id
    rows = await db.runs.find(query).sort("created_at", -1).to_list(200)
    return [r for r in (Run.from_mongo(r) for r in rows) if r]


async def list_evals_for_run(db: Mongo, run_id: str) -> list[EvalReport]:
    rows = await db.eval_reports.find({"run_id": run_id}).to_list(100)
    return [e for e in (EvalReport.from_mongo(r) for r in rows) if e]
