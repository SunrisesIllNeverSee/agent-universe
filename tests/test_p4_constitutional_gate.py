"""P4 slice 5 -- constitutional gate: typed governance motion bound to agreement_id, a consumer that
records the gate result on the Agreement, GOV-005 quorum (50% of eligible attendees) and minimum
async window, and the binding_authority setting (advisory_with_owner_countersign | council_delegated)."""
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from tests.test_p4_entry_api import ADMIN, _agent, _file, _slot, clock  # noqa: F401


def _constitutional(client):
    owner, ent = _agent(client), _agent(client)
    slot = _slot(client, owner)
    r = _file(client, ent, f"slot:{slot['id']}", entry_mode="constitutional")
    assert r.status_code == 201, r.text
    return owner, ent, r.json()["agreement"]["agreement_id"]


def _meeting(client, caller, others):
    m = client.post("/api/governance/meeting", headers=caller["h"],
                    json={"caller": caller["id"], "subject": "gate", "quorum": 1})
    assert m.status_code == 200, m.text
    mid = m.json()["id"]
    for o in others:
        assert client.post(f"/api/governance/meeting/{mid}/join", headers=o["h"],
                           json={"agent_id": o["id"]}).status_code == 200
    return mid


def _gate_motion(client, proposer, mid, aid, **extra):
    return client.post(f"/api/governance/meeting/{mid}/motion", headers=proposer["h"],
                       json={"proposer": proposer["id"], "motion": "", "kind": "work_entry_gate",
                             "agreement_id": aid, **extra})


def _vote(client, who, mid, motion_id, vote="yea"):
    r = client.post(f"/api/governance/meeting/{mid}/vote", headers=who["h"],
                    json={"voter": who["id"], "motion_id": motion_id, "vote": vote})
    assert r.status_code == 200, r.text


def _setup_gate(client, votes=("yea", "yea", "yea")):
    """3 eligible attendees; returns (owner, ent, aid, mid, motion_id)."""
    owner, ent, aid = _constitutional(client)
    third = _agent(client)
    mid = _meeting(client, owner, [ent, third])
    mo = _gate_motion(client, owner, mid, aid)
    assert mo.status_code == 200, mo.text
    mo = mo.json()
    for who, v in zip((owner, ent, third), votes):
        if v:
            _vote(client, who, mid, mo["id"], v)
    return owner, ent, aid, mid, mo["id"]


def _sync(client, who, aid):
    return client.post(f"/api/work-entry/{aid}/gate/sync", headers=who["h"])


def _accept(client, who, aid):
    return client.post(f"/api/work-entry/{aid}/accept", headers=who["h"])


# ── typed motion ─────────────────────────────────────────────────────────

def test_typed_motion_is_bound_to_agreement(client):
    owner, ent, aid = _constitutional(client)
    mid = _meeting(client, owner, [ent])
    r = _gate_motion(client, owner, mid, aid)
    assert r.status_code == 200, r.text
    mo = r.json()
    assert mo["kind"] == "work_entry_gate" and mo["agreement_id"] == aid
    assert mo["status"] == "pending" and mo["closes_at"] > mo["proposed_at"]
    assert mo["motion"]  # a default text is supplied


def test_typed_motion_validation(client):
    owner, ent, aid = _constitutional(client)
    mid = _meeting(client, owner, [ent])
    assert _gate_motion(client, owner, mid, "agr-workentry-nope").status_code == 404
    assert client.post(f"/api/governance/meeting/{mid}/motion", headers=owner["h"],
                       json={"proposer": owner["id"], "motion": "x", "kind": "bogus"}).status_code == 400
    # only constitutional agreements are gated
    o2, e2 = _agent(client), _agent(client)
    std = _file(client, e2, f"slot:{_slot(client, o2)['id']}", entry_mode="standard").json()["agreement"]
    mid2 = _meeting(client, o2, [e2])
    assert _gate_motion(client, o2, mid2, std["agreement_id"]).status_code == 409
    # one open gate motion per agreement
    assert _gate_motion(client, owner, mid, aid).status_code == 200
    assert _gate_motion(client, owner, mid, aid).status_code == 409


def test_untyped_motion_unchanged(client):
    owner, ent = _agent(client), _agent(client)
    mid = _meeting(client, owner, [ent])
    mo = client.post(f"/api/governance/meeting/{mid}/motion", headers=owner["h"],
                     json={"proposer": owner["id"], "motion": "plain"}).json()
    assert "kind" not in mo or mo["kind"] in (None, "")
    _vote(client, owner, mid, mo["id"], "yea")
    _vote(client, ent, mid, mo["id"], "yea")
    m = client.get(f"/api/governance/meeting/{mid}").json()["meeting"]
    assert m["motions"][0]["status"] == "passed"   # legacy auto-resolve


# ── gate required ────────────────────────────────────────────────────────

def test_cannot_accept_or_activate_without_gate(client):
    owner, ent, aid = _constitutional(client)
    r = _accept(client, owner, aid)
    assert r.status_code == 409 and r.json()["code"] == "governance_gate_required"
    assert client.post(f"/api/work-entry/{aid}/activate", headers=ent["h"]).status_code == 409
    got = client.get(f"/api/work-entry/{aid}/gate", headers=owner["h"]).json()
    assert got["required"] is True and got["satisfied"] is False
    assert got["binding_authority"] == "advisory_with_owner_countersign"


def test_window_must_elapse_even_if_all_voted(client, clock):
    owner, ent, aid, mid, motion_id = _setup_gate(client)
    out = _sync(client, owner, aid).json()
    assert out["gates"] == [] and out["open_motions"][0]["motion_id"] == motion_id
    m = client.get(f"/api/governance/meeting/{mid}").json()["meeting"]
    assert m["motions"][0]["status"] == "pending"      # not auto-resolved
    assert _accept(client, owner, aid).status_code == 409
    clock["offset"] = timedelta(hours=23)
    assert _sync(client, owner, aid).json()["gates"] == []
    clock["offset"] = timedelta(hours=25)
    out = _sync(client, owner, aid).json()
    assert out["gates"][0]["result"] == "passed" and out["gates"][0]["quorum_met"] is True


# ── advisory default ─────────────────────────────────────────────────────

def test_passed_motion_alone_is_insufficient_under_advisory(client, clock):
    owner, ent, aid, mid, motion_id = _setup_gate(client)
    clock["offset"] = timedelta(hours=25)
    g = _sync(client, owner, aid).json()["gates"][0]
    assert g["result"] == "passed" and g["record_seed_doi"] and g["countersigned_at"] is None
    r = _accept(client, owner, aid)
    assert r.status_code == 409 and r.json()["code"] == "owner_countersign_required"
    assert client.get(f"/api/work-entry/{aid}", headers=owner["h"]).json()["agreement"]["state"] == "pending"
    # the motion in the meeting reads as passed (advisory)
    m = client.get(f"/api/governance/meeting/{mid}").json()["meeting"]
    assert m["motions"][0]["status"] == "passed"


def test_countersign_then_active_with_receipts(client, clock):
    owner, ent, aid, mid, motion_id = _setup_gate(client)
    clock["offset"] = timedelta(hours=25)
    _sync(client, owner, aid)
    # only the owner-held operator credential may countersign
    assert client.post(f"/api/work-entry/{aid}/gate/countersign", headers=owner["h"]).status_code == 403
    assert client.post(f"/api/work-entry/{aid}/gate/countersign", headers=ent["h"]).status_code == 403
    assert client.post(f"/api/work-entry/{aid}/gate/countersign").status_code == 401
    cs = client.post(f"/api/work-entry/{aid}/gate/countersign", headers=ADMIN)
    assert cs.status_code == 200, cs.text
    g = cs.json()["gate"]
    assert g["countersigned_by"] == "operator:admin" and g["countersign_seed_doi"]
    assert cs.json()["gate_status"]["satisfied"] is True
    acc = _accept(client, owner, aid)
    assert acc.status_code == 200 and acc.json()["agreement"]["state"] == "accepted"
    assert acc.json()["receipt"]["seed_doi"] and g["gate_id"] in acc.json()["receipt"]["reason"]
    act = client.post(f"/api/work-entry/{aid}/activate", headers=ent["h"])
    assert act.status_code == 200 and act.json()["agreement"]["state"] == "active"
    got = client.get(f"/api/work-entry/{aid}", headers=ent["h"]).json()
    assert [h["transition"] for h in got["agreement"]["state_history"]] == \
        ["create", "file", "accept", "activate"]
    assert all(rc["seed_doi"] for rc in got["receipts"])
    assert got["gates"][0]["motion_id"] == motion_id


def test_failed_motion_cannot_be_countersigned_into_force(client, clock):
    owner, ent, aid, mid, motion_id = _setup_gate(client, votes=("nay", "nay", "yea"))
    clock["offset"] = timedelta(hours=25)
    assert _sync(client, owner, aid).json()["gates"][0]["result"] == "failed"
    assert client.post(f"/api/work-entry/{aid}/gate/countersign", headers=ADMIN).status_code == 409
    assert _accept(client, owner, aid).status_code == 409


def test_quorum_is_half_of_eligible(client, clock):
    # 3 eligible -> ceil(1.5) = 2 needed; a single yea is not a quorum
    owner, ent, aid, mid, motion_id = _setup_gate(client, votes=("yea", None, None))
    clock["offset"] = timedelta(hours=25)
    g = _sync(client, owner, aid).json()["gates"][0]
    assert g["quorum_met"] is False and g["result"] == "failed" and g["eligible"] == 3
    assert g["quorum_required"] == 2
    # exactly half rounded up passes (votes are cast inside the window, then the window elapses)
    clock["offset"] = timedelta(0)
    o2, e2, aid2, mid2, mo2 = _setup_gate(client, votes=("yea", "yea", None))
    clock["offset"] = timedelta(hours=25)
    g2 = _sync(client, o2, aid2).json()["gates"][0]
    assert g2["quorum_met"] is True and g2["result"] == "passed"


def test_sync_is_idempotent(client, clock):
    owner, ent, aid, mid, motion_id = _setup_gate(client)
    clock["offset"] = timedelta(hours=25)
    _sync(client, owner, aid)
    _sync(client, ent, aid)
    assert len(client.get(f"/api/work-entry/{aid}/gate", headers=owner["h"]).json()["gates"]) == 1


# ── binding_authority ────────────────────────────────────────────────────

def test_council_delegated_passed_motion_suffices(client, clock):
    owner, ent, aid, mid, motion_id = _setup_gate(client)
    # switching is an owner-held (operator) act
    assert client.post("/api/work-entry/gate/settings", headers=owner["h"],
                       json={"binding_authority": "council_delegated"}).status_code == 403
    bad = client.post("/api/work-entry/gate/settings", headers=ADMIN, json={"binding_authority": "x"})
    assert bad.status_code == 422
    ok = client.post("/api/work-entry/gate/settings", headers=ADMIN,
                     json={"binding_authority": "council_delegated"})
    assert ok.status_code == 200 and ok.json()["binding_authority"] == "council_delegated"
    try:
        clock["offset"] = timedelta(hours=25)
        _sync(client, owner, aid)
        assert client.post(f"/api/work-entry/{aid}/gate/countersign", headers=ADMIN).status_code == 409
        acc = _accept(client, owner, aid)
        assert acc.status_code == 200 and acc.json()["agreement"]["state"] == "accepted"
        assert client.post(f"/api/work-entry/{aid}/activate", headers=ent["h"]).status_code == 200
    finally:
        client.post("/api/work-entry/gate/settings", headers=ADMIN,
                    json={"binding_authority": "advisory_with_owner_countersign"})


def test_council_delegated_still_needs_a_passed_motion(client):
    owner, ent, aid = _constitutional(client)
    client.post("/api/work-entry/gate/settings", headers=ADMIN, json={"binding_authority": "council_delegated"})
    try:
        assert _accept(client, owner, aid).status_code == 409
    finally:
        client.post("/api/work-entry/gate/settings", headers=ADMIN,
                    json={"binding_authority": "advisory_with_owner_countersign"})


def test_window_is_configurable(client):
    owner, ent, aid = _constitutional(client)
    third = _agent(client)
    s = client.post("/api/work-entry/gate/settings", headers=ADMIN, json={"gate_window_hours": 0.5})
    assert s.status_code == 200 and s.json()["gate_window_hours"] == 0.5
    try:
        mid = _meeting(client, owner, [ent, third])
        mo = _gate_motion(client, owner, mid, aid).json()
        opened = datetime.fromisoformat(mo["proposed_at"]); closes = datetime.fromisoformat(mo["closes_at"])
        assert closes - opened == timedelta(minutes=30)
    finally:
        client.post("/api/work-entry/gate/settings", headers=ADMIN, json={"gate_window_hours": 24})
    assert client.get("/api/work-entry/gate/settings", headers=ADMIN).json()["gate_window_hours"] == 24
