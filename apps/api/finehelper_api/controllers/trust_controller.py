from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, Request

from finehelper_api.blockchain import apply_attestation_to_score, attest_score, verify_score_attestation
from finehelper_api.blockchain import local_chain
from finehelper_api.deps import AuthContext
from finehelper_api.ml.trust.explain import explain_score
from finehelper_api.ml.trust.model import get_trust_model
from finehelper_api.ml.trust.qr import parse_qr_payload, scan_to_signal
from finehelper_api.ml.trust.synthetic import assumed_persona, generate_signal_batch
from finehelper_api.models import trust as trust_model
from finehelper_api.schemas import (
    TrustBootstrapIn,
    TrustConsentIn,
    TrustExplainIn,
    TrustOnboardIn,
    TrustScanIn,
    TrustSyntheticIn,
    doc_to_dict,
)
from finehelper_api.security import enforce_trust_rate_limit, normalize_upi, redact_dict
from finehelper_core.db.mongo import Mongo
from finehelper_core.models import TrustProfile, TrustScore, TrustSignalBatch
from finehelper_core.settings import Settings


ALLOWED_SCOPES = frozenset({"upi_6m", "bills", "recharges", "peers", "merchants"})
ALLOWED_OCCUPATIONS = frozenset({"kirana", "gig", "vendor", "farmer", "other"})


def _anchor_score(settings: Settings, row: TrustScore, batch: TrustSignalBatch | None) -> TrustScore:
    attestation = attest_score(settings, row, batch)
    return apply_attestation_to_score(row, attestation)


def _public_score(row: TrustScore) -> dict:
    """Hide raw feature vector from clients — factors + score are enough."""
    return redact_dict(doc_to_dict(row), "features")


def _mask_upi(upi: str | None) -> str | None:
    if not upi or "@" not in upi:
        return upi
    local, host = upi.split("@", 1)
    if len(local) <= 2:
        return f"**@{host}"
    return f"{local[:2]}***@{host}"


def _public_profile(profile: TrustProfile | None) -> dict | None:
    if not profile:
        return None
    data = doc_to_dict(profile)
    data["upi_id"] = _mask_upi(profile.upi_id)
    return data


async def consent(db: Mongo, auth: AuthContext, body: TrustConsentIn, request: Request | None = None) -> dict:
    if request is not None:
        enforce_trust_rate_limit(request, auth.user_id)
    scopes = [s for s in (body.scopes or list(ALLOWED_SCOPES)) if s in ALLOWED_SCOPES]
    if not scopes:
        raise HTTPException(400, "at least one valid consent scope required")
    profile = await trust_model.find_profile(db, auth.user_id)
    if not profile:
        profile = TrustProfile(user_id=auth.user_id, org_id=auth.org_id)
    elif profile.org_id != auth.org_id:
        raise HTTPException(403, "profile org mismatch")
    profile.consent_at = datetime.now(timezone.utc)
    profile.consent_scopes = scopes
    await trust_model.upsert_profile(db, profile)
    return _public_profile(profile) or {}


async def onboard(db: Mongo, auth: AuthContext, body: TrustOnboardIn, request: Request | None = None) -> dict:
    if request is not None:
        enforce_trust_rate_limit(request, auth.user_id)
    occupation = (body.occupation or "kirana").lower()
    if occupation not in ALLOWED_OCCUPATIONS:
        raise HTTPException(400, "invalid occupation")
    if not body.bank_account_last4.isdigit():
        raise HTTPException(400, "bank_account_last4 must be 4 digits")
    profile = await trust_model.find_profile(db, auth.user_id)
    if not profile:
        profile = TrustProfile(user_id=auth.user_id, org_id=auth.org_id)
    elif profile.org_id != auth.org_id:
        raise HTTPException(403, "profile org mismatch")
    profile.upi_id = normalize_upi(body.upi_id)
    profile.bank_name = body.bank_name.strip()[:80]
    profile.bank_account_last4 = body.bank_account_last4
    profile.occupation = occupation
    if not profile.consent_at:
        raise HTTPException(400, "grant consent before onboarding")
    await trust_model.upsert_profile(db, profile)
    return _public_profile(profile) or {}


async def get_profile(db: Mongo, auth: AuthContext) -> dict:
    profile = await trust_model.find_profile(db, auth.user_id)
    return _public_profile(profile) or {}


def _normalize_quality(quality: str) -> str:
    q = (quality or "good").lower()
    if q in {"good", "strong"}:
        return "good"
    if q in {"thin", "weak"}:
        return "thin"
    return "mixed"


async def ingest_synthetic(
    db: Mongo, auth: AuthContext, body: TrustSyntheticIn, request: Request | None = None
) -> dict:
    if request is not None:
        enforce_trust_rate_limit(request, auth.user_id)
    profile = await trust_model.find_profile(db, auth.user_id)
    if not profile or not profile.consent_at:
        raise HTTPException(400, "grant consent before ingesting signals")
    occupation = body.occupation or profile.occupation or "kirana"
    if occupation not in ALLOWED_OCCUPATIONS:
        raise HTTPException(400, "invalid occupation")
    raw = generate_signal_batch(
        seed=body.seed,
        months=body.months,
        occupation=occupation,
        quality=_normalize_quality(body.quality),
    )
    batch = TrustSignalBatch(
        user_id=auth.user_id,
        org_id=auth.org_id,
        months=raw["months"],
        transactions=raw["transactions"],
        bills=raw["bills"],
        recharges=raw["recharges"],
        peers=raw["peers"],
        merchants=raw["merchants"],
    )
    await trust_model.insert_signals(db, batch)
    return {
        "id": batch.id,
        "months": batch.months,
        "txn_count": len(batch.transactions),
        "bill_count": len(batch.bills),
        "recharge_count": len(batch.recharges),
        "peer_count": len(batch.peers),
        "merchants": batch.merchants,
        "synthetic": True,
    }


async def score(db: Mongo, settings: Settings, auth: AuthContext, request: Request | None = None) -> dict:
    if request is not None:
        enforce_trust_rate_limit(request, auth.user_id)
    profile = await trust_model.find_profile(db, auth.user_id)
    if not profile or not profile.consent_at:
        raise HTTPException(400, "grant consent before scoring")
    batch = await trust_model.latest_signals(db, auth.user_id)
    if not batch:
        raise HTTPException(400, "ingest synthetic signals before scoring")
    if batch.org_id != auth.org_id:
        raise HTTPException(403, "signal batch org mismatch")
    payload = {
        "months": batch.months,
        "transactions": batch.transactions,
        "bills": batch.bills,
        "recharges": batch.recharges,
        "peers": batch.peers,
        "merchants": batch.merchants,
    }
    model = get_trust_model(settings.trust_model_path)
    result = model.predict(payload)
    row = TrustScore(
        user_id=auth.user_id,
        org_id=auth.org_id,
        score=result["score"],
        factors=result["factors"],
        eligibility_min=result["eligibility_min"],
        eligibility_max=result["eligibility_max"],
        features=result["features"],
        model_version=result["model_version"],
    )
    row = _anchor_score(settings, row, batch)
    await trust_model.insert_score(db, row)
    return _public_score(row)


def _signals_summary(batch: TrustSignalBatch | None) -> dict | None:
    if not batch:
        return None
    return {
        "txn_count": len(batch.transactions),
        "bill_count": len(batch.bills),
        "recharge_count": len(batch.recharges),
        "peers": batch.peers,
        "merchants": batch.merchants,
        "recent_txns": batch.transactions[-12:],
        "bills": batch.bills,
        "recharges": batch.recharges[-8:],
    }


async def my_score(db: Mongo, auth: AuthContext) -> dict:
    row = await trust_model.latest_score(db, auth.user_id)
    if not row:
        raise HTTPException(404, "no score yet")
    batch = await trust_model.latest_signals(db, auth.user_id)
    profile = await trust_model.find_profile(db, auth.user_id)
    return {
        **_public_score(row),
        "profile": _public_profile(profile),
        "signals_summary": _signals_summary(batch),
    }


async def explain(
    db: Mongo, settings: Settings, auth: AuthContext, body: TrustExplainIn, request: Request | None = None
) -> dict:
    if request is not None:
        enforce_trust_rate_limit(request, auth.user_id)
    row = await trust_model.latest_score(db, auth.user_id)
    if not row:
        raise HTTPException(404, "no score yet")
    lang = "hi" if body.lang.lower().startswith("hi") else "en"
    text = await explain_score(
        settings,
        score=row.score,
        factors=row.factors,
        eligibility_min=row.eligibility_min,
        eligibility_max=row.eligibility_max,
        lang=lang,
    )
    # Cap stored explanation length
    text = text[:2000]
    row.explanation = text
    row.explanation_lang = lang
    await db.trust_scores.replace_one({"_id": row.id}, row.to_mongo())
    return {"explanation": text, "lang": row.explanation_lang, "score_id": row.id}


async def dashboard(db: Mongo, auth: AuthContext) -> dict:
    profile = await trust_model.find_profile(db, auth.user_id)
    score_row = await trust_model.latest_score(db, auth.user_id)
    batch = await trust_model.latest_signals(db, auth.user_id)
    return {
        "profile": _public_profile(profile),
        "score": _public_score(score_row) if score_row else None,
        "signals_summary": _signals_summary(batch),
        "demo": True,
        "assumed": True,
    }


async def bootstrap(
    db: Mongo,
    settings: Settings,
    auth: AuthContext,
    body: TrustBootstrapIn | None = None,
    request: Request | None = None,
) -> dict:
    """
    One-shot fill with assumed data: consent → onboard → synthetic ingest → score → explain.
    Idempotent unless force=True.
    """
    if request is not None:
        enforce_trust_rate_limit(request, auth.user_id)
    opts = body or TrustBootstrapIn()
    occupation = (opts.occupation or "kirana").lower()
    if occupation not in ALLOWED_OCCUPATIONS:
        occupation = "kirana"
    quality = _normalize_quality(opts.quality)
    persona = assumed_persona(occupation)

    existing_score = await trust_model.latest_score(db, auth.user_id)
    existing_batch = await trust_model.latest_signals(db, auth.user_id)
    if existing_score and existing_batch and not opts.force:
        dash = await dashboard(db, auth)
        return {**dash, "bootstrapped": False, "message": "Assumed data already present"}

    # Consent + assumed persona onboard
    profile = await trust_model.find_profile(db, auth.user_id)
    if not profile:
        profile = TrustProfile(user_id=auth.user_id, org_id=auth.org_id)
    profile.consent_at = profile.consent_at or datetime.now(timezone.utc)
    profile.consent_scopes = list(ALLOWED_SCOPES)
    profile.upi_id = normalize_upi(persona["upi_id"])
    profile.bank_name = persona["bank_name"]
    profile.bank_account_last4 = persona["bank_account_last4"]
    profile.occupation = occupation
    await trust_model.upsert_profile(db, profile)

    raw = generate_signal_batch(
        seed=opts.seed if opts.seed is not None else 30994,
        months=opts.months,
        occupation=occupation,
        quality=quality,
    )
    batch = TrustSignalBatch(
        user_id=auth.user_id,
        org_id=auth.org_id,
        months=raw["months"],
        transactions=raw["transactions"],
        bills=raw["bills"],
        recharges=raw["recharges"],
        peers=raw["peers"],
        merchants=raw["merchants"],
    )
    await trust_model.insert_signals(db, batch)

    model = get_trust_model(settings.trust_model_path)
    result = model.predict(
        {
            "months": batch.months,
            "transactions": batch.transactions,
            "bills": batch.bills,
            "recharges": batch.recharges,
            "peers": batch.peers,
            "merchants": batch.merchants,
        }
    )
    row = TrustScore(
        user_id=auth.user_id,
        org_id=auth.org_id,
        score=result["score"],
        factors=result["factors"],
        eligibility_min=result["eligibility_min"],
        eligibility_max=result["eligibility_max"],
        features=result["features"],
        model_version=result["model_version"],
    )
    lang = "hi" if opts.lang.lower().startswith("hi") else "en"
    text = await explain_score(
        settings,
        score=row.score,
        factors=row.factors,
        eligibility_min=row.eligibility_min,
        eligibility_max=row.eligibility_max,
        lang=lang,
    )
    row.explanation = text[:2000]
    row.explanation_lang = lang
    row = _anchor_score(settings, row, batch)
    await trust_model.insert_score(db, row)

    dash = await dashboard(db, auth)
    return {
        **dash,
        "bootstrapped": True,
        "persona": persona,
        "message": "Filled with assumed synthetic UPI/bill data for demo",
    }


async def attest_latest(
    db: Mongo, settings: Settings, auth: AuthContext, request: Request | None = None
) -> dict:
    """Re-anchor the latest score on the local ledger (and EVM if configured)."""
    if request is not None:
        enforce_trust_rate_limit(request, auth.user_id)
    row = await trust_model.latest_score(db, auth.user_id)
    if not row:
        raise HTTPException(404, "no score yet")
    batch = await trust_model.latest_signals(db, auth.user_id)
    row = _anchor_score(settings, row, batch)
    await db.trust_scores.replace_one({"_id": row.id}, row.to_mongo())
    return {
        "ok": True,
        "score": _public_score(row),
        "attestation": {
            "network": row.chain_network,
            "tx_hash": row.chain_tx_hash,
            "block_number": row.chain_block,
            "explorer_url": row.chain_explorer_url,
            "score_hash": row.score_hash,
            "signals_root": row.signals_root,
            "mode": row.chain_mode,
        },
        "demo": True,
    }


async def verify_attestation(db: Mongo, settings: Settings, auth: AuthContext) -> dict:
    row = await trust_model.latest_score(db, auth.user_id)
    if not row:
        raise HTTPException(404, "no score yet")
    if not row.chain_tx_hash:
        # Auto-attest older scores that predate chain support
        batch = await trust_model.latest_signals(db, auth.user_id)
        row = _anchor_score(settings, row, batch)
        await db.trust_scores.replace_one({"_id": row.id}, row.to_mongo())
    batch = await trust_model.latest_signals(db, auth.user_id)
    return verify_score_attestation(settings, row, batch)


async def get_attestation_tx(tx_hash: str) -> dict:
    block = local_chain.find_by_tx(tx_hash)
    if not block:
        raise HTTPException(404, "attestation tx not found on local ledger")
    return {"ok": True, "network": "local", "block": block, "demo": True}


async def chain_status(settings: Settings) -> dict:
    ledger = local_chain.verify_chain()
    return {
        "ok": True,
        "local_ledger": ledger,
        "evm_configured": bool(
            settings.chain_rpc_url and settings.chain_private_key and settings.chain_contract_address
        ),
        "network": settings.chain_network,
        "contract": settings.chain_contract_address,
        "demo": True,
        "note": "Scores are hashed off-chain; only fingerprints are anchored.",
    }


async def scan_qr(db: Mongo, auth: AuthContext, body: TrustScanIn, request: Request | None = None) -> dict:
    """Attach a scanned QR as an assumed spend signal (demo only — no settlement)."""
    if request is not None:
        enforce_trust_rate_limit(request, auth.user_id)
    profile = await trust_model.find_profile(db, auth.user_id)
    if not profile or not profile.consent_at:
        raise HTTPException(400, "grant consent before scanning")
    try:
        parsed = parse_qr_payload(body.raw)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    signal = scan_to_signal(parsed, amount_override=body.amount_override)
    batch = await trust_model.latest_signals(db, auth.user_id)
    if not batch:
        # Seed a thin assumed batch so scans have a home
        raw = generate_signal_batch(seed=7, months=6, occupation=profile.occupation or "kirana", quality="mixed")
        batch = TrustSignalBatch(
            user_id=auth.user_id,
            org_id=auth.org_id,
            months=raw["months"],
            transactions=raw["transactions"],
            bills=raw["bills"],
            recharges=raw["recharges"],
            peers=raw["peers"],
            merchants=raw["merchants"],
        )
        await trust_model.insert_signals(db, batch)

    batch.transactions = list(batch.transactions or []) + [signal["transaction"]]
    merchants = list(batch.merchants or [])
    mname = signal["merchant"]["name"]
    existing = next((m for m in merchants if m.get("name") == mname), None)
    if existing:
        existing["txn_count"] = int(existing.get("txn_count") or 0) + 1
        existing["spend_total"] = float(existing.get("spend_total") or 0) + float(signal["transaction"]["amount"])
    else:
        merchants.append(
            {
                **signal["merchant"],
                "txn_count": 1,
                "spend_total": signal["transaction"]["amount"],
            }
        )
    batch.merchants = merchants
    batch.touch()
    await db.trust_signal_batches.replace_one({"_id": batch.id}, batch.to_mongo())

    return {
        "ok": True,
        "demo": True,
        "settlement": False,
        "message": "Logged as assumed spend signal — no money moved.",
        "parsed": signal["parsed"],
        "transaction": signal["transaction"],
        "merchant": signal["merchant"],
    }
