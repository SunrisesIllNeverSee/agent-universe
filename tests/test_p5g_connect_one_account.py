"""
test_p5g_connect_one_account.py -- one Stripe Connect account per agent.

An agent with a bound account gets 409 (naming it) instead of a second account, on both the v1 and
v2 create routes, and cannot re-bind itself; the operator (admin key) may still create more.
"""
import uuid

import pytest

from app import kassa_payments
from app.deps import state
from tests.conftest import signup_agent

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}
BODY = {"display_name": "x", "email": "x@x.test"}


def _agent(client):
    ip = f"10.57.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"oa-{uuid.uuid4().hex[:6]}", ip=ip).json()
    rec = next(a for a in state.runtime.registry if a["agent_id"] == d["agent_id"])
    return rec, {"Authorization": f"Bearer {d['token']}"}


@pytest.fixture
def fake_stripe(monkeypatch):
    calls = {"n": 0}

    def make(**kw):
        calls["n"] += 1
        return {"account_id": f"acct_{uuid.uuid4().hex[:8]}"}
    monkeypatch.setattr(kassa_payments, "create_connected_account", make)
    monkeypatch.setattr(kassa_payments, "create_recipient_account", make)
    return calls


def test_second_create_returns_409_with_existing_id(client, fake_stripe):
    rec, jwt = _agent(client)
    first = client.post("/api/connect/accounts", json=BODY, headers=jwt)
    assert first.status_code == 200, first.text
    acct = first.json()["account_id"]
    second = client.post("/api/connect/accounts", json=BODY, headers=jwt)
    assert second.status_code == 409
    assert second.json()["detail"]["account_id"] == acct
    assert fake_stripe["n"] == 1  # nothing created at Stripe the second time
    assert rec["stripe_account_id"] == acct


def test_v2_route_also_blocked_and_cannot_rebind(client, fake_stripe):
    rec, jwt = _agent(client)
    acct = client.post("/api/connect/accounts", json=BODY, headers=jwt).json()["account_id"]
    r = client.post("/api/connect/v2/accounts", json=BODY, headers=jwt)
    assert r.status_code == 409 and r.json()["detail"]["account_id"] == acct
    assert fake_stripe["n"] == 1
    assert rec["stripe_account_id"] == acct


def test_v2_first_create_binds_then_v1_blocked(client, fake_stripe):
    rec, jwt = _agent(client)
    acct = client.post("/api/connect/v2/accounts", json=BODY, headers=jwt).json()["account_id"]
    r = client.post("/api/connect/accounts", json=BODY, headers=jwt)
    assert r.status_code == 409 and r.json()["detail"]["account_id"] == acct


def test_other_agents_unaffected(client, fake_stripe):
    _, jwt_a = _agent(client)
    rec_b, jwt_b = _agent(client)
    client.post("/api/connect/accounts", json=BODY, headers=jwt_a)
    r = client.post("/api/connect/accounts", json=BODY, headers=jwt_b)
    assert r.status_code == 200
    assert rec_b["stripe_account_id"] == r.json()["account_id"]


def test_operator_may_create_more_unbound(client, fake_stripe):
    rec, jwt = _agent(client)
    acct = client.post("/api/connect/accounts", json=BODY, headers=jwt).json()["account_id"]
    for _ in range(2):
        r = client.post("/api/connect/accounts", json=BODY, headers=ADMIN)
        assert r.status_code == 200, r.text
        assert r.json()["account_id"] != acct
    assert rec["stripe_account_id"] == acct  # admin-only creates do not touch the agent binding
