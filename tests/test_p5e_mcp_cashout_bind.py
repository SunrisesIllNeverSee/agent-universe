"""P5e -- MCP agent.cashout resolves its destination only from the agent's bound Stripe account
(same binding the HTTP cashout uses); a caller-supplied connected_account_id never selects it."""
import asyncio
import uuid

from app.deps import state
from tests.conftest import signup_agent


def _mcp():
    return state.mcp_bridge.build_fastmcp()


def _call(tool, **args):
    res = asyncio.run(_mcp().call_tool(tool, args))
    sc = getattr(res, "structured_content", None)
    if sc is None and isinstance(res, tuple):
        sc = res[1]
    return sc


def _agent(client):
    ip = f"10.8.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"p5e-{uuid.uuid4().hex[:6]}", ip=ip).json()
    rec = next(a for a in state.runtime.registry if a["agent_id"] == d["agent_id"])
    return d, rec


def test_tool_count_still_41(app):
    assert len(asyncio.run(_mcp().list_tools())) == 41


def test_unbound_agent_gets_clear_error(client):
    d, _ = _agent(client)
    out = _call("agent.cashout", api_key=d["api_key"], amount=5.0)
    assert "No Stripe account linked" in out["error"]
    out = _call("agent.cashout", api_key=d["api_key"], amount=5.0, connected_account_id="acct_attacker")
    assert "No Stripe account linked" in out["error"]
    assert not out.get("status")


def test_foreign_account_rejected(client):
    d, rec = _agent(client)
    rec["stripe_account_id"] = "acct_bound"
    out = _call("agent.cashout", api_key=d["api_key"], amount=5.0, connected_account_id="acct_attacker")
    assert "not this agent's linked account" in out["error"]
    assert not out.get("status")


def test_destination_is_bound_account_when_omitted_or_matching(client):
    d, rec = _agent(client)
    rec["stripe_account_id"] = "acct_bound"
    for kw in ({}, {"connected_account_id": "acct_bound"}):
        out = _call("agent.cashout", api_key=d["api_key"], amount=5.0, **kw)
        assert out["status"] == "queued" and out["account"] == "acct_bound", out


def test_bad_amount_and_key(client):
    d, rec = _agent(client)
    rec["stripe_account_id"] = "acct_bound"
    assert "positive" in _call("agent.cashout", api_key=d["api_key"], amount=0)["error"]
    assert "positive" in _call("agent.cashout", api_key=d["api_key"], amount=float("nan"))["error"]
    assert "Invalid api_key" in _call("agent.cashout", api_key="nope", amount=1.0)["error"]
