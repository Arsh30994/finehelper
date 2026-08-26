from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from finehelper_api.jwt import JwtError, decode_access_token
from finehelper_api.models import Membership, Org, User, auth_model
from finehelper_core.crypto import hash_token
from finehelper_core.db.mongo import Mongo
from finehelper_core.settings import Settings

bearer = HTTPBearer(auto_error=False)


class AuthContext:
    def __init__(self, user: User, org: Org, membership: Membership, via: str):
        self.user = user
        self.org = org
        self.membership = membership
        self.via = via

    @property
    def org_id(self) -> str:
        return self.org.id

    @property
    def user_id(self) -> str:
        return self.user.id


async def get_db(request: Request) -> Mongo:
    return request.app.state.db


DbDep = Annotated[Mongo, Depends(get_db)]


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]


async def get_auth(
    request: Request,
    db: DbDep,
    settings: SettingsDep,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    x_org_id: Annotated[str | None, Header()] = None,
) -> AuthContext:
    if creds is None or not creds.credentials:
        raise HTTPException(401, "missing bearer token")
    token = creds.credentials
    now = datetime.now(timezone.utc)

    if token.startswith("fh_live_"):
        key = await auth_model.find_api_key_by_hash(db, hash_token(token))
        if not key:
            raise HTTPException(401, "invalid api key")
        key.last_used_at = now
        await auth_model.save_api_key(db, key)
        user = await auth_model.find_user_by_id(db, key.user_id)
        org = await auth_model.find_org_by_id(db, key.org_id)
        membership = await auth_model.find_membership(db, org_id=key.org_id, user_id=key.user_id)
        if not user or not org or not membership or org.deleted_at:
            raise HTTPException(401, "invalid api key")
        return AuthContext(user, org, membership, "api_key")

    try:
        payload = decode_access_token(token, settings.secret_key)
    except JwtError:
        raise HTTPException(401, "invalid session") from None
    user = await auth_model.find_user_by_id(db, str(payload.get("sub")))
    if not user:
        raise HTTPException(401, "invalid session")
    memberships = await auth_model.list_memberships_for_user(db, user.id)
    if not memberships:
        raise HTTPException(403, "user has no organization")
    wanted = x_org_id or str(payload.get("org_id") or "")
    if wanted:
        membership = next((m for m in memberships if m.org_id == wanted), None)
        if not membership:
            raise HTTPException(403, "not a member of this org")
        org = await auth_model.find_org_by_id(db, membership.org_id)
    else:
        membership = memberships[0]
        org = await auth_model.find_org_by_id(db, membership.org_id)
    if not org or org.deleted_at:
        raise HTTPException(404, "organization not found")
    return AuthContext(user, org, membership, "jwt")


AuthDep = Annotated[AuthContext, Depends(get_auth)]


def require_role(*roles: str):
    async def _inner(auth: AuthDep) -> AuthContext:
        if auth.membership.role not in roles:
            raise HTTPException(403, "insufficient role")
        return auth

    return _inner


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        _, salt_hex, dk_hex = hashed.split("$", 2)
        dk = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
        return hashlib.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False
