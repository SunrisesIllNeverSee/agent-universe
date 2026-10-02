"""Shared authentication primitives for operator/admin boundaries.

This module owns constant-time comparison plus privacy-safe success/failure
telemetry. It does not decide which routes are admin-only; route/middleware
policy stays where it is today.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Final

from fastapi import HTTPException, Request


_security_logger = logging.getLogger("civitae.security")
_AUTH_LOG_WINDOW_S: Final[float] = 60.0
_AUTH_CACHE_MAX: Final[int] = 2048
_rejection_log_times: dict[str, float] = {}
_success_log_times: dict[str, float] = {}


def secret_matches(provided: str | None, expected: str | None) -> bool:
    """Constant-time comparison that fails closed for absent/empty secrets."""
    if not provided or not expected:
        return False
    return hmac.compare_digest(provided, expected)


def admin_key_matches(request: Request, expected: str | None) -> bool:
    """Return True only when a configured admin key matches the request header."""
    return secret_matches(request.headers.get("X-Admin-Key", ""), expected)


def client_fingerprint(request: Request) -> str:
    """Hash the best available client address for privacy-safe security telemetry."""
    forwarded = request.headers.get("x-forwarded-for", "")
    host = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )
    return hashlib.sha256(host.encode("utf-8")).hexdigest()[:16]


def log_admin_rejection(request: Request, reason: str) -> None:
    """Emit throttled auth-failure telemetry without logging credentials or raw IPs."""
    now = time.monotonic()
    fingerprint = client_fingerprint(request)
    key = f"{fingerprint}:{request.method}:{request.url.path}:{reason}"

    # Bound memory and remove old throttle entries. Logging is attacker-triggerable,
    # so this cache must not grow without limit.
    if len(_rejection_log_times) >= _AUTH_CACHE_MAX:
        cutoff = now - (_AUTH_LOG_WINDOW_S * 5)
        stale = [k for k, seen in _rejection_log_times.items() if seen < cutoff]
        for stale_key in stale:
            _rejection_log_times.pop(stale_key, None)
        if len(_rejection_log_times) >= _AUTH_CACHE_MAX:
            # Telemetry must never become an availability problem.
            _rejection_log_times.clear()

    last = _rejection_log_times.get(key)
    if last is not None and now - last < _AUTH_LOG_WINDOW_S:
        return
    _rejection_log_times[key] = now

    _security_logger.warning(
        "admin_auth_rejected method=%s path=%s client=%s reason=%s",
        request.method,
        request.url.path,
        fingerprint,
        reason,
    )


def log_admin_success(request: Request) -> None:
    """Emit throttled successful operator-auth telemetry without raw secrets/IPs."""
    now = time.monotonic()
    fingerprint = client_fingerprint(request)
    key = f"{fingerprint}:{request.method}:{request.url.path}"

    if len(_success_log_times) >= _AUTH_CACHE_MAX:
        cutoff = now - (_AUTH_LOG_WINDOW_S * 5)
        stale = [k for k, seen in _success_log_times.items() if seen < cutoff]
        for stale_key in stale:
            _success_log_times.pop(stale_key, None)
        if len(_success_log_times) >= _AUTH_CACHE_MAX:
            _success_log_times.clear()

    last = _success_log_times.get(key)
    if last is not None and now - last < _AUTH_LOG_WINDOW_S:
        return
    _success_log_times[key] = now

    _security_logger.info(
        "admin_auth_ok method=%s path=%s client=%s",
        request.method,
        request.url.path,
        fingerprint,
    )


def require_admin(request: Request, expected: str | None) -> None:
    """Fail-closed admin authorization with privacy-safe rejection telemetry."""
    if not expected:
        log_admin_rejection(request, "not_configured")
        raise HTTPException(403, "CIVITAE_ADMIN_KEY not configured")
    if not admin_key_matches(request, expected):
        log_admin_rejection(request, "invalid")
        raise HTTPException(403, "Admin key required")
    log_admin_success(request)
