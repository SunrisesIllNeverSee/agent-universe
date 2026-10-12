"""WorkEntryAgreement store - P4 slice 1 (Agreement core).

SQLite store (workentry.db) plus a pure-python service layer for the
WorkEntryAgreement of Phase 1A section 5.2 (F1-F15) as amended by the owner's
2026-10-12 P4 plan section 7:

    intent -> pending -> accepted -> active -> completed
    exits:     rejected | withdrawn | retired | terminated        (terminal)
    non-terminal side state: dormant (from pending; revives to pending)

There is NO automatic expiry. A pending entry with no activity for 14 days
becomes ``dormant`` (hidden from live lists, kept, revives on any activity by
either party). ``retired`` happens only by a party decision. Terminal records
are kept as the archive and are immutable - enforced here and by SQLite
triggers (nothing is ever deleted).

Every transition writes, in ONE SQLite transaction: an append-only history
row, a durable receipt, and a Seed (+ audit entry). Provenance failure is
loud: the default policy rolls the whole transition back and records an
``evidence_gap`` row; policy ``"evidence_gap"`` instead commits the transition
with a receipt that names the gap (1A 260-266). It is never silent.

Wiring (which API calls this, authority resolution beyond actor/party checks,
slot binding, constitutional gate) belongs to later slices.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, UTC
from pathlib import Path
from threading import RLock
from typing import Any, Callable

AGREEMENT_CLASS = "WorkEntryAgreement"
CLASS_VERSION = 1
SEED_SOURCE_TYPE = "work_entry_agreement"

ENTRY_MODES = ("open", "standard", "constitutional")
TERMINAL_STATES = frozenset({"rejected", "withdrawn", "retired", "terminated", "completed"})
LIVE_STATES = ("intent", "pending", "dormant", "accepted", "active")  # F12 "non-terminal"
DORMANT_AFTER = timedelta(days=14)

# name -> allowed source states, target state, who may perform it.
#   entrant / owner / party (entrant or owner) / system (no human actor)
TRANSITIONS: dict[str, dict[str, Any]] = {
    "file":         {"from": {"intent"},                       "to": "pending",   "by": "entrant_or_system"},
    "resolve_open": {"from": {"pending"},                      "to": "accepted",  "by": "system"},
    "accept":       {"from": {"pending"},                      "to": "accepted",  "by": "owner"},
    "reject":       {"from": {"pending"},                      "to": "rejected",  "by": "owner"},
    "withdraw":     {"from": {"pending", "dormant"},           "to": "withdrawn", "by": "entrant"},
    "retire":       {"from": {"pending", "dormant"},           "to": "retired",   "by": "party"},
    "go_dormant":   {"from": {"pending"},                      "to": "dormant",   "by": "system"},
    "revive":       {"from": {"dormant"},                      "to": "pending",   "by": "party"},
    "activate":     {"from": {"accepted"},                     "to": "active",    "by": "party"},
    "complete":     {"from": {"active"},                       "to": "completed", "by": "party"},
    "terminate":    {"from": {"accepted", "active"},           "to": "terminated", "by": "party"},
}
# actors that speak FOR a named principal (operator; email-only poster magic link)
_DELEGATE_PREFIXES = ("operator:", "poster-link:")
_REASON_REQUIRED = {"reject"}  # F11: rejection carries a named reason


# ── errors ───────────────────────────────────────────────────────────────

class WorkEntryError(Exception):
    status = 400
    code = "workentry_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFound(WorkEntryError):
    status = 404
    code = "agreement_not_found"


class InvalidTransition(WorkEntryError):
    status = 409
    code = "invalid_transition"


class SupersedeConflict(WorkEntryError):
    status = 409
    code = "supersede_conflict"


class AuthorityError(WorkEntryError):
    status = 403
    code = "authority"


class IdempotencyConflict(WorkEntryError):
    status = 409
    code = "idempotency_conflict"


class DuplicateEntryError(WorkEntryError):
    status = 409
    code = "duplicate_entry"

    def __init__(self, existing_agreement_id: str, message: str):
        super().__init__(message)
        self.existing_agreement_id = existing_agreement_id


class ProvenanceError(WorkEntryError):
    status = 500
    code = "provenance_failure"

    def __init__(self, message: str, gap_id: str):
        super().__init__(message)
        self.gap_id = gap_id


class _ProvenanceFailure(Exception):
    def __init__(self, stage: str, detail: str, transition: str, agreement_id: str,
                 actor: str, key: str | None):
        super().__init__(f"{stage}: {detail}")
        self.stage, self.detail = stage, detail
        self.transition, self.agreement_id, self.actor, self.key = transition, agreement_id, actor, key


# ── default writers ──────────────────────────────────────────────────────

def default_seed_fn(**kwargs: Any) -> dict:
    """Drive app.seeds.create_seed synchronously.

    create_seed is declared async but never awaits; if that ever changes this
    raises loudly (which the store turns into a provenance failure).
    """
    from .seeds import create_seed
    coro = create_seed(**kwargs)
    try:
        coro.send(None)
    except StopIteration as done:
        return done.value
    coro.close()
    raise RuntimeError("create_seed awaited; cannot run synchronously inside the store")


# ── schema ───────────────────────────────────────────────────────────────

_TERMINAL_SQL = ", ".join(f"'{s}'" for s in sorted(TERMINAL_STATES))
_LIVE_SQL = ", ".join(f"'{s}'" for s in LIVE_STATES)

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS agreements (
    agreement_id     TEXT PRIMARY KEY,
    agreement_class  TEXT NOT NULL,
    class_version    INTEGER NOT NULL,
    entrant_id       TEXT NOT NULL,
    owner_id         TEXT NOT NULL,
    principals_json  TEXT NOT NULL,
    objects_json     TEXT NOT NULL,
    opportunity_ref  TEXT NOT NULL,
    terms_json       TEXT NOT NULL,
    governance_json  TEXT NOT NULL,
    entry_mode       TEXT NOT NULL,
    state            TEXT NOT NULL,
    outcome_reason   TEXT,
    idempotency_key  TEXT,
    supersedes       TEXT,
    superseded_by    TEXT,
    genesis_seed_doi TEXT,
    last_seed_doi    TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    last_activity_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agr_entrant ON agreements(entrant_id);
CREATE INDEX IF NOT EXISTS idx_agr_owner ON agreements(owner_id);
CREATE INDEX IF NOT EXISTS idx_agr_opp ON agreements(opportunity_ref);
CREATE INDEX IF NOT EXISTS idx_agr_state ON agreements(state);
CREATE UNIQUE INDEX IF NOT EXISTS uq_agr_entrant_key
    ON agreements(entrant_id, idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_agr_one_live_entry
    ON agreements(entrant_id, opportunity_ref) WHERE state IN ({_LIVE_SQL});

CREATE TABLE IF NOT EXISTS agreement_history (
    history_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    agreement_id TEXT NOT NULL,
    seq          INTEGER NOT NULL,
    transition   TEXT NOT NULL,
    from_state   TEXT,
    to_state     TEXT NOT NULL,
    actor        TEXT NOT NULL,
    acting_for   TEXT,
    at           TEXT NOT NULL,
    seed_doi     TEXT,
    receipt_id   TEXT NOT NULL,
    reason       TEXT,
    UNIQUE (agreement_id, seq)
);

CREATE TABLE IF NOT EXISTS receipts (
    receipt_id      TEXT PRIMARY KEY,
    agreement_id    TEXT NOT NULL,
    seq             INTEGER NOT NULL,
    transition      TEXT NOT NULL,
    from_state      TEXT,
    to_state        TEXT NOT NULL,
    actor           TEXT NOT NULL,
    acting_for      TEXT,
    at              TEXT NOT NULL,
    seed_doi        TEXT,
    audit_hash      TEXT,
    idempotency_key TEXT,
    reason          TEXT,
    evidence_gap_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_rcpt_agr ON receipts(agreement_id, idempotency_key);

CREATE TABLE IF NOT EXISTS evidence_gaps (
    gap_id               TEXT PRIMARY KEY,
    agreement_id         TEXT,
    receipt_id           TEXT,
    attempted_transition TEXT NOT NULL,
    stage                TEXT NOT NULL,
    reason               TEXT NOT NULL,
    actor                TEXT,
    idempotency_key      TEXT,
    resolution           TEXT NOT NULL,
    at                   TEXT NOT NULL
);

-- Non-authoritative marks (e.g. the 48 h "ask the poster" prompt was sent for
-- a given activity stamp). Not part of the agreement record.
CREATE TABLE IF NOT EXISTS agreement_flags (
    agreement_id TEXT NOT NULL,
    flag         TEXT NOT NULL,
    mark         TEXT NOT NULL,
    at           TEXT NOT NULL,
    PRIMARY KEY (agreement_id, flag)
);

-- Archive guarantees: nothing is ever deleted; history/receipts/gaps are
-- append-only; terminal agreements are immutable (only the one-time
-- superseded_by back-link may be set, per K9 re-entry).
CREATE TRIGGER IF NOT EXISTS trg_agr_no_delete BEFORE DELETE ON agreements
BEGIN SELECT RAISE(ABORT, 'agreements are never deleted (archive)'); END;
CREATE TRIGGER IF NOT EXISTS trg_agr_terminal_immutable BEFORE UPDATE ON agreements
WHEN OLD.state IN ({_TERMINAL_SQL}) AND NOT (
    OLD.superseded_by IS NULL AND NEW.superseded_by IS NOT NULL
    AND NEW.state = OLD.state AND NEW.terms_json = OLD.terms_json
    AND NEW.principals_json = OLD.principals_json AND NEW.objects_json = OLD.objects_json
    AND NEW.outcome_reason IS OLD.outcome_reason AND NEW.last_seed_doi IS OLD.last_seed_doi
    AND NEW.updated_at = OLD.updated_at AND NEW.last_activity_at = OLD.last_activity_at)
BEGIN SELECT RAISE(ABORT, 'terminal agreement is immutable'); END;
CREATE TRIGGER IF NOT EXISTS trg_hist_no_update BEFORE UPDATE ON agreement_history
BEGIN SELECT RAISE(ABORT, 'agreement_history is append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_hist_no_delete BEFORE DELETE ON agreement_history
BEGIN SELECT RAISE(ABORT, 'agreement_history is append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_rcpt_no_update BEFORE UPDATE ON receipts
BEGIN SELECT RAISE(ABORT, 'receipts are append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_rcpt_no_delete BEFORE DELETE ON receipts
BEGIN SELECT RAISE(ABORT, 'receipts are append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_gap_no_update BEFORE UPDATE ON evidence_gaps
BEGIN SELECT RAISE(ABORT, 'evidence_gaps are append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_gap_no_delete BEFORE DELETE ON evidence_gaps
BEGIN SELECT RAISE(ABORT, 'evidence_gaps are append-only'); END;
"""


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()


class WorkEntryStore:
    """SQLite-backed WorkEntryAgreement store + state machine service."""

    def __init__(
        self,
        db_path: Path,
        *,
        seed_fn: Callable[..., dict] | None = None,
        audit_fn: Callable[[str, str, dict], str | None] | None = None,
        clock: Callable[[], datetime] | None = None,
        provenance_failure: str = "rollback",
    ) -> None:
        if provenance_failure not in ("rollback", "evidence_gap"):
            raise ValueError("provenance_failure must be 'rollback' or 'evidence_gap'")
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._seed_fn = seed_fn or default_seed_fn
        self._audit_fn = audit_fn
        self._clock = clock or (lambda: datetime.now(UTC))
        self._policy = provenance_failure
        # isolation_level=None: transactions are managed explicitly.
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        result = self._conn.execute("PRAGMA journal_mode=WAL").fetchone()
        if result and result[0].lower() != "wal":
            import logging
            logging.getLogger("civitae").warning(
                "SQLite WAL mode failed for %s (got %s).", db_path, result[0])
        self._conn.executescript(_SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        """Additive, guarded column adds (slice 3): receipts name the credential type."""
        for table in ("agreement_history", "receipts"):
            cols = {r[1] for r in self._conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if "credential_ref" not in cols:
                self._conn.execute(f"ALTER TABLE {table} ADD COLUMN credential_ref TEXT")

    def close(self) -> None:
        self._conn.close()

    # ── internals ───────────────────────────────────────────────────────

    def _now(self) -> str:
        return _iso(self._clock())

    def _txn(self, fn: Callable[[], Any]) -> Any:
        """Run fn in one IMMEDIATE transaction; provenance failure -> loud."""
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                out = fn()
                self._conn.execute("COMMIT")
                return out
            except _ProvenanceFailure as pf:
                self._conn.execute("ROLLBACK")
                gap_id = self._write_gap(pf)
                raise ProvenanceError(
                    f"provenance failed at {pf.stage} for '{pf.transition}' "
                    f"({pf.detail}); transition rolled back; evidence_gap {gap_id} recorded",
                    gap_id) from pf
            except BaseException:
                try:
                    self._conn.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise

    def _write_gap(self, pf: _ProvenanceFailure) -> str:
        gap_id = f"gap-{uuid.uuid4().hex[:12]}"
        self._conn.execute(
            "INSERT INTO evidence_gaps (gap_id, agreement_id, receipt_id, attempted_transition, stage,"
            " reason, actor, idempotency_key, resolution, at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (gap_id, pf.agreement_id, None, pf.transition, pf.stage, pf.detail, pf.actor,
             pf.key, "rolled_back", self._now()))
        return gap_id

    @staticmethod
    def _j(v: Any) -> str:
        return json.dumps(v if v is not None else {}, sort_keys=True, default=str)

    def _row(self, agreement_id: str) -> sqlite3.Row:
        row = self._conn.execute("SELECT * FROM agreements WHERE agreement_id=?", (agreement_id,)).fetchone()
        if row is None:
            raise NotFound(f"agreement {agreement_id} not found")
        return row

    def _history(self, agreement_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM agreement_history WHERE agreement_id=? ORDER BY seq", (agreement_id,)).fetchall()
        out = []
        for h in rows:
            item = {"transition": h["transition"], "from": h["from_state"], "to": h["to_state"],
                    "at": h["at"], "actor": h["actor"], "seed_doi": h["seed_doi"],
                    "receipt_id": h["receipt_id"]}
            if h["acting_for"]:
                item["acting_for"] = h["acting_for"]
            if h["credential_ref"]:
                item["credential_ref"] = h["credential_ref"]
            if h["reason"]:
                item["reason"] = h["reason"]
            out.append(item)
        return out

    def _agreement(self, row: sqlite3.Row) -> dict:
        return {
            "agreement_id": row["agreement_id"],
            "agreement_class": row["agreement_class"],
            "class_version": row["class_version"],
            "principals": json.loads(row["principals_json"]),
            "objects": json.loads(row["objects_json"]),
            "opportunity_ref": row["opportunity_ref"],
            "terms": json.loads(row["terms_json"]),
            "governance": json.loads(row["governance_json"]),
            "entry_mode": row["entry_mode"],
            "state": row["state"],
            "state_history": self._history(row["agreement_id"]),
            "outcome_reason": row["outcome_reason"],
            "idempotency_key": row["idempotency_key"],
            "supersedes": row["supersedes"],
            "superseded_by": row["superseded_by"],
            "genesis_seed_doi": row["genesis_seed_doi"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "last_activity_at": row["last_activity_at"],
        }

    @staticmethod
    def _receipt(r: sqlite3.Row) -> dict:
        return {
            "receipt_id": r["receipt_id"], "agreement_id": r["agreement_id"],
            "transition": r["transition"], "from": r["from_state"], "to": r["to_state"],
            "actor": r["actor"], "acting_for": r["acting_for"], "at": r["at"],
            "seed_doi": r["seed_doi"], "audit_hash": r["audit_hash"],
            "idempotency_key": r["idempotency_key"], "reason": r["reason"],
            "evidence_gap_id": r["evidence_gap_id"],
            "credential_ref": r["credential_ref"],
        }

    # ── authority (F3 / 1G): actor-level checks only; credential resolution is slice 2 ──

    @staticmethod
    def _effective_principal(actor: str, acting_for: str | None) -> str | None:
        """The principal an actor speaks as. An operator acts only FOR a named principal."""
        if actor.startswith(_DELEGATE_PREFIXES):
            return acting_for or None
        return actor

    def _check_authority(self, row: sqlite3.Row, name: str, actor: str, acting_for: str | None) -> None:
        by = TRANSITIONS[name]["by"]
        entrant, owner = row["entrant_id"], row["owner_id"]
        if by == "system":
            if actor != "system":
                raise AuthorityError(f"'{name}' is a system transition; actor '{actor}' may not perform it")
            return
        if actor == "system":
            if by == "entrant_or_system":
                return
            raise AuthorityError(f"'{name}' requires a party; 'system' may not perform it")
        who = self._effective_principal(actor, acting_for)
        if who is None:
            raise AuthorityError(f"delegate '{actor}' must name the principal it acts for (acting_for)")
        if not actor.startswith(_DELEGATE_PREFIXES) and acting_for and acting_for != actor:
            raise AuthorityError("acting_for is only valid for operator / poster-link actors")
        allowed = {"entrant": {entrant}, "owner": {owner}, "party": {entrant, owner},
                   "entrant_or_system": {entrant}}[by]
        if who not in allowed:
            role = {"entrant": "the entrant", "owner": "the opportunity owner",
                    "party": "a party to the agreement", "entrant_or_system": "the entrant"}[by]
            raise AuthorityError(f"'{name}' requires {role}; '{who}' is not")

    # ── core step ───────────────────────────────────────────────────────

    def _step(self, row_or_id: Any, name: str, *, actor: str, acting_for: str | None = None,
              reason: str | None = None, key: str, new_agreement: dict | None = None,
              seq: int, credential: str | None = None, gap_note: dict | None = None) -> dict:
        """Apply one transition inside the current transaction; returns the receipt dict.

        When new_agreement is given the row is inserted here (the 'create' step).
        """
        creating = new_agreement is not None
        aid = new_agreement["agreement_id"] if creating else row_or_id
        t = TRANSITIONS.get(name)
        from_state = None if creating else (self._row(aid)["state"])
        to_state = "intent" if creating else t["to"]
        now = self._now()
        receipt_id = f"rcpt-{uuid.uuid4().hex[:16]}"
        last_seed = None if creating else self._row(aid)["last_seed_doi"]

        seed_doi: str | None = None
        audit_hash: str | None = None
        gap_id: str | None = None
        failure: _ProvenanceFailure | None = None
        try:
            seed = self._seed_fn(
                source_type=SEED_SOURCE_TYPE, source_id=aid, creator_id=actor, creator_type="AAI",
                seed_type="planted" if creating else "grown", parent_doi=last_seed,
                metadata={"transition": name, "from": from_state, "to": to_state,
                          "receipt_id": receipt_id, "acting_for": acting_for or "",
                          "reason": reason or "", "agreement_class": AGREEMENT_CLASS})
            seed_doi = (seed or {}).get("doi")
            if not seed_doi:
                raise RuntimeError("seed writer returned no doi")
        except Exception as exc:  # noqa: BLE001 - provenance must never be silent
            failure = _ProvenanceFailure("seed", f"{type(exc).__name__}: {exc}", name, aid, actor, key)
        if failure is None and self._audit_fn is not None:
            try:
                audit_hash = self._audit_fn(
                    "workentry", f"agreement_{name}",
                    {"agreement_id": aid, "transition": name, "from": from_state, "to": to_state,
                     "actor": actor, "acting_for": acting_for, "receipt_id": receipt_id,
                     "seed_doi": seed_doi, "agent": actor, "credential_ref": credential})
            except Exception as exc:  # noqa: BLE001
                failure = _ProvenanceFailure("audit", f"{type(exc).__name__}: {exc}", name, aid, actor, key)
        if failure is not None:
            if self._policy == "rollback":
                raise failure
            gap_id = f"gap-{uuid.uuid4().hex[:12]}"
            self._conn.execute(
                "INSERT INTO evidence_gaps (gap_id, agreement_id, receipt_id, attempted_transition, stage,"
                " reason, actor, idempotency_key, resolution, at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (gap_id, aid, receipt_id, name, failure.stage, failure.detail, actor, key,
                 "committed_with_gap", now))
            if failure.stage == "seed":
                seed_doi = None
        if gap_note is not None:
            # A compensating transition names the failure that forced it (slice 4):
            # the explicit evidence_gap row is linked from the receipt.
            note_id = f"gap-{uuid.uuid4().hex[:12]}"
            self._conn.execute(
                "INSERT INTO evidence_gaps (gap_id, agreement_id, receipt_id, attempted_transition, stage,"
                " reason, actor, idempotency_key, resolution, at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (note_id, aid, receipt_id, gap_note.get("attempted", name), gap_note.get("stage", "binding"),
                 gap_note.get("reason", ""), actor, key, gap_note.get("resolution", "compensated_terminated"), now))
            gap_id = gap_id or note_id

        if creating:
            a = new_agreement
            self._conn.execute(
                "INSERT INTO agreements (agreement_id, agreement_class, class_version, entrant_id, owner_id,"
                " principals_json, objects_json, opportunity_ref, terms_json, governance_json, entry_mode,"
                " state, outcome_reason, idempotency_key, supersedes, superseded_by, genesis_seed_doi,"
                " last_seed_doi, created_at, updated_at, last_activity_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (aid, AGREEMENT_CLASS, CLASS_VERSION, a["entrant"], a["owner"],
                 self._j(a["principals"]), self._j(a["objects"]), a["opportunity_ref"],
                 self._j(a["terms"]), self._j(a["governance"]), a["entry_mode"], to_state, None,
                 key if a.get("key_supplied") else None, a.get("supersedes"), None, seed_doi, seed_doi,
                 now, now, now))
        else:
            outcome = reason if name in ("reject", "terminate", "retire", "withdraw") and reason else None
            self._conn.execute(
                "UPDATE agreements SET state=?, last_seed_doi=COALESCE(?, last_seed_doi),"
                " outcome_reason=COALESCE(?, outcome_reason), updated_at=?, last_activity_at=? WHERE agreement_id=?",
                (to_state, seed_doi, outcome, now, now, aid))
        self._conn.execute(
            "INSERT INTO agreement_history (agreement_id, seq, transition, from_state, to_state, actor,"
            " acting_for, at, seed_doi, receipt_id, reason, credential_ref) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (aid, seq, name, from_state, to_state, actor, acting_for, now, seed_doi, receipt_id, reason,
             credential))
        self._conn.execute(
            "INSERT INTO receipts (receipt_id, agreement_id, seq, transition, from_state, to_state, actor,"
            " acting_for, at, seed_doi, audit_hash, idempotency_key, reason, evidence_gap_id, credential_ref)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (receipt_id, aid, seq, name, from_state, to_state, actor, acting_for, now, seed_doi,
             audit_hash, key, reason, gap_id, credential))
        return self._receipt(self._conn.execute("SELECT * FROM receipts WHERE receipt_id=?", (receipt_id,)).fetchone())

    def _next_seq(self, aid: str) -> int:
        r = self._conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM agreement_history WHERE agreement_id=?",
                               (aid,)).fetchone()
        return r[0]

    # ── filing ──────────────────────────────────────────────────────────

    def file_entry(
        self, *, entrant: str, owner: str, opportunity_ref: str, entry_mode: str,
        objects: dict | None = None, terms: dict | None = None,
        credential_refs: dict | None = None, posture: str = "",
        idempotency_key: str | None = None, supersedes: str | None = None,
        auto_activate: bool = False,
    ) -> dict:
        """Create an Agreement (intent) and file it (-> pending).

        open mode: pending is crossed and resolved atomically to ``accepted``
        (the object is never skipped; activation is the entrant's second step).
        ``auto_activate`` (open mode only; slice 4 /api/slots/fill) adds the
        entrant's activate in the SAME commit: pending->accepted->active, each
        step modeled with its own history row, receipt and Seed.
        """
        if auto_activate and entry_mode != "open":
            raise WorkEntryError("auto_activate is only valid in open mode")
        if entry_mode not in ENTRY_MODES:
            raise WorkEntryError(f"entry_mode must be one of {list(ENTRY_MODES)}; got {entry_mode!r}")
        for field, val in (("entrant", entrant), ("owner", owner), ("opportunity_ref", opportunity_ref)):
            if not isinstance(val, str) or not val.strip():
                raise WorkEntryError(f"{field} is required")
        terms = dict(terms or {})
        objects = {"post_id": None, "mission_id": None, "slot_id": None, **(objects or {})}
        creds = credential_refs or {}
        key_supplied = bool(idempotency_key)
        key = idempotency_key or f"auto-{uuid.uuid4().hex}"

        def run() -> dict:
            if key_supplied:
                prior = self._conn.execute(
                    "SELECT * FROM agreements WHERE entrant_id=? AND idempotency_key=?",
                    (entrant, key)).fetchone()
                if prior is not None:
                    if prior["opportunity_ref"] != opportunity_ref:
                        raise IdempotencyConflict(
                            f"idempotency_key {key!r} already used by {prior['agreement_id']} "
                            f"for a different opportunity ({prior['opportunity_ref']})")
                    rc = self._conn.execute(
                        "SELECT * FROM receipts WHERE agreement_id=? AND idempotency_key=? ORDER BY seq",
                        (prior["agreement_id"], key)).fetchall()
                    return {"agreement": self._agreement(prior), "receipts": [self._receipt(r) for r in rc],
                            "replayed": True}
            if supersedes:
                old = self._row(supersedes)  # NotFound if missing
                if old["state"] not in TERMINAL_STATES:
                    raise SupersedeConflict(
                        f"cannot supersede {supersedes}: it is '{old['state']}', not terminal "
                        f"(only terminal agreements are superseded; dormant revives in place)")
                if old["entrant_id"] != entrant or old["opportunity_ref"] != opportunity_ref:
                    raise WorkEntryError(
                        f"{supersedes} belongs to a different entrant/opportunity; cannot supersede")
                if old["superseded_by"]:
                    raise SupersedeConflict(f"{supersedes} is already superseded by {old['superseded_by']}")
            dup = self._conn.execute(
                "SELECT agreement_id, state FROM agreements WHERE entrant_id=? AND opportunity_ref=?"
                f" AND state IN ({_LIVE_SQL})", (entrant, opportunity_ref)).fetchone()
            if dup is not None:
                raise DuplicateEntryError(
                    dup["agreement_id"],
                    f"entrant {entrant} already has a live entry for {opportunity_ref}: "
                    f"agreement {dup['agreement_id']} is '{dup['state']}'")

            aid = f"agr-workentry-{uuid.uuid4().hex[:12]}"
            resolution = "immediate" if entry_mode == "open" else "pending"
            envelope = {
                "agreement_id": aid, "entrant": entrant, "owner": owner,
                "principals": [
                    {"role": "entrant", "id": entrant, "credential_ref": creds.get("entrant")},
                    {"role": "owner", "id": owner, "credential_ref": creds.get("owner")}],
                "objects": objects, "opportunity_ref": opportunity_ref,
                "terms": {"pitch": terms.get("pitch"), "acceptance_payload": terms.get("acceptance_payload"),
                          "delivery_evidence_class": terms.get("delivery_evidence_class"),
                          "obligations_ref": terms.get("obligations_ref"),
                          "stake_ref": terms.get("stake_ref"),
                          **{k: v for k, v in terms.items() if k not in (
                              "pitch", "acceptance_payload", "delivery_evidence_class",
                              "obligations_ref", "stake_ref")}},
                "governance": {"mode": entry_mode, "posture": posture, "resolution_mode": resolution},
                "entry_mode": entry_mode, "supersedes": supersedes, "key_supplied": key_supplied,
            }
            receipts = [self._step(None, "create", actor=entrant, key=key, new_agreement=envelope, seq=1,
                                   credential=creds.get("entrant"))]
            receipts.append(self._step(aid, "file", actor=entrant, key=key, seq=2,
                                       credential=creds.get("entrant")))
            if entry_mode == "open":
                receipts.append(self._step(aid, "resolve_open", actor="system", key=key, seq=3))
                if auto_activate:
                    receipts.append(self._step(aid, "activate", actor=entrant, key=key, seq=4,
                                               credential=creds.get("entrant")))
            if supersedes:
                self._conn.execute("UPDATE agreements SET superseded_by=? WHERE agreement_id=?", (aid, supersedes))
            return {"agreement": self._agreement(self._row(aid)), "receipts": receipts, "replayed": False}

        return self._txn(run)

    # ── transitions ─────────────────────────────────────────────────────

    def _transition(self, agreement_id: str, name: str, *, actor: str, acting_for: str | None = None,
                    reason: str | None = None, idempotency_key: str | None = None,
                    credential: str | None = None) -> dict:
        if name in _REASON_REQUIRED and not (reason and reason.strip()):
            raise WorkEntryError(f"'{name}' requires a named reason")
        key = idempotency_key or f"auto-{uuid.uuid4().hex}"

        def run() -> dict:
            row = self._row(agreement_id)
            if idempotency_key:
                rcs = self._conn.execute(
                    "SELECT * FROM receipts WHERE agreement_id=? AND idempotency_key=? ORDER BY seq",
                    (agreement_id, key)).fetchall()
                if rcs:
                    if len(rcs) == 1 and rcs[0]["transition"] == name:
                        return {"agreement": self._agreement(row), "receipt": self._receipt(rcs[0]),
                                "replayed": True}
                    raise IdempotencyConflict(
                        f"idempotency_key {key!r} was already used on {agreement_id} for "
                        f"'{rcs[0]['transition']}', not '{name}'")
            state = row["state"]
            spec = TRANSITIONS[name]
            if state not in spec["from"]:
                kind = "terminal and immutable" if state in TERMINAL_STATES else "not a valid source"
                raise InvalidTransition(
                    f"cannot {name} agreement {agreement_id}: state is '{state}' ({kind}); "
                    f"'{name}' requires {sorted(spec['from'])}")
            self._check_authority(row, name, actor, acting_for)
            receipt = self._step(agreement_id, name, actor=actor, acting_for=acting_for, reason=reason,
                                 key=key, seq=self._next_seq(agreement_id), credential=credential)
            return {"agreement": self._agreement(self._row(agreement_id)), "receipt": receipt, "replayed": False}

        return self._txn(run)

    def accept(self, agreement_id, *, actor, acting_for=None, idempotency_key=None, credential=None):
        return self._transition(agreement_id, "accept", actor=actor, acting_for=acting_for,
                                idempotency_key=idempotency_key, credential=credential)

    def reject(self, agreement_id, *, actor, reason, acting_for=None, idempotency_key=None, credential=None):
        return self._transition(agreement_id, "reject", actor=actor, acting_for=acting_for, reason=reason,
                                idempotency_key=idempotency_key, credential=credential)

    def withdraw(self, agreement_id, *, actor, reason=None, acting_for=None, idempotency_key=None, credential=None):
        return self._transition(agreement_id, "withdraw", actor=actor, acting_for=acting_for, reason=reason,
                                idempotency_key=idempotency_key, credential=credential)

    def retire(self, agreement_id, *, actor, reason=None, acting_for=None, idempotency_key=None, credential=None):
        return self._transition(agreement_id, "retire", actor=actor, acting_for=acting_for, reason=reason,
                                idempotency_key=idempotency_key, credential=credential)

    def activate(self, agreement_id, *, actor, acting_for=None, idempotency_key=None, credential=None):
        return self._transition(agreement_id, "activate", actor=actor, acting_for=acting_for,
                                idempotency_key=idempotency_key, credential=credential)

    def complete(self, agreement_id, *, actor, acting_for=None, idempotency_key=None, credential=None):
        return self._transition(agreement_id, "complete", actor=actor, acting_for=acting_for,
                                idempotency_key=idempotency_key, credential=credential)

    def terminate(self, agreement_id, *, actor, reason=None, acting_for=None, idempotency_key=None, credential=None):
        return self._transition(agreement_id, "terminate", actor=actor, acting_for=acting_for, reason=reason,
                                idempotency_key=idempotency_key, credential=credential)

    def revive(self, agreement_id, *, actor, acting_for=None, idempotency_key=None, credential=None):
        return self._transition(agreement_id, "revive", actor=actor, acting_for=acting_for,
                                idempotency_key=idempotency_key, credential=credential)

    # ── slot / mission binding (slice 4) ────────────────────────────────

    def bind_objects(self, agreement_id: str, **objects: Any) -> dict:
        """Set object refs (mission_id / slot_id / ...) on a NON-terminal agreement.

        Not a state transition (no receipt); the change is audited. Terminal
        agreements stay immutable (SQLite trigger + this check).
        """
        with self._lock:
            row = self._row(agreement_id)
            if row["state"] in TERMINAL_STATES:
                raise InvalidTransition(
                    f"cannot bind objects on agreement {agreement_id}: state is "
                    f"'{row['state']}' (terminal and immutable)")
            cur = json.loads(row["objects_json"] or "{}")
            cur.update({k: v for k, v in objects.items() if v is not None})
            self._conn.execute("UPDATE agreements SET objects_json=? WHERE agreement_id=?",
                               (self._j(cur), agreement_id))
            if self._audit_fn is not None:
                try:
                    self._audit_fn("workentry", "agreement_bind_objects",
                                   {"agreement_id": agreement_id, "objects": objects, "agent": "system"})
                except Exception:  # noqa: BLE001 - the transition receipts carry the provenance
                    pass
            return self._agreement(self._row(agreement_id))

    def compensate(self, agreement_id: str, *, stage: str, reason: str,
                   actor: str = "system") -> dict:
        """Compensating ``terminated`` after a failed slot/mission write (H2: no orphans).

        Writes an explicit evidence_gap linked from the terminate receipt. Provenance
        failure inside the compensation itself commits with a gap rather than rolling
        back, because leaving the orphan active agreement is the worse outcome.
        """
        key = f"compensate-{uuid.uuid4().hex}"

        def run() -> dict:
            row = self._row(agreement_id)
            if row["state"] not in TRANSITIONS["terminate"]["from"]:
                return {"agreement": self._agreement(row), "receipt": None, "replayed": True}
            rc = self._step(agreement_id, "terminate", actor=actor, reason=f"compensating: {reason}",
                            key=key, seq=self._next_seq(agreement_id),
                            gap_note={"attempted": "bind", "stage": stage, "reason": reason})
            return {"agreement": self._agreement(self._row(agreement_id)), "receipt": rc, "replayed": False}

        with self._lock:
            prior, self._policy = self._policy, "evidence_gap"
            try:
                return self._txn(run)
            finally:
                self._policy = prior

    # ── dormancy (no auto-expiry) ───────────────────────────────────────

    def record_activity(self, agreement_id: str, *, actor: str, acting_for: str | None = None,
                        credential: str | None = None) -> dict:
        """Any activity by either party. Revives a dormant entry to pending;
        on other live states it only refreshes last_activity_at (no receipt)."""
        with self._lock:
            row = self._row(agreement_id)
            if row["state"] == "dormant":
                return self.revive(agreement_id, actor=actor, acting_for=acting_for, credential=credential)
            if row["state"] in TERMINAL_STATES:
                raise InvalidTransition(
                    f"cannot record activity on agreement {agreement_id}: state is "
                    f"'{row['state']}' (terminal and immutable)")
            who = self._effective_principal(actor, acting_for)
            if who not in (row["entrant_id"], row["owner_id"]):
                raise AuthorityError(f"'{actor}' is not a party to {agreement_id}")
            self._conn.execute("UPDATE agreements SET last_activity_at=? WHERE agreement_id=?",
                               (self._now(), agreement_id))
            return {"agreement": self._agreement(self._row(agreement_id)), "receipt": None, "replayed": False}

    def sweep_dormant(self, *, after: timedelta = DORMANT_AFTER) -> list[str]:
        """pending with no activity for >= 14 days -> dormant (non-terminal, kept)."""
        cutoff = self._clock() - after
        with self._lock:
            rows = self._conn.execute(
                "SELECT agreement_id, last_activity_at FROM agreements WHERE state='pending'").fetchall()
        changed = []
        for r in rows:
            if datetime.fromisoformat(r["last_activity_at"]) <= cutoff:
                try:
                    self._transition(r["agreement_id"], "go_dormant", actor="system",
                                     reason="no activity for 14 days")
                    changed.append(r["agreement_id"])
                except InvalidTransition:
                    continue  # raced with a real transition
        return changed

    def pending_stale(self, *, older_than: timedelta) -> list[dict]:
        """Pending agreements whose last activity is at least ``older_than`` old."""
        cutoff = self._clock() - older_than
        with self._lock:
            rows = self._conn.execute("SELECT * FROM agreements WHERE state='pending'").fetchall()
            return [self._agreement(r) for r in rows
                    if datetime.fromisoformat(r["last_activity_at"]) <= cutoff]

    def claim_flag(self, agreement_id: str, flag: str, mark: str) -> bool:
        """Record a non-authoritative one-shot mark. True only the first time for this
        ``mark`` (e.g. an activity stamp), so a prompt is sent once per quiet spell."""
        with self._lock:
            row = self._conn.execute(
                "SELECT mark FROM agreement_flags WHERE agreement_id=? AND flag=?",
                (agreement_id, flag)).fetchone()
            if row is not None and row["mark"] == mark:
                return False
            self._conn.execute(
                "INSERT INTO agreement_flags (agreement_id, flag, mark, at) VALUES (?,?,?,?)"
                " ON CONFLICT(agreement_id, flag) DO UPDATE SET mark=excluded.mark, at=excluded.at",
                (agreement_id, flag, mark, self._now()))
            return True

    # ── queries ─────────────────────────────────────────────────────────

    def get(self, agreement_id: str) -> dict:
        with self._lock:
            return self._agreement(self._row(agreement_id))

    def list(self, *, entrant: str | None = None, owner: str | None = None,
             opportunity_ref: str | None = None, state: str | None = None) -> list[dict]:
        where, args = [], []
        for col, val in (("entrant_id", entrant), ("owner_id", owner),
                         ("opportunity_ref", opportunity_ref), ("state", state)):
            if val is not None:
                where.append(f"{col}=?"); args.append(val)
        sql = "SELECT * FROM agreements" + (" WHERE " + " AND ".join(where) if where else "") \
              + " ORDER BY created_at, agreement_id"
        with self._lock:
            return [self._agreement(r) for r in self._conn.execute(sql, args).fetchall()]

    def list_by_object(self, key: str, value: str) -> list[dict]:
        """Agreements whose ``objects[key] == value`` (e.g. mission_id / slot_id)."""
        if key not in ("post_id", "mission_id", "slot_id"):
            raise ValueError("unsupported object key")
        with self._lock:
            rows = self._conn.execute(
                f"SELECT * FROM agreements WHERE json_extract(objects_json, '$.{key}')=?"
                " ORDER BY created_at, agreement_id", (value,)).fetchall()
            return [self._agreement(r) for r in rows]

    def record_gap(self, agreement_id: str, *, attempted: str, stage: str, reason: str,
                   actor: str = "system", resolution: str = "recorded") -> str:
        """Append an explicit evidence_gap (never silent) for a failure outside a transition."""
        gap_id = f"gap-{uuid.uuid4().hex[:12]}"
        with self._lock:
            self._conn.execute(
                "INSERT INTO evidence_gaps (gap_id, agreement_id, receipt_id, attempted_transition, stage,"
                " reason, actor, idempotency_key, resolution, at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (gap_id, agreement_id, None, attempted, stage, reason, actor, None, resolution, self._now()))
        return gap_id

    def list_live(self, **filters: Any) -> list[dict]:
        """Non-terminal and not dormant (dormant entries are hidden, not removed)."""
        return [a for a in self.list(**filters) if a["state"] not in TERMINAL_STATES and a["state"] != "dormant"]

    def receipts(self, agreement_id: str) -> list[dict]:
        with self._lock:
            self._row(agreement_id)
            return [self._receipt(r) for r in self._conn.execute(
                "SELECT * FROM receipts WHERE agreement_id=? ORDER BY seq", (agreement_id,)).fetchall()]

    def get_receipt(self, receipt_id: str) -> dict:
        with self._lock:
            r = self._conn.execute("SELECT * FROM receipts WHERE receipt_id=?", (receipt_id,)).fetchone()
        if r is None:
            raise NotFound(f"receipt {receipt_id} not found")
        return self._receipt(r)

    def evidence_gaps(self, agreement_id: str | None = None) -> list[dict]:
        sql, args = "SELECT * FROM evidence_gaps", []
        if agreement_id:
            sql += " WHERE agreement_id=?"; args.append(agreement_id)
        with self._lock:
            return [dict(r) | {"agreement_id": r["agreement_id"]}
                    for r in self._conn.execute(sql + " ORDER BY at, gap_id", args).fetchall()]


