"""Chat / inference Mongo repositories."""

from __future__ import annotations

from finehelper_core.db.mongo import Mongo
from finehelper_core.models import Credential, Deployment, Run


async def find_openai_credential(db: Mongo, org_id: str) -> Credential | None:
    return Credential.from_mongo(await db.credentials.find_one({"org_id": org_id, "provider": "openai"}))


async def find_deployment(db: Mongo, deployment_id: str) -> Deployment | None:
    return Deployment.from_mongo(await db.deployments.find_one({"_id": deployment_id}))


async def find_run(db: Mongo, run_id: str) -> Run | None:
    return Run.from_mongo(await db.runs.find_one({"_id": run_id}))
