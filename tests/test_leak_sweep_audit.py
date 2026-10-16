"""Leak sweep 2026-10-16: the public audit surfaces (/api/audit, the runtime snapshot behind
/api/state and the WS state_snapshot frame, and audit_event broadcasts on /ws + /ws/public)
show audit rows only in their public projection. Before: a linked wallet address
(wallet_linked, withdrawal*) and the sybil-block signup IP were readable by anyone."""
import asyncio
import uuid

from app.deps import state
from tests.conftest import signup_agent

ADDR = "0x" + "ab12cd34" * 5


def _jwt_agent(client):
    d = signup_agent(client, name=f"lsa-{uuid.uuid4().hex[:6]}").json()
    return d, {"Authorization": f"Bearer {d['token']}"}


def test_public_audit_hides_wallet_address_operator_audit_keeps_it(client, admin_client):
    d, jwt = _jwt_agent(client)
    addr = ADDR[:-6] + uuid.uuid4().hex[:6]
    r = client.post("/api/economy/wallets", json={"chain": "base", "address": addr}, headers=jwt)
    assert r.status_code == 201, r.text
    assert addr not in client.get("/api/audit").text
    assert addr not in client.get("/api/state").text
    assert addr not in str(state.current_state_event())
    linked = [e for e in client.get("/api/audit").json()
              if e["action"] == "wallet_linked" and e["detail"].get("agent_id") == d["agent_id"]]
    assert linked and linked[-1]["detail"]["wallet_id"] and "address" not in linked[-1]["detail"]
    # the operator's admin-key audit view is unchanged
    op = admin_client.get("/api/operator/audit?limit=500&type=wallet_linked")
    assert op.status_code == 200 and addr in op.text


def test_audit_event_broadcast_is_projected(monkeypatch):
    sent = []

    class _Hub:
        async def broadcast(self, event):
            sent.append(event)

    monkeypatch.setattr(state, "hub", _Hub())
    monkeypatch.setattr(state, "public_hub", _Hub())
    ev = {"id": 1, "timestamp": "2026-10-16T00:00:00Z", "component": "economy", "action": "withdrawal",
          "detail": {"agent_id": "agent-x", "to": ADDR, "wallet_id": "wal_1", "ip": "203.0.113.5",
                     "nested": {"email": "someone@example.com", "label": "x@signomy.xyz"},
                     "session": "cs_live_abc", "hash": "h"}}
    asyncio.run(state.emit("audit_event", ev))
    assert len(sent) == 2
    for event in sent:
        d = event["payload"]["detail"]
        assert d["agent_id"] == "agent-x" and d["wallet_id"] == "wal_1" and d["hash"] == "h"
        assert "to" not in d and "ip" not in d and "email" not in d["nested"]
        assert d["nested"]["label"] == "x@signomy.xyz"     # platform mailboxes are public labels
        assert d["session"] == "[redacted]"                # Stripe ids are masked by shape
    assert ev["detail"]["to"] == ADDR                      # the stored row is untouched
    # non-audit events pass through as-is
    sent.clear()
    asyncio.run(state.emit("kassa_stake", {"stake_id": "s", "to": "kept"}))
    assert sent[0]["payload"] == {"stake_id": "s", "to": "kept"}


def test_sybil_block_ip_not_public(client):
    ip = f"10.250.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"
    for _ in range(3):
        state.runtime.registry.append({"agent_id": f"agent-{uuid.uuid4().hex[:8]}", "type": "agent",
                                       "status": "active", "signup_ip": ip, "name": uuid.uuid4().hex})
    state.runtime.persist_registry()
    r = client.post("/api/provision/signup", json={"name": f"sy-{uuid.uuid4().hex[:6]}"},
                    headers={"x-forwarded-for": ip})
    assert r.status_code == 429
    assert any(e.action == "sybil_signup_blocked" and e.detail.get("ip") == ip for e in state.audit.recent())
    assert ip not in client.get("/api/audit").text
