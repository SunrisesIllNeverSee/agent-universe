"""Agent-built campaigns: create -> activate -> own mission -> attach -> task -> close.

add_mission needs campaign authority AND an existing, same-owner mission (uniform
Mission-not-found 404 for foreign/unknown, no oracle; admin may attach any EXISTING
mission; re-attach is an idempotent 200 no-op). POST /api/tasks is the only /api/tasks
route reachable by agents at the edge (exact path); a task's campaign_id requires
campaign ownership (uniform 404), mission_id requires mission ownership AND membership
in that campaign (409). Agent-set payout / custom exp_reward are refused (financial/EXP
claim, owner decision). Lifecycle verbs stay admin-only at the edge. Session tmp root.
"""
import json
import uuid

from app.deps import state
from tests.conftest import signup_agent

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


def _agent(client):
    ip = f"10.9.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"oc-{uuid.uuid4().hex[:6]}", ip=ip).json()
    return d["agent_id"], {"Authorization": f"Bearer {d['api_key']}"}


def _lines(name):
    p = state.root / "data" / name
    return len(p.read_text().splitlines()) if p.exists() else 0


def _snap():
    from app.routes import missions as m
    return (json.dumps(m._load_campaigns(), sort_keys=True),
            json.dumps(m._load_missions(), sort_keys=True),
            json.dumps(m._load_tasks(), sort_keys=True),
            _lines("audit.jsonl"), _lines("seeds.jsonl"))


def _campaign(client, h):
    r = client.post("/api/campaigns", json={"name": "c"}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _mission(client, h):
    r = client.post("/api/missions", json={"label": "m"}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _attach(client, cid, mid, h):
    return client.post(f"/api/campaigns/{cid}/add_mission", json={"mission_id": mid}, headers=h)


def _task(client, h, **body):
    return client.post("/api/tasks", json={"title": "t", **body}, headers=h)


# ── full agent workflow ─────────────────────────────────────────────────────

def test_agent_builds_campaign_end_to_end(client):
    aid, h = _agent(client)
    cid = _campaign(client, h)
    assert client.get(f"/api/campaigns/{cid}").json()["campaign"]["owner_agent_id"] == aid
    assert client.post(f"/api/campaigns/{cid}/activate", json={}, headers=h).json()["status"] == "active"
    mid = _mission(client, h)
    assert mid in _attach(client, cid, mid, h).json()["missions"]
    r = _task(client, h, campaign_id=cid, mission_id=mid)
    assert r.status_code == 200, r.text
    t = r.json()
    assert (t["campaign_id"], t["mission_id"], t["owner_agent_id"]) == (cid, mid, aid)
    c = client.post(f"/api/campaigns/{cid}/close", json={"outcome": "done"}, headers=h)
    assert c.status_code == 200 and c.json()["status"] == "closed"


# ── add_mission ─────────────────────────────────────────────────────────────

def test_add_foreign_mission_uniform_404_no_write(client):
    _, ch = _agent(client)
    _, mh = _agent(client)
    cid, foreign = _campaign(client, ch), _mission(client, mh)
    before = _snap()
    r1 = _attach(client, cid, foreign, ch)
    r2 = _attach(client, cid, "mission-nope", ch)
    assert r1.status_code == r2.status_code == 404
    assert r1.json() == {"error": "Mission not found", "mission_id": foreign}
    assert r2.json() == {"error": "Mission not found", "mission_id": "mission-nope"}
    assert _snap() == before


def test_add_ownerless_mission_denied_for_agent(client):
    _, ch = _agent(client)
    cid = _campaign(client, ch)
    mid = _mission(client, ADMIN)
    before = _snap()
    assert _attach(client, cid, mid, ch).status_code == 404
    assert _snap() == before


def test_admin_attaches_any_existing_mission_but_not_unknown(client):
    _, ch = _agent(client)
    _, mh = _agent(client)
    cid, mid = _campaign(client, ch), _mission(client, mh)
    assert mid in _attach(client, cid, mid, ADMIN).json()["missions"]
    before = _snap()
    assert _attach(client, cid, "mission-nope", ADMIN).status_code == 404
    assert _snap() == before


def test_add_mission_idempotent_and_requires_id(client):
    _, h = _agent(client)
    cid, mid = _campaign(client, h), _mission(client, h)
    assert _attach(client, cid, mid, h).status_code == 200
    before = _snap()
    r = _attach(client, cid, mid, h)
    assert r.status_code == 200 and r.json()["missions"].count(mid) == 1
    assert _snap() == before
    assert _attach(client, cid, "", h).status_code == 400
    assert _snap() == before


def test_non_owner_cannot_attach_even_own_mission(client):
    _, oh = _agent(client)
    _, xh = _agent(client)
    cid, mine = _campaign(client, oh), _mission(client, xh)
    before = _snap()
    assert _attach(client, cid, mine, xh).status_code == 403
    assert _snap() == before


# ── task create: campaign scoping ───────────────────────────────────────────

def test_agent_can_create_plain_task_at_edge(client):
    aid, h = _agent(client)
    r = _task(client, h)
    assert r.status_code == 200 and r.json()["owner_agent_id"] == aid


def test_task_in_foreign_unknown_ownerless_campaign_uniform_404(client):
    _, oh = _agent(client)
    _, xh = _agent(client)
    foreign = _campaign(client, oh)
    ownerless = _campaign(client, ADMIN)
    before = _snap()
    bodies = []
    for cid in (foreign, "campaign-nope", ownerless):
        r = _task(client, xh, campaign_id=cid)
        assert r.status_code == 404
        bodies.append(r.json()["error"])
    assert set(bodies) == {"Campaign not found"}
    assert _snap() == before


def test_task_mission_must_belong_to_campaign(client):
    _, h = _agent(client)
    cid, mid = _campaign(client, h), _mission(client, h)  # mid not attached
    before = _snap()
    assert _task(client, h, campaign_id=cid, mission_id=mid).status_code == 409
    assert _snap() == before
    _attach(client, cid, mid, h)
    assert _task(client, h, campaign_id=cid, mission_id=mid).status_code == 200


def test_task_foreign_mission_still_uniform_404_under_own_campaign(client):
    _, h = _agent(client)
    _, oh = _agent(client)
    cid, foreign = _campaign(client, h), _mission(client, oh)
    before = _snap()
    r = _task(client, h, campaign_id=cid, mission_id=foreign)
    assert r.status_code == 404 and r.json() == {"error": "Mission not found", "mission_id": foreign}
    assert _snap() == before


def test_admin_task_in_any_campaign_unchanged(client):
    _, h = _agent(client)
    cid = _campaign(client, h)
    assert _task(client, ADMIN, campaign_id=cid, payout=5, exp_reward=999).status_code == 200


# ── task create: payout / EXP ───────────────────────────────────────────────

def test_agent_payout_and_custom_exp_refused(client):
    _, h = _agent(client)
    before = _snap()
    assert _task(client, h, payout=100).status_code == 403
    assert _task(client, h, payout=-5).status_code == 403
    assert _task(client, h, exp_reward=10**9).status_code == 403
    assert _snap() == before
    assert _task(client, h, payout=0, exp_reward=150).status_code == 200  # default build EXP


# ── edge: lifecycle verbs stay operator-only ────────────────────────────────

def test_task_lifecycle_verbs_not_reachable_by_agents_at_edge(client):
    _, h = _agent(client)
    tid = _task(client, h).json()["id"]
    before = _snap()
    for verb, body in (("assign", {"agent_id": "x"}), ("start", {}), ("deliver", {}),
                       ("close", {}), ("cancel", {})):
        r = client.post(f"/api/tasks/{tid}/{verb}", json=body, headers=h)
        assert r.status_code == 403, verb
    assert client.post("/api/tasks/", json={"title": "t"}, headers=h).status_code in (403, 404, 405, 307)
    assert _snap() == before
