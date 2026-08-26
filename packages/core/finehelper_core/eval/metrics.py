from __future__ import annotations

import hashlib
import json
import re
from typing import Any


def suite_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_suite(raw: bytes) -> list[dict[str, Any]]:
    text = raw.decode("utf-8")
    items = []
    if text.strip().startswith("["):
        data = json.loads(text)
        items = data if isinstance(data, list) else []
    else:
        for line in text.splitlines():
            if line.strip():
                items.append(json.loads(line))
    out = []
    for i, item in enumerate(items):
        expected = item.get("expected") if "expected" in item else item.get("output")
        messages = item.get("messages")
        if not messages:
            user = item.get("input") or item.get("prompt") or item.get("user")
            messages = [{"role": "user", "content": str(user)}] if user else []
        out.append({"id": item.get("id") or str(i), "messages": messages, "expected": expected, "raw": item})
    return out


def exact_match(pred: str, expected: Any) -> float:
    if expected is None:
        return 0.0
    return 1.0 if pred.strip() == str(expected).strip() else 0.0


def contains_metric(pred: str, expected: Any) -> float:
    if expected is None:
        return 0.0
    return 1.0 if str(expected).strip().lower() in pred.lower() else 0.0


def json_valid(pred: str, expected: Any = None) -> float:
    del expected
    try:
        json.loads(pred)
        return 1.0
    except Exception:
        return 0.0


METRIC_FNS = {
    "exact_match": exact_match,
    "contains": contains_metric,
    "json_valid": json_valid,
}


async def llm_judge(pred: str, expected: Any, api_key: str | None, model: str) -> float:
    if not api_key:
        return 0.0
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    prompt = (
        "Score the candidate answer vs the expected answer from 0 to 1. "
        "Return JSON {\"score\": number, \"reason\": string}.\n"
        f"EXPECTED:\n{expected}\n\nCANDIDATE:\n{pred}"
    )
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    text = resp.choices[0].message.content or "0"
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return 0.0
    try:
        return float(json.loads(match.group(0)).get("score", 0))
    except Exception:
        return 0.0


def gate_passed(metrics: dict[str, float], gate: dict[str, Any] | None) -> bool:
    if not gate:
        return True
    metric = gate.get("metric") or "exact_match"
    minimum = float(gate.get("min", 0))
    return float(metrics.get(metric, 0)) >= minimum
