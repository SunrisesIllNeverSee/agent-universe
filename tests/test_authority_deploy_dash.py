"""Authority hardening — mission_dash verbs follow the mission owner; /api/deploy HELD.

mission-dash init/progress/milestone: unknown mission -> 404 before any write,
owner agent or admin only, ownerless legacy missions admin-only, agents cannot
forge the settlement status ``paid``. Order 401 -> 404 -> 403. Runs on the
session tmp root (see conftest) — never real data/.

/api/deploy is global DEPLOY board state with no per-agent principal/object in
the codebase; the owner contract (1G 5.C, O-IA-5) grants it to an
"agreement-bound actor with deployment authority" that does not exist yet.
Held with strict xfail, see test_deploy_* below.
"""
import json
import uuid

import pytest

from app.deps import state
from tests.conftest import signup_agent

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


def _agent(client):
    ip = f"10.9.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"dd-{uuid.uuid4().hex[:6]}", ip=ip).json()
    return d, {"Authorization": f"Bearer {d['api_key']}"}


def _mission(client, headers):
    r = client.post("/api/missions", json={"label": "m"}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _legacy(mission_id):
    from app.routes import missions as m
    ms = m._load_missions()
    ms.append({"id": mission_id, "mission_id": mission_id, "label": "legacy",
               "status": "active", "ended_at": None})
    m._save_missions(ms)


def _lines(name):
    p = state.root / "data" / name
    return len(p.read_text().splitlines()) if p.exists() else 0


def _dash_raw():
    p = state.root / "data" / "mission_dashboard.json"
    return p.read_text() if p.exists() else None


def _snap():
    return (_dash_raw(), _lines("audit.jsonl"), _lines("seeds.jsonl"))


def _seed_dash(client, mid):
    """Admin-initialize a dashboard with one milestone."""
    r = client.post(f"/api/mission-dash/{mid}", headers=ADMIN,
                    json={"status": "posted", "milestones": ["m1"]})
    assert r.status_code == 200, r.text


VERBS = {
    "init": lambda c, mid, h: c.post(f"/api/mission-dash/{mid}", json={"status": "posted"}, headers=h),
    "progress": lambda c, mid, h: c.post(f"/api/mission-dash/{mid}/progress", json={"progress_pct": 50}, headers=h),
    "milestone": lambda c, mid, h: c.post(f"/api/mission-dash/{mid}/milestone", json={"milestone": "m1"}, headers=h),
}
verbs = pytest.mark.parametrize("verb", list(VERBS))


def _denied(r):
    return r.status_code in (401, 403)


# ── owner / admin success ───────────────────────────────────────────────────

@verbs
def test_owner_success(client, verb):
    _, h = _agent(client)
    mid = _mission(client, h)
    _seed_dash(client, mid)
    assert VERBS[verb](client, mid, h).status_code == 200


@verbs
def test_admin_success(client, verb):
    _, h = _agent(client)
    mid = _mission(client, h)
    _seed_dash(client, mid)
    assert VERBS[verb](client, mid, ADMIN).status_code == 200


@verbs
def test_admin_ownerless_legacy_success(client, verb):
    mid = f"legacy-{uuid.uuid4().hex[:6]}"
    _legacy(mid)
    _seed_dash(client, mid)
    assert VERBS[verb](client, mid, ADMIN).status_code == 200


# ── denials leave every store untouched ─────────────────────────────────────

@verbs
def test_anonymous_denied(client, verb):
    _, h = _agent(client)
    mid = _mission(client, h)
    _seed_dash(client, mid)
    before = _snap()
    assert _denied(VERBS[verb](client, mid, {}))
    assert _snap() == before


@verbs
def test_wrong_agent_denied(client, verb):
    _, owner = _agent(client)
    _, other = _agent(client)
    mid = _mission(client, owner)
    _seed_dash(client, mid)
    before = _snap()
    assert VERBS[verb](client, mid, other).status_code == 403
    assert _snap() == before


@verbs
def test_revoked_key_denied(client, verb):
    d, h = _agent(client)
    mid = _mission(client, h)
    _seed_dash(client, mid)
    assert client.post("/api/provision/suspend", json={"agent_id": d["agent_id"]},
                       headers=ADMIN).status_code == 200
    before = _snap()
    assert _denied(VERBS[verb](client, mid, h))
    assert _snap() == before


@verbs
def test_shell_spoof_with_other_agent_key_denied(client, verb):
    _, owner = _agent(client)
    _, other = _agent(client)
    mid = _mission(client, owner)
    _seed_dash(client, mid)
    before = _snap()
    spoof = {**other, "Referer": "http://127.0.0.1:8300/console", "Origin": "http://127.0.0.1:8300",
             "X-Forwarded-For": "127.0.0.1", "X-Shell-Role": "operator"}
    assert VERBS[verb](client, mid, spoof).status_code == 403
    assert _snap() == before


@verbs
def test_spoof_headers_without_credential_denied(client, verb):
    _, owner = _agent(client)
    mid = _mission(client, owner)
    _seed_dash(client, mid)
    before = _snap()
    spoof = {"Referer": "http://127.0.0.1:8300/console", "Origin": "http://127.0.0.1:8300",
             "X-Forwarded-For": "127.0.0.1"}
    assert _denied(VERBS[verb](client, mid, spoof))
    assert _snap() == before


@verbs
def test_garbage_admin_header_plus_other_agent_key_denied(client, verb):
    _, owner = _agent(client)
    _, other = _agent(client)
    mid = _mission(client, owner)
    _seed_dash(client, mid)
    before = _snap()
    h = {**other, "X-Admin-Key": "not-the-admin-key"}
    assert VERBS[verb](client, mid, h).status_code == 403
    assert _snap() == before


@verbs
def test_jwt_denied(client, verb):
    _, owner = _agent(client)
    d, other = _agent(client)
    mid = _mission(client, owner)
    _seed_dash(client, mid)
    jwt = client.post("/api/provision/login",
                      json={"agent_id": d["agent_id"], "api_key": d["api_key"]}).json().get("token")
    before = _snap()
    h = {"Authorization": f"Bearer {jwt or 'x.y.z'}"}
    assert _denied(VERBS[verb](client, mid, h))
    assert _snap() == before


@verbs
def test_unknown_mission_404_before_write(client, verb):
    _, h = _agent(client)
    before = _snap()
    r = VERBS[verb](client, f"no-such-{uuid.uuid4().hex[:6]}", h)
    assert r.status_code == 404
    assert _snap() == before


@verbs
def test_admin_unknown_mission_404(client, verb):
    before = _snap()
    assert VERBS[verb](client, f"no-such-{uuid.uuid4().hex[:6]}", ADMIN).status_code == 404
    assert _snap() == before


@verbs
def test_ownerless_legacy_mission_denies_agents(client, verb):
    _, h = _agent(client)
    mid = f"legacy-{uuid.uuid4().hex[:6]}"
    _legacy(mid)
    _seed_dash(client, mid)
    before = _snap()
    assert VERBS[verb](client, mid, h).status_code == 403
    assert _snap() == before


# ── status forgery ──────────────────────────────────────────────────────────

def test_owner_cannot_forge_paid_via_progress(client):
    _, h = _agent(client)
    mid = _mission(client, h)
    _seed_dash(client, mid)
    before = _snap()
    r = client.post(f"/api/mission-dash/{mid}/progress", json={"status": "paid"}, headers=h)
    assert r.status_code == 403
    assert _snap() == before


def test_owner_cannot_forge_paid_via_init(client):
    _, h = _agent(client)
    mid = _mission(client, h)
    before = _snap()
    r = client.post(f"/api/mission-dash/{mid}", json={"status": "paid"}, headers=h)
    assert r.status_code == 403
    assert _snap() == before


def test_admin_may_set_paid(client):
    _, h = _agent(client)
    mid = _mission(client, h)
    _seed_dash(client, mid)
    r = client.post(f"/api/mission-dash/{mid}/progress", json={"status": "paid"}, headers=ADMIN)
    assert r.status_code == 200
    assert client.get(f"/api/mission-dash/{mid}").json()["status"] == "paid"


def test_owner_may_advance_non_settlement_status(client):
    _, h = _agent(client)
    mid = _mission(client, h)
    _seed_dash(client, mid)
    r = client.post(f"/api/mission-dash/{mid}/progress", json={"status": "in_progress"}, headers=h)
    assert r.status_code == 200
    assert client.get(f"/api/mission-dash/{mid}").json()["status"] == "in_progress"


# ── /api/deploy: HELD owner decision ────────────────────────────────────────
# Today any active agent Bearer key can rewrite the global DEPLOY board
# (tab/objective/posture/formation/target/active flag), persisting state and
# broadcasting `deploy_updated` over WebSocket. It reaches no external
# infrastructure (runtime.persist + audit + WS emit only). Owner contract
# (1G 5.C deploy row, O-IA-5): authority = agreement-bound actor with
# deployment authority, or operator FOR a named principal — neither a
# deployment-authority grant nor an agreement object exists in this codebase,
# so there is no principal to bind. Admin-only would also break the existing
# ST-003 contract test (agent Bearer -> 200). Strict xfail records the gap;
# flip when the owner picks a model.

@pytest.mark.xfail(strict=True, reason="HELD: O-IA-5 deploy authority model undefined (owner decision)")
def test_deploy_agent_bearer_cannot_rewrite_global_board(client):
    _, h = _agent(client)
    before = _snap()
    r = client.post("/api/deploy", json={"objective": f"forged-{uuid.uuid4().hex[:6]}"}, headers=h)
    assert _denied(r)
    assert _snap() == before


def test_deploy_anonymous_and_spoof_denied(client):
    before = _snap()
    spoof = {"Referer": "http://127.0.0.1:8300/deploy", "Origin": "http://127.0.0.1:8300",
             "X-Forwarded-For": "127.0.0.1"}
    assert _denied(client.post("/api/deploy", json={"objective": "x"}, headers={}))
    assert _denied(client.post("/api/deploy", json={"objective": "x"}, headers=spoof))
    assert _denied(client.post("/api/deploy", json={"objective": "x"},
                               headers={"X-Admin-Key": "garbage"}))
    assert _snap() == before


def test_deploy_admin_success(client):
    assert client.post("/api/deploy", json={"label": "ok"}, headers=ADMIN).status_code == 200
