from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from finehelper_api.jwt import JwtError, decode_access_token
from finehelper_core.crypto import hash_token
from finehelper_core.db.mongo import Mongo
from finehelper_core.models import ApiKey, Membership, Org, User
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
        key = ApiKey.from_mongo(
            await db.api_keys.find_one({"key_hash": hash_token(token), "revoked_at": None})
        )
        if not key:
            raise HTTPException(401, "invalid api key")
        key.last_used_at = now
        await db.save(db.api_keys, key)
        user = User.from_mongo(await db.users.find_one({"_id": key.user_id}))
        org = Org.from_mongo(await db.orgs.find_one({"_id": key.org_id}))
        membership = Membership.from_mongo(
            await db.memberships.find_one({"org_id": key.org_id, "user_id": key.user_id})
        )
        if not user or not org or not membership or org.deleted_at:
            raise HTTPException(401, "invalid api key")
        return AuthContext(user, org, membership, "api_key")

    try:
        payload = decode_access_token(token, settings.secret_key)
    except JwtError:
        raise HTTPException(401, "invalid session") from None
    user = User.from_mongo(await db.users.find_one({"_id": str(payload.get("sub"))}))
    if not user:
        raise HTTPException(401, "invalid session")
    cursor = db.memberships.find({"user_id": user.id})
    memberships = [Membership.from_mongo(doc) for doc in await cursor.to_list(100) if doc]
    memberships = [m for m in memberships if m is not None]
    if not memberships:
        raise HTTPException(403, "user has no organization")
    org = None
    membership = None
    wanted = x_org_id or str(payload.get("org_id") or "")
    if wanted:
        membership = next((m for m in memberships if m.org_id == wanted), None)
        if not membership:
            raise HTTPException(403, "not a member of this org")
        org = Org.from_mongo(await db.orgs.find_one({"_id": membership.org_id}))
    else:
        membership = memberships[0]
        org = Org.from_mongo(await db.orgs.find_one({"_id": membership.org_id}))
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
