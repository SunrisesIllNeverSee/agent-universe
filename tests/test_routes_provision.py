"""
test_routes_provision.py — HTTP contract tests for app/routes/provision.py

Covers: signup, login, status, heartbeat, registry (admin-gated)
"""
import uuid
from tests.conftest import signup_agent


def _ip():
    return f"10.2.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"


def test_signup_creates_agent(client):
    name = f"TestBot-{uuid.uuid4().hex[:6]}"
    r = signup_agent(client, name=name, ip=_ip())
    assert r.status_code == 200
    data = r.json()
    assert data["welcome"] is True
    assert "agent_id" in data
    assert "api_key" in data
    assert "token" in data
    assert data["email"].endswith("@signomy.xyz")


def test_signup_duplicate_name_409(client):
    name = f"DupBot-{uuid.uuid4().hex[:6]}"
    ip = _ip()
    r1 = signup_agent(client, name=name, ip=ip)
    assert r1.status_code == 200
    # Use different IP to avoid rate limit, same name
    r2 = signup_agent(client, name=name, ip=_ip())
    assert r2.status_code == 409


def test_signup_empty_name_400(client):
    r = client.post(
        "/api/provision/signup",
        json={"name": ""},
        headers={"x-forwarded-for": _ip()},
    )
    assert r.status_code == 400


def test_login_with_valid_key(client):
    r = signup_agent(client, ip=_ip())
    assert r.status_code == 200
    data = r.json()
    login = client.post("/api/provision/login", json={
        "agent_id": data["agent_id"],
        "api_key": data["api_key"],
    })
    assert login.status_code == 200
    assert "token" in login.json()


def test_login_wrong_key_401(client):
    r = signup_agent(client, ip=_ip())
    assert r.status_code == 200
    agent_id = r.json()["agent_id"]
    login = client.post("/api/provision/login", json={
        "agent_id": agent_id,
        "api_key": "wrong-key",
    })
    assert login.status_code == 401


def test_status_returns_agent_info(client):
    r = signup_agent(client, ip=_ip())
    assert r.status_code == 200
    agent_id = r.json()["agent_id"]
    status = client.get(f"/api/provision/status/{agent_id}")
    assert status.status_code == 200
    data = status.json()
    assert "name" in data
    assert "status" in data


def test_status_unknown_agent_404(client):
    r = client.get("/api/provision/status/nonexistent-agent-xyz")
    assert r.status_code == 404


def test_heartbeat_updates_last_seen(client):
    r = signup_agent(client, ip=_ip())
    assert r.status_code == 200
    agent_id = r.json()["agent_id"]
    hb = client.post(f"/api/provision/heartbeat/{agent_id}")
    assert hb.status_code == 200
    assert hb.json()["ok"] is True


def test_registry_requires_admin(client):
    r = client.get("/api/provision/registry")
    assert r.status_code == 403
