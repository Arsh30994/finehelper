from __future__ import annotations

from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class DatasetPrepareConfig(BaseModel):
    dedupe: bool = True
    max_seq_len: int | None = 4096
    split: dict[str, float] = Field(default_factory=lambda: {"train": 0.9, "val": 0.1})


class DatasetSpec(BaseModel):
    path: str | None = None
    dataset_id: str | None = None
    version_id: str | None = None
    format: str = "openai-chat"
    prepare: DatasetPrepareConfig = Field(default_factory=DatasetPrepareConfig)


class LoraConfig(BaseModel):
    r: int = 16
    alpha: int = 32
    dropout: float = 0.05
    target_modules: str | list[str] = "all-linear"


class HardwareSpec(BaseModel):
    gpu: str = "A100-40GB"
    count: int = 1


class TrainSpec(BaseModel):
    backend: str = "openai"
    base_model: str = "gpt-4.1-mini"
    method: str | None = None
    lora: LoraConfig | None = None
    hyperparams: dict[str, Any] = Field(default_factory=lambda: {"n_epochs": 3})
    hardware: HardwareSpec | None = None


class EvalGate(BaseModel):
    metric: str = "exact_match"
    min: float = 0.8


class EvalSpec(BaseModel):
    suite: str | None = None
    metrics: list[str] = Field(default_factory=lambda: ["exact_match"])
    gate: EvalGate | None = None
    judge_model: str | None = "gpt-4.1-mini"


class DeploySpec(BaseModel):
    name: str = "prod"
    when: Literal["gate_passed", "always"] = "gate_passed"


class RecipeDocument(BaseModel):
    project: str
    dataset: DatasetSpec = Field(default_factory=DatasetSpec)
    train: TrainSpec = Field(default_factory=TrainSpec)
    eval: EvalSpec | None = None
    deploy: DeploySpec | None = None

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.model_dump(mode="json"), sort_keys=False)


def parse_recipe(source: str | dict[str, Any]) -> RecipeDocument:
    if isinstance(source, str):
        data = yaml.safe_load(source) or {}
    else:
        data = source
    if not isinstance(data, dict):
        raise ValueError("Recipe must be a mapping")
    return RecipeDocument.model_validate(data)
