"""P4 slice 6 -- Agreement-bound deploy.

Mission-scoped deploy: ARM DEPLOY preflight (GET) + deploy transition (POST) that requires an active
Agreement whose principal holds deploy authority on the mission. The gate follows the mission's
entry_mode (open: none; standard: the resolver; constitutional: the slice-5 governance gate).
Unavailable while frozen; emits a durable receipt + Seed. The global POST /api/deploy is unchanged.
"""
from datetime import timedelta

from tests.test_p4_entry_api import ADMIN, _agent, _file, _slot, clock  # noqa: F401
from tests.test_p4_constitutional_gate import _setup_gate, _sync, _accept
from tests.test_p4_slot_binding import _mk_slot, _fill


def _store():
    from app.deps import state
    return state.workentry


def _pre(mid):
    return f"/api/work-entry/mission/{mid}/deploy/preflight"


def _dep(mid):
    return f"/api/work-entry/mission/{mid}/deploy"


def _open_mission(client):
    """owner + entrant with an ACTIVE open-mode agreement; returns (owner, ent, mission_id, aid)."""
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner)
    r = _fill(client, ent, s["id"])
    assert r.status_code == 200, r.text
    return owner, ent, s["mission_id"], r.json()["agreement_id"]


def _standard_mission(client):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner, entry_mode="standard")
    aid = _file(client, ent, f"slot:{s['id']}").json()["agreement"]["agreement_id"]
    assert client.post(f"/api/work-entry/{aid}/accept", headers=owner["h"]).status_code == 200
    assert client.post(f"/api/work-entry/{aid}/activate", headers=ent["h"]).status_code == 200
    return owner, ent, s["mission_id"], aid


def _set_mission(mission_id, **fields):
    import app.routes.missions as ms
    missions = ms._load_missions()
    m = next(x for x in missions if x["id"] == mission_id)
    m.update(fields)
    ms._save_missions(missions)


# ── authority: no agreement -> 403 ───────────────────────────────────────

def test_deploy_without_agreement_is_403(client):
    owner = _agent(client)
    s = _mk_slot(client, owner)                      # mission exists, nobody has entered
    r = client.post(_dep(s["mission_id"]), headers=owner["h"], json={})
    assert r.status_code == 403, r.text
    assert "agreement" in r.text.lower()
    assert client.post(_dep(s["mission_id"]), json={}).status_code == 401
    assert client.post(_dep("mission-nope"), headers=owner["h"], json={}).status_code == 404


def test_stranger_and_entrant_hold_no_deploy_authority(client):
    owner, ent, mid, aid = _open_mission(client)
    stranger = _agent(client)
    assert client.post(_dep(mid), headers=stranger["h"], json={}).status_code == 403
    assert client.post(_dep(mid), headers=ent["h"], json={}).status_code == 403   # entrant != deploy authority
    assert _store().deployments(aid) == []


def test_operator_must_name_the_principal_it_acts_for(client):
    owner, ent, mid, aid = _open_mission(client)
    assert client.post(_dep(mid), headers=ADMIN, json={}).status_code == 403
    assert client.post(_dep(mid), headers=ADMIN, json={"acting_for": ent["id"]}).status_code == 403
    assert _store().deployments(aid) == []


def test_non_active_agreement_does_not_authorise(client):
    owner, ent = _agent(client), _agent(client)
    s = _mk_slot(client, owner, entry_mode="standard")
    aid = _file(client, ent, f"slot:{s['id']}").json()["agreement"]["agreement_id"]   # pending
    assert client.post(_dep(s["mission_id"]), headers=owner["h"], json={}).status_code == 403
    client.post(f"/api/work-entry/{aid}/accept", headers=owner["h"])                   # accepted, not active
    assert client.post(_dep(s["mission_id"]), headers=owner["h"], json={}).status_code == 403


# ── right agreement -> receipt + seed ────────────────────────────────────

def test_open_mode_deploy_emits_receipt_and_seed(client):
    owner, ent, mid, aid = _open_mission(client)
    r = client.post(_dep(mid), headers=owner["h"], json={"note": "go"})
    assert r.status_code == 201, r.text
    body = r.json()
    rc = body["receipt"]
    assert rc["seed_doi"] and rc["receipt_id"] and rc["audit_hash"]
    assert rc["agreement_id"] == aid and rc["mission_id"] == mid and rc["transition"] == "deploy"
    assert rc["actor"] == owner["id"] and rc["credential_ref"] == f"{owner['id']}#api_key"
    assert rc["entry_mode"] == "open" and rc["gate_id"] is None
    assert body["deployed"] is True and body["agreement_id"] == aid
    # durable + queryable; the Seed chains onto the agreement's lineage
    assert _store().deployments(aid)[0]["receipt_id"] == rc["receipt_id"]
    got = client.get(f"/api/work-entry/{aid}", headers=owner["h"]).json()
    assert got["agreement"]["state"] == "active"                    # deploy is not an agreement state change
    assert [h["transition"] for h in got["agreement"]["state_history"]][-1] == "activate"


def test_deploy_via_jwt_door(client):
    owner, ent, mid, aid = _open_mission(client)
    r = client.post(_dep(mid), headers=owner["jwt"], json={})
    assert r.status_code == 201, r.text
    assert r.json()["receipt"]["credential_ref"] == f"{owner['id']}#jwt"


def test_idempotent_replay_returns_original_receipt(client):
    owner, ent, mid, aid = _open_mission(client)
    a = client.post(_dep(mid), headers=owner["h"], json={"idempotency_key": "k1"})
    b = client.post(_dep(mid), headers=owner["h"], json={"idempotency_key": "k1"})
    assert a.status_code == 201 and b.status_code == 200
    assert a.json()["receipt"]["receipt_id"] == b.json()["receipt"]["receipt_id"]
    assert b.json()["replayed"] is True
    assert len(_store().deployments(aid)) == 1
    c = client.post(_dep(mid), headers=owner["h"], json={})          # a fresh deploy is a new receipt
    assert c.status_code == 201 and c.json()["receipt"]["receipt_id"] != a.json()["receipt"]["receipt_id"]


def test_standard_mode_resolver_deploys_operator_only_for_named_owner(client):
    owner, ent, mid, aid = _standard_mission(client)
    r = client.post(_dep(mid), headers=ADMIN, json={"acting_for": owner["id"]})
    assert r.status_code == 201, r.text
    rc = r.json()["receipt"]
    assert rc["actor"] == "operator:admin" and rc["acting_for"] == owner["id"]
    assert rc["credential_ref"] == "operator#admin_key" and rc["entry_mode"] == "standard"
    assert client.post(_dep(mid), headers=owner["h"], json={}).status_code == 201


# ── constitutional gate (slice 5) ────────────────────────────────────────

def test_constitutional_deploy_carries_the_governance_gate(client, clock):
    owner, ent, aid, mid, motion_id = _setup_gate(client)
    clock["offset"] = timedelta(hours=25)
    _sync(client, owner, aid)
    assert client.post(f"/api/work-entry/{aid}/gate/countersign", headers=ADMIN).status_code == 200
    assert _accept(client, owner, aid).status_code == 200
    assert client.post(f"/api/work-entry/{aid}/activate", headers=ent["h"]).status_code == 200
    a = client.get(f"/api/work-entry/{aid}", headers=owner["h"]).json()["agreement"]
    mission_id = a["objects"]["mission_id"]
    pre = client.get(_pre(mission_id), headers=owner["h"]).json()
    assert pre["entry_mode"] == "constitutional" and pre["gate"]["required"] is True
    assert pre["gate"]["satisfied"] is True and pre["can_deploy"] is True
    r = client.post(_dep(mission_id), headers=owner["h"], json={})
    assert r.status_code == 201, r.text
    assert r.json()["receipt"]["gate_id"] == pre["gate"]["gate_id"] and r.json()["receipt"]["gate_id"]


def test_mission_mode_constitutional_without_a_satisfied_gate_is_409(client):
    owner, ent, mid, aid = _open_mission(client)          # agreement filed under open
    _set_mission(mid, entry_mode="constitutional")         # the mission's mode now demands the gate
    pre = client.get(_pre(mid), headers=owner["h"]).json()
    assert pre["entry_mode"] == "constitutional" and pre["gate"]["satisfied"] is False
    assert pre["can_deploy"] is False and pre["blocking"] == "governance_gate_required"
    r = client.post(_dep(mid), headers=owner["h"], json={})
    assert r.status_code == 409 and r.json()["code"] == "governance_gate_required"
    assert _store().deployments(aid) == []


# ── frozen -> 409 ────────────────────────────────────────────────────────

def test_frozen_mission_is_409(client):
    owner, ent, mid, aid = _open_mission(client)
    _set_mission(mid, frozen=True)
    r = client.post(_dep(mid), headers=owner["h"], json={})
    assert r.status_code == 409 and r.json()["code"] == "mission_frozen"
    pre = client.get(_pre(mid), headers=owner["h"]).json()
    assert pre["frozen"] is True and pre["can_deploy"] is False and pre["blocking"] == "mission_frozen"
    assert _store().deployments(aid) == []
    _set_mission(mid, frozen=False)                       # unfreeze: available again
    assert client.post(_dep(mid), headers=owner["h"], json={}).status_code == 201


def test_frozen_does_not_leak_to_unauthorised_callers(client):
    owner, ent, mid, aid = _open_mission(client)
    _set_mission(mid, frozen=True)
    assert client.post(_dep(mid), headers=_agent(client)["h"], json={}).status_code == 403


def test_ended_mission_is_409_not_deployable(client):
    owner, ent, mid, aid = _open_mission(client)
    _set_mission(mid, status="cancelled")
    r = client.post(_dep(mid), headers=owner["h"], json={})
    assert r.status_code == 409 and r.json()["code"] == "mission_not_deployable"


# ── preflight ────────────────────────────────────────────────────────────

def test_preflight_lists_agreements_mode_gate_and_frozen(client):
    owner, ent, mid, aid = _open_mission(client)
    pre = client.get(_pre(mid), headers=owner["h"])
    assert pre.status_code == 200, pre.text
    p = pre.json()
    assert p["mission_id"] == mid and p["entry_mode"] == "open" and p["frozen"] is False
    assert p["gate"]["required"] is False and p["gate"]["satisfied"] is True
    assert p["can_deploy"] is True and p["blocking"] is None and p["agreement_id"] == aid
    ag = p["agreements"][0]
    assert ag["agreement_id"] == aid and ag["state"] == "active" and ag["holds_deploy_authority"] is True
    assert ag["owner"] == owner["id"] and ag["entrant"] == ent["id"]
    # the entrant reads it but holds no authority; a stranger may not read it
    pe = client.get(_pre(mid), headers=ent["h"]).json()
    assert pe["can_deploy"] is False and pe["blocking"] == "no_deploy_authority"
    assert client.get(_pre(mid), headers=_agent(client)["h"]).status_code == 403
    assert client.get(_pre(mid)).status_code == 401
    assert client.get(_pre("mission-nope"), headers=owner["h"]).status_code == 404
    # preflight is read-only
    assert _store().deployments(aid) == []


def test_preflight_without_agreement_says_so(client):
    owner = _agent(client)
    s = _mk_slot(client, owner)
    p = client.get(_pre(s["mission_id"]), headers=owner["h"]).json()
    assert p["agreements"] == [] and p["can_deploy"] is False and p["blocking"] == "no_active_agreement"


# ── provenance is loud ───────────────────────────────────────────────────

def test_seed_failure_rolls_back_loudly(client, monkeypatch):
    owner, ent, mid, aid = _open_mission(client)

    def boom(**kw):
        raise RuntimeError("seed store down")
    monkeypatch.setattr(_store(), "_seed_fn", boom)
    r = client.post(_dep(mid), headers=owner["h"], json={})
    assert r.status_code == 500 and r.json()["code"] == "provenance_failure" and r.json()["evidence_gap_id"]
    assert _store().deployments(aid) == []                  # no receipt without provenance
    gaps = _store().evidence_gaps(aid)
    assert any(g["attempted_transition"] == "deploy" and g["stage"] == "seed" for g in gaps)


# ── the global deploy is untouched ───────────────────────────────────────

def test_global_deploy_stays_operator_only_and_unchanged(client):
    owner, ent, mid, aid = _open_mission(client)
    body = {"objective": "global-deploy-untouched"}
    assert client.post("/api/deploy", json=body).status_code == 403
    ok = client.post("/api/deploy", json=body, headers=ADMIN)
    assert ok.status_code == 200, ok.text
    assert _store().deployments(aid) == []                  # global deploy writes no agreement receipt
