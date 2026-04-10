"""
test_routes_core.py — HTTP contract tests for app/routes/core.py

Covers: /health, /api/state, /api/audit, /api/hash,
        /api/governance/check, /api/vault/files, /api/forks
"""


def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "version" in data
    assert "uptime_s" in data
    assert "ts" in data


def test_state_returns_snapshot(client):
    r = client.get("/api/state")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert "governance" in data


def test_audit_returns_list(client):
    r = client.get("/api/audit")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_hash_returns_four_hashes(client):
    r = client.get("/api/hash")
    assert r.status_code == 200
    data = r.json()
    assert "state_hash" in data
    assert "content_hash" in data
    assert "onchain_hash" in data
    assert "snapshot_hash" in data


def test_governance_check_permitted(admin_client):
    r = admin_client.post("/api/governance/check", json={"action": "read data"})
    assert r.status_code == 200
    data = r.json()
    assert "permitted" in data


def test_vault_files_returns_dict(client):
    r = client.get("/api/vault/files")
    assert r.status_code == 200
    data = r.json()
    assert "vault_files" in data


def test_forks_empty_initially(client):
    r = client.get("/api/forks")
    assert r.status_code == 200
    data = r.json()
    assert "forks" in data
    assert isinstance(data["forks"], list)
