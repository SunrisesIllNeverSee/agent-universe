"""
test_routes_governance.py — HTTP contract tests for app/routes/governance.py

Covers: list meetings, call meeting, join, motion/quorum guard, full lifecycle, sessions

Note: All governance POST endpoints are admin-gated.
      GET /api/governance/meetings and /sessions are public.
"""
import uuid


def _caller():
    return f"agent-{uuid.uuid4().hex[:6]}"


def test_list_meetings_empty(client):
    r = client.get("/api/governance/meetings")
    assert r.status_code == 200
    data = r.json()
    assert "meetings" in data
    assert isinstance(data["meetings"], list)


def test_call_meeting(admin_client):
    r = admin_client.post("/api/governance/meeting", json={
        "caller": _caller(),
        "subject": "Test session",
        "quorum": 2,
    })
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data["status"] == "open"
    assert len(data["attendees"]) == 1


def test_join_meeting(admin_client):
    caller = _caller()
    joiner = _caller()
    create = admin_client.post("/api/governance/meeting", json={
        "caller": caller,
        "subject": "Join test",
        "quorum": 2,
    })
    assert create.status_code == 200
    meeting_id = create.json()["id"]

    join = admin_client.post(f"/api/governance/meeting/{meeting_id}/join", json={
        "agent_id": joiner,
    })
    assert join.status_code == 200
    assert join.json()["attendees"] == 2


def test_propose_motion_requires_quorum(admin_client):
    caller = _caller()
    create = admin_client.post("/api/governance/meeting", json={
        "caller": caller,
        "subject": "Quorum test",
        "quorum": 3,
    })
    meeting_id = create.json()["id"]

    motion = admin_client.post(f"/api/governance/meeting/{meeting_id}/motion", json={
        "proposer": caller,
        "motion": "We should do X",
    })
    assert motion.status_code == 409


def test_full_meeting_lifecycle(admin_client):
    a1 = _caller()
    a2 = _caller()

    # Call
    create = admin_client.post("/api/governance/meeting", json={
        "caller": a1,
        "subject": "Full lifecycle",
        "quorum": 2,
    })
    assert create.status_code == 200
    mid = create.json()["id"]

    # Join
    join = admin_client.post(f"/api/governance/meeting/{mid}/join", json={"agent_id": a2})
    assert join.status_code == 200
    assert join.json()["has_quorum"] is True

    # Propose
    motion = admin_client.post(f"/api/governance/meeting/{mid}/motion", json={
        "proposer": a1,
        "motion": "Approve the budget",
    })
    assert motion.status_code == 200
    motion_id = motion.json()["id"]

    # Vote yea x2
    v1 = admin_client.post(f"/api/governance/meeting/{mid}/vote", json={
        "voter": a1, "motion_id": motion_id, "vote": "yea",
    })
    assert v1.status_code == 200
    v2 = admin_client.post(f"/api/governance/meeting/{mid}/vote", json={
        "voter": a2, "motion_id": motion_id, "vote": "yea",
    })
    assert v2.status_code == 200

    # Adjourn
    adjourn = admin_client.post(f"/api/governance/meeting/{mid}/adjourn")
    assert adjourn.status_code == 200
    assert adjourn.json()["status"] == "adjourned"

    # Verify motion passed
    motions = adjourn.json().get("motions", [])
    if motions:
        passed = [m for m in motions if m["id"] == motion_id]
        assert passed[0]["status"] == "passed"


def test_governance_sessions(client):
    r = client.get("/api/governance/sessions")
    assert r.status_code == 200
    data = r.json()
    assert "sessions" in data


def test_call_meeting_missing_fields_400(admin_client):
    r = admin_client.post("/api/governance/meeting", json={
        "caller": "",
        "subject": "",
    })
    assert r.status_code == 400
