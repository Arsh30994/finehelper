"""Ops (credentials, recipes, deployments) Mongo repositories."""

from __future__ import annotations

from finehelper_core.db.mongo import Mongo
from finehelper_core.models import Credential, Deployment, EvalReport, Project, Recipe, Run, UsageEvent


async def find_credential(db: Mongo, org_id: str, provider: str) -> Credential | None:
    return Credential.from_mongo(await db.credentials.find_one({"org_id": org_id, "provider": provider}))


async def save_credential(db: Mongo, cred: Credential) -> None:
    await db.save(db.credentials, cred)


async def insert_credential(db: Mongo, cred: Credential) -> Credential:
    await db.insert(db.credentials, cred)
    return cred


async def list_credentials(db: Mongo, org_id: str) -> list[Credential]:
    rows = await db.credentials.find({"org_id": org_id}).to_list(100)
    return [c for c in (Credential.from_mongo(r) for r in rows) if c]


async def find_project(db: Mongo, project_id: str) -> Project | None:
    return Project.from_mongo(await db.projects.find_one({"_id": project_id}))


async def insert_recipe(db: Mongo, recipe: Recipe) -> Recipe:
    await db.insert(db.recipes, recipe)
    return recipe


async def find_run(db: Mongo, run_id: str) -> Run | None:
    return Run.from_mongo(await db.runs.find_one({"_id": run_id}))


async def list_deployments(db: Mongo, org_id: str, project_id: str | None = None) -> list[Deployment]:
    query: dict = {"org_id": org_id, "deleted_at": None}
    if project_id:
        query["project_id"] = project_id
    rows = await db.deployments.find(query).sort("created_at", -1).to_list(200)
    return [d for d in (Deployment.from_mongo(r) for r in rows) if d]


async def find_eval(db: Mongo, report_id: str) -> EvalReport | None:
    return EvalReport.from_mongo(await db.eval_reports.find_one({"_id": report_id}))


async def list_usage(db: Mongo, org_id: str) -> list[UsageEvent]:
    rows = await db.usage_events.find({"org_id": org_id}).to_list(500)
    return [u for u in (UsageEvent.from_mongo(r) for r in rows) if u]
