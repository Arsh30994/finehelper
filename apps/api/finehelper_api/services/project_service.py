from __future__ import annotations

import re

from fastapi import HTTPException

from finehelper_api.deps import AuthContext
from finehelper_api.schemas import ProjectIn, doc_to_dict
from finehelper_core.db.mongo import Mongo
from finehelper_core.models import Project


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"


async def list_projects(db: Mongo, auth: AuthContext) -> list[dict]:
    rows = await db.projects.find({"org_id": auth.org_id, "deleted_at": None}).sort("created_at", -1).to_list(200)
    return [doc_to_dict(Project.from_mongo(r)) for r in rows if r]


async def create_project(db: Mongo, auth: AuthContext, body: ProjectIn) -> dict:
    slug = body.slug or _slugify(body.name)
    exists = await db.projects.find_one({"org_id": auth.org_id, "slug": slug})
    if exists:
        raise HTTPException(409, "slug already exists")
    row = Project(
        org_id=auth.org_id,
        name=body.name,
        slug=slug,
        task_type=body.task_type,
        default_backend=body.default_backend,
        default_base_model=body.default_base_model,
        quality_gate=body.quality_gate,
    )
    await db.insert(db.projects, row)
    return doc_to_dict(row)


async def get_project(db: Mongo, auth: AuthContext, project_id: str) -> dict:
    row = Project.from_mongo(await db.projects.find_one({"_id": project_id}))
    if not row or row.org_id != auth.org_id or row.deleted_at:
        raise HTTPException(404, "project not found")
    return doc_to_dict(row)
