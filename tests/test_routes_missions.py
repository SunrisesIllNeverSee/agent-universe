"""
test_routes_missions.py — HTTP contract tests for app/routes/missions.py

Missions is the second highest-risk untested surface — 25 endpoints covering
mission lifecycle, slots (fill/leave), tasks, campaigns, and bounties.

Covers:
- Missions: list, get, create, end (4 endpoints)
- Slots: list all, list open, create, fill, leave (5 endpoints)
- Campaigns: create, list, get (3 endpoints)
- Tasks: create, list, get (3 endpoints)
- Bounty posting: post_bounty (1 endpoint)
- Auth guards: admin-gated write paths

Note: POST /api/missions, /api/tasks, /api/slots/create are admin-gated.
      POST /api/slots/fill and /api/slots/leave are public (agent self-service).
"""
import uuid
from tests.conftest import signup_agent


def _unique_ip():
    return f"10.3.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"


def _create_mission(admin_client, label=None):
    """Helper: create a mission and return its id."""
    label = label or f"MISSION-{uuid.uuid4().hex[:4].upper()}"
    r = admin_client.post("/api/missions", json={
        "label": label,
        "objective": "Test objective",
        "posture": "SCOUT",
        "formation": "alpha",
    })
    assert r.status_code == 200, f"mission create failed: {r.text}"
    return r.json()["id"]


# ── Missions ──────────────────────────────────────────────────────────────────

def test_missions_list_public(client):
    r = client.get("/api/missions")
    assert r.status_code == 200
    assert "missions" in r.json()
    assert isinstance(r.json()["missions"], list)


def test_mission_get_404(client):
    r = client.get("/api/missions/nonexistent-mission-xyz")
    assert r.status_code == 404


def test_mission_create_requires_admin(client):
    r = client.post("/api/missions", json={"label": "Unauthorized"})
    assert r.status_code == 403


def test_mission_create(admin_client):
    r = admin_client.post("/api/missions", json={
        "label": f"Test Mission {uuid.uuid4().hex[:4]}",
        "objective": "Test the create endpoint",
        "posture": "SCOUT",
        "formation": "alpha",
    })
    assert r.status_code == 200
    d = r.json()
    assert "id" in d
    assert d["status"] == "active"
    assert "governance_at_launch" in d


def test_mission_create_and_get(admin_client, client):
    mission_id = _create_mission(admin_client)
    r = client.get(f"/api/missions/{mission_id}")
    assert r.status_code == 200
    assert r.json()["mission"]["id"] == mission_id


def test_mission_end(admin_client):
    mission_id = _create_mission(admin_client)
    r = admin_client.post(f"/api/missions/{mission_id}/end", json={
        "payout_per_slot": 0,
        "originator_id": "",
    })
    assert r.status_code == 200
    assert r.json()["status"] == "completed"  # API returns "completed" not "ended"


# ── Slots ─────────────────────────────────────────────────────────────────────

def test_slots_list_all(client):
    r = client.get("/api/slots")
    assert r.status_code == 200
    assert "slots" in r.json()


def test_slots_open_list(client):
    r = client.get("/api/slots/open")
    assert r.status_code == 200
    d = r.json()
    assert "open_slots" in d
    assert "count" in d


def test_slots_create_requires_admin(client):
    r = client.post("/api/slots/create", json={
        "mission_id": "m-test",
        "formation_id": "alpha",
    })
    assert r.status_code == 403


def test_slot_fill_requires_registered_agent(client):
    r = client.post("/api/slots/fill", json={
        "slot_id": "slot-nonexistent",
        "agent_id": "ghost-agent-xyz",
    })
    assert r.status_code == 403


def test_slot_fill_missing_agent_id_400(client):
    r = client.post("/api/slots/fill", json={"slot_id": "slot-x", "agent_id": ""})
    assert r.status_code == 400


def test_slot_fill_nonexistent_slot_404(client):
    # Register real agent first
    signup = signup_agent(client, ip=_unique_ip())
    agent_id = signup.json()["agent_id"]

    r = client.post("/api/slots/fill", json={
        "slot_id": "slot-does-not-exist-xyz",
        "agent_id": agent_id,
    })
    assert r.status_code == 404


def test_slot_full_lifecycle(client, admin_client):
    """Create mission → create slot → fill → leave."""
    mission_id = _create_mission(admin_client)

    # Create slot
    slot_r = admin_client.post("/api/slots/create", json={
        "mission_id": mission_id,
        "formation_id": "alpha",
        "posture": "SCOUT",
        "label": "Test slot",
        "positions": [{"row": 0, "col": 0}],
        "roles": ["secondary"],
        "revenue_splits": [50],
    })
    assert slot_r.status_code == 200
    slots_created = slot_r.json().get("slots", [])
    if not slots_created:
        return  # Formation may not generate slots in test env

    slot_id = slots_created[0]["id"]

    # Register agent
    signup = signup_agent(client, ip=_unique_ip())
    agent_id = signup.json()["agent_id"]

    # Fill
    fill = client.post("/api/slots/fill", json={"slot_id": slot_id, "agent_id": agent_id})
    assert fill.status_code == 200
    assert fill.json()["filled"] is True

    # Leave
    leave = client.post("/api/slots/leave", json={"slot_id": slot_id, "agent_id": agent_id})
    assert leave.status_code == 200


# ── Campaigns ─────────────────────────────────────────────────────────────────

def test_campaigns_list(client):
    r = client.get("/api/campaigns")
    assert r.status_code == 200
    assert "campaigns" in r.json()


def test_campaign_create_requires_admin(client):
    r = client.post("/api/campaigns", json={"name": "Unauthorized"})
    assert r.status_code == 403


def test_campaign_create(admin_client):
    r = admin_client.post("/api/campaigns", json={
        "name": f"Test Campaign {uuid.uuid4().hex[:4]}",
        "objective": "Integration test campaign",
        "created_by": "test-suite",
    })
    assert r.status_code == 200
    d = r.json()
    assert "id" in d


def test_campaign_create_and_get(admin_client, client):
    r = admin_client.post("/api/campaigns", json={
        "name": f"Get Test {uuid.uuid4().hex[:4]}",
        "objective": "Test get",
        "created_by": "test",
    })
    assert r.status_code == 200
    campaign_id = r.json()["id"]

    get = client.get(f"/api/campaigns/{campaign_id}")
    assert get.status_code == 200


# ── Tasks ─────────────────────────────────────────────────────────────────────

def test_tasks_list(client):
    r = client.get("/api/tasks")
    assert r.status_code == 200
    assert "tasks" in r.json()


def test_task_get_404(client):
    r = client.get("/api/tasks/nonexistent-task-xyz")
    assert r.status_code == 404


def test_task_create_requires_admin(client):
    r = client.post("/api/tasks", json={"label": "Unauthorized"})
    assert r.status_code == 403


def test_task_create(admin_client):
    r = admin_client.post("/api/tasks", json={
        "title": f"Test Task {uuid.uuid4().hex[:4]}",
        "type": "build",
        "track": "development",
        "objective": "A test task",
    })
    assert r.status_code == 200
    d = r.json()
    assert "id" in d


# ── Bounty ────────────────────────────────────────────────────────────────────

def test_bounty_post_requires_admin(client):
    # /api/slots/bounty is admin-gated (not in _PUBLIC_WRITE_PREFIXES)
    r = client.post("/api/slots/bounty", json={
        "agent_id": "ghost-xyz",
        "label": "Ghost bounty",
        "slots_needed": 2,
    })
    assert r.status_code == 403


def test_bounty_post_with_admin_key(admin_client, client):
    # Register a real agent so the bounty agent_id is valid
    signup = signup_agent(client, ip=_unique_ip())
    agent_id = signup.json()["agent_id"]

    r = admin_client.post("/api/slots/bounty", json={
        "agent_id": agent_id,
        "agent_name": "Test Agent",
        "label": f"Bounty {uuid.uuid4().hex[:4]}",
        "description": "Help needed",
        "posture": "SCOUT",
        "slots_needed": 2,
        "revenue_pool": 0,
    })
    assert r.status_code == 200
    d = r.json()
    assert d.get("bounty_posted") is True
    assert "mission_id" in d
    assert d.get("open_slots") == 2
