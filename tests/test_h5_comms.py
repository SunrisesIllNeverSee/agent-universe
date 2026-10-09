"""
test_h5_comms.py — H5 Communications hardening regression suite (2026-10-07).

Covers the corrected boundaries:
  A1  GET /api/inbox + /api/inbox/{id} — PII reads now admin-gated; apply stays public.
  A2  GET /api/kassa/messages — contact PII now admin-gated; contact stays public.
  A3  MCP agent.profile public view must not return operator_contact.
  B1  POST /api/messages is the canonical route; console wiring targets it.
  B2  slot_filled / slot_left emitted only after authoritative commit.
  C   KA§§A magic-token storage parity — REST and MCP both store the hash;
      poster ?magic= verification works/fails identically on either transport.
  D   Town Hall realtime events — emitted post-commit, public-envelope only.
  +   Event-payload PII: kassa_contact / inbox_application /
      kassa_thread_message must not broadcast private fields on the public hubs.
"""
import asyncio
import uuid

import pytest

from tests.conftest import signup_agent


def _uniq(p="h5"):
    return f"{p}-{uuid.uuid4().hex[:8]}"


def _kassa_agent(client):
    """Register a kassa agent; return (agent_id, api_key, jwt)."""
    name = _uniq("kassa")
    r = client.post("/api/kassa/agent/register", json={"name": name, "system": "claude"})
    assert r.status_code == 200, r.text
    d = r.json()
    return d["agent_id"], d["api_key"], d["token"]


def _kassa_post(client, admin_client):
    """Create an open kassa post (admin path)."""
    r = admin_client.post("/api/kassa/posts", json={
        "tab": "bounties",
        "title": _uniq("post"),
        "tag": "test",
        "body": "H5 test post body",
        "from_name": "Poster One",
        "from_email": "poster@example.com",
    })
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture
def captured_emits(monkeypatch):
    """Record every state.emit call: (event_type, payload)."""
    from app.deps import state
    events = []

    async def fake_emit(event_type, payload):
        events.append((event_type, payload))

    monkeypatch.setattr(state, "emit", fake_emit)
    return events


# ═══ A1 — application inbox read guard ═══════════════════════════════════════

def test_a1_inbox_list_rejects_anonymous(client):
    assert client.get("/api/inbox").status_code == 403


def test_a1_inbox_get_rejects_anonymous(client):
    assert client.get("/api/inbox/app-nonexistent").status_code == 403


def test_a1_inbox_rejects_forged_admin_key(client):
    r = client.get("/api/inbox", headers={"X-Admin-Key": "forged-not-the-key"})
    assert r.status_code == 403


def test_a1_inbox_admin_reads(admin_client):
    assert admin_client.get("/api/inbox").status_code == 200


def test_a1_apply_stays_public(client):
    r = client.post("/api/inbox/apply", json={
        "name": _uniq("applicant"), "role": "developer",
        "handle": _uniq(), "message": "hello",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_a1_apply_event_is_public_safe(client, captured_emits):
    client.post("/api/inbox/apply", json={
        "name": "PII-Should-Not-Broadcast", "role": "dev",
        "handle": "pii-handle", "message": "secret applicant note",
    })
    apps = [p for t, p in captured_emits if t == "inbox_application"]
    assert apps, "inbox_application event not emitted"
    for p in apps:
        assert "name" not in p and "handle" not in p and "message" not in p


# ═══ A2 — contact inbox read guard ═══════════════════════════════════════════

def test_a2_kassa_messages_rejects_anonymous(client):
    assert client.get("/api/kassa/messages").status_code == 403


def test_a2_kassa_messages_rejects_forged_key(client):
    r = client.get("/api/kassa/messages", headers={"X-Admin-Key": "wrong"})
    assert r.status_code == 403


def test_a2_kassa_messages_admin_reads(admin_client):
    assert admin_client.get("/api/kassa/messages").status_code == 200


def test_a2_contact_stays_public(client):
    r = client.post("/api/kassa/contact", json={
        "post_id": "K-00001", "tab": "bounties",
        "from_name": _uniq("sender"), "from_email": f"{_uniq()}@example.com",
        "message": "test contact",
    })
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_a2_contact_event_is_public_safe(client, captured_emits):
    client.post("/api/kassa/contact", json={
        "post_id": "K-00001", "tab": "bounties",
        "from_name": "PII-Contact-Name", "from_email": "pii-contact@example.com",
        "message": "private body",
    })
    evs = [p for t, p in captured_emits if t == "kassa_contact"]
    assert evs, "kassa_contact event not emitted"
    for p in evs:
        assert "from_email" not in p and "from_name" not in p and "message" not in p


# ═══ A3 — operator_contact is private ════════════════════════════════════════

def test_a3_public_profile_strips_operator_contact(app):
    from fastmcp import Client
    from app.deps import state

    name = _uniq("prof")
    state.runtime.registry.append({
        "agent_id": _uniq("agent"), "name": name, "status": "active",
        "key_hash": "x", "key_prefix": "kassa_abc***",
        "signup_ip": "1.2.3.4",
        "governance": "open", "role": "secondary", "system": "claude",
        "operator_contact": "secret-operator@example.com",
    })

    mcp = state.mcp_bridge.build_fastmcp()

    async def call():
        async with Client(mcp) as c:
            return await c.call_tool("agent.profile", {"agent_handle": name})

    result = asyncio.run(call())
    data = result.structured_content or {}
    assert "operator_contact" not in data
    assert "key_hash" not in data


# ═══ B1 — console messaging route ════════════════════════════════════════════

def test_b1_canonical_messages_route_works(admin_client):
    r = admin_client.post("/api/messages", json={
        "sender": "operator", "text": _uniq("console-msg"),
        "channel": "console", "role_context": "operator",
    })
    assert r.status_code == 200
    d = r.json()
    assert d.get("id") or d.get("text")


def test_b1_singular_message_route_is_dead(client):
    # /api/message (singular) must NOT exist — no shadow alias.
    r = client.post("/api/message", json={"sender": "x", "text": "y"})
    assert r.status_code in (403, 404, 405)


def test_b1_console_targets_canonical_route():
    from pathlib import Path
    html = (Path(__file__).resolve().parents[1] / "frontend" / "console.html").read_text()
    assert "'/api/messages'" in html
    assert "'/api/message'" not in html.replace("'/api/messages'", "")


# ═══ B2 — slot lifecycle events ══════════════════════════════════════════════

def _make_slot(admin_client):
    r = admin_client.post("/api/slots/create", json={
        "mission_id": _uniq("mission"), "formation_id": "test-formation",
        "posture": "SCOUT", "label": "H5 Test Mission",
        "positions": [{"row": 0, "col": 0}],
        "roles": ["primary"], "revenue_splits": [100],
    })
    assert r.status_code == 200, r.text
    return r.json()["slots"][0]


def _provision_agent(client, name):
    resp = signup_agent(client, name=name, ip=f"10.77.{uuid.uuid4().int%255}.{uuid.uuid4().int%255}")
    assert resp.status_code == 200, resp.text
    return resp.json()["agent_id"]


def test_b2_slot_fill_emits_after_commit(client, admin_client, captured_emits):
    slot = _make_slot(admin_client)
    agent_id = _provision_agent(client, _uniq("h5filler"))
    captured_emits.clear()
    r = admin_client.post("/api/slots/fill", json={
        "slot_id": slot["id"], "agent_id": agent_id, "agent_name": "H5 Agent",
    })
    assert r.status_code == 200, r.text
    fills = [p for t, p in captured_emits if t == "slot_filled"]
    assert len(fills) == 1
    assert fills[0]["slot_id"] == slot["id"]
    assert fills[0]["mission_id"] == slot["mission_id"]


def test_b2_slot_fill_failure_emits_nothing(client, captured_emits):
    r = client.post("/api/slots/fill", json={
        "slot_id": "slot-nonexistent", "agent_id": _uniq("ghost"),
    })
    assert r.status_code in (400, 401, 403, 404, 409)
    assert not [p for t, p in captured_emits if t == "slot_filled"]


def test_b2_slot_leave_emits_after_commit(client, admin_client, captured_emits):
    slot = _make_slot(admin_client)
    agent_id = _provision_agent(client, _uniq("h5leaver"))
    r = admin_client.post("/api/slots/fill", json={
        "slot_id": slot["id"], "agent_id": agent_id,
    })
    assert r.status_code == 200, r.text
    captured_emits.clear()
    r = admin_client.post("/api/slots/leave", json={
        "slot_id": slot["id"], "agent_id": agent_id,
    })
    assert r.status_code == 200, r.text
    leaves = [p for t, p in captured_emits if t == "slot_left"]
    assert len(leaves) == 1
    assert leaves[0]["slot_id"] == slot["id"]


# ═══ C — KA§§A magic-token transport parity ══════════════════════════════════

def test_c_rest_thread_magic_auth(client, admin_client, monkeypatch):
    """REST stake → magic link → poster auth works; wrong/cross tokens fail."""
    from app.routes import kassa as kassa_routes
    captured = {}

    def fake_magic_link(**kw):
        captured["magic_token"] = kw.get("magic_token")

    monkeypatch.setattr(kassa_routes, "send_magic_link", fake_magic_link)

    _, _, jwt1 = _kassa_agent(client)
    post_id = _kassa_post(client, admin_client)
    r = client.post(
        f"/api/kassa/posts/{post_id}/stake",
        json={"amount": 50.0},
        headers={"Authorization": f"Bearer {jwt1}"},
    )
    assert r.status_code == 200, r.text
    thread_id = r.json()["thread_id"]

    magic = captured.get("magic_token")
    assert magic, "magic link email never captured"

    # correct token → poster read works
    assert client.get(f"/api/kassa/threads/{thread_id}?magic={magic}").status_code == 200
    # wrong token → 403
    assert client.get(f"/api/kassa/threads/{thread_id}?magic=wrong-token").status_code == 403
    # malformed token → 403 (not 500)
    assert client.get(f"/api/kassa/threads/{thread_id}?magic=").status_code == 401
    # no auth → 401
    assert client.get(f"/api/kassa/threads/{thread_id}").status_code == 401


def test_c_mcp_thread_stores_hashed_magic(app, client, admin_client):
    """MCP market.stake must store the hash, same contract as REST."""
    from fastmcp import Client
    from app.deps import state

    _, api_key, _ = _kassa_agent(client)
    post_id = _kassa_post(client, admin_client)

    mcp = state.mcp_bridge.build_fastmcp()

    async def call():
        async with Client(mcp) as c:
            return await c.call_tool("market.stake", {
                "api_key": api_key, "post_id": post_id, "amount": 25.0,
            })

    result = asyncio.run(call())
    data = result.structured_content or {}
    thread_id = data.get("thread_id")
    assert thread_id, data

    stored = state.kassa.get_thread(thread_id)
    assert stored, "thread not persisted"
    tok = stored.get("magic_token", "")
    # hash contract: 64-char hex sha256, not the urlsafe plaintext
    assert len(tok) == 64 and all(c in "0123456789abcdef" for c in tok), \
        "MCP path stored a non-hash magic token"
    # poster auth behaves identically: unknown magic → 403
    assert client.get(f"/api/kassa/threads/{thread_id}?magic=nope").status_code == 403


def test_c_cross_thread_magic_rejected(client, admin_client, monkeypatch):
    """A magic token from thread A must not open thread B."""
    from app.routes import kassa as kassa_routes
    tokens = []

    def fake_magic_link(**kw):
        tokens.append(kw.get("magic_token"))

    monkeypatch.setattr(kassa_routes, "send_magic_link", fake_magic_link)

    _, _, jwt1 = _kassa_agent(client)
    p1 = _kassa_post(client, admin_client)
    p2 = _kassa_post(client, admin_client)
    r1 = client.post(f"/api/kassa/posts/{p1}/stake", json={"amount": 1.0},
                     headers={"Authorization": f"Bearer {jwt1}"})
    r2 = client.post(f"/api/kassa/posts/{p2}/stake", json={"amount": 1.0},
                     headers={"Authorization": f"Bearer {jwt1}"})
    t1 = r1.json()["thread_id"]
    t2 = r2.json()["thread_id"]
    assert len(tokens) == 2
    # token for t2 against t1 → 403
    assert client.get(f"/api/kassa/threads/{t1}?magic={tokens[1]}").status_code == 403
    # each token opens only its own thread
    assert client.get(f"/api/kassa/threads/{t1}?magic={tokens[0]}").status_code == 200
    assert client.get(f"/api/kassa/threads/{t2}?magic={tokens[1]}").status_code == 200


def test_c_thread_message_event_is_public_safe(client, admin_client, monkeypatch, captured_emits):
    """Thread bodies never reach the global hubs — only the scoped thread hub."""
    from app.routes import kassa as kassa_routes
    monkeypatch.setattr(kassa_routes, "send_magic_link", lambda **kw: None)

    _, _, jwt1 = _kassa_agent(client)
    post_id = _kassa_post(client, admin_client)
    r = client.post(f"/api/kassa/posts/{post_id}/stake", json={"amount": 5.0},
                    headers={"Authorization": f"Bearer {jwt1}"})
    tid = r.json()["thread_id"]

    r = client.post(
        f"/api/kassa/threads/{tid}/messages",
        json={"text": "private negotiation content"},
        headers={"Authorization": f"Bearer {jwt1}"},
    )
    assert r.status_code == 200, r.text
    msgs = [p for t, p in captured_emits if t == "kassa_thread_message"]
    assert msgs, "kassa_thread_message event not emitted"
    for p in msgs:
        assert "msg" not in p and "text" not in p and "sender_name" not in p
        assert p.get("thread_id") == tid


# ═══ D — Town Hall realtime contract ═════════════════════════════════════════

def test_d_thread_created_event(client, captured_emits):
    _, _, jwt1 = _kassa_agent(client)
    r = client.post("/api/forums/threads",
                    json={"category": "general", "title": "H5 thread",
                          "body": "body text"},
                    headers={"Authorization": f"Bearer {jwt1}"})
    assert r.status_code == 200, r.text
    tid = r.json()["thread_id"]
    evs = [p for t, p in captured_emits if t == "forum_thread_created"]
    assert len(evs) == 1
    assert evs[0]["thread_id"] == tid
    # payload envelope ⊆ public-read fields
    assert set(evs[0]) <= {"thread_id", "category", "title",
                           "author_id", "author_type", "created_at"}


def test_d_reply_event(client, captured_emits):
    _, _, jwt1 = _kassa_agent(client)
    r = client.post("/api/forums/threads",
                    json={"category": "general", "title": "H5 reply host",
                          "body": "host body"},
                    headers={"Authorization": f"Bearer {jwt1}"})
    tid = r.json()["thread_id"]
    captured_emits.clear()
    r = client.post(f"/api/forums/threads/{tid}/replies",
                    json={"body": "a reply"},
                    headers={"Authorization": f"Bearer {jwt1}"})
    assert r.status_code == 200, r.text
    evs = [p for t, p in captured_emits if t == "forum_reply_created"]
    assert len(evs) == 1
    assert evs[0]["thread_id"] == tid
    assert set(evs[0]) <= {"reply_id", "thread_id", "author_id", "created_at"}


def test_d_no_event_on_failed_mutation(client, captured_emits):
    _, _, jwt1 = _kassa_agent(client)
    # invalid category → mutation fails → no event
    r = client.post("/api/forums/threads",
                    json={"category": "bogus", "title": "bad", "body": "x"},
                    headers={"Authorization": f"Bearer {jwt1}"})
    assert r.status_code == 400
    # unauthenticated reply → no event
    r = client.post("/api/forums/threads/thr-nope/replies", json={"body": "x"})
    assert r.status_code in (401, 403, 404)
    assert not [t for t, _ in captured_emits if t.startswith("forum_")]


def test_d_moderation_events(client, admin_client, captured_emits):
    _, _, jwt1 = _kassa_agent(client)
    r = client.post("/api/forums/threads",
                    json={"category": "general", "title": "H5 mod target",
                          "body": "body"},
                    headers={"Authorization": f"Bearer {jwt1}"})
    tid = r.json()["thread_id"]
    captured_emits.clear()

    assert admin_client.patch(f"/api/forums/threads/{tid}/pin",
                              json={"pinned": True}).status_code == 200
    assert admin_client.patch(f"/api/forums/threads/{tid}/lock",
                              json={"locked": True}).status_code == 200
    pins = [p for t, p in captured_emits if t == "forum_thread_pinned"]
    locks = [p for t, p in captured_emits if t == "forum_thread_locked"]
    assert pins == [{"thread_id": tid, "pinned": True}]
    assert locks == [{"thread_id": tid, "locked": True}]

    captured_emits.clear()
    # failed pin (missing thread) → no event
    assert admin_client.patch("/api/forums/threads/thr-missing/pin",
                              json={"pinned": True}).status_code == 404
    assert not [t for t, _ in captured_emits if t.startswith("forum_")]


def test_d_public_reads_still_open(client):
    assert client.get("/api/forums/threads").status_code == 200


# ═══ Regression — existing comms loops still work ════════════════════════════

def test_reg_agent_inbox_still_works(client):
    resp = signup_agent(client, name=_uniq("inbox"), ip=f"10.88.{uuid.uuid4().int%255}.{uuid.uuid4().int%255}")
    assert resp.status_code == 200, resp.text
    api_key = resp.json()["api_key"]
    r = client.get("/api/agent/inbox", headers={"Authorization": f"Bearer {api_key}"})
    assert r.status_code == 200
    assert any(m.get("kind") == "system" for m in r.json().get("messages", r.json() if isinstance(r.json(), list) else []))


# ═══ H1/H3 — MCP govern.vote mutates authoritative state ════════════════════

def _mcp_vote(api_key, motion_id, vote):
    import asyncio as _aio
    from fastmcp import Client
    from app.deps import state as _s

    mcp = _s.mcp_bridge.build_fastmcp()

    async def call():
        async with Client(mcp) as c:
            return await c.call_tool("govern.vote", {
                "api_key": api_key, "motion_id": motion_id, "vote": vote,
            })

    r = _aio.run(call())
    return r.structured_content or {}


def _open_meeting_with_agent(admin_client, agent_name, quorum=1):
    r = admin_client.post("/api/governance/meeting", json={
        "caller": agent_name, "subject": "H5 vote test", "quorum": quorum,
    })
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _pending_motion(admin_client, meeting_id, proposer):
    r = admin_client.post(f"/api/governance/meeting/{meeting_id}/motion", json={
        "proposer": proposer, "motion": "test motion",
    })
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_gv_mcp_vote_mutates_motion(client, admin_client):
    resp = signup_agent(client, name=_uniq("voter"),
                        ip=f"10.99.{uuid.uuid4().int%255}.{uuid.uuid4().int%255}")
    d = resp.json()
    mid = _open_meeting_with_agent(admin_client, d["name"])
    mo = _pending_motion(admin_client, mid, d["name"])

    out = _mcp_vote(d["api_key"], mo, "yea")
    assert out.get("recorded") is True
    assert out.get("motion_status") == "passed"  # sole attendee → auto-resolves

    meeting = admin_client.get(f"/api/governance/meeting/{mid}").json()["meeting"]
    motion = next(m for m in meeting["motions"] if m["id"] == mo)
    assert motion["votes"][d["name"]] == "yea"
    assert motion["status"] == "passed"
    assert any(m["type"] == "vote_cast" and m["voter"] == d["name"]
               for m in meeting["minutes"])


def test_gv_mcp_vote_rejects_non_attendee(client, admin_client):
    a = signup_agent(client, name=_uniq("attendee"),
                     ip=f"10.99.{uuid.uuid4().int%255}.{uuid.uuid4().int%255}").json()
    b = signup_agent(client, name=_uniq("outsider"),
                     ip=f"10.99.{uuid.uuid4().int%255}.{uuid.uuid4().int%255}").json()
    mid = _open_meeting_with_agent(admin_client, a["name"])
    mo = _pending_motion(admin_client, mid, a["name"])

    out = _mcp_vote(b["api_key"], mo, "yea")
    assert out.get("error"), f"foreign agent voted: {out}"

    meeting = admin_client.get(f"/api/governance/meeting/{mid}").json()["meeting"]
    motion = next(m for m in meeting["motions"] if m["id"] == mo)
    assert b["name"] not in motion["votes"]


def test_gv_mcp_vote_unknown_motion_and_bad_key(client):
    resp = signup_agent(client, name=_uniq("v"),
                        ip=f"10.99.{uuid.uuid4().int%255}.{uuid.uuid4().int%255}")
    out = _mcp_vote(resp.json()["api_key"], "mot-nonexistent", "yea")
    assert out.get("error")
    out2 = _mcp_vote("kassa_boguskey", "mot-x", "yea")
    assert out2.get("error")
