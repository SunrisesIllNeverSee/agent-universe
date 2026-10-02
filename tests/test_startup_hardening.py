"""ST-012 regression tests for fail-fast production startup dependencies."""
from __future__ import annotations

import json

import pytest


def _minimal_root(tmp_path):
    root = tmp_path / "root"
    config = root / "config"
    config.mkdir(parents=True)
    (root / "frontend").mkdir()
    (root / "vault").mkdir()
    (root / "data").mkdir()

    (config / "systems.json").write_text(json.dumps({
        "systems": [
            {"id": "claude", "name": "Claude", "provider": "Anthropic",
             "codename": "Signal Analyst", "class": "Recursive Reasoner", "online": True},
            {"id": "gpt", "name": "GPT", "provider": "OpenAI",
             "codename": "Bridge Strategist", "class": "Architect-Transmitter", "online": True},
        ]
    }), encoding="utf-8")
    (config / "agents.json").write_text(json.dumps({"agents": []}), encoding="utf-8")
    (config / "vault.json").write_text(json.dumps({"vault": {}}), encoding="utf-8")
    (config / "pages.json").write_text(json.dumps({
        "tileZero": {"slot": "0.0", "name": "Home", "route": "/", "status": "live"},
        "layers": [],
    }), encoding="utf-8")
    (config / "formations.json").write_text(json.dumps({"formations": []}), encoding="utf-8")
    (config / "provision.json").write_text(json.dumps({
        "require_governance": False,
        "max_agents": 100,
        "approval_mode": "auto",
        "rate_limit": 10,
    }), encoding="utf-8")
    return root


def test_create_app_fails_on_corrupt_authoritative_provision_config(tmp_path, monkeypatch):
    from app.jwt_config import clear_kassa_jwt_secret_cache
    from app.server import create_app

    root = _minimal_root(tmp_path)
    (root / "config" / "provision.json").write_text("{not-json", encoding="utf-8")
    monkeypatch.setenv("KASSA_JWT_SECRET", "test-startup-secret")
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    clear_kassa_jwt_secret_cache()

    with pytest.raises(json.JSONDecodeError):
        create_app(root)

    clear_kassa_jwt_secret_cache()


def test_create_app_refuses_ephemeral_jwt_secret_on_railway(tmp_path, monkeypatch):
    from app.jwt_config import clear_kassa_jwt_secret_cache
    from app.server import create_app

    root = _minimal_root(tmp_path)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.delenv("KASSA_JWT_SECRET", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    clear_kassa_jwt_secret_cache()

    with pytest.raises(RuntimeError, match="KASSA_JWT_SECRET or JWT_SECRET"):
        create_app(root)

    clear_kassa_jwt_secret_cache()
