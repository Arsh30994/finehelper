from __future__ import annotations

from fastapi import HTTPException
from openai import AsyncOpenAI

from finehelper_api.deps import AuthContext
from finehelper_api.schemas import ChatIn
from finehelper_core.crypto import decrypt_secret
from finehelper_core.db.mongo import Mongo
from finehelper_core.models import Credential, Deployment, Run
from finehelper_core.settings import Settings


async def _openai_key(db: Mongo, settings: Settings, org_id: str) -> str | None:
    cred = Credential.from_mongo(await db.credentials.find_one({"org_id": org_id, "provider": "openai"}))
    if not cred:
        return None
    return decrypt_secret(cred.encrypted_secret, settings.master_key)


async def chat_completions(db: Mongo, settings: Settings, auth: AuthContext, body: ChatIn) -> dict:
    run = None
    if body.deployment_id:
        deployment = Deployment.from_mongo(await db.deployments.find_one({"_id": str(body.deployment_id)}))
        if not deployment or deployment.org_id != auth.org_id:
            raise HTTPException(404, "deployment not found")
        run = Run.from_mongo(await db.runs.find_one({"_id": deployment.run_id}))
    elif body.run_id:
        run = Run.from_mongo(await db.runs.find_one({"_id": str(body.run_id)}))
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

    api_key = await _openai_key(db, settings, auth.org_id)
    if not api_key:
        raise HTTPException(400, "store an OpenAI credential to chat with this model")
    client = AsyncOpenAI(api_key=api_key)
    resp = await client.chat.completions.create(
        model=model,
        messages=body.messages,
        temperature=body.temperature,
    )
    return resp.model_dump()
