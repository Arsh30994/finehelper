from __future__ import annotations

from fastapi import HTTPException

from finehelper_api.deps import AuthContext
from finehelper_api.models import Dataset, dataset_model
from finehelper_api.schemas import DatasetIn, UploadCompleteIn, UploadInitIn, doc_to_dict
from finehelper_core.db.mongo import Mongo
from finehelper_core.enums import JobType
from finehelper_core.jobs.queue import enqueue_job
from finehelper_core.storage import ObjectStore, object_key


async def create_dataset(db: Mongo, auth: AuthContext, body: DatasetIn) -> dict:
    project = await dataset_model.find_project(db, str(body.project_id))
    if not project or project.org_id != auth.org_id:
        raise HTTPException(404, "project not found")
    row = Dataset(org_id=auth.org_id, project_id=str(body.project_id), name=body.name, description=body.description)
    await dataset_model.insert_dataset(db, row)
    return doc_to_dict(row)


async def list_datasets(db: Mongo, auth: AuthContext, project_id: str | None = None) -> list[dict]:
    return [doc_to_dict(d) for d in await dataset_model.list_datasets(db, auth.org_id, project_id)]


async def get_dataset(db: Mongo, auth: AuthContext, dataset_id: str) -> dict:
    row = await dataset_model.find_dataset(db, dataset_id)
    if not row or row.org_id != auth.org_id:
        raise HTTPException(404, "dataset not found")
    versions = await dataset_model.list_versions(db, dataset_id)
    return {**doc_to_dict(row), "versions": [doc_to_dict(v) for v in versions]}


async def init_upload(db: Mongo, auth: AuthContext, store: ObjectStore, body: UploadInitIn) -> dict:
    dataset = await dataset_model.find_dataset(db, str(body.dataset_id))
    if not dataset or dataset.org_id != auth.org_id:
        raise HTTPException(404, "dataset not found")
    key = object_key("uploads", str(auth.org_id), str(dataset.id), body.filename)
    url = store.presign_put(key, content_type=body.content_type)
    return {"key": key, "upload_url": url, "method": "PUT"}


async def complete_upload(
    db: Mongo, auth: AuthContext, store: ObjectStore, dataset_id: str, body: UploadCompleteIn
) -> dict:
    dataset = await dataset_model.find_dataset(db, dataset_id)
    if not dataset or dataset.org_id != auth.org_id:
        raise HTTPException(404, "dataset not found")
    if not store.exists(body.key):
        raise HTTPException(400, "upload not found at key; PUT the file first")
    uri = store.uri(body.key)
    job = await enqueue_job(
        db,
        org_id=auth.org_id,
        project_id=dataset.project_id,
        job_type=JobType.ingest.value,
        payload={
            "dataset_id": dataset.id,
            "uri": uri,
            "filename": body.filename,
            "format": body.format,
            "prepare": body.prepare,
            "auto_prepare": True,
        },
        idempotency_key=body.idempotency_key,
    )
    return {"job_id": job.id, "status": job.status}


async def get_version(db: Mongo, auth: AuthContext, dataset_id: str, version_id: str) -> dict:
    version = await dataset_model.find_version(db, version_id)
    if not version or version.org_id != auth.org_id or version.dataset_id != dataset_id:
        raise HTTPException(404, "version not found")
    return doc_to_dict(version)


async def preview_version(
    db: Mongo, auth: AuthContext, store: ObjectStore, dataset_id: str, version_id: str, limit: int = 8
) -> dict:
    from finehelper_core.dataset.prepare import canonical_loads
    from finehelper_core.storage import key_from_uri

    version = await dataset_model.find_version(db, version_id)
    if not version or version.org_id != auth.org_id or version.dataset_id != dataset_id:
        raise HTTPException(404, "version not found")
    if version.status != "ready":
        return {"status": version.status, "rows": [], "stats": version.stats}
    blob = store.get(key_from_uri(version.uri))
    rows = canonical_loads(blob)[: max(1, min(limit, 50))]
    return {"status": version.status, "stats": version.stats, "split_map": version.split_map, "rows": rows}
