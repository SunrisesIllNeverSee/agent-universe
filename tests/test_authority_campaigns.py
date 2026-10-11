"""Campaign ownership boundary.

A campaign records the authentic creating agent (`owner_agent_id`, derived
server-side from the live Bearer API key). add_mission / close / activate
require that agent or the admin key; check order is 401 -> 404 -> 403, all
before any write. Ownerless legacy campaigns fail closed for agents. JWTs are
not accepted (api_key-only convention). Campaign authority is distinct from
mission authority (frozen contract 1B D16-P7, 1G §5.C). Runs on the session
tmp root (see conftest) — never real data/.
"""
import json
import uuid

import pytest

from app.deps import state
from tests.conftest import signup_agent

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


def _agent(client):
    ip = f"10.9.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"ac-{uuid.uuid4().hex[:6]}", ip=ip).json()
    return d["agent_id"], {"Authorization": f"Bearer {d['api_key']}"}, d


def _campaign(client, headers, **body):
    r = client.post("/api/campaigns", json={"name": "c", **body}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _lines(name):
    p = state.root / "data" / name
    return len(p.read_text().splitlines()) if p.exists() else 0


def _snap():
    from app.routes import missions as m
    return (json.dumps(m._load_campaigns(), sort_keys=True),
            json.dumps(m._load_missions(), sort_keys=True),
            _lines("audit.jsonl"), _lines("seeds.jsonl"))


def _legacy(cid):
    from app.routes import missions as m
    cs = m._load_campaigns()
    cs.append({"id": cid, "name": "legacy", "status": "active", "missions": [],
               "closed_at": None, "outcome": ""})
    m._save_campaigns(cs)


VERBS = {
    "add_mission": lambda c, cid, h: c.post(f"/api/campaigns/{cid}/add_mission", json={"mission_id": "mission-x"}, headers=h),
    "close": lambda c, cid, h: c.post(f"/api/campaigns/{cid}/close", json={"outcome": "done"}, headers=h),
    "activate": lambda c, cid, h: c.post(f"/api/campaigns/{cid}/activate", json={}, headers=h),
}
verbs = pytest.mark.parametrize("verb", list(VERBS))


# ── creation ────────────────────────────────────────────────────────────────

def test_agent_creation_records_authentic_owner(client):
    aid, h, _ = _agent(client)
    c = _campaign(client, h)
    assert c["owner_agent_id"] == aid and c["created_by"] == "agent"


def test_body_supplied_owner_is_ignored(client):
    aid, h, _ = _agent(client)
    other, _, _ = _agent(client)
    c = _campaign(client, h, owner_agent_id=other, agent_id=other, created_by="operator")
    assert c["owner_agent_id"] == aid and c["created_by"] == "agent"


def test_admin_creation_records_no_agent_principal(client):
    c = _campaign(client, ADMIN, owner_agent_id="agent-forged", created_by="agent")
    assert c["owner_agent_id"] is None and c["created_by"] == "operator"


def test_create_denied_for_forged_and_revoked(client, admin_client):
    aid, h, _ = _agent(client)
    assert admin_client.post("/api/provision/revoke", json={"agent_id": aid}).status_code == 200
    before = _snap()
    r = client.post("/api/campaigns", json={"name": "x"}, headers={"Authorization": "Bearer forged-" + uuid.uuid4().hex})
    assert r.status_code in (401, 403)
    assert client.post("/api/campaigns", json={"name": "x"}, headers=h).status_code in (401, 403)
    assert _snap() == before


# ── per-verb authorization ──────────────────────────────────────────────────

@verbs
def test_anonymous_denied_no_write(client, verb):
    _, h, _ = _agent(client)
    cid = _campaign(client, h)["id"]
    before = _snap()
    assert VERBS[verb](client, cid, {}).status_code in (401, 403)
    assert _snap() == before


@verbs
def test_unknown_campaign_404_before_write(client, verb):
    _, h, _ = _agent(client)
    before = _snap()
    assert VERBS[verb](client, "campaign-nope", h).status_code == 404
    assert VERBS[verb](client, "campaign-nope", ADMIN).status_code == 404
    assert _snap() == before


@verbs
def test_unauthenticated_unknown_is_401_not_404(client, verb):
    r = VERBS[verb](client, "campaign-nope", {"Authorization": "Bearer forged-" + uuid.uuid4().hex})
    assert r.status_code in (401, 403) and r.status_code != 404


@verbs
def test_revoked_key_denied_no_write(client, admin_client, verb):
    aid, h, _ = _agent(client)
    cid = _campaign(client, h)["id"]
    assert admin_client.post("/api/provision/revoke", json={"agent_id": aid}).status_code == 200
    before = _snap()
    assert VERBS[verb](client, cid, h).status_code in (401, 403)
    assert _snap() == before


@verbs
def test_forged_referer_and_localhost_xff_denied(client, verb):
    _, owner_h, _ = _agent(client)
    _, other_h, _ = _agent(client)
    cid = _campaign(client, owner_h)["id"]
    before = _snap()
    h = {**other_h, "Referer": "http://localhost:8300/console", "Origin": "http://localhost:8300",
         "X-Forwarded-For": "127.0.0.1"}
    assert VERBS[verb](client, cid, h).status_code in (401, 403)
    assert _snap() == before


@verbs
def test_garbage_admin_header_plus_other_agent_key_denied(client, verb):
    _, owner_h, _ = _agent(client)
    _, other_h, _ = _agent(client)
    cid = _campaign(client, owner_h)["id"]
    before = _snap()
    h = {**other_h, "X-Admin-Key": "garbage-" + uuid.uuid4().hex}
    assert VERBS[verb](client, cid, h).status_code in (401, 403)
    assert _snap() == before


@verbs
def test_other_agent_denied_no_write(client, verb):
    _, owner_h, _ = _agent(client)
    _, other_h, _ = _agent(client)
    cid = _campaign(client, owner_h)["id"]
    before = _snap()
    assert VERBS[verb](client, cid, other_h).status_code == 403
    assert _snap() == before


@verbs
def test_owner_agent_allowed(client, verb):
    _, h, _ = _agent(client)
    cid = _campaign(client, h)["id"]
    assert VERBS[verb](client, cid, h).status_code == 200


@verbs
def test_admin_allowed_on_agent_campaign(client, verb):
    _, h, _ = _agent(client)
    cid = _campaign(client, h)["id"]
    assert VERBS[verb](client, cid, ADMIN).status_code == 200


@verbs
def test_legacy_ownerless_denied_for_agent_allowed_for_admin(client, verb):
    cid = f"campaign-legacy-{uuid.uuid4().hex[:6]}"
    _legacy(cid)
    _, h, _ = _agent(client)
    before = _snap()
    assert VERBS[verb](client, cid, h).status_code == 403
    assert _snap() == before
    assert VERBS[verb](client, cid, ADMIN).status_code == 200


@verbs
def test_operator_created_campaign_denied_for_agents(client, verb):
    cid = _campaign(client, ADMIN)["id"]
    _, h, _ = _agent(client)
    before = _snap()
    assert VERBS[verb](client, cid, h).status_code == 403
    assert _snap() == before


@verbs
def test_owner_jwt_does_not_authorize(client, verb):
    """api_key-only convention: the owner's own JWT must not mutate."""
    _, h, d = _agent(client)
    cid = _campaign(client, h)["id"]
    tok = d.get("token") or d.get("jwt") or "x"
    before = _snap()
    assert VERBS[verb](client, cid, {"Authorization": f"Bearer {tok}"}).status_code in (401, 403)
    assert _snap() == before


# ── held owner decision ─────────────────────────────────────────────────────

@pytest.mark.xfail(strict=True, reason=(
    "HELD owner decision: add_mission touches two objects. Today only campaign "
    "authority is required; whether the caller must ALSO own the mission is not "
    "defined by frozen contracts (1B D16-P7 / 1G §5.C only separate the layers)."))
def test_add_mission_requires_mission_ownership_too(client):
    _, camp_h, _ = _agent(client)
    _, mis_h, _ = _agent(client)
    mid = client.post("/api/missions", json={"label": "m"}, headers=mis_h).json()["id"]
    cid = _campaign(client, camp_h)["id"]
    r = client.post(f"/api/campaigns/{cid}/add_mission", json={"mission_id": mid}, headers=camp_h)
    assert r.status_code == 403
