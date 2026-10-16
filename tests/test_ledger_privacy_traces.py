"""Leak-sweep follow-ups (2026-10-16): /api/traces/dataset and /api/traces/sigrank."""
from __future__ import annotations

import os
import uuid

import pytest


def test_dataset_export_is_operator_only_and_never_writes_for_anonymous(client, admin_client, tmp_path,
                                                                         monkeypatch):
    from app import seeds_otel
    monkeypatch.setattr(seeds_otel, "_PROJECT_ROOT", tmp_path)
    out = tmp_path / "data" / "civitae-agent-traces.jsonl"
    for headers in ({}, {"Authorization": "Bearer not-a-key"}, {"X-Admin-Key": "wrong"}):
        r = client.get("/api/traces/dataset?anonymize=false", headers=headers)
        assert r.status_code in (401, 403), r.text
        assert not out.exists(), "an unauthorised call must not touch the disk"
        assert str(tmp_path) not in r.text
    r = admin_client.get("/api/traces/dataset")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["output"] == "civitae-agent-traces.jsonl"       # file name only, never a server path
    assert os.sep not in body["output"] and str(tmp_path) not in r.text
    assert out.exists()


def test_dataset_rejects_agent_credentials(client):
    from tests.conftest import signup_agent
    d = signup_agent(client, ip=f"10.8.{uuid.uuid4().int % 255}.1").json()
    r = client.get("/api/traces/dataset", headers={"Authorization": f"Bearer {d['api_key']}"})
    assert r.status_code == 403


def test_sigrank_board_is_computed_once_per_window(client, monkeypatch):
    from app import seeds_otel
    seeds_otel._sigrank_cache.clear()
    calls = {"n": 0}
    real = seeds_otel._read_seeds

    def counting():
        calls["n"] += 1
        return real()

    monkeypatch.setattr(seeds_otel, "_read_seeds", counting)
    first = client.get("/api/traces/sigrank", headers={"x-forwarded-for": "10.66.1.1"})
    assert first.status_code == 200
    for i in range(5):
        r = client.get("/api/traces/sigrank", headers={"x-forwarded-for": f"10.66.2.{i}"})
        assert r.json() == first.json()
    assert calls["n"] == 1, "the all-agents board must be cached, and read the seeds once per build"
    seeds_otel._sigrank_cache.clear()


def test_sigrank_board_single_pass_matches_per_agent_compute(client):
    from app import seeds_otel
    seeds_otel._sigrank_cache.clear()
    board = seeds_otel.sigrank_board()
    for row in board["leaderboard"][:5]:
        assert row == seeds_otel.compute_sigrank(row["agent_id"])
    seeds_otel._sigrank_cache.clear()


@pytest.mark.parametrize("path", ["/api/traces/sigrank", "/api/traces/sigrank/agent-nobody"])
def test_sigrank_is_rate_limited_per_client(client, path, monkeypatch):
    from app import seeds_otel
    from app.rate_limit import RATE_STORES
    monkeypatch.setattr(seeds_otel, "SIGRANK_RATE", (3, 60))
    RATE_STORES.pop("traces_sigrank", None)
    RATE_STORES.pop("traces_sigrank_agent", None)
    ip = {"x-forwarded-for": f"10.67.{uuid.uuid4().int % 250}.9"}
    codes = [client.get(path, headers=ip).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    assert client.get(path, headers={"x-forwarded-for": "10.67.251.1"}).status_code == 200
