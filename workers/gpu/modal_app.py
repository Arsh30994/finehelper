"""Modal GPU workers: QLoRA train, GGUF export, optional vLLM serve.

Deploy:
  modal deploy workers/gpu/modal_app.py

The control plane calls Function.from_name("finehelper-gpu", "train_qlora").
Secrets expected in the Modal environment: HF_TOKEN, S3_* (R2), MASTER_KEY.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import modal

app = modal.App("finehelper-gpu")

train_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch",
        "transformers>=4.44",
        "datasets",
        "peft",
        "trl",
        "bitsandbytes",
        "accelerate",
        "boto3",
        "httpx",
        extra_index_url="https://download.pytorch.org/whl/cu121",
    )
)


def _s3():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("S3_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("S3_REGION", "auto"),
        config=Config(signature_version="s3v4"),
    )


@app.function(image=train_image, gpu="A100", timeout=4 * 60 * 60, memory=32768)
def train_qlora(payload: dict[str, Any]) -> dict[str, Any]:
    """QLoRA SFT with TRL + PEFT. Dataset bytes are fetched from R2 by digest/job id if present.

    For a first Modal deploy this function is real training code; the control plane
    currently sends metadata. Wire dataset download via payload['dataset_uri'] when R2 is enabled.
    """
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
    base = payload.get("base_model") or "meta-llama/Llama-3.1-8B-Instruct"
    lora = payload.get("lora") or {"r": 16, "alpha": 32, "dropout": 0.05}
    hyper = payload.get("hyperparams") or {}
    out_dir = Path(tempfile.mkdtemp()) / "adapter"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Lightweight path: if no dataset_uri, persist a config-only adapter marker so the
    # control plane can still record an artifact URI during bring-up.
    dataset_uri = payload.get("dataset_uri")
    if not dataset_uri:
        marker = {
            "status": "skipped_no_dataset_uri",
            "base_model": base,
            "lora": lora,
            "hyperparams": hyper,
            "job_id": payload.get("job_id"),
        }
        (out_dir / "finehelper.json").write_text(json.dumps(marker, indent=2))
        return {
            "metrics": {"train_loss": None},
            "adapter_uri": f"modal://finehelper-gpu/{payload.get('job_id')}",
            "note": "Pass dataset_uri to run full QLoRA.",
        }

    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer
    import gzip
    import json as jsonlib
    import torch

    bucket_key = dataset_uri.split("r2://", 1)[-1]
    bucket, _, key = bucket_key.partition("/")
    raw = _s3().get_object(Bucket=bucket, Key=key)["Body"].read()
    try:
        text = gzip.decompress(raw).decode("utf-8")
    except OSError:
        text = raw.decode("utf-8")
    rows = [jsonlib.loads(line) for line in text.splitlines() if line.strip()]
    ds = Dataset.from_list(rows)

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    tokenizer = AutoTokenizer.from_pretrained(base, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        base,
        quantization_config=bnb,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    peft_cfg = LoraConfig(
        r=int(lora.get("r", 16)),
        lora_alpha=int(lora.get("alpha", 32)),
        lora_dropout=float(lora.get("dropout", 0.05)),
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=None if lora.get("target_modules") == "all-linear" else lora.get("target_modules"),
    )

    def formatting(example):
        return tokenizer.apply_chat_template(example["messages"], tokenize=False)

    args = SFTConfig(
        output_dir=str(out_dir),
        num_train_epochs=float(hyper.get("epochs") or hyper.get("n_epochs") or 1),
        per_device_train_batch_size=int(hyper.get("batch_size") or 2),
        learning_rate=float(hyper.get("lr") or 2e-4),
        logging_steps=5,
        save_strategy="no",
        bf16=True,
        max_seq_length=int(hyper.get("max_seq_len") or 2048),
        report_to=[],
    )
    trainer = SFTTrainer(
        model=model,
        args=args,
        train_dataset=ds,
        peft_config=peft_cfg,
        formatting_func=formatting,
    )
    result = trainer.train()
    trainer.model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)

    adapter_key = f"artifacts/{payload.get('job_id')}/adapter"
    # Upload all files under out_dir
    for path in out_dir.rglob("*"):
        if path.is_file():
            rel = path.relative_to(out_dir).as_posix()
            _s3().put_object(
                Bucket=os.environ["S3_BUCKET"],
                Key=f"{adapter_key}/{rel}",
                Body=path.read_bytes(),
            )
    metrics = result.metrics if hasattr(result, "metrics") else {}
    return {
        "metrics": {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))},
        "adapter_uri": f"r2://{os.environ['S3_BUCKET']}/{adapter_key}",
    }


@app.function(image=train_image, gpu="A100", timeout=2 * 60 * 60)
def export_gguf(payload: dict[str, Any]) -> dict[str, Any]:
    """Export merged weights to GGUF via llama.cpp convert if present on the image."""
    return {
        "status": "not_configured",
        "hint": "Add llama.cpp convert_hf_to_gguf.py to this image, then write the GGUF to R2.",
        "adapter_uri": payload.get("adapter_uri"),
    }


serve_image = (
    modal.Image.from_registry("vllm/vllm-openai:latest")
)


@app.function(image=serve_image, gpu="A100", timeout=24 * 60 * 60)
@modal.web_server(port=8000)
def vllm_endpoint():
    """OpenAI-compatible vLLM server. Configure MODEL env at spawn time."""
    model = os.environ.get("MODEL", "meta-llama/Llama-3.1-8B-Instruct")
    subprocess.Popen(
        [
            "python",
            "-m",
            "vllm.entrypoints.openai.api_server",
            "--model",
            model,
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ]
    )
