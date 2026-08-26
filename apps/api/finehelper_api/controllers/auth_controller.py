from __future__ import annotations

from finehelper_api.deps import AuthContext
from finehelper_api.schemas import LoginIn, SignupIn, TokenOut
from finehelper_api.services import auth_service
from finehelper_core.db.mongo import Mongo
from finehelper_core.settings import Settings


async def signup(db: Mongo, settings: Settings, body: SignupIn) -> TokenOut:
    return await auth_service.signup(db, settings, body)


async def login(db: Mongo, settings: Settings, body: LoginIn) -> TokenOut:
    return await auth_service.login(db, settings, body)


def me(auth: AuthContext) -> dict:
    return auth_service.me(auth)


async def create_api_key(db: Mongo, auth: AuthContext, name: str = "cli") -> dict:
    return await auth_service.create_api_key(db, auth, name)


async def list_api_keys(db: Mongo, auth: AuthContext) -> list[dict]:
    return await auth_service.list_api_keys(db, auth)
