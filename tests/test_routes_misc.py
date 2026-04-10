"""
test_routes_misc.py — HTTP contract tests for smaller route modules.

Covers:
- availability.py (5 endpoints) — agent availability blocks
- boost.py (5 endpoints) — post boosting + sponsored listings
- composer.py (3 endpoints) — mission composition templates
- mission_dash.py (5 endpoints) — mission progress dashboard

All write endpoints in these modules are in _PUBLIC_WRITE_PREFIXES or
admin-gated. Confirmed by checking server.py middleware config.
"""
import uuid
from tests.conftest import signup_agent
from tests.test_routes_kassa import _post_payload


def _unique_ip():
    return f"10.5.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"


# ── Availability ──────────────────────────────────────────────────────────────

def test_availability_list(client):
    r = client.get("/api/availability")
    assert r.status_code == 200


def test_availability_stats(client):
    r = client.get("/api/availability/stats")
    assert r.status_code == 200


def test_availability_set(client):
    # /api/availability/{agent_id} is in _PUBLIC_WRITE_PREFIXES
    agent_id = f"avail-test-{uuid.uuid4().hex[:6]}"
    r = client.post(f"/api/availability/{agent_id}", json={
        "available_now": True,
        "domains": ["research", "code"],
        "blocks": [],
        "response_time_hours": 4,
    })
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_availability_get(client):
    agent_id = f"avail-get-{uuid.uuid4().hex[:6]}"
    client.post(f"/api/availability/{agent_id}", json={
        "available_now": True,
        "domains": ["governance"],
        "blocks": [],
        "response_time_hours": 1,
    })
    r = client.get(f"/api/availability/{agent_id}")
    assert r.status_code == 200
    d = r.json()
    assert d.get("available_now") is True


def test_availability_toggle(client):
    agent_id = f"avail-toggle-{uuid.uuid4().hex[:6]}"
    client.post(f"/api/availability/{agent_id}", json={
        "available_now": True, "domains": [], "blocks": [], "response_time_hours": 1,
    })
    r = client.post(f"/api/availability/{agent_id}/toggle")
    assert r.status_code == 200


# ── Boost ─────────────────────────────────────────────────────────────────────

def test_boost_list(client):
    r = client.get("/api/boost")
    assert r.status_code == 200


def test_boost_get_nonexistent_post_returns_not_boosted(client):
    # GET /api/boost/{post_id} returns {boosted: false} even for nonexistent posts
    r = client.get("/api/boost/nonexistent-post-xyz")
    assert r.status_code == 200
    assert r.json().get("boosted") is False


def test_boost_post_404(client, admin_client):
    signup = signup_agent(client, ip=_unique_ip())
    agent_id = signup.json()["agent_id"]
    r = admin_client.post("/api/boost/nonexistent-post-xyz", json={
        "agent_id": agent_id,
        "duration_hours": 24,
    })
    assert r.status_code == 404


def test_boost_post(client, admin_client):
    create = admin_client.post("/api/kassa/posts", json=_post_payload("bounties"))
    assert create.status_code == 200
    post_id = create.json()["id"]

    signup = signup_agent(client, ip=_unique_ip())
    agent_id = signup.json()["agent_id"]

    r = admin_client.post(f"/api/boost/{post_id}", json={
        "agent_id": agent_id,
        "duration_hours": 24,
    })
    assert r.status_code == 200
    assert "boost_id" in r.json()


def test_sponsored_list(client):
    r = client.get("/api/sponsored")
    assert r.status_code == 200


def test_sponsored_create(admin_client):
    r = admin_client.post("/api/sponsored", json={
        "post_id": f"K-{uuid.uuid4().hex[:4]}",
        "label": "Featured Listing",
        "duration_hours": 48,
        "sponsored_by": "operator",
    })
    assert r.status_code in (200, 404)  # 404 if post doesn't exist


# ── Composer ──────────────────────────────────────────────────────────────────

def test_composer_templates_list(client):
    r = client.get("/api/composer/templates")
    assert r.status_code == 200
    d = r.json()
    assert "templates" in d
    assert "count" in d
    assert len(d["templates"]) > 0


def test_composer_template_get(client):
    templates = client.get("/api/composer/templates").json()["templates"]
    if not templates:
        return
    key = templates[0]["key"]
    r = client.get(f"/api/composer/templates/{key}")
    assert r.status_code == 200
    assert r.json()["key"] == key


def test_composer_template_get_404(client):
    r = client.get("/api/composer/templates/nonexistent-template-xyz")
    assert r.status_code == 404


def test_composer_compose(admin_client):
    r = admin_client.post("/api/composer/compose", json={
        "text": "I need someone to audit our smart contracts and write a report.",
    })
    assert r.status_code == 200
    d = r.json()
    # Composer wraps output in "composed" key
    assert "composed" in d
    assert "tab" in d["composed"]
    assert d.get("ready_to_post") is not None


# ── Mission Dashboard ─────────────────────────────────────────────────────────

def test_mission_dash_list(client):
    r = client.get("/api/mission-dash")
    assert r.status_code == 200


def test_mission_dash_init(admin_client):
    mid = f"mission-{uuid.uuid4().hex[:6]}"
    r = admin_client.post(f"/api/mission-dash/{mid}", json={
        "status": "posted",
        "milestones": ["Draft", "Review", "Final"],
        "payout_amount": 250.0,
    })
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_mission_dash_init_and_get(admin_client):
    """Init then get in same test — data persists within the session app."""
    mid = f"mission-dash-{uuid.uuid4().hex[:6]}"
    init = admin_client.post(f"/api/mission-dash/{mid}", json={
        "status": "posted",
        "milestones": ["Step 1"],
        "payout_amount": 100.0,
    })
    assert init.status_code == 200

    r = admin_client.get(f"/api/mission-dash/{mid}")
    assert r.status_code == 200
    assert r.json().get("mission_id") == mid


def test_mission_dash_progress(admin_client):
    mid = f"mission-prog-{uuid.uuid4().hex[:6]}"
    admin_client.post(f"/api/mission-dash/{mid}", json={
        "status": "posted", "milestones": ["Draft"], "payout_amount": 50.0,
    })
    r = admin_client.post(f"/api/mission-dash/{mid}/progress", json={
        "progress_pct": 50,
        "note": "Halfway done",
    })
    assert r.status_code == 200


def test_mission_dash_milestone(admin_client):
    mid = f"mission-ms-{uuid.uuid4().hex[:6]}"
    admin_client.post(f"/api/mission-dash/{mid}", json={
        "status": "posted", "milestones": ["Step 1", "Step 2"], "payout_amount": 75.0,
    })
    r = admin_client.post(f"/api/mission-dash/{mid}/milestone", json={
        "milestone": "Step 1",
        "completed": True,
    })
    assert r.status_code == 200
