from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from finehelper_api.controllers import project_controller
from finehelper_api.deps import AuthDep, DbDep
from finehelper_api.schemas import ProjectIn

router = APIRouter(prefix="/v1", tags=["projects"])


@router.get("/projects")
async def list_projects(auth: AuthDep, db: DbDep):
    return await project_controller.list_projects(db, auth)


@router.post("/projects", status_code=201)
async def create_project(body: ProjectIn, auth: AuthDep, db: DbDep):
    return await project_controller.create_project(db, auth, body)


@router.get("/projects/{project_id}")
async def get_project(project_id: UUID, auth: AuthDep, db: DbDep):
    return await project_controller.get_project(db, auth, str(project_id))
