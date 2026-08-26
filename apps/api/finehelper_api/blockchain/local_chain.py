"""Append-only local demo ledger (hash-linked blocks). Always available offline."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from finehelper_api.blockchain.hasher import sha256_hex

_lock = threading.Lock()


def _default_path() -> Path:
    return Path(".data/chain/trustmesh_ledger.jsonl")


def _block_hash(block: dict[str, Any]) -> str:
    body = {k: v for k, v in block.items() if k != "hash"}
    return "0x" + sha256_hex(json.dumps(body, sort_keys=True, separators=(",", ":")))


def append_attestation(
    *,
    user_id_hash: str,
    score_hash: str,
    signals_root: str,
    model_version: str,
    score_id: str,
    path: Path | None = None,
) -> dict[str, Any]:
    ledger = path or _default_path()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        prev_hash = "0x" + ("0" * 64)
        index = 0
        if ledger.exists():
            lines = [ln for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if lines:
                last = json.loads(lines[-1])
                prev_hash = last.get("hash") or prev_hash
                index = int(last.get("index") or 0) + 1
        block: dict[str, Any] = {
            "index": index,
            "prev_hash": prev_hash,
            "network": "local",
            "attested_at": datetime.now(timezone.utc).isoformat(),
            "user_id_hash": user_id_hash,
            "score_hash": score_hash,
            "signals_root": signals_root,
            "model_version": model_version,
            "score_id": score_id,
        }
        block["hash"] = _block_hash(block)
        with ledger.open("a", encoding="utf-8") as f:
            f.write(json.dumps(block, separators=(",", ":")) + "\n")
        return {
            "network": "local",
            "tx_hash": block["hash"],
            "block_number": index,
            "explorer_url": None,
            "user_id_hash": user_id_hash,
            "score_hash": score_hash,
            "signals_root": signals_root,
            "model_version": model_version,
            "score_id": score_id,
            "attested_at": block["attested_at"],
            "mode": "local_ledger",
        }


def find_by_tx(tx_hash: str, path: Path | None = None) -> dict[str, Any] | None:
    ledger = path or _default_path()
    if not ledger.exists():
        return None
    want = tx_hash.lower()
    for ln in ledger.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        block = json.loads(ln)
        if str(block.get("hash", "")).lower() == want:
            return block
    return None


def verify_chain(path: Path | None = None) -> dict[str, Any]:
    """Walk the local ledger and confirm hash links."""
    ledger = path or _default_path()
    if not ledger.exists():
        return {"ok": True, "blocks": 0, "network": "local"}
    prev = "0x" + ("0" * 64)
    count = 0
    for ln in ledger.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        block = json.loads(ln)
        if block.get("prev_hash") != prev:
            return {"ok": False, "error": "broken prev_hash", "at": count, "network": "local"}
        expected = _block_hash(block)
        if block.get("hash") != expected:
            return {"ok": False, "error": "bad block hash", "at": count, "network": "local"}
        prev = block["hash"]
        count += 1
    return {"ok": True, "blocks": count, "network": "local", "tip": prev}
