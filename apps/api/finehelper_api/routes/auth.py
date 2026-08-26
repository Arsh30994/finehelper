from __future__ import annotations

from fastapi import APIRouter

from finehelper_api.controllers import auth_controller
from finehelper_api.deps import AuthDep, DbDep, SettingsDep
from finehelper_api.schemas import LoginIn, SignupIn, TokenOut

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/signup", response_model=TokenOut)
async def signup(body: SignupIn, db: DbDep, settings: SettingsDep):
    return await auth_controller.signup(db, settings, body)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, db: DbDep, settings: SettingsDep):
    return await auth_controller.login(db, settings, body)


@router.get("/me")
async def me(auth: AuthDep):
    return auth_controller.me(auth)


@router.post("/api-keys")
async def create_api_key(auth: AuthDep, db: DbDep, name: str = "cli"):
    return await auth_controller.create_api_key(db, auth, name)


@router.get("/api-keys")
async def list_api_keys(auth: AuthDep, db: DbDep):
    return await auth_controller.list_api_keys(db, auth)
