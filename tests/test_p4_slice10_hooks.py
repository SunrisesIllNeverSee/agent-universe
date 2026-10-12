"""P4 slice 10 -- Entity/Node hooks (nullable, additive, open) + gate vote window."""
import json
from datetime import timedelta

import pytest

from tests.test_workentry_store import store, seeds, audit, clock, file_  # noqa: F401
from tests.test_p4_entry_api import _agent, _file, _post, _slot, clock as api_clock  # noqa: F401
from tests.test_p4_constitutional_gate import _constitutional, _meeting, _gate_motion, _vote

HOOKS = ("formation_id", "node_id", "entity_id", "relation_id", "economic_terms_id",
         "domain_id", "contribution_id", "escrow_id", "task_id")


# (a) principal typing
def test_principals_carry_principal_type_defaulted(store):
    a = file_(store, owner="poster:x@example.com", credential_refs={"entrant": "agent-a#api_key"})["agreement"]
    types = {p["role"]: p["principal_type"] for p in a["principals"]}
    assert types == {"entrant": "agent", "owner": "person"}


def test_principal_type_open_and_explicit(store):
    a = file_(store, principal_types={"entrant": "node_actor", "owner": "brand_new_kind"})["agreement"]
    assert {p["role"]: p["principal_type"] for p in a["principals"]} == {
        "entrant": "node_actor", "owner": "brand_new_kind"}
    assert store.get(a["agreement_id"])["principals"][1]["principal_type"] == "brand_new_kind"


def test_legacy_principals_backfilled_lazily_without_update(store):
    a = file_(store)["agreement"]
    aid = a["agreement_id"]
    legacy = [{"role": "entrant", "id": "agent-a", "credential_ref": None},
              {"role": "owner", "id": "agent-o", "credential_ref": None}]
    store._conn.execute("UPDATE agreements SET principals_json=? WHERE agreement_id=?",
                        (json.dumps(legacy), aid))
    got = store.get(aid)
    assert [p["principal_type"] for p in got["principals"]] == ["agent", "agent"]
    raw = store._conn.execute("SELECT principals_json FROM agreements WHERE agreement_id=?", (aid,)).fetchone()[0]
    assert "principal_type" not in raw   # derived on read, never written back


def test_receipts_expose_actor_types(store):
    r = file_(store)["receipts"]
    assert r[0]["actor_type"] == "agent" and r[2 - 1]["actor_type"] == "agent"
    st = store.receipts(file_(store, entrant="agent-b", mode="open")["agreement"]["agreement_id"])
    assert any(x["actor"] == "system" and x["actor_type"] == "platform" for x in st)


# (b) object reference slots
def test_object_hook_slots_default_null_and_round_trip(store):
    a = file_(store)["agreement"]
    for k in HOOKS:
        assert k in a["objects"] and a["objects"][k] is None
    vals = {k: f"{k}-1" for k in HOOKS} | {"future_ref": "x"}
    b = store.file_entry(entrant="e2", owner="o2", opportunity_ref="post:K-2", entry_mode="standard",
                         objects={"post_id": "K-2", **vals})["agreement"]
    assert all(store.get(b["agreement_id"])["objects"][k] == v for k, v in vals.items())


def test_api_file_accepts_and_returns_object_refs(client):
    owner, ent = _agent(client), _agent(client)
    pid = _post(owner["id"])
    r = _file(client, ent, f"post:{pid}", objects={"node_id": "n-1", "entity_id": "e-1", "weird": 5},
              participation_ref="part-1")
    assert r.status_code == 201, r.text
    aid = r.json()["agreement"]["agreement_id"]
    got = client.get(f"/api/work-entry/{aid}", headers=ent["h"]).json()["agreement"]
    assert got["objects"]["node_id"] == "n-1" and got["objects"]["entity_id"] == "e-1"
    assert got["objects"]["weird"] == 5 and got["objects"]["formation_id"] is None
    assert got["objects"]["post_id"] == pid     # the opportunity's own binding wins
    assert got["participation_ref"] == "part-1"
    assert got["principals"][0]["principal_type"] == "agent"


def test_mcp_file_accepts_object_refs(client):
    import asyncio
    from tests.test_p4_mcp_entry import _call, _key
    o, e = _key(client), _key(client)
    pid = _post(o["id"])
    f = _call("entry.file", api_key=e["key"], opportunity_ref=f"post:{pid}", pitch="hi",
              objects={"node_id": "n-9"}, participation_ref="p-9", agreement_class="mission_work")
    assert f["ok"], f
    a = f["agreement"]
    assert a["objects"]["node_id"] == "n-9" and a["participation_ref"] == "p-9"
    assert a["agreement_class"] == "mission_work"


# (c) participation_ref + open class
def test_participation_ref_and_open_class(store):
    a = file_(store)["agreement"]
    assert a["participation_ref"] is None and a["agreement_class"] == "WorkEntryAgreement"
    b = store.file_entry(entrant="e3", owner="o3", opportunity_ref="post:K-3", entry_mode="standard",
                         participation_ref="pp-1", agreement_class="ContributionAgreement",
                         class_version=7)["agreement"]
    assert b["participation_ref"] == "pp-1"
    assert (b["agreement_class"], b["class_version"]) == ("ContributionAgreement", 7)
    assert store.get(b["agreement_id"])["participation_ref"] == "pp-1"


def test_participation_ref_column_added_to_existing_db(tmp_path):
    import sqlite3
    from app.workentry_store import WorkEntryStore
    s = WorkEntryStore(tmp_path / "w.db")
    s.close()
    c = sqlite3.connect(tmp_path / "w.db")
    cols = {r[1] for r in c.execute("PRAGMA table_info(agreements)")}
    assert "participation_ref" in cols
    s2 = WorkEntryStore(tmp_path / "w.db")  # guarded: re-open does not fail
    s2.close()


# (d) seeds
def test_seed_metadata_hooks_and_genesis_kind(store, seeds):
    store.file_entry(entrant="e4", owner="o4", opportunity_ref="post:K-4", entry_mode="standard",
                     objects={"node_id": "n-4", "entity_id": "en-4", "formation_id": "f-4"})
    md = [c["metadata"] for c in seeds.calls]
    assert md[0]["kind"] == "work_entry_genesis" and md[0]["kind"] != "node_root"
    assert all(m["node_id"] == "n-4" and m["entity_id"] == "en-4" and m["formation_id"] == "f-4" for m in md)
    assert md[1]["kind"] != "work_entry_genesis"


def test_seed_metadata_omits_absent_hooks(store, seeds):
    file_(store)
    assert all("node_id" not in c["metadata"] for c in seeds.calls)


# (e) settlement-ready receipts
def test_receipts_expose_economic_terms_and_escrow(store):
    b = store.file_entry(entrant="e5", owner="o5", opportunity_ref="post:K-5", entry_mode="standard",
                         objects={"economic_terms_id": "et-1", "escrow_id": "es-1"})
    assert all(r["economic_terms_id"] == "et-1" and r["escrow_id"] == "es-1" for r in b["receipts"])
    plain = file_(store, entrant="e6", opp="post:K-6")
    assert all(r["economic_terms_id"] is None and r["escrow_id"] is None for r in plain["receipts"])
    t = store.accept(b["agreement"]["agreement_id"], actor="o5")
    assert t["receipt"]["escrow_id"] == "es-1"


# (g) gate votes at/after closes_at
def test_gate_vote_rejected_after_window(client, api_clock):
    owner, ent, aid = _constitutional(client)
    third = _agent(client)
    mid = _meeting(client, owner, [ent, third])
    mo = _gate_motion(client, owner, mid, aid).json()
    _vote(client, owner, mid, mo["id"], "yea")                      # inside the window: fine
    api_clock["offset"] = timedelta(hours=25)
    r = client.post(f"/api/governance/meeting/{mid}/vote", headers=ent["h"],
                    json={"voter": ent["id"], "motion_id": mo["id"], "vote": "yea"})
    assert r.status_code == 409, r.text
