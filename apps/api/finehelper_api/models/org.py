"""Org / invite Mongo repositories."""

from __future__ import annotations

from finehelper_core.db.mongo import Mongo
from finehelper_core.models import Invite, Membership, User


async def count_members(db: Mongo, org_id: str) -> int:
    return await db.memberships.count_documents({"org_id": org_id})


async def list_memberships(db: Mongo, org_id: str) -> list[Membership]:
    rows = await db.memberships.find({"org_id": org_id}).to_list(500)
    return [m for m in (Membership.from_mongo(r) for r in rows) if m]


async def find_user(db: Mongo, user_id: str) -> User | None:
    return User.from_mongo(await db.users.find_one({"_id": user_id}))


async def insert_invite(db: Mongo, invite: Invite) -> Invite:
    await db.insert(db.invites, invite)
    return invite


async def list_open_invites(db: Mongo, org_id: str) -> list[Invite]:
    rows = await db.invites.find({"org_id": org_id, "accepted_at": None}).to_list(200)
    return [i for i in (Invite.from_mongo(r) for r in rows) if i]


async def find_invite(db: Mongo, invite_id: str) -> Invite | None:
    return Invite.from_mongo(await db.invites.find_one({"_id": invite_id}))


async def save_invite(db: Mongo, invite: Invite) -> None:
    await db.save(db.invites, invite)


async def insert_membership(db: Mongo, membership: Membership) -> Membership:
    await db.insert(db.memberships, membership)
    return membership


async def find_membership(db: Mongo, org_id: str, user_id: str) -> Membership | None:
    return Membership.from_mongo(await db.memberships.find_one({"org_id": org_id, "user_id": user_id}))
