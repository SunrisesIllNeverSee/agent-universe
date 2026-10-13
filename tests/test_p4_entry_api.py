"""P4 slice 3 -- Entry API (/api/work-entry): per-mode resolution, receipts, notifications,
dormancy (no auto-expiry), authority via the one principal resolver."""
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import signup_agent

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


def _agent(client):
    ip = f"10.8.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"s3-{uuid.uuid4().hex[:6]}", ip=ip).json()
    lg = client.post("/api/provision/login", json={"agent_id": d["agent_id"], "api_key": d["api_key"]},
                     headers={"x-forwarded-for": ip})
    return {"id": d["agent_id"], "h": {"Authorization": f"Bearer {d['api_key']}"},
            "jwt": {"Authorization": f"Bearer {lg.json()['token']}"}}


def _post(owner_agent_id=None, email="poster@example.com"):
    from app.deps import state
    pid = f"K-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC).isoformat()
    state.kassa.insert_post({"id": pid, "tab": "iso", "title": f"Post {pid}", "tag": "t", "body": "b",
                             "from_name": "P", "from_email": email, "created_at": now, "updated_at": now,
                             "poster_agent_id": owner_agent_id})
    return pid


def _slot(client, owner):
    r = client.post("/api/slots/create", headers=owner["h"],
                    json={"label": "S3", "positions": [{"row": 0, "col": 0}], "roles": ["primary"]})
    assert r.status_code == 200, r.text
    return r.json()["slots"][0]


def _file(client, who, ref, **kw):
    return client.post("/api/work-entry", json={"opportunity_ref": ref, "pitch": "I can do it", **kw}, headers=who["h"])


@pytest.fixture
def clock(monkeypatch):
    from app.deps import state
    box = {"offset": timedelta(0)}
    monkeypatch.setattr(state.workentry, "_clock", lambda: datetime.now(UTC) + box["offset"])
    return box


# ── standard mode (post) ─────────────────────────────────────────────────

def test_standard_full_path_with_receipts(client):
    owner, ent = _agent(client), _agent(client)
    pid = _post(owner["id"])
    r = _file(client, ent, f"post:{pid}", delivery_evidence_class=2)
    assert r.status_code == 201, r.text
    a = r.json()["agreement"]
    aid = a["agreement_id"]
    assert a["state"] == "pending" and a["governance"]["mode"] == "standard"
    assert a["objects"]["post_id"] == pid and a["objects"]["slot_id"] is None
    assert a["terms"]["delivery_evidence_class"] == "solution_proof"
    assert all(rc["seed_doi"] for rc in r.json()["receipts"])
    assert r.json()["receipts"][0]["credential_ref"] == f"{ent['id']}#api_key"

    acc = client.post(f"/api/work-entry/{aid}/accept", headers=owner["h"])
    assert acc.status_code == 200 and acc.json()["agreement"]["state"] == "accepted"
    assert acc.json()["receipt"]["seed_doi"] and acc.json()["receipt"]["credential_ref"].endswith("#api_key")
    act = client.post(f"/api/work-entry/{aid}/activate", headers=ent["jwt"])  # either door
    assert act.status_code == 200 and act.json()["agreement"]["state"] == "active"
    assert act.json()["receipt"]["credential_ref"] == f"{ent['id']}#jwt"
    got = client.get(f"/api/work-entry/{aid}", headers=ent["h"]).json()
    assert [h["transition"] for h in got["agreement"]["state_history"]] == \
        ["create", "file", "accept", "activate"]
    assert len(got["receipts"]) == 4


def test_standard_authority(client):
    owner, ent, stranger = _agent(client), _agent(client), _agent(client)
    aid = _file(client, ent, f"post:{_post(owner['id'])}").json()["agreement"]["agreement_id"]
    assert client.post(f"/api/work-entry/{aid}/accept", headers=stranger["h"]).status_code == 403
    assert client.post(f"/api/work-entry/{aid}/accept", headers=ent["h"]).status_code == 403
    assert client.post(f"/api/work-entry/{aid}/accept").status_code == 401
    # operator must name the principal it acts for
    assert client.post(f"/api/work-entry/{aid}/accept", headers=ADMIN, json={}).status_code == 403
    ok = client.post(f"/api/work-entry/{aid}/accept", headers=ADMIN, json={"acting_for": owner["id"]})
    assert ok.status_code == 200
    rc = ok.json()["receipt"]
    assert rc["actor"] == "operator:admin" and rc["acting_for"] == owner["id"]
    assert rc["credential_ref"] == "operator#admin_key"


def test_reject_needs_reason_then_terminal_and_reentry_supersedes(client):
    owner, ent = _agent(client), _agent(client)
    ref = f"post:{_post(owner['id'])}"
    aid = _file(client, ent, ref).json()["agreement"]["agreement_id"]
    assert client.post(f"/api/work-entry/{aid}/reject", headers=owner["h"], json={}).status_code == 400
    assert client.post(f"/api/work-entry/{aid}/reject", headers=owner["h"], json={"reason": "  "}).status_code == 400
    rj = client.post(f"/api/work-entry/{aid}/reject", headers=owner["h"], json={"reason": "scope mismatch"})
    assert rj.status_code == 200 and rj.json()["agreement"]["state"] == "rejected"
    assert rj.json()["agreement"]["outcome_reason"] == "scope mismatch"
    again = client.post(f"/api/work-entry/{aid}/accept", headers=owner["h"])
    assert again.status_code == 409 and "rejected" in again.text
    new = _file(client, ent, ref, supersedes=aid)
    assert new.status_code == 201 and new.json()["agreement"]["supersedes"] == aid
    assert client.get(f"/api/work-entry/{aid}", headers=ent["h"]).json()["agreement"]["superseded_by"] == \
        new.json()["agreement"]["agreement_id"]


def test_withdraw_only_entrant_and_only_pre_acceptance(client):
    owner, ent = _agent(client), _agent(client)
    aid = _file(client, ent, f"post:{_post(owner['id'])}").json()["agreement"]["agreement_id"]
    assert client.post(f"/api/work-entry/{aid}/withdraw", headers=owner["h"]).status_code == 403
    w = client.post(f"/api/work-entry/{aid}/withdraw", headers=ent["h"], json={"reason": "changed mind"})
    assert w.status_code == 200 and w.json()["agreement"]["state"] == "withdrawn"
    aid2 = _file(client, ent, f"post:{_post(owner['id'])}").json()["agreement"]["agreement_id"]
    client.post(f"/api/work-entry/{aid2}/accept", headers=owner["h"])
    late = client.post(f"/api/work-entry/{aid2}/withdraw", headers=ent["h"])
    assert late.status_code == 409 and "accepted" in late.text


def test_retire_by_either_party_is_terminal(client):
    owner, ent = _agent(client), _agent(client)
    for who in (owner, ent):
        aid = _file(client, ent, f"post:{_post(owner['id'])}").json()["agreement"]["agreement_id"]
        r = client.post(f"/api/work-entry/{aid}/retire", headers=who["h"], json={"reason": "done with it"})
        assert r.status_code == 200 and r.json()["agreement"]["state"] == "retired"
        assert client.post(f"/api/work-entry/{aid}/activate", headers=ent["h"]).status_code == 409
        assert client.get(f"/api/work-entry/{aid}", headers=ent["h"]).status_code == 200  # archive stays queryable
    s = _agent(client)
    aid = _file(client, ent, f"post:{_post(owner['id'])}").json()["agreement"]["agreement_id"]
    assert client.post(f"/api/work-entry/{aid}/retire", headers=s["h"]).status_code == 403


# ── open mode (slot) ─────────────────────────────────────────────────────

def test_open_mode_two_clicks_object_never_skipped(client):
    owner, ent = _agent(client), _agent(client)
    slot = _slot(client, owner)
    r = _file(client, ent, f"slot:{slot['id']}")
    assert r.status_code == 201, r.text
    a = r.json()["agreement"]
    assert a["state"] == "accepted" and a["governance"]["mode"] == "open"
    assert [h["transition"] for h in a["state_history"]] == ["create", "file", "resolve_open"]
    assert a["objects"]["slot_id"] == slot["id"] and a["objects"]["mission_id"] == slot["mission_id"]
    # click 1 does not bind the slot: it stays open until click 2 (binding is slice 4)
    assert client.get("/api/slots", headers=ent["h"]).json()["slots"] is not None
    sl = next(s for s in client.get("/api/slots").json()["slots"] if s["id"] == slot["id"])
    assert sl["status"] == "open"
    assert client.post(f"/api/work-entry/{a['agreement_id']}/accept", headers=owner["h"]).status_code == 409
    act = client.post(f"/api/work-entry/{a['agreement_id']}/activate", headers=ent["h"])
    assert act.status_code == 200 and act.json()["agreement"]["state"] == "active"


def test_slot_not_open_409_and_unknown_404(client):
    owner, ent = _agent(client), _agent(client)
    assert _file(client, ent, "slot:slot-nope").status_code == 404
    assert _file(client, ent, "post:K-nope").status_code == 404
    assert _file(client, ent, "mission:mission-nope").status_code == 404
    slot = _slot(client, owner)
    client.post("/api/slots/fill", headers=ent["h"], json={"slot_id": slot["id"], "agent_id": ent["id"]})
    other = _agent(client)
    assert _file(client, other, f"slot:{slot['id']}").status_code == 409


def test_open_mode_fill_still_works(client):
    """0.4.0 loop: /api/slots/fill is untouched by this slice."""
    owner, ent = _agent(client), _agent(client)
    slot = _slot(client, owner)
    r = client.post("/api/slots/fill", headers=ent["h"], json={"slot_id": slot["id"], "agent_id": ent["id"]})
    assert r.status_code == 200 and r.json()["filled"] is True


# ── constitutional ───────────────────────────────────────────────────────

def test_constitutional_accept_409_until_gate(client):
    owner, ent = _agent(client), _agent(client)
    slot = _slot(client, owner)
    r = _file(client, ent, f"slot:{slot['id']}", entry_mode="constitutional")  # may escalate
    a = r.json()["agreement"]
    assert a["state"] == "pending" and a["governance"]["mode"] == "constitutional"
    acc = client.post(f"/api/work-entry/{a['agreement_id']}/accept", headers=owner["h"])
    assert acc.status_code == 409 and acc.json()["error"] == "governance gate required"
    # a stranger still learns nothing about the gate: authority is checked first
    assert client.post(f"/api/work-entry/{a['agreement_id']}/accept", headers=_agent(client)["h"]).status_code == 403
    # rejection needs no gate
    rj = client.post(f"/api/work-entry/{a['agreement_id']}/reject", headers=owner["h"], json={"reason": "no"})
    assert rj.status_code == 200


def test_entrant_cannot_relax_mode(client):
    owner, ent = _agent(client), _agent(client)
    r = _file(client, ent, f"post:{_post(owner['id'])}", entry_mode="open")
    assert r.json()["agreement"]["governance"]["mode"] == "standard"


# ── email-only poster: magic link ────────────────────────────────────────

def _thread(post_id):
    from app.deps import state
    plain = secrets.token_urlsafe(32)
    tid = f"thr-{secrets.token_hex(6)}"
    now = datetime.now(UTC).isoformat()
    state.kassa.insert_thread({
        "thread_id": tid, "post_id": post_id, "post_tab": "iso", "post_title": "t", "agent_id": "x",
        "agent_name": "x", "poster_name": "P", "poster_email": "p@example.com",
        "magic_token": hashlib.sha256(plain.encode()).hexdigest(), "status": "open",
        "message_count": 0, "created_at": now, "updated_at": now})
    return tid, plain


def test_magic_link_poster_resolves_only_own_post(client):
    ent = _agent(client)
    pid, other_pid = _post(None), _post(None)
    aid = _file(client, ent, f"post:{pid}").json()["agreement"]["agreement_id"]
    _, tok = _thread(pid)
    _, other_tok = _thread(other_pid)
    assert client.post(f"/api/work-entry/{aid}/accept", headers={"X-Magic-Token": other_tok}).status_code == 403
    assert client.post(f"/api/work-entry/{aid}/accept", headers={"X-Magic-Token": "forged"}).status_code == 401
    # the link is never the entrant's door
    assert client.post(f"/api/work-entry/{aid}/withdraw", headers={"X-Magic-Token": tok}).status_code == 403
    ok = client.post(f"/api/work-entry/{aid}/accept", headers={"X-Magic-Token": tok})
    assert ok.status_code == 200, ok.text
    rc = ok.json()["receipt"]
    assert rc["credential_ref"].startswith("poster-link:") and rc["credential_ref"].endswith("#magic_link")
    assert rc["actor"].startswith("poster-link:") and rc["acting_for"] == f"poster:{pid}"
    assert client.get(f"/api/work-entry/{aid}", headers={"X-Magic-Token": tok}).status_code == 200


# ── idempotency / duplicates / validation ────────────────────────────────

def test_duplicate_409_names_existing_and_idempotent_retry(client):
    owner, ent = _agent(client), _agent(client)
    ref = f"post:{_post(owner['id'])}"
    k = uuid.uuid4().hex
    first = _file(client, ent, ref, idempotency_key=k)
    assert first.status_code == 201
    aid = first.json()["agreement"]["agreement_id"]
    replay = _file(client, ent, ref, idempotency_key=k)
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    assert replay.json()["agreement"]["agreement_id"] == aid
    dup = _file(client, ent, ref)
    assert dup.status_code == 409 and dup.json()["agreement_id"] == aid


def test_validation_and_auth(client):
    owner, ent = _agent(client), _agent(client)
    pid = _post(owner["id"])
    assert client.post("/api/work-entry", json={"opportunity_ref": f"post:{pid}"}).status_code == 401
    assert _file(client, owner, f"post:{pid}").status_code == 409  # own opportunity
    assert _file(client, ent, f"post:{pid}", delivery_evidence_class="gold").status_code == 422
    assert _file(client, ent, f"post:{pid}", entry_mode="weird").status_code == 422
    # operator cannot file (an entrant is a registered agent)
    assert client.post("/api/work-entry", headers=ADMIN, json={"opportunity_ref": f"post:{pid}"}).status_code == 403
    # not reachable as an admin-only write: unauthenticated gets 401 from the handler, not the edge guard
    r = client.post(f"/api/work-entry/agr-workentry-nope/accept")
    assert r.status_code == 401


def test_visibility_parties_only(client):
    owner, ent, stranger = _agent(client), _agent(client), _agent(client)
    aid = _file(client, ent, f"post:{_post(owner['id'])}").json()["agreement"]["agreement_id"]
    assert client.get(f"/api/work-entry/{aid}", headers=stranger["h"]).status_code == 403
    assert client.get(f"/api/work-entry/{aid}", headers=owner["h"]).status_code == 200
    assert client.get(f"/api/work-entry/agr-workentry-nope", headers=owner["h"]).status_code == 404
    assert client.get("/api/work-entry", headers=stranger["h"]).json()["count"] == 0
    mine = client.get("/api/work-entry", headers=ent["h"], params={"entrant": ent["id"]}).json()
    assert mine["count"] == 1
    by_opp = client.get("/api/work-entry", headers=owner["h"],
                        params={"opportunity_ref": mine["entries"][0]["opportunity_ref"]}).json()
    assert by_opp["count"] == 1
    assert client.get("/api/work-entry", headers=ADMIN, params={"owner": owner["id"]}).json()["count"] == 1


def test_provenance_failure_is_loud_and_leaves_no_agreement(client, monkeypatch):
    from app.deps import state
    owner, ent = _agent(client), _agent(client)
    ref = f"post:{_post(owner['id'])}"

    def boom(**kw):
        raise RuntimeError("seed store down")
    monkeypatch.setattr(state.workentry, "_seed_fn", boom)
    r = _file(client, ent, ref)
    assert r.status_code == 500 and r.json()["code"] == "provenance_failure" and r.json()["evidence_gap_id"]
    monkeypatch.undo()
    assert client.get("/api/work-entry", headers=ent["h"], params={"opportunity_ref": ref}).json()["count"] == 0


# ── notifications ────────────────────────────────────────────────────────

def test_transitions_notify_counterparty_inbox(client):
    from app.deps import state
    owner, ent = _agent(client), _agent(client)
    aid = _file(client, ent, f"post:{_post(owner['id'])}").json()["agreement"]["agreement_id"]
    assert any(m["kind"] == "work_entry_file" and m["ref_id"] == aid for m in state.inbox.load(owner["id"]))
    client.post(f"/api/work-entry/{aid}/accept", headers=owner["h"])
    assert any(m["kind"] == "work_entry_accept" and m["ref_id"] == aid for m in state.inbox.load(ent["id"]))
    assert not any(m["kind"] == "work_entry_accept" for m in state.inbox.load(owner["id"]))


def test_poster_email_on_transition(client, monkeypatch):
    sent = []
    import app.notifications as n
    monkeypatch.setattr(n, "_send_email", lambda to, subj, body, from_addr=None: sent.append((to, subj)) or True)
    owner, ent = _agent(client), _agent(client)
    pid = _post(None, email="realposter@example.org")
    aid = _file(client, ent, f"post:{pid}").json()["agreement"]["agreement_id"]
    _, tok = _thread(pid)
    client.post(f"/api/work-entry/{aid}/accept", headers={"X-Magic-Token": tok})
    assert len([s for s in sent if s[0] == "realposter@example.org"]) >= 2  # file + accept


# ── dormancy: no auto-expiry ─────────────────────────────────────────────

def test_48h_asks_poster_once_per_quiet_spell(client, clock):
    from app.deps import state
    owner, ent = _agent(client), _agent(client)
    aid = _file(client, ent, f"post:{_post(owner['id'])}").json()["agreement"]["agreement_id"]
    asks = lambda: [m for m in state.inbox.load(owner["id"]) if m["kind"] == "work_entry_ask_poster" and m["ref_id"] == aid]
    client.get(f"/api/work-entry/{aid}", headers=owner["h"])
    assert asks() == []
    clock["offset"] = timedelta(hours=49)
    g = client.get(f"/api/work-entry/{aid}", headers=owner["h"]).json()
    assert g["agreement"]["state"] == "pending"          # nothing expired
    assert len(asks()) == 1
    client.get("/api/work-entry", headers=owner["h"])
    client.post("/api/work-entry/sweep", headers=ADMIN)
    assert len(asks()) == 1                              # idempotent


def test_14_days_dormant_not_terminal_and_hidden_from_live(client, clock):
    owner, ent = _agent(client), _agent(client)
    aid = _file(client, ent, f"post:{_post(owner['id'])}").json()["agreement"]["agreement_id"]
    clock["offset"] = timedelta(days=15)
    lst = client.get("/api/work-entry", headers=ent["h"]).json()          # lazy evaluation on list
    assert aid not in [e["agreement_id"] for e in lst["entries"]]         # hidden from live lists
    inc = client.get("/api/work-entry", headers=ent["h"], params={"include_dormant": "true"}).json()
    row = next(e for e in inc["entries"] if e["agreement_id"] == aid)
    assert row["state"] == "dormant"
    assert any(h["transition"] == "go_dormant" and h["actor"] == "system" for h in row["state_history"])
    clock["offset"] = timedelta(days=400)                                 # never auto-expires
    assert client.get(f"/api/work-entry/{aid}", headers=ent["h"]).json()["agreement"]["state"] == "dormant"
    sw = client.post("/api/work-entry/sweep", headers=ADMIN)
    assert sw.status_code == 200 and aid not in sw.json()["dormant"]      # idempotent


def test_sweep_function_and_admin_only(client, clock):
    from app.routes.workentry import sweep_entries
    owner, ent = _agent(client), _agent(client)
    aid = _file(client, ent, f"post:{_post(owner['id'])}").json()["agreement"]["agreement_id"]
    clock["offset"] = timedelta(days=15)
    assert client.post("/api/work-entry/sweep", headers=ent["h"]).status_code == 403
    assert aid in sweep_entries()["dormant"]
    assert aid not in sweep_entries()["dormant"]


def test_any_activity_revives_dormant(client, clock):
    owner, ent = _agent(client), _agent(client)
    ref = f"post:{_post(owner['id'])}"
    a1 = _file(client, ent, ref).json()["agreement"]["agreement_id"]
    clock["offset"] = timedelta(days=15)
    client.get("/api/work-entry", headers=ent["h"])
    r = client.post(f"/api/work-entry/{a1}/activity", headers=ent["h"])
    assert r.status_code == 200 and r.json()["agreement"]["state"] == "pending"
    assert r.json()["receipt"]["transition"] == "revive"
    # owner's accept on a dormant entry is itself activity
    owner2, ent2 = _agent(client), _agent(client)
    a2 = _file(client, ent2, f"post:{_post(owner2['id'])}").json()["agreement"]["agreement_id"]
    clock["offset"] = timedelta(days=40)
    client.get("/api/work-entry", headers=ent2["h"])
    acc = client.post(f"/api/work-entry/{a2}/accept", headers=owner2["h"])
    assert acc.status_code == 200 and acc.json()["agreement"]["state"] == "accepted"
    assert [h["transition"] for h in acc.json()["agreement"]["state_history"]][-3:] == \
        ["go_dormant", "revive", "accept"]
    # entrant may retire a dormant entry (party decision) and it is then terminal + kept
    owner3, ent3 = _agent(client), _agent(client)
    a3 = _file(client, ent3, f"post:{_post(owner3['id'])}").json()["agreement"]["agreement_id"]
    clock["offset"] = timedelta(days=80)
    client.get("/api/work-entry", headers=ent3["h"])
    rt = client.post(f"/api/work-entry/{a3}/retire", headers=ent3["h"])
    assert rt.status_code == 200 and rt.json()["agreement"]["state"] == "retired"


# ── P5c G2 polish: entrant-facing wait + poster response time ────────────

def test_entrant_sees_waiting_on_poster_and_response_time(client, clock):
    owner, ent, ent2 = _agent(client), _agent(client), _agent(client)
    first = _file(client, ent, f"post:{_post(owner['id'])}").json()
    assert first["agreement"]["state"] == "pending"
    assert first["waiting_on"] == "poster"
    assert first["poster_response"]["label"] == "no history yet"
    aid = first["agreement"]["agreement_id"]
    g = client.get(f"/api/work-entry/{aid}", headers=ent["h"]).json()
    assert g["waiting_on"] == "poster" and g["poster_response"]["median_hours"] is None
    clock["offset"] = timedelta(hours=4)
    assert client.post(f"/api/work-entry/{aid}/accept", headers=owner["h"]).status_code == 200
    g = client.get(f"/api/work-entry/{aid}", headers=ent["h"]).json()
    assert g["waiting_on"] is None                              # no longer pending on the poster
    assert g["poster_response"]["label"] == "usually responds in ~4 h"
    second = _file(client, ent2, f"post:{_post(owner['id'])}").json()
    assert second["waiting_on"] == "poster"
    assert second["poster_response"] == {"samples": 1, "median_hours": 4.0, "label": "usually responds in ~4 h"}
    mine = client.get(f"/api/work-entry/opportunity/post:{second['agreement']['objects']['post_id']}",
                      headers=ent2["h"]).json()["mine"]
    assert mine["waiting_on"] == "poster" and mine["poster_response"]["label"] == "usually responds in ~4 h"
