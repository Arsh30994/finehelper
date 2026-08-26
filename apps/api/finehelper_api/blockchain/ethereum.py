"""Optional EVM attestation via web3 (Polygon / any RPC). Falls back if unset/unavailable."""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

# Minimal ABI for TrustAttestation.attest
ATTEST_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "userIdHash", "type": "bytes32"},
            {"internalType": "bytes32", "name": "scoreHash", "type": "bytes32"},
            {"internalType": "bytes32", "name": "signalsRoot", "type": "bytes32"},
            {"internalType": "string", "name": "modelVersion", "type": "string"},
        ],
        "name": "attest",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]


def _to_bytes32(hex_str: str) -> bytes:
    h = hex_str[2:] if hex_str.startswith("0x") else hex_str
    return bytes.fromhex(h)


def try_ethereum_attest(
    *,
    rpc_url: str,
    private_key: str,
    contract_address: str,
    chain_id: int,
    explorer_base: str,
    network_name: str,
    user_id_hash: str,
    score_hash: str,
    signals_root: str,
    model_version: str,
) -> dict[str, Any] | None:
    try:
        from web3 import Web3
    except ImportError:
        log.warning("web3 not installed — skipping EVM attest")
        return None
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 25}))
        if not w3.is_connected():
            log.warning("EVM RPC not connected: %s", rpc_url)
            return None
        account = w3.eth.account.from_key(private_key)
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=ATTEST_ABI,
        )
        nonce = w3.eth.get_transaction_count(account.address)
        tx = contract.functions.attest(
            _to_bytes32(user_id_hash),
            _to_bytes32(score_hash),
            _to_bytes32(signals_root),
            model_version,
        ).build_transaction(
            {
                "from": account.address,
                "nonce": nonce,
                "chainId": chain_id,
                "gas": 200_000,
                "maxFeePerGas": w3.to_wei("40", "gwei"),
                "maxPriorityFeePerGas": w3.to_wei("2", "gwei"),
            }
        )
        signed = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=90)
        hx = tx_hash.hex() if hasattr(tx_hash, "hex") else w3.to_hex(tx_hash)
        if not hx.startswith("0x"):
            hx = "0x" + hx
        explorer = explorer_base.rstrip("/") + "/tx/" + hx
        return {
            "network": network_name,
            "tx_hash": hx,
            "block_number": int(receipt.blockNumber),
            "explorer_url": explorer,
            "user_id_hash": user_id_hash,
            "score_hash": score_hash,
            "signals_root": signals_root,
            "model_version": model_version,
            "mode": "evm",
            "issuer": account.address,
        }
    except Exception as exc:
        log.warning("EVM attest failed: %s", exc)
        return None
