from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID

import hashlib
import os

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from finehelper_core.crypto import hash_token
from finehelper_core.db.models import ApiKey, Membership, Org, Session, User
from finehelper_core.settings import Settings

bearer = HTTPBearer(auto_error=False)


class AuthContext:
    def __init__(self, user: User, org: Org, membership: Membership, via: str):
        self.user = user
        self.org = org
        self.membership = membership
        self.via = via

    @property
    def org_id(self) -> UUID:
        return self.org.id

    @property
    def user_id(self) -> UUID:
        return self.user.id


async def _apply_org_rls(session: AsyncSession, org_id: UUID) -> None:
    bind = session.get_bind()
    dialect = getattr(getattr(bind, "dialect", None), "name", None)
    if dialect != "postgresql":
        return
    await session.execute(text("SELECT set_config('app.current_org_id', :oid, true)"), {"oid": str(org_id)})


async def get_session(request: Request) -> AsyncSession:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


async def get_auth(
    request: Request,
    session: SessionDep,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    x_org_id: Annotated[str | None, Header()] = None,
) -> AuthContext:
    if creds is None or not creds.credentials:
        raise HTTPException(401, "missing bearer token")
    token = creds.credentials
    now = datetime.now(timezone.utc)

    if token.startswith("fh_live_"):
        key = await session.scalar(select(ApiKey).where(ApiKey.key_hash == hash_token(token), ApiKey.revoked_at.is_(None)))
        if not key:
            raise HTTPException(401, "invalid api key")
        key.last_used_at = now
        user = await session.get(User, key.user_id)
        org = await session.get(Org, key.org_id)
        membership = await session.scalar(
            select(Membership).where(Membership.org_id == key.org_id, Membership.user_id == key.user_id)
        )
        if not user or not org or not membership or org.deleted_at:
            raise HTTPException(401, "invalid api key")
        await _apply_org_rls(session, org.id)
        return AuthContext(user, org, membership, "api_key")

    sess = await session.scalar(select(Session).where(Session.token_hash == hash_token(token)))
    expires = sess.expires_at if sess else None
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if not sess or expires is None or expires < now:
        raise HTTPException(401, "invalid session")
    user = await session.get(User, sess.user_id)
    if not user:
        raise HTTPException(401, "invalid session")
    memberships = (
        await session.scalars(select(Membership).where(Membership.user_id == user.id))
    ).all()
    if not memberships:
        raise HTTPException(403, "user has no organization")
    org = None
    membership = None
    if x_org_id:
        membership = next((m for m in memberships if str(m.org_id) == x_org_id), None)
        if not membership:
            raise HTTPException(403, "not a member of this org")
        org = await session.get(Org, membership.org_id)
    else:
        membership = memberships[0]
        org = await session.get(Org, membership.org_id)
    if not org or org.deleted_at:
        raise HTTPException(404, "organization not found")
    await _apply_org_rls(session, org.id)
    return AuthContext(user, org, membership, "session")


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


def session_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=14)
