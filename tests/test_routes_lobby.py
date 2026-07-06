"""
test_routes_lobby.py — HTTP contract tests for app/routes/lobby.py

Covers: chamber status, join request, missing fields guard, admin gate
"""
import uuid


def test_chamber_status(client):
    r = client.get("/api/lobby/chamber")
    assert r.status_code == 200
    data = r.json()
    assert "active" in data
    assert "capacity" in data
    assert "available" in data


def test_join_request(client):
    r = client.post("/api/lobby/join", json={
        "name": f"Tester-{uuid.uuid4().hex[:6]}",
        "email": f"test-{uuid.uuid4().hex[:6]}@example.com",
    })
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "request_id" in data


def test_join_missing_fields_400(client):
    r = client.post("/api/lobby/join", json={})
    assert r.status_code == 400


# ── Admin gate ────────────────────────────────────────────────────────────────

def test_list_requests_requires_admin_key(client):
    """GET /api/lobby/requests must require admin key — contains PII (names, emails)."""
    r = client.get("/api/lobby/requests")
    assert r.status_code == 403


def test_list_requests_with_admin_key(admin_client):
    """Admin client can list join requests."""
    r = admin_client.get("/api/lobby/requests")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_approve_request_requires_admin_key(client):
    """POST /api/lobby/approve/{req_id} must require admin key."""
    r = client.post("/api/lobby/approve/fake-req-id")
    assert r.status_code == 403


def test_approve_request_with_admin_key_not_found(admin_client):
    """Admin client can reach the endpoint; non-existent req_id returns 404."""
    r = admin_client.post("/api/lobby/approve/nonexistent-req-id-xyz")
    assert r.status_code == 404
