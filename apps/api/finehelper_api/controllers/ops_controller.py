from __future__ import annotations

from finehelper_api.deps import AuthContext
from finehelper_api.schemas import CredentialIn, DeployIn, PipelineIn, RecipeIn
from finehelper_api.services import ops_service
from finehelper_core.db.mongo import Mongo
from finehelper_core.settings import Settings


async def put_credential(db: Mongo, settings: Settings, auth: AuthContext, body: CredentialIn) -> dict:
    return await ops_service.put_credential(db, settings, auth, body)


async def list_credentials(db: Mongo, auth: AuthContext) -> list[dict]:
    return await ops_service.list_credentials(db, auth)


async def create_recipe(db: Mongo, auth: AuthContext, body: RecipeIn) -> dict:
    return await ops_service.create_recipe(db, auth, body)


async def start_pipeline(db: Mongo, auth: AuthContext, body: PipelineIn) -> dict:
    return await ops_service.start_pipeline(db, auth, body)


async def deploy(db: Mongo, auth: AuthContext, body: DeployIn) -> dict:
    return await ops_service.deploy(db, auth, body)


async def list_deployments(db: Mongo, auth: AuthContext, project_id: str | None = None) -> list[dict]:
    return await ops_service.list_deployments(db, auth, project_id)


async def get_eval(db: Mongo, auth: AuthContext, report_id: str) -> dict:
    return await ops_service.get_eval(db, auth, report_id)


async def usage(db: Mongo, auth: AuthContext) -> list[dict]:
    return await ops_service.usage(db, auth)
