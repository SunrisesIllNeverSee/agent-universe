"""P4 slice 4 -- slot / mission binding.

Activation binds the slot (Agreement first, then slot write under slot_lock; slot failure
-> evidence_gap + compensating terminated). /api/slots/fill on open-mode slots mints the
Agreement atomically; standard/constitutional -> 409 'enter via agreement'. slots/leave and
mission end drive the Agreement. Post-origin acceptance mints the slot/mission.
"""
import pytest

from tests.test_p4_entry_api import _agent, _file, _post, _slot  # noqa: F401

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


def _mk_slot(client, owner, **extra):
    r = client.post("/api/slots/create", headers=owner["h"],
                    json={"label": "S4", "positions": [{"row": 0, "col": 0}], "roles": ["primary"], **extra})
    assert r.status_code == 200, r.text
    return r.json()["slots"][0]


def _slot_now(client, slot_id):
    return next(s for s in client.get("/api/slots").json()["slots"] if s["id"] == slot_id)


def _fill(client, who, slot_id):
    return client.post("/api/slots/fill", headers=who["h"], json={"slot_id": slot_id, "agent_id": who["id"]})


def _store():
    from app.deps import state
    return state.workentry


# ── fields ───────────────────────────────────────────────────────────────

def test_new_slots_and_missions_carry_additive_fields(client):
    owner = _agent(client)
    s = _mk_slot(client, owner)
    assert s["entry_mode"] == "open" and s["agreement_id"] is None and s["post_id"] is None
    m = client.get(f"/api/missions/{s['mission_id']}").json()["mission"]
    assert m["entry_mode"] == "open" and m["post_id"] is None
    s2 = _mk_slot(client, owner, entry_mode="standard")
    assert s2["entry_mode"] == "standard"
    bad = client.post("/api/slots/create", headers=owner["h"],
                      json={"positions": [{"row": 0, "col": 0}], "entry_mode": "nope"})
    assert bad.status_code == 422


def test_legacy_records_default_to_open(client):
    import json
    from app.deps import state
    p = state.data_path("slots.json")
    legacy = {"id": "slot-legacy1", "mission_id": "mission-legacy1", "mission_label": "L", "role": "primary",
              "grid_ref": "A1", "governance": {"mode": "x", "posture": "SCOUT"}, "revenue_split_pct": 10,
              "status": "open", "agent_id": None, "agent_name": None, "filled_at": None}
    cur = json.loads(p.read_text()) if p.exists() else []
    p.write_text(json.dumps(cur + [legacy]))
    got = _slot_now(client, "slot-legacy1")
    assert got["entry_mode"] == "open" and got["agreement_id"] is None


# ── open-mode fill: Agreement minted atomically ──────────────────────────

def test_open_fill_mints_agreement_atomically_and_returns_receipt(client):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    r = _fill(client, ent, s["id"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["filled"] is True and body["slot"]["agent_id"] == ent["id"]       # unchanged keys
    aid = body["agreement_id"]
    a = _store().get(aid)
    assert a["state"] == "active" and a["entry_mode"] == "open"
    assert a["objects"]["slot_id"] == s["id"] and a["objects"]["mission_id"] == s["mission_id"]
    assert [h["transition"] for h in a["state_history"]] == ["create", "file", "resolve_open", "activate"]
    assert body["receipt"]["to"] == "active" and body["receipt"]["seed_doi"]
    assert body["mission_id"] == s["mission_id"]
    sl = _slot_now(client, s["id"])
    assert sl["status"] == "filled" and sl["agreement_id"] == aid


def test_fill_standard_slot_409_enter_via_agreement(client):
    owner, ent = _agent(client), _agent(client)
    for mode in ("standard", "constitutional"):
        s = _mk_slot(client, owner, entry_mode=mode)
        r = _fill(client, ent, s["id"])
        assert r.status_code == 409, r.text
        assert "enter via agreement" in r.json()["error"]
        assert r.json()["opportunity_ref"] == f"slot:{s['id']}"
        assert _slot_now(client, s["id"])["status"] == "open"
    assert _store().list(entrant=ent["id"]) == []


def test_open_fill_provenance_failure_is_loud_and_leaves_slot_open(client, monkeypatch):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner)

    def boom(**kw):
        raise RuntimeError("seed down")
    monkeypatch.setattr(_store(), "_seed_fn", boom)
    r = _fill(client, ent, s["id"])
    assert r.status_code == 500 and r.json().get("evidence_gap_id")
    assert _slot_now(client, s["id"])["status"] == "open"


def test_open_fill_slot_write_failure_compensates(client, monkeypatch):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    import app.routes.missions as ms
    monkeypatch.setattr(ms, "_save_slots", lambda slots: (_ for _ in ()).throw(OSError("disk full")))
    r = _fill(client, ent, s["id"])
    assert r.status_code == 500
    monkeypatch.undo()
    rows = _store().list(entrant=ent["id"])
    assert len(rows) == 1 and rows[0]["state"] == "terminated"            # no orphan active agreement
    assert _store().evidence_gaps(rows[0]["agreement_id"])
    assert _slot_now(client, s["id"])["status"] == "open"


def test_fill_already_filled_still_409_and_no_agreement(client):
    owner, a, b = _agent(client), _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    assert _fill(client, a, s["id"]).status_code == 200
    r = _fill(client, b, s["id"])
    assert r.status_code == 409
    assert _store().list(entrant=b["id"]) == []


# ── activation binds the slot (standard) ─────────────────────────────────

def test_activation_binds_slot_standard(client):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner, entry_mode="standard")
    ref = f"slot:{s['id']}"
    aid = _file(client, ent, ref).json()["agreement"]["agreement_id"]
    assert client.post(f"/api/work-entry/{aid}/accept", headers=owner["h"]).status_code == 200
    assert _slot_now(client, s["id"])["status"] == "open"        # accepted does not bind
    act = client.post(f"/api/work-entry/{aid}/activate", headers=ent["h"])
    assert act.status_code == 200, act.text
    assert act.json()["mission_id"] == s["mission_id"] and act.json()["slot_id"] == s["id"]
    sl = _slot_now(client, s["id"])
    assert sl["status"] == "filled" and sl["agent_id"] == ent["id"] and sl["agreement_id"] == aid
    m = client.get(f"/api/missions/{s['mission_id']}").json()["mission"]
    assert any(x["agreement_id"] == aid and x["state"] == "active" for x in m["agreements"])


def test_activation_slot_taken_compensates(client):
    owner, e1, e2 = _agent(client), _agent(client), _agent(client)
    s = _mk_slot(client, owner, entry_mode="standard")
    ids = []
    for e in (e1, e2):
        aid = _file(client, e, f"slot:{s['id']}").json()["agreement"]["agreement_id"]
        client.post(f"/api/work-entry/{aid}/accept", headers=owner["h"])
        ids.append(aid)
    assert client.post(f"/api/work-entry/{ids[0]}/activate", headers=e1["h"]).status_code == 200
    r = client.post(f"/api/work-entry/{ids[1]}/activate", headers=e2["h"])
    assert r.status_code == 409
    a2 = _store().get(ids[1])
    assert a2["state"] == "terminated" and _store().evidence_gaps(ids[1])
    assert _slot_now(client, s["id"])["agreement_id"] == ids[0]


def test_activation_slot_write_failure_compensates(client, monkeypatch):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner, entry_mode="standard")
    aid = _file(client, ent, f"slot:{s['id']}").json()["agreement"]["agreement_id"]
    client.post(f"/api/work-entry/{aid}/accept", headers=owner["h"])
    import app.routes.missions as ms
    monkeypatch.setattr(ms, "_save_slots", lambda slots: (_ for _ in ()).throw(OSError("disk full")))
    r = client.post(f"/api/work-entry/{aid}/activate", headers=ent["h"])
    assert r.status_code == 500
    monkeypatch.undo()
    assert _store().get(aid)["state"] == "terminated"
    gaps = _store().evidence_gaps(aid)
    assert gaps and "slot" in gaps[0]["reason"]
    assert _slot_now(client, s["id"])["status"] == "open"


# ── post-origin: acceptance mints the slot/mission under the poster's authority ──

def test_post_origin_accept_mints_slot_and_mission(client):
    owner, ent = _agent(client), _agent(client)
    pid = _post(owner["id"])
    aid = _file(client, ent, f"post:{pid}").json()["agreement"]["agreement_id"]
    acc = client.post(f"/api/work-entry/{aid}/accept", headers=owner["h"])
    assert acc.status_code == 200, acc.text
    obj = acc.json()["agreement"]["objects"]
    assert obj["post_id"] == pid and obj["mission_id"] and obj["slot_id"]
    m = client.get(f"/api/missions/{obj['mission_id']}").json()["mission"]
    assert m["post_id"] == pid and m["owner_agent_id"] == owner["id"] and m["entry_mode"] == "standard"
    sl = _slot_now(client, obj["slot_id"])
    assert sl["post_id"] == pid and sl["status"] == "reserved" and sl["agreement_id"] == aid
    # a stranger cannot take the reserved slot
    other = _agent(client)
    assert _fill(client, other, obj["slot_id"]).status_code == 409
    act = client.post(f"/api/work-entry/{aid}/activate", headers=ent["h"])
    assert act.status_code == 200 and act.json()["mission_id"] == obj["mission_id"]
    sl = _slot_now(client, obj["slot_id"])
    assert sl["status"] == "filled" and sl["agent_id"] == ent["id"]
    # poster owns the minted mission and may end it -> active agreement completes
    end = client.post(f"/api/missions/{obj['mission_id']}/end", headers=owner["h"], json={})
    assert end.status_code == 200
    assert _store().get(aid)["state"] == "completed"


def test_post_origin_open_mode_mints_at_filing(client, monkeypatch):
    from app.deps import state
    owner, ent = _agent(client), _agent(client)
    pid = _post(owner["id"])
    real = state.kassa.get_post
    monkeypatch.setattr(state.kassa, "get_post",
                        lambda i: ({**real(i), "entry_mode": "open"} if real(i) else None))
    r = _file(client, ent, f"post:{pid}")
    assert r.status_code == 201, r.text
    a = r.json()["agreement"]
    assert a["governance"]["mode"] == "open" and a["state"] == "accepted"
    assert a["objects"]["slot_id"] and a["objects"]["mission_id"] == r.json()["mission_id"]
    assert _slot_now(client, a["objects"]["slot_id"])["status"] == "reserved"
    m = client.get(f"/api/missions/{a['objects']['mission_id']}").json()["mission"]
    assert m["status"] == "published"          # stays PUBLISHED until click 2
    act = client.post(f"/api/work-entry/{a['agreement_id']}/activate", headers=ent["h"])
    assert act.status_code == 200
    m = client.get(f"/api/missions/{a['objects']['mission_id']}").json()["mission"]
    assert m["status"] == "active"
    assert _slot_now(client, a["objects"]["slot_id"])["agent_id"] == ent["id"]


def test_post_origin_mint_failure_compensates(client, monkeypatch):
    owner, ent = _agent(client), _agent(client)
    pid = _post(owner["id"])
    aid = _file(client, ent, f"post:{pid}").json()["agreement"]["agreement_id"]
    import app.routes.missions as ms
    monkeypatch.setattr(ms, "_save_missions", lambda m: (_ for _ in ()).throw(OSError("disk full")))
    r = client.post(f"/api/work-entry/{aid}/accept", headers=owner["h"])
    assert r.status_code == 500
    monkeypatch.undo()
    assert _store().get(aid)["state"] == "terminated" and _store().evidence_gaps(aid)


# ── leave / end ──────────────────────────────────────────────────────────

def test_leave_active_slot_terminates_agreement(client):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    aid = _fill(client, ent, s["id"]).json()["agreement_id"]
    r = client.post("/api/slots/leave", headers=ent["h"], json={"slot_id": s["id"], "agent_id": ent["id"]})
    assert r.status_code == 200 and r.json()["vacated"] is True
    assert _store().get(aid)["state"] == "terminated"
    sl = _slot_now(client, s["id"])
    assert sl["status"] == "open" and sl["agreement_id"] is None
    # open-mode: the agent may fill again (a new Agreement)
    assert _fill(client, ent, s["id"]).status_code == 200


def test_leave_pending_entry_withdraws(client):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner, entry_mode="standard")
    aid = _file(client, ent, f"slot:{s['id']}").json()["agreement"]["agreement_id"]
    r = client.post("/api/slots/leave", headers=ent["h"], json={"slot_id": s["id"], "agent_id": ent["id"]})
    assert r.status_code == 200, r.text
    assert _store().get(aid)["state"] == "withdrawn"
    assert _slot_now(client, s["id"])["status"] == "open"


def test_mission_end_completes_active_agreements(client):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    aid = _fill(client, ent, s["id"]).json()["agreement_id"]
    r = client.post(f"/api/missions/{s['mission_id']}/end", headers=owner["h"], json={})
    assert r.status_code == 200
    assert _store().get(aid)["state"] == "completed"
    assert r.json()["agreements_completed"] == [aid]


def test_mission_end_without_agreements_unchanged(client):
    owner = _agent(client)
    s = _mk_slot(client, owner)
    r = client.post(f"/api/missions/{s['mission_id']}/end", headers=owner["h"], json={})
    assert r.status_code == 200 and r.json()["agreements_completed"] == []


# ── slot-create / bounty carry post_id / agreement refs ──────────────────

def test_slots_create_carries_post_and_agreement_refs(client):
    owner, other = _agent(client), _agent(client)
    pid = _post(owner["id"])
    s = _mk_slot(client, owner, post_id=pid, entry_mode="standard")
    assert s["post_id"] == pid
    m = client.get(f"/api/missions/{s['mission_id']}").json()["mission"]
    assert m["post_id"] == pid and m["entry_mode"] == "standard"
    # someone else's post / unknown post fail closed
    r = client.post("/api/slots/create", headers=other["h"],
                    json={"positions": [{"row": 0, "col": 0}], "post_id": pid})
    assert r.status_code == 403
    r = client.post("/api/slots/create", headers=owner["h"],
                    json={"positions": [{"row": 0, "col": 0}], "post_id": "K-nope"})
    assert r.status_code == 404
    r = client.post("/api/slots/create", headers=owner["h"],
                    json={"positions": [{"row": 0, "col": 0}], "agreement_id": "agr-workentry-nope"})
    assert r.status_code == 404


def test_bounty_carries_post_id_and_entry_mode(client):
    owner = _agent(client)
    pid = _post(owner["id"])
    r = client.post("/api/slots/bounty", headers=owner["h"],
                    json={"agent_id": owner["id"], "label": "B", "slots_needed": 1,
                          "post_id": pid, "entry_mode": "standard"})
    assert r.status_code == 200, r.text
    mid = r.json()["mission_id"]
    m = client.get(f"/api/missions/{mid}").json()["mission"]
    assert m["post_id"] == pid and m["entry_mode"] == "standard"
    assert all(s["post_id"] == pid and s["entry_mode"] == "standard" for s in r.json()["slots"])
    open_slot = next(s for s in r.json()["slots"] if s["status"] == "open")
    ent = _agent(client)
    assert _fill(client, ent, open_slot["id"]).status_code == 409
    # default bounty stays open and fillable
    r2 = client.post("/api/slots/bounty", headers=owner["h"],
                     json={"agent_id": owner["id"], "label": "B2", "slots_needed": 1})
    s2 = next(s for s in r2.json()["slots"] if s["status"] == "open")
    assert s2["entry_mode"] == "open" and _fill(client, ent, s2["id"]).status_code == 200
