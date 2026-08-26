from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request

from finehelper_api.controllers import dataset_controller
from finehelper_api.deps import AuthDep, DbDep
from finehelper_api.schemas import DatasetIn, UploadCompleteIn, UploadInitIn

router = APIRouter(prefix="/v1", tags=["datasets"])


@router.post("/datasets", status_code=201)
async def create_dataset(body: DatasetIn, auth: AuthDep, db: DbDep):
    return await dataset_controller.create_dataset(db, auth, body)


@router.get("/datasets")
async def list_datasets(auth: AuthDep, db: DbDep, project_id: UUID | None = None):
    return await dataset_controller.list_datasets(db, auth, str(project_id) if project_id else None)


@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: UUID, auth: AuthDep, db: DbDep):
    return await dataset_controller.get_dataset(db, auth, str(dataset_id))


@router.post("/datasets/uploads")
async def init_upload(body: UploadInitIn, auth: AuthDep, db: DbDep, request: Request):
    return await dataset_controller.init_upload(db, auth, request.app.state.store, body)


@router.post("/datasets/{dataset_id}/versions", status_code=202)
async def complete_upload(dataset_id: UUID, body: UploadCompleteIn, auth: AuthDep, db: DbDep, request: Request):
    return await dataset_controller.complete_upload(db, auth, request.app.state.store, str(dataset_id), body)


@router.get("/datasets/{dataset_id}/versions/{version_id}")
async def get_version(dataset_id: UUID, version_id: UUID, auth: AuthDep, db: DbDep):
    return await dataset_controller.get_version(db, auth, str(dataset_id), str(version_id))


@router.get("/datasets/{dataset_id}/versions/{version_id}/preview")
async def preview_version(
    dataset_id: UUID, version_id: UUID, auth: AuthDep, db: DbDep, request: Request, limit: int = 8
):
    return await dataset_controller.preview_version(
        db, auth, request.app.state.store, str(dataset_id), str(version_id), limit
    )
