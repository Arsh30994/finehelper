from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI
from sqlalchemy import select

from finehelper_api.deps import AuthDep, SessionDep
from finehelper_api.schemas import ChatIn
from finehelper_core.crypto import decrypt_secret
from finehelper_core.db.models import Credential, Deployment, Run
from finehelper_core.settings import get_settings

router = APIRouter(tags=["inference"])


async def _openai_key(session, org_id: UUID) -> str | None:
    cred = await session.scalar(
        select(Credential).where(Credential.org_id == org_id, Credential.provider == "openai")
    )
    if not cred:
        return None
    return decrypt_secret(cred.encrypted_secret, get_settings().master_key)


@router.post("/v1/chat/completions")
async def chat_completions(body: ChatIn, auth: AuthDep, session: SessionDep):
    run = None
    deployment = None
    if body.deployment_id:
        deployment = await session.get(Deployment, body.deployment_id)
        if not deployment or deployment.org_id != auth.org_id:
            raise HTTPException(404, "deployment not found")
        run = await session.get(Run, deployment.run_id)
    elif body.run_id:
        run = await session.get(Run, body.run_id)
        if not run or run.org_id != auth.org_id:
            raise HTTPException(404, "run not found")
    model = body.model
    backend = run.backend if run else "openai"
    if run and run.provider_model_id:
        model = model or run.provider_model_id
    if not model:
        raise HTTPException(400, "model, run_id, or deployment_id required")

    if backend in {"dry_run"} or (isinstance(model, str) and model.startswith("dry-run://")):
        last = next((m.get("content") for m in reversed(body.messages) if m.get("role") == "user"), "")
        content = f"[dry-run] {last}"
        return {
            "id": "chatcmpl-finehelper",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "model": model,
        }

    api_key = await _openai_key(session, auth.org_id)
    if not api_key:
        raise HTTPException(400, "store an OpenAI credential to chat with this model")
    client = AsyncOpenAI(api_key=api_key)
    resp = await client.chat.completions.create(
        model=model,
        messages=body.messages,
        temperature=body.temperature,
    )
    return resp.model_dump()
