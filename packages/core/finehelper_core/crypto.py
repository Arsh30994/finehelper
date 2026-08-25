from __future__ import annotations

import base64
import hashlib
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _aes_key(master: str) -> bytes:
    return hashlib.sha256(master.encode("utf-8")).digest()


def encrypt_secret(plaintext: str, master_key: str) -> str:
    key = _aes_key(master_key)
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt_secret(token: str, master_key: str) -> str:
    raw = base64.b64decode(token)
    nonce, ct = raw[:12], raw[12:]
    key = _aes_key(master_key)
    return AESGCM(key).decrypt(nonce, ct, None).decode("utf-8")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_api_key() -> tuple[str, str, str]:
    """Return (full_key, prefix, hash). Full key is shown once."""
    secret = secrets.token_urlsafe(32)
    full = f"fh_live_{secret}"
    prefix = full[:16]
    return full, prefix, hash_token(full)


def last4(secret: str) -> str:
    cleaned = secret.strip()
    return cleaned[-4:] if len(cleaned) >= 4 else "****"
