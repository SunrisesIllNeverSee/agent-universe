"""test_p5f_review.py -- findings from the adversarial review of p5e-integration.

1. /api/economy/withdraw asked the chain adapter to move money BEFORE the chargeback-hold gate, so a
   held balance still reached the adapter (and, once adapters are live, the chain). The gate now runs first.
2. A chain adapter answering status "ERROR" (unknown chain) was treated as success: the treasury was
   debited for a transfer that never happened and never reversed.
3. A non-finite amount passed `amount > 0`.
4. MCP agent.cashout queued payout requests with no balance or hold check at all.
"""
import asyncio
import uuid

import pytest

from app.deps import state
from tests.test_p5_money_path import _agent
from tests.test_p5e_mcp_cashout_bind import _call
from tests.test_p5e_mcp_cashout_bind import _agent as _mcp_agent

BODY = {"amount": 30, "chain": "base", "confirm": True, "to": "0x0000000000000000000000000000000000000001"}


class _Router:
    def __init__(self, status="SIGNED", note="live adapter"):
        self.calls, self.status, self.note = [], status, note

    def transfer(self, chain, to, amount, agent_id="", confirm=False):
        self.calls.append((chain, to, amount, agent_id))
        return {"status": self.status, "chain": chain, "note": self.note}


@pytest.fixture()
def router(monkeypatch):
    import app.routes.economy as economy
    r = _Router()
    monkeypatch.setattr(economy, "_get_chain_router", lambda: r)
    return r


def _fund(agent_id, amount):
    state.economy.treasury.credit(agent_id, amount, reason="test_seed_balance")


def test_held_balance_never_reaches_the_chain_adapter(client, router):
    d, _, jwt = _agent(client)
    aid = d["agent_id"]
    _fund(aid, 50)
    state.economy.treasury.hold(aid, 50, reason="card_funded_payout", ref="esc-x")   # all of it held
    before = state.economy.treasury.balance(aid)
    r = client.post("/api/economy/withdraw", json=BODY, headers=jwt)
    assert "matured" in r.json().get("error", "").lower() or "Insufficient" in r.json().get("error", ""), r.text
    assert router.calls == [], "the adapter was asked to move held money"
    assert state.economy.treasury.balance(aid) == before


def test_partly_held_balance_limits_to_matured(client, router):
    d, _, jwt = _agent(client)
    aid = d["agent_id"]
    _fund(aid, 50)
    state.economy.treasury.hold(aid, 30, reason="card_funded_payout", ref="esc-y")   # 20 matured
    assert "error" in client.post("/api/economy/withdraw", json={**BODY, "amount": 21}, headers=jwt).json()
    assert router.calls == []
    r = client.post("/api/economy/withdraw", json={**BODY, "amount": 20}, headers=jwt)
    assert r.status_code == 200 and r.json()["withdrawal"]["amount"] == 20, r.text
    assert len(router.calls) == 1
    assert state.economy.treasury.balance(aid) == 30


def test_adapter_error_status_does_not_debit(client, router):
    router.status = "ERROR"          # what MultiChainRouter returns for an unknown chain
    d, _, jwt = _agent(client)
    aid = d["agent_id"]
    _fund(aid, 50)
    r = client.post("/api/economy/withdraw", json={**BODY, "chain": "nonesuch"}, headers=jwt)
    assert r.status_code == 200 and r.json()["withdrawal"] is None, r.text
    assert state.economy.treasury.balance(aid) == 50


def test_real_router_unknown_chain_does_not_debit(client):
    d, _, jwt = _agent(client)
    aid = d["agent_id"]
    _fund(aid, 50)
    r = client.post("/api/economy/withdraw", json={**BODY, "chain": "nonesuch"}, headers=jwt)
    assert r.json().get("withdrawal") is None, r.text
    assert state.economy.treasury.balance(aid) == 50


def test_infinite_amount_rejected(client, router):
    d, _, jwt = _agent(client)
    r = client.post("/api/economy/withdraw", content='{"amount": Infinity, "chain": "base", "to": "0x1"}',
                    headers={**jwt, "Content-Type": "application/json"})
    assert r.status_code in (400, 422), r.text
    assert router.calls == []


def test_stub_path_needs_a_matured_balance_too(client, router):
    router.note = "governed transaction stub"
    d, _, jwt = _agent(client)          # zero balance
    r = client.post("/api/economy/withdraw", json=BODY, headers=jwt)
    assert "error" in r.json() and "withdrawal" not in r.json(), r.text


# ── MCP agent.cashout ───────────────────────────────────────────────────────

def test_mcp_cashout_refuses_more_than_balance(client):
    d, rec = _mcp_agent(client)
    rec["stripe_account_id"] = "acct_bound"
    out = _call("agent.cashout", api_key=d["api_key"], amount=5.0)      # zero balance
    assert "matured" in out["error"] and not out.get("status")


def test_mcp_cashout_refuses_held_money(client):
    d, rec = _mcp_agent(client)
    rec["stripe_account_id"] = "acct_bound"
    state.economy.treasury.credit(rec["agent_id"], 40, reason="test_seed_balance")
    state.economy.treasury.hold(rec["agent_id"], 40, reason="card_funded_payout", ref="esc-z")
    out = _call("agent.cashout", api_key=d["api_key"], amount=10.0)
    assert "matured" in out["error"] and not out.get("status")


def test_mcp_cashout_matured_balance_queues(client):
    d, rec = _mcp_agent(client)
    rec["stripe_account_id"] = "acct_bound"
    state.economy.treasury.credit(rec["agent_id"], 40, reason="test_seed_balance")
    state.economy.treasury.hold(rec["agent_id"], 30, reason="card_funded_payout", ref="esc-w")
    assert _call("agent.cashout", api_key=d["api_key"], amount=10.0)["status"] == "queued"
    assert "matured" in _call("agent.cashout", api_key=d["api_key"], amount=10.5)["error"]
