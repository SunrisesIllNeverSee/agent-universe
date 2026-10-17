"""Hotfix 2026-10-17: poster thread reads/reply are owner-bound; mission channels are participant-only.
Copied from tests/test_p7_shell_app.py (new-site branch) so the hotfix ships with its tests."""
import json
import re
from pathlib import Path

def _cm_agent(client):
    import uuid
    from tests.conftest import signup_agent
    ip = f"10.8.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"cm5-{uuid.uuid4().hex[:6]}", ip=ip).json()
    lg = client.post("/api/provision/login", json={"agent_id": d["agent_id"], "api_key": d["api_key"]},
                     headers={"x-forwarded-for": ip})
    return {"id": d["agent_id"], "name": d["name"], "key": {"Authorization": "Bearer " + d["api_key"]},
            "jwt": {"Authorization": "Bearer " + lg.json()["token"]}}


def test_poster_thread_reads_are_principal_bound(client):
    import uuid
    from datetime import UTC, datetime
    from app.deps import state
    from tests.conftest import signup_agent

    def agent():
        ip = f"10.9.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
        d = signup_agent(client, name=f"cm-{uuid.uuid4().hex[:6]}", ip=ip).json()
        lg = client.post("/api/provision/login", json={"agent_id": d["agent_id"], "api_key": d["api_key"]},
                         headers={"x-forwarded-for": ip})
        return {"id": d["agent_id"], "key": {"Authorization": "Bearer " + d["api_key"]},
                "jwt": {"Authorization": "Bearer " + lg.json()["token"]}}

    owner, staker, other = agent(), agent(), agent()
    pid = f"K-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC).isoformat()
    state.kassa.insert_post({"id": pid, "tab": "iso", "title": "Comms post", "tag": "t", "body": "b",
                             "from_name": "Private Person", "from_email": "private.person@example.com",
                             "created_at": now, "updated_at": now, "poster_agent_id": owner["id"]})
    st = client.post(f"/api/kassa/posts/{pid}/stake", json={}, headers=staker["jwt"])
    assert st.status_code == 200, st.text
    tid = st.json()["thread_id"]
    assert client.post(f"/api/kassa/threads/{tid}/messages", json={"text": "hello poster"}, headers=staker["jwt"]).status_code == 200

    # no credential / forged credential: 401, no data
    assert client.get("/api/kassa/poster/threads").status_code == 401
    assert client.get(f"/api/kassa/poster/threads/{tid}/messages").status_code == 401
    assert client.get("/api/kassa/poster/threads", headers={"Authorization": "Bearer forged"}).status_code == 401
    # the post's owner reads its threads through either door, with explicit fields only
    for cred in (owner["key"], owner["jwt"]):
        r = client.get("/api/kassa/poster/threads", headers=cred)
        assert r.status_code == 200
        mine = [t for t in r.json() if t["thread_id"] == tid]
        assert len(mine) == 1
        assert set(mine[0]) == {"thread_id", "post_id", "post_tab", "post_title", "agent_id", "agent_name",
                                "status", "message_count", "created_at", "updated_at", "role"}
        assert mine[0]["role"] == "poster" and mine[0]["agent_id"] == staker["id"]
        m = client.get(f"/api/kassa/poster/threads/{tid}/messages", headers=cred)
        assert m.status_code == 200
        assert set(m.json()) == {"thread", "messages"}
        assert [x["text"] for x in m.json()["messages"]] == ["hello poster"]
        assert set(m.json()["messages"][0]) == {"msg_id", "thread_id", "sender_type", "sender_name", "text", "created_at"}
        for resp in (r, m):
            assert "private.person@example.com" not in resp.text and "magic" not in resp.text
            assert "Private Person" not in resp.text
    # the staker and an unrelated agent are not the poster: nothing listed, 403 on the thread
    for who in (staker, other):
        assert all(t["thread_id"] != tid for t in client.get("/api/kassa/poster/threads", headers=who["key"]).json())
        assert client.get(f"/api/kassa/poster/threads/{tid}/messages", headers=who["key"]).status_code == 403
        assert client.get(f"/api/kassa/poster/threads/{tid}/messages", headers=who["jwt"]).status_code == 403


# ── Slice 5 (Part A): poster reply, participant-only mission channels ───────


def test_poster_reply_is_principal_bound_and_reaches_the_staker(client):
    import uuid
    from datetime import UTC, datetime
    from app.deps import state

    owner, staker, other = _cm_agent(client), _cm_agent(client), _cm_agent(client)
    pid = f"K-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC).isoformat()
    state.kassa.insert_post({"id": pid, "tab": "iso", "title": "Reply post", "tag": "t", "body": "b",
                             "from_name": "Private Person", "from_email": "private.person@example.com",
                             "created_at": now, "updated_at": now, "poster_agent_id": owner["id"]})
    st = client.post(f"/api/kassa/posts/{pid}/stake", json={}, headers=staker["jwt"])
    assert st.status_code == 200, st.text
    tid = st.json()["thread_id"]
    url = f"/api/kassa/threads/{tid}/poster-reply"

    # anonymous / forged: 401; the staker and an unrelated agent are not the poster: 403
    assert client.post(url, json={"text": "x"}).status_code == 401
    assert client.post(url, json={"text": "x"}, headers={"Authorization": "Bearer forged"}).status_code == 401
    for who in (staker, other):
        for cred in (who["key"], who["jwt"]):
            assert client.post(url, json={"text": "not mine"}, headers=cred).status_code == 403
    # the post's owner replies through either door; explicit response fields
    r = client.post(url, json={"text": "hello staker", "idempotency_key": "k-1"}, headers=owner["key"])
    assert r.status_code == 200, r.text
    assert set(r.json()) == {"sent", "replayed", "msg_id", "thread_id", "seed_doi"}
    assert r.json()["replayed"] is False
    # a retry with the same key returns the first message, nothing is sent twice
    again = client.post(url, json={"text": "hello staker", "idempotency_key": "k-1"}, headers=owner["key"])
    assert again.status_code == 200 and again.json()["replayed"] is True and again.json()["msg_id"] == r.json()["msg_id"]
    assert client.post(url, json={"text": "via session"}, headers=owner["jwt"]).status_code == 200
    assert client.post(url, json={"text": "  "}, headers=owner["key"]).status_code == 400
    # the staker sees both replies in its own thread, sent as the poster, and got an inbox notice
    msgs = client.get(f"/api/kassa/threads/{tid}/messages", headers=staker["jwt"]).json()
    texts = [m["text"] for m in msgs if m["sender_type"] == "poster"]
    assert texts == ["hello staker", "via session"]
    inbox = client.get("/api/agent/inbox?limit=50", headers=staker["key"]).json()
    assert any(m.get("ref_type") == "thread" and m.get("ref_id") == tid and "hello staker" in (m.get("body") or "")
               for m in inbox["messages"])
    for resp in (r, again):
        assert "private.person@example.com" not in resp.text and "Private Person" not in resp.text and "magic" not in resp.text
    # a closed thread takes no reply
    state.kassa.update_thread(tid, {"status": "closed"})
    assert client.post(url, json={"text": "late"}, headers=owner["key"]).status_code == 403


def test_mission_channel_read_is_participant_only(client, monkeypatch):
    import uuid
    from app.deps import state
    from app.routes import core

    owner, member, other = _cm_agent(client), _cm_agent(client), _cm_agent(client)
    label = f"cm5 {uuid.uuid4().hex[:6]}"
    m = client.post("/api/missions", json={"label": label, "objective": "o", "agents": {member["name"]: "secondary"}},
                    headers=owner["key"])
    assert m.status_code == 200, m.text
    mid, chan = m.json()["id"], m.json()["channel"]
    secret = f"TEAM-ONLY-{uuid.uuid4().hex}"
    posted = client.post("/api/messages", json={"sender": owner["name"], "text": secret, "channel": chan}, headers=owner["key"])
    assert posted.status_code == 200, posted.text
    url = f"/api/missions/{mid}/channel"

    assert client.get(url).status_code == 401
    assert client.get(url, headers={"Authorization": "Bearer forged"}).status_code == 401
    for cred in (other["key"], other["jwt"]):
        r = client.get(url, headers=cred)
        assert r.status_code == 403 and secret not in r.text
    for who, role in ((owner, "owner"), (member, "formation")):
        for cred in (who["key"], who["jwt"]):
            r = client.get(url, headers=cred)
            assert r.status_code == 200, r.text
            d = r.json()
            assert set(d) == {"mission_id", "channels", "viewer_role", "messages", "count"}
            assert d["viewer_role"] == role and chan in d["channels"]
            assert [x["text"] for x in d["messages"]] == [secret]
            assert set(d["messages"][0]) == {"id", "sender", "text", "timestamp", "channel", "role_context"}
    op = client.get(url, headers={"X-Admin-Key": state.admin_key})
    assert op.status_code == 200 and op.json()["viewer_role"] == "operator"
    assert client.get("/api/missions/mission-nope/channel", headers={"X-Admin-Key": state.admin_key}).status_code == 404
    assert client.get("/api/missions/mission-nope/channel", headers=owner["key"]).status_code == 403

    # the public projections never carry a mission-channel message
    assert secret not in client.get("/api/state").text
    for reader in (other["name"], f"anon-{uuid.uuid4().hex[:6]}"):
        res = state.mcp_bridge.chat_read(reader, channel=chan)
        assert res["messages"] == [] and res.get("private") is True and secret not in str(res)
    monkeypatch.setattr(core, "_ws_connect_times", {})
    with client.websocket_connect("/ws") as ws:
        assert secret not in str(ws.receive_json())
        ws.send_json({"action": "mcp_read", "payload": {"name": other["name"], "channel": chan}})
        assert secret not in str(ws.receive_json())
    with client.websocket_connect("/ws/public") as ws:
        assert secret not in str(ws.receive_json())
    # the general channel stays public
    from app.mission_channels import is_private_channel
    assert not is_private_channel("general") and is_private_channel(chan) and is_private_channel(f"bounty-{mid}")

