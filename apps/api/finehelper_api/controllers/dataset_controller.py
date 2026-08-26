from __future__ import annotations

from finehelper_api.deps import AuthContext
from finehelper_api.schemas import DatasetIn, UploadCompleteIn, UploadInitIn
from finehelper_api.services import dataset_service
from finehelper_core.db.mongo import Mongo
from finehelper_core.storage import ObjectStore


async def create_dataset(db: Mongo, auth: AuthContext, body: DatasetIn) -> dict:
    return await dataset_service.create_dataset(db, auth, body)


async def list_datasets(db: Mongo, auth: AuthContext, project_id: str | None = None) -> list[dict]:
    return await dataset_service.list_datasets(db, auth, project_id)


async def get_dataset(db: Mongo, auth: AuthContext, dataset_id: str) -> dict:
    return await dataset_service.get_dataset(db, auth, dataset_id)


async def init_upload(db: Mongo, auth: AuthContext, store: ObjectStore, body: UploadInitIn) -> dict:
    return await dataset_service.init_upload(db, auth, store, body)


async def complete_upload(
    db: Mongo, auth: AuthContext, store: ObjectStore, dataset_id: str, body: UploadCompleteIn
) -> dict:
    return await dataset_service.complete_upload(db, auth, store, dataset_id, body)


async def get_version(db: Mongo, auth: AuthContext, dataset_id: str, version_id: str) -> dict:
    return await dataset_service.get_version(db, auth, dataset_id, version_id)


async def preview_version(
    db: Mongo, auth: AuthContext, store: ObjectStore, dataset_id: str, version_id: str, limit: int = 8
) -> dict:
    return await dataset_service.preview_version(db, auth, store, dataset_id, version_id, limit)
