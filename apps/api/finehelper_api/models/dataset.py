"""Dataset Mongo repositories."""

from __future__ import annotations

from finehelper_core.db.mongo import Mongo
from finehelper_core.models import Dataset, DatasetVersion, Project


async def find_project(db: Mongo, project_id: str) -> Project | None:
    return Project.from_mongo(await db.projects.find_one({"_id": project_id}))


async def insert_dataset(db: Mongo, dataset: Dataset) -> Dataset:
    await db.insert(db.datasets, dataset)
    return dataset


async def list_datasets(db: Mongo, org_id: str, project_id: str | None = None) -> list[Dataset]:
    query: dict = {"org_id": org_id, "deleted_at": None}
    if project_id:
        query["project_id"] = project_id
    rows = await db.datasets.find(query).sort("created_at", -1).to_list(200)
    return [d for d in (Dataset.from_mongo(r) for r in rows) if d]


async def find_dataset(db: Mongo, dataset_id: str) -> Dataset | None:
    return Dataset.from_mongo(await db.datasets.find_one({"_id": dataset_id}))


async def list_versions(db: Mongo, dataset_id: str) -> list[DatasetVersion]:
    rows = await db.dataset_versions.find({"dataset_id": dataset_id}).sort("created_at", -1).to_list(200)
    return [v for v in (DatasetVersion.from_mongo(r) for r in rows) if v]


async def find_version(db: Mongo, version_id: str) -> DatasetVersion | None:
    return DatasetVersion.from_mongo(await db.dataset_versions.find_one({"_id": version_id}))
