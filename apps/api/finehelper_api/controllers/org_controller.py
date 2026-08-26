from __future__ import annotations

from finehelper_api.deps import AuthContext
from finehelper_api.services import org_service
from finehelper_api.services.org_service import InviteIn
from finehelper_core.db.mongo import Mongo


async def current_org(db: Mongo, auth: AuthContext) -> dict:
    return await org_service.current_org(db, auth)


async def list_members(db: Mongo, auth: AuthContext) -> list[dict]:
    return await org_service.list_members(db, auth)


async def create_invite(db: Mongo, auth: AuthContext, body: InviteIn) -> dict:
    return await org_service.create_invite(db, auth, body)


async def list_invites(db: Mongo, auth: AuthContext) -> list[dict]:
    return await org_service.list_invites(db, auth)


async def accept_invite(db: Mongo, auth: AuthContext, invite_id: str) -> dict:
    return await org_service.accept_invite(db, auth, invite_id)
