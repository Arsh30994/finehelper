from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from pydantic import BaseModel, EmailStr

from finehelper_api.deps import AuthContext
from finehelper_api.schemas import doc_to_dict
from finehelper_core.crypto import hash_token
from finehelper_core.db.mongo import Mongo
from finehelper_core.models import Invite, Membership, Org, User


class InviteIn(BaseModel):
    email: EmailStr
    role: str = "member"


async def current_org(db: Mongo, auth: AuthContext) -> dict:
    count = await db.memberships.count_documents({"org_id": auth.org_id})
    return {**doc_to_dict(auth.org), "role": auth.membership.role, "member_count": count}


async def list_members(db: Mongo, auth: AuthContext) -> list[dict]:
    rows = await db.memberships.find({"org_id": auth.org_id}).to_list(500)
    out = []
    for doc in rows:
        m = Membership.from_mongo(doc)
        if not m:
            continue
        user = User.from_mongo(await db.users.find_one({"_id": m.user_id}))
        out.append({**doc_to_dict(m), "email": user.email if user else None, "name": user.name if user else None})
    return out


async def create_invite(db: Mongo, auth: AuthContext, body: InviteIn) -> dict:
    if auth.membership.role not in {"owner", "admin"}:
        raise HTTPException(403, "only owner/admin can invite")
    if body.role not in {"admin", "member", "viewer"}:
        raise HTTPException(400, "invalid role")
    raw = secrets.token_urlsafe(24)
    invite = Invite(
        org_id=auth.org_id,
        email=body.email.lower(),
        role=body.role,
        token_hash=hash_token(raw),
        invited_by=auth.user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    await db.insert(db.invites, invite)
    return {**doc_to_dict(invite), "token": raw}


async def list_invites(db: Mongo, auth: AuthContext) -> list[dict]:
    rows = await db.invites.find({"org_id": auth.org_id, "accepted_at": None}).to_list(200)
    return [doc_to_dict(Invite.from_mongo(r)) for r in rows if r]


async def accept_invite(db: Mongo, auth: AuthContext, invite_id: str) -> dict:
    invite = Invite.from_mongo(await db.invites.find_one({"_id": invite_id}))
    if not invite or invite.accepted_at:
        raise HTTPException(404, "invite not found")
    if invite.email.lower() != auth.user.email.lower():
        raise HTTPException(403, "invite email does not match this user")
    existing = await db.memberships.find_one({"org_id": invite.org_id, "user_id": auth.user_id})
    if not existing:
        await db.insert(db.memberships, Membership(org_id=invite.org_id, user_id=auth.user_id, role=invite.role))
    invite.accepted_at = datetime.now(timezone.utc)
    await db.save(db.invites, invite)
    org = Org.from_mongo(await db.orgs.find_one({"_id": invite.org_id}))
    return {"ok": True, "org": doc_to_dict(org) if org else None}
