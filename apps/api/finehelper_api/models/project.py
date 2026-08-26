"""Project Mongo repositories."""

from __future__ import annotations

from finehelper_core.db.mongo import Mongo
from finehelper_core.models import Project


async def list_projects(db: Mongo, org_id: str) -> list[Project]:
    rows = await db.projects.find({"org_id": org_id, "deleted_at": None}).sort("created_at", -1).to_list(200)
    return [p for p in (Project.from_mongo(r) for r in rows) if p]


async def find_by_slug(db: Mongo, org_id: str, slug: str) -> Project | None:
    return Project.from_mongo(await db.projects.find_one({"org_id": org_id, "slug": slug}))


async def find_by_id(db: Mongo, project_id: str) -> Project | None:
    return Project.from_mongo(await db.projects.find_one({"_id": project_id}))


async def insert(db: Mongo, project: Project) -> Project:
    await db.insert(db.projects, project)
    return project
