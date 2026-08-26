from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request

from finehelper_api.deps import AuthContext, hash_password, verify_password_timing_safe
from finehelper_api.jwt import encode_access_token
from finehelper_api.models import ApiKey, Membership, Org, User, auth_model
from finehelper_api.schemas import (
    BiometricRegisterIn,
    BiometricUnlockIn,
    LoginIn,
    OtpVerifyIn,
    PhoneIn,
    SignupIn,
    TokenOut,
    doc_to_dict,
)
from finehelper_api.security import enforce_auth_rate_limit, validate_password_strength
from finehelper_core.crypto import new_api_key
from finehelper_core.db.mongo import Mongo
from finehelper_core.settings import Settings

OTP_TTL_MIN = 10
PHONE_RE = re.compile(r"^[6-9]\d{9}$|^(\+91)?[6-9]\d{9}$")


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


def _otp_hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _new_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _public_user(user: User) -> dict:
    data = doc_to_dict(user)
    data["email_verified"] = bool(user.email_verified_at)
    data["phone_verified"] = bool(user.phone_verified_at)
    data["biometric_enabled"] = bool(user.biometric_enabled)
    data["security"] = {
        "email_verified": bool(user.email_verified_at),
        "phone_verified": bool(user.phone_verified_at),
        "biometric_enabled": bool(user.biometric_enabled),
        "phone": user.phone,
    }
    return data


async def signup(db: Mongo, settings: Settings, body: SignupIn, request: Request | None = None) -> TokenOut:
    if request is not None:
        enforce_auth_rate_limit(request, email=body.email)
    validate_password_strength(body.password)
    if await auth_model.find_user_by_email(db, body.email.lower()):
        raise HTTPException(409, "email already registered")
    user = User(email=body.email.lower(), password_hash=hash_password(body.password), name=body.name.strip()[:120])
    slug = _slugify(body.org_name)
    if await auth_model.find_org_by_slug(db, slug):
        slug = f"{slug}-{secrets.token_hex(2)}"
    org = Org(name=body.org_name.strip()[:120], slug=slug)
    membership = Membership(org_id=org.id, user_id=user.id, role="owner")
    await auth_model.insert_user(db, user)
    await auth_model.insert_org(db, org)
    await auth_model.insert_membership(db, membership)
    token = encode_access_token(
        user_id=user.id,
        org_id=org.id,
        email=user.email,
        role=membership.role,
        secret=settings.secret_key,
        ttl_days=settings.jwt_ttl_days,
    )
    return TokenOut(token=token, user=_public_user(user), org=doc_to_dict(org))


async def login(db: Mongo, settings: Settings, body: LoginIn, request: Request | None = None) -> TokenOut:
    email = body.email.lower()
    if request is not None:
        enforce_auth_rate_limit(request, email=email)
    user = await auth_model.find_user_by_email(db, email)
    if not verify_password_timing_safe(body.password, user.password_hash if user else None):
        raise HTTPException(401, "invalid credentials")
    assert user is not None
    membership = await auth_model.find_membership(db, user_id=user.id)
    org = await auth_model.find_org_by_id(db, membership.org_id) if membership else None
    if not membership or not org:
        raise HTTPException(403, "no organization")
    token = encode_access_token(
        user_id=user.id,
        org_id=org.id,
        email=user.email,
        role=membership.role,
        secret=settings.secret_key,
        ttl_days=settings.jwt_ttl_days,
    )
    return TokenOut(token=token, user=_public_user(user), org=doc_to_dict(org))


def me(auth: AuthContext) -> dict:
    return {
        "user": _public_user(auth.user),
        "org": doc_to_dict(auth.org),
        "role": auth.membership.role,
        "via": auth.via,
    }


async def create_api_key(db: Mongo, auth: AuthContext, name: str = "cli") -> dict:
    safe_name = (name or "cli").strip()[:64] or "cli"
    full, prefix, hashed = new_api_key()
    row = ApiKey(org_id=auth.org_id, user_id=auth.user_id, name=safe_name, prefix=prefix, key_hash=hashed)
    await auth_model.insert_api_key(db, row)
    return {"id": row.id, "key": full, "prefix": prefix, "name": safe_name}


async def list_api_keys(db: Mongo, auth: AuthContext) -> list[dict]:
    rows = await auth_model.list_api_keys(db, auth.org_id)
    return [doc_to_dict(r) for r in rows]


async def _fresh_user(db: Mongo, auth: AuthContext) -> User:
    user = await auth_model.find_user_by_id(db, auth.user_id)
    if not user:
        raise HTTPException(401, "invalid session")
    return user


async def send_email_otp(db: Mongo, settings: Settings, auth: AuthContext, request: Request | None = None) -> dict:
    if request is not None:
        enforce_auth_rate_limit(request, email=auth.user.email)
    user = await _fresh_user(db, auth)
    code = _new_otp()
    user.email_otp_hash = _otp_hash(code)
    user.email_otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MIN)
    await auth_model.save_user(db, user)
    out: dict = {
        "ok": True,
        "channel": "email",
        "destination": user.email,
        "expires_in_sec": OTP_TTL_MIN * 60,
        "message": "OTP generated for email verification (demo — no real email sent).",
    }
    if not settings.is_production:
        out["demo_otp"] = code
    return out


async def verify_email_otp(db: Mongo, auth: AuthContext, body: OtpVerifyIn, request: Request | None = None) -> dict:
    if request is not None:
        enforce_auth_rate_limit(request, email=auth.user.email)
    user = await _fresh_user(db, auth)
    if not user.email_otp_hash or not user.email_otp_expires_at:
        raise HTTPException(400, "request an email OTP first")
    if user.email_otp_expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "OTP expired — request a new one")
    if not hmac.compare_digest(user.email_otp_hash, _otp_hash(body.code.strip())):
        raise HTTPException(400, "invalid OTP")
    user.email_verified_at = datetime.now(timezone.utc)
    user.email_otp_hash = None
    user.email_otp_expires_at = None
    await auth_model.save_user(db, user)
    return {"ok": True, "email_verified": True, "user": _public_user(user)}


async def set_phone(db: Mongo, auth: AuthContext, body: PhoneIn) -> dict:
    raw = re.sub(r"[\s\-]", "", body.phone)
    if raw.startswith("+91"):
        raw = raw[3:]
    if raw.startswith("91") and len(raw) == 12:
        raw = raw[2:]
    if not PHONE_RE.match(raw) and not (raw.isdigit() and len(raw) == 10):
        raise HTTPException(400, "enter a valid 10-digit Indian mobile number")
    user = await _fresh_user(db, auth)
    user.phone = raw
    user.phone_verified_at = None
    await auth_model.save_user(db, user)
    return {"ok": True, "phone": raw, "user": _public_user(user)}


async def send_phone_otp(db: Mongo, settings: Settings, auth: AuthContext, request: Request | None = None) -> dict:
    if request is not None:
        enforce_auth_rate_limit(request, email=auth.user.email)
    user = await _fresh_user(db, auth)
    if not user.phone:
        raise HTTPException(400, "set a phone number first")
    code = _new_otp()
    user.phone_otp_hash = _otp_hash(code)
    user.phone_otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_TTL_MIN)
    await auth_model.save_user(db, user)
    out: dict = {
        "ok": True,
        "channel": "sms",
        "destination": f"+91******{user.phone[-4:]}",
        "expires_in_sec": OTP_TTL_MIN * 60,
        "message": "OTP generated for phone verification (demo — no real SMS sent).",
    }
    if not settings.is_production:
        out["demo_otp"] = code
    return out


async def verify_phone_otp(db: Mongo, auth: AuthContext, body: OtpVerifyIn, request: Request | None = None) -> dict:
    if request is not None:
        enforce_auth_rate_limit(request, email=auth.user.email)
    user = await _fresh_user(db, auth)
    if not user.phone_otp_hash or not user.phone_otp_expires_at:
        raise HTTPException(400, "request a phone OTP first")
    if user.phone_otp_expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "OTP expired — request a new one")
    if not hmac.compare_digest(user.phone_otp_hash, _otp_hash(body.code.strip())):
        raise HTTPException(400, "invalid OTP")
    user.phone_verified_at = datetime.now(timezone.utc)
    user.phone_otp_hash = None
    user.phone_otp_expires_at = None
    await auth_model.save_user(db, user)
    return {"ok": True, "phone_verified": True, "user": _public_user(user)}


async def biometric_status(db: Mongo, auth: AuthContext) -> dict:
    user = await _fresh_user(db, auth)
    challenge = secrets.token_urlsafe(32)
    user.webauthn_challenge = challenge
    user.webauthn_challenge_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    await auth_model.save_user(db, user)
    return {
        "challenge": challenge,
        "rp_id": "localhost",
        "user_id": user.id,
        "biometric_enabled": bool(user.biometric_enabled),
        "has_credential": bool(user.webauthn_credential_id),
    }


async def biometric_register(db: Mongo, auth: AuthContext, body: BiometricRegisterIn) -> dict:
    user = await _fresh_user(db, auth)
    if body.demo:
        # Hackathon / unsupported-browser path — still requires an explicit user gesture
        user.biometric_enabled = True
        user.webauthn_credential_id = user.webauthn_credential_id or f"demo-{user.id[:8]}"
        user.webauthn_public_key = user.webauthn_public_key or "demo-local-unlock"
        user.last_biometric_at = datetime.now(timezone.utc)
        await auth_model.save_user(db, user)
        return {"ok": True, "biometric_enabled": True, "mode": "demo", "user": _public_user(user)}

    if not user.webauthn_challenge or not user.webauthn_challenge_expires_at:
        raise HTTPException(400, "request a biometric challenge first")
    if user.webauthn_challenge_expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "biometric challenge expired")
    user.webauthn_credential_id = body.credential_id[:512]
    user.webauthn_public_key = body.public_key[:4096]
    user.biometric_enabled = True
    user.webauthn_challenge = None
    user.webauthn_challenge_expires_at = None
    user.last_biometric_at = datetime.now(timezone.utc)
    await auth_model.save_user(db, user)
    return {"ok": True, "biometric_enabled": True, "mode": "webauthn", "user": _public_user(user)}


async def biometric_unlock(db: Mongo, auth: AuthContext, body: BiometricUnlockIn) -> dict:
    user = await _fresh_user(db, auth)
    if not user.biometric_enabled:
        raise HTTPException(400, "enable fingerprint first")
    if body.demo:
        user.last_biometric_at = datetime.now(timezone.utc)
        await auth_model.save_user(db, user)
        return {"ok": True, "unlocked": True, "mode": "demo", "user": _public_user(user)}
    if body.credential_id and user.webauthn_credential_id:
        if not hmac.compare_digest(body.credential_id, user.webauthn_credential_id):
            raise HTTPException(401, "biometric credential mismatch")
    user.last_biometric_at = datetime.now(timezone.utc)
    await auth_model.save_user(db, user)
    return {"ok": True, "unlocked": True, "mode": "webauthn", "user": _public_user(user)}


async def security_status(db: Mongo, auth: AuthContext) -> dict:
    user = await _fresh_user(db, auth)
    return {
        "email": user.email,
        "phone": user.phone,
        "email_verified": bool(user.email_verified_at),
        "phone_verified": bool(user.phone_verified_at),
        "biometric_enabled": bool(user.biometric_enabled),
        "last_biometric_at": user.last_biometric_at.isoformat() if user.last_biometric_at else None,
        "demo": True,
    }
