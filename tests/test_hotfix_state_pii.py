"""Hotfix 2026-10-16: the unauthenticated runtime snapshot must not leak private registry fields.

Production /api/state (and the public state_snapshot websocket frame) returned every
registry entry verbatim: email, key_hash, key_prefix, signup_ip, operator_contact, ...
"""

PRIVATE = ("email", "key_hash", "key_prefix", "signup_ip", "operator_contact", "last_login", "rate_limit")


def _seed_private_entry():
    from app.deps import state
    entry = {
        "agent_id": "pii-probe", "name": "PII Probe", "type": "agent", "status": "active",
        "email": "probe@example.com", "key_hash": "deadbeef", "key_prefix": "cmd_xxxx",
        "signup_ip": "203.0.113.7", "operator_contact": "op@example.com",
        "last_login": "2026-10-16T00:00:00Z", "rate_limit": 60,
    }
    state.runtime.registry.append(entry)
    return state, entry


def test_api_state_registry_has_no_private_fields(client):
    state, entry = _seed_private_entry()
    try:
        r = client.get("/api/state")
        assert r.status_code == 200
        reg = r.json()["registry"]
        probe = [a for a in reg if a.get("agent_id") == "pii-probe"]
        assert probe and probe[0]["name"] == "PII Probe" and probe[0]["status"] == "active"
        for a in reg:
            for k in PRIVATE:
                assert k not in a, f"/api/state leaks {k}"
        body = r.text
        for v in ("probe@example.com", "deadbeef", "203.0.113.7", "op@example.com"):
            assert v not in body
    finally:
        state.runtime.registry.remove(entry)


def test_public_ws_snapshot_frame_has_no_private_fields():
    state, entry = _seed_private_entry()
    try:
        snap = state.runtime.snapshot().model_dump(mode="json")
        for a in snap["registry"]:
            for k in PRIVATE:
                assert k not in a
        # the private registry itself is untouched (auth/login still need it)
        assert entry["email"] == "probe@example.com" and entry["key_hash"] == "deadbeef"
    finally:
        state.runtime.registry.remove(entry)
