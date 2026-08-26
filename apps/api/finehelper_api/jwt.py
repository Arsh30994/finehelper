"""JWT access tokens for Finehelper sessions (HS256)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

ALGORITHM = "HS256"
TOKEN_TYPE = "access"


class JwtError(Exception):
    pass


def encode_access_token(
    *,
    user_id: str,
    org_id: str,
    email: str,
    role: str,
    secret: str,
    ttl_days: int = 14,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "org_id": org_id,
        "email": email,
        "role": role,
        "typ": TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(days=ttl_days),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(token: str, secret: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise JwtError("invalid token") from exc
    if payload.get("typ") != TOKEN_TYPE:
        raise JwtError("invalid token type")
    return payload
