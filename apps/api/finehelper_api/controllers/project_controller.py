from __future__ import annotations

import re

from fastapi import HTTPException

from finehelper_api.deps import AuthContext
from finehelper_api.models import Project, project_model
from finehelper_api.schemas import ProjectIn, doc_to_dict
from finehelper_core.db.mongo import Mongo


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"


async def list_projects(db: Mongo, auth: AuthContext) -> list[dict]:
    return [doc_to_dict(p) for p in await project_model.list_projects(db, auth.org_id)]


async def create_project(db: Mongo, auth: AuthContext, body: ProjectIn) -> dict:
    slug = body.slug or _slugify(body.name)
    if await project_model.find_by_slug(db, auth.org_id, slug):
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
    await project_model.insert(db, row)
    return doc_to_dict(row)


async def get_project(db: Mongo, auth: AuthContext, project_id: str) -> dict:
    row = await project_model.find_by_id(db, project_id)
    if not row or row.org_id != auth.org_id or row.deleted_at:
        raise HTTPException(404, "project not found")
    return doc_to_dict(row)
