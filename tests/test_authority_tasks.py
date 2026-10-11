"""Task principal binding — every task mutation is owner-bound.

The edge middleware keeps /api/tasks admin-only, so the handler-level binding
is exercised on a bare FastAPI app that mounts only the missions router (no
middleware): there the handler is the only gate. A separate test pins the
edge behavior on the full app. Runs on the session tmp root (see conftest).
"""
import json
import uuid

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.deps import state
from tests.conftest import signup_agent

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


@pytest.fixture
def bare(app):
    from app.routes import missions as m
    a = FastAPI()
    a.include_router(m.router)
    return TestClient(a, raise_server_exceptions=False)


def _agent(client):
    ip = f"10.9.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"at-{uuid.uuid4().hex[:6]}", ip=ip).json()
    return d["agent_id"], {"Authorization": f"Bearer {d['api_key']}"}, d


def _lines(name):
    p = state.root / "data" / name
    return len(p.read_text().splitlines()) if p.exists() else 0


def _snap():
    from app.routes import missions as m
    return (json.dumps(m._load_tasks(), sort_keys=True),
            json.dumps(m._load_missions(), sort_keys=True),
            _lines("audit.jsonl"), _lines("seeds.jsonl"))


def _task(bare, headers, **body):
    r = bare.post("/api/tasks", json={"title": "t", **body}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _legacy(task_id=None):
    from app.routes import missions as m
    tid = task_id or f"task-legacy-{uuid.uuid4().hex[:6]}"
    ts = m._load_tasks()
    ts.append({"id": tid, "title": "legacy", "type": "build", "track": "tool",
               "exp_reward": 10, "payout": 0.0, "assigned_agent": None,
               "mission_id": None, "campaign_id": None, "status": "open",
               "deliverable": "", "created_by": "operator"})
    m._save_tasks(ts)
    return tid


def _assigned(bare, owner_h, assignee):
    tid = _task(bare, owner_h)["id"]
    r = bare.post(f"/api/tasks/{tid}/assign", json={"agent_id": assignee}, headers=owner_h)
    assert r.status_code == 200, r.text
    return tid


VERBS = {
    "assign": lambda c, t, h: c.post(f"/api/tasks/{t}/assign", json={"agent_id": "agent-x"}, headers=h),
    "start": lambda c, t, h: c.post(f"/api/tasks/{t}/start", headers=h),
    "deliver": lambda c, t, h: c.post(f"/api/tasks/{t}/deliver", json={"deliverable": "d"}, headers=h),
    "close": lambda c, t, h: c.post(f"/api/tasks/{t}/close", json={}, headers=h),
    "cancel": lambda c, t, h: c.post(f"/api/tasks/{t}/cancel", headers=h),
}
verbs = pytest.mark.parametrize("verb", list(VERBS))


# ── creation ────────────────────────────────────────────────────────────────

def test_agent_creation_records_authentic_owner(client, bare):
    aid, h, _ = _agent(client)
    t = _task(bare, h)
    assert t["owner_agent_id"] == aid and t["created_by"] == "agent"


def test_body_supplied_owner_is_ignored(client, bare):
    aid, h, _ = _agent(client)
    other, _, _ = _agent(client)
    t = _task(bare, h, owner_agent_id=other, created_by="operator", agent_id=other)
    assert t["owner_agent_id"] == aid and t["created_by"] == "agent"


def test_admin_creation_is_operator(bare):
    t = _task(bare, ADMIN, owner_agent_id="agent-forged", created_by="agent")
    assert t["owner_agent_id"] is None and t["created_by"] == "operator"


@pytest.mark.parametrize("hdr", [
    {}, {"Authorization": "Bearer forged-abc"},
    {"X-Admin-Key": "garbage"},
    {"Referer": "https://signomy.xyz/", "Origin": "https://signomy.xyz"},
    {"X-Forwarded-For": "127.0.0.1"},
])
def test_create_unauthenticated_denied_no_write(client, bare, hdr):
    before = _snap()
    assert bare.post("/api/tasks", json={"title": "t"}, headers=hdr).status_code in (401, 403)
    assert _snap() == before


def test_create_garbage_admin_with_other_agent_key_is_that_agent_only(client, bare):
    aid, h, _ = _agent(client)
    t = _task(bare, {**h, "X-Admin-Key": "garbage"})
    assert t["owner_agent_id"] == aid


def test_create_in_foreign_mission_denied(client, bare):
    _, owner_h, _ = _agent(client)
    _, other_h, _ = _agent(client)
    mid = client.post("/api/missions", json={"label": "m"}, headers=owner_h).json()["id"]
    before = _snap()
    r = bare.post("/api/tasks", json={"title": "t", "mission_id": mid}, headers=other_h)
    assert r.status_code == 404  # uniform with unknown mission (existence oracle closed)
    assert r.json() == {"error": "Mission not found", "mission_id": mid}
    assert _snap() == before


def test_create_in_own_mission_allowed(client, bare):
    _, h, _ = _agent(client)
    mid = client.post("/api/missions", json={"label": "m"}, headers=h).json()["id"]
    assert _task(bare, h, mission_id=mid)["mission_id"] == mid


def test_create_in_unknown_mission_404_for_agent(client, bare):
    _, h, _ = _agent(client)
    before = _snap()
    assert bare.post("/api/tasks", json={"title": "t", "mission_id": "mission-nope"}, headers=h).status_code == 404
    assert _snap() == before


def test_agent_cannot_attach_campaign(client, bare):
    _, h, _ = _agent(client)
    before = _snap()
    assert bare.post("/api/tasks", json={"title": "t", "campaign_id": "c1"}, headers=h).status_code == 403
    assert _snap() == before


# ── per-verb authorization ──────────────────────────────────────────────────

@verbs
def test_anonymous_denied_no_write(client, bare, verb):
    _, h, _ = _agent(client)
    tid = _task(bare, h)["id"]
    before = _snap()
    assert VERBS[verb](bare, tid, {}).status_code in (401, 403)
    assert _snap() == before


@verbs
def test_forged_headers_denied_no_write(client, bare, verb):
    _, h, _ = _agent(client)
    tid = _task(bare, h)["id"]
    before = _snap()
    for hdr in ({"Authorization": "Bearer forged-" + uuid.uuid4().hex},
                {"X-Admin-Key": "garbage"},
                {"Referer": "https://signomy.xyz/", "Origin": "https://signomy.xyz",
                 "X-Forwarded-For": "127.0.0.1"}):
        assert VERBS[verb](bare, tid, hdr).status_code in (401, 403)
    assert _snap() == before


@verbs
def test_revoked_key_denied_no_write(client, admin_client, bare, verb):
    aid, h, _ = _agent(client)
    tid = _task(bare, h)["id"]
    assert admin_client.post("/api/provision/revoke", json={"agent_id": aid}).status_code == 200
    before = _snap()
    assert VERBS[verb](bare, tid, h).status_code in (401, 403)
    assert _snap() == before


@verbs
def test_wrong_agent_denied_no_write(client, bare, verb):
    _, owner_h, _ = _agent(client)
    _, other_h, _ = _agent(client)
    tid = _task(bare, owner_h)["id"]
    before = _snap()
    assert VERBS[verb](bare, tid, other_h).status_code == 403
    assert _snap() == before


@verbs
def test_garbage_admin_header_with_other_agent_key_denied(client, bare, verb):
    _, owner_h, _ = _agent(client)
    _, other_h, _ = _agent(client)
    tid = _task(bare, owner_h)["id"]
    before = _snap()
    assert VERBS[verb](bare, tid, {**other_h, "X-Admin-Key": "garbage"}).status_code == 403
    assert _snap() == before


@verbs
def test_owner_allowed(client, bare, verb):
    _, h, _ = _agent(client)
    tid = _task(bare, h)["id"]
    assert VERBS[verb](bare, tid, h).status_code == 200


@verbs
def test_admin_allowed_on_agent_task(client, bare, verb):
    _, h, _ = _agent(client)
    tid = _task(bare, h)["id"]
    assert VERBS[verb](bare, tid, ADMIN).status_code == 200


@verbs
def test_legacy_ownerless_denied_for_agent_allowed_for_admin(client, bare, verb):
    tid = _legacy()
    _, h, _ = _agent(client)
    before = _snap()
    assert VERBS[verb](bare, tid, h).status_code == 403
    assert _snap() == before
    assert VERBS[verb](bare, tid, ADMIN).status_code == 200


@verbs
def test_operator_created_task_denied_for_agents(client, bare, verb):
    tid = _task(bare, ADMIN)["id"]
    _, h, _ = _agent(client)
    before = _snap()
    assert VERBS[verb](bare, tid, h).status_code == 403
    assert _snap() == before


@verbs
def test_jwt_does_not_authorize(client, bare, verb):
    aid, h, d = _agent(client)
    _, owner_h, _ = _agent(client)
    tid = _task(bare, owner_h)["id"]
    tok = d.get("token") or d.get("jwt") or "x"
    before = _snap()
    assert VERBS[verb](bare, tid, {"Authorization": f"Bearer {tok}"}).status_code in (401, 403)
    assert _snap() == before


@verbs
def test_unknown_task_404_for_agent_401_for_anonymous(client, bare, verb):
    _, h, _ = _agent(client)
    assert VERBS[verb](bare, "task-nope", h).status_code == 404
    assert VERBS[verb](bare, "task-nope", {}).status_code in (401, 403)


# ── assignee paths (assigned_agent is the recorded role) ────────────────────

@pytest.mark.parametrize("verb", ["start", "deliver"])
def test_assignee_may_start_and_deliver(client, bare, verb):
    _, owner_h, _ = _agent(client)
    aid, ah, _ = _agent(client)
    tid = _assigned(bare, owner_h, aid)
    assert VERBS[verb](bare, tid, ah).status_code == 200


@pytest.mark.parametrize("verb", ["assign", "close", "cancel"])
def test_assignee_may_not_assign_close_cancel(client, bare, verb):
    _, owner_h, _ = _agent(client)
    aid, ah, _ = _agent(client)
    tid = _assigned(bare, owner_h, aid)
    before = _snap()
    # assign on non-open task would 409 for the owner; the assignee is denied first
    assert VERBS[verb](bare, tid, ah).status_code == 403
    assert _snap() == before


def test_assignee_on_ownerless_legacy_task_denied(client, bare):
    from app.routes import missions as m
    aid, ah, _ = _agent(client)
    tid = _legacy()
    ts = m._load_tasks()
    next(t for t in ts if t["id"] == tid)["assigned_agent"] = aid
    m._save_tasks(ts)
    before = _snap()
    assert VERBS["deliver"](bare, tid, ah).status_code == 403
    assert _snap() == before


# ── edge behavior pinned ────────────────────────────────────────────────────

def test_edge_keeps_tasks_admin_only_for_agents(client):
    _, h, _ = _agent(client)
    assert client.post("/api/tasks", json={"title": "t"}, headers=h).status_code == 403
