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
os.environ.pop("RAILWAY_ENVIRONMENT", None)  # ensure dev mode kicks in


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

    # Frontend dir — empty but must exist for StaticFiles mounts
    (root / "frontend").mkdir()
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
