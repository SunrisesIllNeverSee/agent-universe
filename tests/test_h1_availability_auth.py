"""H1 — availability mutations require a live credential for the exact agent_id.

Covers POST /api/availability/{agent_id} and /toggle. Runs against the
session-scoped app whose root is a tmp dir (never real data/). Every rejected
call must leave persisted availability state untouched.
"""
import json
import uuid

import pytest

from app.deps import state
from tests.conftest import signup_agent

BODY = {"available_now": True, "domains": ["code"], "blocks": [], "response_time_hours": 2}
HOSTILE = {"Origin": "http://127.0.0.1:8300", "Referer": "http://127.0.0.1:8300/shell"}


def _agent(client):
    ip = f"10.9.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"av-{uuid.uuid4().hex[:6]}", ip=ip).json()
    return d["agent_id"], d["api_key"]


def _persisted(agent_id):
    p = state.root / "data" / "availability.json"
    if not p.exists():
        return None
    return json.loads(p.read_text()).get("agents", {}).get(agent_id)


def _bearer(key):
    return {"Authorization": f"Bearer {key}"}


def _set(client, aid, headers=None):
    return client.post(f"/api/availability/{aid}", json=BODY, headers=headers or {})


def _toggle(client, aid, headers=None):
    return client.post(f"/api/availability/{aid}/toggle", headers=headers or {})


CALLS = [pytest.param(_set, id="set"), pytest.param(_toggle, id="toggle")]


@pytest.mark.parametrize("call", CALLS)
def test_anonymous_rejected(client, call):
    aid = f"victim-{uuid.uuid4().hex[:6]}"
    r = call(client, aid)
    assert r.status_code in (401, 403)
    assert _persisted(aid) is None


@pytest.mark.parametrize("call", CALLS)
def test_garbage_token_rejected(client, call):
    aid, _ = _agent(client)
    r = call(client, aid, _bearer("not-a-real-key-" + uuid.uuid4().hex))
    assert r.status_code in (401, 403)
    assert _persisted(aid) is None


@pytest.mark.parametrize("call", CALLS)
def test_other_agents_key_rejected(client, call):
    victim, _ = _agent(client)
    _, attacker_key = _agent(client)
    r = call(client, victim, _bearer(attacker_key))
    assert r.status_code == 403
    assert _persisted(victim) is None


@pytest.mark.parametrize("call", CALLS)
def test_revoked_credential_rejected(client, admin_client, call):
    aid, key = _agent(client)
    assert admin_client.post("/api/provision/revoke", json={"agent_id": aid}).status_code == 200
    r = call(client, aid, _bearer(key))
    assert r.status_code in (401, 403)
    assert _persisted(aid) is None


@pytest.mark.parametrize("call", CALLS)
def test_spoofed_shell_origin_never_confers_authority(client, call):
    aid, key = _agent(client)
    r = call(client, aid, HOSTILE)
    assert r.status_code in (401, 403)
    assert _persisted(aid) is None
    # Same spoofed headers with a garbage credential.
    r = call(client, aid, {**HOSTILE, **_bearer("garbage")})
    assert r.status_code in (401, 403)
    assert _persisted(aid) is None


def test_name_alias_does_not_authorize_set(client):
    """Availability is keyed by agent_id; a name/handle path must not pass."""
    aid, key = _agent(client)
    name = next(a["name"] for a in state.runtime.registry if a["agent_id"] == aid)
    r = _set(client, name, _bearer(key))
    assert r.status_code == 403
    assert _persisted(name) is None


def test_own_agent_set_and_toggle_succeed(client):
    aid, key = _agent(client)
    r = _set(client, aid, {**HOSTILE, **_bearer(key)})
    assert r.status_code == 200 and r.json()["ok"] is True
    assert _persisted(aid)["available_now"] is True
    r = _toggle(client, aid, _bearer(key))
    assert r.status_code == 200 and r.json()["available_now"] is False
    assert _persisted(aid)["available_now"] is False


def test_operator_admin_key_still_works(admin_client):
    aid = f"op-{uuid.uuid4().hex[:6]}"
    assert admin_client.post(f"/api/availability/{aid}", json=BODY).status_code == 200
    assert _persisted(aid)["available_now"] is True


def test_public_gets_still_open(client):
    assert client.get("/api/availability").status_code == 200
    assert client.get("/api/availability/stats").status_code == 200
    assert client.get(f"/api/availability/nobody-{uuid.uuid4().hex[:6]}").status_code == 200
