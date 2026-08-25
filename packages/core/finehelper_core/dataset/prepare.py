from __future__ import annotations

import gzip
import hashlib
import json
import re
import uuid
from collections import Counter
from typing import Any, Iterable

from finehelper_core.enums import DatasetFormat

CANONICAL_ROLES = {"system", "user", "assistant"}
ERROR_RATE_FAIL = 0.2


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_row_id(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def canonical_dumps(rows: list[dict[str, Any]]) -> bytes:
    lines = [json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows]
    body = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
    return gzip.compress(body)


def canonical_loads(blob: bytes) -> list[dict[str, Any]]:
    try:
        raw = gzip.decompress(blob)
    except OSError:
        raw = blob
    rows = []
    for line in raw.decode("utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _as_messages_openai(obj: dict[str, Any]) -> list[dict[str, str]] | None:
    msgs = obj.get("messages")
    if not isinstance(msgs, list) or not msgs:
        return None
    out = []
    for m in msgs:
        if not isinstance(m, dict):
            return None
        role = str(m.get("role") or "").lower()
        content = m.get("content")
        if role not in CANONICAL_ROLES or content is None:
            return None
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        out.append({"role": role, "content": content})
    return out


def _as_messages_sharegpt(obj: dict[str, Any]) -> list[dict[str, str]] | None:
    conv = obj.get("conversations") or obj.get("conversation")
    if not isinstance(conv, list):
        return None
    mapping = {"human": "user", "user": "user", "gpt": "assistant", "assistant": "assistant", "system": "system"}
    out = []
    for turn in conv:
        if not isinstance(turn, dict):
            return None
        role = mapping.get(str(turn.get("from") or turn.get("role") or "").lower())
        value = turn.get("value") if "value" in turn else turn.get("content")
        if not role or value is None:
            return None
        out.append({"role": role, "content": str(value)})
    return out or None


def _as_messages_alpaca(obj: dict[str, Any]) -> list[dict[str, str]] | None:
    instruction = obj.get("instruction")
    output = obj.get("output") or obj.get("response")
    if not instruction or not output:
        return None
    inp = obj.get("input") or ""
    user = str(instruction) if not inp else f"{instruction}\n\n{inp}"
    msgs: list[dict[str, str]] = []
    if obj.get("system"):
        msgs.append({"role": "system", "content": str(obj["system"])})
    msgs.append({"role": "user", "content": user})
    msgs.append({"role": "assistant", "content": str(output)})
    return msgs


def detect_format(sample: Any, declared: DatasetFormat | None) -> DatasetFormat:
    if declared and declared not in {DatasetFormat.jsonl, DatasetFormat.json, DatasetFormat.csv}:
        return declared
    if isinstance(sample, dict):
        if _as_messages_openai(sample):
            return DatasetFormat.openai_chat
        if _as_messages_sharegpt(sample):
            return DatasetFormat.sharegpt
        if _as_messages_alpaca(sample):
            return DatasetFormat.alpaca
    return DatasetFormat.jsonl


def parse_bytes(raw: bytes, filename: str, declared: DatasetFormat | None) -> list[dict[str, Any]]:
    name = filename.lower()
    if name.endswith(".parquet") or declared == DatasetFormat.parquet:
        try:
            import io

            import pyarrow.parquet as pq
        except ImportError as exc:
            raise ValueError("Parquet ingest requires pyarrow (`pip install pyarrow`)") from exc
        table = pq.read_table(io.BytesIO(raw))
        return [row for row in table.to_pylist() if isinstance(row, dict)]
    text = raw.decode("utf-8-sig")
    if name.endswith(".csv") or declared == DatasetFormat.csv:
        import csv
        from io import StringIO

        reader = csv.DictReader(StringIO(text))
        return [dict(row) for row in reader]
    stripped = text.strip()
    if stripped.startswith("["):
        data = json.loads(stripped)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        raise ValueError("JSON root must be an array of objects")
    rows = []
    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at line {i}: {exc}") from exc
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def to_canonical_row(obj: dict[str, Any], fmt: DatasetFormat, source: str) -> dict[str, Any] | None:
    messages = None
    if fmt in {DatasetFormat.openai_chat, DatasetFormat.canonical, DatasetFormat.jsonl, DatasetFormat.json}:
        messages = _as_messages_openai(obj) or _as_messages_sharegpt(obj) or _as_messages_alpaca(obj)
    elif fmt == DatasetFormat.sharegpt:
        messages = _as_messages_sharegpt(obj)
    elif fmt == DatasetFormat.alpaca:
        messages = _as_messages_alpaca(obj)
    elif fmt == DatasetFormat.csv:
        messages = _as_messages_alpaca(obj) or _as_messages_openai(obj)
        if messages is None and obj.get("user") and obj.get("assistant"):
            messages = [
                {"role": "user", "content": str(obj["user"])},
                {"role": "assistant", "content": str(obj["assistant"])},
            ]
    if not messages:
        return None
    row = {"id": obj.get("id") or stable_row_id({"messages": messages}), "messages": messages, "meta": {"source": source}}
    if isinstance(obj.get("meta"), dict):
        row["meta"] = {**obj["meta"], "source": source}
    return row


def validate_chat_row(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    msgs = row.get("messages")
    if not isinstance(msgs, list) or len(msgs) < 2:
        return ["messages must contain at least two turns"]
    for m in msgs:
        role = m.get("role")
        content = m.get("content")
        if role not in CANONICAL_ROLES:
            errors.append(f"invalid role {role!r}")
        if not isinstance(content, str) or not content.strip():
            errors.append(f"empty content for role {role!r}")
    last = msgs[-1]
    if last.get("role") != "assistant" or not str(last.get("content") or "").strip():
        errors.append("final message must be a non-empty assistant turn")
    roles = [m.get("role") for m in msgs]
    if "user" not in roles:
        errors.append("missing user turn")
    return errors


def _minhash_signature(text: str, num_perm: int = 16) -> tuple[int, ...]:
    if not text:
        return (0,) * num_perm
    shingles = [text[i : i + 5] for i in range(0, max(1, len(text) - 4))]
    sig = []
    for seed in range(num_perm):
        acc = 2**64 - 1
        for shingle in shingles:
            digest = hashlib.blake2b(f"{seed}:{shingle}".encode(), digest_size=8).digest()
            acc = min(acc, int.from_bytes(digest, "big"))
        sig.append(acc)
    return tuple(sig)


def dedupe_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Exact SHA-256 plus MinHash banding for near-duplicate chat rows."""
    seen_exact: set[str] = set()
    seen_bands: set[tuple[int, ...]] = set()
    out = []
    dropped = 0
    for row in rows:
        blob = "\n".join(f"{m['role']}:{m['content']}" for m in row["messages"])
        exact = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        band = _minhash_signature(blob)[:4]
        if exact in seen_exact or band in seen_bands:
            dropped += 1
            continue
        seen_exact.add(exact)
        seen_bands.add(band)
        out.append(row)
    return out, dropped


def approx_token_len(text: str) -> int:
    return max(1, len(text.split()))


def length_filter(rows: list[dict[str, Any]], max_seq_len: int | None) -> tuple[list[dict[str, Any]], int]:
    if not max_seq_len:
        return rows, 0
    kept, dropped = [], 0
    for row in rows:
        n = sum(approx_token_len(m["content"]) for m in row["messages"])
        if n > max_seq_len:
            dropped += 1
            continue
        kept.append(row)
    return kept, dropped


def split_rows(rows: list[dict[str, Any]], train: float = 0.9, val: float = 0.1, test: float = 0.0) -> dict[str, list[str]]:
    total = train + val + test
    train, val, test = train / total, val / total, test / total
    splits = {"train": [], "val": [], "test": []}
    for row in rows:
        h = int(hashlib.sha256(str(row["id"]).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        if h < train:
            splits["train"].append(row["id"])
        elif h < train + val:
            splits["val"].append(row["id"])
        else:
            splits["test"].append(row["id"])
    if not splits["val"] and rows:
        splits["val"].append(rows[0]["id"])
        if rows[0]["id"] in splits["train"]:
            splits["train"].remove(rows[0]["id"])
    return splits


def compute_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lengths = []
    empty_target = 0
    role_counts: Counter[str] = Counter()
    for row in rows:
        msgs = row["messages"]
        lengths.append(sum(approx_token_len(m["content"]) for m in msgs))
        for m in msgs:
            role_counts[m["role"]] += 1
        if not str(msgs[-1].get("content") or "").strip():
            empty_target += 1
    lengths_sorted = sorted(lengths) or [0]
    def pct(p: float) -> int:
        idx = min(len(lengths_sorted) - 1, int(p * (len(lengths_sorted) - 1)))
        return lengths_sorted[idx]
    return {
        "row_count": len(rows),
        "approx_tokens_p50": pct(0.5),
        "approx_tokens_p95": pct(0.95),
        "approx_tokens_max": lengths_sorted[-1],
        "empty_target_rate": empty_target / max(len(rows), 1),
        "role_counts": dict(role_counts),
    }


def prepare_dataset(
    raw: bytes,
    filename: str,
    *,
    declared_format: DatasetFormat | None = None,
    source: str = "upload",
    dedupe: bool = True,
    max_seq_len: int | None = 4096,
    split: dict[str, float] | None = None,
    error_rate_fail: float = ERROR_RATE_FAIL,
) -> dict[str, Any]:
    parsed = parse_bytes(raw, filename, declared_format)
    if not parsed:
        raise ValueError("Dataset is empty")
    fmt = detect_format(parsed[0], declared_format)
    errors: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for i, obj in enumerate(parsed):
        row = to_canonical_row(obj, fmt, source)
        if row is None:
            errors.append({"index": i, "errors": ["unrecognized schema"]})
            continue
        row_errors = validate_chat_row(row)
        if row_errors:
            errors.append({"index": i, "id": row["id"], "errors": row_errors})
            continue
        rows.append(row)
    error_rate = len(errors) / max(len(parsed), 1)
    dropped_dedupe = 0
    dropped_len = 0
    if dedupe:
        rows, dropped_dedupe = dedupe_rows(rows)
    rows, dropped_len = length_filter(rows, max_seq_len)
    split = split or {"train": 0.9, "val": 0.1, "test": 0.0}
    split_map = split_rows(rows, split.get("train", 0.9), split.get("val", 0.1), split.get("test", 0.0))
    blob = canonical_dumps(rows)
    digest = sha256_bytes(blob)
    failed = error_rate > error_rate_fail or not rows
    return {
        "format_detected": fmt.value,
        "digest": digest,
        "blob": blob,
        "rows": rows,
        "row_count": len(rows),
        "stats": compute_stats(rows),
        "split_map": {k: {"count": len(v)} for k, v in split_map.items()},
        "split_ids": split_map,
        "errors": errors[:500],
        "error_count": len(errors),
        "error_rate": error_rate,
        "dropped_dedupe": dropped_dedupe,
        "dropped_length": dropped_len,
        "failed": failed,
        "prepare_config": {
            "dedupe": dedupe,
            "max_seq_len": max_seq_len,
            "split": split,
            "format": fmt.value,
        },
    }


SECRET_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|hf_[A-Za-z0-9]{8,}|Bearer\s+[A-Za-z0-9\-._]+|fh_live_[A-Za-z0-9_\-]+)")


def scrub_log(message: str) -> str:
    return SECRET_RE.sub("[redacted]", message)


def openai_jsonl(rows: Iterable[dict[str, Any]]) -> bytes:
    lines = []
    for row in rows:
        lines.append(json.dumps({"messages": row["messages"]}, ensure_ascii=False))
    return ("\n".join(lines) + "\n").encode("utf-8")


def new_id() -> str:
    return str(uuid.uuid4())
