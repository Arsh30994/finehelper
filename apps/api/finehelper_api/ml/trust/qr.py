"""Parse UPI-style / demo QR payloads into assumed trust signals."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


def parse_qr_payload(raw: str) -> dict[str, Any]:
    """
    Accepts:
    - upi://pay?pa=...&pn=...&am=...
    - https://upi.link/... or any query with pa=
    - trustmesh://merchant?name=...&upi=...&category=...
    - plain text "merchant@upi"
    """
    text = (raw or "").strip()
    if not text:
        raise ValueError("empty QR payload")
    if len(text) > 2048:
        raise ValueError("QR payload too long")

    lower = text.lower()
    parsed: dict[str, Any] = {
        "raw": text[:500],
        "kind": "unknown",
        "upi": None,
        "name": "Unknown merchant",
        "amount": None,
        "category": "commerce",
        "assumed": True,
        "settlement": False,
    }

    if lower.startswith("upi://") or "pa=" in lower or lower.startswith("http"):
        # Normalize upi:// to parseable URL
        url = text if "://" in text else f"upi://pay?{text}"
        if lower.startswith("upi://") and "://" in text:
            # urlparse handles upi://pay?...
            parts = urlparse(text)
            qs = parse_qs(parts.query)
        else:
            parts = urlparse(url)
            qs = parse_qs(parts.query)
            if not qs and "?" in text:
                qs = parse_qs(text.split("?", 1)[1])

        pa = (qs.get("pa") or qs.get("PA") or [None])[0]
        pn = (qs.get("pn") or qs.get("PN") or [None])[0]
        am = (qs.get("am") or qs.get("AM") or [None])[0]
        tn = (qs.get("tn") or qs.get("TN") or [None])[0]
        parsed["kind"] = "upi"
        parsed["upi"] = unquote(pa).lower() if pa else None
        parsed["name"] = unquote(pn) if pn else (parsed["upi"] or "UPI merchant")
        if am:
            try:
                parsed["amount"] = float(am)
            except ValueError:
                parsed["amount"] = None
        if tn:
            parsed["note"] = unquote(tn)[:80]
        parsed["category"] = _guess_category(parsed["name"])
        return parsed

    if lower.startswith("trustmesh://") or lower.startswith("tm://"):
        parts = urlparse(text.replace("tm://", "trustmesh://", 1))
        qs = parse_qs(parts.query)
        parsed["kind"] = "trustmesh"
        parsed["name"] = unquote((qs.get("name") or ["Demo Merchant"])[0])[:80]
        parsed["upi"] = unquote((qs.get("upi") or ["demo@oksbi"])[0]).lower()
        parsed["category"] = unquote((qs.get("category") or ["commerce"])[0])[:40]
        am = (qs.get("amount") or [None])[0]
        if am:
            try:
                parsed["amount"] = float(am)
            except ValueError:
                pass
        return parsed

    if "@" in text and " " not in text and len(text) < 80:
        parsed["kind"] = "upi_id"
        parsed["upi"] = text.lower()
        parsed["name"] = text.split("@", 1)[0].replace(".", " ").title()
        return parsed

    parsed["name"] = text[:60]
    parsed["kind"] = "text"
    return parsed


def _guess_category(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ("blinkit", "bigbasket", "grocery", "kirana")):
        return "groceries"
    if any(k in n for k in ("swiggy", "zomato", "food")):
        return "food"
    if any(k in n for k in ("jio", "airtel", "recharge", "vi ")):
        return "telecom"
    if any(k in n for k in ("irctc", "confirm", "ticket", "metro")):
        return "travel"
    if any(k in n for k in ("bescom", "power", "fiber", "act")):
        return "utilities"
    return "commerce"


def scan_to_signal(parsed: dict[str, Any], *, amount_override: float | None = None) -> dict[str, Any]:
    amount = amount_override if amount_override is not None else parsed.get("amount")
    if amount is None:
        amount = 199.0
    now = datetime.now(timezone.utc).isoformat()
    return {
        "transaction": {
            "at": now,
            "amount": round(float(amount), 2),
            "direction": "out",
            "counterparty": parsed.get("name") or "Scanned merchant",
            "upi": parsed.get("upi") or "scan@demo",
            "note": "qr_scan",
            "assumed": True,
            "source": "qr_scanner",
        },
        "merchant": {
            "name": parsed.get("name") or "Scanned merchant",
            "category": parsed.get("category") or "commerce",
            "upi": parsed.get("upi"),
            "assumed": True,
            "source": "qr_scanner",
        },
        "parsed": parsed,
    }
