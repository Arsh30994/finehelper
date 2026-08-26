"""Thin-file trust scoring: synthetic signals, features, and model inference."""

from __future__ import annotations

FEATURE_NAMES = [
    "upi_txn_per_month",
    "upi_amount_cv",
    "upi_in_out_ratio",
    "bill_on_time_ratio",
    "bill_count_6m",
    "recharge_regularity",
    "recharge_count_6m",
    "peer_recurrence",
    "peer_tenure_months",
    "unique_peers",
    "merchant_diversity",
    "income_like_periodicity",
    "avg_monthly_volume",
    "max_single_txn_ratio",
    "rental_upi_present",
    "gst_regularity",
    "smartphone_active_days",
    "contact_stability",
]
