#!/usr/bin/env python3
"""Seed a stage-ready TrustMesh demo user with consent, signals, and score."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT / "packages" / "core"))

from finehelper_api.controllers import trust_controller
from finehelper_api.deps import AuthContext, hash_password
from finehelper_api.ml.trust.model import get_trust_model
from finehelper_api.schemas import TrustConsentIn, TrustOnboardIn, TrustSyntheticIn
from finehelper_core.db import connect_mongo, ensure_indexes
from finehelper_core.models import Membership, Org, User
from finehelper_core.settings import get_settings

DEMO_EMAIL = "demo@trustmesh.app"
DEMO_PASSWORD = "Demo!Trust94"
DEMO_NAME = "Demo Kirana"


async def main() -> None:
    settings = get_settings()
    get_trust_model(settings.trust_model_path)
    db = connect_mongo(settings)
    await db.ping()
    await ensure_indexes(db)

    existing = await db.users.find_one({"email": DEMO_EMAIL})
    if existing:
        user = User.from_mongo(existing)
        user.password_hash = hash_password(DEMO_PASSWORD)
        user.touch()
        await db.users.replace_one({"_id": user.id}, user.to_mongo())
        mem_doc = await db.memberships.find_one({"user_id": user.id})
        if not mem_doc:
            raise SystemExit("demo user exists without membership")
        mem = Membership.from_mongo(mem_doc)
        org = Org.from_mongo(await db.orgs.find_one({"_id": mem.org_id}))
        if not org:
            raise SystemExit("demo org missing")
        print(f"Reusing demo user {DEMO_EMAIL} ({user.id})")
    else:
        org = Org(name="TrustMesh Demo", slug="trustmesh-demo")
        await db.insert(db.orgs, org)
        user = User(email=DEMO_EMAIL, name=DEMO_NAME, password_hash=hash_password(DEMO_PASSWORD))
        await db.insert(db.users, user)
        mem = Membership(org_id=org.id, user_id=user.id, role="owner")
        await db.insert(db.memberships, mem)
        print(f"Created demo user {DEMO_EMAIL}")

    auth = AuthContext(user=user, org=org, membership=mem, via="seed")
    await trust_controller.consent(db, auth, TrustConsentIn())
    await trust_controller.onboard(
        db,
        auth,
        TrustOnboardIn(
            upi_id="demo.kirana@oksbi",
            bank_name="Demo Bank",
            bank_account_last4="4242",
            occupation="kirana",
        ),
    )
    await trust_controller.ingest_synthetic(
        db,
        auth,
        TrustSyntheticIn(months=6, seed=30994, occupation="kirana", quality="good"),
    )
    scored = await trust_controller.score(db, settings, auth)
    print(f"Trust score ready: {scored.get('score')}/100")
    print(f"Login -> {DEMO_EMAIL} / {DEMO_PASSWORD}")
    db.close()


if __name__ == "__main__":
    asyncio.run(main())
