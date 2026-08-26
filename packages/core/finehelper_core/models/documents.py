from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MongoModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=new_id)

    def to_mongo(self) -> dict[str, Any]:
        data = self.model_dump(mode="python")
        data["_id"] = data.pop("id")
        return data

    @classmethod
    def from_mongo(cls, doc: dict[str, Any] | None) -> Self | None:
        if not doc:
            return None
        data = dict(doc)
        data["id"] = str(data.pop("_id"))
        return cls.model_validate(data)


class Timestamped(MongoModel):
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    def touch(self) -> None:
        self.updated_at = utcnow()


class Org(Timestamped):
    slug: str
    name: str
    deleted_at: datetime | None = None


class User(Timestamped):
    email: str
    password_hash: str
    name: str


class Membership(Timestamped):
    org_id: str
    user_id: str
    role: str = "owner"


class Invite(Timestamped):
    org_id: str
    email: str
    role: str = "member"
    token_hash: str
    invited_by: str
    accepted_at: datetime | None = None
    expires_at: datetime


class ApiKey(Timestamped):
    org_id: str
    user_id: str
    name: str
    prefix: str
    key_hash: str
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


class Project(Timestamped):
    org_id: str
    slug: str
    name: str
    task_type: str = "chat_sft"
    default_backend: str = "openai"
    default_base_model: str = "gpt-4.1-mini"
    quality_gate: dict[str, Any] | None = None
    deleted_at: datetime | None = None


class Credential(Timestamped):
    org_id: str
    provider: str
    encrypted_secret: str
    last4: str
    created_by: str


class Dataset(Timestamped):
    org_id: str
    project_id: str
    name: str
    description: str | None = None
    deleted_at: datetime | None = None


class DatasetVersion(Timestamped):
    org_id: str
    dataset_id: str
    content_digest: str
    uri: str
    row_count: int = 0
    schema_id: str = "chat_canonical_v1"
    stats: dict[str, Any] | None = None
    split_map: dict[str, Any] | None = None
    prepare_config: dict[str, Any] | None = None
    status: str = "pending"
    error_report_uri: str | None = None


class Recipe(Timestamped):
    org_id: str
    project_id: str
    name: str
    yaml_source: str
    parsed: dict[str, Any]


class Job(Timestamped):
    org_id: str
    project_id: str | None = None
    type: str
    status: str = "queued"
    parent_job_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    external_ref: str | None = None
    worker_id: str | None = None
    claimed_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    idempotency_key: str | None = None


class JobEvent(MongoModel):
    org_id: str
    job_id: str
    kind: str
    message: str = ""
    data: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Run(Timestamped):
    org_id: str
    project_id: str
    job_id: str
    dataset_version_id: str
    backend: str
    base_model: str
    hyperparams: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None
    provider_model_id: str | None = None
    adapter_uri: str | None = None
    git_sha: str | None = None


class Artifact(Timestamped):
    org_id: str
    run_id: str | None = None
    job_id: str | None = None
    kind: str
    uri: str
    size_bytes: int = 0
    content_type: str = "application/octet-stream"


class EvalReport(Timestamped):
    org_id: str
    project_id: str
    run_id: str
    job_id: str
    suite_digest: str
    metrics: dict[str, Any]
    passed: bool = False
    gate: dict[str, Any] | None = None
    traces_uri: str | None = None
    judge_model: str | None = None


class Deployment(Timestamped):
    org_id: str
    project_id: str
    run_id: str
    eval_report_id: str | None = None
    name: str
    backend: str
    target: dict[str, Any]
    override_gate: bool = False
    deleted_at: datetime | None = None


class UsageEvent(MongoModel):
    org_id: str
    job_id: str | None = None
    kind: str
    quantity: float = 0
    unit: str = "token"
    amount_usd: float | None = None
    created_at: datetime = Field(default_factory=utcnow)
