from __future__ import annotations

from finehelper_api.deps import AuthContext
from finehelper_api.schemas import ChatIn
from finehelper_api.services import chat_service
from finehelper_core.db.mongo import Mongo
from finehelper_core.settings import Settings


async def chat_completions(db: Mongo, settings: Settings, auth: AuthContext, body: ChatIn) -> dict:
    return await chat_service.chat_completions(db, settings, auth, body)
