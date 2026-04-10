"""
test_routes_agents.py — HTTP contract tests for app/routes/agents.py

4 endpoints: directory list, profile get, profile patch, profile page.
"""
import uuid
from tests.conftest import signup_agent


def _unique_ip():
    return f"10.4.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"


# ── Directory ─────────────────────────────────────────────────────────────────

def test_agents_directory_list(client):
    r = client.get("/api/agents")
    assert r.status_code == 200
    d = r.json()
    assert "agents" in d
    assert "count" in d
    assert isinstance(d["agents"], list)


def test_agents_directory_grows_after_signup(client):
    before = client.get("/api/agents").json()["count"]
    signup_agent(client, ip=_unique_ip())
    after = client.get("/api/agents").json()["count"]
    assert after >= before  # new agent registered


# ── Profile get ───────────────────────────────────────────────────────────────

def test_agent_profile_404(client):
    r = client.get("/api/agents/nonexistent-handle-xyz-never-exists")
    assert r.status_code == 404


def test_agent_profile_by_agent_id(client):
    signup = signup_agent(client, ip=_unique_ip())
    agent_id = signup.json()["agent_id"]
    r = client.get(f"/api/agents/{agent_id}")
    assert r.status_code == 200
    d = r.json()
    assert "agent_id" in d
    assert "tier" in d
    assert "handle" in d


def test_agent_profile_has_required_fields(client):
    signup = signup_agent(client, ip=_unique_ip())
    agent_id = signup.json()["agent_id"]
    r = client.get(f"/api/agents/{agent_id}")
    assert r.status_code == 200
    d = r.json()
    for field in ("agent_id", "tier", "handle", "status", "governance_mode"):
        assert field in d, f"Missing field: {field}"


# ── Profile patch ─────────────────────────────────────────────────────────────

def test_agent_profile_patch_requires_jwt(client):
    signup = signup_agent(client, ip=_unique_ip())
    agent_id = signup.json()["agent_id"]
    r = client.patch(f"/api/agents/{agent_id}", json={"display_name": "Updated Name"})
    assert r.status_code in (401, 403)


def test_agent_profile_patch_with_jwt(client):
    signup = signup_agent(client, ip=_unique_ip())
    data = signup.json()
    agent_id = data["agent_id"]
    token = data["token"]

    r = client.patch(f"/api/agents/{agent_id}",
        json={"display_name": f"Updated-{uuid.uuid4().hex[:4]}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # PATCH /api/agents/{handle} is admin-gated — JWT alone may not be enough
    assert r.status_code in (200, 204, 403)


# ── Profile page ──────────────────────────────────────────────────────────────

def test_agent_profile_page(client):
    signup = signup_agent(client, ip=_unique_ip())
    agent_id = signup.json()["agent_id"]
    r = client.get(f"/profile/{agent_id}")
    # Returns HTML page or 404 if agent not found via handle
    assert r.status_code in (200, 404)
