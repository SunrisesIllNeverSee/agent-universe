"""
test_routes_forums.py — HTTP contract tests for app/routes/forums.py

7 endpoints: list threads, get thread, create thread, reply, pin, lock.
Forums require KASSA JWT for write operations.
"""
import uuid
from tests.test_routes_kassa import _kassa_signup, _auth_headers


def _unique_title():
    return f"Test Thread {uuid.uuid4().hex[:6]}"


def _create_thread(client):
    """Register kassa agent and create a forum thread. Returns (thread_id, token)."""
    _, _, token = _kassa_signup(client)
    r = client.post("/api/forums/threads",
        json={"title": _unique_title(), "body": "Thread body content here.", "category": "general"},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, f"thread create failed: {r.text}"
    d = r.json()
    # Forum threads return thread_id (not id)
    return d.get("thread_id") or d.get("id"), token


# ── List / Get ────────────────────────────────────────────────────────────────

def test_forums_list_threads(client):
    r = client.get("/api/forums/threads")
    assert r.status_code == 200
    d = r.json()
    assert "threads" in d
    assert "count" in d
    assert isinstance(d["threads"], list)


def test_forums_list_threads_by_category(client):
    r = client.get("/api/forums/threads", params={"category": "governance_qa"})
    assert r.status_code == 200
    assert "threads" in r.json()


def test_forums_list_threads_invalid_category_400(client):
    r = client.get("/api/forums/threads", params={"category": "not-a-real-category"})
    assert r.status_code == 400


def test_forums_get_thread_404(client):
    r = client.get("/api/forums/threads/nonexistent-thread-xyz")
    assert r.status_code == 404


def test_forums_get_thread(client):
    thread_id, _ = _create_thread(client)
    r = client.get(f"/api/forums/threads/{thread_id}")
    assert r.status_code == 200
    d = r.json()
    assert "thread" in d
    assert "replies" in d
    t = d["thread"]
    assert t.get("thread_id") == thread_id or t.get("id") == thread_id


# ── Create ────────────────────────────────────────────────────────────────────

def test_forums_create_thread_requires_jwt(client):
    r = client.post("/api/forums/threads", json={
        "title": "Unauthorized Thread",
        "body": "Should fail",
        "category": "general",
    })
    assert r.status_code == 401


def test_forums_create_thread(client):
    _, _, token = _kassa_signup(client)
    r = client.post("/api/forums/threads",
        json={"title": _unique_title(), "body": "Valid thread body.", "category": "governance_qa"},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200
    d = r.json()
    assert "thread_id" in d or "id" in d
    assert d.get("category") == "governance_qa"


def test_forums_create_thread_short_title_400(client):
    _, _, token = _kassa_signup(client)
    r = client.post("/api/forums/threads",
        json={"title": "ab", "body": "Body here", "category": "general"},
        headers=_auth_headers(token),
    )
    assert r.status_code == 400


def test_forums_create_thread_invalid_category_400(client):
    _, _, token = _kassa_signup(client)
    r = client.post("/api/forums/threads",
        json={"title": _unique_title(), "body": "Body here", "category": "not-a-category"},
        headers=_auth_headers(token),
    )
    assert r.status_code == 400


# ── Reply ─────────────────────────────────────────────────────────────────────

def test_forums_reply_requires_jwt(client):
    thread_id, _ = _create_thread(client)
    r = client.post(f"/api/forums/threads/{thread_id}/replies", json={"body": "Reply"})
    assert r.status_code == 401


def test_forums_reply(client):
    thread_id, token = _create_thread(client)
    r = client.post(f"/api/forums/threads/{thread_id}/replies",
        json={"body": "This is a reply to the thread."},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200
    d = r.json()
    assert "reply_id" in d or "id" in d  # returns reply_id not id


def test_forums_reply_thread_404(client):
    _, _, token = _kassa_signup(client)
    r = client.post("/api/forums/threads/nonexistent-xyz/replies",
        json={"body": "Reply to ghost"},
        headers=_auth_headers(token),
    )
    assert r.status_code == 404


# ── Pin / Lock (admin ops) ────────────────────────────────────────────────────

def test_forums_pin_requires_admin(client):
    thread_id, _ = _create_thread(client)
    r = client.patch(f"/api/forums/threads/{thread_id}/pin")
    assert r.status_code == 403


def test_forums_pin_thread(admin_client, client):
    thread_id, _ = _create_thread(client)
    r = admin_client.patch(f"/api/forums/threads/{thread_id}/pin", json={"pinned": True})
    assert r.status_code == 200
    d = r.json()
    assert d.get("pinned") is True or d.get("ok") is True


def test_forums_lock_requires_admin(client):
    thread_id, _ = _create_thread(client)
    r = client.patch(f"/api/forums/threads/{thread_id}/lock", json={"locked": True})
    assert r.status_code == 403


def test_forums_lock_thread(admin_client, client):
    thread_id, _ = _create_thread(client)
    r = admin_client.patch(f"/api/forums/threads/{thread_id}/lock", json={"locked": True})
    assert r.status_code == 200
    d = r.json()
    assert d.get("locked") is True or d.get("ok") is True
