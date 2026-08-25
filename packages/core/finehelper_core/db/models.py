from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    BigInteger,
    Boolean,
    Float,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator, Uuid


class JSONType(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class UUIDType(TypeDecorator):
    impl = Uuid
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(Uuid(as_uuid=True))


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Org(Base, TimestampMixin):
    __tablename__ = "orgs"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    members: Mapped[list[Membership]] = relationship(back_populates="org")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(200))


class Membership(Base, TimestampMixin):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("org_id", "user_id", name="uq_membership_org_user"),)

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("orgs.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="owner")

    org: Mapped[Org] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class Invite(Base, TimestampMixin):
    __tablename__ = "invites"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("orgs.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    role: Mapped[str] = mapped_column(String(20), default="member")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    invited_by: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id"))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Session(Base, TimestampMixin):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ApiKey(Base, TimestampMixin):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("orgs.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    prefix: Mapped[str] = mapped_column(String(24), index=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("org_id", "slug", name="uq_project_org_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("orgs.id"), index=True)
    slug: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(200))
    task_type: Mapped[str] = mapped_column(String(40), default="chat_sft")
    default_backend: Mapped[str] = mapped_column(String(40), default="openai")
    default_base_model: Mapped[str] = mapped_column(String(200), default="gpt-4.1-mini")
    quality_gate: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Credential(Base, TimestampMixin):
    __tablename__ = "credentials"
    __table_args__ = (UniqueConstraint("org_id", "provider", name="uq_credential_org_provider"),)

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("orgs.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    encrypted_secret: Mapped[str] = mapped_column(Text)
    last4: Mapped[str] = mapped_column(String(8))
    created_by: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("users.id"))


class Dataset(Base, TimestampMixin):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("orgs.id"), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DatasetVersion(Base, TimestampMixin):
    __tablename__ = "dataset_versions"
    __table_args__ = (Index("ix_dataset_version_digest", "org_id", "content_digest"),)

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("orgs.id"), index=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("datasets.id"), index=True)
    content_digest: Mapped[str] = mapped_column(String(64), index=True)
    uri: Mapped[str] = mapped_column(String(500))
    row_count: Mapped[int] = mapped_column(default=0)
    schema_id: Mapped[str] = mapped_column(String(40), default="chat_canonical_v1")
    stats: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    split_map: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    prepare_config: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_report_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Recipe(Base, TimestampMixin):
    __tablename__ = "recipes"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("orgs.id"), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    yaml_source: Mapped[str] = mapped_column(Text)
    parsed: Mapped[dict[str, Any]] = mapped_column(JSONType)


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("org_id", "idempotency_key", name="uq_job_idempotency"),
        Index("ix_jobs_queue", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("orgs.id"), index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("projects.id"), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    parent_job_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType, ForeignKey("jobs.id"), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True)


class JobEvent(Base):
    __tablename__ = "job_events"
    __table_args__ = (Index("ix_job_events_job_created", "job_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("orgs.id"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("jobs.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Run(Base, TimestampMixin):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("orgs.id"), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("projects.id"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("jobs.id"), unique=True)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("dataset_versions.id"))
    backend: Mapped[str] = mapped_column(String(40))
    base_model: Mapped[str] = mapped_column(String(200))
    hyperparams: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    provider_model_id: Mapped[str | None] = mapped_column(String(300), nullable=True)
    adapter_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    git_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Artifact(Base, TimestampMixin):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("orgs.id"), index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType, ForeignKey("runs.id"), nullable=True, index=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType, ForeignKey("jobs.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(40))
    uri: Mapped[str] = mapped_column(String(500))
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")


class EvalReport(Base, TimestampMixin):
    __tablename__ = "eval_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("orgs.id"), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("projects.id"), index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("runs.id"), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("jobs.id"))
    suite_digest: Mapped[str] = mapped_column(String(64))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONType)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    gate: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    traces_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    judge_model: Mapped[str | None] = mapped_column(String(200), nullable=True)


class Deployment(Base, TimestampMixin):
    __tablename__ = "deployments"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("orgs.id"), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("projects.id"), index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("runs.id"))
    eval_report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("eval_reports.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200))
    backend: Mapped[str] = mapped_column(String(40))
    target: Mapped[dict[str, Any]] = mapped_column(JSONType)
    override_gate: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=_uuid)
    org_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("orgs.id"), index=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUIDType, ForeignKey("jobs.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(40))
    quantity: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(40), default="token")
    amount_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
