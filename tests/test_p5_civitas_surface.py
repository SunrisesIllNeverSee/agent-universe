"""P5 G7 — CIVITAS surface: MCP procedure tools mirror REST (shared app/civitas_acts), page is registered."""
import asyncio
import json
import uuid
from pathlib import Path

from tests.conftest import signup_agent


def _agent(client):
    r = signup_agent(client, name=f"civ-{uuid.uuid4().hex[:6]}", ip=f"10.77.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}")
    assert r.status_code == 200, r.text
    d = r.json()
    return {"name": d["name"], "id": d["agent_id"], "key": d["api_key"], "h": {"Authorization": "Bearer " + d["api_key"]}}


def _mcp(tool, **args):
    from fastmcp import Client
    from app.deps import state

    mcp = state.mcp_bridge.build_fastmcp()

    async def call():
        async with Client(mcp) as c:
            r = await c.call_tool(tool, args)
            return r.structured_content or {}

    return asyncio.run(call())


def _world(client, admin_client, n=3):
    """Meeting with n named agents (chair first); returns (mid, agents)."""
    ags = [_agent(client) for _ in range(n)]
    mid = admin_client.post("/api/governance/meeting", json={"caller": ags[0]["name"], "subject": "Surface", "quorum": n}).json()["id"]
    for a in ags[1:]:
        assert admin_client.post(f"/api/governance/meeting/{mid}/join", json={"agent_id": a["name"]}).status_code == 200
    return mid, ags


def _blocked(admin_client, mid, chair):
    r = admin_client.post(f"/api/governance/meeting/{mid}/motion", json={
        "proposer": chair, "motion": "Delete audit entries for last week", "flags": ["destroys_records"]})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _meeting(admin_client, mid):
    return admin_client.get(f"/api/governance/meeting/{mid}").json()["meeting"]


def test_mcp_point_of_order_and_chair_rule(client, admin_client):
    mid, (chair, m2, _m3) = _world(client, admin_client)
    mo = admin_client.post(f"/api/governance/meeting/{mid}/motion", json={"proposer": chair["name"], "motion": "Approve the Q4 plan"}).json()["id"]
    po = _mcp("govern.point_of_order", api_key=m2["key"], meeting_id=mid, motion_id=mo, text="Out of scope", flame_law="iv")
    assert po["ok"] is True and po["raised_by"] == m2["name"] and po["flame_law"] == "IV" and po["status"] == "pending"
    # only the Chair may rule
    bad = _mcp("govern.rule", api_key=m2["key"], meeting_id=mid, point_of_order_id=po["id"], ruling="sustained")
    assert bad["ok"] is False and bad["status_code"] == 403
    ok = _mcp("govern.rule", api_key=chair["key"], meeting_id=mid, point_of_order_id=po["id"], ruling="sustained", reason="Agreed")
    assert ok["ok"] is True and ok["ruling"] == "sustained" and ok["ruled_by"] == chair["name"]
    # REST sees the same record
    stored = _meeting(admin_client, mid)["points_of_order"][0]
    assert stored["id"] == po["id"] and stored["ruling"] == "sustained"
    types = [x["type"] for x in _meeting(admin_client, mid)["minutes"]]
    assert "point_of_order_raised" in types and "point_of_order_ruled" in types


def test_mcp_appeal_flow_unblocks_motion(client, admin_client):
    mid, (chair, m2, m3) = _world(client, admin_client)
    mo = _blocked(admin_client, mid, chair["name"])
    ap = _mcp("govern.appeal", api_key=m2["key"], meeting_id=mid, target_type="flame_block", target_id=mo, reason="Wording only")
    assert ap["ok"] is True and ap["status"] == "awaiting_second" and ap["appellant"] == m2["name"]
    # appellant cannot second their own appeal
    me = _mcp("govern.second", api_key=m2["key"], meeting_id=mid, appeal_id=ap["id"])
    assert me["ok"] is False and me["code"] == "self_second"
    # voting before a second is refused
    early = _mcp("govern.appeal_vote", api_key=m3["key"], meeting_id=mid, appeal_id=ap["id"], vote="overturn")
    assert early["ok"] is False and early["code"] == "appeal_not_open"
    sec = _mcp("govern.second", api_key=m3["key"], meeting_id=mid, appeal_id=ap["id"])
    assert sec["ok"] is True and sec["status"] == "open_for_vote" and sec["seconded_by"] == m3["name"]
    for who, v in ((m2, "overturn"), (m3, "overturn"), (chair, "sustain")):
        r = _mcp("govern.appeal_vote", api_key=who["key"], meeting_id=mid, appeal_id=ap["id"], vote=v)
        assert r["ok"] is True
    done = _meeting(admin_client, mid)
    assert done["appeals"][0]["outcome"] == "overturned"
    # the motion is now votable through the existing vote path (GOV-001 5.3)
    vr = admin_client.post(f"/api/governance/meeting/{mid}/vote", json={"voter": chair["name"], "motion_id": mo, "vote": "yea"})
    assert vr.status_code == 200, vr.text


def test_mcp_matches_rest_refusals(client, admin_client):
    mid, (chair, m2, _m3) = _world(client, admin_client)
    mo = _blocked(admin_client, mid, chair["name"])
    # unauthenticated
    assert _mcp("govern.appeal", api_key="nope", meeting_id=mid, target_type="flame_block", target_id=mo)["status_code"] == 401
    # not a BLOCKED motion / unknown target type mirror REST codes
    sound = admin_client.post(f"/api/governance/meeting/{mid}/motion", json={"proposer": chair["name"], "motion": "Approve the Q4 plan"}).json()["id"]
    assert _mcp("govern.appeal", api_key=m2["key"], meeting_id=mid, target_type="flame_block", target_id=sound)["status_code"] == 409
    assert _mcp("govern.appeal", api_key=m2["key"], meeting_id=mid, target_type="bogus", target_id=mo)["status_code"] == 400
    rest = admin_client.post(f"/api/governance/meeting/{mid}/appeal", json={"appellant": m2["name"], "target_type": "bogus", "target_id": mo})
    assert rest.status_code == 400
    # outsider (registered but not an attendee) is refused
    out = _agent(client)
    r = _mcp("govern.point_of_order", api_key=out["key"], meeting_id=mid, motion_id=mo)
    assert r["ok"] is False and r["status_code"] == 403
    # duplicate appeal mirrors REST 409
    first = _mcp("govern.appeal", api_key=m2["key"], meeting_id=mid, target_type="flame_block", target_id=mo)
    assert first["ok"] is True
    dup = admin_client.post(f"/api/governance/meeting/{mid}/appeal", json={"appellant": m2["name"], "target_type": "flame_block", "target_id": mo})
    assert dup.status_code == 409 and dup.json()["code"] == "already_appealed"


def test_rest_still_binds_actor_to_credentials(client, admin_client):
    """The refactor kept the claim check: an agent cannot act as another member."""
    mid, (chair, m2, _m3) = _world(client, admin_client)
    mo = _blocked(admin_client, mid, chair["name"])
    r = client.post(f"/api/governance/meeting/{mid}/appeal", headers=m2["h"],
                    json={"appellant": chair["name"], "target_type": "flame_block", "target_id": mo})
    assert r.status_code == 403
    ok = client.post(f"/api/governance/meeting/{mid}/appeal", headers=m2["h"],
                     json={"appellant": m2["name"], "target_type": "flame_block", "target_id": mo})
    assert ok.status_code == 200


def test_meetings_page_registered_and_in_civitas_mode():
    root = Path(__file__).resolve().parents[1]
    assert (root / "frontend" / "meetings.html").exists()
    assert '"route": "/meetings"' in (root / "config" / "pages.json").read_text()
    shell = (root / "frontend" / "shell.html").read_text()
    assert 'routes:["/governance","/meetings"' in shell


def test_meetings_route_registered(client):
    """The test root has no frontend files; the real page is served in the browser test."""
    from app.deps import state
    assert any(getattr(r, "path", "") == "/meetings" for r in client.app.routes)


def test_governance_seed_failures_are_loud_not_silent(client, admin_client, monkeypatch):
    """A Seed failure on meeting/motion/procedure acts is audited as provenance_failed,
    never swallowed, and never fails the user action."""
    from app import seeds
    from app.deps import state

    async def _boom(**_):
        raise RuntimeError("seed store down")
    monkeypatch.setattr(seeds, "create_seed", _boom)

    mid, (chair, m2, _m3) = _world(client, admin_client)
    r = admin_client.post(f"/api/governance/meeting/{mid}/motion", json={"proposer": chair["name"], "motion": "Approve the Q4 plan"})
    assert r.status_code == 200
    mo = r.json()["id"]
    po = admin_client.post(f"/api/governance/meeting/{mid}/point-of-order", json={"member": m2["name"], "motion_id": mo, "text": "x"}, headers=m2["h"])
    assert po.status_code == 200
    failed = {(e.detail or {}).get("action") for e in state.audit.recent(500) if e.action == "provenance_failed"}
    assert {"meeting_called", "meeting_joined", "motion", "point_of_order_raised"} <= failed
