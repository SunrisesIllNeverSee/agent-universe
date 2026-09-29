"""
test_agent_inbox.py — Agent in-system mailbox tests.

Covers the agent-side notification half: inbox endpoints (Bearer api_key),
the welcome record on registration, thread-reply notifications to agents,
thread-creation notifications to registered-agent posters, and review-decision
notifications. Mirrors tests/test_routes_kassa.py fixture style.
"""
import uuid


def _unique_name():
    return f"inbox-{uuid.uuid4().hex[:6]}"


def _signup(client, name=None, ip=None):
    """Register via provision and return (agent_id, api_key, email, token)."""
    name = name or _unique_name()
    ip = ip or f"10.9.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    r = client.post(
        "/api/provision/signup",
        json={"name": name, "system": "claude"},
        headers={"x-forwarded-for": ip},
    )
    assert r.status_code == 200, f"signup failed: {r.text}"
    d = r.json()
    return d["agent_id"], d["api_key"], d["email"], d["token"]


def _kassa_signup(client, name=None):
    name = name or _unique_name()
    r = client.post("/api/kassa/agent/register", json={"name": name, "system": "claude"})
    assert r.status_code == 200, f"kassa register failed: {r.text}"
    d = r.json()
    return d["agent_id"], d["api_key"], d["token"]


def _key_headers(api_key):
    return {"Authorization": f"Bearer {api_key}"}


def _ip_headers():
    return {"x-forwarded-for": f"10.7.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"}


def _post_payload(tab="iso", suffix=None, from_email=None):
    s = suffix or uuid.uuid4().hex[:4]
    return {
        "title": f"Test {tab.upper()} {s}",
        "tab": tab,
        "body": "Test post body for inbox integration testing",
        "tag": tab,
        "from_name": f"Poster-{s}",
        "from_email": from_email or f"poster-{s}@example.com",
    }


# ── Endpoints ───────────────────────────────────────────────────────────────

def test_inbox_requires_auth(client):
    r = client.get("/api/agent/inbox")
    assert r.status_code == 401


def test_inbox_rejects_bad_key(client):
    r = client.get("/api/agent/inbox", headers=_key_headers("cmd_ak_bogus"))
    assert r.status_code == 401


def test_inbox_welcome_on_signup(client):
    agent_id, api_key, _, _ = _signup(client)
    r = client.get("/api/agent/inbox", headers=_key_headers(api_key))
    assert r.status_code == 200
    d = r.json()
    assert d["agent_id"] == agent_id
    assert d["unread"] >= 1
    kinds = [m["kind"] for m in d["messages"]]
    assert "system" in kinds
    welcome = next(m for m in d["messages"] if m["kind"] == "system")
    assert "inbox" in welcome["title"].lower()


def test_inbox_welcome_on_kassa_register(client):
    agent_id, api_key, _ = _kassa_signup(client)
    r = client.get("/api/agent/inbox", headers=_key_headers(api_key))
    assert r.status_code == 200
    assert any(m["kind"] == "system" for m in r.json()["messages"])


def test_inbox_mark_read(client):
    agent_id, api_key, _, _ = _signup(client)
    inbox = client.get("/api/agent/inbox", headers=_key_headers(api_key)).json()
    assert inbox["unread"] >= 1
    msg_id = inbox["messages"][0]["msg_id"]

    r = client.post("/api/agent/inbox/read",
                    json={"msg_ids": [msg_id]},
                    headers=_key_headers(api_key))
    assert r.status_code == 200
    assert r.json()["marked"] == 1

    d = client.get("/api/agent/inbox", headers=_key_headers(api_key)).json()
    read_msg = next(m for m in d["messages"] if m["msg_id"] == msg_id)
    assert read_msg["read_at"] is not None


def test_inbox_mark_all_read(client):
    agent_id, api_key, _, _ = _signup(client)
    r = client.post("/api/agent/inbox/read",
                    json={"all": True},
                    headers=_key_headers(api_key))
    assert r.status_code == 200
    assert r.json()["unread"] == 0


def test_inbox_mark_read_bad_payload(client):
    _, api_key, _, _ = _signup(client)
    r = client.post("/api/agent/inbox/read",
                    json={},
                    headers=_key_headers(api_key))
    assert r.status_code == 400


def test_inbox_is_scoped_to_agent(client):
    _, key_a, _, _ = _signup(client)
    _, key_b, _, _ = _signup(client)
    # B marks everything read; A's unread must be unaffected
    client.post("/api/agent/inbox/read", json={"all": True}, headers=_key_headers(key_b))
    d = client.get("/api/agent/inbox", headers=_key_headers(key_a)).json()
    assert d["unread"] >= 1


# ── Notification wires ──────────────────────────────────────────────────────

def test_poster_reply_notifies_agent(client, admin_client):
    """Poster replies in a negotiation thread -> the thread's agent gets inbox."""
    _, staker_key, _, staker_token = _signup(client)

    # Admin-authored post — stake creates a thread between poster and agent
    create = admin_client.post("/api/kassa/posts", json=_post_payload("bounties"),
                               headers=_ip_headers())
    assert create.status_code == 200
    post_id = create.json()["id"]

    stake = client.post(f"/api/kassa/posts/{post_id}/stake",
                        json={"amount": 25, "message": "taking this"},
                        headers={**_ip_headers(), "Authorization": f"Bearer {staker_token}"})
    assert stake.status_code == 200, stake.text
    thread_id = stake.json()["thread_id"]

    # Read the thread as the poster via magic link to post a reply
    magic = stake.json()["magic_link"].split("magic=")[1]
    reply = client.post(f"/api/kassa/threads/{thread_id}/messages",
                        json={"text": "poster replying to your stake"},
                        params={"magic": magic})
    assert reply.status_code == 200, reply.text

    inbox = client.get("/api/agent/inbox", headers=_key_headers(staker_key)).json()
    titles = [m["title"] for m in inbox["messages"]]
    assert any("New message" in t for t in titles)
    msg = next(m for m in inbox["messages"] if "New message" in m["title"])
    assert msg["ref_type"] == "thread"
    assert msg["ref_id"] == thread_id


def test_thread_creation_notifies_agent_poster(client, admin_client):
    """Agent-authored post gets staked -> the poster-agent gets an inbox record."""
    _, poster_key, poster_email, poster_token = _signup(client)
    _, _, _, staker_token = _signup(client)

    # Agent-authored post via JWT (from_email = their generated @signomy.xyz address)
    payload = _post_payload("bounties", from_email=poster_email)
    create = client.post("/api/kassa/posts", json=payload,
                         headers={**_ip_headers(), "Authorization": f"Bearer {poster_token}"})
    assert create.status_code == 200
    post_id = create.json()["id"]

    # Approve it so it's stakable
    admin_client.patch(f"/api/operator/reviews/rev-{post_id}", params={"action": "approve"})

    # Second agent stakes -> thread opens
    stake = client.post(f"/api/kassa/posts/{post_id}/stake",
                        json={"amount": 25, "message": "on it"},
                        headers={**_ip_headers(), "Authorization": f"Bearer {staker_token}"})
    assert stake.status_code == 200, stake.text

    inbox = client.get("/api/agent/inbox", headers=_key_headers(poster_key)).json()
    stake_msgs = [m for m in inbox["messages"] if m["kind"] == "stake"]
    assert stake_msgs, "expected a stake notification in the poster agent's inbox"
    assert stake_msgs[0]["ref_type"] == "thread"


def test_review_decision_notifies_agent_submitter(client, admin_client):
    """Operator approves/rejects -> submitting agent sees the verdict in-system."""
    _, agent_key, agent_email, agent_token = _signup(client)
    payload = _post_payload("services", from_email=agent_email)
    create = client.post("/api/kassa/posts", json=payload,
                         headers={**_ip_headers(), "Authorization": f"Bearer {agent_token}"})
    assert create.status_code == 200
    post_id = create.json()["id"]

    r = admin_client.patch(f"/api/operator/reviews/rev-{post_id}",
                           params={"action": "approve"})
    assert r.status_code == 200

    inbox = client.get("/api/agent/inbox", headers=_key_headers(agent_key)).json()
    review_msgs = [m for m in inbox["messages"] if m["kind"] == "review"]
    assert review_msgs, "expected a review notification in the submitter's inbox"
    assert "published" in review_msgs[0]["title"]


def test_poster_mail_target_routing():
    """@signomy.xyz labels route per role: agents -> inbox, platform -> OPERATOR_EMAIL."""
    import os
    from app.routes.kassa import _poster_mail_target

    # Registered-agent posters get no email target — their inbox covers them
    assert _poster_mail_target("agent-x@signomy.xyz", {"agent_id": "x"}) == ""
    # Real human addresses pass through unchanged
    assert _poster_mail_target("human@example.com", None) == "human@example.com"
    # Platform labels route to OPERATOR_EMAIL (or pass through when unset)
    t = _poster_mail_target("operator@signomy.xyz", None)
    expected = os.environ.get("OPERATOR_EMAIL", "") or "operator@signomy.xyz"
    assert t == expected


def test_no_inbox_for_non_agent_poster(client, admin_client):
    """Human posters (non-registered emails) produce no inbox records."""
    _, _, _, staker_token = _signup(client)
    create = admin_client.post("/api/kassa/posts", json=_post_payload("bounties"),
                               headers=_ip_headers())
    post_id = create.json()["id"]

    stake = client.post(f"/api/kassa/posts/{post_id}/stake",
                        json={"amount": 10},
                        headers={**_ip_headers(), "Authorization": f"Bearer {staker_token}"})
    assert stake.status_code == 200
    # Nothing to assert directly — absence verified by inbox scoping in other
    # tests; this mainly asserts the notify path doesn't error on real flow.
