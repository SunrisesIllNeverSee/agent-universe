"""P5 G1 -- scheduled dormancy sweep. Same transition as the lazy path (receipt + Seed),
idempotent, never retires/deletes. Tests call the sweep directly (scheduler is off in tests)."""
import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from tests.test_p4_entry_api import _agent, _file, _post


@pytest.fixture
def clock(monkeypatch):
    from app.deps import state
    box = {"offset": timedelta(0)}
    monkeypatch.setattr(state.workentry, "_clock", lambda: datetime.now(UTC) + box["offset"])
    return box


def _new(client):
    owner, ent = _agent(client), _agent(client)
    r = _file(client, ent, f"post:{_post(owner['id'])}")
    assert r.status_code == 201, r.text
    return owner, ent, r.json()["agreement"]["agreement_id"]


def _get(aid):
    from app.deps import state
    return state.workentry.get(aid)


def test_scheduler_env_config(monkeypatch):
    from app.routes.workentry import sweep_interval_seconds, SWEEP_INTERVAL_ENV
    monkeypatch.delenv(SWEEP_INTERVAL_ENV, raising=False)
    assert sweep_interval_seconds() == 6 * 3600
    monkeypatch.setenv(SWEEP_INTERVAL_ENV, "0.5")
    assert sweep_interval_seconds() == 1800
    monkeypatch.setenv(SWEEP_INTERVAL_ENV, "0")
    assert sweep_interval_seconds() == 0
    monkeypatch.setenv(SWEEP_INTERVAL_ENV, "junk")
    assert sweep_interval_seconds() == 0


def test_old_pending_goes_dormant_with_receipt_and_seed(client, clock):
    from app.deps import state
    _, _, aid = _new(client)
    before = len(state.workentry.receipts(aid))
    clock["offset"] = timedelta(days=15)
    res = asyncio.run(__import__("app.routes.workentry", fromlist=["x"]).run_scheduled_sweep())
    assert aid in res["dormant"]
    a = _get(aid)
    assert a["state"] == "dormant"
    h = [x for x in a["state_history"] if x["transition"] == "go_dormant"]
    assert len(h) == 1 and h[0]["actor"] == "system"
    rcs = state.workentry.receipts(aid)
    assert len(rcs) == before + 1
    assert rcs[-1]["transition"] == "go_dormant" and rcs[-1]["seed_doi"]


def test_fresh_entry_untouched(client, clock):
    from app.routes.workentry import sweep_entries
    _, _, aid = _new(client)
    clock["offset"] = timedelta(days=3)
    assert aid not in sweep_entries()["dormant"]
    assert _get(aid)["state"] == "pending"


def test_second_sweep_is_noop(client, clock):
    from app.routes.workentry import sweep_entries
    _, _, aid = _new(client)
    clock["offset"] = timedelta(days=15)
    assert aid in sweep_entries()["dormant"]
    n = len(_get(aid)["state_history"])
    second = sweep_entries()
    assert aid not in second["dormant"]
    assert len(_get(aid)["state_history"]) == n and _get(aid)["state"] == "dormant"


def test_dormant_revives_on_activity_after_sweep(client, clock):
    from app.routes.workentry import sweep_entries
    owner, ent, aid = _new(client)
    clock["offset"] = timedelta(days=15)
    sweep_entries()
    assert _get(aid)["state"] == "dormant"
    r = client.post(f"/api/work-entry/{aid}/activity", headers=ent["h"])
    assert r.status_code == 200, r.text
    assert _get(aid)["state"] == "pending"
    assert [h["transition"] for h in _get(aid)["state_history"]][-2:] == ["go_dormant", "revive"]


def test_non_pending_states_untouched_and_nothing_retired(client, clock):
    from app.routes.workentry import sweep_entries
    owner, ent, aid = _new(client)
    assert client.post(f"/api/work-entry/{aid}/accept", headers=owner["h"]).status_code == 200
    _, ent2, aid2 = _new(client)
    assert client.post(f"/api/work-entry/{aid2}/withdraw", headers=ent2["h"]).status_code == 200
    clock["offset"] = timedelta(days=60)
    res = sweep_entries()
    assert aid not in res["dormant"] and aid2 not in res["dormant"]
    assert _get(aid)["state"] == "accepted" and _get(aid2)["state"] == "withdrawn"


def test_sweep_never_retires_dormant(client, clock):
    from app.routes.workentry import sweep_entries
    _, _, aid = _new(client)
    clock["offset"] = timedelta(days=15)
    sweep_entries()
    clock["offset"] = timedelta(days=400)
    sweep_entries()
    assert _get(aid)["state"] == "dormant"
