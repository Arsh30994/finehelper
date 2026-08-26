"""Auth-related Mongo repositories."""

from __future__ import annotations

from finehelper_core.db.mongo import Mongo
from finehelper_core.models import ApiKey, Membership, Org, User


async def find_user_by_email(db: Mongo, email: str) -> User | None:
    return User.from_mongo(await db.users.find_one({"email": email.lower()}))


async def find_user_by_id(db: Mongo, user_id: str) -> User | None:
    return User.from_mongo(await db.users.find_one({"_id": user_id}))


async def save_user(db: Mongo, user: User) -> User:
    user.touch()
    await db.users.replace_one({"_id": user.id}, user.to_mongo(), upsert=True)
    return user


async def insert_user(db: Mongo, user: User) -> User:
    await db.insert(db.users, user)
    return user


async def find_org_by_slug(db: Mongo, slug: str) -> Org | None:
    return Org.from_mongo(await db.orgs.find_one({"slug": slug}))


async def find_org_by_id(db: Mongo, org_id: str) -> Org | None:
    return Org.from_mongo(await db.orgs.find_one({"_id": org_id}))


async def insert_org(db: Mongo, org: Org) -> Org:
    await db.insert(db.orgs, org)
    return org


async def find_membership(db: Mongo, *, org_id: str | None = None, user_id: str | None = None) -> Membership | None:
    query: dict = {}
    if org_id:
        query["org_id"] = org_id
    if user_id:
        query["user_id"] = user_id
    return Membership.from_mongo(await db.memberships.find_one(query))


async def list_memberships_for_user(db: Mongo, user_id: str) -> list[Membership]:
    rows = await db.memberships.find({"user_id": user_id}).to_list(100)
    return [m for m in (Membership.from_mongo(r) for r in rows) if m]


async def insert_membership(db: Mongo, membership: Membership) -> Membership:
    await db.insert(db.memberships, membership)
    return membership


async def find_api_key_by_hash(db: Mongo, key_hash: str) -> ApiKey | None:
    return ApiKey.from_mongo(await db.api_keys.find_one({"key_hash": key_hash, "revoked_at": None}))


async def insert_api_key(db: Mongo, key: ApiKey) -> ApiKey:
    await db.insert(db.api_keys, key)
    return key


async def list_api_keys(db: Mongo, org_id: str) -> list[ApiKey]:
    rows = await db.api_keys.find({"org_id": org_id, "revoked_at": None}).to_list(200)
    return [k for k in (ApiKey.from_mongo(r) for r in rows) if k]


async def save_api_key(db: Mongo, key: ApiKey) -> None:
    await db.save(db.api_keys, key)
