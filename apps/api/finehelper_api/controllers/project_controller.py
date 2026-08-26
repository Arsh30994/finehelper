from __future__ import annotations

from finehelper_api.deps import AuthContext
from finehelper_api.schemas import ProjectIn
from finehelper_api.services import project_service
from finehelper_core.db.mongo import Mongo


async def list_projects(db: Mongo, auth: AuthContext) -> list[dict]:
    return await project_service.list_projects(db, auth)


async def create_project(db: Mongo, auth: AuthContext, body: ProjectIn) -> dict:
    return await project_service.create_project(db, auth, body)


async def get_project(db: Mongo, auth: AuthContext, project_id: str) -> dict:
    return await project_service.get_project(db, auth, project_id)
