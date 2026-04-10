from __future__ import annotations

import logging
import os
import secrets
from functools import lru_cache

import jwt as pyjwt
from fastapi import HTTPException, Request


@lru_cache(maxsize=1)
def get_kassa_jwt_secret() -> str:
    secret = os.environ.get("KASSA_JWT_SECRET", "") or os.environ.get("JWT_SECRET", "")
    if secret:
        return secret

    # In production (Railway), refuse to start with an ephemeral secret —
    # every deploy would invalidate all JWTs, breaking auth silently.
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        raise RuntimeError(
            "KASSA_JWT_SECRET or JWT_SECRET must be set in production. "
            "Run: railway variables set KASSA_JWT_SECRET=$(openssl rand -hex 32)"
        )

    secret = secrets.token_hex(32)
    logging.getLogger("civitae").warning(
        "KASSA_JWT_SECRET and JWT_SECRET not set -- using one ephemeral key for "
        "this process. All JWTs will expire on restart. Set one of these env vars "
        "in production."
    )
    return secret


def get_kassa_jwt_secret_prev() -> str | None:
    """Return the previous JWT secret for graceful rotation, or None."""
    return os.environ.get("KASSA_JWT_SECRET_PREV", "") or None


def clear_kassa_jwt_secret_cache() -> None:
    get_kassa_jwt_secret.cache_clear()


# ── Shared JWT helpers (dual-secret fallback) ────────────────────────────────

def verify_jwt(token: str) -> dict | None:
    """Decode a JWT, trying current secret first then previous.

    Returns claims dict on success, None on failure.
    """
    current = get_kassa_jwt_secret()
    for secret in (current, get_kassa_jwt_secret_prev()):
        if not secret:
            continue
        try:
            return pyjwt.decode(token, secret, algorithms=["HS256"])
        except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
            continue
    return None


def extract_jwt(request: Request) -> dict | None:
    """Extract and validate JWT from Authorization: Bearer header.

    Returns claims dict or None (no exception).
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return verify_jwt(auth[7:])


def require_jwt(request: Request) -> dict:
    """Extract JWT or raise 401. Use in endpoints that must have auth."""
    claims = extract_jwt(request)
    if not claims:
        raise HTTPException(status_code=401, detail="Valid JWT required")
    return claims
