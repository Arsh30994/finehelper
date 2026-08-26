"""Unified Trust Score attestation — local ledger (+ optional EVM)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finehelper_api.blockchain import hasher, local_chain
from finehelper_api.blockchain.ethereum import try_ethereum_attest
from finehelper_core.models import TrustScore, TrustSignalBatch
from finehelper_core.settings import Settings


def build_attestation_hashes(
    row: TrustScore,
    batch: TrustSignalBatch | None,
) -> dict[str, str]:
    batch_dict = None
    if batch:
        batch_dict = {
            "transactions": batch.transactions,
            "bills": batch.bills,
            "recharges": batch.recharges,
        }
    signals_root = hasher.signals_merkle_root(batch_dict)
    uid_hash = hasher.user_id_hash(row.user_id)
    score_hash = hasher.score_payload_hash(
        score_id=row.id,
        user_id=row.user_id,
        score=row.score,
        factors=row.factors,
        eligibility_min=row.eligibility_min,
        eligibility_max=row.eligibility_max,
        model_version=row.model_version,
        signals_root=signals_root,
    )
    return {
        "user_id_hash": uid_hash,
        "score_hash": score_hash,
        "signals_root": signals_root,
    }


def attest_score(
    settings: Settings,
    row: TrustScore,
    batch: TrustSignalBatch | None,
) -> dict[str, Any]:
    """
    Anchor score fingerprint.
    Always writes local hash-linked ledger; also tries EVM if configured.
    """
    hashes = build_attestation_hashes(row, batch)
    local = local_chain.append_attestation(
        user_id_hash=hashes["user_id_hash"],
        score_hash=hashes["score_hash"],
        signals_root=hashes["signals_root"],
        model_version=row.model_version,
        score_id=row.id,
    )

    result: dict[str, Any] = {
        **hashes,
        "network": local["network"],
        "tx_hash": local["tx_hash"],
        "block_number": local["block_number"],
        "explorer_url": local["explorer_url"],
        "mode": local["mode"],
        "local_tx_hash": local["tx_hash"],
        "score_id": row.id,
    }

    if settings.chain_rpc_url and settings.chain_private_key and settings.chain_contract_address:
        evm = try_ethereum_attest(
            rpc_url=settings.chain_rpc_url,
            private_key=settings.chain_private_key,
            contract_address=settings.chain_contract_address,
            chain_id=settings.chain_id,
            explorer_base=settings.chain_explorer_url,
            network_name=settings.chain_network or "polygon",
            user_id_hash=hashes["user_id_hash"],
            score_hash=hashes["score_hash"],
            signals_root=hashes["signals_root"],
            model_version=row.model_version,
        )
        if evm:
            result.update(
                {
                    "network": evm["network"],
                    "tx_hash": evm["tx_hash"],
                    "block_number": evm["block_number"],
                    "explorer_url": evm["explorer_url"],
                    "mode": "evm+local",
                    "issuer": evm.get("issuer"),
                }
            )

    return result


def apply_attestation_to_score(row: TrustScore, attestation: dict[str, Any]) -> TrustScore:
    row.score_hash = attestation.get("score_hash")
    row.signals_root = attestation.get("signals_root")
    row.user_id_hash = attestation.get("user_id_hash")
    row.chain_network = attestation.get("network")
    row.chain_tx_hash = attestation.get("tx_hash")
    row.chain_block = attestation.get("block_number")
    row.chain_explorer_url = attestation.get("explorer_url")
    row.chain_mode = attestation.get("mode")
    row.local_tx_hash = attestation.get("local_tx_hash") or (
        attestation.get("tx_hash") if attestation.get("mode") == "local_ledger" else None
    )
    return row


def verify_score_attestation(
    settings: Settings,
    row: TrustScore,
    batch: TrustSignalBatch | None,
) -> dict[str, Any]:
    hashes = build_attestation_hashes(row, batch)
    match_score = (row.score_hash or "").lower() == hashes["score_hash"].lower()
    match_root = (row.signals_root or "").lower() == hashes["signals_root"].lower()
    chain_ok = local_chain.verify_chain()

    lookup_hash = row.local_tx_hash or row.chain_tx_hash
    tx_block = local_chain.find_by_tx(lookup_hash) if lookup_hash else None
    if not tx_block:
        ledger = Path(".data/chain/trustmesh_ledger.jsonl")
        if ledger.exists():
            for ln in ledger.read_text(encoding="utf-8").splitlines():
                if not ln.strip():
                    continue
                b = json.loads(ln)
                if str(b.get("score_hash", "")).lower() == hashes["score_hash"].lower():
                    tx_block = b
                    break

    return {
        "ok": bool(match_score and match_root and chain_ok.get("ok") and row.chain_tx_hash),
        "hash_match": match_score and match_root,
        "score_hash": hashes["score_hash"],
        "stored_score_hash": row.score_hash,
        "signals_root": hashes["signals_root"],
        "stored_signals_root": row.signals_root,
        "chain_tx_hash": row.chain_tx_hash,
        "local_tx_hash": row.local_tx_hash,
        "network": row.chain_network or "local",
        "explorer_url": row.chain_explorer_url,
        "local_ledger": chain_ok,
        "found_in_ledger": bool(tx_block),
        "demo": True,
        "note": "Fingerprint only — not CIBIL, no raw UPI on-chain.",
        "chain_configured": bool(settings.chain_rpc_url and settings.chain_contract_address),
    }
