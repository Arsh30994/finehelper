from __future__ import annotations

import asyncio
from typing import Any

from openai import AsyncOpenAI

from finehelper_core.backends.base import ArtifactRef, BackendStatus, ExternalRef, TrainingBackend, ValidationResult
from finehelper_core.dataset.prepare import canonical_loads, openai_jsonl
from finehelper_core.recipe import RecipeDocument


class OpenAITrainingBackend:
    name = "openai"

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    def validate(self, recipe: RecipeDocument, dataset_stats: dict[str, Any] | None) -> ValidationResult:
        errors = []
        if not recipe.train.base_model:
            errors.append("base_model is required")
        if dataset_stats and dataset_stats.get("row_count", 0) < 10:
            errors.append("OpenAI fine-tunes typically need at least 10 examples")
        return ValidationResult(ok=not errors, errors=errors)

    async def submit(
        self, job_id: str, recipe: RecipeDocument, dataset_bytes: bytes, dataset_digest: str, dataset_uri: str | None = None
    ) -> ExternalRef:
        rows = canonical_loads(dataset_bytes)
        payload = openai_jsonl(rows)
        uploaded = await self.client.files.create(
            file=(f"{job_id}-{dataset_digest[:8]}.jsonl", payload, "application/jsonl"),
            purpose="fine-tune",
        )
        hyper = recipe.train.hyperparams or {}
        body: dict[str, Any] = {
            "model": recipe.train.base_model,
            "training_file": uploaded.id,
        }
        if "n_epochs" in hyper:
            body["hyperparameters"] = {"n_epochs": hyper["n_epochs"]}
        elif "hyperparameters" in hyper:
            body["hyperparameters"] = hyper["hyperparameters"]
        ft = await self.client.fine_tuning.jobs.create(**body)
        return ExternalRef(backend=self.name, ref=ft.id, extra={"file_id": uploaded.id})

    async def poll(self, ref: ExternalRef) -> BackendStatus:
        ft = await self.client.fine_tuning.jobs.retrieve(ref.ref)
        status = ft.status or "queued"
        mapped = {
            "validating_files": "running",
            "queued": "queued",
            "running": "running",
            "succeeded": "succeeded",
            "failed": "failed",
            "cancelled": "cancelled",
        }.get(status, "running")
        metrics: dict[str, Any] = {}
        try:
            events = await self.client.fine_tuning.jobs.list_events(ref.ref, limit=20)
            message = ""
            for ev in reversed(list(events.data or [])):
                message = getattr(ev, "message", "") or message
                data = getattr(ev, "data", None)
                if isinstance(data, dict):
                    metrics.update({k: v for k, v in data.items() if isinstance(v, (int, float))})
        except Exception:
            message = status
        error = getattr(ft, "error", None)
        if error:
            message = getattr(error, "message", None) or str(error)
        return BackendStatus(
            state=mapped,
            metrics=metrics,
            message=message or status,
            provider_model_id=getattr(ft, "fine_tuned_model", None),
        )

    async def cancel(self, ref: ExternalRef) -> None:
        await self.client.fine_tuning.jobs.cancel(ref.ref)

    async def collect(self, ref: ExternalRef) -> list[ArtifactRef]:
        status = await self.poll(ref)
        if not status.provider_model_id:
            return []
        return [
            ArtifactRef(
                kind="provider_model",
                uri=f"openai://{status.provider_model_id}",
                extra={"provider_model_id": status.provider_model_id},
            )
        ]


class DryRunTrainingBackend:
    """Local demo backend: no GPU, no provider. Emits synthetic metrics then succeeds."""

    name = "dry_run"

    def validate(self, recipe: RecipeDocument, dataset_stats: dict[str, Any] | None) -> ValidationResult:
        return ValidationResult(ok=True)

    async def submit(
        self, job_id: str, recipe: RecipeDocument, dataset_bytes: bytes, dataset_digest: str, dataset_uri: str | None = None
    ) -> ExternalRef:
        del recipe, dataset_bytes
        return ExternalRef(backend=self.name, ref=f"dry_{job_id}", extra={"digest": dataset_digest, "ticks": 0})

    async def poll(self, ref: ExternalRef) -> BackendStatus:
        ticks = int(ref.extra.get("ticks", 0)) + 1
        ref.extra["ticks"] = ticks
        await asyncio.sleep(0.05)
        if ticks < 4:
            return BackendStatus(state="running", metrics={"step": ticks, "train_loss": round(1.4 / ticks, 4)})
        return BackendStatus(
            state="succeeded",
            metrics={"step": ticks, "train_loss": 0.21, "val_loss": 0.28},
            message="dry run complete",
            provider_model_id=f"dry-run://{ref.ref}",
        )

    async def cancel(self, ref: ExternalRef) -> None:
        ref.extra["cancelled"] = True

    async def collect(self, ref: ExternalRef) -> list[ArtifactRef]:
        return [
            ArtifactRef(
                kind="provider_model",
                uri=f"dry-run://{ref.ref}",
                extra={"provider_model_id": f"dry-run://{ref.ref}"},
            )
        ]


class ModalLoraBackend:
    name = "lora_modal"

    def __init__(self, modal_app: str = "finehelper-gpu"):
        self.modal_app = modal_app

    def validate(self, recipe: RecipeDocument, dataset_stats: dict[str, Any] | None) -> ValidationResult:
        errors = []
        if not recipe.train.base_model:
            errors.append("base_model is required")
        return ValidationResult(ok=not errors, errors=errors)

    async def submit(
        self, job_id: str, recipe: RecipeDocument, dataset_bytes: bytes, dataset_digest: str, dataset_uri: str | None = None
    ) -> ExternalRef:
        try:
            import modal
        except ImportError as exc:
            raise RuntimeError("modal is not installed on this worker") from exc
        fn = modal.Function.from_name(self.modal_app, "train_qlora")
        payload = {
            "job_id": job_id,
            "base_model": recipe.train.base_model,
            "method": recipe.train.method or "qlora",
            "lora": (recipe.train.lora.model_dump() if recipe.train.lora else {"r": 16, "alpha": 32}),
            "hyperparams": recipe.train.hyperparams,
            "dataset_digest": dataset_digest,
            "dataset_len": len(dataset_bytes),
            "dataset_uri": dataset_uri,
        }
        call = fn.spawn(payload)
        return ExternalRef(backend=self.name, ref=call.object_id, extra={"call_id": call.object_id})

    async def poll(self, ref: ExternalRef) -> BackendStatus:
        try:
            import modal
        except ImportError:
            return BackendStatus(state="failed", message="modal SDK missing")
        fn_call = modal.FunctionCall.from_id(ref.ref)
        try:
            result = fn_call.get(timeout=0)
            return BackendStatus(
                state="succeeded",
                metrics=result.get("metrics", {}),
                message="qlora finished",
                provider_model_id=result.get("adapter_uri"),
            )
        except TimeoutError:
            return BackendStatus(state="running", message="gpu job running")
        except Exception as exc:
            return BackendStatus(state="failed", message=str(exc))

    async def cancel(self, ref: ExternalRef) -> None:
        return None

    async def collect(self, ref: ExternalRef) -> list[ArtifactRef]:
        status = await self.poll(ref)
        if status.state != "succeeded" or not status.provider_model_id:
            return []
        return [ArtifactRef(kind="adapter", uri=status.provider_model_id)]


class LocalLoraBackend:
    """CLI reports progress via heartbeats; this backend just records the local run id."""

    name = "lora_local"

    def validate(self, recipe: RecipeDocument, dataset_stats: dict[str, Any] | None) -> ValidationResult:
        return ValidationResult(ok=True)

    async def submit(
        self, job_id: str, recipe: RecipeDocument, dataset_bytes: bytes, dataset_digest: str, dataset_uri: str | None = None
    ) -> ExternalRef:
        return ExternalRef(
            backend=self.name,
            ref=f"local_{job_id}",
            extra={"waiting_for_cli": True, "digest": dataset_digest, "bytes": len(dataset_bytes)},
        )

    async def poll(self, ref: ExternalRef) -> BackendStatus:
        if ref.extra.get("failed"):
            return BackendStatus(state="failed", message=ref.extra.get("error", "local runner failed"))
        if ref.extra.get("succeeded"):
            return BackendStatus(
                state="succeeded",
                metrics=ref.extra.get("metrics") or {},
                provider_model_id=ref.extra.get("adapter_uri"),
                message="local runner finished",
            )
        return BackendStatus(state="running", message="waiting for local CLI runner heartbeat")

    async def cancel(self, ref: ExternalRef) -> None:
        ref.extra["cancelled"] = True

    async def collect(self, ref: ExternalRef) -> list[ArtifactRef]:
        uri = ref.extra.get("adapter_uri")
        if not uri:
            return []
        return [ArtifactRef(kind="adapter", uri=uri)]
