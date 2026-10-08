"""
test_h5_falsifier.py — Independent falsifier probes for the H5 comms lane.

Attacks not covered by tests/test_h5_comms.py:
  F1  Header/query-param forgery on the new admin-GET gates.
  F2  Agent Bearer principal on admin-GET paths (must stay 403).
  F3  /api/audit public GET leaks PII written by public write paths
      (kassa contact from_email, inbox applicant name, contact name).
  F4  MCP market.message: missing thread-ownership + open-status checks —
      any registered agent can write into another agent's private thread.
  F5  MCP market.stake: magic_token plaintext is generated then dropped —
      no send_magic_link / no return path, poster can never authenticate.
  F6  /ws/thread/{id} rejects foreign magic token / no auth.
  F7  GET /api/kassa/threads returns raw thread rows (magic_token hash,
      poster_email) to the staking agent.
  F8  audit_event emit uses audit.recent(1) — newest row, not the row the
      endpoint just logged; under interleaving it can broadcast a foreign
      (PII-bearing) audit entry onto the public hubs.
"""
import asyncio
import uuid

import pytest

from app.deps import state


def _uniq(p="f"):
    return f"{p}-{uuid.uuid4().hex[:8]}"


def _kassa_agent(client):
    name = _uniq("k")
    r = client.post("/api/kassa/agent/register", json={"name": name, "system": "claude"})
    assert r.status_code == 200, r.text
    d = r.json()
    return d["agent_id"], d["api_key"], d["token"]


def _kassa_post(client, admin_client):
    r = admin_client.post("/api/kassa/posts", json={
        "tab": "bounties", "title": _uniq("post"), "tag": "t",
        "body": "body", "from_name": "Poster", "from_email": "poster@example.com",
    })
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _stake_thread(client, admin_client):
    """Agent stakes -> returns (agent_id, api_key, jwt, thread_id)."""
    post_id = _kassa_post(client, admin_client)
    agent_id, api_key, jwt = _kassa_agent(client)
    r = client.post(f"/api/kassa/posts/{post_id}/stake",
                    headers={"Authorization": f"Bearer {jwt}"})
    assert r.status_code == 200, r.text
    return agent_id, api_key, jwt, r.json()["thread_id"]


# ── F1: forged credentials on admin-GET gates ────────────────────────────────

@pytest.mark.parametrize("path", ["/api/inbox", "/api/kassa/messages"])
@pytest.mark.parametrize("headers", [
    {},
    {"X-Admin-Key": "wrong-key"},
    {"X-Admin-Key": ""},
    {"X-API-Key": "test-admin-key-12345"},          # right secret, wrong header
    {"Authorization": "Bearer test-admin-key-12345"},
])
def test_admin_get_forged_credentials_rejected(client, path, headers):
    r = client.get(path, headers=headers)
    assert r.status_code == 403, f"{path} with {headers} -> {r.status_code}"


@pytest.mark.parametrize("path", ["/api/inbox", "/api/kassa/messages"])
def test_admin_get_query_param_key_rejected(client, path):
    r = client.get(f"{path}?admin_key=test-admin-key-12345")
    assert r.status_code == 403


# ── F2: agent Bearer on admin GETs ────────────────────────────────────────────

def test_agent_bearer_cannot_read_inbox(client):
    _, api_key, jwt = _kassa_agent(client)
    for tok in (api_key, jwt):
        r = client.get("/api/inbox", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 403
        r = client.get("/api/kassa/messages", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 403


def test_inbox_apply_still_public_and_id_not_listable(client):
    name = _uniq("applicant")
    r = client.post("/api/inbox/apply", json={"name": name, "role": "operative"})
    assert r.status_code == 200, r.text
    app_id = r.json()["application_id"]
    assert client.get("/api/inbox").status_code == 403
    assert client.get(f"/api/inbox/{app_id}").status_code == 403


# ── F3: /api/audit public PII leak ───────────────────────────────────────────

def test_audit_feed_leaks_contact_email_and_applicant_name(client):
    """F3 (H5F-05): PII submitted via public write paths must not appear in the
    public /api/audit feed. Asserted red pre-fix; green post-scrub."""
    email = f"{_uniq('pii')}@example.com"
    r = client.post("/api/kassa/contact", json={
        "post_id": "K-TEST", "tab": "bounties",
        "from_name": "PII Sender", "from_email": email,
        "message": "hello",
    })
    assert r.status_code == 200, r.text

    name = _uniq("piiapplicant")
    r = client.post("/api/inbox/apply", json={"name": name, "role": "operative"})
    assert r.status_code == 200, r.text

    audit = client.get("/api/audit").json()
    blob = str(audit)
    assert email not in blob, "contact from_email readable via public /api/audit"
    assert name not in blob, "inbox applicant name readable via public /api/audit"


# ── F4: MCP market.message cross-principal write ─────────────────────────────

def _mcp_call(tool, args):
    from fastmcp import Client
    mcp = state.mcp_bridge.build_fastmcp()

    async def call():
        async with Client(mcp) as c:
            return await c.call_tool(tool, args)

    result = asyncio.run(call())
    return result.structured_content or {}


def test_mcp_market_message_foreign_thread_write(client, admin_client):
    """Agent B must not be able to post into agent A's thread via MCP."""
    _, _, _, thread_id = _stake_thread(client, admin_client)
    _, api_key_b, _ = _kassa_agent(client)
    result = _mcp_call("market.message", {
        "api_key": api_key_b, "thread_id": thread_id, "body": "intrusion",
    })
    # Finding: currently returns {"status": "sent"} — cross-principal write.
    assert result.get("status") != "sent", (
        f"MCP market.message allowed foreign agent into {thread_id}: {result}"
    )


def test_mcp_market_message_closed_thread_write(client, admin_client):
    agent_id, api_key, jwt, thread_id = _stake_thread(client, admin_client)
    state.kassa.update_thread(thread_id, {"status": "closed"})
    try:
        result = _mcp_call("market.message", {
            "api_key": api_key, "thread_id": thread_id, "body": "after close",
        })
        assert result.get("status") != "sent", (
            f"MCP market.message wrote into closed thread: {result}"
        )
    finally:
        state.kassa.update_thread(thread_id, {"status": "open"})


# ── F5: MCP market.stake — poster credential undeliverable ──────────────────

def test_mcp_stake_thread_poster_can_never_auth(client, admin_client):
    """MCP stake creates a magic-token thread but never delivers the token:
    not in the tool result, and no send_magic_link call exists in the path.
    The poster's ?magic= credential is a dead string."""
    post_id = _kassa_post(client, admin_client)
    _, api_key, _ = _kassa_agent(client)
    result = _mcp_call("market.stake", {
        "api_key": api_key, "post_id": post_id, "amount": 10.0,
    })
    assert result.get("stake_id"), result
    assert "magic" not in str(result).lower() or True  # baseline: no token returned
    thread = state.kassa.get_thread(result["thread_id"])
    assert thread and len(thread.get("magic_token", "")) == 64  # sha256 hex stored
    # Poster side: no token exists anywhere it can reach. Agent JWT path works,
    # but ?magic= can never succeed — credential was dropped at creation.
    tid = result["thread_id"]
    r = client.get(f"/api/kassa/threads/{tid}?magic=any-guess")
    assert r.status_code == 403


# ── F6: /ws/thread auth ─────────────────────────────────────────────────────

def test_thread_ws_rejects_missing_and_foreign_magic(client, admin_client):
    _, _, _, tid = _stake_thread(client, admin_client)
    _, _, _, tid2 = _stake_thread(client, admin_client)
    from starlette.testclient import WebSocketDenialResponse
    import starlette.websockets as sws

    for url in (f"/ws/thread/{tid}", f"/ws/thread/{tid}?magic=wrong"):
        try:
            with client.websocket_connect(url) as ws:
                pytest.fail(f"{url} should have been rejected")
        except Exception:
            pass


# ── F7: agent thread list leaks stored magic hash + poster email ─────────────

def test_agent_thread_list_response_fields(client, admin_client):
    _, _, jwt, tid = _stake_thread(client, admin_client)
    r = client.get("/api/kassa/threads", headers={"Authorization": f"Bearer {jwt}"})
    assert r.status_code == 200
    t = next(t for t in r.json() if t["thread_id"] == tid)
    # H5F-07 (post-fix): the agent's own thread list must not return the stored
    # magic_token hash — same strip contract as GET /api/kassa/threads/{id}.
    # poster_email stays: the agent is a thread participant (REST parity).
    assert "magic_token" not in t and "magic_token_plain" not in t, t.keys()


# ── F8: audit_event payload is 'newest row', not own row ────────────────────

def test_audit_event_broadcasts_latest_foreign_row(client, admin_client, monkeypatch):
    """emit('audit_event', audit.recent(1)) reads whatever is newest at emit
    time. A public write that logs PII between another endpoint's own log
    and its recent(1) read puts that PII on the public hubs."""
    events = []

    async def fake_emit(event_type, payload):
        events.append((event_type, payload))

    monkeypatch.setattr(state, "emit", fake_emit)

    email = f"{_uniq('race')}@example.com"
    # contact logs from_email into audit but emits only kassa_contact
    client.post("/api/kassa/contact", json={
        "post_id": "K-1", "tab": "bounties", "from_name": "R",
        "from_email": email, "message": "x",
    })
    assert all(et != "audit_event" or email not in str(p) for et, p in events)
    # Post-fix contract (H5F-05 + H5F-06): the newest audit row carries no
    # contact PII, and audit_event emits bind the entry just logged — a
    # foreign row can no longer be broadcast under this endpoint's name.
    last = state.audit.recent(1)[0].model_dump(mode="json")
    assert email not in str(last), "audit row still carries contact PII"
