from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from finehelper_api.controllers import org_controller
from finehelper_api.deps import AuthDep, DbDep
from finehelper_api.schemas import InviteIn

router = APIRouter(prefix="/v1", tags=["orgs"])


@router.get("/orgs")
async def current_org(auth: AuthDep, db: DbDep):
    return await org_controller.current_org(db, auth)


@router.get("/orgs/members")
async def list_members(auth: AuthDep, db: DbDep):
    return await org_controller.list_members(db, auth)


@router.post("/invites")
async def create_invite(body: InviteIn, auth: AuthDep, db: DbDep):
    return await org_controller.create_invite(db, auth, body)


@router.get("/invites")
async def list_invites(auth: AuthDep, db: DbDep):
    return await org_controller.list_invites(db, auth)


@router.post("/invites/{invite_id}/accept")
async def accept_invite(invite_id: UUID, auth: AuthDep, db: DbDep):
    return await org_controller.accept_invite(db, auth, str(invite_id))
