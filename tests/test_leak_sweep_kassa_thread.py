"""Leak sweep 2026-10-16: a KA§§A negotiation thread shows the poster's email only to the
poster (magic link). Before: any registered agent could stake any open post and read the
poster's private from_email from GET /api/kassa/threads, /api/kassa/threads/{id} and the
/ws/thread thread_info frame -- the same address public_kassa_post hides from discovery."""
import hashlib
import uuid
from datetime import UTC, datetime

from app.deps import state
from tests.conftest import signup_agent


def _setup(client, admin_client):
    email = f"poster-{uuid.uuid4().hex[:8]}@example.com"
    pid = admin_client.post("/api/kassa/posts", json={"tab": "bounties", "title": "t", "body": "b",
                                                      "from_name": "P", "from_email": email}).json()["id"]
    d = signup_agent(client, name=f"kt-{uuid.uuid4().hex[:6]}").json()
    jwt = {"Authorization": f"Bearer {d['token']}"}
    r = client.post(f"/api/kassa/posts/{pid}/stake", headers=jwt)
    assert r.status_code == 200, r.text
    return email, jwt, r.json()["thread_id"]


def test_staking_agent_does_not_see_poster_email(client, admin_client):
    email, jwt, tid = _setup(client, admin_client)
    lst = client.get("/api/kassa/threads", headers=jwt)
    one = client.get(f"/api/kassa/threads/{tid}", headers=jwt)
    assert lst.status_code == 200 and one.status_code == 200
    t = next(t for t in lst.json() if t["thread_id"] == tid)
    for view in (t, one.json()):
        assert "poster_email" not in view and "magic_token" not in view
        assert view["poster_name"] == "P" and view["thread_id"] == tid
    assert email not in lst.text and email not in one.text
    with client.websocket_connect(f"/ws/thread/{tid}?token={jwt['Authorization'][7:]}") as ws:
        info = ws.receive_json()
    assert info["type"] == "thread_info" and "poster_email" not in info["payload"]


def test_poster_magic_link_still_sees_own_thread(client):
    magic = uuid.uuid4().hex
    tid = f"thr-{uuid.uuid4().hex[:16]}"
    now = datetime.now(UTC).isoformat()
    state.kassa.insert_thread({"thread_id": tid, "post_id": "K-x", "agent_id": "agent-x", "agent_name": "x",
                               "poster_name": "P", "poster_email": "me@example.com",
                               "magic_token": hashlib.sha256(magic.encode()).hexdigest(),
                               "status": "open", "message_count": 0, "created_at": now, "updated_at": now})
    r = client.get(f"/api/kassa/threads/{tid}?magic={magic}")
    assert r.status_code == 200
    assert r.json()["poster_email"] == "me@example.com" and "magic_token" not in r.json()
