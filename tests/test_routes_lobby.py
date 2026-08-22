"""
test_routes_lobby.py — HTTP contract and session invariant tests for the Velvet Rope.

Covers: chamber status, join request, missing fields guard, admin gate,
and the canonical identity-vs-occupancy lifecycle.
"""
import uuid

from app.lobby import LobbyStore


def _approved_user(lobby: LobbyStore) -> str:
    request_id = lobby.submit_join(
        name=f"Lobby Tester {uuid.uuid4().hex[:6]}",
        email=f"lobby-{uuid.uuid4().hex[:6]}@example.com",
    )
    user_id = lobby.approve_join(request_id)
    assert user_id is not None
    return user_id


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


def test_lobby_entry_consumes_exactly_one_seat(tmp_path):
    lobby = LobbyStore(tmp_path / "lobby.db", max_active=2, session_ttl=3600)
    user_id = _approved_user(lobby)

    before = lobby.chamber_status()
    info = lobby.enter(user_id)
    after = lobby.chamber_status()

    assert info.status == "active"
    assert after["active"] == before["active"] + 1
    assert after["available"] == before["available"] - 1


def test_lobby_expiry_releases_seat_and_preserves_identity(tmp_path, monkeypatch):
    import app.lobby as lobby_module

    lobby = LobbyStore(tmp_path / "lobby.db", max_active=1, session_ttl=60)
    user_id = _approved_user(lobby)
    info = lobby.enter(user_id)
    assert info.status == "active"
    assert lobby.is_approved(user_id) is True

    assert info.expires_at is not None
    monkeypatch.setattr(lobby_module.time, "time", lambda: info.expires_at + 1)

    chamber = lobby.chamber_status()
    assert chamber["active"] == 0
    assert chamber["available"] == 1
    assert lobby.is_approved(user_id) is True


def test_lobby_queue_promotes_after_expiry(tmp_path, monkeypatch):
    import app.lobby as lobby_module

    lobby = LobbyStore(tmp_path / "lobby.db", max_active=1, session_ttl=60)
    first_user = _approved_user(lobby)
    second_user = _approved_user(lobby)

    first = lobby.enter(first_user)
    second = lobby.enter(second_user)
    assert first.status == "active"
    assert second.status == "queued"
    assert second.queue_position == 1

    assert first.expires_at is not None
    monkeypatch.setattr(lobby_module.time, "time", lambda: first.expires_at + 1)

    promoted = lobby.status(second_user)
    assert promoted is not None
    assert promoted.status == "active"
    assert lobby.is_approved(first_user) is True
    assert lobby.is_approved(second_user) is True


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
    """POST /api/lobby/approve/{req_id} must require admin key — contains PII (names, emails)."""
    r = client.post("/api/lobby/approve/fake-req-id")
    assert r.status_code == 403


def test_approve_request_with_admin_key_not_found(admin_client):
    """Admin client can reach the endpoint; non-existent req_id returns 404."""
    r = admin_client.post("/api/lobby/approve/nonexistent-req-id-xyz")
    assert r.status_code == 404
