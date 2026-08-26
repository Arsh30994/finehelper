"""Canonical hashing for Trust Score attestations (off-chain compute, on-chain anchor)."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def bytes32_hex(data: str | bytes) -> str:
    """Return 0x-prefixed 32-byte hex (sha256 digest)."""
    return "0x" + sha256_hex(data)


def user_id_hash(user_id: str) -> str:
    return bytes32_hex(f"trustmesh:user:{user_id}")


def score_payload_hash(
    *,
    score_id: str,
    user_id: str,
    score: int,
    factors: dict[str, float],
    eligibility_min: int,
    eligibility_max: int,
    model_version: str,
    signals_root: str,
) -> str:
    payload = {
        "score_id": score_id,
        "user_id_hash": user_id_hash(user_id),
        "score": int(score),
        "factors": {k: round(float(v), 4) for k, v in sorted((factors or {}).items())},
        "eligibility_min": int(eligibility_min),
        "eligibility_max": int(eligibility_max),
        "model_version": model_version,
        "signals_root": signals_root,
    }
    return bytes32_hex(_canon(payload))


def merkle_root(leaves: list[str]) -> str:
    """Simple binary Merkle root over hex/string leaves (sha256). Empty → zero hash."""
    if not leaves:
        return bytes32_hex("trustmesh:empty")
    layer = [sha256_hex(x) for x in leaves]
    while len(layer) > 1:
        nxt: list[str] = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else left
            nxt.append(sha256_hex(left + right))
        layer = nxt
    return "0x" + layer[0]


def signals_merkle_root(batch: dict[str, Any] | None) -> str:
    if not batch:
        return merkle_root([])
    leaves: list[str] = []
    for i, t in enumerate(batch.get("transactions") or []):
        leaves.append(_canon({"kind": "txn", "i": i, **{k: t.get(k) for k in ("at", "amount", "direction", "upi", "counterparty")}}))
    for i, b in enumerate(batch.get("bills") or []):
        leaves.append(_canon({"kind": "bill", "i": i, **{k: b.get(k) for k in ("at", "amount", "on_time", "provider", "name")}}))
    for i, r in enumerate(batch.get("recharges") or []):
        leaves.append(_canon({"kind": "recharge", "i": i, **{k: r.get(k) for k in ("at", "amount", "operator")}}))
    return merkle_root(leaves)
