from __future__ import annotations

from fastapi import APIRouter

from finehelper_api.deps import AuthDep, SessionDep, get_settings_dep, hash_password, session_expiry, verify_password
from finehelper_api.schemas import LoginIn, SignupIn, TokenOut, orm_to_dict
from finehelper_core.crypto import hash_token, new_api_key
from finehelper_core.db.models import ApiKey, Membership, Org, Session, User
from sqlalchemy import select
from fastapi import HTTPException
import re
import secrets
from datetime import datetime, timezone

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


@router.post("/signup", response_model=TokenOut)
async def signup(body: SignupIn, session: SessionDep, request_settings=None):
    existing = await session.scalar(select(User).where(User.email == body.email.lower()))
    if existing:
        raise HTTPException(409, "email already registered")
    user = User(email=body.email.lower(), password_hash=hash_password(body.password), name=body.name)
    session.add(user)
    await session.flush()
    slug = _slugify(body.org_name)
    taken = await session.scalar(select(Org).where(Org.slug == slug))
    if taken:
        slug = f"{slug}-{secrets.token_hex(2)}"
    org = Org(name=body.org_name, slug=slug)
    session.add(org)
    await session.flush()
    session.add(Membership(org_id=org.id, user_id=user.id, role="owner"))
    raw = secrets.token_urlsafe(32)
    session.add(Session(user_id=user.id, token_hash=hash_token(raw), expires_at=session_expiry()))
    await session.flush()
    return TokenOut(token=raw, user=orm_to_dict(user), org=orm_to_dict(org))


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, session: SessionDep):
    user = await session.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "invalid credentials")
    raw = secrets.token_urlsafe(32)
    session.add(Session(user_id=user.id, token_hash=hash_token(raw), expires_at=session_expiry()))
    membership = await session.scalar(select(Membership).where(Membership.user_id == user.id))
    org = await session.get(Org, membership.org_id) if membership else None
    if not org:
        raise HTTPException(403, "no organization")
    return TokenOut(token=raw, user=orm_to_dict(user), org=orm_to_dict(org))


@router.get("/me")
async def me(auth: AuthDep):
    return {"user": orm_to_dict(auth.user), "org": orm_to_dict(auth.org), "role": auth.membership.role, "via": auth.via}


@router.post("/api-keys")
async def create_api_key(auth: AuthDep, session: SessionDep, name: str = "cli"):
    full, prefix, hashed = new_api_key()
    row = ApiKey(org_id=auth.org_id, user_id=auth.user_id, name=name, prefix=prefix, key_hash=hashed)
    session.add(row)
    await session.flush()
    return {"id": str(row.id), "key": full, "prefix": prefix, "name": name}


@router.get("/api-keys")
async def list_api_keys(auth: AuthDep, session: SessionDep):
    rows = (
        await session.scalars(select(ApiKey).where(ApiKey.org_id == auth.org_id, ApiKey.revoked_at.is_(None)))
    ).all()
    return [orm_to_dict(r) for r in rows]
