"""P5e G2 options C, D, E -- per-tier multipliers, poster-declared answer window and per-mode timers.
Explanation/visibility timing only: nothing expires, nothing moves money."""
import json
from datetime import timedelta
from pathlib import Path

from app import economy
from app import workentry_store as ws
from app.routes import workentry as wr
from tests.test_workentry_store import audit, clock, seeds, store, file_  # noqa: F401

REPO = Path(__file__).resolve().parents[1]
H, D = timedelta(hours=1), timedelta(days=1)


def cfg(monkeypatch, **c):
    monkeypatch.setattr(economy, "_load_rates", lambda *a, **k: {"workentry_pending": c})


def test_shipped_config_is_inert():
    assert ws.pending_timers() == (48 * H, 14 * D)
    for mode in ("open", "standard", "constitutional"):
        assert ws.pending_timers(mode=mode) == (48 * H, 14 * D)
    for tier in ("ungoverned", "governed", "constitutional", "blackcard"):
        assert ws.pending_timers(tier=tier) == (48 * H, 14 * D)
    assert not ws.tier_multipliers_configured()
    c = json.loads((REPO / "config" / "economic_rates.json").read_text())["workentry_pending"]
    assert c["answer_window_min_hours"] == 12 and c["answer_window_max_hours"] == 168


# E: per-mode
def test_mode_override_and_fallback(monkeypatch):
    cfg(monkeypatch, ask_poster_after_hours=48, dormant_after_days=14,
        by_mode={"standard": {"ask_poster_after_hours": 24}, "constitutional": {"dormant_after_days": 30}})
    assert ws.pending_timers(mode="standard") == (24 * H, 14 * D)
    assert ws.pending_timers(mode="constitutional") == (48 * H, 30 * D)
    assert ws.pending_timers(mode="open") == (48 * H, 14 * D)
    cfg(monkeypatch, by_mode={"standard": {"ask_poster_after_hours": "x", "dormant_after_days": -2}})
    assert ws.pending_timers(mode="standard") == (48 * H, 14 * D)


def test_sweep_dormant_is_per_mode(store, clock, monkeypatch):
    cfg(monkeypatch, by_mode={"constitutional": {"dormant_after_days": 30}})
    std = file_(store, entrant="e1", opp="post:K-1")["agreement"]["agreement_id"]
    con = file_(store, mode="constitutional", entrant="e2", opp="post:K-2")["agreement"]["agreement_id"]
    clock.advance(days=15)
    assert store.sweep_dormant() == [std]
    assert store.get(con)["state"] == "pending"
    clock.advance(days=16)
    assert store.sweep_dormant() == [con]


# C: tier multipliers (ask window only)
def test_tier_multiplier_scales_ask_only(monkeypatch):
    cfg(monkeypatch, tier_multipliers={"blackcard": 0.5, "ungoverned": 2, "governed": "x"})
    assert ws.tier_multipliers_configured()
    assert ws.pending_timers(tier="blackcard") == (24 * H, 14 * D)
    assert ws.pending_timers(tier="ungoverned") == (96 * H, 14 * D)
    assert ws.pending_timers(tier="governed") == (48 * H, 14 * D)
    assert ws.pending_timers(tier=None) == (48 * H, 14 * D)
    cfg(monkeypatch, dormant_after_days=1, tier_multipliers={"ungoverned": 10})
    assert ws.pending_timers(tier="ungoverned") == (1 * D, 1 * D)   # ask never exceeds dormant


# D: poster-declared window
def test_declared_window_clamped_and_wins(monkeypatch):
    cfg(monkeypatch, tier_multipliers={"blackcard": 0.5})
    assert ws.pending_timers(answer_window_hours=72)[0] == 72 * H
    assert ws.pending_timers(answer_window_hours=1)[0] == 12 * H
    assert ws.pending_timers(answer_window_hours=100000)[0] == 168 * H
    assert ws.pending_timers(tier="blackcard", answer_window_hours=72)[0] == 72 * H
    assert ws.pending_timers(answer_window_hours=True)[0] == 48 * H
    assert ws.pending_timers(answer_window_hours=-5)[0] == 48 * H
    assert ws.pending_timers(answer_window_hours=72)[1] == 14 * D


def test_entry_timers_reads_terms(monkeypatch):
    a = {"entry_mode": "standard", "terms": {"answer_window_hours": 30}}
    assert wr._entry_timers(a) == (30 * H, 14 * D)
    assert wr._entry_timers({"entry_mode": "standard", "terms": {}}) == (48 * H, 14 * D)


def test_wait_view_explains_windows(store, monkeypatch):
    monkeypatch.setattr(wr, "_store", lambda: store)
    a = file_(store)["agreement"]
    v = wr._wait_view(a)
    assert v["waiting_on"] == "poster"
    assert v["pending_windows"]["ask_poster_after_hours"] == 48
    assert v["pending_windows"]["dormant_after_days"] == 14
    assert "Nothing expires" in v["pending_windows"]["label"]
    done = {**a, "state": "accepted"}
    assert "pending_windows" not in wr._wait_view(done)


def test_frontend_shows_window_label():
    js = (REPO / "frontend" / "_entry.js").read_text()
    assert "pending_windows" in js


def _api_clock(monkeypatch):
    from datetime import UTC, datetime
    from app.deps import state
    box = {"offset": timedelta(0)}
    monkeypatch.setattr(state.workentry, "_clock", lambda: datetime.now(UTC) + box["offset"])
    return box


def test_sweep_asks_per_entry_window(client, monkeypatch):
    """End to end through the sweep: a 24 h per-mode window nudges at 25 h."""
    from app.deps import state
    from tests.test_p4_entry_api import _agent, _file, _post
    box = _api_clock(monkeypatch)
    cfg(monkeypatch, by_mode={"standard": {"ask_poster_after_hours": 24}})
    owner, ent = _agent(client), _agent(client)
    aid = _file(client, ent, f"post:{_post(owner['id'])}").json()["agreement"]["agreement_id"]
    asks = lambda: [m for m in state.inbox.load(owner["id"]) if m["kind"] == "work_entry_ask_poster" and m["ref_id"] == aid]
    box["offset"] = timedelta(hours=25)
    assert aid in wr.sweep_entries()["asked_poster"]   # shared state may hold other entries
    assert len(asks()) == 1
    assert aid not in wr.sweep_entries()["asked_poster"]


def test_poster_declared_window_end_to_end(client, monkeypatch):
    """The window comes from the post, not the request body; the sweep honours it."""
    from datetime import UTC, datetime
    from app.deps import state
    from tests.test_p4_entry_api import _agent, _file
    box = _api_clock(monkeypatch)
    owner, ent = _agent(client), _agent(client)
    now = datetime.now(UTC).isoformat()
    state.kassa.insert_post({"id": "K-win1", "tab": "iso", "title": "t", "tag": "t", "body": "b",
                             "from_name": "P", "from_email": "", "created_at": now, "updated_at": now,
                             "poster_agent_id": owner["id"]})
    # the posts table has no such column yet (not built); simulate a post record that carries it
    real = state.kassa.get_post
    monkeypatch.setattr(state.kassa, "get_post",
                        lambda pid: {**real(pid), "answer_window_hours": 96} if real(pid) else None)
    # an entrant-supplied value in terms is discarded
    r = _file(client, ent, "post:K-win1", terms={"answer_window_hours": 1}).json()
    a = r["agreement"]
    assert a["terms"]["answer_window_hours"] == 96
    assert r["pending_windows"]["ask_poster_after_hours"] == 96
    aid = a["agreement_id"]
    box["offset"] = timedelta(hours=60)
    assert aid not in wr.sweep_entries()["asked_poster"]      # default 48 h would have fired
    box["offset"] = timedelta(hours=97)
    assert aid in wr.sweep_entries()["asked_poster"]
    assert state.workentry.get(aid)["state"] == "pending"  # nothing expired
