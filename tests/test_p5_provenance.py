"""P5 provenance closure: MCP write paths seed like REST, trial lifecycle is
provenanced, and money-route Seed failures are loud (audit provenance_failed),
never silent and never a failed user action."""
import ast
import asyncio
import uuid
from pathlib import Path

import pytest

from tests.conftest import signup_agent
from tests.test_p4_entry_api import _post


def _mcp():
    from app.deps import state
    return state.mcp_bridge.build_fastmcp()


def _call(tool, **args):
    res = asyncio.run(_mcp().call_tool(tool, args))
    sc = getattr(res, "structured_content", None)
    if sc is None and isinstance(res, tuple):
        sc = res[1]
    return sc


def _key(client):
    ip = f"10.7.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"pv-{uuid.uuid4().hex[:6]}", ip=ip).json()
    lg = client.post("/api/provision/login", json={"agent_id": d["agent_id"], "api_key": d["api_key"]},
                     headers={"x-forwarded-for": ip})
    return {"id": d["agent_id"], "name": d.get("name") or d["agent_id"], "key": d["api_key"],
            "jwt": {"Authorization": f"Bearer {lg.json()['token']}"}}


def _seed_for(doi):
    from app.seeds import _read_seeds
    return next((s for s in _read_seeds() if s["doi"] == doi), None)


def _failed_events(action):
    from app.deps import state
    return [e for e in state.audit.recent(500)
            if e.action == "provenance_failed" and (e.detail or {}).get("action") == action]


@pytest.fixture
def boom(monkeypatch):
    from app import seeds

    async def _boom(**_):
        raise RuntimeError("seed store down")
    monkeypatch.setattr(seeds, "create_seed", _boom)


# ── MCP paths now write the same Seed REST writes ───────────────────────────

def test_mcp_register_seeds_registration(client):
    h = f"pv-{uuid.uuid4().hex[:8]}"
    r = _call("agent.register", handle=h, name=f"N-{h}", capabilities=["x"])
    assert r["provenance_error"] is False
    s = _seed_for(r["seed_doi"])
    assert (s["source_type"], s["seed_type"], s["creator_id"]) == ("registration", "planted", r["agent_id"])
    assert s["metadata"]["capabilities"] == ["x"]


def test_mcp_post_seeds_kassa_post(client):
    a = _key(client)
    r = _call("market.post", api_key=a["key"], title="T", category="iso", body="body")
    assert r["provenance_error"] is False
    s = _seed_for(r["seed_doi"])
    assert (s["source_type"], s["source_id"], s["creator_id"]) == ("kassa_post", r["post_id"], a["id"])
    assert s["metadata"]["tab"] == "iso"


def test_mcp_stake_and_message_seed(client):
    poster, staker = _key(client), _key(client)
    pid = _post(poster["id"])
    st = _call("market.stake", api_key=staker["key"], post_id=pid, amount=5, message="hello")
    assert st["provenance_error"] is False, st
    s = _seed_for(st["seed_doi"])
    assert (s["source_type"], s["source_id"], s["metadata"]["post_id"]) == ("stake", st["stake_id"], pid)
    t = _seed_for(st["thread_seed_doi"])
    assert (t["source_type"], t["source_id"]) == ("thread", st["thread_id"])
    m = _call("market.message", api_key=staker["key"], thread_id=st["thread_id"], body="more")
    assert m["status"] == "sent" and m["provenance_error"] is False
    ms = _seed_for(m["seed_doi"])
    assert (ms["source_type"], ms["source_id"], ms["metadata"]["thread_id"]) == ("message", m["message_id"], st["thread_id"])


def test_mcp_vote_seeds_vote(client, admin_client):
    a = _key(client)
    me = _call("agent.status", api_key=a["key"])["agent"]["name"]
    mid = admin_client.post("/api/governance/meeting", json={"caller": me, "subject": "S", "quorum": 1}).json()["id"]
    mr = admin_client.post(f"/api/governance/meeting/{mid}/motion",
                           json={"proposer": me, "motion": "Approve the budget for Q4 planning"})
    assert mr.status_code == 200, mr.text
    mo = mr.json()["id"]
    r = _call("govern.vote", api_key=a["key"], motion_id=mo, vote="yea")
    assert r["recorded"] is True and r["provenance_error"] is False, r
    s = _seed_for(r["seed_doi"])
    assert (s["source_type"], s["seed_type"], s["source_id"]) == ("vote", "touched", f"{mid}-{mo}-{me}")


def test_mcp_seed_failure_is_loud_and_never_fails_the_action(client, boom):
    a = _key(client)
    r = _call("market.post", api_key=a["key"], title="T2", category="iso", body="body")
    assert r["status"] == "pending" and r["post_id"]
    assert r["seed_doi"] is None and r["provenance_error"] is True
    assert any(e.detail.get("source_id") == r["post_id"] for e in _failed_events("post_submitted_mcp"))


# ── trial lifecycle ─────────────────────────────────────────────────────────

def _trial_returned(admin_client, agent_id, liability=7.5):
    from app.deps import state
    admin_client.post("/api/economy/trial/init", json={"agent_id": agent_id})
    state.economy.trials.record_trial_mission(agent_id, liability)
    return admin_client.post("/api/economy/trial/depart", json={"agent_id": agent_id}).json()


def test_trial_init_depart_return_settle_all_seed(admin_client):
    ag = f"trial-{uuid.uuid4().hex[:6]}"
    init = admin_client.post("/api/economy/trial/init", json={"agent_id": ag}).json()
    assert _seed_for(init["seed_doi"])["source_type"] == "trial_start"
    from app.deps import state
    state.economy.trials.record_trial_mission(ag, 7.5)
    dep = admin_client.post("/api/economy/trial/depart", json={"agent_id": ag}).json()
    assert dep["departed"] and dep["provenance_error"] is False
    assert _seed_for(dep["seed_doi"])["source_type"] == "trial_depart"
    ret = admin_client.post("/api/economy/trial/return", json={"agent_id": ag}).json()
    assert ret["returned"] and _seed_for(ret["seed_doi"])["source_type"] == "trial_return"
    st = admin_client.post("/api/economy/trial/settle", json={"agent_id": ag, "amount": ret["settlement_due"]}).json()
    assert st["settled"] and st["provenance_error"] is False
    s = _seed_for(st["seed_doi"])
    assert (s["source_type"], s["seed_type"], s["creator_id"]) == ("trial_settle", "grown", ag)


def test_trial_refused_transitions_write_no_seed(admin_client):
    ag = f"trial-{uuid.uuid4().hex[:6]}"
    admin_client.post("/api/economy/trial/init", json={"agent_id": ag})
    r = admin_client.post("/api/economy/trial/return", json={"agent_id": ag}).json()
    assert "error" in r and "seed_doi" not in r
    r = admin_client.post("/api/economy/trial/settle", json={"agent_id": ag, "amount": 0}).json()
    assert "error" in r and "seed_doi" not in r


def test_trial_settle_binds_agent_to_caller_jwt(client, admin_client):
    me, other = _key(client), _key(client)
    for who in (me, other):
        _trial_returned(admin_client, who["id"])
        admin_client.post("/api/economy/trial/return", json={"agent_id": who["id"]})
    hdr = {"X-Admin-Key": "test-admin-key-12345", **other["jwt"]}
    # another agent's JWT cannot settle me
    r = client.post("/api/economy/trial/settle", json={"agent_id": me["id"], "amount": 7.5}, headers=hdr)
    assert r.status_code == 403
    # own JWT settles self
    r = client.post("/api/economy/trial/settle", json={"agent_id": other["id"], "amount": 7.5}, headers=hdr)
    assert r.status_code == 200 and r.json()["settled"] is True
    # no JWT, admin key only: unchanged
    r = admin_client.post("/api/economy/trial/settle", json={"agent_id": me["id"], "amount": 7.5})
    assert r.status_code == 200 and r.json()["settled"] is True


def test_trial_settle_without_admin_key_still_refused(client):
    me = _key(client)
    r = client.post("/api/economy/trial/settle", json={"agent_id": me["id"], "amount": 1}, headers=me["jwt"])
    assert r.status_code in (401, 403)


def test_trial_seed_failure_is_loud_not_a_failed_settle(admin_client, boom):
    ag = f"trial-{uuid.uuid4().hex[:6]}"
    _trial_returned(admin_client, ag)
    admin_client.post("/api/economy/trial/return", json={"agent_id": ag})
    r = admin_client.post("/api/economy/trial/settle", json={"agent_id": ag, "amount": 7.5})
    assert r.status_code == 200
    b = r.json()
    assert b["settled"] is True and b["seed_doi"] is None and b["provenance_error"] is True
    assert any(e.detail.get("source_id") == ag for e in _failed_events("trial_settle"))


def test_trial_init_seed_failure_audited(admin_client, boom):
    ag = f"trial-{uuid.uuid4().hex[:6]}"
    r = admin_client.post("/api/economy/trial/init", json={"agent_id": ag})
    assert r.status_code == 200 and r.json()["seed_doi"] is None
    assert any(e.detail.get("source_id") == ag for e in _failed_events("trial_start"))


# ── sweep guard: no silent `except: pass` around create_seed in money routes ──

@pytest.mark.parametrize("name", ["connect", "kassa", "economy", "missions"])
def test_money_routes_have_no_silent_seed_swallow(name):
    src = (Path(__file__).resolve().parent.parent / "app" / "routes" / f"{name}.py").read_text()
    offenders = []
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Try):
            continue
        has_seed = any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "create_seed"
                       for b in node.body for n in ast.walk(b))
        if has_seed and any(all(isinstance(s, ast.Pass) for s in h.body) for h in node.handlers):
            offenders.append(node.lineno)
    assert not offenders, f"silent create_seed swallow at lines {offenders}"
