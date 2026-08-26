from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from finehelper_core.recipe import RecipeDocument


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class ExternalRef:
    backend: str
    ref: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class BackendStatus:
    state: str  # queued | running | succeeded | failed | cancelled
    metrics: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    provider_model_id: str | None = None


@dataclass
class ArtifactRef:
    kind: str
    uri: str
    size_bytes: int = 0
    content_type: str = "application/octet-stream"
    extra: dict[str, Any] = field(default_factory=dict)


class TrainingBackend(Protocol):
    name: str

    def validate(self, recipe: RecipeDocument, dataset_stats: dict[str, Any] | None) -> ValidationResult: ...

    async def submit(
        self, job_id: str, recipe: RecipeDocument, dataset_bytes: bytes, dataset_digest: str, dataset_uri: str | None = None
    ) -> ExternalRef: ...

    async def poll(self, ref: ExternalRef) -> BackendStatus: ...

    async def cancel(self, ref: ExternalRef) -> None: ...

    async def collect(self, ref: ExternalRef) -> list[ArtifactRef]: ...
