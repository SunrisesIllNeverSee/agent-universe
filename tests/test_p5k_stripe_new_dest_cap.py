"""test_p5k_stripe_new_dest_cap.py — the on-chain new-wallet rule applied to Stripe cashout:
$25 cumulative for 24h after an account is bound; over that, reserve + pending approval in the
shared queue (kind=stripe, destination snapshotted); approve transfers once, reject refunds."""
import asyncio
from datetime import datetime, timedelta

import pytest

from app import kassa_payments
from app.deps import state
from tests.test_p5_money_path import ADMIN, _agent


@pytest.fixture
def stripe(monkeypatch):
    calls = []
    monkeypatch.setattr(kassa_payments, "create_connected_account",
                        lambda **kw: {"account_id": f"acct_{len(calls)}_{id(kw)}"})
    monkeypatch.setattr(kassa_payments, "get_account_status", lambda acct: {"charges_enabled": True})

    def transfer(**kw):
        calls.append(kw)
        return {"transfer_id": f"tr_{len(calls)}"}
    monkeypatch.setattr(kassa_payments, "create_transfer", transfer)
    return calls


def _setup(client, balance=200):
    d, _, jwt = _agent(client)
    acct = client.post("/api/connect/accounts", json={"display_name": "x", "email": "x@x.test"}, headers=jwt).json()["account_id"]
    state.economy.treasury.credit(d["agent_id"], balance, reason="test_seed_balance")
    return d["agent_id"], jwt, acct


def _co(client, jwt, amount):
    return client.post("/api/connect/cashout", json={"amount": amount}, headers=jwt)


def _bal(aid):
    return state.economy.treasury.balance(aid)


def _age(hours):
    c = state.wallets._conn
    for k, a, v in c.execute("SELECT agent_id, account_id, first_bound_at FROM stripe_bindings").fetchall():
        c.execute("UPDATE stripe_bindings SET first_bound_at=? WHERE agent_id=? AND account_id=?",
                  ((datetime.fromisoformat(v) - timedelta(hours=hours)).isoformat(), k, a))


def test_under_cap_pays_directly_and_cap_is_cumulative(client, stripe):
    aid, jwt, _ = _setup(client)
    assert _co(client, jwt, 10).status_code == 200
    assert _co(client, jwt, 15).status_code == 200      # exactly $25 total
    assert len(stripe) == 2
    r = _co(client, jwt, 1)                              # pushes past $25
    assert r.status_code == 202 and r.json()["status"] == "pending_approval"
    assert len(stripe) == 2 and _bal(aid) == 200 - 25 - 1


def test_over_cap_first_request_reserves_and_queues(client, stripe):
    aid, jwt, acct = _setup(client)
    r = _co(client, jwt, 60)
    assert r.status_code == 202, r.text
    assert stripe == [] and _bal(aid) == 140
    q = client.get("/api/operator/payout-approvals", headers=ADMIN).json()["approvals"]
    a = next(x for x in q if x["approval_id"] == r.json()["approval_id"])
    assert a["kind"] == "stripe" and a["address"] == acct and a["amount"] == 60 and a["status"] == "pending"


def test_approve_transfers_once_to_snapshotted_account(client, stripe):
    aid, jwt, acct = _setup(client)
    apr = _co(client, jwt, 60).json()["approval_id"]
    rec = next(a for a in state.runtime.registry if a["agent_id"] == aid)
    rec["stripe_account_id"] = "acct_rebound_elsewhere"      # rebind after the request
    r = client.post(f"/api/operator/payout-approvals/{apr}/approve", headers=ADMIN)
    assert r.status_code == 200, r.text
    assert len(stripe) == 1 and stripe[0]["connected_account_id"] == acct and stripe[0]["amount_cents"] == 6000
    assert client.post(f"/api/operator/payout-approvals/{apr}/approve", headers=ADMIN).status_code == 409
    assert len(stripe) == 1 and _bal(aid) == 140


def test_failed_transfer_on_approve_stays_pending_then_retries(client, stripe, monkeypatch):
    aid, jwt, _ = _setup(client)
    apr = _co(client, jwt, 60).json()["approval_id"]
    monkeypatch.setattr(kassa_payments, "create_transfer", lambda **kw: {"error": "stripe down"})
    assert client.post(f"/api/operator/payout-approvals/{apr}/approve", headers=ADMIN).status_code == 502
    assert state.wallets.get_approval(apr)["status"] == "pending" and _bal(aid) == 140
    monkeypatch.setattr(kassa_payments, "create_transfer", lambda **kw: {"transfer_id": "tr_ok"})
    assert client.post(f"/api/operator/payout-approvals/{apr}/approve", headers=ADMIN).status_code == 200


def test_reject_refunds_and_frees_cap(client, stripe):
    aid, jwt, _ = _setup(client)
    apr = _co(client, jwt, 60).json()["approval_id"]
    assert client.post(f"/api/operator/payout-approvals/{apr}/reject", headers=ADMIN).status_code == 200
    assert _bal(aid) == 200 and stripe == []
    assert _co(client, jwt, 25).status_code == 200       # cap usage freed


def test_window_expiry_pays_directly(client, stripe):
    aid, jwt, _ = _setup(client)
    _age(25)
    r = _co(client, jwt, 100)
    assert r.status_code == 200 and len(stripe) == 1


def test_failed_direct_transfer_does_not_consume_cap(client, stripe, monkeypatch):
    aid, jwt, _ = _setup(client)
    monkeypatch.setattr(kassa_payments, "create_transfer", lambda **kw: {"error": "stripe down"})
    assert _co(client, jwt, 20).status_code == 502
    monkeypatch.setattr(kassa_payments, "create_transfer", lambda **kw: {"transfer_id": "tr_ok"})
    assert _co(client, jwt, 25).status_code == 200


def test_rebind_to_new_account_starts_new_window(client, stripe):
    aid, jwt, acct1 = _setup(client)
    _age(25)
    assert _co(client, jwt, 100).status_code == 200      # old account is past its window
    from app.routes.connect import _bind_stripe_account
    rec = next(a for a in state.runtime.registry if a["agent_id"] == aid)
    _bind_stripe_account(rec, "acct_second")
    assert _co(client, jwt, 40).status_code == 202       # new account: capped again
    _bind_stripe_account(rec, acct1)                     # back to the matured one: rebinding does not reset
    assert _co(client, jwt, 40).status_code == 200


def test_over_cap_needs_matured_balance(client, stripe):
    aid, jwt, _ = _setup(client, balance=30)
    r = _co(client, jwt, 40)
    assert r.status_code == 400 and _bal(aid) == 30


# ── MCP ─────────────────────────────────────────────────────────────────────

def _call(tool, **args):
    res = asyncio.run(state.mcp_bridge.build_fastmcp().call_tool(tool, args))
    sc = getattr(res, "structured_content", None)
    return res[1] if sc is None and isinstance(res, tuple) else sc


def test_mcp_tool_count_still_41(app):
    assert len(asyncio.run(state.mcp_bridge.build_fastmcp().list_tools())) == 41


def test_mcp_cashout_under_cap_queues_over_cap_pends(client, stripe):
    d, key, _ = _agent(client)[0], None, None
    aid = d["agent_id"]
    rec = next(a for a in state.runtime.registry if a["agent_id"] == aid)
    rec["stripe_account_id"] = "acct_mcp"
    state.economy.treasury.credit(aid, 100, reason="test_seed_balance")
    assert _call("agent.cashout", api_key=d["api_key"], amount=20.0)["status"] == "queued"
    # P5m owner decision: queued requests do not count against the cap, so the over-cap probe is $26.
    out = _call("agent.cashout", api_key=d["api_key"], amount=26.0)
    assert out["status"] == "pending_approval" and out["account"] == "acct_mcp"
    assert _bal(aid) == 74
    a = state.wallets.get_approval(out["approval_id"])
    assert a["kind"] == "stripe" and a["address"] == "acct_mcp"
