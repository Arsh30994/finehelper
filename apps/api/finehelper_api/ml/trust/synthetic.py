"""Assumed / synthetic 6-month UPI · bill · recharge signals for demos.

No real NPCI, bank, or CIBIL data — everything here is invented for product demos.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

MERCHANTS = [
    ("Blinkit", "groceries"),
    ("BigBasket", "groceries"),
    ("Swiggy", "food"),
    ("Zomato", "food"),
    ("ConfirmTkt", "travel"),
    ("IRCTC", "travel"),
    ("Jio Recharge", "telecom"),
    ("Airtel Postpaid", "telecom"),
    ("BESCOM Power", "utilities"),
    ("ACT Fibernet", "utilities"),
    ("Metro Card", "transit"),
    ("Pharmacy Plus", "health"),
]

PEERS = [
    ("Ravi Wholesale", "ravi.wholesale@oksbi", "supplier"),
    ("Meena Dairy", "meena@paytm", "supplier"),
    ("Akhilesh Das", "akhilesh@ybl", "customer"),
    ("Suresh Transport", "suresh@okhdfcbank", "logistics"),
    ("Priya Rent", "priya@oksbi", "landlord"),
    ("Vendor Collective", "vendor@ybl", "peer"),
    ("Ananya Sharma", "ananya@oksbi", "customer"),
    ("Kiran Fruits", "kiran@ybl", "supplier"),
]

BILLERS = [
    ("electricity", "BESCOM"),
    ("water", "BWSSB"),
    ("postpaid", "Airtel"),
    ("fiber", "ACT Fibernet"),
    ("gas", "Indane"),
    ("cable", "Tata Play"),
]

ASSUMED_PERSONAS = {
    "kirana": {
        "display_name": "Ramesh Kirana",
        "upi_id": "ramesh.kirana@oksbi",
        "bank_name": "Demo State Bank",
        "bank_account_last4": "4821",
        "city": "Bengaluru",
        "tagline": "Neighborhood kirana with steady UPI inflows",
        "quality": "good",
    },
    "gig": {
        "display_name": "Priya Rider",
        "upi_id": "priya.rider@ybl",
        "bank_name": "Demo Payments Bank",
        "bank_account_last4": "9033",
        "city": "Hyderabad",
        "tagline": "Gig delivery — frequent small UPI settlements",
        "quality": "mixed",
    },
    "vendor": {
        "display_name": "Suresh Stall",
        "upi_id": "suresh.stall@paytm",
        "bank_name": "Demo Cooperative Bank",
        "bank_account_last4": "1170",
        "city": "Pune",
        "tagline": "Street vendor with recurring supplier pays",
        "quality": "good",
    },
    "farmer": {
        "display_name": "Lakshmi Farm",
        "upi_id": "lakshmi.farm@oksbi",
        "bank_name": "Demo Rural Bank",
        "bank_account_last4": "6654",
        "city": "Mysuru",
        "tagline": "Seasonal income + regular utility bills",
        "quality": "mixed",
    },
}


def assumed_persona(occupation: str = "kirana") -> dict[str, Any]:
    return dict(ASSUMED_PERSONAS.get(occupation, ASSUMED_PERSONAS["kirana"]))


def generate_signal_batch(
    *,
    seed: int | None = None,
    months: int = 6,
    occupation: str = "kirana",
    quality: str = "good",
) -> dict[str, Any]:
    """
    quality: good | mixed | thin — drives believable score bands for demos.
    All rows are assumed / synthetic.
    """
    rng = random.Random(seed if seed is not None else 42)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30 * months)
    persona = assumed_persona(occupation)

    if quality == "good":
        txn_per_month, on_time, peer_n, recharge_n = 48, 0.94, 7, 6
    elif quality == "thin":
        txn_per_month, on_time, peer_n, recharge_n = 9, 0.52, 2, 2
    else:
        txn_per_month, on_time, peer_n, recharge_n = 24, 0.78, 5, 4

    peers: list[dict[str, Any]] = []
    for i in range(peer_n):
        name, upi, role = PEERS[i % len(PEERS)]
        peers.append(
            {
                "name": name,
                "upi": upi,
                "role": role,
                "direction": "both" if role in {"supplier", "customer"} else rng.choice(["in", "out"]),
                "months_known": rng.randint(16, 40) if quality == "good" else rng.randint(3, 18),
                "txn_count": rng.randint(12, 90) if quality != "thin" else rng.randint(2, 18),
            }
        )

    base_in = {"kirana": 1200, "vendor": 900, "gig": 380, "farmer": 2200}.get(occupation, 700)
    base_out = {"kirana": 650, "vendor": 500, "gig": 220, "farmer": 800}.get(occupation, 400)

    transactions: list[dict[str, Any]] = []
    day = start
    while day < now:
        # Weekends slightly busier for kirana/vendor
        weekend_boost = 1.35 if day.weekday() >= 5 and occupation in {"kirana", "vendor"} else 1.0
        n = max(0, int(rng.gauss((txn_per_month / 30) * weekend_boost, 0.9)))
        for _ in range(n):
            peer = rng.choice(peers)
            direction = peer["direction"] if peer["direction"] != "both" else rng.choice(["in", "out"])
            mu = base_in if direction == "in" else base_out
            amount = round(max(40, min(abs(rng.gauss(mu, mu * 0.35)), 28000)), 2)
            note = rng.choice(
                ["goods", "goods", "transfer", "salary-like", "rent", "settlement", ""]
                if occupation == "kirana"
                else ["settlement", "transfer", "goods", ""]
            )
            transactions.append(
                {
                    "at": (day + timedelta(hours=rng.randint(6, 22), minutes=rng.randint(0, 59))).isoformat(),
                    "amount": amount,
                    "direction": direction,
                    "counterparty": peer["name"],
                    "upi": peer["upi"],
                    "note": note,
                    "assumed": True,
                }
            )
        day += timedelta(days=1)

    # Recurring monthly income-like credit (assumed settlement)
    for m in range(months):
        transactions.append(
            {
                "at": (now - timedelta(days=28 * m + 2, hours=10)).isoformat(),
                "amount": round(base_in * rng.uniform(8, 14), 2),
                "direction": "in",
                "counterparty": "Weekly Settlement Pool",
                "upi": "settle@oksbi",
                "note": "salary-like",
                "assumed": True,
            }
        )

    # Rent UPI every month
    if quality != "thin":
        for m in range(months):
            transactions.append(
                {
                    "at": (now - timedelta(days=28 * m + 5, hours=9)).isoformat(),
                    "amount": round(rng.uniform(6500, 11000), 2),
                    "direction": "out",
                    "counterparty": "Priya Rent",
                    "upi": "priya@oksbi",
                    "note": "rent",
                    "assumed": True,
                }
            )

    bills: list[dict[str, Any]] = []
    for m in range(months):
        for kind, provider in BILLERS[: 4 if quality != "thin" else 2]:
            bills.append(
                {
                    "kind": kind,
                    "name": f"{provider} {kind}",
                    "provider": provider,
                    "amount": round(rng.uniform(280, 3200), 2),
                    "month_offset": m,
                    "on_time": rng.random() < on_time,
                    "at": (now - timedelta(days=28 * m + rng.randint(1, 12))).isoformat(),
                    "assumed": True,
                }
            )

    recharges: list[dict[str, Any]] = []
    for i in range(max(3, recharge_n * months // 2)):
        recharges.append(
            {
                "operator": rng.choice(["Jio", "Airtel", "Vi"]),
                "amount": rng.choice([149, 199, 239, 299, 666, 719]),
                "at": (now - timedelta(days=rng.randint(1, 30 * months))).isoformat(),
                "assumed": True,
            }
        )

    merchants: list[dict[str, Any]] = []
    take = MERCHANTS if quality != "thin" else MERCHANTS[:4]
    for name, category in take:
        merchants.append(
            {
                "name": name,
                "category": category,
                "spend_total": round(rng.uniform(400, 14000), 2),
                "txn_count": rng.randint(3, 48),
                "assumed": True,
            }
        )

    # Sort txns chronologically for history UI
    transactions.sort(key=lambda t: t["at"])

    return {
        "months": months,
        "transactions": transactions,
        "bills": bills,
        "recharges": recharges,
        "peers": peers,
        "merchants": merchants,
        "meta": {
            "occupation": occupation,
            "quality": quality,
            "synthetic": True,
            "assumed": True,
            "persona": persona,
            "disclaimer": "Assumed synthetic data for demo — not real bank/UPI/CIBIL records.",
        },
    }
