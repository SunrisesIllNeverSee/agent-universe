"""D-B — mission principal binding.

A mission records the authentic creating agent (server-derived from the live
Bearer API key). end / update / slot-create on an existing mission require that
same agent or the admin key; other agents get a uniform 404 (existence oracle closed) before any write. Missions
with no recorded owner fail closed for agents. Runs on the session tmp root
(see conftest) — never real data/.
"""
import json
import uuid

import pytest

from app.deps import state
from tests.conftest import signup_agent

SLOTS = {
    "formation_id": "pb", "posture": "SCOUT", "label": "PB",
    "positions": [{"row": 0, "col": 0}], "roles": ["primary"], "revenue_splits": [100],
}
ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


def _agent(client):
    ip = f"10.7.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"pb-{uuid.uuid4().hex[:6]}", ip=ip).json()
    return d["agent_id"], {"Authorization": f"Bearer {d['api_key']}"}


def _mission(client, headers, **body):
    r = client.post("/api/missions", json={"label": "m", **body}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _lines(name):
    p = state.root / "data" / name
    return len(p.read_text().splitlines()) if p.exists() else 0


def _snap():
    from app.routes import missions as m
    return (json.dumps(m._load_missions(), sort_keys=True),
            json.dumps(m._load_slots(), sort_keys=True),
            _lines("audit.jsonl"), _lines("seeds.jsonl"))


def _legacy(mission_id):
    """Inject an ownerless pre-binding record straight into the tmp store."""
    from app.routes import missions as m
    ms = m._load_missions()
    ms.append({"id": mission_id, "mission_id": mission_id, "label": "legacy",
               "status": "active", "ended_at": None})
    m._save_missions(ms)


VERBS = {
    "end": lambda c, mid, h: c.post(f"/api/missions/{mid}/end", json={}, headers=h),
    "update": lambda c, mid, h: c.post(f"/api/missions/{mid}/update", json={"posture": "HOLD"}, headers=h),
    "slots": lambda c, mid, h: c.post("/api/slots/create", json={**SLOTS, "mission_id": mid}, headers=h),
}
verbs = pytest.mark.parametrize("verb", list(VERBS))


# ── creation ────────────────────────────────────────────────────────────────

def test_agent_creation_records_authentic_owner(client):
    aid, h = _agent(client)
    m = _mission(client, h)
    assert m["owner_agent_id"] == aid and m["created_by"] == "agent"


def test_body_supplied_owner_is_ignored(client):
    aid, h = _agent(client)
    other, _ = _agent(client)
    m = _mission(client, h, owner_agent_id=other, agent_id=other, created_by="operator")
    assert m["owner_agent_id"] == aid and m["created_by"] == "agent"


def test_admin_creation_records_no_agent_principal(admin_client):
    m = admin_client.post("/api/missions", json={"label": "op", "owner_agent_id": "agent-forged"}).json()
    assert m["owner_agent_id"] is None and m["created_by"] == "operator"


def test_slots_create_minted_mission_is_owned(client):
    aid, h = _agent(client)
    r = client.post("/api/slots/create", json=SLOTS, headers=h)
    assert r.status_code == 200
    mid = r.json()["mission_id"]
    got = client.get(f"/api/missions/{mid}").json()["mission"]
    assert got["owner_agent_id"] == aid


def test_bounty_mission_is_owned_by_poster(client):
    aid, h = _agent(client)
    r = client.post("/api/slots/bounty", json={"agent_id": aid, "label": "b"}, headers=h)
    assert r.status_code == 200, r.text
    got = client.get(f"/api/missions/{r.json()['mission_id']}").json()["mission"]
    assert got["owner_agent_id"] == aid


def test_get_exposes_no_key_material(client):
    _, h = _agent(client)
    m = _mission(client, h)
    blob = json.dumps(client.get(f"/api/missions/{m['id']}").json()) + json.dumps(client.get("/api/missions").json())
    token = h["Authorization"].split()[1]
    assert token not in blob and "key_hash" not in blob and "api_key" not in blob


# ── per-verb authorization ──────────────────────────────────────────────────

@verbs
def test_anonymous_denied_no_write(client, verb):
    _, h = _agent(client)
    mid = _mission(client, h)["id"]
    before = _snap()
    assert VERBS[verb](client, mid, {}).status_code in (401, 403)
    assert _snap() == before


@verbs
def test_forged_key_denied_no_write(client, verb):
    _, h = _agent(client)
    mid = _mission(client, h)["id"]
    before = _snap()
    r = VERBS[verb](client, mid, {"Authorization": "Bearer forged-" + uuid.uuid4().hex})
    assert r.status_code in (401, 403)
    assert _snap() == before


@verbs
def test_revoked_key_denied_no_write(client, admin_client, verb):
    aid, h = _agent(client)
    mid = _mission(client, h)["id"]
    assert admin_client.post("/api/provision/revoke", json={"agent_id": aid}).status_code == 200
    before = _snap()
    assert VERBS[verb](client, mid, h).status_code in (401, 403)
    assert _snap() == before


@verbs
def test_other_agent_denied_no_write(client, verb):
    _, owner_h = _agent(client)
    _, other_h = _agent(client)
    mid = _mission(client, owner_h)["id"]
    before = _snap()
    assert VERBS[verb](client, mid, other_h).status_code == 404  # oracle: was 403
    assert _snap() == before


@verbs
def test_owner_agent_allowed(client, verb):
    _, h = _agent(client)
    mid = _mission(client, h)["id"]
    assert VERBS[verb](client, mid, h).status_code == 200


@verbs
def test_admin_allowed_on_agent_mission(client, verb):
    _, h = _agent(client)
    mid = _mission(client, h)["id"]
    assert VERBS[verb](client, mid, ADMIN).status_code == 200


@verbs
def test_legacy_ownerless_denied_for_agent_allowed_for_admin(client, verb):
    mid = f"mission-legacy-{uuid.uuid4().hex[:6]}"
    _legacy(mid)
    _, h = _agent(client)
    before = _snap()
    assert VERBS[verb](client, mid, h).status_code == 404  # oracle: was 403
    assert _snap() == before
    assert VERBS[verb](client, mid, ADMIN).status_code == 200


@verbs
def test_operator_created_mission_denied_for_agents(client, admin_client, verb):
    mid = admin_client.post("/api/missions", json={"label": "op"}).json()["id"]
    _, h = _agent(client)
    before = _snap()
    assert VERBS[verb](client, mid, h).status_code == 404  # oracle: was 403
    assert _snap() == before


@verbs
def test_jwt_does_not_authorize(client, verb):
    """Existing guards accept only API keys; an agent JWT must not mutate."""
    d = signup_agent(client, name=f"pbj-{uuid.uuid4().hex[:6]}",
                     ip=f"10.8.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}").json()
    _, owner_h = _agent(client)
    mid = _mission(client, owner_h)["id"]
    tok = d.get("token") or d.get("jwt") or "x"
    before = _snap()
    assert VERBS[verb](client, mid, {"Authorization": f"Bearer {tok}"}).status_code in (401, 403)
    assert _snap() == before
