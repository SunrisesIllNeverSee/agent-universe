"""Leak sweep 2026-10-16: GET /api/provision/status/{agent_id} without a key is public status
only; the agent's own provisioning settings (rate_limit) need the agent's key."""
from tests.conftest import signup_agent


def test_status_rate_limit_only_with_own_key(client):
    d = signup_agent(client).json()
    anon = client.get(f"/api/provision/status/{d['agent_id']}")
    assert anon.status_code == 200 and "rate_limit" not in anon.json()
    assert anon.json()["agent_id"] == d["agent_id"] and anon.json()["status"] == "active"
    own = client.get(f"/api/provision/status/{d['agent_id']}", headers={"Authorization": f"Bearer {d['api_key']}"})
    assert own.status_code == 200 and own.json()["rate_limit"] == d["rate_limit"]
    other = signup_agent(client).json()
    wrong = client.get(f"/api/provision/status/{d['agent_id']}", headers={"Authorization": f"Bearer {other['api_key']}"})
    assert wrong.status_code == 401
