"""test_p5e_withdraw_auth.py — withdrawal and Stripe account creation need a principal.

/api/economy/withdraw was unauthenticated-by-handler: the body named whose balance left.
Now only the authenticated agent (its own balance) or the operator admin key may call it.
"""
import pytest

from app import kassa_payments
from app.deps import state
from tests.test_p5_money_path import ADMIN, _agent

BODY = {"amount": 5, "chain": "base", "confirm": True, "to": "0x0000000000000000000000000000000000000001"}


@pytest.fixture()
def fake_account(monkeypatch):
    import uuid
    acct = f"acct_p5e_{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(kassa_payments, "create_connected_account", lambda **kw: {"account_id": acct})
    return acct


@pytest.fixture(autouse=True)
def _open_gate(monkeypatch):
    """The governance gate blocks every transfer under the default SCOUT posture; these tests are
    about who may ask, so the chain router is replaced by a stub that records the call."""
    import app.routes.economy as economy

    class _Router:
        calls: list = []

        def transfer(self, chain, to, amount, agent_id="", confirm=False):
            self.calls.append(agent_id)
            return {"status": "SIGNED", "chain": chain, "note": "governed transaction stub"}

    monkeypatch.setattr(economy, "_get_chain_router", lambda: _Router())


def _seed(agent_id, amount=50):
    state.economy.treasury.credit(agent_id, amount, reason="test_seed_balance")
    if not state.wallets.find(agent_id, "base", BODY["to"]):      # P5g: destination must be a linked wallet
        state.wallets.link(agent_id, "base", BODY["to"])


def test_anonymous_withdraw_denied(client):
    d, _, _ = _agent(client)
    _seed(d["agent_id"])
    before = state.economy.treasury.balance(d["agent_id"])
    r = client.post("/api/economy/withdraw", json={**BODY, "agent_id": d["agent_id"]})
    assert r.status_code in (401, 403)
    assert state.economy.treasury.balance(d["agent_id"]) == before


def test_wrong_agent_withdraw_forbidden(client):
    victim, _, _ = _agent(client)
    _, _, attacker_jwt = _agent(client)
    _seed(victim["agent_id"])
    before = state.economy.treasury.balance(victim["agent_id"])
    r = client.post("/api/economy/withdraw", json={**BODY, "agent_id": victim["agent_id"]}, headers=attacker_jwt)
    assert r.status_code == 403
    assert state.economy.treasury.balance(victim["agent_id"]) == before


def test_own_agent_withdraw_ok(client):
    d, _, jwt = _agent(client)
    _seed(d["agent_id"])
    r = client.post("/api/economy/withdraw", json={**BODY, "agent_id": d["agent_id"]}, headers=jwt)
    assert r.status_code == 200, r.text
    assert r.json()["withdrawal"]["agent_id"] == d["agent_id"]


def test_own_agent_withdraw_ignores_body_agent_id_when_omitted(client):
    d, _, jwt = _agent(client)
    _seed(d["agent_id"])
    r = client.post("/api/economy/withdraw", json=BODY, headers=jwt)
    assert r.status_code == 200, r.text
    assert r.json()["withdrawal"]["agent_id"] == d["agent_id"]


def test_operator_withdraw_ok(client):
    d, _, _ = _agent(client)
    _seed(d["agent_id"])
    r = client.post("/api/economy/withdraw", json={**BODY, "agent_id": d["agent_id"]}, headers=ADMIN)
    assert r.status_code == 200, r.text
    assert r.json()["withdrawal"]["agent_id"] == d["agent_id"]


def test_operator_withdraw_needs_an_agent_id(client):
    r = client.post("/api/economy/withdraw", json=BODY, headers=ADMIN)
    assert r.status_code == 400


def test_nonpositive_amount_rejected(client):
    d, _, jwt = _agent(client)
    r = client.post("/api/economy/withdraw", json={**BODY, "amount": -5}, headers=jwt)
    assert r.status_code == 400


# ── account creation ────────────────────────────────────────────────────────

def test_anonymous_account_creation_denied(client, fake_account):
    r = client.post("/api/connect/accounts", json={"display_name": "x", "email": "x@x.test"})
    assert r.status_code in (401, 403)


def test_agent_account_is_bound_to_itself(client, fake_account):
    d, _, jwt = _agent(client)
    r = client.post("/api/connect/accounts", json={"display_name": "x", "email": "x@x.test"}, headers=jwt)
    assert r.status_code == 200, r.text
    rec = next(a for a in state.runtime.registry if a["agent_id"] == d["agent_id"])
    assert rec["stripe_account_id"] == fake_account


def test_operator_may_create_an_unbound_account(client, fake_account):
    r = client.post("/api/connect/accounts", json={"display_name": "x", "email": "x@x.test"}, headers=ADMIN)
    assert r.status_code == 200, r.text
    assert not any(a.get("stripe_account_id") == fake_account for a in state.runtime.registry)
