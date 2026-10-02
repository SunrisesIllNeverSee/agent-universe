"""Shared in-process rate limiting for the current single-worker deployment.

The store is intentionally process-local. Production remains single-worker until
authoritative state storage is redesigned, so persistence/Redis is not required
for correctness today.
"""
from __future__ import annotations

import hashlib
import time as _time

from fastapi import HTTPException, Request


RATE_STORES: dict[str, dict[str, list[float]]] = {}


def client_fingerprint(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


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
