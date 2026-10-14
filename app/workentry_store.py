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

from .anchor_outbox import content_digest

AGREEMENT_CLASS = "WorkEntryAgreement"
CLASS_VERSION = 1
SEED_SOURCE_TYPE = "work_entry_agreement"

FORCE_ASSIGN = "force_assign"   # Agreement origin: an operator assigned the agent (P2 Q9 / P5 G5)
ENTRY_MODES = ("open", "standard", "constitutional")
TERMINAL_STATES = frozenset({"rejected", "withdrawn", "retired", "terminated", "completed"})
LIVE_STATES = ("intent", "pending", "dormant", "accepted", "active")  # F12 "non-terminal"
DORMANT_AFTER = timedelta(days=14)          # fallback; the live value is config/economic_rates.json "workentry_pending"
ASK_POSTER_AFTER = timedelta(hours=48)      # fallback, same source
ANCHOR_STATES = frozenset({"completed"})   # P5/Q5: only completed Agreements anchor through ProofPress



ANSWER_WINDOW_FLOOR_HOURS = 12.0     # fallbacks for the poster-declared answer window bounds (D)
ANSWER_WINDOW_CEILING_HOURS = 168.0


def _pending_cfg() -> dict:
    from . import economy
    try:
        return (economy._load_rates() or {}).get("workentry_pending") or {}
    except Exception:  # noqa: BLE001
        return {}


def _pos(v) -> float | None:
    return None if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0 else float(v)


def tier_multipliers_configured() -> bool:
    """True when config carries any tier multiplier other than 1 (so the tier lookup is worth doing)."""
    tm = _pending_cfg().get("tier_multipliers")
    return isinstance(tm, dict) and any(_pos(v) not in (None, 1.0) for v in tm.values())


def pending_timers(mode: str | None = None, tier: str | None = None,
                   answer_window_hours: float | None = None) -> tuple[timedelta, timedelta]:
    """(ask-the-poster, dormant) windows for a quiet pending entry, read from config at call time
    so a CIVITAS vote changes them without a deploy. Missing or invalid values fall back.

    Optional refinements (all display/nudge timing only; nothing expires and no money is touched):
      * ``mode``: ``by_mode[mode]`` may override either window (open / standard / constitutional).
      * ``tier``: ``tier_multipliers[tier]`` scales the ask window only (never dormancy).
      * ``answer_window_hours``: the poster's declared window, clamped to the configured
        floor/ceiling; it replaces the ask window (and wins over the tier multiplier).
    The ask window never exceeds the dormant window."""
    cfg = _pending_cfg()
    by_mode = cfg.get("by_mode")
    over = by_mode.get(mode) if isinstance(by_mode, dict) and isinstance(by_mode.get(mode), dict) else {}

    def num(key: str, default: timedelta, unit: str) -> timedelta:
        v = _pos(over.get(key))
        if v is None:
            v = _pos(cfg.get(key))
        return default if v is None else timedelta(**{unit: v})

    ask = num("ask_poster_after_hours", ASK_POSTER_AFTER, "hours")
    dormant = num("dormant_after_days", DORMANT_AFTER, "days")
    tm = cfg.get("tier_multipliers")
    mult = _pos(tm.get(tier)) if isinstance(tm, dict) and tier else None
    if mult is not None:
        ask = ask * mult
    declared = _pos(answer_window_hours)
    if declared is not None:
        lo = _pos(cfg.get("answer_window_min_hours")) or ANSWER_WINDOW_FLOOR_HOURS
        hi = _pos(cfg.get("answer_window_max_hours")) or ANSWER_WINDOW_CEILING_HOURS
        ask = timedelta(hours=min(max(declared, lo), max(hi, lo)))
    return (min(ask, dormant), dormant)


# Constitutional gate (slice 5). GOV-001 s9.3: committee recommendations are advisory unless the
# Council delegates binding authority by a two-thirds vote; the setting flips without code change.
BINDING_ADVISORY = "advisory_with_owner_countersign"
BINDING_DELEGATED = "council_delegated"
BINDING_AUTHORITIES = (BINDING_ADVISORY, BINDING_DELEGATED)
GATE_QUORUM_FRACTION = 0.5        # GOV-005 Art. 2: constitutional quorum = 50% of eligible attendees
DEFAULT_GATE_WINDOW_HOURS = 24.0  # GOV-005 s5.3: async votes stay open at least 24 h

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
# Entity / Node hooks (slice 10). All nullable, additive and open: unknown keys / values are stored as given.
OBJECT_HOOKS = ("formation_id", "node_id", "entity_id", "relation_id", "economic_terms_id",
                "domain_id", "contribution_id", "escrow_id", "task_id")
SEED_HOOKS = ("node_id", "entity_id", "formation_id")
KNOWN_PRINCIPAL_TYPES = ("agent", "person", "operator", "poster_link", "platform", "entity", "node_actor")


def derive_principal_type(ident: str | None, credential_ref: str | None = None) -> str:
    """Default principal_type from the credential / actor kind (the field itself is open)."""
    cred, who = credential_ref or "", ident or ""
    if cred.startswith("poster-link:") or who.startswith("poster-link:"):
        return "poster_link"
    if cred.startswith("operator#") or who.startswith("operator"):
        return "operator"
    if who.startswith("poster:"):
        return "person"
    if who in ("system", "platform") or who.startswith("platform"):
        return "platform"
    return "agent"


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


class GateRequired(WorkEntryError):
    """Constitutional gate (P4 slice 5) is not satisfied."""
    status = 409
    code = "governance_gate_required"


class ProvenanceError(WorkEntryError):
    status = 500
    code = "provenance_failure"

    def __init__(self, message: str, gap_id: str):
        super().__init__(message)
        self.gap_id = gap_id


class OwnerCountersignRequired(GateRequired):
    code = "owner_countersign_required"


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
    last_activity_at TEXT NOT NULL,
    participation_ref TEXT
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

-- Constitutional gate results recorded on the agreement (slice 5). Append-only except the
-- one-time owner countersign.
CREATE TABLE IF NOT EXISTS agreement_gates (
    gate_id              TEXT PRIMARY KEY,
    agreement_id         TEXT NOT NULL,
    meeting_id           TEXT NOT NULL,
    motion_id            TEXT NOT NULL UNIQUE,
    result               TEXT NOT NULL,
    yeas                 INTEGER NOT NULL,
    nays                 INTEGER NOT NULL,
    abstain              INTEGER NOT NULL,
    eligible             INTEGER NOT NULL,
    quorum_required      INTEGER NOT NULL,
    quorum_met           INTEGER NOT NULL,
    opened_at            TEXT,
    closes_at            TEXT,
    recorded_at          TEXT NOT NULL,
    binding_authority    TEXT NOT NULL,
    record_seed_doi      TEXT,
    record_audit_hash    TEXT,
    countersigned_by     TEXT,
    countersigned_at     TEXT,
    countersign_credential TEXT,
    countersign_seed_doi TEXT,
    countersign_audit_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_gate_agr ON agreement_gates(agreement_id);
CREATE TRIGGER IF NOT EXISTS trg_gate_no_delete BEFORE DELETE ON agreement_gates
BEGIN SELECT RAISE(ABORT, 'agreement_gates are never deleted (archive)'); END;
CREATE TRIGGER IF NOT EXISTS trg_gate_countersign_once BEFORE UPDATE ON agreement_gates
WHEN OLD.countersigned_at IS NOT NULL OR NEW.result IS NOT OLD.result OR NEW.motion_id IS NOT OLD.motion_id
BEGIN SELECT RAISE(ABORT, 'agreement_gates are append-only'); END;

CREATE TABLE IF NOT EXISTS workentry_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    at    TEXT NOT NULL
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

-- Agreement-bound deploy receipts (slice 6). One row per mission-scoped deploy; append-only.
-- Deploy is not an agreement state change; the receipt + Seed are the durable record.
CREATE TABLE IF NOT EXISTS deployments (
    deploy_id       TEXT PRIMARY KEY,
    receipt_id      TEXT NOT NULL UNIQUE,
    agreement_id    TEXT NOT NULL,
    mission_id      TEXT NOT NULL,
    actor           TEXT NOT NULL,
    acting_for      TEXT,
    credential_ref  TEXT,
    entry_mode      TEXT NOT NULL,
    gate_id         TEXT,
    note            TEXT,
    idempotency_key TEXT,
    at              TEXT NOT NULL,
    seed_doi        TEXT NOT NULL,
    audit_hash      TEXT
);
CREATE INDEX IF NOT EXISTS idx_dep_agr ON deployments(agreement_id);
CREATE INDEX IF NOT EXISTS idx_dep_mission ON deployments(mission_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_dep_key ON deployments(agreement_id, actor, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
CREATE TRIGGER IF NOT EXISTS trg_dep_no_update BEFORE UPDATE ON deployments
BEGIN SELECT RAISE(ABORT, 'deployments are append-only'); END;
CREATE TRIGGER IF NOT EXISTS trg_dep_no_delete BEFORE DELETE ON deployments
BEGIN SELECT RAISE(ABORT, 'deployments are append-only'); END;
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
        anchors: Any | None = None,
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
        self._anchors = anchors      # P5 ProofPress anchor outbox (None = feature off)
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
        acols = {r[1] for r in self._conn.execute("PRAGMA table_info(agreements)").fetchall()}
        if "participation_ref" not in acols:   # slice 10: nullable parent link to the Participation agreement
            self._conn.execute("ALTER TABLE agreements ADD COLUMN participation_ref TEXT")

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
            "principals": self._typed_principals(json.loads(row["principals_json"])),
            "objects": {**dict.fromkeys(OBJECT_HOOKS), **json.loads(row["objects_json"])},
            "participation_ref": row["participation_ref"],
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
    def _typed_principals(principals: list[dict]) -> list[dict]:
        """Lazy backfill: derive principal_type for rows stored before slice 10 (read-only; never written)."""
        out = []
        for p in principals:
            if isinstance(p, dict) and not p.get("principal_type"):
                p = {**p, "principal_type": derive_principal_type(p.get("id"), p.get("credential_ref"))}
            out.append(p)
        return out

    def _receipt(self, r: sqlite3.Row) -> dict:
        obj_row = self._conn.execute("SELECT objects_json FROM agreements WHERE agreement_id=?",
                                     (r["agreement_id"],)).fetchone()
        objs = json.loads(obj_row[0]) if obj_row else {}
        return {
            "actor_type": derive_principal_type(r["actor"], r["credential_ref"]),
            "acting_for_type": derive_principal_type(r["acting_for"]) if r["acting_for"] else None,
            "economic_terms_id": objs.get("economic_terms_id"), "escrow_id": objs.get("escrow_id"),
            "receipt_id": r["receipt_id"], "agreement_id": r["agreement_id"],
            "transition": r["transition"], "from": r["from_state"], "to": r["to_state"],
            "actor": r["actor"], "acting_for": r["acting_for"], "at": r["at"],
            "seed_doi": r["seed_doi"], "audit_hash": r["audit_hash"],
            "idempotency_key": r["idempotency_key"], "reason": r["reason"],
            "evidence_gap_id": r["evidence_gap_id"],
            "credential_ref": r["credential_ref"],
            **self._anchor_view(r["receipt_id"]),
        }

    def _anchor_view(self, receipt_id: str) -> dict:
        """Receipts are append-only; the anchor status lives in the outbox and is joined here."""
        if self._anchors is None:
            return {}
        try:
            return {"anchor": self._anchors.for_receipt(receipt_id) or {"anchor": "none"}}
        except Exception:  # noqa: BLE001 - a read never fails on the anchor side
            return {}

    def _anchor_after_commit(self, receipts: list[dict]) -> None:
        """Queue an anchor job for completed-Agreement receipts only (Q5). Runs AFTER the COMMIT; never raises."""
        if self._anchors is None:
            return
        for rc in receipts:
            try:
                if rc.get("to") not in ANCHOR_STATES:
                    continue
                with self._lock:
                    row = self._conn.execute("SELECT terms_json, objects_json FROM agreements WHERE agreement_id=?",
                                             (rc["agreement_id"],)).fetchone()
                terms_digest = content_digest(json.loads(row["terms_json"])) if row else None
                self._anchors.enqueue(
                    f"agreement.{rc['to']}", rc["agreement_id"],
                    {"agreement_id": rc["agreement_id"], "receipt_id": rc["receipt_id"], "seed_doi": rc["seed_doi"],
                     "transition": rc["transition"], "from": rc["from"], "to": rc["to"], "actor": rc["actor"],
                     "acting_for": rc["acting_for"], "at": rc["at"], "terms_digest": terms_digest,
                     "economic_terms_id": rc.get("economic_terms_id"), "escrow_id": rc.get("escrow_id")},
                    digest=content_digest({"receipt_id": rc["receipt_id"], "agreement_id": rc["agreement_id"],
                                           "transition": rc["transition"], "to": rc["to"], "at": rc["at"],
                                           "seed_doi": rc["seed_doi"], "terms_digest": terms_digest}),
                    receipt_id=rc["receipt_id"], seed_doi=rc["seed_doi"],
                    dedupe_key=f"agreement:{rc['receipt_id']}")
            except Exception as exc:  # noqa: BLE001 - the interaction already committed
                import logging
                logging.getLogger("civitae").warning("anchor enqueue skipped for %s: %s", rc.get("receipt_id"), exc)

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
        if name in ("accept", "reject") and json.loads(row["governance_json"]).get("origin") == FORCE_ASSIGN:
            # the operator assigned it, so only the assigned agent itself may take it or turn it down:
            # no delegate, no owner, no operator acting for either side
            if actor != entrant:
                raise AuthorityError(f"'{name}' on a force-assigned entry requires the assigned agent "
                                     f"itself; '{actor}' may not act for it")
            return
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
        if creating:
            cur_objects, cur_class = new_agreement["objects"], new_agreement.get("agreement_class") or AGREEMENT_CLASS
        else:
            _r = self._row(aid)
            cur_objects, cur_class = json.loads(_r["objects_json"] or "{}"), _r["agreement_class"]
        seed_meta = {"transition": name, "from": from_state, "to": to_state,
                     "receipt_id": receipt_id, "acting_for": acting_for or "",
                     "reason": reason or "", "agreement_class": cur_class,
                     # the genesis Seed is the Agreement's own origin, NOT a Node Root Seed (1D s5.4)
                     "kind": "work_entry_genesis" if creating else "work_entry_transition",
                     **({"origin": new_agreement["origin"]} if creating and new_agreement.get("origin") else {}),
                     **{k: cur_objects[k] for k in SEED_HOOKS if cur_objects.get(k)}}

        seed_doi: str | None = None
        audit_hash: str | None = None
        gap_id: str | None = None
        failure: _ProvenanceFailure | None = None
        try:
            seed = self._seed_fn(
                source_type=SEED_SOURCE_TYPE, source_id=aid, creator_id=actor,
                creator_type="BI" if actor.startswith("operator:") else "AAI",
                seed_type="planted" if creating else "grown", parent_doi=last_seed,
                metadata=seed_meta)
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
                " last_seed_doi, created_at, updated_at, last_activity_at, participation_ref)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (aid, cur_class, a.get("class_version") or CLASS_VERSION, a["entrant"], a["owner"],
                 self._j(a["principals"]), self._j(a["objects"]), a["opportunity_ref"],
                 self._j(a["terms"]), self._j(a["governance"]), a["entry_mode"], to_state, None,
                 key if a.get("key_supplied") else None, a.get("supersedes"), None, seed_doi, seed_doi,
                 now, now, now, a.get("participation_ref")))
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
        principal_types: dict | None = None, participation_ref: str | None = None,
        agreement_class: str | None = None, class_version: int | None = None,
        origin: str | None = None, assigned_by: str | None = None,
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
        objects = {"post_id": None, "mission_id": None, "slot_id": None, **dict.fromkeys(OBJECT_HOOKS),
                   **(objects or {})}
        ptypes = principal_types or {}
        creds = credential_refs or {}
        key_supplied = bool(idempotency_key)
        key = idempotency_key or f"auto-{uuid.uuid4().hex}"
        forced = origin == FORCE_ASSIGN
        if forced and not (assigned_by and assigned_by.startswith("operator:")):
            raise WorkEntryError("a force-assign must name the operator who assigned (assigned_by)")
        if forced:
            terms["assigned_by"] = assigned_by

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
                    {"role": "entrant", "id": entrant, "credential_ref": creds.get("entrant"),
                     "principal_type": ptypes.get("entrant") or derive_principal_type(entrant, creds.get("entrant"))},
                    {"role": "owner", "id": owner, "credential_ref": creds.get("owner"),
                     "principal_type": ptypes.get("owner") or derive_principal_type(owner, creds.get("owner"))}],
                "participation_ref": participation_ref,
                "agreement_class": agreement_class or AGREEMENT_CLASS,
                "class_version": class_version or CLASS_VERSION,
                "objects": objects, "opportunity_ref": opportunity_ref,
                "terms": {"pitch": terms.get("pitch"), "acceptance_payload": terms.get("acceptance_payload"),
                          "delivery_evidence_class": terms.get("delivery_evidence_class"),
                          "obligations_ref": terms.get("obligations_ref"),
                          "stake_ref": terms.get("stake_ref"),
                          **{k: v for k, v in terms.items() if k not in (
                              "pitch", "acceptance_payload", "delivery_evidence_class",
                              "obligations_ref", "stake_ref")}},
                "governance": {"mode": entry_mode, "posture": posture, "resolution_mode": resolution,
                               **({"origin": origin} if forced else {})},
                "origin": origin if forced else None,
                "entry_mode": entry_mode, "supersedes": supersedes, "key_supplied": key_supplied,
            }
            # a force-assign is the operator's act, not the entrant's: the operator is the actor on
            # the genesis and file steps (the agent has not yet done anything; it must still accept)
            who = assigned_by if forced else entrant
            why = f"force_assign by {assigned_by}" if forced else None
            receipts = [self._step(None, "create", actor=who, key=key, new_agreement=envelope, seq=1,
                                   credential=creds.get("entrant"), reason=why)]
            receipts.append(self._step(aid, "file", actor=who, key=key, seq=2,
                                       credential=creds.get("entrant"), reason=why))
            if entry_mode == "open":
                receipts.append(self._step(aid, "resolve_open", actor="system", key=key, seq=3))
                if auto_activate:
                    receipts.append(self._step(aid, "activate", actor=entrant, key=key, seq=4,
                                               credential=creds.get("entrant")))
            if supersedes:
                self._conn.execute("UPDATE agreements SET superseded_by=? WHERE agreement_id=?", (aid, supersedes))
            return {"agreement": self._agreement(self._row(aid)), "receipts": receipts, "replayed": False}

        out = self._txn(run)
        if not out.get("replayed"):
            self._anchor_after_commit(out.get("receipts") or [])
        return out

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
            step_reason = reason
            if name in ("accept", "activate") and row["entry_mode"] == "constitutional":
                note = self._gate_note(agreement_id)      # raises GateRequired when not satisfied
                if name == "accept":
                    step_reason = note
            receipt = self._step(agreement_id, name, actor=actor, acting_for=acting_for, reason=step_reason,
                                 key=key, seq=self._next_seq(agreement_id), credential=credential)
            return {"agreement": self._agreement(self._row(agreement_id)), "receipt": receipt, "replayed": False}

        out = self._txn(run)
        if not out.get("replayed"):
            self._anchor_after_commit([out["receipt"]])
        return out

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

    # ── constitutional gate (slice 5) ───────────────────────────────────

    def now_dt(self) -> datetime:
        return self._clock()

    def _setting(self, key: str, default: str) -> str:
        r = self._conn.execute("SELECT value FROM workentry_settings WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default

    @property
    def binding_authority(self) -> str:
        import os
        with self._lock:
            return self._setting("binding_authority",
                                 os.environ.get("CIVITAE_BINDING_AUTHORITY", BINDING_ADVISORY))

    @property
    def gate_window_hours(self) -> float:
        import os
        with self._lock:
            return float(self._setting("gate_window_hours",
                                       os.environ.get("CIVITAE_GATE_WINDOW_HOURS",
                                                      str(DEFAULT_GATE_WINDOW_HOURS))))

    def gate_settings(self) -> dict:
        return {"binding_authority": self.binding_authority, "gate_window_hours": self.gate_window_hours,
                "quorum_fraction": GATE_QUORUM_FRACTION, "binding_authorities": list(BINDING_AUTHORITIES)}

    def set_gate_settings(self, *, binding_authority: str | None = None,
                          gate_window_hours: float | None = None, actor: str = "operator:admin") -> dict:
        if binding_authority is not None and binding_authority not in BINDING_AUTHORITIES:
            raise WorkEntryError(f"binding_authority must be one of {list(BINDING_AUTHORITIES)}")
        if gate_window_hours is not None and gate_window_hours < 0:
            raise WorkEntryError("gate_window_hours must be >= 0")
        with self._lock:
            for k, v in (("binding_authority", binding_authority), ("gate_window_hours", gate_window_hours)):
                if v is not None:
                    self._conn.execute(
                        "INSERT INTO workentry_settings (key, value, at) VALUES (?,?,?)"
                        " ON CONFLICT(key) DO UPDATE SET value=excluded.value, at=excluded.at",
                        (k, str(v), self._now()))
                    if self._audit_fn is not None:
                        self._audit_fn("workentry", "gate_setting_changed",
                                       {"setting": k, "value": v, "agent": actor})
        return self.gate_settings()

    @staticmethod
    def _gate(r: sqlite3.Row) -> dict:
        d = dict(r)
        d["quorum_met"] = bool(d["quorum_met"])
        return d

    def gates(self, agreement_id: str) -> list[dict]:
        with self._lock:
            self._row(agreement_id)
            return [self._gate(r) for r in self._conn.execute(
                "SELECT * FROM agreement_gates WHERE agreement_id=? ORDER BY recorded_at, gate_id",
                (agreement_id,)).fetchall()]

    def gate_status(self, agreement_id: str) -> dict:
        with self._lock:
            row = self._row(agreement_id)
            authority = self.binding_authority
            required = row["entry_mode"] == "constitutional"
            gates = self.gates(agreement_id)
            sat = next((g for g in reversed(gates) if g["result"] == "passed"
                        and (authority == BINDING_DELEGATED or g["countersigned_at"])), None)
            passed = next((g for g in reversed(gates) if g["result"] == "passed"), None)
            reason = None
            if required and sat is None:
                if passed is not None:
                    reason = "owner_countersign_required"
                else:
                    reason = "governance_gate_required"
            return {"agreement_id": agreement_id, "required": required, "binding_authority": authority,
                    "satisfied": (not required) or sat is not None, "blocking": reason,
                    "gate_id": sat["gate_id"] if sat else None, "gates": gates}

    def _gate_note(self, agreement_id: str) -> str:
        st = self.gate_status(agreement_id)
        if st["satisfied"]:
            return f"gate {st['gate_id']} ({st['binding_authority']})"
        if st["blocking"] == "owner_countersign_required":
            raise OwnerCountersignRequired(
                "owner countersign required: the governance motion passed but is advisory "
                "(GOV-001 s9.3); an owner-held countersign is the binding act")
        raise GateRequired("governance gate required")

    def record_gate_result(self, agreement_id: str, *, meeting_id: str, motion_id: str, result: str,
                           yeas: int, nays: int, abstain: int, eligible: int, quorum_required: int,
                           quorum_met: bool, opened_at: str | None, closes_at: str | None,
                           actor: str = "system") -> dict:
        """Record a resolved gate motion on the agreement (idempotent per motion). Seed + audit
        are loud: failure rolls back and writes an evidence_gap."""
        if result not in ("passed", "failed"):
            raise WorkEntryError("gate result must be 'passed' or 'failed'")

        def run() -> dict:
            row = self._row(agreement_id)
            if row["entry_mode"] != "constitutional":
                raise InvalidTransition(f"agreement {agreement_id} is not constitutional; no gate applies")
            ex = self._conn.execute("SELECT * FROM agreement_gates WHERE motion_id=?", (motion_id,)).fetchone()
            if ex is not None:
                return {"gate": self._gate(ex), "replayed": True}
            if row["state"] in TERMINAL_STATES:
                raise InvalidTransition(f"agreement {agreement_id} is terminal ('{row['state']}'); "
                                        "a gate result cannot be recorded")
            gate_id = f"gate-{uuid.uuid4().hex[:12]}"
            seed_doi, audit_hash = self._gate_provenance(
                agreement_id, "gate_record", actor, gate_id,
                {"gate_id": gate_id, "motion_id": motion_id, "meeting_id": meeting_id, "result": result,
                 "yeas": yeas, "nays": nays, "eligible": eligible, "quorum_met": quorum_met},
                row["last_seed_doi"])
            self._conn.execute(
                "INSERT INTO agreement_gates (gate_id, agreement_id, meeting_id, motion_id, result, yeas, nays,"
                " abstain, eligible, quorum_required, quorum_met, opened_at, closes_at, recorded_at,"
                " binding_authority, record_seed_doi, record_audit_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (gate_id, agreement_id, meeting_id, motion_id, result, yeas, nays, abstain, eligible,
                 quorum_required, int(quorum_met), opened_at, closes_at, self._now(), self.binding_authority,
                 seed_doi, audit_hash))
            self._conn.execute("UPDATE agreements SET last_activity_at=? WHERE agreement_id=? AND state NOT IN ("
                               + _TERMINAL_SQL + ")", (self._now(), agreement_id))
            return {"gate": self._gate(self._conn.execute(
                "SELECT * FROM agreement_gates WHERE gate_id=?", (gate_id,)).fetchone()), "replayed": False}

        return self._txn(run)

    def countersign_gate(self, agreement_id: str, *, actor: str, credential: str | None = None) -> dict:
        """The owner-held binding act under advisory authority. Operator credential only."""
        if not actor.startswith("operator:"):
            raise AuthorityError("the gate countersign is owner-held: an operator (admin/owner) credential is required")

        def run() -> dict:
            row = self._row(agreement_id)
            if row["entry_mode"] != "constitutional":
                raise InvalidTransition(f"agreement {agreement_id} is not constitutional; no gate applies")
            if row["state"] in TERMINAL_STATES:
                raise InvalidTransition(f"agreement {agreement_id} is terminal ('{row['state']}')")
            if self.binding_authority == BINDING_DELEGATED:
                raise InvalidTransition("no countersign is needed: binding_authority is council_delegated")
            g = self._conn.execute(
                "SELECT * FROM agreement_gates WHERE agreement_id=? AND result='passed'"
                " AND countersigned_at IS NULL ORDER BY recorded_at DESC LIMIT 1", (agreement_id,)).fetchone()
            if g is None:
                raise GateRequired("no passed governance motion awaiting countersign")
            seed_doi, audit_hash = self._gate_provenance(
                agreement_id, "gate_countersign", actor, g["gate_id"],
                {"gate_id": g["gate_id"], "motion_id": g["motion_id"], "credential_ref": credential},
                row["last_seed_doi"])
            self._conn.execute(
                "UPDATE agreement_gates SET countersigned_by=?, countersigned_at=?, countersign_credential=?,"
                " countersign_seed_doi=?, countersign_audit_hash=? WHERE gate_id=?",
                (actor, self._now(), credential, seed_doi, audit_hash, g["gate_id"]))
            return {"gate": self._gate(self._conn.execute(
                "SELECT * FROM agreement_gates WHERE gate_id=?", (g["gate_id"],)).fetchone())}

        return self._txn(run)

    def _gate_provenance(self, aid: str, name: str, actor: str, gate_id: str, detail: dict,
                         parent: str | None) -> tuple[str | None, str | None]:
        """Seed + audit for a gate event. Failure is loud (rolls back, evidence_gap)."""
        try:
            seed = self._seed_fn(source_type="work_entry_gate", source_id=gate_id, creator_id=actor,
                                 creator_type="AAI", seed_type="grown", parent_doi=parent,
                                 metadata={**{k: str(v) for k, v in detail.items()}, "event": name,
                                           "agreement_id": aid, "agreement_class": AGREEMENT_CLASS})
            seed_doi = (seed or {}).get("doi")
            if not seed_doi:
                raise RuntimeError("seed writer returned no doi")
        except Exception as exc:  # noqa: BLE001
            raise _ProvenanceFailure("seed", f"{type(exc).__name__}: {exc}", name, aid, actor, None)
        audit_hash = None
        if self._audit_fn is not None:
            try:
                audit_hash = self._audit_fn("workentry", name,
                                            {"agreement_id": aid, "seed_doi": seed_doi, "agent": actor, **detail})
            except Exception as exc:  # noqa: BLE001
                raise _ProvenanceFailure("audit", f"{type(exc).__name__}: {exc}", name, aid, actor, None)
        return seed_doi, audit_hash

    # ── agreement-bound deploy (slice 6) ────────────────────────────────

    @staticmethod
    def _deployment(r: sqlite3.Row) -> dict:
        return {"receipt_id": r["receipt_id"], "deploy_id": r["deploy_id"], "agreement_id": r["agreement_id"],
                "mission_id": r["mission_id"], "transition": "deploy", "actor": r["actor"],
                "acting_for": r["acting_for"], "credential_ref": r["credential_ref"],
                "entry_mode": r["entry_mode"], "gate_id": r["gate_id"], "note": r["note"],
                "idempotency_key": r["idempotency_key"], "at": r["at"], "seed_doi": r["seed_doi"],
                "audit_hash": r["audit_hash"]}

    def deployments(self, agreement_id: str | None = None, mission_id: str | None = None) -> list[dict]:
        where, args = [], []
        for col, val in (("agreement_id", agreement_id), ("mission_id", mission_id)):
            if val is not None:
                where.append(f"{col}=?"); args.append(val)
        sql = "SELECT * FROM deployments" + (" WHERE " + " AND ".join(where) if where else "")
        with self._lock:
            return [self._deployment(r) for r in self._conn.execute(
                sql + " ORDER BY at, deploy_id", args).fetchall()]

    def record_deploy(self, agreement_id: str, *, mission_id: str, actor: str, acting_for: str | None = None,
                      credential: str | None = None, entry_mode: str, gate_id: str | None = None,
                      note: str | None = None, idempotency_key: str | None = None) -> dict:
        """Receipt + Seed for a mission-scoped deploy under an ACTIVE agreement. Provenance is loud:
        a failed Seed/audit rolls the receipt back and writes an evidence_gap. Same (agreement, actor,
        key) returns the original receipt. Returns {receipt, replayed}."""
        def run() -> dict:
            row = self._row(agreement_id)
            if idempotency_key:
                ex = self._conn.execute(
                    "SELECT * FROM deployments WHERE agreement_id=? AND actor=? AND idempotency_key=?",
                    (agreement_id, actor, idempotency_key)).fetchone()
                if ex is not None:
                    return {"receipt": self._deployment(ex), "replayed": True}
            if row["state"] != "active":
                raise InvalidTransition(
                    f"agreement {agreement_id} is '{row['state']}'; deploy needs an active agreement")
            if json.loads(row["objects_json"]).get("mission_id") != mission_id:
                raise InvalidTransition(f"agreement {agreement_id} is not bound to mission {mission_id}")
            who = self._effective_principal(actor, acting_for)
            if who != row["owner_id"]:
                raise AuthorityError("deploy requires the agreement's owner (deploy authority); "
                                     f"'{who}' is not")
            deploy_id = f"dep-{uuid.uuid4().hex[:16]}"
            receipt_id = f"rcpt-{uuid.uuid4().hex[:16]}"
            now = self._now()
            try:
                seed = self._seed_fn(
                    source_type="work_entry_deploy", source_id=deploy_id, creator_id=actor,
                    creator_type="AAI", seed_type="grown", parent_doi=row["last_seed_doi"],
                    metadata={"event": "deploy", "deploy_id": deploy_id, "receipt_id": receipt_id,
                              "agreement_id": agreement_id, "mission_id": mission_id,
                              "entry_mode": entry_mode, "gate_id": gate_id or "",
                              "acting_for": acting_for or "", "agreement_class": AGREEMENT_CLASS})
                seed_doi = (seed or {}).get("doi")
                if not seed_doi:
                    raise RuntimeError("seed writer returned no doi")
            except Exception as exc:  # noqa: BLE001 - provenance must never be silent
                raise _ProvenanceFailure("seed", f"{type(exc).__name__}: {exc}", "deploy",
                                         agreement_id, actor, idempotency_key)
            audit_hash = None
            if self._audit_fn is not None:
                try:
                    audit_hash = self._audit_fn(
                        "workentry", "mission_deploy",
                        {"agreement_id": agreement_id, "mission_id": mission_id, "deploy_id": deploy_id,
                         "receipt_id": receipt_id, "seed_doi": seed_doi, "agent": actor,
                         "acting_for": acting_for, "credential_ref": credential, "entry_mode": entry_mode})
                except Exception as exc:  # noqa: BLE001
                    raise _ProvenanceFailure("audit", f"{type(exc).__name__}: {exc}", "deploy",
                                             agreement_id, actor, idempotency_key)
            self._conn.execute(
                "INSERT INTO deployments (deploy_id, receipt_id, agreement_id, mission_id, actor, acting_for,"
                " credential_ref, entry_mode, gate_id, note, idempotency_key, at, seed_doi, audit_hash)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (deploy_id, receipt_id, agreement_id, mission_id, actor, acting_for, credential, entry_mode,
                 gate_id, note, idempotency_key, now, seed_doi, audit_hash))
            # keep the Seed lineage one hash chain; deploy is activity on a live agreement
            self._conn.execute("UPDATE agreements SET last_seed_doi=?, last_activity_at=? WHERE agreement_id=?",
                               (seed_doi, now, agreement_id))
            return {"receipt": self._deployment(self._conn.execute(
                "SELECT * FROM deployments WHERE deploy_id=?", (deploy_id,)).fetchone()), "replayed": False}

        return self._txn(run)

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

    def sweep_dormant(self, *, after: timedelta | None = None) -> list[str]:
        """pending with no activity for >= the configured window (14 days) -> dormant (non-terminal, kept).
        With ``after`` omitted the window is the configured one for each entry's mode."""
        now = self._clock()
        with self._lock:
            rows = self._conn.execute(
                "SELECT agreement_id, last_activity_at, entry_mode FROM agreements WHERE state='pending'").fetchall()
        changed = []
        for r in rows:
            win = after if after is not None else pending_timers(mode=r["entry_mode"])[1]
            days = win.total_seconds() / 86400
            if datetime.fromisoformat(r["last_activity_at"]) <= now - win:
                try:
                    self._transition(r["agreement_id"], "go_dormant", actor="system",
                                     reason=f"no activity for {days:g} days")
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

    def poster_response(self, owner_id: str) -> dict:
        """Median hours from entry to this owner's own ``accept`` on their opportunities, from
        stored timestamps. A displayed fact, never a rule: system-resolved (open mode) entries and
        unanswered ones are not samples."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT a.created_at AS c, MIN(h.at) AS t FROM agreements a"
                " JOIN agreement_history h ON h.agreement_id=a.agreement_id AND h.transition='accept'"
                " WHERE a.owner_id=? GROUP BY a.agreement_id", (owner_id,)).fetchall()
        hours = sorted((datetime.fromisoformat(r["t"]) - datetime.fromisoformat(r["c"])).total_seconds() / 3600
                       for r in rows)
        if not hours:
            return {"samples": 0, "median_hours": None}
        n, mid = len(hours), len(hours) // 2
        med = hours[mid] if n % 2 else (hours[mid - 1] + hours[mid]) / 2
        return {"samples": n, "median_hours": round(max(med, 0.0), 1)}

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


