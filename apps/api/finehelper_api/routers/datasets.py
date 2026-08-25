from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from finehelper_api.deps import AuthDep, SessionDep
from finehelper_api.schemas import DatasetIn, UploadCompleteIn, UploadInitIn, orm_to_dict
from finehelper_core.db.models import Dataset, DatasetVersion, Job, Project
from finehelper_core.enums import JobType
from finehelper_core.jobs.queue import enqueue_job
from finehelper_core.storage import object_key

router = APIRouter(prefix="/v1", tags=["datasets"])


@router.post("/datasets", status_code=201)
async def create_dataset(body: DatasetIn, auth: AuthDep, session: SessionDep):
    project = await session.get(Project, body.project_id)
    if not project or project.org_id != auth.org_id:
        raise HTTPException(404, "project not found")
    row = Dataset(org_id=auth.org_id, project_id=body.project_id, name=body.name, description=body.description)
    session.add(row)
    await session.flush()
    return orm_to_dict(row)


@router.get("/datasets")
async def list_datasets(auth: AuthDep, session: SessionDep, project_id: UUID | None = None):
    stmt = select(Dataset).where(Dataset.org_id == auth.org_id, Dataset.deleted_at.is_(None))
    if project_id:
        stmt = stmt.where(Dataset.project_id == project_id)
    rows = (await session.scalars(stmt.order_by(Dataset.created_at.desc()))).all()
    return [orm_to_dict(r) for r in rows]


@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: UUID, auth: AuthDep, session: SessionDep):
    row = await session.get(Dataset, dataset_id)
    if not row or row.org_id != auth.org_id:
        raise HTTPException(404, "dataset not found")
    versions = (
        await session.scalars(
            select(DatasetVersion).where(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.created_at.desc())
        )
    ).all()
    return {**orm_to_dict(row), "versions": [orm_to_dict(v) for v in versions]}


@router.post("/datasets/uploads")
async def init_upload(body: UploadInitIn, auth: AuthDep, session: SessionDep, request: Request):
    dataset = await session.get(Dataset, body.dataset_id)
    if not dataset or dataset.org_id != auth.org_id:
        raise HTTPException(404, "dataset not found")
    store = request.app.state.store
    key = object_key("uploads", str(auth.org_id), str(dataset.id), body.filename)
    url = store.presign_put(key, content_type=body.content_type)
    return {"key": key, "upload_url": url, "method": "PUT"}


@router.post("/datasets/{dataset_id}/versions", status_code=202)
async def complete_upload(dataset_id: UUID, body: UploadCompleteIn, auth: AuthDep, session: SessionDep, request: Request):
    dataset = await session.get(Dataset, dataset_id)
    if not dataset or dataset.org_id != auth.org_id:
        raise HTTPException(404, "dataset not found")
    store = request.app.state.store
    if not store.exists(body.key):
        raise HTTPException(400, "upload not found at key; PUT the file first")
    uri = store.uri(body.key)
    job = await enqueue_job(
        session,
        org_id=auth.org_id,
        project_id=dataset.project_id,
        job_type=JobType.ingest.value,
        payload={
            "dataset_id": str(dataset.id),
            "uri": uri,
            "filename": body.filename,
            "format": body.format,
            "prepare": body.prepare,
            "auto_prepare": True,
        },
        idempotency_key=body.idempotency_key,
    )
    await session.flush()
    return {"job_id": str(job.id), "status": job.status}


@router.get("/datasets/{dataset_id}/versions/{version_id}")
async def get_version(dataset_id: UUID, version_id: UUID, auth: AuthDep, session: SessionDep):
    version = await session.get(DatasetVersion, version_id)
    if not version or version.org_id != auth.org_id or version.dataset_id != dataset_id:
        raise HTTPException(404, "version not found")
    return orm_to_dict(version)


@router.get("/datasets/{dataset_id}/versions/{version_id}/preview")
async def preview_version(dataset_id: UUID, version_id: UUID, auth: AuthDep, session: SessionDep, request: Request, limit: int = 8):
    from finehelper_core.dataset.prepare import canonical_loads
    from finehelper_core.storage import key_from_uri

    version = await session.get(DatasetVersion, version_id)
    if not version or version.org_id != auth.org_id or version.dataset_id != dataset_id:
        raise HTTPException(404, "version not found")
    if version.status != "ready":
        return {"status": version.status, "rows": [], "stats": version.stats}
    blob = request.app.state.store.get(key_from_uri(version.uri))
    rows = canonical_loads(blob)[: max(1, min(limit, 50))]
    return {"status": version.status, "stats": version.stats, "split_map": version.split_map, "rows": rows}
