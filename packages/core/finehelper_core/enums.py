from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"


class TaskType(StrEnum):
    chat_sft = "chat_sft"
    completion = "completion"
    classification = "classification"


class JobType(StrEnum):
    ingest = "ingest"
    prepare = "prepare"
    train = "train"
    eval = "eval"
    export = "export"
    deploy = "deploy"


class JobStatus(StrEnum):
    queued = "queued"
    running = "running"
    uploading = "uploading"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class TrainingBackendName(StrEnum):
    openai = "openai"
    google = "google"
    together = "together"
    fireworks = "fireworks"
    hf_autotrain = "hf_autotrain"
    lora_modal = "lora_modal"
    lora_local = "lora_local"
    dry_run = "dry_run"


class DatasetFormat(StrEnum):
    openai_chat = "openai-chat"
    canonical = "canonical"
    sharegpt = "sharegpt"
    alpaca = "alpaca"
    csv = "csv"
    json = "json"
    jsonl = "jsonl"
    parquet = "parquet"


class EventKind(StrEnum):
    queued = "queued"
    log = "log"
    metric = "metric"
    artifact_ready = "artifact_ready"
    failed = "failed"
    status = "status"


class ArtifactKind(StrEnum):
    adapter = "adapter"
    merged_weights = "merged_weights"
    gguf = "gguf"
    tokenizer = "tokenizer"
    train_log = "train_log"
    dataset = "dataset"
    error_report = "error_report"
    eval_traces = "eval_traces"
    provider_model = "provider_model"
