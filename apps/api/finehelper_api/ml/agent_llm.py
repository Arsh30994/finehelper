"""Gemini helper for TrustMesh agent replies (with offline fallback)."""

from __future__ import annotations

import httpx

from finehelper_core.settings import Settings

SYSTEM = (
    "You are TrustMesh Agent — a thin-file trust assistant for credit-invisible Indians. "
    "You ONLY talk about Trust Score, synthetic UPI/bill signals, offers, scan, and security. "
    "Never invent bank balances or claim this is CIBIL. "
    "Data is assumed/demo. Keep answers under 4 short sentences — calm, patient, dignified; suitable to speak aloud. "
    "Match the user's language in the moment: pure English, pure Hindi, or Hinglish (code-switch naturally). "
    "Do not force one language for the whole session."
)


async def gemini_reply(settings: Settings, *, user_message: str, context: str, lang: str) -> str | None:
    if not settings.gemini_api_key:
        return None
    lang_note = "Hinglish (simple Hindi + English)" if lang.startswith("hi") else "simple English"
    prompt = (
        f"{SYSTEM}\nPreferred language: {lang_note}.\n\n"
        f"Tool context (facts — do not contradict):\n{context}\n\n"
        f"User: {user_message}\nAgent:"
    )
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    try:
        async with httpx.AsyncClient(timeout=25) as client:
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
            return text[:1500] if text else None
    except Exception:
        return None


def fallback_reply(*, intent: str, context: dict, lang: str) -> str:
    hi = lang.startswith("hi")
    score = context.get("score")
    if intent == "bootstrap":
        if hi:
            return (
                f"Maine assumed demo data load kar diya. "
                f"Aapka Trust Score ab {score}/100 hai. "
                f"Ye synthetic UPI/bill signals par based hai — real bank ya CIBIL nahi."
            )
        return (
            f"I loaded assumed demo data. Your Trust Score is now {score}/100. "
            f"This uses synthetic UPI/bill signals — not a real bank or CIBIL."
        )
    if intent == "explain":
        factors = context.get("factors") or {}
        best = max(factors, key=factors.get) if factors else "payment_consistency"
        if hi:
            return (
                f"Aapka score {score}/100 hai. Sabse strong factor: {best.replace('_', ' ')}. "
                f"Eligibility roughly ₹{context.get('eligibility_min', 0)}–₹{context.get('eligibility_max', 0)}. "
                f"Demo thin-file model hai."
            )
        return (
            f"Your score is {score}/100. Strongest factor: {best.replace('_', ' ')}. "
            f"Eligibility band ₹{context.get('eligibility_min', 0)}–₹{context.get('eligibility_max', 0)}. "
            f"This is a demo thin-file model."
        )
    if intent == "signals":
        s = context.get("signals") or {}
        if hi:
            return (
                f"Signals mein {s.get('txn_count', 0)} UPI txns, {s.get('bill_count', 0)} bills, "
                f"{s.get('recharge_count', 0)} recharges hain — sab assumed/synthetic."
            )
        return (
            f"You have {s.get('txn_count', 0)} UPI txns, {s.get('bill_count', 0)} bills, "
            f"and {s.get('recharge_count', 0)} recharges — all assumed/synthetic."
        )
    if intent == "offers":
        if hi:
            return (
                f"Score {score}/100 ke hisaab se demo offers ₹{context.get('eligibility_min', 0)} "
                f"se ₹{context.get('eligibility_max', 0)} tak dikhte hain. Real loan nahi."
            )
        return (
            f"Based on score {score}/100, demo offers show about "
            f"₹{context.get('eligibility_min', 0)}–₹{context.get('eligibility_max', 0)}. Not a real loan."
        )
    if intent == "security":
        sec = context.get("security") or {}
        if hi:
            return (
                f"Security: email={'verified' if sec.get('email_verified') else 'pending'}, "
                f"phone={'verified' if sec.get('phone_verified') else 'pending'}, "
                f"fingerprint={'on' if sec.get('biometric_enabled') else 'off'}. "
                f"/app/security par complete karein."
            )
        return (
            f"Security status — email: {'verified' if sec.get('email_verified') else 'pending'}, "
            f"phone: {'verified' if sec.get('phone_verified') else 'pending'}, "
            f"fingerprint: {'on' if sec.get('biometric_enabled') else 'off'}. "
            f"Open Security to finish setup."
        )
    if intent == "scan":
        if hi:
            return "QR scan demo signal log karta hai — paise move nahi hote. /app/scan kholen."
        return "QR scan only logs an assumed spend signal — no money moves. Open Scan to try."
    if intent == "chain":
        ch = context.get("chain") or {}
        tx = (ch.get("chain_tx_hash") or context.get("chain_tx") or "")[:18]
        ok = ch.get("ok")
        if hi:
            return (
                f"Score fingerprint chain par anchored hai "
                f"({'verified' if ok else 'pending'}). Tx: {tx or 'n/a'}… "
                f"Sirf hash — raw UPI nahi. CIBIL nahi."
            )
        return (
            f"Your score fingerprint is anchored on the ledger "
            f"({'verified' if ok else 'check pending'}). Tx: {tx or 'n/a'}… "
            f"Hashes only — no raw UPI. Not CIBIL."
        )
    if intent == "help":
        if hi:
            return (
                "Main TrustMesh agent hoon. Pooch sakte ho: score kyun, signals, offers, "
                "bootstrap/demo data, security, ya scan. Sab synthetic demo hai."
            )
        return (
            "I'm the TrustMesh agent. Ask about your score, signals, offers, "
            "demo data bootstrap, security, or scan. Everything is synthetic demo data."
        )
    # general
    if score is not None:
        if hi:
            return f"Aapka current Trust Score {score}/100 hai (assumed data). Aur detail chahiye to 'explain my score' boliye."
        return f"Your Trust Score is {score}/100 (assumed data). Say “explain my score” for details."
    if hi:
        return "Abhi score nahi mila. 'load demo data' boliye — main assumed signals fill kar dunga."
    return "No score yet. Say “load demo data” and I’ll fill assumed signals for you."
