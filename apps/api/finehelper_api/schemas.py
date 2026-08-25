from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str
    org_name: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    token: str
    token_type: str = "bearer"
    user: dict[str, Any]
    org: dict[str, Any]


class ProjectIn(BaseModel):
    name: str
    slug: str | None = None
    task_type: str = "chat_sft"
    default_backend: str = "openai"
    default_base_model: str = "gpt-4.1-mini"
    quality_gate: dict[str, Any] | None = None


class DatasetIn(BaseModel):
    name: str
    description: str | None = None
    project_id: UUID


class UploadInitIn(BaseModel):
    dataset_id: UUID
    filename: str
    content_type: str = "application/octet-stream"
    format: str | None = None
    prepare: dict[str, Any] | None = None


class UploadCompleteIn(BaseModel):
    dataset_id: UUID
    key: str
    filename: str
    format: str | None = None
    prepare: dict[str, Any] | None = None
    idempotency_key: str | None = None


class CredentialIn(BaseModel):
    provider: str
    secret: str


class RecipeIn(BaseModel):
    project_id: UUID
    name: str
    yaml_source: str


class PipelineIn(BaseModel):
    project_id: UUID
    yaml_source: str | None = None
    recipe: dict[str, Any] | None = None
    dataset_version_id: UUID | None = None
    git_sha: str | None = None
    idempotency_key: str | None = None


class TrainIn(BaseModel):
    project_id: UUID
    dataset_version_id: UUID
    backend: str | None = None
    recipe: dict[str, Any] | None = None
    yaml_source: str | None = None
    git_sha: str | None = None
    idempotency_key: str | None = None


class EvalIn(BaseModel):
    run_id: UUID
    suite_key: str | None = None
    suite_inline: list[dict[str, Any]] | None = None
    metrics: list[str] = Field(default_factory=lambda: ["exact_match"])
    gate: dict[str, Any] | None = None
    judge_model: str | None = None
    idempotency_key: str | None = None


class DeployIn(BaseModel):
    run_id: UUID
    name: str = "prod"
    override_gate: bool = False
    eval_report_id: UUID | None = None
    idempotency_key: str | None = None


class ChatIn(BaseModel):
    model: str | None = None
    deployment_id: UUID | None = None
    run_id: UUID | None = None
    messages: list[dict[str, Any]]
    temperature: float = 0.2
    stream: bool = False


class ApiKeyIn(BaseModel):
    name: str = "cli"


class HeartbeatIn(BaseModel):
    metrics: dict[str, Any] | None = None
    message: str | None = None
    succeeded: bool | None = None
    failed: bool | None = None
    error: str | None = None
    adapter_uri: str | None = None


def orm_to_dict(obj: Any, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, UUID):
            val = str(val)
        elif isinstance(val, datetime):
            val = val.isoformat()
        data[col.name] = val
    if extra:
        data.update(extra)
    # never leak secrets
    data.pop("password_hash", None)
    data.pop("encrypted_secret", None)
    data.pop("key_hash", None)
    data.pop("token_hash", None)
    return data
