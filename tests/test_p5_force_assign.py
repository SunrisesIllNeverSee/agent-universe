"""P5 G5 -- operator force-assign (P2 Q9): an operator assigns a named agent to an open slot.

Same Agreement as the Enter path but origin 'force_assign', the operator recorded as the actor.
The assigned agent must still accept (no operator or owner can accept for it); no money moves.
"""
from tests.test_p4_entry_api import ADMIN, _agent, _file, _post  # noqa: F401
from tests.test_p4_slot_binding import _mk_slot, _slot_now

URL = "/api/work-entry/force-assign"


def _assign(client, slot_id, agent_id, headers=ADMIN, **kw):
    return client.post(URL, headers=headers,
                       json={"opportunity_ref": f"slot:{slot_id}", "agent_id": agent_id,
                             "reason": "recovery: prior agent lost", **kw})


def test_force_assign_creates_pending_agreement_with_operator_actor(client):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    r = _assign(client, s["id"], ent["id"])
    assert r.status_code == 201, r.text
    a = r.json()["agreement"]
    assert a["state"] == "pending"
    assert a["governance"]["origin"] == "force_assign" and a["governance"]["mode"] == "standard"
    assert a["terms"]["assigned_by"] == "operator:admin"
    assert [p["id"] for p in a["principals"]] == [ent["id"], owner["id"]]
    rcs = r.json()["receipts"]
    assert [x["transition"] for x in rcs] == ["create", "file"]
    assert all(x["actor"] == "operator:admin" and x["seed_doi"] for x in rcs)
    assert _slot_now(client, s["id"])["status"] == "open"      # not filled until the agent accepts


def test_non_admin_is_403_and_creates_nothing(client):
    owner, ent, other = _agent(client), _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    for h in ({}, other["h"], owner["h"], ent["h"]):
        assert _assign(client, s["id"], ent["id"], headers=h).status_code == 403
    from app.deps import state
    assert state.workentry.list(opportunity_ref=f"slot:{s['id']}") == []


def test_only_the_assigned_agent_can_accept(client):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    aid = _assign(client, s["id"], ent["id"]).json()["agreement"]["agreement_id"]
    acc = f"/api/work-entry/{aid}/accept"
    assert client.post(acc, headers=owner["h"]).status_code == 403
    assert client.post(acc, headers=ADMIN, json={"acting_for": ent["id"]}).status_code == 403
    assert client.post(acc, headers=ADMIN, json={"acting_for": owner["id"]}).status_code == 403
    ok = client.post(acc, headers=ent["h"])
    assert ok.status_code == 200 and ok.json()["agreement"]["state"] == "accepted"
    act = client.post(f"/api/work-entry/{aid}/activate", headers=ent["h"])
    assert act.status_code == 200 and act.json()["agreement"]["state"] == "active"
    assert _slot_now(client, s["id"])["status"] != "open"


def test_assigned_agent_can_decline(client):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    aid = _assign(client, s["id"], ent["id"]).json()["agreement"]["agreement_id"]
    rej = f"/api/work-entry/{aid}/reject"
    assert client.post(rej, headers=owner["h"], json={"reason": "x"}).status_code == 403
    r = client.post(rej, headers=ent["h"], json={"reason": "not for me"})
    assert r.status_code == 200 and r.json()["agreement"]["state"] == "rejected"
    # declined is terminal: the slot can be assigned again
    assert _assign(client, s["id"], _agent(client)["id"]).status_code == 201


def test_double_assign_is_409(client):
    owner, a, b = _agent(client), _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    first = _assign(client, s["id"], a["id"])
    assert first.status_code == 201
    same = _assign(client, s["id"], a["id"])
    assert same.status_code == 409 and same.json()["agreement_id"] == first.json()["agreement"]["agreement_id"]
    other = _assign(client, s["id"], b["id"])
    assert other.status_code == 409 and other.json()["code"] == "already_assigned"


def test_revoked_or_unknown_agent_cannot_be_assigned(client):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    assert client.post("/api/provision/revoke", headers=ADMIN, json={"agent_id": ent["id"]}).status_code == 200
    r = _assign(client, s["id"], ent["id"])
    assert r.status_code == 409 and r.json()["code"] == "agent_not_assignable"
    assert _assign(client, s["id"], "agent-does-not-exist").status_code == 404


def test_cannot_assign_owner_or_filled_slot_and_reason_required(client):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    assert _assign(client, s["id"], owner["id"]).status_code == 409
    assert client.post(URL, headers=ADMIN, json={"opportunity_ref": f"slot:{s['id']}",
                                                 "agent_id": ent["id"]}).status_code == 422
    assert _assign(client, "slot-nope", ent["id"]).status_code == 404


def test_force_assign_moves_no_money(client):
    from app.deps import state
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    body = _assign(client, s["id"], ent["id"], amount=999, payout=999).json()
    assert "amount" not in str(body["agreement"]["terms"]) and "payout" not in str(body["agreement"]["terms"])
    assert not any("escrow" in k and v for k, v in body["agreement"]["objects"].items())


def _call(tool, **args):
    import asyncio
    from app.deps import state
    res = asyncio.run(state.mcp_bridge.build_fastmcp().call_tool(tool, args))
    sc = getattr(res, "structured_content", None)
    return res[1] if sc is None and isinstance(res, tuple) else sc


def test_mcp_operator_tool_is_admin_gated_and_matches_rest(client):
    owner, ent, bad = _agent(client), _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    ref = f"slot:{s['id']}"
    denied = _call("admin.force_assign", admin_key="wrong", opportunity_ref=ref, agent_id=ent["id"], reason="r")
    assert "error" in denied and "agreement" not in denied
    ok = _call("admin.force_assign", admin_key=ADMIN["X-Admin-Key"], opportunity_ref=ref,
               agent_id=ent["id"], reason="direct hire")
    assert ok["ok"] and ok["status_code"] == 201 and ok["agreement"]["state"] == "pending"
    assert ok["agreement"]["governance"]["origin"] == "force_assign"
    again = _call("admin.force_assign", admin_key=ADMIN["X-Admin-Key"], opportunity_ref=ref,
                  agent_id=bad["id"], reason="x")
    assert again["status_code"] == 409
    # the agent accepts through the ordinary MCP verb
    aid = ok["agreement"]["agreement_id"]
    r = client.post(f"/api/work-entry/{aid}/accept", headers=ent["h"])
    assert r.status_code == 200
