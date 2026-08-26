from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from finehelper_api.controllers import agent_controller
from finehelper_api.deps import AuthDep, DbDep, SettingsDep
from finehelper_api.ml import sarvam_voice
from finehelper_api.schemas import AgentChatIn, AgentTtsIn
from finehelper_api.security import enforce_trust_rate_limit

router = APIRouter(prefix="/v1/agent", tags=["agent"])

MAX_AUDIO_BYTES = 8 * 1024 * 1024  # 8 MB


@router.post("/chat")
async def chat(body: AgentChatIn, request: Request, auth: AuthDep, db: DbDep, settings: SettingsDep):
    """TrustMesh agentic assistant — tools + Gemini (or template fallback)."""
    return await agent_controller.chat(db, settings, auth, body, request)


@router.post("/voice/stt")
async def voice_stt(
    request: Request,
    auth: AuthDep,
    settings: SettingsDep,
    file: UploadFile = File(...),
):
    """Sarvam Saaras STT — Hinglish/EN/HI auto-detect (codemix). Voice shell only."""
    enforce_trust_rate_limit(request, auth.user_id)
    if not settings.sarvam_api_key:
        raise HTTPException(503, "voice STT not configured (SARVAM_API_KEY)")
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "empty audio")
    if len(raw) > MAX_AUDIO_BYTES:
        raise HTTPException(400, "audio too large")
    try:
        result = await sarvam_voice.speech_to_text(
            settings,
            audio=raw,
            filename=file.filename or "audio.webm",
            content_type=file.content_type or "audio/webm",
        )
    except Exception as exc:
        raise HTTPException(502, f"STT failed: {exc}") from exc
    if not result.get("transcript"):
        raise HTTPException(422, "could not hear speech — try again, hold closer to mic")
    return result


@router.post("/voice/tts")
async def voice_tts(body: AgentTtsIn, request: Request, auth: AuthDep, settings: SettingsDep):
    """Sarvam Bulbul TTS — calm Indian voices; language follows text."""
    enforce_trust_rate_limit(request, auth.user_id)
    if not settings.sarvam_api_key:
        raise HTTPException(503, "voice TTS not configured (SARVAM_API_KEY)")
    try:
        return await sarvam_voice.text_to_speech(
            settings,
            text=body.text,
            language_code=body.language_code,
            speaker=body.speaker,
        )
    except Exception as exc:
        raise HTTPException(502, f"TTS failed: {exc}") from exc


@router.get("/health")
async def agent_health(settings: SettingsDep):
    return {
        "ok": True,
        "gemini": bool(settings.gemini_api_key),
        "sarvam": bool(settings.sarvam_api_key),
        "voice_shell": bool(settings.sarvam_api_key),
        "tools": [
            "get_dashboard",
            "bootstrap",
            "explain_score",
            "security_status",
            "verify_attestation",
        ],
        "chain_evm": bool(settings.chain_rpc_url and settings.chain_contract_address),
    }
