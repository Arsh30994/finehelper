from __future__ import annotations

from fastapi import APIRouter

from finehelper_api.controllers import chat_controller
from finehelper_api.deps import AuthDep, DbDep, SettingsDep
from finehelper_api.schemas import ChatIn

router = APIRouter(tags=["inference"])


@router.post("/v1/chat/completions")
async def chat_completions(body: ChatIn, auth: AuthDep, db: DbDep, settings: SettingsDep):
    return await chat_controller.chat_completions(db, settings, auth, body)
