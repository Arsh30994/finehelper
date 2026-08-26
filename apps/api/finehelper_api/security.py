"""Security helpers: rate limits, headers, password policy, path safety."""

from __future__ import annotations

import re
import secrets
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Callable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Weak / demo defaults — refused in production
INSECURE_SECRET_MARKERS = (
    "change-me",
    "dev-secret",
    "secret",
    "password",
    "123456",
)

PASSWORD_MIN_LEN = 10
PASSWORD_MAX_LEN = 128
UPI_RE = re.compile(r"^[a-zA-Z0-9.\-_]{2,64}@[a-zA-Z]{2,32}$")
MAX_BODY_BYTES = 8 * 1024 * 1024  # 8 MiB default for API bodies
MAX_UPLOAD_BYTES = 32 * 1024 * 1024  # 32 MiB local upload cap


class SlidingWindowLimiter:
    """In-memory sliding-window rate limiter (per-process; fine for demo/single node)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, *, limit: int, window_sec: float) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window_sec:
                q.popleft()
            if len(q) >= limit:
                raise HTTPException(429, "too many requests — slow down")
            q.append(now)


limiter = SlidingWindowLimiter()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return request.client.host
    return "unknown"


def enforce_auth_rate_limit(request: Request, *, email: str | None = None) -> None:
    ip = client_ip(request)
    limiter.check(f"auth:ip:{ip}", limit=30, window_sec=60)
    if email:
        limiter.check(f"auth:email:{email.lower()[:120]}", limit=10, window_sec=60)


def enforce_trust_rate_limit(request: Request, user_id: str) -> None:
    limiter.check(f"trust:user:{user_id}", limit=40, window_sec=60)
    limiter.check(f"trust:ip:{client_ip(request)}", limit=80, window_sec=60)


def validate_password_strength(password: str) -> None:
    if len(password) < PASSWORD_MIN_LEN:
        raise HTTPException(400, f"password must be at least {PASSWORD_MIN_LEN} characters")
    if len(password) > PASSWORD_MAX_LEN:
        raise HTTPException(400, f"password must be at most {PASSWORD_MAX_LEN} characters")
    if password.isspace() or not password.strip():
        raise HTTPException(400, "password cannot be blank")
    classes = sum(
        [
            any(c.islower() for c in password),
            any(c.isupper() for c in password),
            any(c.isdigit() for c in password),
            any(not c.isalnum() for c in password),
        ]
    )
    if classes < 2:
        raise HTTPException(
            400,
            "password needs at least two of: lowercase, uppercase, digit, symbol",
        )
    lowered = password.lower()
    banned = {
        "password",
        "password123",
        "password123!",
        "trustmesh",
        "finehelper",
        "1234567890",
        "qwertyuiop",
        "letmein123",
    }
    if lowered in banned:
        raise HTTPException(400, "password is too common")


def normalize_upi(upi_id: str) -> str:
    cleaned = upi_id.strip().lower()
    if not UPI_RE.match(cleaned):
        raise HTTPException(400, "invalid UPI id format")
    return cleaned


def sanitize_storage_key(key: str, org_id: str) -> str:
    """Reject path traversal and require org ownership in key."""
    decoded = key.replace("\\", "/")
    if ".." in decoded.split("/") or decoded.startswith("/") or ":" in decoded:
        raise HTTPException(400, "invalid storage key")
    parts = [p for p in decoded.split("/") if p]
    if org_id not in parts and not decoded.startswith(f"{org_id}/"):
        raise HTTPException(403, "key is not in this org prefix")
    return "/".join(parts)


def assert_secure_settings(*, app_env: str, secret_key: str, master_key: str) -> None:
    env = (app_env or "development").lower()
    if env in {"development", "dev", "test", "local"}:
        return
    if len(secret_key) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters in production")
    if len(master_key) < 32:
        raise RuntimeError("MASTER_KEY must be at least 32 characters in production")
    sk = secret_key.lower()
    mk = master_key.lower()
    if any(m in sk for m in INSECURE_SECRET_MARKERS) or any(m in mk for m in INSECURE_SECRET_MARKERS):
        raise RuntimeError("Refusing to start with default/insecure SECRET_KEY or MASTER_KEY")


def redact_dict(data: dict, *keys: str) -> dict:
    out = dict(data)
    for k in keys:
        out.pop(k, None)
    return out


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Reject obviously oversized Content-Length early
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > MAX_BODY_BYTES and not request.url.path.startswith(
            "/v1/internal/local-upload/"
        ):
            return Response("request too large", status_code=413)

        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("X-XSS-Protection", "0")
        response.headers.setdefault("Cache-Control", "no-store")
        # API is not a document origin — CSP still helps mis-rendered responses
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


def new_request_id() -> str:
    return secrets.token_hex(8)
