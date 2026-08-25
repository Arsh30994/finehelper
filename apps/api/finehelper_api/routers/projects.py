from __future__ import annotations

import re
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from finehelper_api.deps import AuthDep, SessionDep
from finehelper_api.schemas import ProjectIn, orm_to_dict
from finehelper_core.db.models import Project

router = APIRouter(prefix="/v1", tags=["projects"])


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"


@router.get("/projects")
async def list_projects(auth: AuthDep, session: SessionDep):
    rows = (
        await session.scalars(
            select(Project).where(Project.org_id == auth.org_id, Project.deleted_at.is_(None)).order_by(Project.created_at.desc())
        )
    ).all()
    return [orm_to_dict(r) for r in rows]


@router.post("/projects", status_code=201)
async def create_project(body: ProjectIn, auth: AuthDep, session: SessionDep):
    slug = body.slug or _slugify(body.name)
    exists = await session.scalar(select(Project).where(Project.org_id == auth.org_id, Project.slug == slug))
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
    session.add(row)
    await session.flush()
    return orm_to_dict(row)


@router.get("/projects/{project_id}")
async def get_project(project_id: UUID, auth: AuthDep, session: SessionDep):
    row = await session.get(Project, project_id)
    if not row or row.org_id != auth.org_id or row.deleted_at:
        raise HTTPException(404, "project not found")
    return orm_to_dict(row)
