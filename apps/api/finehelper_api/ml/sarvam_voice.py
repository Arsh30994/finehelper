"""Sarvam AI STT/TTS client — India English / Hindi / Hinglish voice shell."""

from __future__ import annotations

import base64
import logging
import re
from typing import Any

import httpx

from finehelper_core.settings import Settings

log = logging.getLogger(__name__)

SARVAM_BASE = "https://api.sarvam.ai"
# Calm, natural Indian English / Hinglish-friendly voice
DEFAULT_SPEAKER = "anushka"
FALLBACK_SPEAKER = "shubh"


def _headers(api_key: str) -> dict[str, str]:
    return {"api-subscription-key": api_key}


def detect_tts_language(text: str) -> str:
    """Pick TTS language from reply script — no session lock."""
    if not text:
        return "en-IN"
    # Devanagari → Hindi TTS (handles Hinglish with native script well)
    if re.search(r"[\u0900-\u097F]", text):
        return "hi-IN"
    # Romanized Hindi / Hinglish cues
    if re.search(
        r"\b(hai|hain|kya|mera|meri|aap|score|wajah|kyun|kaise|nahi|bahut|accha|theek)\b",
        text.lower(),
    ):
        return "hi-IN"
    return "en-IN"


async def speech_to_text(
    settings: Settings,
    *,
    audio: bytes,
    filename: str = "audio.webm",
    content_type: str = "audio/webm",
) -> dict[str, Any]:
    if not settings.sarvam_api_key:
        raise RuntimeError("SARVAM_API_KEY not configured")
    # codemix preserves Hinglish naturally; unknown = auto language detect
    data = {
        "model": "saaras:v3",
        "mode": "codemix",
        "language_code": "unknown",
    }
    files = {"file": (filename or "audio.webm", audio, content_type or "audio/webm")}
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{SARVAM_BASE}/speech-to-text",
            headers=_headers(settings.sarvam_api_key),
            data=data,
            files=files,
        )
        if resp.status_code >= 400:
            log.warning("Sarvam STT error %s: %s", resp.status_code, resp.text[:400])
            resp.raise_for_status()
        payload = resp.json()
    transcript = (payload.get("transcript") or "").strip()
    lang = payload.get("language_code") or detect_tts_language(transcript)
    return {
        "transcript": transcript,
        "language_code": lang,
        "language_probability": payload.get("language_probability"),
        "request_id": payload.get("request_id"),
        "provider": "sarvam",
        "mode": "codemix",
    }


async def text_to_speech(
    settings: Settings,
    *,
    text: str,
    language_code: str | None = None,
    speaker: str | None = None,
) -> dict[str, Any]:
    if not settings.sarvam_api_key:
        raise RuntimeError("SARVAM_API_KEY not configured")
    clean = (text or "").strip()[:2400]
    if not clean:
        raise ValueError("empty text")
    lang = language_code or detect_tts_language(clean)
    body = {
        "text": clean,
        "language_code": lang,
        "target_language_code": lang,  # compat across bulbul versions
        "speaker": speaker or settings.sarvam_tts_speaker or DEFAULT_SPEAKER,
        "model": "bulbul:v3",
        "pace": 0.95,
        "speech_sample_rate": 22050,
        "enable_preprocessing": True,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{SARVAM_BASE}/text-to-speech",
            headers={**_headers(settings.sarvam_api_key), "Content-Type": "application/json"},
            json=body,
        )
        # Retry once with alternate speaker if voice id rejected
        if resp.status_code >= 400 and body["speaker"] != FALLBACK_SPEAKER:
            log.warning("Sarvam TTS retry with %s: %s", FALLBACK_SPEAKER, resp.text[:300])
            body["speaker"] = FALLBACK_SPEAKER
            resp = await client.post(
                f"{SARVAM_BASE}/text-to-speech",
                headers={**_headers(settings.sarvam_api_key), "Content-Type": "application/json"},
                json=body,
            )
        if resp.status_code >= 400:
            log.warning("Sarvam TTS error %s: %s", resp.status_code, resp.text[:400])
            resp.raise_for_status()
        payload = resp.json()

    audios = payload.get("audios") or payload.get("audio")
    if isinstance(audios, list) and audios:
        b64 = audios[0]
    elif isinstance(audios, str):
        b64 = audios
    else:
        raise RuntimeError("Sarvam TTS returned no audio")

    # Validate base64
    raw = base64.b64decode(b64)
    return {
        "audio_base64": b64,
        "byte_length": len(raw),
        "mime_type": "audio/wav",
        "language_code": lang,
        "speaker": body["speaker"],
        "provider": "sarvam",
        "request_id": payload.get("request_id"),
    }
