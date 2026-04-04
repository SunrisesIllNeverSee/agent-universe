from __future__ import annotations

import logging
import os
import secrets
from functools import lru_cache


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


def clear_kassa_jwt_secret_cache() -> None:
    get_kassa_jwt_secret.cache_clear()
