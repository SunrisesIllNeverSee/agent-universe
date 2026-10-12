"""P4 slice 11 (G1) -- mission auto-complete completes its bound active Agreements, loudly."""
from tests.test_p4_entry_api import _agent
from tests.test_p4_slot_binding import _fill, _mk_slot, _store

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


def _close_only_task(client, owner, mission_id):
    t = client.post("/api/tasks", headers=owner["h"], json={"title": "t", "mission_id": mission_id})
    assert t.status_code == 200, t.text
    tid = t.json()["id"]
    r = client.post(f"/api/tasks/{tid}/close", headers=ADMIN, json={})
    assert r.status_code == 200, r.text
    return r.json()


def test_auto_complete_completes_active_agreements(client):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    aid = _fill(client, ent, s["id"]).json()["agreement_id"]
    assert _store().get(aid)["state"] == "active"
    out = _close_only_task(client, owner, s["mission_id"])
    mc = out["mission_completed"]
    assert mc["auto_completed"] is True and mc["agreements_completed"] == [aid] and mc["agreement_errors"] == []
    ag = _store().get(aid)
    assert ag["state"] == "completed"
    rcs = _store().receipts(aid)
    last = rcs[-1]
    assert last["transition"] == "complete" and last["seed_doi"]
    assert last["actor"].startswith("operator:mission-auto-complete")


def test_auto_complete_failure_is_loud_and_mission_still_completes(client, monkeypatch):
    from app.workentry_store import WorkEntryError
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    aid = _fill(client, ent, s["id"]).json()["agreement_id"]

    def boom(*a, **k):
        raise WorkEntryError("provenance down")
    monkeypatch.setattr(_store(), "complete", boom)
    out = _close_only_task(client, owner, s["mission_id"])
    mc = out["mission_completed"]
    assert mc["auto_completed"] is True and mc["agreements_completed"] == []
    assert [e["agreement_id"] for e in mc["agreement_errors"]] == [aid]
    m = client.get(f"/api/missions/{s['mission_id']}").json()["mission"]
    assert m["status"] == "completed"


def test_auto_complete_without_agreements_unchanged(client):
    owner = _agent(client)
    s = _mk_slot(client, owner)
    mc = _close_only_task(client, owner, s["mission_id"])["mission_completed"]
    assert mc["auto_completed"] is True and mc["agreements_completed"] == []
