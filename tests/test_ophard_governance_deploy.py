"""Operational hardening — global governance/deploy mutations are operator-only.

POST /api/governance (global mode/posture/role) and POST /api/deploy (global
DEPLOY board) are admin-key only. Live agent Bearer keys reach these prefixes
through the middleware but hold no authority over global state; every denial
must leave governance state, deploy state, audit.jsonl and seeds.jsonl
untouched. /api/governance/check is a pure evaluation and stays agent-callable.
Runs on the session tmp root (see conftest), never real data/.
"""
import uuid

import pytest

from app.deps import state
from tests.conftest import signup_agent

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}
GARBAGE = {"X-Admin-Key": "garbage"}


def _agent(client):
    ip = f"10.8.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"og-{uuid.uuid4().hex[:6]}", ip=ip).json()
    return d, {"Authorization": f"Bearer {d['api_key']}"}


def _lines(name):
    p = state.root / "data" / name
    return len(p.read_text().splitlines()) if p.exists() else 0


def _snap():
    rt = state.runtime
    return (
        rt.governance.model_dump_json(),
        rt.deploy.model_dump_json(),
        _lines("audit.jsonl"),
        _lines("seeds.jsonl"),
    )


def _gov(c, h, body=None):
    return c.post("/api/governance", json=body or {"mode": "high-security", "posture": "defensive", "role": "observer"}, headers=h)


def _dep(c, h, body=None):
    return c.post("/api/deploy", json=body or {"objective": f"forged-{uuid.uuid4().hex[:6]}"}, headers=h)


ROUTES = pytest.mark.parametrize("call", [_gov, _dep], ids=["governance", "deploy"])
SPOOFS = pytest.mark.parametrize("body", [
    {"role": "primary", "agent_id": "operator", "operator": True, "objective": "x", "mode": "none"},
    {"mode": "high-security", "posture": "scout", "role": "observer", "objective": "y", "is_admin": True},
], ids=["spoof-a", "spoof-b"])


def _denied(r):
    return r.status_code in (401, 403)


@ROUTES
def test_agent_key_denied_no_state_change(client, call):
    _, h = _agent(client)
    before = _snap()
    assert _denied(call(client, h))
    assert _snap() == before


@ROUTES
def test_agent_key_with_garbage_admin_key_denied(client, call):
    _, h = _agent(client)
    before = _snap()
    assert _denied(call(client, {**h, **GARBAGE}))
    assert _snap() == before


@ROUTES
@SPOOFS
def test_body_spoof_fields_denied(client, call, body):
    _, h = _agent(client)
    before = _snap()
    assert _denied(call(client, h, body))
    assert _snap() == before


@ROUTES
def test_revoked_key_denied(client, admin_client, call):
    d, h = _agent(client)
    assert admin_client.post("/api/provision/revoke", json={"agent_id": d["agent_id"]}).status_code == 200
    before = _snap()
    assert _denied(call(client, h))
    assert _snap() == before


@ROUTES
def test_jwt_instead_of_api_key_denied(client, call):
    d, _ = _agent(client)
    tok = d.get("token") or d.get("jwt") or "x"
    before = _snap()
    assert _denied(call(client, {"Authorization": f"Bearer {tok}"}))
    assert _snap() == before


@ROUTES
def test_anonymous_and_garbage_admin_denied(client, call):
    before = _snap()
    assert _denied(call(client, {}))
    assert _denied(call(client, GARBAGE))
    assert _snap() == before


def test_admin_governance_success_changes_state(client):
    before = _snap()
    r = _gov(client, ADMIN)
    assert r.status_code == 200
    assert r.json()["posture"] == "defensive"
    assert _snap() != before


def test_admin_deploy_success_changes_state(client):
    before = _snap()
    obj = f"ok-{uuid.uuid4().hex[:6]}"
    r = _dep(client, ADMIN, {"objective": obj})
    assert r.status_code == 200
    assert r.json()["objective"] == obj
    assert _snap() != before


def test_governance_check_stays_agent_callable_and_read_only(client):
    _, h = _agent(client)
    before = _snap()
    r = client.post("/api/governance/check", json={"action": "read a file"}, headers=h)
    assert r.status_code == 200
    assert _snap() == before


def test_agent_meeting_flow_still_bound_to_own_identity(client):
    """Meeting routes already bind actor to the Bearer principal; unchanged."""
    d, h = _agent(client)
    other, _ = _agent(client)
    r = client.post("/api/governance/meeting", json={"caller": d["agent_id"], "subject": "s", "quorum": 1}, headers=h)
    assert r.status_code == 200, r.text
    mid = r.json()["id"]
    assert client.post(f"/api/governance/meeting/{mid}/join", json={"agent_id": other["agent_id"]}, headers=h).status_code == 403
    assert client.post(f"/api/governance/meeting/{mid}/adjourn", headers=h).status_code == 200
