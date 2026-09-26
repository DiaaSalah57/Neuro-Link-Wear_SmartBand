"""
NeuroLink Wear — authentication & role-based access control.

- Passwords: PBKDF2-HMAC-SHA256 (stdlib, no external deps).
- Sessions: compact HMAC-signed bearer tokens (persistent — 30 day expiry),
  stored client-side so a refresh keeps the user logged in.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from fastapi import Depends, HTTPException, Request, status

from .db import get_db, one

TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days — persistent sessions

_pbkdf2_iterations = 100_000


# ── Password hashing ─────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), _pbkdf2_iterations
    ).hex()
    return f"pbkdf2_sha256${_pbkdf2_iterations}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt, digest = stored.split("$")
        calc = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iters)
        ).hex()
        return hmac.compare_digest(calc, digest)
    except Exception:
        return False


# ── Signing secret (persisted so restarts keep sessions valid) ───────────────
def _get_secret() -> bytes:
    with get_db() as db:
        row = one(db.execute("SELECT value FROM settings WHERE key='auth_secret'"))
        if row:
            return row["value"].encode()
        secret = secrets.token_hex(32)
        db.execute(
            "INSERT OR REPLACE INTO settings(key,value) VALUES('auth_secret',?)",
            (secret,),
        )
        return secret.encode()


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# ── Token issue / verify ─────────────────────────────────────────────────────
def create_token(user: dict) -> str:
    payload = {
        "uid": user["id"],
        "role": user["role"],
        "name": user["name"],
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(_get_secret(), raw, hashlib.sha256).digest()
    return f"{_b64e(raw)}.{_b64e(sig)}"


def decode_token(token: str) -> dict | None:
    try:
        body_s, sig_s = token.split(".")
        raw, sig = _b64d(body_s), _b64d(sig_s)
        expect = hmac.new(_get_secret(), raw, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expect):
            return None
        payload = json.loads(raw)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


# ── FastAPI dependencies ─────────────────────────────────────────────────────
def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    # WebSocket clients pass ?token=
    return request.query_params.get("token")


def get_current_user(request: Request) -> dict:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired or invalid")
    with get_db() as db:
        user = one(db.execute("SELECT id,email,name,role,phone FROM users WHERE id=?", (payload["uid"],)))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return user


def require_roles(*roles: str):
    def _dep(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return _dep


require_admin = require_roles("admin")
require_staff = require_roles("admin", "caregiver")


def bootstrap_secret() -> None:
    """Force secret creation at startup so env is deterministic."""
    if not os.environ.get("NEUROLINK_SECRET"):
        _get_secret()
