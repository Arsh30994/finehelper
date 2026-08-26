from __future__ import annotations

import re
import secrets

from fastapi import HTTPException

from finehelper_api.deps import AuthContext, hash_password, verify_password
from finehelper_api.jwt import encode_access_token
from finehelper_api.schemas import LoginIn, SignupIn, TokenOut, doc_to_dict
from finehelper_core.crypto import new_api_key
from finehelper_core.db.mongo import Mongo
from finehelper_core.models import ApiKey, Membership, Org, User
from finehelper_core.settings import Settings


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


async def signup(db: Mongo, settings: Settings, body: SignupIn) -> TokenOut:
    existing = await db.users.find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(409, "email already registered")
    user = User(email=body.email.lower(), password_hash=hash_password(body.password), name=body.name)
    slug = _slugify(body.org_name)
    if await db.orgs.find_one({"slug": slug}):
        slug = f"{slug}-{secrets.token_hex(2)}"
    org = Org(name=body.org_name, slug=slug)
    membership = Membership(org_id=org.id, user_id=user.id, role="owner")
    await db.insert(db.users, user)
    await db.insert(db.orgs, org)
    await db.insert(db.memberships, membership)
    token = encode_access_token(
        user_id=user.id,
        org_id=org.id,
        email=user.email,
        role=membership.role,
        secret=settings.secret_key,
        ttl_days=settings.jwt_ttl_days,
    )
    return TokenOut(token=token, user=doc_to_dict(user), org=doc_to_dict(org))


async def login(db: Mongo, settings: Settings, body: LoginIn) -> TokenOut:
    user = User.from_mongo(await db.users.find_one({"email": body.email.lower()}))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "invalid credentials")
    membership = Membership.from_mongo(await db.memberships.find_one({"user_id": user.id}))
    org = Org.from_mongo(await db.orgs.find_one({"_id": membership.org_id})) if membership else None
    if not membership or not org:
        raise HTTPException(403, "no organization")
    token = encode_access_token(
        user_id=user.id,
        org_id=org.id,
        email=user.email,
        role=membership.role,
        secret=settings.secret_key,
        ttl_days=settings.jwt_ttl_days,
    )
    return TokenOut(token=token, user=doc_to_dict(user), org=doc_to_dict(org))


def me(auth: AuthContext) -> dict:
    return {"user": doc_to_dict(auth.user), "org": doc_to_dict(auth.org), "role": auth.membership.role, "via": auth.via}


async def create_api_key(db: Mongo, auth: AuthContext, name: str = "cli") -> dict:
    full, prefix, hashed = new_api_key()
    row = ApiKey(org_id=auth.org_id, user_id=auth.user_id, name=name, prefix=prefix, key_hash=hashed)
    await db.insert(db.api_keys, row)
    return {"id": row.id, "key": full, "prefix": prefix, "name": name}


async def list_api_keys(db: Mongo, auth: AuthContext) -> list[dict]:
    rows = await db.api_keys.find({"org_id": auth.org_id, "revoked_at": None}).to_list(200)
    return [doc_to_dict(ApiKey.from_mongo(r)) for r in rows if r]
