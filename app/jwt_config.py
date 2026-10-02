from __future__ import annotations

import logging
import os
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import jwt as pyjwt
from fastapi import HTTPException, Request


JWT_ISSUER = os.environ.get("CIVITAE_JWT_ISSUER", "https://signomy.xyz")
JWT_AUDIENCE = os.environ.get("CIVITAE_JWT_AUDIENCE", "civitae-agent")

# Migration boundary for pre-scope tokens already issued before Phase 2.
# Active legacy issuers used a 24h exp, so tokens issued before this cutoff
# naturally disappear by 2026-10-04T12:00:00Z.
JWT_LEGACY_IAT_CUTOFF = int(
    datetime(2026, 10, 3, 12, 0, 0, tzinfo=UTC).timestamp()
)


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


def issue_agent_jwt(
    agent_id: str,
    name: str,
    *,
    expiry_hours: int = 24,
) -> str:
    """Issue a scoped CIVITAE agent-session JWT."""
    now = datetime.now(UTC)
    payload = {
        "sub": agent_id,
        "name": name,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(hours=expiry_hours),
        "ver": 2,
    }
    return pyjwt.encode(payload, get_kassa_jwt_secret(), algorithm="HS256")


def _decode_scoped(token: str, secret: str) -> dict:
    return pyjwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        issuer=JWT_ISSUER,
        audience=JWT_AUDIENCE,
        options={"require": ["sub", "iat", "exp", "iss", "aud"]},
    )


def _decode_legacy(token: str, secret: str) -> dict | None:
    """Accept only bounded pre-migration tokens that had no trust-domain claims."""
    try:
        claims = pyjwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={
                "require": ["sub", "iat", "exp"],
                "verify_aud": False,
                "verify_iss": False,
            },
        )
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
        return None

    # A token that attempts to carry scope claims must satisfy them through the
    # scoped verifier; never let a wrong audience/issuer fall back to legacy.
    if "iss" in claims or "aud" in claims:
        return None

    try:
        issued_at = int(claims["iat"])
    except (KeyError, TypeError, ValueError):
        return None

    if issued_at >= JWT_LEGACY_IAT_CUTOFF:
        return None
    return claims


# ── Shared JWT helpers (dual-secret rotation + scoped migration) ─────────────

def verify_jwt(token: str) -> dict | None:
    """Validate a scoped JWT, with bounded fallback for pre-migration tokens."""
    current = get_kassa_jwt_secret()
    for secret in (current, get_kassa_jwt_secret_prev()):
        if not secret:
            continue
        try:
            return _decode_scoped(token, secret)
        except pyjwt.ExpiredSignatureError:
            continue
        except pyjwt.InvalidTokenError:
            legacy = _decode_legacy(token, secret)
            if legacy is not None:
                return legacy
    return None


def extract_jwt(request: Request) -> dict | None:
    """Extract and validate JWT from Authorization: Bearer header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return verify_jwt(auth[7:].strip())


def require_jwt(request: Request) -> dict:
    """Extract JWT or raise 401. Use in endpoints that must have auth."""
    claims = extract_jwt(request)
    if not claims:
        raise HTTPException(status_code=401, detail="Valid JWT required")
    return claims
