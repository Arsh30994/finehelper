from __future__ import annotations

from fastapi import APIRouter, Request

from finehelper_api.controllers import trust_controller
from finehelper_api.deps import AuthDep, DbDep, SettingsDep
from finehelper_api.schemas import (
    TrustBootstrapIn,
    TrustConsentIn,
    TrustExplainIn,
    TrustOnboardIn,
    TrustScanIn,
    TrustSyntheticIn,
)

router = APIRouter(prefix="/v1/trust", tags=["trust"])


@router.post("/consent")
async def consent(body: TrustConsentIn, request: Request, auth: AuthDep, db: DbDep):
    return await trust_controller.consent(db, auth, body, request)


@router.post("/onboard")
async def onboard(body: TrustOnboardIn, request: Request, auth: AuthDep, db: DbDep):
    return await trust_controller.onboard(db, auth, body, request)


@router.get("/profile")
async def profile(auth: AuthDep, db: DbDep):
    return await trust_controller.get_profile(db, auth)


@router.post("/ingest/synthetic")
async def ingest_synthetic(body: TrustSyntheticIn, request: Request, auth: AuthDep, db: DbDep):
    return await trust_controller.ingest_synthetic(db, auth, body, request)


@router.post("/bootstrap")
async def bootstrap(request: Request, auth: AuthDep, db: DbDep, settings: SettingsDep, body: TrustBootstrapIn | None = None):
    """Fill assumed profile, signals, score, and explanation in one call."""
    return await trust_controller.bootstrap(db, settings, auth, body or TrustBootstrapIn(), request)


@router.post("/score")
async def score(request: Request, auth: AuthDep, db: DbDep, settings: SettingsDep):
    return await trust_controller.score(db, settings, auth, request)


@router.get("/score/me")
async def my_score(auth: AuthDep, db: DbDep):
    return await trust_controller.my_score(db, auth)


@router.post("/explain")
async def explain(body: TrustExplainIn, request: Request, auth: AuthDep, db: DbDep, settings: SettingsDep):
    return await trust_controller.explain(db, settings, auth, body, request)


@router.get("/dashboard")
async def dashboard(auth: AuthDep, db: DbDep):
    return await trust_controller.dashboard(db, auth)


@router.post("/scan")
async def scan_qr(body: TrustScanIn, request: Request, auth: AuthDep, db: DbDep):
    """Camera/file QR → assumed spend signal (demo only)."""
    return await trust_controller.scan_qr(db, auth, body, request)


@router.post("/attest")
async def attest(request: Request, auth: AuthDep, db: DbDep, settings: SettingsDep):
    """Anchor latest Trust Score fingerprint on local ledger (+ optional EVM)."""
    return await trust_controller.attest_latest(db, settings, auth, request)


@router.get("/attest/verify")
async def attest_verify(auth: AuthDep, db: DbDep, settings: SettingsDep):
    return await trust_controller.verify_attestation(db, settings, auth)


@router.get("/attest/status")
async def attest_status(settings: SettingsDep):
    return await trust_controller.chain_status(settings)


@router.get("/attest/tx/{tx_hash}")
async def attest_tx(tx_hash: str):
    return await trust_controller.get_attestation_tx(tx_hash)
