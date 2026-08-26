from __future__ import annotations

from fastapi import HTTPException

from finehelper_api.deps import AuthContext
from finehelper_api.schemas import CredentialIn, DeployIn, PipelineIn, RecipeIn, doc_to_dict
from finehelper_core.crypto import encrypt_secret, last4
from finehelper_core.db.mongo import Mongo
from finehelper_core.enums import JobType
from finehelper_core.jobs.queue import enqueue_job
from finehelper_core.models import Credential, Deployment, EvalReport, Project, Recipe, Run, UsageEvent
from finehelper_core.recipe import parse_recipe
from finehelper_core.settings import Settings


async def put_credential(db: Mongo, settings: Settings, auth: AuthContext, body: CredentialIn) -> dict:
    existing = Credential.from_mongo(
        await db.credentials.find_one({"org_id": auth.org_id, "provider": body.provider})
    )
    token = encrypt_secret(body.secret, settings.master_key)
    if existing:
        existing.encrypted_secret = token
        existing.last4 = last4(body.secret)
        await db.save(db.credentials, existing)
        row = existing
    else:
        row = Credential(
            org_id=auth.org_id,
            provider=body.provider,
            encrypted_secret=token,
            last4=last4(body.secret),
            created_by=auth.user_id,
        )
        await db.insert(db.credentials, row)
    return doc_to_dict(row)


async def list_credentials(db: Mongo, auth: AuthContext) -> list[dict]:
    rows = await db.credentials.find({"org_id": auth.org_id}).to_list(100)
    return [doc_to_dict(Credential.from_mongo(r)) for r in rows if r]


async def create_recipe(db: Mongo, auth: AuthContext, body: RecipeIn) -> dict:
    project = Project.from_mongo(await db.projects.find_one({"_id": str(body.project_id)}))
    if not project or project.org_id != auth.org_id:
        raise HTTPException(404, "project not found")
    parsed = parse_recipe(body.yaml_source)
    row = Recipe(
        org_id=auth.org_id,
        project_id=project.id,
        name=body.name,
        yaml_source=body.yaml_source,
        parsed=parsed.model_dump(mode="json"),
    )
    await db.insert(db.recipes, row)
    return doc_to_dict(row)


async def start_pipeline(db: Mongo, auth: AuthContext, body: PipelineIn) -> dict:
    project = Project.from_mongo(await db.projects.find_one({"_id": str(body.project_id)}))
    if not project or project.org_id != auth.org_id:
        raise HTTPException(404, "project not found")
    source = body.yaml_source if body.yaml_source is not None else body.recipe
    if source is None:
        raise HTTPException(400, "yaml_source or recipe required")
    doc = parse_recipe(source)
    if not body.dataset_version_id:
        raise HTTPException(400, "dataset_version_id required for pipeline v1")
    train_job = await enqueue_job(
        db,
        org_id=auth.org_id,
        project_id=project.id,
        job_type=JobType.train.value,
        payload={
            "dataset_version_id": str(body.dataset_version_id),
            "backend": doc.train.backend,
            "recipe": doc.model_dump(mode="json"),
            "git_sha": body.git_sha,
        },
        idempotency_key=body.idempotency_key,
    )
    return {"job_id": train_job.id, "recipe": doc.model_dump(mode="json")}


async def deploy(db: Mongo, auth: AuthContext, body: DeployIn) -> dict:
    run = Run.from_mongo(await db.runs.find_one({"_id": str(body.run_id)}))
    if not run or run.org_id != auth.org_id:
        raise HTTPException(404, "run not found")
    job = await enqueue_job(
        db,
        org_id=auth.org_id,
        project_id=run.project_id,
        job_type=JobType.deploy.value,
        payload={
            "run_id": run.id,
            "name": body.name,
            "override_gate": body.override_gate,
            "eval_report_id": str(body.eval_report_id) if body.eval_report_id else None,
        },
        idempotency_key=body.idempotency_key,
    )
    return {"job_id": job.id, "status": job.status}


async def list_deployments(db: Mongo, auth: AuthContext, project_id: str | None = None) -> list[dict]:
    query: dict = {"org_id": auth.org_id, "deleted_at": None}
    if project_id:
        query["project_id"] = project_id
    rows = await db.deployments.find(query).sort("created_at", -1).to_list(200)
    return [doc_to_dict(Deployment.from_mongo(r)) for r in rows if r]


async def get_eval(db: Mongo, auth: AuthContext, report_id: str) -> dict:
    row = EvalReport.from_mongo(await db.eval_reports.find_one({"_id": report_id}))
    if not row or row.org_id != auth.org_id:
        raise HTTPException(404, "eval not found")
    return doc_to_dict(row)


async def usage(db: Mongo, auth: AuthContext) -> list[dict]:
    rows = await db.usage_events.find({"org_id": auth.org_id}).to_list(500)
    return [doc_to_dict(UsageEvent.from_mongo(r)) for r in rows if r]
