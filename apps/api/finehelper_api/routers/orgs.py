from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from finehelper_api.deps import AuthDep, SessionDep
from finehelper_api.schemas import orm_to_dict
from finehelper_core.crypto import hash_token
from finehelper_core.db.models import Invite, Membership, Org, User

router = APIRouter(prefix="/v1", tags=["orgs"])


class InviteIn(BaseModel):
    email: EmailStr
    role: str = "member"


@router.get("/orgs")
async def current_org(auth: AuthDep, session: SessionDep):
    members = (
        await session.scalars(select(Membership).where(Membership.org_id == auth.org_id))
    ).all()
    return {**orm_to_dict(auth.org), "role": auth.membership.role, "member_count": len(members)}


@router.get("/orgs/members")
async def list_members(auth: AuthDep, session: SessionDep):
    rows = (await session.scalars(select(Membership).where(Membership.org_id == auth.org_id))).all()
    out = []
    for m in rows:
        user = await session.get(User, m.user_id)
        out.append({**orm_to_dict(m), "email": user.email if user else None, "name": user.name if user else None})
    return out


@router.post("/invites")
async def create_invite(body: InviteIn, auth: AuthDep, session: SessionDep):
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
    session.add(invite)
    await session.flush()
    return {**orm_to_dict(invite), "token": raw}


@router.get("/invites")
async def list_invites(auth: AuthDep, session: SessionDep):
    rows = (
        await session.scalars(select(Invite).where(Invite.org_id == auth.org_id, Invite.accepted_at.is_(None)))
    ).all()
    return [orm_to_dict(r) for r in rows]


@router.post("/invites/{invite_id}/accept")
async def accept_invite(invite_id: UUID, auth: AuthDep, session: SessionDep):
    invite = await session.get(Invite, invite_id)
    if not invite or invite.accepted_at:
        raise HTTPException(404, "invite not found")
    if invite.email.lower() != auth.user.email.lower():
        raise HTTPException(403, "invite email does not match this user")
    existing = await session.scalar(
        select(Membership).where(Membership.org_id == invite.org_id, Membership.user_id == auth.user_id)
    )
    if not existing:
        session.add(Membership(org_id=invite.org_id, user_id=auth.user_id, role=invite.role))
    invite.accepted_at = datetime.now(timezone.utc)
    org = await session.get(Org, invite.org_id)
    return {"ok": True, "org": orm_to_dict(org) if org else None}
