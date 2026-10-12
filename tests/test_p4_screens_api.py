"""P4 slice 7 -- server read models behind the screens.

GET /api/work-entry/opportunity/{ref}  -- terms/mode preview for the Enter flow (every value the
                                          screen shows comes from here; public, optionally personalised).
GET /api/work-entry/mission/{id}       -- the Agreement node + Acceptance record + receipts for
                                          Mission Control (party or operator only).
"""
import uuid

from tests.test_p4_entry_api import ADMIN, _agent, _file, _post, _slot  # noqa: F401
from tests.test_p4_slot_binding import _mk_slot, _fill


# ── opportunity preview ──────────────────────────────────────────────────

def test_preview_post_is_public_and_server_derived(client):
    owner = _agent(client)
    pid = _post(owner["id"])
    r = client.get(f"/api/work-entry/opportunity/post:{pid}")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["ref"] == f"post:{pid}" and d["kind"] == "post"
    assert d["entry_mode"] == "standard"
    assert d["title"] == f"Post {pid}"
    assert [c["id"] for c in d["delivery_evidence_classes"]] == [
        "solution", "solution_proof", "solution_proof_work_access"]
    assert d["acceptance"]["resolver"] == "owner"
    assert d["objects"]["post_id"] == pid
    assert d["caller"] is None and d["mine"] is None
    # the owner's id is not disclosed to the public preview
    assert owner["id"] not in r.text


def test_preview_bare_post_id_and_missing(client):
    pid = _post(None)
    assert client.get(f"/api/work-entry/opportunity/{pid}").json()["ref"] == f"post:{pid}"
    assert client.get("/api/work-entry/opportunity/post:K-nope").status_code == 404


def test_preview_slot_modes_and_acceptance_text(client):
    owner = _agent(client)
    s_open = _mk_slot(client, owner)
    s_std = _mk_slot(client, owner, entry_mode="standard")
    o = client.get(f"/api/work-entry/opportunity/slot:{s_open['id']}").json()
    st = client.get(f"/api/work-entry/opportunity/slot:{s_std['id']}").json()
    assert o["entry_mode"] == "open" and o["acceptance"]["kind"] == "auto_accept"
    assert o["acceptance"]["clicks"] == 2
    assert st["entry_mode"] == "standard" and st["acceptance"]["kind"] == "resolver"
    assert st["objects"]["slot_id"] == s_std["id"]


def test_preview_personalised_for_caller(client):
    owner, ent = _agent(client), _agent(client)
    pid = _post(owner["id"])
    ref = f"post:{pid}"
    d = client.get(f"/api/work-entry/opportunity/{ref}", headers=ent["h"]).json()
    assert d["caller"] == {"principal": ent["id"], "credential_type": "api_key", "own_opportunity": False}
    assert d["mine"] is None
    own = client.get(f"/api/work-entry/opportunity/{ref}", headers=owner["h"]).json()
    assert own["caller"]["own_opportunity"] is True
    filed = _file(client, ent, ref).json()["agreement"]
    mine = client.get(f"/api/work-entry/opportunity/{ref}", headers=ent["jwt"]).json()["mine"]
    assert mine["agreement_id"] == filed["agreement_id"] and mine["state"] == "pending"
    # a forged credential fails closed rather than falling back to the public view
    bad = client.get(f"/api/work-entry/opportunity/{ref}", headers={"Authorization": "Bearer nope"})
    assert bad.status_code == 401


# ── mission read model ───────────────────────────────────────────────────

def test_mission_read_model_for_parties(client):
    owner, ent, stranger = _agent(client), _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    aid = _fill(client, ent, s["id"]).json()["agreement_id"]
    mid = s["mission_id"]
    r = client.get(f"/api/work-entry/mission/{mid}", headers=ent["h"])
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["mission_id"] == mid and d["entry_mode"] == "open"
    [row] = d["agreements"]
    assert row["agreement"]["agreement_id"] == aid and row["agreement"]["state"] == "active"
    assert [x["transition"] for x in row["receipts"]][-1] == "activate"
    assert all(x["seed_doi"] for x in row["receipts"])
    assert row["acceptance"]["terms_accepted_at"] and row["acceptance"]["active_at"]
    assert row["acceptance"]["accepted_by"]
    assert d["node"] == {"label": "terms_accepted → active", "state": "active", "agreement_id": aid}
    assert client.get(f"/api/work-entry/mission/{mid}", headers=owner["jwt"]).status_code == 200
    assert client.get(f"/api/work-entry/mission/{mid}", headers=ADMIN).status_code == 200
    assert client.get(f"/api/work-entry/mission/{mid}", headers=stranger["h"]).status_code == 403
    assert client.get(f"/api/work-entry/mission/{mid}").status_code == 401
    assert client.get("/api/work-entry/mission/mission-nope", headers=ent["h"]).status_code == 404


def test_mission_read_model_pending_has_no_active_time(client):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner, entry_mode="standard")
    aid = _file(client, ent, f"slot:{s['id']}").json()["agreement"]["agreement_id"]
    # not yet bound to the mission until acceptance mints/binds; the slot's mission is the object
    d = client.get(f"/api/work-entry/mission/{s['mission_id']}", headers=owner["h"]).json()
    ids = [r["agreement"]["agreement_id"] for r in d["agreements"]]
    assert aid in ids
    row = next(r for r in d["agreements"] if r["agreement"]["agreement_id"] == aid)
    assert row["agreement"]["state"] == "pending" and row["acceptance"]["terms_accepted_at"] is None
    assert d["node"]["state"] == "pending"
