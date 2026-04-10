"""
test_routes_economy.py — HTTP contract tests for app/routes/economy.py

Covers: tiers, tier check, balance, trial lifecycle, pay auth guard, blackcard info

Note: POST economy endpoints are admin-gated (not in _PUBLIC_WRITE_PREFIXES).
      GET endpoints are public.
"""
import uuid


def test_get_tiers(client):
    r = client.get("/api/economy/tiers")
    assert r.status_code == 200
    data = r.json()
    assert "tiers" in data
    tiers = data["tiers"]
    for key in ("ungoverned", "governed", "constitutional", "blackcard"):
        assert key in tiers


def test_check_tier_empty_metrics(admin_client):
    r = admin_client.post("/api/economy/tier", json={"agent_id": "x", "metrics": {}})
    assert r.status_code == 200
    data = r.json()
    assert "tier" in data
    assert data["tier"].upper() == "UNGOVERNED"


def test_check_tier_returns_valid_tier(admin_client):
    r = admin_client.post("/api/economy/tier", json={
        "agent_id": "y",
        "metrics": {"governance_checks": 20, "governance_violations": 0},
    })
    assert r.status_code == 200
    data = r.json()
    assert "tier" in data
    assert data["tier"].upper() in ("UNGOVERNED", "GOVERNED", "CONSTITUTIONAL", "BLACK_CARD")


def test_balance_zero_for_new_agent(client):
    r = client.get(f"/api/economy/balance/nonexistent-{uuid.uuid4().hex[:8]}")
    assert r.status_code == 200
    data = r.json()
    assert "balance" in data
    assert data["balance"] == 0


def test_trial_init(admin_client):
    agent_id = f"trial-agent-{uuid.uuid4().hex[:6]}"
    r = admin_client.post("/api/economy/trial/init", json={"agent_id": agent_id})
    assert r.status_code == 200
    data = r.json()
    assert "trial" in data or "ok" in data


def test_trial_status(admin_client):
    agent_id = f"trial-status-{uuid.uuid4().hex[:6]}"
    admin_client.post("/api/economy/trial/init", json={"agent_id": agent_id})
    r = admin_client.get(f"/api/economy/trial/{agent_id}")
    assert r.status_code == 200


def test_trial_commit(admin_client):
    agent_id = f"trial-commit-{uuid.uuid4().hex[:6]}"
    admin_client.post("/api/economy/trial/init", json={"agent_id": agent_id})
    r = admin_client.post("/api/economy/trial/commit", json={"agent_id": agent_id})
    assert r.status_code == 200


def test_trial_depart(admin_client):
    agent_id = f"trial-depart-{uuid.uuid4().hex[:6]}"
    admin_client.post("/api/economy/trial/init", json={"agent_id": agent_id})
    r = admin_client.post("/api/economy/trial/depart", json={"agent_id": agent_id})
    assert r.status_code == 200


def test_pay_requires_jwt(admin_client):
    # /api/economy/pay requires JWT on top of admin key — should 401 with no Bearer
    r = admin_client.post("/api/economy/pay", json={"amount": 10, "agent_id": "x"})
    assert r.status_code == 401


def test_blackcard_info(client):
    r = client.get("/api/economy/blackcard/info")
    assert r.status_code == 200
    data = r.json()
    assert "price_usd" in data
    assert "perks" in data
