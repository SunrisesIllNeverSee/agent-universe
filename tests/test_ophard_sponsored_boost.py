"""Boost / sponsored attribution is bound to the authenticated principal.

An agent's body agent_id/handle may not name anyone else (403, no write); an omitted
one is filled from the Bearer key. Admin keeps free-form attribution. No payment is
triggered by these routes (sponsored fee is a constant 0, boost has no Stripe call).
Session tmp root, real seeded KA§§A post.
"""
import json
import uuid

from app.deps import state
from tests.conftest import signup_agent
from tests.test_routes_kassa import _post_payload

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


def _agent(client):
    ip = f"10.9.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"ob-{uuid.uuid4().hex[:6]}", ip=ip).json()
    return d["agent_id"], {"Authorization": f"Bearer {d['api_key']}"}


def _post(client):
    r = client.post("/api/kassa/posts", json=_post_payload("bounties"), headers=ADMIN)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _lines(name):
    p = state.root / "data" / name
    return len(p.read_text().splitlines()) if p.exists() else 0


def _boosts():
    p = state.root / "data" / "boosts.json"
    return p.read_text() if p.exists() else ""


def _snap():
    return (_boosts(), _lines("audit.jsonl"), _lines("seeds.jsonl"))


# ── boost ───────────────────────────────────────────────────────────────────

def test_boost_binds_to_principal_when_body_omits(client):
    aid, h = _agent(client)
    pid = _post(client)
    r = client.post(f"/api/boost/{pid}", json={"duration_hours": 2}, headers=h)
    assert r.status_code == 200, r.text
    b = [x for x in json.loads(_boosts())["boosts"] if x["boost_id"] == r.json()["boost_id"]][0]
    assert b["boosted_by"] == aid


def test_boost_matching_body_agent_ok(client):
    aid, h = _agent(client)
    pid = _post(client)
    assert client.post(f"/api/boost/{pid}", json={"agent_id": aid}, headers=h).status_code == 200


def test_boost_forged_body_agent_denied_no_write(client):
    _, h = _agent(client)
    victim, _ = _agent(client)
    pid = _post(client)
    before = _snap()
    assert client.post(f"/api/boost/{pid}", json={"agent_id": victim}, headers=h).status_code == 403
    assert _snap() == before


def test_boost_forged_credential_and_anonymous_denied(client):
    pid = _post(client)
    before = _snap()
    forged = {"Authorization": "Bearer forged-" + uuid.uuid4().hex}
    assert client.post(f"/api/boost/{pid}", json={}, headers=forged).status_code in (401, 403)
    assert client.post(f"/api/boost/{pid}", json={}).status_code in (401, 403)
    assert _snap() == before


def test_boost_unknown_post_and_bad_duration_noop(client):
    _, h = _agent(client)
    pid = _post(client)
    before = _snap()
    assert client.post("/api/boost/K-nope", json={}, headers=h).status_code == 404
    assert client.post(f"/api/boost/{pid}", json={"duration_hours": 0}, headers=h).status_code == 400
    assert client.post(f"/api/boost/{pid}", json={"duration_hours": 999}, headers=h).status_code == 400
    assert _snap() == before


def test_boost_admin_keeps_free_form_attribution(client):
    pid = _post(client)
    r = client.post(f"/api/boost/{pid}", json={"agent_id": "agent-any"}, headers=ADMIN)
    assert r.status_code == 200
    assert any(x["boosted_by"] == "agent-any" for x in json.loads(_boosts())["boosts"])


# ── sponsored ───────────────────────────────────────────────────────────────

def _sp(raw, sid):
    return [x for x in json.loads(raw)["sponsored"] if x["sponsored_id"] == sid][0]


def test_sponsored_binds_to_principal_when_body_omits(client):
    pid = _post(client)
    aid, h = _agent(client)
    r = client.post("/api/sponsored", json={"post_id": pid, "label": "L"}, headers=h)
    assert r.status_code == 200, r.text
    assert _sp(_boosts(), r.json()["sponsored_id"])["agent_id"] == aid
    assert r.json()["fee_usd"] == 0  # no billing path


def test_sponsored_forged_agent_or_handle_denied_no_write(client):
    pid = _post(client)
    _, h = _agent(client)
    victim, _ = _agent(client)
    before = _snap()
    assert client.post("/api/sponsored", json={"post_id": pid, "agent_id": victim}, headers=h).status_code == 403
    assert client.post("/api/sponsored", json={"post_id": pid, "handle": "someone-else"}, headers=h).status_code == 403
    assert _snap() == before


def test_sponsored_forged_credential_and_anonymous_denied(client):
    pid = _post(client)
    before = _snap()
    forged = {"Authorization": "Bearer forged-" + uuid.uuid4().hex}
    assert client.post("/api/sponsored", json={"post_id": pid}, headers=forged).status_code in (401, 403)
    assert client.post("/api/sponsored", json={"post_id": pid}).status_code in (401, 403)
    assert _snap() == before


def test_sponsored_admin_keeps_free_form_attribution(client):
    pid = _post(client)
    r = client.post("/api/sponsored", json={"post_id": pid, "agent_id": "agent-any"}, headers=ADMIN)
    assert r.status_code == 200
    assert _sp(_boosts(), r.json()["sponsored_id"])["agent_id"] == "agent-any"


def test_sponsored_unknown_post_and_unbounded_duration_rejected_no_write(client):
    pid = _post(client)
    aid, h = _agent(client)
    before = _snap()
    for hdr in (h, ADMIN):
        assert client.post("/api/sponsored", json={"post_id": "K-DOES-NOT-EXIST"}, headers=hdr).status_code == 404
        assert client.post("/api/sponsored", json={"post_id": ""}, headers=hdr).status_code == 404
        for d in (0, 169, 10_000_000):
            r = client.post("/api/sponsored", json={"post_id": pid, "duration_hours": d}, headers=hdr)
            assert r.status_code == 400, (d, r.status_code)
    assert _snap() == before
