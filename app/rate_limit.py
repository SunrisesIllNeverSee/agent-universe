"""Shared in-process rate limiting for the current single-worker deployment.

The store is intentionally process-local. Production remains single-worker until
authoritative state storage is redesigned, so persistence/Redis is not required
for correctness today.
"""
from __future__ import annotations

import hashlib
import os
import time as _time
from ipaddress import ip_address

from fastapi import HTTPException, Request


RATE_STORES: dict[str, dict[str, list[float]]] = {}


def client_ip(request: Request) -> str:
    """Use Railway HTTP ingress's remote address; forwarded chains are not identity."""
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        real_ip = request.headers.get("x-real-ip", "").strip()
        try:
            return str(ip_address(real_ip))
        except ValueError:
            pass
    elif os.environ.get("CIVITAE_DEV_MODE") == "1":
        # Explicit local development/test compatibility; never active on Railway.
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        try:
            return str(ip_address(forwarded))
        except ValueError:
            pass
    return request.client.host if request.client else "unknown"


def client_fingerprint(request: Request) -> str:
    return hashlib.sha256(client_ip(request).encode()).hexdigest()[:16]


def check_rate_limit(
    request: Request,
    bucket_name: str,
    max_hits: int,
    window_s: int = 3600,
) -> None:
    """Enforce a per-client fixed-window hit count with stale-entry eviction."""
    now = _time.time()
    bucket = RATE_STORES.setdefault(bucket_name, {})

    # Evict stale clients on every check so idle identifiers do not accumulate.
    bucket = {
        key: hits
        for key, hits in bucket.items()
        if hits and now - hits[-1] < window_s
    }
    RATE_STORES[bucket_name] = bucket

    fingerprint = client_fingerprint(request)
    recent = [hit for hit in bucket.get(fingerprint, []) if now - hit < window_s]
    if len(recent) >= max_hits:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: {max_hits} requests per {window_s} seconds",
        )

    recent.append(now)
    bucket[fingerprint] = recent
