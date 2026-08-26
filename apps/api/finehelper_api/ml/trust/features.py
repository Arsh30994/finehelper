"""Feature extraction from trust signal batches."""

from __future__ import annotations

import math
import statistics
from collections import Counter
from datetime import datetime
from typing import Any

from finehelper_api.ml.trust import FEATURE_NAMES


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def extract_features(batch: dict[str, Any]) -> dict[str, float]:
    txns = batch.get("transactions") or []
    bills = batch.get("bills") or []
    recharges = batch.get("recharges") or []
    peers = batch.get("peers") or []
    merchants = batch.get("merchants") or []
    months = max(1, int(batch.get("months") or 6))

    amounts = [float(t.get("amount") or 0) for t in txns]
    ins = [float(t["amount"]) for t in txns if t.get("direction") == "in"]
    outs = [float(t["amount"]) for t in txns if t.get("direction") == "out"]

    mean_amt = statistics.fmean(amounts) if amounts else 0.0
    std_amt = statistics.pstdev(amounts) if len(amounts) > 1 else 0.0
    cv = (std_amt / mean_amt) if mean_amt > 0 else 0.0

    in_sum = sum(ins) or 0.0
    out_sum = sum(outs) or 1.0
    on_time = [1.0 for b in bills if b.get("on_time")]
    bill_on_time = (sum(on_time) / len(bills)) if bills else 0.0

    # Recharge regularity: inverse of day-gap CV
    recharge_dates = sorted(d for d in (_parse_dt(r.get("at", "")) for r in recharges) if d)
    if len(recharge_dates) >= 3:
        gaps = [(recharge_dates[i] - recharge_dates[i - 1]).days for i in range(1, len(recharge_dates))]
        gmean = statistics.fmean(gaps) or 1
        regularity = max(0.0, 1.0 - (statistics.pstdev(gaps) / gmean))
    else:
        regularity = 0.2 if recharges else 0.0

    peer_recurrence = 0.0
    if peers:
        peer_recurrence = statistics.fmean([min(1.0, (p.get("txn_count") or 0) / 40) for p in peers])
    peer_tenure = statistics.fmean([float(p.get("months_known") or 0) for p in peers]) if peers else 0.0

    notes = Counter((t.get("note") or "") for t in txns)
    rental = 1.0 if notes.get("rent", 0) > 0 or any(p.get("name", "").lower().find("rent") >= 0 for p in peers) else 0.0
    # GST proxy: regular "goods" notes + vendor peers
    gst = min(1.0, notes.get("goods", 0) / max(10, len(txns) * 0.15)) if txns else 0.0

    # Income-like: recurring inbound similar amounts
    income_like = 0.0
    if len(ins) >= 6:
        # bucket to nearest 100
        buckets = Counter(int(a // 100) * 100 for a in ins)
        top = buckets.most_common(1)[0][1]
        income_like = min(1.0, top / (len(ins) * 0.35))

    max_txn = max(amounts) if amounts else 0.0
    max_ratio = (max_txn / mean_amt) if mean_amt > 0 else 0.0

    active_days = len({(_parse_dt(t.get("at", "")) or datetime.min).date() for t in txns})
    smartphone_active = min(1.0, active_days / (months * 22))
    contact_stability = min(1.0, peer_tenure / 24.0)

    feats = {
        "upi_txn_per_month": len(txns) / months,
        "upi_amount_cv": min(3.0, cv),
        "upi_in_out_ratio": min(5.0, in_sum / out_sum),
        "bill_on_time_ratio": bill_on_time,
        "bill_count_6m": float(len(bills)),
        "recharge_regularity": regularity,
        "recharge_count_6m": float(len(recharges)),
        "peer_recurrence": peer_recurrence,
        "peer_tenure_months": peer_tenure,
        "unique_peers": float(len(peers)),
        "merchant_diversity": float(len(merchants)),
        "income_like_periodicity": income_like,
        "avg_monthly_volume": (sum(amounts) / months) if amounts else 0.0,
        "max_single_txn_ratio": min(20.0, max_ratio),
        "rental_upi_present": rental,
        "gst_regularity": gst,
        "smartphone_active_days": smartphone_active,
        "contact_stability": contact_stability,
    }
    # Ensure stable key order
    return {k: float(feats.get(k, 0.0)) for k in FEATURE_NAMES}


def factor_breakdown(features: dict[str, float]) -> dict[str, float]:
    """Human-facing 0–100 factor scores derived from features."""

    def clip100(*parts: float) -> float:
        return round(max(0.0, min(100.0, sum(parts))), 1)

    return {
        "payment_consistency": clip100(
            features.get("bill_on_time_ratio", 0) * 55,
            features.get("recharge_regularity", 0) * 30,
            (1 - min(1.0, features.get("upi_amount_cv", 0) / 2)) * 15,
        ),
        "transaction_volume": clip100(
            min(40.0, features.get("upi_txn_per_month", 0)),
            min(40.0, features.get("avg_monthly_volume", 0) / 400),
            features.get("merchant_diversity", 0) * 4,
        ),
        "network_stability": clip100(
            features.get("contact_stability", 0) * 45,
            features.get("peer_recurrence", 0) * 35,
            min(20.0, features.get("unique_peers", 0) * 4),
        ),
        "income_regularity": clip100(
            features.get("income_like_periodicity", 0) * 50,
            features.get("upi_in_out_ratio", 0) * 8,
            features.get("rental_upi_present", 0) * 15,
            features.get("gst_regularity", 0) * 20,
        ),
    }


def eligibility_band(score: int) -> tuple[int, int]:
    if score >= 80:
        return 50_000, 150_000
    if score >= 65:
        return 25_000, 50_000
    if score >= 50:
        return 5_000, 25_000
    if score >= 35:
        return 100, 5_000
    return 0, 0
