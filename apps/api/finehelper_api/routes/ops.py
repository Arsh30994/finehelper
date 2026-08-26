from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from finehelper_api.controllers import ops_controller
from finehelper_api.deps import AuthDep, DbDep, SettingsDep
from finehelper_api.schemas import CredentialIn, DeployIn, PipelineIn, RecipeIn

router = APIRouter(prefix="/v1", tags=["ops"])


@router.post("/credentials")
async def put_credential(body: CredentialIn, auth: AuthDep, db: DbDep, settings: SettingsDep):
    return await ops_controller.put_credential(db, settings, auth, body)


@router.get("/credentials")
async def list_credentials(auth: AuthDep, db: DbDep):
    return await ops_controller.list_credentials(db, auth)


@router.post("/recipes")
async def create_recipe(body: RecipeIn, auth: AuthDep, db: DbDep):
    return await ops_controller.create_recipe(db, auth, body)


@router.post("/pipelines", status_code=202)
async def start_pipeline(body: PipelineIn, auth: AuthDep, db: DbDep):
    return await ops_controller.start_pipeline(db, auth, body)


@router.post("/deployments", status_code=202)
async def deploy(body: DeployIn, auth: AuthDep, db: DbDep):
    return await ops_controller.deploy(db, auth, body)


@router.get("/deployments")
async def list_deployments(auth: AuthDep, db: DbDep, project_id: UUID | None = None):
    return await ops_controller.list_deployments(db, auth, str(project_id) if project_id else None)


@router.get("/evals/{report_id}")
async def get_eval(report_id: UUID, auth: AuthDep, db: DbDep):
    return await ops_controller.get_eval(db, auth, str(report_id))


@router.get("/usage")
async def usage(auth: AuthDep, db: DbDep):
    return await ops_controller.usage(db, auth)
