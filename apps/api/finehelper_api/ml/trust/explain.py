"""Gemini (or local fallback) explanations for trust scores."""

from __future__ import annotations

import httpx

from finehelper_core.settings import Settings


def _fallback_explanation(score: int, factors: dict[str, float], lang: str) -> str:
    best = max(factors, key=factors.get) if factors else "payment_consistency"
    worst = min(factors, key=factors.get) if factors else "income_regularity"
    labels = {
        "payment_consistency": ("bill payments", "bill payments"),
        "transaction_volume": ("UPI activity", "UPI activity"),
        "network_stability": ("stable contacts", "stable contacts / network"),
        "income_regularity": ("income regularity", "income pattern"),
    }
    strong = labels.get(best, (best, best))[1]
    weak = labels.get(worst, (worst, worst))[1]
    if lang.startswith("hi"):
        return (
            f"Aapka Trust Score {score}/100 hai. "
            f"Strong point: {strong}. "
            f"Improve karne layak: {weak}. "
            f"Ye synthetic demo signals par based hai — CIBIL nahi."
        )
    return (
        f"Your Trust Score is {score}/100 because {strong} looks solid "
        f"while {weak} still varies. "
        f"This is a thin-file demo score from synthetic UPI/bill signals — not a CIBIL score."
    )


async def explain_score(
    settings: Settings,
    *,
    score: int,
    factors: dict[str, float],
    eligibility_min: int,
    eligibility_max: int,
    lang: str = "en",
) -> str:
    lang = "hi" if lang.lower().startswith("hi") else "en"
    if not settings.gemini_api_key:
        return _fallback_explanation(score, factors, lang)

    prompt = (
        "You explain alternate credit / trust scores for credit-invisible Indians. "
        "Be warm, clear, and honest that this is a demo thin-file model (not CIBIL). "
        f"Language: {'Hinglish (simple Hindi mixed with English)' if lang == 'hi' else 'simple English'}. "
        f"Score={score}/100. Factors={factors}. "
        f"Eligibility band INR {eligibility_min}-{eligibility_max}. "
        "Max 3 short sentences. Name the strongest and weakest factor. "
        "Do not invent bank balances, account numbers, or real lender names."
    )
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": settings.gemini_api_key,
                },
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return text or _fallback_explanation(score, factors, lang)
    except Exception:
        return _fallback_explanation(score, factors, lang)
