"""
test_slots_reference_failclosed.py — D-C: POST /api/slots/create with a
caller-supplied mission_id that matches no mission record fails closed (404)
before any write. Omitted/empty id still mints exactly one mission.

Status choice: 404 {"error": "Mission not found"} — same as GET
/api/missions/{id} and every other missions.py lookup miss.
Matching: exact, case-sensitive, no stripping (same as get_mission).
"""
import uuid

import pytest

from tests.conftest import signup_agent

CREATE = {
    "formation_id": "fc-formation", "posture": "SCOUT", "label": "FC Mission",
    "positions": [{"row": 0, "col": 0}, {"row": 0, "col": 1}],
    "roles": ["primary", "observer"], "revenue_splits": [60, 40],
}


def _uniq(p="fc"):
    return f"{p}-{uuid.uuid4().hex[:8]}"


def _state():
    from app.deps import state
    from app.routes import missions as m
    from app import seeds
    try:
        with open(seeds.SEEDS_FILE) as f:
            seed_lines = sum(1 for _ in f)
    except FileNotFoundError:
        seed_lines = 0
    return (len(m._load_missions()), len(m._load_slots()),
            len(state.audit.recent(10_000)), seed_lines)


@pytest.fixture
def agent_headers(client):
    key = signup_agent(client, name=_uniq("fcagent")).json()["api_key"]
    return {"Authorization": f"Bearer {key}"}


@pytest.fixture(params=["admin", "agent"])
def authed(request, admin_client, client, agent_headers):
    if request.param == "admin":
        return lambda body: admin_client.post("/api/slots/create", json=body)
    return lambda body: client.post("/api/slots/create", json=body, headers=agent_headers)


def test_unknown_mission_id_rejected_no_side_effects(authed):
    before = _state()
    r = authed({**CREATE, "mission_id": _uniq("ghost")})
    assert r.status_code == 404
    assert r.json()["error"] == "Mission not found"
    assert _state() == before


@pytest.mark.parametrize("bad", ["   ", "\t", "ghost mission"])
def test_whitespace_ids_are_supplied_and_rejected(authed, bad):
    before = _state()
    assert authed({**CREATE, "mission_id": bad}).status_code == 404
    assert _state() == before


def test_slot_id_is_not_a_mission_id(authed):
    minted = authed(CREATE).json()
    slot_id = minted["slots"][0]["id"]
    before = _state()
    assert authed({**CREATE, "mission_id": slot_id}).status_code == 404
    assert _state() == before


def test_orphan_slot_mission_id_not_accepted(authed):
    """An id that only exists on legacy orphan slots is still not a mission."""
    from app.routes import missions as m
    mid = _uniq("orphan")
    slots = m._load_slots()
    slots.append({"id": _uniq("slot"), "mission_id": mid, "status": "open"})
    m._save_slots(slots)
    before = _state()
    assert authed({**CREATE, "mission_id": mid}).status_code == 404
    assert _state() == before


def test_case_variation_is_unknown(authed):
    d = authed(CREATE).json()
    mid = d["mission_id"]
    before = _state()
    assert authed({**CREATE, "mission_id": mid.upper()}).status_code == 404
    assert _state() == before


def test_existing_mission_id_still_works_no_new_mission(authed):
    mid = authed(CREATE).json()["mission_id"]
    m0, s0, _, _ = _state()
    r = authed({**CREATE, "mission_id": mid})
    assert r.status_code == 200 and r.json()["mission_id"] == mid
    m1, s1, _, _ = _state()
    assert m1 == m0 and s1 == s0 + 2
    from app.routes import missions as m
    assert sum(1 for x in m._load_missions() if x["mission_id"] == mid) == 1


@pytest.mark.parametrize("omitted", [{}, {"mission_id": ""}])
def test_omitted_or_empty_id_mints_exactly_one_mission(authed, omitted):
    m0, s0, _, _ = _state()
    r = authed({**CREATE, **omitted})
    assert r.status_code == 200
    m1, s1, _, _ = _state()
    assert m1 == m0 + 1 and s1 == s0 + 2


def test_unauthenticated_still_403_before_validation(client):
    before = _state()
    r = client.post("/api/slots/create", json={**CREATE, "mission_id": "ghost"})
    assert r.status_code == 403
    assert _state() == before
