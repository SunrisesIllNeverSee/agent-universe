"""H1 — revoked-key deny-list enforcement (1G: in-path before acceptance).

Covers: revoke endpoint, deny-list consulted by bearer auth on REST +
per-agent guard + MCP, rotation/decommission deny writes, restart
persistence, suspension staying distinct, and no plaintext key storage.
"""
import asyncio
import json
import uuid

from tests.conftest import signup_agent

ADMIN = {"X-Admin-Key": "test-admin-key"}


def _signup(client, tag):
    ip = f"10.7.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    return signup_agent(client, name=_uniq(tag), ip=ip).json()


def _uniq(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:6]}"


def _slot_target(client):
    """A slot-fill call is a simple in-path bearer gate to probe."""
    return "/api/slots/fill"


def test_h1_revoked_key_rejected_everywhere(client, admin_client):
    d = _signup(client, "rev")
    aid, key, name = d["agent_id"], d["api_key"], d["name"]

    # Sanity: key works before revocation (bearer path).
    r = client.get("/api/agent/inbox", headers={"Authorization": f"Bearer {key}"})
    assert r.status_code == 200

    # Admin revokes.
    rv = admin_client.post("/api/provision/revoke", json={"agent_id": aid})
    assert rv.status_code == 200 and rv.json()["revoked"] is True

    # Same key now fails on every acceptance path.
    assert client.get("/api/agent/inbox",
                      headers={"Authorization": f"Bearer {key}"}).status_code == 401
    # Login exchange: revoked key cannot mint a JWT.
    lg = client.post("/api/provision/login", json={"agent_id": aid, "api_key": key})
    assert lg.status_code == 401
    # MCP path.
    from app.deps import state
    from fastmcp import Client
    mcp = state.mcp_bridge.build_fastmcp()

    async def prof():
        async with Client(mcp) as c:
            try:
                r = await c.call_tool("agent.profile", {"api_key": key})
                return r.structured_content or {}
            except Exception as e:  # ToolError = rejection surfaced
                return {"error": str(e)}
    out = asyncio.run(prof())
    assert out.get("error"), f"revoked key accepted on MCP: {out}"


def test_h1_rotation_denies_superseded_key(client, admin_client):
    d = _signup(client, "rot")
    aid, old_key = d["agent_id"], d["api_key"]
    r = admin_client.post("/api/provision/key", json={
        "agent_id": aid, "requested_by": "test",
    })
    assert r.status_code == 200
    new_key = r.json()["key"]
    assert client.get("/api/agent/inbox",
                      headers={"Authorization": f"Bearer {old_key}"}).status_code == 401
    assert client.get("/api/agent/inbox",
                      headers={"Authorization": f"Bearer {new_key}"}).status_code == 200


def test_h1_decommission_denies_key_and_record(client, admin_client):
    d = _signup(client, "dec")
    aid, key = d["agent_id"], d["api_key"]
    r = admin_client.delete(f"/api/provision/decommission/{aid}")
    assert r.status_code == 200
    assert client.get("/api/agent/inbox",
                      headers={"Authorization": f"Bearer {key}"}).status_code == 401


def test_h1_suspend_distinct_from_revoke(client, admin_client):
    d = _signup(client, "sus")
    aid, key = d["agent_id"], d["api_key"]
    assert admin_client.post("/api/provision/suspend",
                             json={"agent_id": aid}).status_code == 200
    # Suspended principal's key fails on status check — but via status, and
    # the credential digest is NOT in the deny-list (suspension ≠ revoke).
    from app.deps import state
    import hashlib
    assert hashlib.sha256(key.encode()).hexdigest() not in state.runtime.revoked_keys
    # Suspension fails on the status check (403), revocation on the
    # credential check (401) — the distinction is the mechanism.
    assert client.get("/api/agent/inbox",
                      headers={"Authorization": f"Bearer {key}"}).status_code == 403


def test_h1_unrelated_principal_unaffected(client, admin_client):
    a = _signup(client, "keep")
    b = _signup(client, "drop")
    admin_client.post("/api/provision/revoke", json={"agent_id": b["agent_id"]})
    assert client.get("/api/agent/inbox",
                      headers={"Authorization": f"Bearer {a['api_key']}"}).status_code == 200


def test_h1_revoke_requires_admin_and_persists(client, admin_client):
    d = _signup(client, "persist")
    aid = d["agent_id"]
    # Non-admin cannot revoke.
    r = client.post("/api/provision/revoke", json={"agent_id": aid})
    assert r.status_code in (401, 403)
    assert admin_client.post("/api/provision/revoke",
                             json={"agent_id": aid}).status_code == 200

    # Deny-list is durable on disk (restart persistence is the file —
    # a fresh RuntimeState over the same data dir must re-load it).
    from app.deps import state
    path = state.runtime.data_dir / "revoked_keys.json"
    assert path.exists()
    digests = json.loads(path.read_text())
    import hashlib
    assert hashlib.sha256(d["api_key"].encode()).hexdigest() in digests
    # No plaintext key material ever persisted.
    assert d["api_key"] not in path.read_text()


def test_h1_revoke_twice_and_unknown_client_rejects(client, admin_client):
    aid = _signup(client, "n2")["agent_id"]
    admin_client.post("/api/provision/revoke", json={"agent_id": aid})
    r2 = admin_client.post("/api/provision/revoke", json={"agent_id": aid})
    assert r2.status_code == 409  # no credential left to revoke
    assert admin_client.post("/api/provision/revoke",
                             json={"agent_id": "agent-does-not-exist"}
                             ).status_code == 404


# ── Falsifier-corrected findings (H1F-01..05) ──────────────────────────────

def _jwt_for(client, aid, key):
    r = client.post("/api/provision/login", json={"agent_id": aid, "api_key": key})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_h1f01_revoked_key_kills_outstanding_jwt(client, admin_client):
    """H1F-01: JWT minted before revocation must die with the credential."""
    d = _signup(client, "jwtdead")
    aid, key = d["agent_id"], d["api_key"]
    jwt = _jwt_for(client, aid, key)
    # JWT works pre-revocation on a status-checked surface.
    assert client.get("/api/kassa/agent/me",
                      headers={"Authorization": f"Bearer {jwt}"}).status_code == 200

    assert admin_client.post("/api/provision/revoke",
                             json={"agent_id": aid}).status_code == 200
    for path in ("/api/kassa/agent/me",):
        r = client.get(path, headers={"Authorization": f"Bearer {jwt}"})
        assert r.status_code in (401, 403), f"{path} accepted dead JWT: {r.status_code}"
    # JWT-only post surface.
    r = client.post("/api/kassa/posts",
                    headers={"Authorization": f"Bearer {jwt}"},
                    json={"tab": "general", "title": "t", "body": "b"})
    assert r.status_code in (401, 403), r.status_code


def test_h1f02_decommission_kills_jwt_on_money_paths(client, admin_client):
    """H1F-02: decommissioned principal's JWT must not move money."""
    d = _signup(client, "moneydead")
    aid, key = d["agent_id"], d["api_key"]
    jwt = _jwt_for(client, aid, key)
    assert admin_client.delete(f"/api/provision/decommission/{aid}").status_code == 200
    r = client.post("/api/economy/pay",
                    headers={"Authorization": f"Bearer {jwt}"},
                    json={"amount": 1})
    assert r.status_code in (401, 403), r.status_code


def test_h1f03_rearmed_digest_denied_everywhere(client, admin_client):
    """H1F-03: a re-registered record carrying a revoked digest re-auths nowhere."""
    from app.deps import state
    import hashlib
    a = _signup(client, "rearm")
    old_hash = hashlib.sha256(a["api_key"].encode()).hexdigest()
    admin_client.post("/api/provision/revoke", json={"agent_id": a["agent_id"]})
    # Simulate a duplicate/restored registry record re-arming the digest.
    state.runtime.registry.append({
        "agent_id": "agent-ghost", "name": "ghost", "status": "active",
        "key_hash": old_hash, "key_prefix": a["api_key"][:12] + "***",
        "governance": "open", "role": "agent",
    })
    state.runtime.persist_registry()
    key = a["api_key"]
    assert client.get("/api/agent/inbox",
                      headers={"Authorization": f"Bearer {key}"}).status_code == 401
    r = client.post("/api/kassa/agent/login",
                    json={"agent_id": "agent-ghost", "api_key": key})
    assert r.status_code == 401
    r2 = client.post("/api/provision/login",
                     json={"agent_id": "agent-ghost", "api_key": key})
    assert r2.status_code == 401


def test_h1f04_malformed_denylist_fails_loud(client):
    """H1F-04: malformed revoked_keys.json must not silently yield empty set."""
    import pytest
    from app.runtime import RuntimeState
    from pathlib import Path
    import tempfile, json as J
    data_dir = Path(tempfile.mkdtemp())
    (data_dir / "revoked_keys.json").write_text(J.dumps({"not": "a-list"}))
    with pytest.raises(ValueError):
        RuntimeState._load_revoked_keys(data_dir / "revoked_keys.json")


def test_h1f05_reload_propagates_revocation(client, admin_client):
    """H1F-05: reload_registry refreshes the deny-list (multi-worker parity)."""
    from app.deps import state
    d = _signup(client, "reload")
    import hashlib, json as J
    digest = hashlib.sha256(d["api_key"].encode()).hexdigest()
    # Another "worker" writes the deny-list directly.
    path = state.runtime.data_dir / "revoked_keys.json"
    current = J.loads(path.read_text()) if path.exists() else []
    current.append(digest)
    path.write_text(J.dumps(current))
    state.runtime.revoked_keys.discard(digest)  # simulate stale in-memory
    state.runtime.reload_registry()
    assert digest in state.runtime.revoked_keys
