"""
test_routes_lobby.py — HTTP contract tests for app/routes/lobby.py

Covers: chamber status, join request, missing fields guard
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
