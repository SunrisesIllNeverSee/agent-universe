"""ST-010 regression tests for current single-process rate-limit semantics."""
from __future__ import annotations

import hashlib

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app import rate_limit


def _request(ip: str) -> Request:
    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": "/test",
        "raw_path": b"/test",
        "query_string": b"",
        "headers": [(b"x-forwarded-for", ip.encode("ascii"))],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 443),
    })


def test_rate_limit_rejects_at_boundary(monkeypatch):
    rate_limit.RATE_STORES.clear()
    monkeypatch.setattr(rate_limit._time, "time", lambda: 1000.0)
    req = _request("203.0.113.10")

    rate_limit.check_rate_limit(req, "boundary", max_hits=2, window_s=3600)
    rate_limit.check_rate_limit(req, "boundary", max_hits=2, window_s=3600)

    with pytest.raises(HTTPException) as exc:
        rate_limit.check_rate_limit(req, "boundary", max_hits=2, window_s=3600)

    assert exc.value.status_code == 429


def test_rate_limit_evicts_stale_idle_clients(monkeypatch):
    rate_limit.RATE_STORES.clear()
    stale_ip = "203.0.113.20"
    stale_hash = hashlib.sha256(stale_ip.encode()).hexdigest()[:16]
    rate_limit.RATE_STORES["eviction"] = {stale_hash: [100.0]}

    monkeypatch.setattr(rate_limit._time, "time", lambda: 1000.0)
    rate_limit.check_rate_limit(_request("203.0.113.21"), "eviction", max_hits=2, window_s=100)

    assert stale_hash not in rate_limit.RATE_STORES["eviction"]


def test_rate_limit_uses_first_forwarded_client_ip(monkeypatch):
    rate_limit.RATE_STORES.clear()
    monkeypatch.setattr(rate_limit._time, "time", lambda: 1000.0)
    rate_limit.check_rate_limit(
        _request("203.0.113.30, 10.0.0.4"),
        "forwarded",
        max_hits=2,
        window_s=3600,
    )

    expected = hashlib.sha256("203.0.113.30".encode()).hexdigest()[:16]
    assert expected in rate_limit.RATE_STORES["forwarded"]
