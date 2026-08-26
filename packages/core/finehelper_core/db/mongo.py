from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ASCENDING, IndexModel

from finehelper_core.models import MongoModel
from finehelper_core.settings import Settings


class Mongo:
    """Single Motor client reused for the API process and embedded worker."""

    def __init__(self, client: AsyncIOMotorClient, database: AsyncIOMotorDatabase):
        self.client = client
        self.database = database
        self.orgs: AsyncIOMotorCollection = database["orgs"]
        self.users: AsyncIOMotorCollection = database["users"]
        self.memberships: AsyncIOMotorCollection = database["memberships"]
        self.invites: AsyncIOMotorCollection = database["invites"]
        self.api_keys: AsyncIOMotorCollection = database["api_keys"]
        self.projects: AsyncIOMotorCollection = database["projects"]
        self.credentials: AsyncIOMotorCollection = database["credentials"]
        self.datasets: AsyncIOMotorCollection = database["datasets"]
        self.dataset_versions: AsyncIOMotorCollection = database["dataset_versions"]
        self.recipes: AsyncIOMotorCollection = database["recipes"]
        self.jobs: AsyncIOMotorCollection = database["jobs"]
        self.job_events: AsyncIOMotorCollection = database["job_events"]
        self.runs: AsyncIOMotorCollection = database["runs"]
        self.artifacts: AsyncIOMotorCollection = database["artifacts"]
        self.eval_reports: AsyncIOMotorCollection = database["eval_reports"]
        self.deployments: AsyncIOMotorCollection = database["deployments"]
        self.usage_events: AsyncIOMotorCollection = database["usage_events"]

    async def ping(self) -> None:
        await self.client.admin.command("ping")

    def close(self) -> None:
        self.client.close()

    async def insert(self, coll: AsyncIOMotorCollection, model: MongoModel) -> None:
        await coll.insert_one(model.to_mongo())

    async def save(self, coll: AsyncIOMotorCollection, model: MongoModel) -> None:
        if hasattr(model, "touch"):
            model.touch()
        await coll.replace_one({"_id": model.id}, model.to_mongo(), upsert=True)


def make_client(settings: Settings) -> AsyncIOMotorClient:
    # Long-running Render web + CPU worker (OLTP). Two processes, one client each.
    # Peak concurrent ops are API requests plus a handful of job polls — 50 leaves
    # headroom without pinning ~1MB/conn on a starter Mongo instance.
    return AsyncIOMotorClient(
        settings.mongodb_uri,
        maxPoolSize=50,
        # minPoolSize=0: API and worker are separate clients; do not pre-open
        # 10–20 sockets each on a small local or Atlas M0/M2 cluster.
        minPoolSize=0,
        maxIdleTimeMS=300_000,  # 5 min — drop idle sockets between bursts
        connectTimeoutMS=10_000,
        serverSelectionTimeoutMS=5_000,
        retryWrites=True,
    )


def connect_mongo(settings: Settings) -> Mongo:
    client = make_client(settings)
    return Mongo(client, client[settings.mongodb_db])


async def ensure_indexes(db: Mongo) -> None:
    await db.users.create_indexes([IndexModel([("email", ASCENDING)], unique=True, name="uq_users_email")])
    await db.orgs.create_indexes([IndexModel([("slug", ASCENDING)], unique=True, name="uq_orgs_slug")])
    await db.memberships.create_indexes(
        [
            IndexModel([("org_id", ASCENDING), ("user_id", ASCENDING)], unique=True, name="uq_membership_org_user"),
            IndexModel([("user_id", ASCENDING)], name="ix_membership_user"),
        ]
    )
    await db.invites.create_indexes(
        [
            IndexModel([("token_hash", ASCENDING)], unique=True, name="uq_invites_token"),
            IndexModel([("org_id", ASCENDING), ("email", ASCENDING)], name="ix_invites_org_email"),
        ]
    )
    await db.api_keys.create_indexes(
        [
            IndexModel([("key_hash", ASCENDING)], unique=True, name="uq_api_keys_hash"),
            IndexModel([("org_id", ASCENDING), ("revoked_at", ASCENDING)], name="ix_api_keys_org"),
            IndexModel([("prefix", ASCENDING)], name="ix_api_keys_prefix"),
        ]
    )
    await db.projects.create_indexes(
        [
            IndexModel([("org_id", ASCENDING), ("slug", ASCENDING)], unique=True, name="uq_project_org_slug"),
            IndexModel([("org_id", ASCENDING), ("created_at", ASCENDING)], name="ix_projects_org_created"),
        ]
    )
    await db.credentials.create_indexes(
        [IndexModel([("org_id", ASCENDING), ("provider", ASCENDING)], unique=True, name="uq_credential_org_provider")]
    )
    await db.datasets.create_indexes(
        [
            IndexModel([("org_id", ASCENDING), ("project_id", ASCENDING)], name="ix_datasets_org_project"),
            IndexModel([("project_id", ASCENDING), ("created_at", ASCENDING)], name="ix_datasets_project_created"),
        ]
    )
    await db.dataset_versions.create_indexes(
        [
            IndexModel([("dataset_id", ASCENDING), ("created_at", ASCENDING)], name="ix_versions_dataset_created"),
            IndexModel([("org_id", ASCENDING), ("content_digest", ASCENDING)], name="ix_versions_digest"),
        ]
    )
    await db.jobs.create_indexes(
        [
            IndexModel([("status", ASCENDING), ("created_at", ASCENDING)], name="ix_jobs_queue"),
            IndexModel([("org_id", ASCENDING), ("created_at", ASCENDING)], name="ix_jobs_org_created"),
            IndexModel(
                [("org_id", ASCENDING), ("idempotency_key", ASCENDING)],
                unique=True,
                name="uq_job_idempotency",
                partialFilterExpression={"idempotency_key": {"$type": "string"}},
            ),
        ]
    )
    await db.job_events.create_indexes(
        [IndexModel([("job_id", ASCENDING), ("created_at", ASCENDING)], name="ix_job_events_job_created")]
    )
    await db.runs.create_indexes(
        [
            IndexModel([("job_id", ASCENDING)], unique=True, name="uq_runs_job"),
            IndexModel([("org_id", ASCENDING), ("project_id", ASCENDING), ("created_at", ASCENDING)], name="ix_runs_org_project"),
        ]
    )
    await db.artifacts.create_indexes(
        [
            IndexModel([("run_id", ASCENDING)], name="ix_artifacts_run"),
            IndexModel([("job_id", ASCENDING)], name="ix_artifacts_job"),
        ]
    )
    await db.eval_reports.create_indexes(
        [IndexModel([("run_id", ASCENDING), ("created_at", ASCENDING)], name="ix_evals_run_created")]
    )
    await db.deployments.create_indexes(
        [IndexModel([("org_id", ASCENDING), ("project_id", ASCENDING), ("created_at", ASCENDING)], name="ix_deployments_org_project")]
    )
    await db.usage_events.create_indexes([IndexModel([("org_id", ASCENDING), ("created_at", ASCENDING)], name="ix_usage_org")])


async def get_by_id(coll: AsyncIOMotorCollection, model_cls: type[MongoModel], doc_id: str) -> Any:
    return model_cls.from_mongo(await coll.find_one({"_id": str(doc_id)}))
