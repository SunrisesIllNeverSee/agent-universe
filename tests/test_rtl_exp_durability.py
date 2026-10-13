"""EXP durability — EXP awarded on a legitimate task close survives restart.

EXP lives on the agent's registry entry. A "restart" is simulated by building
a fresh RuntimeState over the same data root (the way create_app loads it at
startup) and reading the registry it loads from provision.json. The shared
app/deps.state singleton is left untouched. Runs on the session tmp root.
"""
import json
import uuid

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.deps import state
from app.runtime import RuntimeState
from tests.conftest import signup_agent

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


@pytest.fixture
def bare(app):
    from app.routes import missions as m
    a = FastAPI()
    a.include_router(m.router)
    return TestClient(a, raise_server_exceptions=False)


def _agent(client):
    ip = f"10.11.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"exp-{uuid.uuid4().hex[:6]}", ip=ip).json()
    return d["agent_id"], {"Authorization": f"Bearer {d['api_key']}"}


def _prov_path():
    return state.runtime.data_dir / "provision.json"


def _restarted_exp(agent_id):
    rt = RuntimeState(root=state.root, data_dir=state.runtime.data_dir,
                      store=state.runtime.store, audit=state.runtime.audit)
    entry = next(r for r in rt.registry if r.get("agent_id") == agent_id)
    return entry.get("exp", 0), entry.get("exp_by_track", {})


def _live_exp(agent_id):
    entry = next(r for r in state.runtime.registry if r.get("agent_id") == agent_id)
    return entry.get("exp", 0)


def _assigned_task(admin_client, agent_id, **body):
    r = admin_client.post("/api/tasks", json={"title": "t", "type": "research",
                                              "track": "research", **body})
    assert r.status_code == 200, r.text
    tid = r.json()["id"]
    r = admin_client.post(f"/api/tasks/{tid}/assign", json={"agent_id": agent_id})
    assert r.status_code == 200, r.text
    return tid, r.json()["exp_reward"]


def test_operator_close_exp_survives_restart(client, admin_client):
    agent_id, _ = _agent(client)
    before = _live_exp(agent_id)
    tid, reward = _assigned_task(admin_client, agent_id)
    assert reward > 0

    r = admin_client.post(f"/api/tasks/{tid}/close", json={})
    assert r.status_code == 200, r.text
    assert _live_exp(agent_id) == before + reward

    exp, by_track = _restarted_exp(agent_id)
    assert exp == before + reward
    assert by_track.get("research", 0) >= reward


def test_persisted_registry_is_valid_json_after_award(client, admin_client):
    agent_id, _ = _agent(client)
    tid, reward = _assigned_task(admin_client, agent_id)
    assert admin_client.post(f"/api/tasks/{tid}/close", json={}).status_code == 200

    data = json.loads(_prov_path().read_text(encoding="utf-8"))
    entry = next(r for r in data["registry"] if r.get("agent_id") == agent_id)
    assert entry["exp"] == reward
    assert not _prov_path().with_suffix(".json.tmp").exists()


def _denied_close_writes_nothing(caller, tid, headers, agent_id):
    from app.routes import missions as m
    prov_before = _prov_path().read_bytes()
    exp_before = _live_exp(agent_id)
    r = caller.post(f"/api/tasks/{tid}/close", json={}, headers=headers)
    assert r.status_code in (401, 403), r.text
    assert _prov_path().read_bytes() == prov_before
    assert _live_exp(agent_id) == exp_before
    assert _restarted_exp(agent_id)[0] == exp_before
    task = next(t for t in m._load_tasks() if t["id"] == tid)
    assert task["status"] != "closed"


def test_anonymous_close_denied_awards_nothing(client, admin_client):
    agent_id, _ = _agent(client)
    tid, _ = _assigned_task(admin_client, agent_id)
    _denied_close_writes_nothing(client, tid, {}, agent_id)


def test_assignee_close_denied_awards_nothing(client, admin_client):
    agent_id, agent_h = _agent(client)
    tid, _ = _assigned_task(admin_client, agent_id)
    _denied_close_writes_nothing(client, tid, agent_h, agent_id)


def test_wrong_principal_close_denied_at_handler(client, bare):
    # Handler-level owner binding (no edge middleware): a non-owner agent's
    # close is refused before any EXP is credited.
    owner_id, owner_h = _agent(client)
    assignee_id, _ = _agent(client)
    _, other_h = _agent(client)
    r = bare.post("/api/tasks", json={"title": "t"}, headers=owner_h)
    assert r.status_code == 200, r.text
    tid = r.json()["id"]
    r = bare.post(f"/api/tasks/{tid}/assign", json={"agent_id": assignee_id}, headers=owner_h)
    assert r.status_code == 200, r.text
    _denied_close_writes_nothing(bare, tid, other_h, assignee_id)


def test_duplicate_close_does_not_double_award(client, admin_client):
    agent_id, _ = _agent(client)
    before = _live_exp(agent_id)
    tid, reward = _assigned_task(admin_client, agent_id)
    assert admin_client.post(f"/api/tasks/{tid}/close", json={}).status_code == 200
    prov_after_first = _prov_path().read_bytes()

    r = admin_client.post(f"/api/tasks/{tid}/close", json={})
    assert r.status_code == 409
    assert _prov_path().read_bytes() == prov_after_first
    assert _live_exp(agent_id) == before + reward
    assert _restarted_exp(agent_id)[0] == before + reward
