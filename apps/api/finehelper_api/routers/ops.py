from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from finehelper_api.deps import AuthDep, SessionDep
from finehelper_api.schemas import CredentialIn, DeployIn, PipelineIn, RecipeIn, orm_to_dict
from finehelper_core.crypto import encrypt_secret, last4
from finehelper_core.db.models import Credential, Deployment, EvalReport, Project, Recipe, Run, UsageEvent
from finehelper_core.enums import JobType
from finehelper_core.jobs.queue import enqueue_job
from finehelper_core.recipe import parse_recipe

router = APIRouter(prefix="/v1", tags=["ops"])


@router.post("/credentials")
async def put_credential(body: CredentialIn, auth: AuthDep, session: SessionDep, request_settings=None):
    from finehelper_core.settings import get_settings

    settings = get_settings()
    existing = await session.scalar(
        select(Credential).where(Credential.org_id == auth.org_id, Credential.provider == body.provider)
    )
    token = encrypt_secret(body.secret, settings.master_key)
    if existing:
        existing.encrypted_secret = token
        existing.last4 = last4(body.secret)
        row = existing
    else:
        row = Credential(
            org_id=auth.org_id,
            provider=body.provider,
            encrypted_secret=token,
            last4=last4(body.secret),
            created_by=auth.user_id,
        )
        session.add(row)
    await session.flush()
    return orm_to_dict(row)


@router.get("/credentials")
async def list_credentials(auth: AuthDep, session: SessionDep):
    rows = (await session.scalars(select(Credential).where(Credential.org_id == auth.org_id))).all()
    return [orm_to_dict(r) for r in rows]


@router.post("/recipes")
async def create_recipe(body: RecipeIn, auth: AuthDep, session: SessionDep):
    project = await session.get(Project, body.project_id)
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
    session.add(row)
    await session.flush()
    return orm_to_dict(row)


@router.post("/pipelines", status_code=202)
async def start_pipeline(body: PipelineIn, auth: AuthDep, session: SessionDep):
    project = await session.get(Project, body.project_id)
    if not project or project.org_id != auth.org_id:
        raise HTTPException(404, "project not found")
    source = body.yaml_source if body.yaml_source is not None else body.recipe
    if source is None:
        raise HTTPException(400, "yaml_source or recipe required")
    doc = parse_recipe(source)
    if not body.dataset_version_id:
        raise HTTPException(400, "dataset_version_id required for pipeline v1")
    train_job = await enqueue_job(
        session,
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
    await session.flush()
    return {"job_id": str(train_job.id), "recipe": doc.model_dump(mode="json")}


@router.post("/deployments", status_code=202)
async def deploy(body: DeployIn, auth: AuthDep, session: SessionDep):
    run = await session.get(Run, body.run_id)
    if not run or run.org_id != auth.org_id:
        raise HTTPException(404, "run not found")
    job = await enqueue_job(
        session,
        org_id=auth.org_id,
        project_id=run.project_id,
        job_type=JobType.deploy.value,
        payload={
            "run_id": str(run.id),
            "name": body.name,
            "override_gate": body.override_gate,
            "eval_report_id": str(body.eval_report_id) if body.eval_report_id else None,
        },
        idempotency_key=body.idempotency_key,
    )
    await session.flush()
    return {"job_id": str(job.id), "status": job.status}


@router.get("/deployments")
async def list_deployments(auth: AuthDep, session: SessionDep, project_id: UUID | None = None):
    stmt = select(Deployment).where(Deployment.org_id == auth.org_id, Deployment.deleted_at.is_(None))
    if project_id:
        stmt = stmt.where(Deployment.project_id == project_id)
    rows = (await session.scalars(stmt.order_by(Deployment.created_at.desc()))).all()
    return [orm_to_dict(r) for r in rows]


@router.get("/evals/{report_id}")
async def get_eval(report_id: UUID, auth: AuthDep, session: SessionDep):
    row = await session.get(EvalReport, report_id)
    if not row or row.org_id != auth.org_id:
        raise HTTPException(404, "eval not found")
    return orm_to_dict(row)


@router.get("/usage")
async def usage(auth: AuthDep, session: SessionDep):
    rows = (await session.scalars(select(UsageEvent).where(UsageEvent.org_id == auth.org_id))).all()
    return [orm_to_dict(r) for r in rows]
