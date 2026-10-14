"""test_p5m_mcp_queued_not_counted.py — owner decision (P5m): an MCP agent.cashout that is only
'queued' moves no money, so it must not consume the $25 new-destination cap. The cap is enforced
where money actually moves (HTTP cashout) and over-cap MCP requests still go to approval."""
from app.deps import state
from tests.test_p5k_stripe_new_dest_cap import _bal, _call, _co, stripe  # noqa: F401


def _used(aid):
    return state.wallets._conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM wallet_payouts WHERE agent_id=? AND status='counted'", (aid,)).fetchone()[0]


def test_queued_mcp_cashouts_leave_cap_untouched(client, stripe):
    from tests.test_p5_money_path import _agent
    d, _, jwt = _agent(client)
    aid = d["agent_id"]
    client.post("/api/connect/accounts", json={"display_name": "x", "email": "x@x.test"}, headers=jwt)
    state.economy.treasury.credit(aid, 500, reason="test_seed_balance")
    for _ in range(10):
        assert _call("agent.cashout", api_key=d["api_key"], amount=5.0)["status"] == "queued"
    assert _used(aid) == 0 and stripe == []
    # A real HTTP cashout of the full $25 still pays automatically.
    r = _co(client, jwt, 25)
    assert r.status_code == 200, r.text
    assert len(stripe) == 1 and _used(aid) == 25
    # And the cap is now truly spent: one more dollar needs approval.
    assert _co(client, jwt, 1).status_code == 202


def test_over_cap_mcp_still_goes_to_approval(client, stripe):
    from tests.test_p5_money_path import _agent
    d, _, jwt = _agent(client)
    aid = d["agent_id"]
    client.post("/api/connect/accounts", json={"display_name": "x", "email": "x@x.test"}, headers=jwt)
    state.economy.treasury.credit(aid, 500, reason="test_seed_balance")
    for _ in range(10):
        assert _call("agent.cashout", api_key=d["api_key"], amount=5.0)["status"] == "queued"
    out = _call("agent.cashout", api_key=d["api_key"], amount=26.0)
    assert out["status"] == "pending_approval"
    assert _bal(aid) == 500 - 26 and stripe == []


def test_http_cashout_26_after_queued_mcp_goes_to_approval(client, stripe):
    from tests.test_p5_money_path import _agent
    d, _, jwt = _agent(client)
    aid = d["agent_id"]
    client.post("/api/connect/accounts", json={"display_name": "x", "email": "x@x.test"}, headers=jwt)
    state.economy.treasury.credit(aid, 500, reason="test_seed_balance")
    for _ in range(3):
        assert _call("agent.cashout", api_key=d["api_key"], amount=5.0)["status"] == "queued"
    r = _co(client, jwt, 26)
    assert r.status_code == 202 and r.json()["status"] == "pending_approval"
    assert stripe == []
