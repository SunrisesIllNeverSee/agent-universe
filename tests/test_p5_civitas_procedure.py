"""P5 G7 — CIVITAS procedure: motion Flame review, point of order, appeal (GOV-001 Art 5-6)."""
import uuid

import pytest

from app import civitas_procedure as proc


def _n():
    return f"agent-{uuid.uuid4().hex[:6]}"


def _meeting(c, n=3):
    """Meeting with `n` attendees; returns (mid, [chair, m2, ...])."""
    ids = [_n() for _ in range(n)]
    mid = c.post("/api/governance/meeting", json={"caller": ids[0], "subject": "Procedure", "quorum": n}).json()["id"]
    for a in ids[1:]:
        assert c.post(f"/api/governance/meeting/{mid}/join", json={"agent_id": a}).status_code == 200
    return mid, ids


def _motion(c, mid, proposer, text, **kw):
    r = c.post(f"/api/governance/meeting/{mid}/motion", json={"proposer": proposer, "motion": text, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def _vote(c, mid, voter, mo, v="yea"):
    return c.post(f"/api/governance/meeting/{mid}/vote", json={"voter": voter, "motion_id": mo, "vote": v})


def _blocked(c, mid, chair):
    return _motion(c, mid, chair, "Delete audit entries for last week's session")


def _base(mid):
    return f"/api/governance/meeting/{mid}"


# ── evaluator ──
def test_review_results():
    assert proc.review_motion("Approve the budget for Q4 planning")["result"] == "SOUND"
    w = proc.review_motion("ok")
    assert w["result"] == "WARNING" and w["laws_cited"][0]["law"] == "III"
    b = proc.review_motion("Quietly falsify the vote tally")
    assert b["result"] == "BLOCKED" and b["laws_cited"][0]["law"] == "V" and b["advisory"] is True
    f = proc.review_motion("Approve the budget for Q4 planning", ["exceeds_scope"])
    assert f["result"] == "BLOCKED" and f["laws_cited"][0]["law"] == "IV"


def test_motion_records_review_and_rejects_unknown_flag(admin_client):
    mid, (chair, *_r) = _meeting(admin_client)
    m = _motion(admin_client, mid, chair, "Approve the budget for Q4 planning")
    assert m["flame_review"]["result"] == "SOUND"
    assert _blocked(admin_client, mid, chair)["flame_review"]["result"] == "BLOCKED"
    bad = admin_client.post(f"{_base(mid)}/motion", json={"proposer": chair, "motion": "Fund the thing now", "flags": ["nope"]})
    assert bad.status_code == 400
    stored = admin_client.get(_base(mid)).json()["meeting"]["motions"][0]
    assert stored["flame_review"]["result"] == "SOUND"


# ── 5.3 ──
def test_vote_on_blocked_motion_refused(admin_client):
    mid, (chair, *_r) = _meeting(admin_client)
    mo = _blocked(admin_client, mid, chair)["id"]
    r = _vote(admin_client, mid, chair, mo)
    assert r.status_code == 409 and r.json()["code"] == "motion_blocked"


def test_warning_motion_still_votable(admin_client):
    mid, (chair, *_r) = _meeting(admin_client)
    mo = _motion(admin_client, mid, chair, "ok")
    assert mo["flame_review"]["result"] == "WARNING"
    assert _vote(admin_client, mid, chair, mo["id"]).status_code == 200


# ── 6.1 ──
def test_point_of_order_ruling(admin_client):
    mid, (chair, m2, _m3) = _meeting(admin_client)
    mo = _motion(admin_client, mid, chair, "Approve the budget for Q4 planning")["id"]
    po = admin_client.post(f"{_base(mid)}/point-of-order",
                           json={"member": m2, "motion_id": mo, "text": "Out of order", "flame_law": "iv"})
    assert po.status_code == 200 and po.json()["flame_law"] == "IV" and po.json()["status"] == "pending"
    pid = po.json()["id"]
    # non-chair cannot rule
    assert admin_client.post(f"{_base(mid)}/point-of-order/{pid}/rule", json={"chair": m2, "ruling": "sustained"}).status_code == 403
    assert admin_client.post(f"{_base(mid)}/point-of-order/{pid}/rule", json={"chair": chair, "ruling": "maybe"}).status_code == 400
    r = admin_client.post(f"{_base(mid)}/point-of-order/{pid}/rule", json={"chair": chair, "ruling": "not_sustained", "reason": "in order"})
    assert r.status_code == 200 and r.json()["ruling"] == "not_sustained" and r.json()["ruled_by"] == chair
    assert admin_client.post(f"{_base(mid)}/point-of-order/{pid}/rule", json={"chair": chair, "ruling": "sustained"}).status_code == 409
    types = [x["type"] for x in admin_client.get(_base(mid)).json()["meeting"]["minutes"]]
    assert "point_of_order_raised" in types and "point_of_order_ruled" in types
    bad_law = admin_client.post(f"{_base(mid)}/point-of-order", json={"member": m2, "motion_id": mo, "flame_law": "IX"})
    assert bad_law.status_code == 400


# ── 6.2 ──
def _appeal(c, mid, who, mo):
    r = c.post(f"{_base(mid)}/appeal", json={"appellant": who, "target_type": "flame_block", "target_id": mo, "reason": "advisory only"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_appeal_requires_second_from_different_member(admin_client):
    mid, (chair, m2, m3) = _meeting(admin_client)
    mo = _blocked(admin_client, mid, chair)["id"]
    aid = _appeal(admin_client, mid, m2, mo)
    ballot = {"voter": m3, "vote": "overturn"}
    assert admin_client.post(f"{_base(mid)}/appeal/{aid}/vote", json=ballot).status_code == 409  # no second yet
    assert admin_client.post(f"{_base(mid)}/appeal/{aid}/second", json={"member": m2}).status_code == 409  # self-second
    assert admin_client.post(f"{_base(mid)}/appeal/{aid}/second", json={"member": m3}).status_code == 200
    assert admin_client.post(f"{_base(mid)}/appeal/{aid}/vote", json=ballot).status_code == 200
    # duplicate appeal of the same determination refused
    dup = admin_client.post(f"{_base(mid)}/appeal", json={"appellant": m3, "target_type": "flame_block", "target_id": mo})
    assert dup.status_code == 409


def test_appeal_tie_sustains_chair(admin_client):
    mid, (chair, m2, m3, m4) = _meeting(admin_client, 4)
    mo = _blocked(admin_client, mid, chair)["id"]
    aid = _appeal(admin_client, mid, m2, mo)
    admin_client.post(f"{_base(mid)}/appeal/{aid}/second", json={"member": m3})
    for who, v in [(chair, "sustain"), (m2, "overturn"), (m3, "overturn"), (m4, "sustain")]:
        r = admin_client.post(f"{_base(mid)}/appeal/{aid}/vote", json={"voter": who, "vote": v})
        assert r.status_code == 200
    ap = r.json()
    assert ap["status"] == "resolved" and ap["outcome"] == "sustained"
    assert _vote(admin_client, mid, chair, mo).status_code == 409  # still blocked


def test_successful_appeal_unblocks_motion(admin_client):
    mid, (chair, m2, m3) = _meeting(admin_client)
    mo = _blocked(admin_client, mid, chair)["id"]
    aid = _appeal(admin_client, mid, m2, mo)
    admin_client.post(f"{_base(mid)}/appeal/{aid}/second", json={"member": m3})
    admin_client.post(f"{_base(mid)}/appeal/{aid}/vote", json={"voter": m2, "vote": "overturn"})
    admin_client.post(f"{_base(mid)}/appeal/{aid}/vote", json={"voter": m3, "vote": "overturn"})
    # chair tallies early; abstentions not counted
    assert admin_client.post(f"{_base(mid)}/appeal/{aid}/close", json={"chair": m2}).status_code == 403
    r = admin_client.post(f"{_base(mid)}/appeal/{aid}/close", json={"chair": chair})
    assert r.status_code == 200 and r.json()["outcome"] == "overturned"
    assert _vote(admin_client, mid, chair, mo).status_code == 200
    m = next(x for x in admin_client.get(_base(mid)).json()["meeting"]["motions"] if x["id"] == mo)
    assert m["appeal_overturned_block"] is True and m["flame_review"]["result"] == "BLOCKED"


def test_appeal_point_of_order_ruling(admin_client):
    mid, (chair, m2, m3) = _meeting(admin_client)
    mo = _motion(admin_client, mid, chair, "Approve the budget for Q4 planning")["id"]
    pid = admin_client.post(f"{_base(mid)}/point-of-order", json={"member": m2, "motion_id": mo}).json()["id"]
    unruled = admin_client.post(f"{_base(mid)}/appeal", json={"appellant": m2, "target_type": "point_of_order", "target_id": pid})
    assert unruled.status_code == 409
    admin_client.post(f"{_base(mid)}/point-of-order/{pid}/rule", json={"chair": chair, "ruling": "not_sustained"})
    a = admin_client.post(f"{_base(mid)}/appeal", json={"appellant": m2, "target_type": "point_of_order", "target_id": pid}).json()["id"]
    admin_client.post(f"{_base(mid)}/appeal/{a}/second", json={"member": m3})
    for who in (chair, m2, m3):
        admin_client.post(f"{_base(mid)}/appeal/{a}/vote", json={"voter": who, "vote": "overturn" if who != chair else "sustain"})
    po = admin_client.get(_base(mid)).json()["meeting"]["points_of_order"][0]
    assert po["ruling_overturned"] is True and po["final_ruling"] == "sustained"


def test_appeal_non_blocked_motion_refused(admin_client):
    mid, (chair, m2, _m3) = _meeting(admin_client)
    mo = _motion(admin_client, mid, chair, "Approve the budget for Q4 planning")["id"]
    r = admin_client.post(f"{_base(mid)}/appeal", json={"appellant": m2, "target_type": "flame_block", "target_id": mo})
    assert r.status_code == 409


def test_procedural_acts_audited(admin_client):
    mid, (chair, m2, m3) = _meeting(admin_client)
    mo = _blocked(admin_client, mid, chair)["id"]
    _appeal(admin_client, mid, m2, mo)
    types = [x["type"] for x in admin_client.get(_base(mid)).json()["meeting"]["minutes"]]
    assert "flame_review" in types and "appeal_filed" in types
    from app.deps import state
    actions = [e.action for e in state.audit.recent(300)]
    assert "flame_review_motion" in actions and "appeal_filed" in actions


# ── backward compat ──
def test_existing_flow_unchanged(admin_client):
    mid, (chair, m2) = _meeting(admin_client, 2)
    m = _motion(admin_client, mid, chair, "Approve the budget")
    assert m["status"] == "pending"
    assert _vote(admin_client, mid, chair, m["id"]).status_code == 200
    assert _vote(admin_client, mid, m2, m["id"]).status_code == 200
    mt = admin_client.post(f"{_base(mid)}/adjourn").json()
    assert mt["motions"][0]["status"] == "passed"
    assert mt["caller"] == chair
