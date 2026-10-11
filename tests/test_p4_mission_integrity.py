"""
test_p4_mission_integrity.py — P4_BASELINE / P4_REPAIR_MISSION_INTEGRITY.

/api/slots/create used to mint `mission-<hex>` ids (when mission_id omitted)
that never resolved to a mission record (orphans). Sibling fix for
/api/slots/bounty is commit b06ae00.

Isolation: the session `app` fixture runs on a tmp root (see conftest), so
_load_missions/_load_slots read the temp data dir, never real data/.
"""
import uuid

import pytest

from tests.conftest import signup_agent

CREATE = {
    "formation_id": "p4-formation", "posture": "SCOUT", "label": "P4 Mission",
    "positions": [{"row": 0, "col": 0}, {"row": 0, "col": 1}],
    "roles": ["primary", "observer"], "revenue_splits": [60, 40],
}


def _uniq(p="p4"):
    return f"{p}-{uuid.uuid4().hex[:8]}"


def _stores():
    from app.routes import missions as m
    return m._load_missions(), m._load_slots()


def _snapshot():
    missions, slots = _stores()
    return len(missions), len(slots)


def _ledger_len():
    from app.deps import state
    return len(state.audit.recent(10_000))


# ── pinned authorization behavior (unchanged by the repair) ─────────────────

def test_create_requires_admin_or_agent_bearer_no_mutation(client):
    before = _snapshot()
    r = client.post("/api/slots/create", json=CREATE)
    assert r.status_code == 403
    assert _snapshot() == before


def test_create_rejects_bad_admin_key_no_mutation(client):
    before = _snapshot()
    r = client.post("/api/slots/create", json=CREATE,
                    headers={"X-Admin-Key": "wrong-key"})
    assert r.status_code == 403
    assert _snapshot() == before


def test_create_rejects_bogus_bearer_no_mutation(client):
    before = _snapshot()
    r = client.post("/api/slots/create", json=CREATE,
                    headers={"Authorization": "Bearer not-a-real-key"})
    assert r.status_code == 403
    assert _snapshot() == before


def test_create_allows_admin(admin_client):
    r = admin_client.post("/api/slots/create", json=CREATE)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["created"] == 2 and d["mission_id"].startswith("mission-")
    assert all(s["mission_id"] == d["mission_id"] and s["status"] == "open"
               for s in d["slots"])


def test_create_allows_registered_agent_bearer(client):
    resp = signup_agent(client, name=_uniq("p4agent"))
    key = resp.json()["api_key"]
    r = client.post("/api/slots/create", json=CREATE,
                    headers={"Authorization": f"Bearer {key}"})
    assert r.status_code == 200, r.text


def test_create_logs_one_slots_created_audit_event(admin_client):
    from app.deps import state
    r = admin_client.post("/api/slots/create", json=CREATE)
    assert r.status_code == 200
    mid = r.json()["mission_id"]
    hits = [e for e in state.audit.recent(10_000)
            if e.action == "slots_created" and e.detail.get("mission_id") == mid]
    assert len(hits) == 1 and hits[0].component == "deploy"
    assert hits[0].detail["slots_created"] == 2


# ── pinned: caller-supplied mission_id is passed through unchanged ──────────

def test_supplied_unknown_mission_id_passthrough_unchanged(admin_client):
    """Supplied-but-unknown ids are NOT validated here (would break existing
    callers; binding preconditions belong to later P4 nodes)."""
    mid = _uniq("caller-mission")
    r = admin_client.post("/api/slots/create", json={**CREATE, "mission_id": mid})
    assert r.status_code == 200
    assert r.json()["mission_id"] == mid
    missions, slots = _stores()
    assert sum(1 for s in slots if s["mission_id"] == mid) == 2
    assert not any(m.get("mission_id") == mid for m in missions)  # no record minted


# ── repair: minted ids resolve, linkage both ways, no collisions ────────────

def test_minted_mission_id_resolves_to_mission_record(admin_client):
    r = admin_client.post("/api/slots/create", json=CREATE)
    assert r.status_code == 200
    mid = r.json()["mission_id"]
    g = admin_client.get(f"/api/missions/{mid}")
    assert g.status_code == 200, f"orphan mission id {mid}"
    m = g.json()["mission"]
    assert m["id"] == m["mission_id"] == mid
    assert m["status"] == "active" and m["origin"] == "slots_create"
    assert m["label"] == "P4 Mission" and m["agents"] == []  # no owner chosen


def test_slot_mission_linkage_both_ways(admin_client):
    d = admin_client.post("/api/slots/create", json=CREATE).json()
    missions, slots = _stores()
    recs = [m for m in missions if m["mission_id"] == d["mission_id"]]
    assert len(recs) == 1  # exactly one record
    stored = {s["id"] for s in slots if s["mission_id"] == d["mission_id"]}
    assert stored == {s["id"] for s in d["slots"]} == set(recs[0]["slot_ids"])


def test_every_minted_id_resolves_across_repeated_calls(admin_client):
    mids = [admin_client.post("/api/slots/create", json=CREATE).json()["mission_id"]
            for _ in range(3)]
    recorded = {m["mission_id"] for m in _stores()[0]}
    assert set(mids) <= recorded


def test_retry_is_not_idempotent_but_never_collides(admin_client):
    """Documented semantics: omitted mission_id => each call mints a NEW
    mission + NEW slots (same as pre-fix, minus the orphan). No dedupe key."""
    a = admin_client.post("/api/slots/create", json=CREATE).json()
    b = admin_client.post("/api/slots/create", json=CREATE).json()
    assert a["mission_id"] != b["mission_id"]
    assert not ({s["id"] for s in a["slots"]} & {s["id"] for s in b["slots"]})
    missions, _ = _stores()
    ids = [m["mission_id"] for m in missions]
    assert len(ids) == len(set(ids))


def test_minted_id_avoids_existing_ids(admin_client, monkeypatch):
    """Force the RNG to first emit an already-taken id; handler must re-mint."""
    from app.routes import missions as mr
    taken = admin_client.post("/api/slots/create", json=CREATE).json()["mission_id"]
    forced = iter([taken[len("mission-"):], "feedface"])
    real = mr._secrets_mod.token_hex
    monkeypatch.setattr(mr._secrets_mod, "token_hex",
                        lambda n: next(forced, None) or real(n))
    d = admin_client.post("/api/slots/create", json=CREATE).json()
    assert d["mission_id"] == "mission-feedface"
    ids = [m["mission_id"] for m in _stores()[0]]
    assert ids.count(taken) == 1 and ids.count("mission-feedface") == 1


def test_denied_calls_still_mutate_nothing(client):
    before = _snapshot()
    assert client.post("/api/slots/create", json=CREATE).status_code == 403
    assert _snapshot() == before


def test_seed_provenance_unchanged(admin_client):
    d = admin_client.post("/api/slots/create", json=CREATE).json()
    assert set(d) == {"created", "mission_id", "slots", "seed_doi"}
