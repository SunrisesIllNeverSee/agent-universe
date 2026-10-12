"""P4 slice 1 - Agreement core (WorkEntryAgreement store + state machine).

Pure-python service layer tests: no HTTP. Seed and audit writers are injected
fakes so provenance failure can be forced.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, UTC

import pytest

from app.workentry_store import (
    AuthorityError,
    DuplicateEntryError,
    IdempotencyConflict,
    InvalidTransition,
    NotFound,
    ProvenanceError,
    TERMINAL_STATES,
    WorkEntryStore,
    WorkEntryError,
)


class FakeSeeds:
    def __init__(self):
        self.calls = []
        self.fail = False

    def __call__(self, **kw):
        if self.fail:
            raise RuntimeError("seed disk full")
        self.calls.append(kw)
        return {"doi": f"10.test/seed-{len(self.calls)}", "content_hash": "h", "created_at": "t"}


class FakeAudit:
    def __init__(self):
        self.calls = []
        self.fail = False

    def __call__(self, component, action, detail):
        if self.fail:
            raise RuntimeError("audit down")
        self.calls.append((component, action, detail))
        return f"audithash{len(self.calls):04d}"


class Clock:
    def __init__(self):
        self.now = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)

    def __call__(self):
        return self.now

    def advance(self, **kw):
        self.now += timedelta(**kw)


@pytest.fixture
def seeds():
    return FakeSeeds()


@pytest.fixture
def audit():
    return FakeAudit()


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def store(tmp_path, seeds, audit, clock):
    return WorkEntryStore(tmp_path / "workentry.db", seed_fn=seeds, audit_fn=audit, clock=clock)


def file_(store, mode="standard", entrant="agent-a", owner="agent-o", opp="post:K-1", key=None, **kw):
    return store.file_entry(
        entrant=entrant, owner=owner, opportunity_ref=opp, entry_mode=mode,
        objects={"post_id": "K-1"}, terms={"pitch": "I can do it"},
        idempotency_key=key, **kw,
    )


# ── creation / modes ────────────────────────────────────────────────────────

def test_standard_files_to_pending(store):
    r = file_(store)
    a = r["agreement"]
    assert a["state"] == "pending"
    assert a["agreement_id"].startswith("agr-workentry-")
    assert a["agreement_class"] == "WorkEntryAgreement"
    assert a["governance"]["mode"] == "standard"
    assert a["governance"]["resolution_mode"] == "pending"
    assert [p["role"] for p in a["principals"]] == ["entrant", "owner"]
    assert a["objects"]["post_id"] == "K-1"
    assert a["genesis_seed_doi"]
    assert [h["transition"] for h in a["state_history"]] == ["create", "file"]
    assert [x["transition"] for x in r["receipts"]] == ["create", "file"]


def test_constitutional_files_to_pending(store):
    a = file_(store, mode="constitutional")["agreement"]
    assert a["state"] == "pending"
    assert a["governance"]["resolution_mode"] == "pending"


def test_open_mode_resolves_immediately_to_accepted(store):
    r = file_(store, mode="open")
    a = r["agreement"]
    assert a["state"] == "accepted"
    assert a["governance"]["resolution_mode"] == "immediate"
    # pending is modeled, not elided
    assert [h["to"] for h in a["state_history"]] == ["intent", "pending", "accepted"]
    assert [x["transition"] for x in r["receipts"]] == ["create", "file", "resolve_open"]
    # mission stays unbound until click 2
    r2 = store.activate(a["agreement_id"], actor="agent-a")
    assert r2["agreement"]["state"] == "active"


def test_invalid_mode_rejected(store):
    with pytest.raises(WorkEntryError) as e:
        file_(store, mode="bogus")
    assert e.value.status == 400


@pytest.mark.parametrize("kw", [{"entrant": ""}, {"owner": ""}, {"opp": ""}])
def test_required_fields(store, kw):
    with pytest.raises(WorkEntryError) as e:
        file_(store, **kw)
    assert e.value.status == 400


# ── allowed transitions ─────────────────────────────────────────────────────

def test_full_happy_path(store):
    aid = file_(store)["agreement"]["agreement_id"]
    assert store.accept(aid, actor="agent-o")["agreement"]["state"] == "accepted"
    assert store.activate(aid, actor="agent-a")["agreement"]["state"] == "active"
    assert store.complete(aid, actor="agent-o")["agreement"]["state"] == "completed"
    a = store.get(aid)
    assert [h["to"] for h in a["state_history"]] == [
        "intent", "pending", "accepted", "active", "completed"]


def test_reject_requires_reason_and_records_it(store):
    aid = file_(store)["agreement"]["agreement_id"]
    with pytest.raises(WorkEntryError) as e:
        store.reject(aid, actor="agent-o", reason="")
    assert e.value.status == 400
    r = store.reject(aid, actor="agent-o", reason="out of scope")
    assert r["agreement"]["state"] == "rejected"
    assert r["receipt"]["reason"] == "out of scope"
    assert store.get(aid)["outcome_reason"] == "out of scope"


def test_withdraw_from_pending(store):
    aid = file_(store)["agreement"]["agreement_id"]
    assert store.withdraw(aid, actor="agent-a")["agreement"]["state"] == "withdrawn"


def test_withdraw_only_by_entrant(store):
    aid = file_(store)["agreement"]["agreement_id"]
    with pytest.raises(AuthorityError):
        store.withdraw(aid, actor="agent-o")


def test_accept_only_by_owner_or_operator_for_owner(store):
    aid = file_(store)["agreement"]["agreement_id"]
    with pytest.raises(AuthorityError):
        store.accept(aid, actor="agent-a")
    with pytest.raises(AuthorityError):
        store.accept(aid, actor="operator:op1")  # no acting_for
    with pytest.raises(AuthorityError):
        store.accept(aid, actor="operator:op1", acting_for="someone-else")
    r = store.accept(aid, actor="operator:op1", acting_for="agent-o")
    assert r["agreement"]["state"] == "accepted"
    assert r["receipt"]["actor"] == "operator:op1"
    assert r["receipt"]["acting_for"] == "agent-o"


def test_terminate_from_active_and_accepted(store):
    a1 = file_(store, opp="post:1")["agreement"]["agreement_id"]
    store.accept(a1, actor="agent-o"); store.activate(a1, actor="agent-a")
    assert store.terminate(a1, actor="agent-a", reason="leaving")["agreement"]["state"] == "terminated"
    a2 = file_(store, opp="post:2")["agreement"]["agreement_id"]
    store.accept(a2, actor="agent-o")
    assert store.terminate(a2, actor="agent-o", reason="gone")["agreement"]["state"] == "terminated"


def test_retire_by_either_party_only(store):
    a1 = file_(store, opp="post:1")["agreement"]["agreement_id"]
    assert store.retire(a1, actor="agent-o", reason="filled elsewhere")["agreement"]["state"] == "retired"
    a2 = file_(store, opp="post:2")["agreement"]["agreement_id"]
    assert store.retire(a2, actor="agent-a")["agreement"]["state"] == "retired"
    a3 = file_(store, opp="post:3")["agreement"]["agreement_id"]
    with pytest.raises(AuthorityError):
        store.retire(a3, actor="stranger")


# ── disallowed transitions ──────────────────────────────────────────────────

DISALLOWED = [
    # (setup path, method, kwargs-actor)
    ("pending", "activate", "agent-a"),
    ("pending", "complete", "agent-o"),
    ("pending", "terminate", "agent-o"),
    ("accepted", "accept", "agent-o"),
    ("accepted", "reject", "agent-o"),
    ("accepted", "withdraw", "agent-a"),
    ("accepted", "complete", "agent-o"),
    ("accepted", "retire", "agent-o"),
    ("active", "accept", "agent-o"),
    ("active", "reject", "agent-o"),
    ("active", "withdraw", "agent-a"),
    ("active", "activate", "agent-a"),
    ("active", "retire", "agent-o"),
]


def _drive(store, target, opp):
    aid = file_(store, opp=opp)["agreement"]["agreement_id"]
    if target in ("accepted", "active"):
        store.accept(aid, actor="agent-o")
    if target == "active":
        store.activate(aid, actor="agent-a")
    return aid


@pytest.mark.parametrize("state,method,actor", DISALLOWED)
def test_disallowed_transition_409_names_state(store, state, method, actor):
    aid = _drive(store, state, f"post:{state}-{method}")
    kw = {"reason": "x"} if method in ("reject", "terminate", "retire") else {}
    with pytest.raises(InvalidTransition) as e:
        getattr(store, method)(aid, actor=actor, **kw)
    assert e.value.status == 409
    assert state in str(e.value)
    assert store.get(aid)["state"] == state  # unchanged


def test_every_pair_matrix(store):
    """Exhaustive: for every (state, transition) the outcome is allowed XOR 409."""
    from app.workentry_store import TRANSITIONS
    # TRANSITIONS: name -> {"from": set, "to": state}
    allowed = {(f, n) for n, t in TRANSITIONS.items() for f in t["from"]}
    expected = {
        ("intent", "file"),
        ("pending", "resolve_open"), ("pending", "accept"), ("pending", "reject"),
        ("pending", "withdraw"), ("pending", "retire"), ("pending", "go_dormant"),
        ("dormant", "revive"), ("dormant", "withdraw"), ("dormant", "retire"),
        ("accepted", "activate"), ("accepted", "terminate"),
        ("active", "complete"), ("active", "terminate"),
    }
    assert allowed == expected
    assert set(TRANSITIONS["file"]["from"]) == {"intent"}
    for t in TERMINAL_STATES:
        assert not any(f == t for f, _ in allowed)


# ── terminal immutability ───────────────────────────────────────────────────

def _terminal(store, kind, opp):
    aid = file_(store, opp=opp)["agreement"]["agreement_id"]
    if kind == "rejected":
        store.reject(aid, actor="agent-o", reason="no")
    elif kind == "withdrawn":
        store.withdraw(aid, actor="agent-a")
    elif kind == "retired":
        store.retire(aid, actor="agent-a")
    else:
        store.accept(aid, actor="agent-o"); store.activate(aid, actor="agent-a")
        if kind == "completed":
            store.complete(aid, actor="agent-o")
        else:
            store.terminate(aid, actor="agent-o", reason="x")
    return aid


@pytest.mark.parametrize("kind", ["rejected", "withdrawn", "retired", "completed", "terminated"])
def test_terminal_is_immutable_and_queryable(store, kind):
    aid = _terminal(store, kind, f"post:t-{kind}")
    assert kind in TERMINAL_STATES
    for method in ("accept", "activate", "withdraw", "complete"):
        with pytest.raises(InvalidTransition) as e:
            getattr(store, method)(aid, actor="agent-o")
        assert kind in str(e.value)
    with pytest.raises(InvalidTransition):
        store.revive(aid, actor="agent-a")
    a = store.get(aid)
    assert a["state"] == kind
    assert any(x["agreement_id"] == aid for x in store.list(state=kind))


def test_database_level_terminal_immutability(store, tmp_path):
    aid = _terminal(store, "rejected", "post:db")
    conn = sqlite3.connect(tmp_path / "workentry.db")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE agreements SET state='active' WHERE agreement_id=?", (aid,))
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM agreements WHERE agreement_id=?", (aid,))
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE agreement_history SET actor='x' WHERE agreement_id=?", (aid,))
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM receipts WHERE agreement_id=?", (aid,))


def test_not_found(store):
    with pytest.raises(NotFound) as e:
        store.accept("agr-workentry-nope", actor="x")
    assert e.value.status == 404


# ── dormant / revive / retire ───────────────────────────────────────────────

def test_dormant_after_14_days_is_non_terminal_and_hidden_from_live(store, clock):
    aid = file_(store)["agreement"]["agreement_id"]
    clock.advance(days=13, hours=23)
    assert store.sweep_dormant() == []
    clock.advance(hours=2)
    changed = store.sweep_dormant()
    assert changed == [aid]
    a = store.get(aid)
    assert a["state"] == "dormant"
    assert "dormant" not in TERMINAL_STATES
    assert all(x["agreement_id"] != aid for x in store.list_live())
    assert any(x["agreement_id"] == aid for x in store.list())
    assert store.get(aid)["state_history"][-1]["transition"] == "go_dormant"


def test_no_auto_expiry_ever(store, clock):
    aid = file_(store)["agreement"]["agreement_id"]
    clock.advance(days=3650)
    store.sweep_dormant()
    store.sweep_dormant()
    assert store.get(aid)["state"] == "dormant"
    assert not any(h["to"] in ("expired", "retired") for h in store.get(aid)["state_history"])


def test_open_accepted_entries_are_not_swept(store, clock):
    aid = file_(store, mode="open")["agreement"]["agreement_id"]
    clock.advance(days=100)
    assert store.sweep_dormant() == []
    assert store.get(aid)["state"] == "accepted"


def test_activity_on_pending_defers_dormancy(store, clock):
    aid = file_(store)["agreement"]["agreement_id"]
    clock.advance(days=10)
    store.record_activity(aid, actor="agent-o")
    clock.advance(days=10)
    assert store.sweep_dormant() == []
    clock.advance(days=5)
    assert store.sweep_dormant() == [aid]


@pytest.mark.parametrize("who", ["agent-a", "agent-o"])
def test_dormant_revives_to_pending_on_activity_by_either_side(store, clock, who):
    aid = file_(store, opp=f"post:{who}")["agreement"]["agreement_id"]
    clock.advance(days=15)
    store.sweep_dormant()
    r = store.record_activity(aid, actor=who)
    assert r["agreement"]["state"] == "pending"
    assert r["receipt"]["transition"] == "revive"
    assert r["receipt"]["from"] == "dormant" and r["receipt"]["to"] == "pending"
    # and it can then be accepted normally
    assert store.accept(aid, actor="agent-o")["agreement"]["state"] == "accepted"


def test_stranger_activity_does_not_revive(store, clock):
    aid = file_(store)["agreement"]["agreement_id"]
    clock.advance(days=15); store.sweep_dormant()
    with pytest.raises(AuthorityError):
        store.record_activity(aid, actor="stranger")
    assert store.get(aid)["state"] == "dormant"


def test_dormant_can_be_retired_or_withdrawn_by_party_decision(store, clock):
    a1 = file_(store, opp="post:1")["agreement"]["agreement_id"]
    a2 = file_(store, opp="post:2")["agreement"]["agreement_id"]
    clock.advance(days=15); store.sweep_dormant()
    assert store.retire(a1, actor="agent-o")["agreement"]["state"] == "retired"
    assert store.withdraw(a2, actor="agent-a")["agreement"]["state"] == "withdrawn"


def test_dormant_still_blocks_duplicate_live_entry(store, clock):
    aid = file_(store)["agreement"]["agreement_id"]
    clock.advance(days=15); store.sweep_dormant()
    with pytest.raises(DuplicateEntryError) as e:
        file_(store)
    assert aid in str(e.value)


# ── supersedes ──────────────────────────────────────────────────────────────

def test_supersedes_after_terminal_links_both_ways(store):
    old = _terminal(store, "rejected", "post:s")
    new = file_(store, opp="post:s", supersedes=old)["agreement"]
    assert new["supersedes"] == old
    assert store.get(old)["superseded_by"] == new["agreement_id"]
    assert store.get(old)["state"] == "rejected"  # old record untouched


def test_supersedes_requires_terminal_same_parties_and_unsuperseded(store):
    live = file_(store, opp="post:live")["agreement"]["agreement_id"]
    with pytest.raises(WorkEntryError) as e:
        file_(store, opp="post:live2", supersedes=live)
    assert e.value.status == 409 and "pending" in str(e.value)
    old = _terminal(store, "withdrawn", "post:w")
    with pytest.raises(WorkEntryError):
        file_(store, opp="post:w", entrant="agent-z", supersedes=old)
    file_(store, opp="post:w", supersedes=old)
    with pytest.raises(WorkEntryError) as e:
        file_(store, opp="post:w", entrant="agent-a", supersedes=old)
    assert e.value.status == 409
    with pytest.raises(NotFound):
        file_(store, opp="post:w2", supersedes="agr-workentry-missing")


def test_refile_after_terminal_without_supersedes_allowed(store):
    _terminal(store, "retired", "post:r")
    assert file_(store, opp="post:r")["agreement"]["state"] == "pending"


# ── idempotency (F12) ───────────────────────────────────────────────────────

def test_file_same_key_returns_same_agreement_and_receipts(store, seeds):
    r1 = file_(store, key="k1")
    n = len(seeds.calls)
    r2 = file_(store, key="k1")
    assert r2["replayed"] is True and r1.get("replayed") is not True
    assert r2["agreement"]["agreement_id"] == r1["agreement"]["agreement_id"]
    assert [x["receipt_id"] for x in r2["receipts"]] == [x["receipt_id"] for x in r1["receipts"]]
    assert len(seeds.calls) == n  # no new seed
    assert len(store.list()) == 1


def test_file_same_key_different_opportunity_conflicts(store):
    file_(store, key="k1")
    with pytest.raises(IdempotencyConflict) as e:
        file_(store, key="k1", opp="post:other")
    assert e.value.status == 409


def test_second_live_entry_409_names_existing(store):
    aid = file_(store, key="a")["agreement"]["agreement_id"]
    with pytest.raises(DuplicateEntryError) as e:
        file_(store, key="b")
    assert e.value.status == 409
    assert e.value.existing_agreement_id == aid
    assert aid in str(e.value)


def test_duplicate_scoped_to_entrant_and_opportunity(store):
    file_(store)
    file_(store, entrant="agent-b")
    file_(store, opp="post:other")


def test_transition_same_key_returns_original_receipt(store, seeds):
    aid = file_(store)["agreement"]["agreement_id"]
    r1 = store.accept(aid, actor="agent-o", idempotency_key="acc-1")
    n = len(seeds.calls)
    r2 = store.accept(aid, actor="agent-o", idempotency_key="acc-1")
    assert r2["replayed"] is True
    assert r2["receipt"]["receipt_id"] == r1["receipt"]["receipt_id"]
    assert len(seeds.calls) == n
    assert len(store.get(aid)["state_history"]) == 3  # create, file, accept


def test_transition_key_reuse_for_other_transition_conflicts(store):
    aid = file_(store)["agreement"]["agreement_id"]
    store.accept(aid, actor="agent-o", idempotency_key="kk")
    with pytest.raises(IdempotencyConflict):
        store.activate(aid, actor="agent-a", idempotency_key="kk")


def test_without_key_second_identical_transition_is_409_not_silent(store):
    aid = file_(store)["agreement"]["agreement_id"]
    store.accept(aid, actor="agent-o")
    with pytest.raises(InvalidTransition):
        store.accept(aid, actor="agent-o")


# ── receipts / seeds / audit ────────────────────────────────────────────────

def test_every_transition_has_receipt_history_seed_audit(store, seeds, audit):
    aid = file_(store, key="kf")["agreement"]["agreement_id"]
    store.accept(aid, actor="agent-o", idempotency_key="ka")
    store.activate(aid, actor="agent-a")
    a = store.get(aid)
    receipts = store.receipts(aid)
    assert len(receipts) == len(a["state_history"]) == 4
    for r in receipts:
        for f in ("receipt_id", "agreement_id", "transition", "from", "to", "actor",
                  "at", "seed_doi", "audit_hash", "idempotency_key"):
            assert f in r
        assert r["seed_doi"].startswith("10.test/")
        assert r["audit_hash"].startswith("audithash")
        assert store.get_receipt(r["receipt_id"]) == r
    assert receipts[0]["from"] is None and receipts[0]["to"] == "intent"
    for h, r in zip(a["state_history"], receipts):
        assert h["receipt_id"] == r["receipt_id"] and h["seed_doi"] == r["seed_doi"]
    assert len(seeds.calls) == 4 and len(audit.calls) == 4
    assert a["genesis_seed_doi"] == receipts[0]["seed_doi"]


def test_seeds_chain_lineage(store, seeds):
    aid = file_(store)["agreement"]["agreement_id"]
    store.accept(aid, actor="agent-o")
    assert seeds.calls[0]["parent_doi"] is None
    assert seeds.calls[0]["seed_type"] == "planted"
    assert seeds.calls[1]["parent_doi"] == "10.test/seed-1"
    assert seeds.calls[2]["parent_doi"] == "10.test/seed-2"
    assert all(c["source_id"] == aid for c in seeds.calls)
    assert seeds.calls[2]["metadata"]["transition"] == "accept"


def test_receipts_survive_reopen(tmp_path, seeds, audit, clock):
    s1 = WorkEntryStore(tmp_path / "w.db", seed_fn=seeds, audit_fn=audit, clock=clock)
    aid = file_(s1)["agreement"]["agreement_id"]
    s1.close()
    s2 = WorkEntryStore(tmp_path / "w.db", seed_fn=seeds, audit_fn=audit, clock=clock)
    assert len(s2.receipts(aid)) == 2
    assert s2.get(aid)["state"] == "pending"


# ── loud provenance ─────────────────────────────────────────────────────────

def test_seed_failure_on_file_rolls_back_loudly(store, seeds):
    seeds.fail = True
    with pytest.raises(ProvenanceError) as e:
        file_(store, key="kf")
    assert e.value.status == 500
    assert store.list() == []
    gaps = store.evidence_gaps()
    assert len(gaps) == 1 and gaps[0]["attempted_transition"] == "create"
    assert "seed" in gaps[0]["reason"] and gaps[0]["gap_id"] in str(e.value)
    # retry with same key after recovery works and is not a replay
    seeds.fail = False
    assert file_(store, key="kf")["agreement"]["state"] == "pending"


def test_seed_failure_on_transition_rolls_back_state_history_receipt(store, seeds):
    aid = file_(store)["agreement"]["agreement_id"]
    before = (store.get(aid), store.receipts(aid))
    seeds.fail = True
    with pytest.raises(ProvenanceError):
        store.accept(aid, actor="agent-o", idempotency_key="k")
    assert (store.get(aid), store.receipts(aid)) == before
    gaps = store.evidence_gaps(aid)
    assert len(gaps) == 1 and gaps[0]["attempted_transition"] == "accept"
    seeds.fail = False
    assert store.accept(aid, actor="agent-o", idempotency_key="k")["agreement"]["state"] == "accepted"


def test_audit_failure_is_loud_too(store, audit):
    aid = file_(store)["agreement"]["agreement_id"]
    audit.fail = True
    with pytest.raises(ProvenanceError):
        store.accept(aid, actor="agent-o")
    assert store.get(aid)["state"] == "pending"


def test_mid_filing_failure_leaves_no_partial_agreement(tmp_path, audit, clock):
    """Open mode makes 3 transitions; failing on the 3rd must roll back all."""
    calls = {"n": 0}

    def flaky(**kw):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("boom")
        return {"doi": f"10.test/{calls['n']}"}

    s = WorkEntryStore(tmp_path / "f.db", seed_fn=flaky, audit_fn=audit, clock=clock)
    with pytest.raises(ProvenanceError):
        file_(s, mode="open")
    assert s.list() == []
    assert s.evidence_gaps()[0]["attempted_transition"] == "resolve_open"


def test_gap_policy_commits_transition_with_explicit_gap_record(tmp_path, audit, clock):
    seeds = FakeSeeds()
    s = WorkEntryStore(tmp_path / "g.db", seed_fn=seeds, audit_fn=audit, clock=clock,
                       provenance_failure="evidence_gap")
    aid = file_(s)["agreement"]["agreement_id"]
    seeds.fail = True
    r = s.accept(aid, actor="agent-o")
    assert r["agreement"]["state"] == "accepted"
    assert r["receipt"]["seed_doi"] is None
    assert r["receipt"]["evidence_gap_id"]
    gaps = s.evidence_gaps(aid)
    assert len(gaps) == 1 and gaps[0]["gap_id"] == r["receipt"]["evidence_gap_id"]
    assert gaps[0]["receipt_id"] == r["receipt"]["receipt_id"]


def test_bad_provenance_policy_rejected(tmp_path):
    with pytest.raises(ValueError):
        WorkEntryStore(tmp_path / "x.db", provenance_failure="ignore")


# ── queries ─────────────────────────────────────────────────────────────────

def test_list_filters(store):
    a = file_(store, opp="post:1")["agreement"]["agreement_id"]
    file_(store, opp="post:2", entrant="agent-b")
    assert len(store.list(entrant="agent-a")) == 1
    assert len(store.list(owner="agent-o")) == 2
    assert len(store.list(opportunity_ref="post:2")) == 1
    assert len(store.list(state="pending")) == 2
    store.accept(a, actor="agent-o")
    assert len(store.list(state="pending")) == 1
    assert len(store.list_live()) == 2


# ── app wiring + real seed writer ───────────────────────────────────────────

def test_app_state_has_workentry_store(app):
    from app.deps import state
    assert isinstance(state.workentry, WorkEntryStore)
    assert state.workentry._db_path.name == "workentry.db"


def test_default_writers_produce_real_seed_and_audit(app):
    from app.deps import state
    import uuid
    opp = f"post:real-{uuid.uuid4().hex[:6]}"
    r = state.workentry.file_entry(
        entrant="agent-real-a", owner="agent-real-o", opportunity_ref=opp,
        entry_mode="standard", objects={}, terms={})
    rc = r["receipts"][-1]
    assert rc["seed_doi"] and rc["audit_hash"]
    from app.seeds import _read_seeds
    assert any(s["doi"] == rc["seed_doi"] for s in _read_seeds())
