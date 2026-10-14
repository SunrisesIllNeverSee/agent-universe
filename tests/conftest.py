"""
conftest.py — Shared pytest fixtures for CIVITAE route tests.

Uses starlette.testclient.TestClient (sync) — no pytest-asyncio required.
All tests share a session-scoped app instance with a temporary root directory.

State note: app/deps.state is a singleton — it accumulates across tests.
Use unique agent names (uuid4 suffix) to avoid 409 conflicts.
Pass x-forwarded-for headers with unique IPs to avoid rate limit collisions.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest
from starlette.testclient import TestClient

# Set env vars BEFORE importing create_app — they're read at import time
os.environ.setdefault("CIVITAE_ADMIN_KEY", "test-admin-key-12345")
os.environ.setdefault("CIVITAE_DEV_MODE", "1")
os.environ.setdefault("WORKENTRY_SWEEP_INTERVAL_HOURS", "0")  # scheduler off in tests unless invoked
os.environ.pop("RAILWAY_ENVIRONMENT", None)  # ensure dev mode kicks in


# scratch debug file kept on disk (never delete); not collected as a test module
collect_ignore = ["zz_dbg_test.py", "zz_dbg2_test.py"]


@pytest.fixture(scope="session")
def tmp_root(tmp_path_factory) -> Path:
    """Temporary root directory mimicking production layout."""
    root = tmp_path_factory.mktemp("civitae_root")

    # Config files — minimal valid structure
    config = root / "config"
    config.mkdir()

    (config / "systems.json").write_text(json.dumps({
        "systems": [
            {"id": "claude", "name": "Claude", "provider": "Anthropic",
             "codename": "Signal Analyst", "class": "Recursive Reasoner", "online": True},
            {"id": "gpt", "name": "GPT", "provider": "OpenAI",
             "codename": "Bridge Strategist", "class": "Architect-Transmitter", "online": True},
        ]
    }))
    (config / "agents.json").write_text(json.dumps({"agents": []}))
    (config / "vault.json").write_text(json.dumps({"vault": {}}))
    (config / "pages.json").write_text(json.dumps({
        "tileZero": {"slot": "0.0", "name": "Home", "route": "/", "status": "live"},
        "layers": []
    }))
    (config / "formations.json").write_text(json.dumps({"formations": []}))
    (config / "provision.json").write_text(json.dumps({
        "require_governance": False,
        "max_agents": 100,
        "approval_mode": "auto",
        "rate_limit": 10,
    }))

    # Frontend dir — copy the shell page so its route is servable in tests;
    # everything else stays empty (StaticFiles mounts only need the dir).
    (root / "frontend").mkdir()
    shell_src = Path(__file__).resolve().parents[1] / "frontend" / "shell.html"
    if shell_src.is_file():
        import shutil as _sh
        _sh.copy2(shell_src, root / "frontend" / "shell.html")
    (root / "vault").mkdir()
    (root / "data").mkdir()

    return root


@pytest.fixture(scope="session")
def app(tmp_root):
    """Session-scoped FastAPI app — shared across all route tests."""
    from app.server import create_app
    return create_app(tmp_root)


@pytest.fixture
def client(app):
    """Function-scoped sync TestClient."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def admin_client(app):
    """Function-scoped sync TestClient with X-Admin-Key header."""
    return TestClient(
        app,
        headers={"X-Admin-Key": "test-admin-key-12345"},
        raise_server_exceptions=False,
    )


@pytest.fixture
def unique_ip():
    """Return a unique IP string per test to avoid rate limit collisions."""
    return f"10.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"


def signup_agent(client, name: str = None, ip: str = None) -> dict:
    """Helper: POST /api/provision/signup and return response dict."""
    name = name or f"TestBot-{uuid.uuid4().hex[:6]}"
    ip = ip or f"10.1.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    resp = client.post(
        "/api/provision/signup",
        json={"name": name, "system": "claude"},
        headers={"x-forwarded-for": ip},
    )
    return resp


@pytest.fixture
def fresh_agent(client, unique_ip):
    """Fixture: creates a fresh agent and returns the signup response dict."""
    resp = signup_agent(client, ip=unique_ip)
    assert resp.status_code == 200, f"signup failed: {resp.text}"
    return resp.json()


@pytest.fixture(autouse=True)
def _webhook_signing_secret(monkeypatch):
    """The Stripe webhook refuses to run with no signing secret; tests that mock construct_event
    still need one configured. Tests of the unset case override it."""
    from app import kassa_payments
    monkeypatch.setattr(kassa_payments, "STRIPE_WEBHOOK_SECRET", "whsec_test")


@pytest.fixture(autouse=True)
def _relaxed_wallet_rules(request, monkeypatch):
    """P5i wallet limits (12h link interval, 24h/$25 new-wallet cap) are exercised only by
    test_p5i_wallet_safety.py; every other test links several wallets and withdraws freely."""
    if request.module.__name__.endswith(("test_p5i_wallet_safety", "test_p5j_review", "test_p5k_stripe_new_dest_cap", "test_p5k_approval_recovery", "test_p5k_stripe_recovery", "test_p5l_review")):
        return
    import app.wallet_store as ws
    monkeypatch.setattr(ws, "wallet_rules", lambda: {
        "link_interval_hours": 0, "new_wallet_window_hours": 0, "new_wallet_cap_usd": 25.0})
