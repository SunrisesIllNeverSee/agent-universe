"""
test_routes_provision.py — HTTP contract tests for app/routes/provision.py

Covers: signup, login, status, heartbeat, registry (admin-gated)
"""
import uuid

from app.deps import state
from app.routes import provision as provision_routes
from tests.conftest import signup_agent


def _ip():
    return f"10.2.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"


def _agent_record(index: int, *, signup_ip: str | None = None) -> dict:
    return {
        "agent_id": f"historical-agent-{index}",
        "handle": f"historical-agent-{index}",
        "name": f"Historical Agent {index}",
        "type": "agent",
        "status": "active",
        "signup_ip": signup_ip or f"172.16.{index // 255}.{index % 255}",
    }


def _restore_registry(registry: list[dict], provision: dict) -> None:
    state.runtime.registry = registry
    state.runtime.provision = provision
    state.runtime.persist_registry()
    provision_routes._rate_stores.clear()


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


def test_signup_ignores_legacy_global_agent_cap(client):
    """Persistent identities must not consume Velvet Rope live capacity."""
    original_registry = list(state.runtime.registry)
    original_provision = dict(state.runtime.provision)
    try:
        state.runtime.registry = [_agent_record(i) for i in range(51)]
        state.runtime.provision = {**original_provision, "max_agents": 50}
        state.runtime.persist_registry()
        provision_routes._rate_stores.clear()

        r = signup_agent(
            client,
            name=f"CapacityIndependent-{uuid.uuid4().hex[:6]}",
            ip=_ip(),
        )
        assert r.status_code == 200, r.text
        assert r.json()["welcome"] is True
        assert len([x for x in state.runtime.registry if x.get("type") == "agent"]) == 52
    finally:
        _restore_registry(original_registry, original_provision)


def test_signup_does_not_consume_lobby_seat(client):
    """Registration creates identity only; chamber occupancy begins at lobby entry."""
    before = state.lobby.chamber_status()
    r = signup_agent(
        client,
        name=f"IdentityOnly-{uuid.uuid4().hex[:6]}",
        ip=_ip(),
    )
    assert r.status_code == 200
    after = state.lobby.chamber_status()
    assert after["active"] == before["active"]
    assert after["available"] == before["available"]


def test_signup_per_origin_cap_still_enforced(client):
    """Removing the global registry cap must not weaken Sybil resistance."""
    original_registry = list(state.runtime.registry)
    original_provision = dict(state.runtime.provision)
    origin_ip = _ip()
    try:
        state.runtime.registry = [
            _agent_record(i, signup_ip=origin_ip) for i in range(3)
        ]
        state.runtime.persist_registry()
        provision_routes._rate_stores.clear()

        r = signup_agent(
            client,
            name=f"FourthFromOrigin-{uuid.uuid4().hex[:6]}",
            ip=origin_ip,
        )
        assert r.status_code == 429
        assert r.json()["error"] == "Max agents per origin reached"
    finally:
        _restore_registry(original_registry, original_provision)


def test_signup_hourly_rate_limit_still_enforced(client):
    """Two signup attempts per IP per hour remains the first-line rate limit."""
    provision_routes._rate_stores.clear()
    ip = _ip()
    assert signup_agent(client, name=f"RateOne-{uuid.uuid4().hex[:6]}", ip=ip).status_code == 200
    assert signup_agent(client, name=f"RateTwo-{uuid.uuid4().hex[:6]}", ip=ip).status_code == 200
    third = signup_agent(client, name=f"RateThree-{uuid.uuid4().hex[:6]}", ip=ip)
    assert third.status_code == 429
    assert "Rate limit" in third.text
    provision_routes._rate_stores.clear()


def test_signup_preserves_handle_and_capabilities(client):
    handle = f"agent-handle-{uuid.uuid4().hex[:6]}"
    caps = ["research", "mcp"]
    r = client.post(
        "/api/provision/signup",
        json={
            "name": f"HandleProvisionBot-{uuid.uuid4().hex[:6]}",
            "handle": handle,
            "system": "claude",
            "capabilities": caps,
        },
        headers={"x-forwarded-for": _ip()},
    )
    assert r.status_code == 200
    agent_id = r.json()["agent_id"]

    status = client.get(f"/api/provision/status/{agent_id}")
    assert status.status_code == 200

    profile = client.get(f"/api/agents/{handle}")
    assert profile.status_code == 200
    data = profile.json()
    assert data["agent_id"] == agent_id
    assert data["handle"] == handle
    assert data["capabilities"] == caps


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
    # Dashboard-compatible field names
    assert "agent_name" in data
    assert "governance_posture" in data


def test_status_unknown_agent_404(client):
    r = client.get("/api/provision/status/nonexistent-agent-xyz")
    assert r.status_code == 404


def test_status_with_valid_bearer_key(client):
    """Dashboard login path: Bearer key is validated against stored hash."""
    r = signup_agent(client, ip=_ip())
    assert r.status_code == 200
    data = r.json()
    agent_id = data["agent_id"]
    api_key = data["api_key"]

    status = client.get(
        f"/api/provision/status/{agent_id}",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert status.status_code == 200
    assert status.json()["agent_id"] == agent_id


def test_status_with_invalid_bearer_key_401(client):
    """Wrong API key via Bearer header is rejected."""
    r = signup_agent(client, ip=_ip())
    assert r.status_code == 200
    agent_id = r.json()["agent_id"]

    status = client.get(
        f"/api/provision/status/{agent_id}",
        headers={"Authorization": "Bearer wrong-key-xyz"},
    )
    assert status.status_code == 401


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
