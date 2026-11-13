import hashlib

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app import auth, rate_limit


def request(headers=None):
    return Request({
        "type": "http", "method": "GET", "path": "/", "scheme": "https",
        "client": ("192.0.2.90", 1234),
        "headers": [(k.encode(), v.encode()) for k, v in (headers or {}).items()],
    })


def test_railway_remote_ip_wins_over_forwarded_chain(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv("CIVITAE_DEV_MODE", "1")
    req = request({"x-real-ip": "198.51.100.4", "x-forwarded-for": "203.0.113.1, 203.0.113.2"})
    assert rate_limit.client_ip(req) == "198.51.100.4"
    expected = hashlib.sha256(b"198.51.100.4").hexdigest()[:16]
    assert rate_limit.client_fingerprint(req) == expected
    assert auth.client_fingerprint(req) == expected


@pytest.mark.parametrize("real_ip", ["", "not-an-ip", "198.51.100.1, 198.51.100.2"])
def test_missing_or_invalid_platform_ip_does_not_trust_forwarded_chain(monkeypatch, real_ip):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    req = request({"x-real-ip": real_ip, "x-forwarded-for": "203.0.113.1"})
    assert rate_limit.client_ip(req) == "192.0.2.90"


def test_unconfigured_ingress_ignores_address_headers(monkeypatch):
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("CIVITAE_DEV_MODE", raising=False)
    req = request({"x-real-ip": "198.51.100.1", "x-forwarded-for": "203.0.113.1"})
    assert rate_limit.client_ip(req) == "192.0.2.90"


def test_explicit_local_dev_keeps_test_origin_support(monkeypatch):
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.setenv("CIVITAE_DEV_MODE", "1")
    assert rate_limit.client_ip(request({"x-forwarded-for": "198.51.100.7"})) == "198.51.100.7"


def test_forwarded_changes_cannot_reset_railway_rate_budget(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    bucket = "client_ip_regression"
    rate_limit.RATE_STORES.pop(bucket, None)
    try:
        rate_limit.check_rate_limit(request({"x-real-ip": "198.51.100.1", "x-forwarded-for": "203.0.113.1"}), bucket, 1)
        with pytest.raises(HTTPException) as error:
            rate_limit.check_rate_limit(request({"x-real-ip": "198.51.100.1", "x-forwarded-for": "203.0.113.2"}), bucket, 1)
        assert error.value.status_code == 429
        rate_limit.check_rate_limit(request({"x-real-ip": "198.51.100.2"}), bucket, 1)
    finally:
        rate_limit.RATE_STORES.pop(bucket, None)


@pytest.mark.parametrize("origin", ["https://signomy.xyz", "https://www.signomy.xyz"])
def test_signup_direct_backend_preflight_accepts_production_site(client, origin):
    response = client.options("/api/provision/signup", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_signup_preflight_rejects_unlisted_browser_origin(client):
    response = client.options("/api/provision/signup", headers={
        "Origin": "https://untrusted.example",
        "Access-Control-Request-Method": "POST",
    })
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
