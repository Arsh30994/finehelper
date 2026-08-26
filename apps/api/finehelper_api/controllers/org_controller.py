from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from finehelper_api.deps import AuthContext
from finehelper_api.models import Invite, Membership, auth_model, org_model
from finehelper_api.schemas import InviteIn, doc_to_dict
from finehelper_core.crypto import hash_token
from finehelper_core.db.mongo import Mongo


async def current_org(db: Mongo, auth: AuthContext) -> dict:
    count = await org_model.count_members(db, auth.org_id)
    return {**doc_to_dict(auth.org), "role": auth.membership.role, "member_count": count}


async def list_members(db: Mongo, auth: AuthContext) -> list[dict]:
    out = []
    for m in await org_model.list_memberships(db, auth.org_id):
        user = await org_model.find_user(db, m.user_id)
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
    await org_model.insert_invite(db, invite)
    return {**doc_to_dict(invite), "token": raw}


async def list_invites(db: Mongo, auth: AuthContext) -> list[dict]:
    return [doc_to_dict(i) for i in await org_model.list_open_invites(db, auth.org_id)]


async def accept_invite(db: Mongo, auth: AuthContext, invite_id: str) -> dict:
    invite = await org_model.find_invite(db, invite_id)
    if not invite or invite.accepted_at:
        raise HTTPException(404, "invite not found")
    if invite.email.lower() != auth.user.email.lower():
        raise HTTPException(403, "invite email does not match this user")
    existing = await org_model.find_membership(db, invite.org_id, auth.user_id)
    if not existing:
        await org_model.insert_membership(db, Membership(org_id=invite.org_id, user_id=auth.user_id, role=invite.role))
    invite.accepted_at = datetime.now(timezone.utc)
    await org_model.save_invite(db, invite)
    org = await auth_model.find_org_by_id(db, invite.org_id)
    return {"ok": True, "org": doc_to_dict(org) if org else None}
