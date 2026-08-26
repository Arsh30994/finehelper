"""TrustMesh agentic orchestrator — intent → tools → natural reply."""

from __future__ import annotations

import re

from fastapi import Request

from finehelper_api.controllers import auth_controller, trust_controller
from finehelper_api.deps import AuthContext
from finehelper_api.ml.agent_llm import fallback_reply, gemini_reply
from finehelper_api.schemas import AgentChatIn, TrustBootstrapIn, TrustExplainIn
from finehelper_api.security import enforce_trust_rate_limit
from finehelper_core.db.mongo import Mongo
from finehelper_core.settings import Settings


def detect_intent(message: str) -> str:
    m = message.lower().strip()
    if re.search(r"\b(bootstrap|load demo|fill data|start demo|generate data|assumed data)\b", m) or "demo data" in m:
        return "bootstrap"
    if re.search(r"\b(blockchain|on-?chain|attest|ledger|hash|polygon|web3)\b", m) or (
        "verify" in m and re.search(r"\b(score|trust|chain|hash)\b", m)
    ):
        return "chain"
    if re.search(r"\b(explain|why|kaise|kyun|wajah|hinglish|factor)\b", m) or "score" in m and re.search(
        r"\b(explain|why|detail|batao|samjhao)\b", m
    ):
        return "explain"
    if re.search(r"\b(signal|signals|bill|bills|upi|peer|people|recharge|txn|transaction)\b", m):
        return "signals"
    if re.search(r"\b(offer|offers|loan|credit|eligib|limit|flex)\b", m):
        return "offers"
    if re.search(r"\b(security|fingerprint|otp|phone|email|biometric)\b", m) or (
        "verify" in m and re.search(r"\b(phone|email|otp|finger)\b", m)
    ):
        return "security"
    if re.search(r"\b(scan|qr|camera)\b", m):
        return "scan"
    if re.search(r"\b(help|kya kar|what can|commands|menu)\b", m):
        return "help"
    if re.search(r"\b(score|trust)\b", m):
        return "explain"
    return "general"


async def chat(
    db: Mongo,
    settings: Settings,
    auth: AuthContext,
    body: AgentChatIn,
    request: Request | None = None,
) -> dict:
    if request is not None:
        enforce_trust_rate_limit(request, auth.user_id)

    message = (body.message or "").strip()[:1000]
    if not message:
        return {
            "reply": "Ask me about your Trust Score, signals, offers, or say “load demo data”.",
            "intent": "help",
            "tools_used": [],
            "lang": "en",
        }

    requested = (body.lang or "auto").lower().strip()
    if requested in {"auto", "detect", ""}:
        lang = "hi" if _looks_hinglish(message) or re.search(r"[\u0900-\u097F]", message) else "en"
    elif requested.startswith("hi"):
        lang = "hi"
    else:
        lang = "en"
    intent = detect_intent(message)
    tools_used: list[str] = []
    context: dict = {}

    # Always peek dashboard
    dash = await trust_controller.dashboard(db, auth)
    tools_used.append("get_dashboard")
    score_row = dash.get("score") or {}
    context["score"] = score_row.get("score") if score_row else None
    context["factors"] = score_row.get("factors") if score_row else {}
    context["eligibility_min"] = score_row.get("eligibility_min", 0) if score_row else 0
    context["eligibility_max"] = score_row.get("eligibility_max", 0) if score_row else 0
    context["signals"] = dash.get("signals_summary") or {}

    if intent == "bootstrap" or (intent in {"explain", "general"} and not context["score"]):
        boot = await trust_controller.bootstrap(
            db,
            settings,
            auth,
            TrustBootstrapIn(occupation="kirana", quality="good", force=body.force_refresh, lang=lang),
            request,
        )
        tools_used.append("bootstrap")
        score_row = boot.get("score") or {}
        context["score"] = score_row.get("score")
        context["factors"] = score_row.get("factors") or {}
        context["eligibility_min"] = score_row.get("eligibility_min", 0)
        context["eligibility_max"] = score_row.get("eligibility_max", 0)
        context["signals"] = boot.get("signals_summary") or {}
        if intent == "general":
            intent = "bootstrap"

    if intent == "explain" and context.get("score") is not None:
        explained = await trust_controller.explain(
            db, settings, auth, TrustExplainIn(lang=lang), request
        )
        tools_used.append("explain_score")
        context["explanation"] = explained.get("explanation")

    if intent == "security":
        sec = await auth_controller.security_status(db, auth)
        tools_used.append("security_status")
        context["security"] = sec

    if intent == "chain":
        verified = await trust_controller.verify_attestation(db, settings, auth)
        tools_used.append("verify_attestation")
        context["chain"] = verified
        # Refresh score fields after possible auto-attest
        dash = await trust_controller.dashboard(db, auth)
        score_row = dash.get("score") or {}
        context["score"] = score_row.get("score") if score_row else context.get("score")
        context["chain_tx"] = score_row.get("chain_tx_hash")
        context["score_hash"] = score_row.get("score_hash")

    # Build factual context string for Gemini
    ctx_lines = [
        f"intent={intent}",
        f"score={context.get('score')}",
        f"eligibility={context.get('eligibility_min')}-{context.get('eligibility_max')}",
        f"factors={context.get('factors')}",
    ]
    if context.get("explanation"):
        ctx_lines.append(f"stored_explanation={context['explanation']}")
    if context.get("signals"):
        s = context["signals"]
        ctx_lines.append(
            f"signals txn={s.get('txn_count')} bills={s.get('bill_count')} recharges={s.get('recharge_count')} peers={len(s.get('peers') or [])}"
        )
    if context.get("security"):
        ctx_lines.append(f"security={context['security']}")
    if context.get("chain"):
        ctx_lines.append(f"chain_verify={context['chain']}")
        ctx_lines.append(f"chain_tx={context.get('chain_tx')} score_hash={context.get('score_hash')}")
    ctx_lines.append("disclaimer=assumed synthetic demo data, not CIBIL, no real money movement, chain stores hashes only")

    reply = await gemini_reply(
        settings,
        user_message=message,
        context="\n".join(ctx_lines),
        lang=lang,
    )
    if not reply:
        # Prefer stored explanation when available
        if intent == "explain" and context.get("explanation"):
            reply = context["explanation"]
        else:
            reply = fallback_reply(intent=intent, context=context, lang=lang)

    suggestions = _suggestions(intent, lang)
    return {
        "reply": reply,
        "intent": intent,
        "tools_used": tools_used,
        "lang": lang,
        "score": context.get("score"),
        "suggestions": suggestions,
        "demo": True,
    }


def _looks_hinglish(message: str) -> bool:
    return bool(re.search(r"\b(hai|kya|mera|mere|batao|samjhao|kyun|kaise|score|wajah)\b", message.lower()))


def _suggestions(intent: str, lang: str) -> list[str]:
    if lang.startswith("hi"):
        return [
            "Mera score explain karo",
            "Signals dikhao",
            "Offers kya hain?",
            "Demo data load karo",
        ]
    return [
        "Explain my trust score",
        "Show my signals",
        "What offers do I get?",
        "Load demo data",
    ]
