"""Decision 10: newly issued agent keys carry 256-bit entropy.

Existing (64-bit legacy) keys are verified by hash, so they keep working;
rotation issues a long key and still revokes the superseded one.
"""
import re
import uuid
from pathlib import Path

from app.deps import state
from app.routes.provision import _hash_key
from tests.conftest import signup_agent

LONG_KEY = re.compile(r"^cmd_ak_[0-9a-f]{64}$")


def _ip():
    return f"10.9.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"


def _login(client, agent_id, key):
    return client.post("/api/provision/login", json={"agent_id": agent_id, "api_key": key},
                       headers={"x-forwarded-for": _ip()})


def test_signup_issues_256_bit_key(client):
    d = signup_agent(client, ip=_ip()).json()
    assert LONG_KEY.match(d["api_key"]), d["api_key"]
    assert _login(client, d["agent_id"], d["api_key"]).status_code == 200


def test_rotation_issues_256_bit_key_and_revokes_old(client, admin_client):
    d = signup_agent(client, ip=_ip()).json()
    r = admin_client.post("/api/provision/key", json={"agent_id": d["agent_id"], "requested_by": "test"})
    assert r.status_code == 200
    new_key = r.json()["key"]
    assert LONG_KEY.match(new_key)
    assert _login(client, d["agent_id"], d["api_key"]).status_code != 200
    assert _login(client, d["agent_id"], new_key).status_code == 200


def test_legacy_64_bit_key_still_authenticates(client):
    d = signup_agent(client, ip=_ip()).json()
    legacy = f"cmd_ak_{uuid.uuid4().hex[:16]}"
    agent = next(r for r in state.runtime.registry if r["agent_id"] == d["agent_id"])
    agent["key_hash"] = _hash_key(legacy)
    agent["key_prefix"] = legacy[:12] + "***"
    assert _login(client, d["agent_id"], legacy).status_code == 200
    r = client.get("/api/agent/inbox", headers={"Authorization": f"Bearer {legacy}"})
    assert r.status_code != 403


def test_no_short_key_issuance_left_in_source():
    root = Path(__file__).resolve().parents[1] / "app"
    hits = [str(p) for p in root.rglob("*.py") if 'cmd_ak_{secrets.token_hex(8)}' in p.read_text()]
    assert hits == []
