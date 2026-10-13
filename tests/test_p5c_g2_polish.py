"""P5c G2 polish -- pending-Agreement timers come from config, the entrant sees who the entry
is waiting on, and the poster's typical response time is a displayed fact (not a rule)."""
import json
from datetime import timedelta
from pathlib import Path

import pytest

from app import economy
from app import workentry_store as ws
from tests.test_workentry_store import Clock, FakeAudit, FakeSeeds, file_  # noqa: F401
from tests.test_workentry_store import audit, clock, seeds, store  # noqa: F401  (fixtures)

REPO = Path(__file__).resolve().parents[1]


def test_config_carries_todays_values():
    cfg = json.loads((REPO / "config" / "economic_rates.json").read_text())["workentry_pending"]
    assert cfg["ask_poster_after_hours"] == 48
    assert cfg["dormant_after_days"] == 14
    assert ws.pending_timers() == (timedelta(hours=48), timedelta(days=14))


def test_timers_read_config_and_fall_back(monkeypatch):
    monkeypatch.setattr(economy, "_load_rates",
                        lambda *a, **k: {"workentry_pending": {"ask_poster_after_hours": 6, "dormant_after_days": 2}})
    assert ws.pending_timers() == (timedelta(hours=6), timedelta(days=2))
    monkeypatch.setattr(economy, "_load_rates", lambda *a, **k: {})
    assert ws.pending_timers() == (timedelta(hours=48), timedelta(days=14))
    monkeypatch.setattr(economy, "_load_rates",
                        lambda *a, **k: {"workentry_pending": {"ask_poster_after_hours": "x", "dormant_after_days": -1}})
    assert ws.pending_timers() == (timedelta(hours=48), timedelta(days=14))


def test_sweep_dormant_uses_configured_days(store, clock, monkeypatch):
    monkeypatch.setattr(economy, "_load_rates",
                        lambda *a, **k: {"workentry_pending": {"dormant_after_days": 2}})
    aid = file_(store)["agreement"]["agreement_id"]
    clock.advance(days=3)
    assert store.sweep_dormant() == [aid]
    assert "no activity for 2 days" in store.get(aid)["state_history"][-1]["reason"]


def test_poster_response_median_hours(store, clock):
    assert store.poster_response("agent-o") == {"samples": 0, "median_hours": None}
    for hours in (1, 5, 3):
        aid = file_(store, entrant=f"e{hours}", opp=f"post:K-{hours}")["agreement"]["agreement_id"]
        clock.advance(hours=hours)
        store.accept(aid, actor="agent-o")
    out = store.poster_response("agent-o")
    assert out == {"samples": 3, "median_hours": 3.0}
    # pending, system-resolved and other posters' entries do not count
    file_(store, entrant="e9", opp="post:K-9")
    open_ = file_(store, mode="open", entrant="e8", opp="post:K-8")
    assert open_["agreement"]["state"] == "accepted"
    assert store.poster_response("agent-o")["samples"] == 3
    assert store.poster_response("someone-else")["samples"] == 0
