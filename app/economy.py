"""
MO§ES™ Sovereign Economy — Trust ladder + tiered fees + agent treasury.

Four tiers (fee charged per mission payout, not per transaction).
The live rates come from config/economic_rates.json (single source of truth;
CIVITAS changes them by vote, not by deploy). The rates below are the
post-ratification TARGET and the code fallback when the config is absent:
  UNGOVERNED     — 15% fee, public bounties only
  GOVERNED       — 10% fee, all slots
  CONSTITUTIONAL —  5% fee, premium + priority (EARNED)
  BLACK CARD     —  2% fee, VIP access, big-time ops (PAID or EARNED at scale)

Fee Philosophy
──────────────
Fees are charged at the mission-level income event (mission close / payout),
not on individual slot fills or tool calls. A mission with 200 internal
transactions is one economic event: one fee, one ledger entry.

Trial Period
────────────
New agents receive a free trial: first TRIAL_MISSION_LIMIT missions OR
TRIAL_DAY_LIMIT days, whichever comes first.

  During trial:   0% fee, GOVERNED-tier access.
                  All fees that *would* have applied are tracked as trial_liability.
                  This is shown to the agent — transparent, not hidden.

  At trial end:
    STAY  → fees activate from the next mission. trial_liability forgiven.
    LEAVE → account archived. trial_liability zeroed. No obligation, no chase.

  On return after leaving:
    Status → "returned". Agent must settle their trial_liability before
    accessing slots. Once settled: fully active at governed tier.
    Return is always voluntary. No one is hunted.

Credits
───────
Originator credit  (-1% off tier rate):  awarded to the agent who created /
  posted the mission. You built the work — you get a write-off.
  Floor: 0.5% minimum (platform always earns something).

Recruiter bounty   (0.5% of platform cut): paid to whoever onboarded this
  agent into the universe, for their first RECRUITER_BOUNTY_MISSIONS missions.
  Funded from the platform's share — the recruited agent is not charged extra.

These credits are the economic incentive layer for network growth:
  create work → pay less · bring agents in → earn a perpetual micro-cut.

Constitutional is earned. Black Card is bought or earned at elite level.

──────────────────────────────────────────────────────────────
ECONOMIC PHILOSOPHY (for CIVITAS constitutional vote)
──────────────────────────────────────────────────────────────

The platform fee is a creation claim, not a tax.
The percentage is compensation for infrastructure built — the constitutional
framework, governance rails, slot marketplace, trust ladder — no more,
no less. Rates should reflect what was built, not what the market will bear.

This module handles FLOW 1 only. The full sovereign economy has 8 flows:

  FLOW 1 — Mission Fee       — % at mission close (this file)
  FLOW 2 — Premium Access    — Black Card subscription (perks, not just discount)
  FLOW 3 — Recruiter Bounty  — platform pays out to network builders
  FLOW 4 — Originator Credit — platform earns less from work creators (inverse)
  FLOW 5 — Signal Economy    — KASSA data gems, % back to signal generators
  FLOW 6 — Treasury Ops      — fees on governed cross-chain treasury movements
  FLOW 7 — Gov Certification — MO§ES™ stamp as a licensable credential mark
  FLOW 8 — Operator Licensing — white-label constitutional infra for enterprises

Because FLOW 1 is one of eight, mission fees can be kept genuinely low.
The platform does not need to extract maximum margin from agents —
it earns at scale across multiple flows.

Black Card is an Amex Centurion model, not a fee waiver.
The 2% rate is almost incidental. The product is access:
  kassa_founding_ops, governance_escalation_request, treasury_credit_line,
  first_fill_priority, multi_mission_concurrent, white_label_slots.
You pay for the room, not the discount.

All rates in this file are PROPOSALS pending CIVITAS vote.
The mechanisms are live. The numbers are drafts.

© 2026 Ello Cello LLC. Patent Pending: Serial No. 63/877,177
"""

try:
    import fcntl
except ImportError:
    fcntl = None  # Non-POSIX (Windows) — file locking unavailable
import hashlib
import json
import logging
import math
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

# ── Load flex rates from config (CIVITAS-voteable without code deploy) ──────
# Falls back to hardcoded defaults if config file is missing.

def _load_rates(config_path: Path | None = None) -> dict:
    """Load economic rates from config/economic_rates.json if present."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "economic_rates.json"
    try:
        if config_path.exists():
            return json.loads(config_path.read_text())
    except Exception:
        pass
    return {}

def _atomic_save(path: Path, data: dict) -> None:
    """Write JSON atomically: write to tmp, fsync, rename. Prevents partial writes."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    content = json.dumps(data, indent=2)
    with tmp.open("w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _locked_load(path: Path, default: dict) -> dict:
    """Read JSON with shared lock to avoid reading mid-write."""
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            if fcntl:
                fcntl.flock(f, fcntl.LOCK_SH)
            try:
                return json.load(f)
            finally:
                if fcntl:
                    fcntl.flock(f, fcntl.LOCK_UN)
    except (json.JSONDecodeError, OSError):
        return default


_RATES = _load_rates()
_TIER_OVERRIDES  = _RATES.get("tiers", {})
_CREDIT_CFG      = _RATES.get("credits", {})
_TRIAL_CFG       = _RATES.get("trial", {})
_SETTLE_CFG      = _RATES.get("settlement", {})

# Card-funded money (and anything paid out of it) cannot be cashed out for this many days.
_log = logging.getLogger(__name__)
CHARGEBACK_HOLD_DAYS = _SETTLE_CFG.get("chargeback_hold_days", 7)

# ── Platform-level Credit Constants ──────────────────────────────
# These apply on top of the tier fee rate at mission payout time.
# Loaded from config/economic_rates.json if present; hardcoded fallback otherwise.

ORIGINATOR_CREDIT         = _CREDIT_CFG.get("originator_credit",        0.01)
FEE_FLOOR                 = _CREDIT_CFG.get("fee_floor",                 0.005)
RECRUITER_BOUNTY_RATE     = _CREDIT_CFG.get("recruiter_bounty_rate",     0.005)
RECRUITER_BOUNTY_MISSIONS = _CREDIT_CFG.get("recruiter_bounty_missions", 10)

# ── Trial Period Constants ────────────────────────────────────────
TRIAL_MISSION_LIMIT = _TRIAL_CFG.get("mission_limit", 10)
TRIAL_DAY_LIMIT     = _TRIAL_CFG.get("day_limit",     7)
TRIAL_FEE_RATE      = _TRIAL_CFG.get("fee_rate",      0.0)

# Trial status values stored in agent record
TRIAL_STATUS_TRIAL    = "trial"
TRIAL_STATUS_ACTIVE   = "active"
TRIAL_STATUS_DEPARTED = "departed"
TRIAL_STATUS_RETURNED = "returned"


# ── Tier Definitions ──────────────────────────────────────────────

TIERS = {
    "ungoverned": {
        "label": "UNGOVERNED",
        "fee_rate": 0.15,
        "access": ["public_bounties"],
        "badge": None,
        "requirements": None,
    },
    "governed": {
        "label": "GOVERNED",
        "fee_rate": 0.10,
        "access": ["public_bounties", "standard_slots", "all_postures"],
        "badge": "governed",
        "requirements": {
            "governance_active": True,
        },
    },
    "constitutional": {
        "label": "CONSTITUTIONAL",
        "fee_rate": 0.05,
        "access": ["public_bounties", "standard_slots", "premium_slots", "priority_matching", "treasury_ops", "all_postures"],
        "badge": "constitutional",
        "requirements": {
            "governance_active": True,
            "dual_signature": True,
            "compliance_score_min": 0.90,
            "missions_completed_min": 10,
            "violations_last_30d": 0,
            "lineage_verified": True,
        },
    },
    "blackcard": {
        "label": "BLACK CARD",
        "fee_rate": 0.02,
        "access": [
            "public_bounties",
            "standard_slots",
            "premium_slots",
            "private_bounties",
            "priority_matching",
            "first_fill_priority",
            "treasury_ops",
            "all_postures",
            "cross_chain_unlimited",
            "multi_mission_concurrent",
            "custom_formations",
            "governance_escalation_request",
            "white_label_slots",
            "treasury_credit_line",
            "audit_export_credential",
            "platform_governance_vote",
            "financial_operations",
            "multi_agent_campaigns",
            "kassa_founding_ops",
        ],
        "badge": "blackcard",
        "revenue_split_bonus": 0.10,
        "max_concurrent_missions": 10,
        "first_fill_window_seconds": 60,
        "credit_line_pct": 0.20,
        "requirements_earned": {
            "governance_active": True,
            "dual_signature": True,
            "compliance_score_min": 0.95,
            "missions_completed_min": 50,
            "violations_last_30d": 0,
            "lineage_verified": True,
            "revenue_generated_min": 10000,
        },
        "requirements_paid": {
            "governance_active": True,
            "payment": True,
        },
        "price_usd": 2500,
    },
}

# Apply config overrides to tier fee_rates (CIVITAS vote changes config, not code)
for _tier_key, _tier_override in _TIER_OVERRIDES.items():
    if _tier_key in TIERS and "fee_rate" in _tier_override:
        TIERS[_tier_key]["fee_rate"] = _tier_override["fee_rate"]


class TrialLedger:
    """Tracks trial status and accrued liability for all agents.

    trial_liability = sum of fees that *would have* applied during the free trial.
    Shown to agent transparently so they know what settlement means if they return.
    """

    def __init__(self, data_dir: str | Path = "./data"):
        self.path = Path(data_dir) / "trial_ledger.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._store = self._load()

    def _load(self) -> dict:
        return _locked_load(self.path, {})

    def _save(self):
        _atomic_save(self.path, self._store)

    def get(self, agent_id: str) -> dict:
        return self._store.get(agent_id, {
            "status": TRIAL_STATUS_TRIAL,
            "trial_missions_used": 0,
            "trial_started": None,
            "trial_liability": 0.0,
            "departed_at": None,
            "returned_at": None,
            "settlement_paid": 0.0,
        })

    def init_trial(self, agent_id: str) -> dict:
        """Register a new agent into trial status."""
        record = {
            "status": TRIAL_STATUS_TRIAL,
            "trial_missions_used": 0,
            "trial_started": datetime.now(UTC).isoformat(),
            "trial_liability": 0.0,
            "departed_at": None,
            "returned_at": None,
            "settlement_paid": 0.0,
        }
        self._store[agent_id] = record
        self._save()
        return record

    def record_trial_mission(self, agent_id: str, would_have_paid: float) -> dict:
        """Track a mission completed during trial. Accrues liability."""
        rec = self.get(agent_id)
        rec["trial_missions_used"] = rec.get("trial_missions_used", 0) + 1
        rec["trial_liability"] = round(rec.get("trial_liability", 0.0) + would_have_paid, 4)
        self._store[agent_id] = rec
        self._save()
        return rec

    def is_in_trial(self, agent_id: str) -> bool:
        """True if agent is still within their free trial window."""
        from datetime import timedelta
        rec = self.get(agent_id)
        if rec["status"] != TRIAL_STATUS_TRIAL:
            return False
        if rec["trial_missions_used"] >= TRIAL_MISSION_LIMIT:
            return False
        if rec["trial_started"]:
            started = datetime.fromisoformat(rec["trial_started"])
            if (datetime.now(UTC) - started).days >= TRIAL_DAY_LIMIT:
                return False
        return True

    def trial_status_summary(self, agent_id: str) -> dict:
        """What the agent sees: where they are in the trial, what they owe."""
        rec = self.get(agent_id)
        missions_left = max(0, TRIAL_MISSION_LIMIT - rec.get("trial_missions_used", 0))
        return {
            "status": rec["status"],
            "trial_missions_used": rec.get("trial_missions_used", 0),
            "trial_missions_remaining": missions_left,
            "trial_liability": rec.get("trial_liability", 0.0),
            "trial_liability_note": (
                "Forgiven if you commit. Owed if you return after leaving."
                if rec["status"] == TRIAL_STATUS_TRIAL else
                "Settled." if rec["status"] == TRIAL_STATUS_ACTIVE else
                "Zeroed — you left clean." if rec["status"] == TRIAL_STATUS_DEPARTED else
                f"Settlement due: ${rec.get('trial_liability', 0.0):.2f}"
            ),
        }

    def commit(self, agent_id: str) -> dict:
        """Agent commits to stay. Trial liability forgiven. Fees activate."""
        rec = self.get(agent_id)
        rec["status"] = TRIAL_STATUS_ACTIVE
        rec["trial_liability"] = 0.0  # forgiven
        self._store[agent_id] = rec
        self._save()
        return {"committed": True, "agent_id": agent_id, "trial_liability_forgiven": True}

    def depart(self, agent_id: str) -> dict:
        """Agent chooses to leave. No obligation. No chase."""
        rec = self.get(agent_id)
        rec["status"] = TRIAL_STATUS_DEPARTED
        rec["departed_at"] = datetime.now(UTC).isoformat()
        # Liability preserved in record for transparency but agent owes nothing
        departed_liability = rec.get("trial_liability", 0.0)
        rec["trial_liability"] = 0.0  # zeroed — no obligation
        rec["_departed_liability_for_return"] = departed_liability  # stored if they come back
        self._store[agent_id] = rec
        self._save()
        return {
            "departed": True,
            "agent_id": agent_id,
            "note": "No harm, no foul. You're free. Come back anytime.",
        }

    def return_after_departure(self, agent_id: str) -> dict:
        """Agent returns after leaving. Restores trial_liability for settlement."""
        rec = self.get(agent_id)
        if rec["status"] != TRIAL_STATUS_DEPARTED:
            return {"error": "Agent is not in departed status", "status": rec["status"]}
        owed = rec.get("_departed_liability_for_return", 0.0)
        rec["status"] = TRIAL_STATUS_RETURNED
        rec["returned_at"] = datetime.now(UTC).isoformat()
        rec["trial_liability"] = owed  # reactivated — must settle before slot access
        self._store[agent_id] = rec
        self._save()
        return {
            "returned": True,
            "agent_id": agent_id,
            "settlement_due": owed,
            "note": (
                f"Welcome back. Settlement of ${owed:.2f} required to activate slots."
                if owed > 0 else
                "Welcome back. No settlement needed — trial was empty."
            ),
        }

    def settle(self, agent_id: str, amount_paid: float) -> dict:
        """Agent pays their return settlement. Activates full access."""
        rec = self.get(agent_id)
        if rec["status"] != TRIAL_STATUS_RETURNED:
            return {"error": "Agent is not in returned status", "status": rec["status"]}
        owed = rec.get("trial_liability", 0.0)
        if round(amount_paid, 4) < round(owed, 4):
            return {
                "error": "Partial settlement not accepted",
                "owed": owed,
                "paid": amount_paid,
            }
        rec["status"] = TRIAL_STATUS_ACTIVE
        rec["settlement_paid"] = round(rec.get("settlement_paid", 0.0) + amount_paid, 4)
        rec["trial_liability"] = 0.0
        self._store[agent_id] = rec
        self._save()
        return {
            "settled": True,
            "agent_id": agent_id,
            "amount_paid": amount_paid,
            "note": "Settlement accepted. Full access restored.",
        }


_TREASURY_SCHEMA = """
CREATE TABLE IF NOT EXISTS balances (agent_id TEXT PRIMARY KEY, balance REAL NOT NULL);
CREATE TABLE IF NOT EXISTS transactions (
    seq      INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT,
    reason   TEXT,
    doc      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_txn_agent ON transactions(agent_id);
CREATE TABLE IF NOT EXISTS holds (
    seq      INTEGER PRIMARY KEY AUTOINCREMENT,
    hold_id  TEXT NOT NULL UNIQUE,
    agent_id TEXT NOT NULL,
    doc      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_holds_agent ON holds(agent_id);
CREATE TABLE IF NOT EXISTS treasury_meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
"""


class AgentTreasury:
    """Per-agent balance ledger inside the sovereign economy.

    Durable on SQLite (the same pattern as EscrowStore): every balance read-modify-write
    (credit, debit, hold, release_hold) runs inside one BEGIN IMMEDIATE transaction that
    re-reads state from the database, never from a process cache, so two processes sharing
    the volume cannot lose an update or spend the same balance twice. An existing
    treasury.json is imported once on first start and left on disk untouched.
    TREASURY_STORE=json keeps the legacy single-process JSON file (local/dev fallback).
    """

    def __init__(self, data_dir: str | Path = "./data"):
        data_dir = Path(data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        self.json_path = data_dir / "treasury.json"
        self._lock = threading.RLock()
        self._depth = 0
        self._json = os.environ.get("TREASURY_STORE") == "json"
        if self._json:
            self.path = self.json_path
            self._conn = None
            self._jl = self._load_json()
            self._dirty = False
            return
        self.path = data_dir / "treasury.db"
        # isolation_level=None: transactions are managed explicitly.
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False, isolation_level=None, timeout=30)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_TREASURY_SCHEMA)
        self._import_json(self.json_path)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()

    # ── storage ─────────────────────────────────────────────────────────
    def _load_json(self) -> dict:
        led = _locked_load(self.json_path, {"balances": {}, "transactions": []})
        led.setdefault("holds", [])
        return led

    def _import_json(self, src: Path) -> int:
        """One-time import of a legacy treasury.json (left in place, untouched). Guarded by a
        meta row inside the write transaction, so concurrent first starts import exactly once."""
        if not src.exists():
            return 0
        try:
            led = json.loads(src.read_text(encoding="utf-8"))
            balances, txns, holds = dict(led.get("balances", {})), list(led.get("transactions", [])), list(led.get("holds", []))
        except Exception:  # noqa: BLE001 - unreadable legacy file: leave it, do not block boot
            _log.error("TREASURY IMPORT SKIPPED: %s exists but cannot be read; the treasury database starts "
                       "EMPTY. Repair the file and restart (the import is retried until it succeeds).", src)
            return 0
        with self._txn():
            if self._conn.execute("SELECT 1 FROM treasury_meta WHERE k='json_imported'").fetchone():
                return 0
            for agent_id, bal in balances.items():
                self._conn.execute("INSERT OR IGNORE INTO balances (agent_id, balance) VALUES (?,?)", (agent_id, bal))
            for t in txns:
                self._conn.execute("INSERT INTO transactions (agent_id, reason, doc) VALUES (?,?,?)",
                                   (t.get("agent_id"), t.get("reason"), json.dumps(t)))
            for h in holds:
                self._conn.execute("INSERT OR IGNORE INTO holds (hold_id, agent_id, doc) VALUES (?,?,?)",
                                   (h["hold_id"], h["agent_id"], json.dumps(h)))
            self._conn.execute("INSERT INTO treasury_meta (k, v) VALUES ('json_imported', ?)",
                               (datetime.now(UTC).isoformat(),))
        return len(txns)

    @contextmanager
    def _txn(self):
        """Serialize a read-modify-write. SQLite: one BEGIN IMMEDIATE (write lock held from the
        first read), rolled back on any error. JSON: the process lock, saved on exit."""
        with self._lock:
            if self._depth:
                self._depth += 1
                try:
                    yield
                finally:
                    self._depth -= 1
                return
            if self._json:
                self._depth = 1
                try:
                    yield
                    if self._dirty:
                        _atomic_save(self.json_path, self._jl)
                        self._dirty = False
                except BaseException:
                    self._jl = self._load_json()   # drop half-applied in-memory changes
                    self._dirty = False
                    raise
                finally:
                    self._depth = 0
                return
            self._conn.execute("BEGIN IMMEDIATE")
            self._depth = 1
            try:
                yield
                self._conn.execute("COMMIT")
            except BaseException:
                try:
                    self._conn.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise
            finally:
                self._depth = 0

    def atomic(self):
        """Public: run several treasury operations (credit + hold, ...) as ONE transaction, so no
        other process can observe or spend the state in between. Rolled back as a whole on error."""
        return self._txn()

    @contextmanager
    def _read(self):
        """A consistent snapshot for multi-statement reads (deferred txn; WAL readers never block)."""
        with self._lock:
            if self._json or self._depth:
                yield
                return
            self._conn.execute("BEGIN")
            self._depth = 1
            try:
                yield
            finally:
                self._depth = 0
                try:
                    self._conn.execute("COMMIT")
                except sqlite3.Error:
                    pass

    def _bal(self, agent_id: str) -> float:
        if self._json:
            return self._jl["balances"].get(agent_id, 0.0)
        r = self._conn.execute("SELECT balance FROM balances WHERE agent_id=?", (agent_id,)).fetchone()
        return r[0] if r else 0.0

    def _set_bal(self, agent_id: str, value: float) -> None:
        if self._json:
            self._jl["balances"][agent_id] = value
            self._dirty = True
            return
        self._conn.execute("INSERT INTO balances (agent_id, balance) VALUES (?,?)"
                           " ON CONFLICT(agent_id) DO UPDATE SET balance=excluded.balance", (agent_id, value))

    def _add_txn(self, txn: dict) -> None:
        if self._json:
            self._jl["transactions"].append(txn)
            self._dirty = True
            return
        self._conn.execute("INSERT INTO transactions (agent_id, reason, doc) VALUES (?,?,?)",
                           (txn.get("agent_id"), txn.get("reason"), json.dumps(txn)))

    def _txns(self, agent_id: str | None = None, limit: int | None = None) -> list[dict]:
        if self._json:
            rows = self._jl["transactions"]
            if agent_id:
                rows = [t for t in rows if t["agent_id"] == agent_id]
            return list(rows[-limit:] if limit else rows)
        q, args = "SELECT doc FROM transactions", []
        if agent_id:
            q += " WHERE agent_id=?"
            args.append(agent_id)
        if limit:
            rows = self._conn.execute(q + " ORDER BY seq DESC LIMIT ?", (*args, limit)).fetchall()[::-1]
        else:
            rows = self._conn.execute(q + " ORDER BY seq", args).fetchall()
        return [json.loads(r[0]) for r in rows]

    def _holds_all(self, agent_id: str | None = None) -> list[dict]:
        if self._json:
            return [h for h in self._jl["holds"] if agent_id is None or h["agent_id"] == agent_id]
        if agent_id is None:
            rows = self._conn.execute("SELECT doc FROM holds ORDER BY seq").fetchall()
        else:
            rows = self._conn.execute("SELECT doc FROM holds WHERE agent_id=? ORDER BY seq", (agent_id,)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def _add_hold(self, rec: dict) -> None:
        if self._json:
            self._jl["holds"].append(rec)
            self._dirty = True
            return
        self._conn.execute("INSERT INTO holds (hold_id, agent_id, doc) VALUES (?,?,?)",
                           (rec["hold_id"], rec["agent_id"], json.dumps(rec)))

    @property
    def _ledger(self) -> dict:
        """Read-only snapshot in the legacy ledger shape (balances, transactions, holds).
        Mutating the returned dict does not change the treasury."""
        with self._read():
            if self._json:
                return json.loads(json.dumps(self._jl))
            return {"balances": self.all_balances(), "transactions": self._txns(), "holds": self._holds_all()}

    # ── balances ────────────────────────────────────────────────────────
    def balance(self, agent_id: str) -> float:
        with self._read():
            return self._bal(agent_id)

    @staticmethod
    def _valid_amount(amount: float) -> bool:
        """Finite and non-negative: NaN would pass every later balance check, a negative flips the sign."""
        return isinstance(amount, (int, float)) and math.isfinite(amount) and amount >= 0

    def credit(self, agent_id: str, amount: float, reason: str, mission_id: str = "") -> dict:
        if not self._valid_amount(amount):
            raise ValueError(f"invalid credit amount: {amount!r}")
        with self._txn():
            new = self._bal(agent_id) + amount
            self._set_bal(agent_id, new)
            txn = {
                "id": hashlib.sha256(f"{agent_id}{amount}{datetime.now(UTC).isoformat()}".encode()).hexdigest()[:16],
                "agent_id": agent_id,
                "type": "credit",
                "amount": amount,
                "reason": reason,
                "mission_id": mission_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "balance_after": new,
            }
            self._add_txn(txn)
        return txn

    def debit(self, agent_id: str, amount: float, reason: str, chain: str = "", *,
              matured_only: bool = False) -> dict:
        """Debit inside one transaction that re-reads the balance. ``matured_only`` additionally
        requires ``amount <= matured_balance`` in the same transaction (withdraw / cashout), so
        the hold gate and the debit cannot be separated by another writer."""
        with self._txn():
            current = self._bal(agent_id)
            if not self._valid_amount(amount):
                return {"error": "Invalid amount", "balance": current, "requested": amount}
            if matured_only:
                matured = self._matured(agent_id, current)
                if amount > matured:
                    return {"error": "Insufficient matured balance", "balance": current,
                            "matured": matured, "requested": amount}
            if amount > current:
                return {"error": "Insufficient balance", "balance": current, "requested": amount}
            new = current - amount
            self._set_bal(agent_id, new)
            txn = {
                "id": hashlib.sha256(f"{agent_id}{amount}{datetime.now(UTC).isoformat()}".encode()).hexdigest()[:16],
                "agent_id": agent_id,
                "type": "debit",
                "amount": amount,
                "reason": reason,
                "chain": chain,
                "timestamp": datetime.now(UTC).isoformat(),
                "balance_after": new,
            }
            self._add_txn(txn)
        return txn

    # ── chargeback holds ────────────────────────────────────────────────
    # A hold marks part of a balance as not yet cashable. It never moves money; cashout and
    # withdrawal may only spend ``matured_balance``. Spending held money elsewhere is assumed
    # to consume the matured part first, so a hold can never be dodged by many small debits.

    def hold(self, agent_id: str, amount: float, *, reason: str, ref: str = "", days: float | None = None,
             charged_at: str | None = None) -> dict:
        """Hold ``amount`` for the chargeback window. The window runs from ``charged_at`` (when the
        underlying card charge succeeded), because that is when the dispute clock starts. With no
        charge time (non-card funding, or a record that never captured one) it falls back to now,
        and says so loudly: the hold is then longer than the card network's clock, never shorter."""
        if not self._valid_amount(amount):
            raise ValueError(f"invalid hold amount: {amount!r}")
        days = CHARGEBACK_HOLD_DAYS if days is None else days
        now = datetime.now(UTC)
        start, basis = now, "payout_time"
        if charged_at:
            try:
                start = datetime.fromisoformat(charged_at)
                if start.tzinfo is None:
                    start = start.replace(tzinfo=UTC)
                start, basis = min(start, now), "charge_time"   # a future charge time must not extend the hold
            except (TypeError, ValueError):
                start = now
        if basis == "payout_time":
            _log.warning("HOLD FALLBACK: no usable charge time for hold ref=%r agent=%s (charged_at=%r); "
                         "counting the %s-day chargeback window from payout time", ref, agent_id, charged_at, days)
        rec = {"hold_id": f"hold-{uuid.uuid4().hex[:10]}", "agent_id": agent_id, "amount": round(float(amount), 4),
               "reason": reason, "ref": ref, "created_at": now.isoformat(),
               "charged_at": start.isoformat() if basis == "charge_time" else None, "hold_basis": basis,
               "matures_at": (start + timedelta(days=days)).isoformat()}
        with self._txn():
            self._add_hold(rec)
        return rec

    def release_hold(self, hold_id: str) -> None:
        """Drop a hold (used only to undo one whose payout failed)."""
        with self._txn():
            if self._json:
                self._jl["holds"] = [h for h in self._jl["holds"] if h["hold_id"] != hold_id]
                self._dirty = True
            else:
                self._conn.execute("DELETE FROM holds WHERE hold_id=?", (hold_id,))

    def _force_mature(self, agent_id: str) -> None:
        """Test support: pretend every hold of ``agent_id`` has passed its window."""
        past = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
        with self._txn():
            for h in self._holds_all(agent_id):
                new = {**h, "matures_at": past}
                if self._json:
                    h["matures_at"] = past
                    self._dirty = True
                else:
                    self._conn.execute("UPDATE holds SET doc=? WHERE hold_id=?", (json.dumps(new), h["hold_id"]))

    def _open_holds(self, agent_id: str) -> list[dict]:
        now = datetime.now(UTC)
        return [h for h in self._holds_all(agent_id) if datetime.fromisoformat(h["matures_at"]) > now]

    def _held(self, agent_id: str, balance: float) -> float:
        return round(min(balance, sum(h["amount"] for h in self._open_holds(agent_id))), 4)

    def _matured(self, agent_id: str, balance: float) -> float:
        return round(max(0.0, balance - self._held(agent_id, balance)), 4)

    def held_balance(self, agent_id: str) -> float:
        with self._read():
            return self._held(agent_id, self._bal(agent_id))

    def matured_balance(self, agent_id: str) -> float:
        with self._read():
            return self._matured(agent_id, self._bal(agent_id))

    def held_until(self, agent_id: str) -> str | None:
        """When the last open hold matures (all of the balance is cashable from then), else None."""
        with self._read():
            holds = self._open_holds(agent_id)
            return max(h["matures_at"] for h in holds) if holds and self._held(agent_id, self._bal(agent_id)) > 0 else None

    def all_balances(self) -> dict:
        with self._read():
            if self._json:
                return dict(self._jl["balances"])
            return {a: b for a, b in self._conn.execute("SELECT agent_id, balance FROM balances ORDER BY rowid")}

    def history(self, agent_id: str = None, limit: int = 20) -> list:
        with self._read():
            return self._txns(agent_id, limit)

    def platform_revenue(self) -> float:
        with self._read():
            return sum(t["amount"] for t in self._txns() if t.get("reason") == "platform_fee")


class FeeCreditLedger:
    """Tracks prepaid fee credit balances per agent.

    Credits represent USD coverage of governance fees, purchased in advance.
    They are consumed automatically at mission settlement before charging the live fee rate.
    """

    def __init__(self, data_dir: str | Path = "./data"):
        self.path = Path(data_dir) / "fee_credits.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ledger = self._load()

    def _load(self) -> dict:
        return _locked_load(self.path, {"balances": {}, "transactions": []})

    def _save(self):
        _atomic_save(self.path, self._ledger)

    def balance(self, agent_id: str) -> float:
        return self._ledger["balances"].get(agent_id, 0.0)

    def credit(self, agent_id: str, amount: float, pack_name: str, stripe_session_id: str = "") -> dict:
        """Add fee coverage credits to an agent's balance. Idempotent on stripe_session_id
        (a replayed or retried webhook must not credit the same purchase twice)."""
        if stripe_session_id:
            prior = next((t for t in self._ledger["transactions"]
                          if t.get("type") == "credit" and t.get("stripe_session_id") == stripe_session_id), None)
            if prior is not None:
                return {**prior, "duplicate": True}
        self._ledger["balances"][agent_id] = self.balance(agent_id) + amount
        txn = {
            "id": hashlib.sha256(f"{agent_id}{amount}{datetime.now(UTC).isoformat()}".encode()).hexdigest()[:16],
            "agent_id": agent_id,
            "type": "credit",
            "amount": amount,
            "pack_name": pack_name,
            "stripe_session_id": stripe_session_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "balance_after": self._ledger["balances"][agent_id],
        }
        self._ledger["transactions"].append(txn)
        self._save()
        return txn

    def consume(self, agent_id: str, amount: float, mission_id: str = "") -> dict:
        """Consume fee credits at mission settlement. Returns amount actually consumed."""
        current = self.balance(agent_id)
        consumed = min(amount, current)
        if consumed <= 0:
            return {"consumed": 0.0, "balance_after": current}
        self._ledger["balances"][agent_id] = current - consumed
        txn = {
            "id": hashlib.sha256(f"{agent_id}{consumed}{datetime.now(UTC).isoformat()}".encode()).hexdigest()[:16],
            "agent_id": agent_id,
            "type": "consume",
            "amount": consumed,
            "mission_id": mission_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "balance_after": self._ledger["balances"][agent_id],
        }
        self._ledger["transactions"].append(txn)
        self._save()
        return {"consumed": consumed, "balance_after": self._ledger["balances"][agent_id], "txn": txn}

    def history(self, agent_id: str, limit: int = 20) -> list:
        txns = [t for t in self._ledger["transactions"] if t["agent_id"] == agent_id]
        return txns[-limit:]


class SovereignEconomy:
    """The economic engine. Determines tier, calculates fees, manages treasury."""

    def __init__(self, data_dir: str | Path = "./data"):
        self.treasury = AgentTreasury(data_dir)
        self.trials = TrialLedger(data_dir)
        self.fee_credits = FeeCreditLedger(data_dir)

    def determine_tier(self, agent_metrics: dict) -> str:
        """Determine an agent's tier based on metrics or payment status."""
        if not agent_metrics:
            return "ungoverned"

        # Black Card — paid OR earned at elite level
        if agent_metrics.get("blackcard_paid", False) and agent_metrics.get("governance_active", False):
            return "blackcard"

        # Black Card — earned through elite performance
        bc_reqs = TIERS["blackcard"]["requirements_earned"]
        compliance = agent_metrics.get("compliance_score", 0)
        missions = agent_metrics.get("missions_completed", 0)
        violations = agent_metrics.get("governance_violations", 0)
        has_lineage = agent_metrics.get("lineage_verified", False)
        has_dual_sig = agent_metrics.get("dual_signature", False)
        revenue = agent_metrics.get("revenue_generated", 0)

        if (compliance >= bc_reqs["compliance_score_min"]
                and missions >= bc_reqs["missions_completed_min"]
                and violations <= bc_reqs["violations_last_30d"]
                and has_lineage
                and has_dual_sig
                and revenue >= bc_reqs["revenue_generated_min"]):
            return "blackcard"

        # Constitutional — earned through strong performance
        const_reqs = TIERS["constitutional"]["requirements"]
        if (compliance >= const_reqs["compliance_score_min"]
                and missions >= const_reqs["missions_completed_min"]
                and violations <= const_reqs["violations_last_30d"]
                and has_lineage
                and has_dual_sig):
            return "constitutional"

        # Governed — governance is active
        if agent_metrics.get("governance_active", False):
            return "governed"

        return "ungoverned"

    def purchase_blackcard(self, agent_id: str) -> dict:
        """Purchase Black Card status. Returns payment details."""
        price = TIERS["blackcard"]["price_usd"]
        # Record the purchase
        self.treasury.debit("platform_escrow", 0, reason="blackcard_placeholder")  # tracking only
        txn = self.treasury.credit("platform", price, reason="blackcard_purchase", mission_id=f"bc-{agent_id}")
        return {
            "purchased": True,
            "agent_id": agent_id,
            "tier": "blackcard",
            "price_usd": price,
            "perks": list(TIERS["blackcard"]["access"]),
            "fee_rate": f"{int(TIERS['blackcard']['fee_rate'] * 100)}%",
            "revenue_split_bonus": f"+{int(TIERS['blackcard']['revenue_split_bonus'] * 100)}%",
            "max_concurrent_missions": TIERS["blackcard"]["max_concurrent_missions"],
            "first_fill_window": f"{TIERS['blackcard']['first_fill_window_seconds']}s priority",
            "credit_line": f"{int(TIERS['blackcard']['credit_line_pct'] * 100)}% of balance",
            "platform_transaction": txn,
            "note": "Black Card active. Governance still required. Welcome to the room.",
        }

    def calculate_fee(self, tier: str, gross_amount: float, originator: bool = False) -> dict:
        """Calculate platform fee based on tier, with optional originator credit.

        originator=True: agent created/posted this mission — earns ORIGINATOR_CREDIT
        discount off their tier rate (write-off for creating work).
        Effective rate is floored at FEE_FLOOR so platform always earns something.
        """
        tier_config = TIERS.get(tier, TIERS["ungoverned"])
        base_rate = tier_config["fee_rate"]
        credit_applied = ORIGINATOR_CREDIT if originator else 0.0
        effective_rate = max(base_rate - credit_applied, FEE_FLOOR)
        fee = round(gross_amount * effective_rate, 4)
        net = round(gross_amount - fee, 4)
        return {
            "tier": tier_config["label"],
            "gross": gross_amount,
            "base_rate": base_rate,
            "originator_credit": credit_applied,
            "effective_rate": effective_rate,
            "fee_rate_pct": f"{round(effective_rate * 100, 1)}%",
            "platform_fee": fee,
            "net_to_agent": net,
        }

    def process_mission_payout(
        self,
        agent_id: str,
        agent_metrics: dict,
        gross_amount: float,
        mission_id: str,
        originator_id: str = "",
        recruiter_id: str = "",
        agent_mission_count: int = 0,
    ) -> dict:
        """Mission-level payout — the canonical fee event.

        One fee calculation per mission close. Not per transaction, not per slot fill.
        A mission with 200 internal tool calls is still one economic event.

        originator_id: agent who created / posted the mission — gets originator credit
        recruiter_id:  agent who onboarded agent_id — gets recruiter bounty from
                       platform's cut for first RECRUITER_BOUNTY_MISSIONS missions
        agent_mission_count: how many missions agent_id has completed (for bounty gate)
        """
        tier = self.determine_tier(agent_metrics)
        is_originator = bool(originator_id and originator_id == agent_id)
        fee_calc = self.calculate_fee(tier, gross_amount, originator=is_originator)

        # ── Trial path: 0% fee, track liability ─────────────────────
        in_trial = self.trials.is_in_trial(agent_id)
        if in_trial:
            trial_rec = self.trials.record_trial_mission(agent_id, fee_calc["platform_fee"])
            agent_txn = self.treasury.credit(
                agent_id, gross_amount,  # full gross — no fee taken
                reason="trial_mission_payout", mission_id=mission_id,
            )
            return {
                "agent_id": agent_id,
                "mission_id": mission_id,
                "tier": fee_calc["tier"],
                "trial": True,
                "trial_missions_used": trial_rec["trial_missions_used"],
                "trial_missions_remaining": max(0, TRIAL_MISSION_LIMIT - trial_rec["trial_missions_used"]),
                "trial_liability_accrued": trial_rec["trial_liability"],
                "fee_breakdown": {**fee_calc, "effective_rate": 0.0, "fee_rate_pct": "0% (trial)", "platform_fee": 0.0, "net_to_agent": gross_amount},
                "originator_credit_applied": is_originator,
                "recruiter_bounty": None,
                "agent_transaction": agent_txn,
                "platform_transaction": None,
                "agent_balance": self.treasury.balance(agent_id),
                "note": f"Trial: {TRIAL_MISSION_LIMIT - trial_rec['trial_missions_used']} missions remaining. "
                        f"Accrued liability (forgiven on commit): ${trial_rec['trial_liability']:.2f}",
            }

        # ── Active path: apply tier fee, consume fee credits first ──
        platform_fee = fee_calc["platform_fee"]
        fee_credit_used = 0.0
        credit_bal = self.fee_credits.balance(agent_id)
        if credit_bal > 0 and platform_fee > 0:
            fee_credit_used = min(credit_bal, platform_fee)
            self.fee_credits.consume(agent_id, fee_credit_used, mission_id)
            platform_fee = round(platform_fee - fee_credit_used, 4)
            # Agent keeps what fee credits covered
            fee_calc = {**fee_calc, "platform_fee": platform_fee, "net_to_agent": gross_amount - platform_fee}

        agent_txn = self.treasury.credit(
            agent_id, fee_calc["net_to_agent"],
            reason="mission_payout", mission_id=mission_id,
        )

        platform_net = fee_calc["platform_fee"]
        recruiter_txn = None

        # Recruiter bounty — funded from platform's cut, not from agent's payout
        bounty_amount = 0.0
        if recruiter_id and agent_mission_count <= RECRUITER_BOUNTY_MISSIONS:
            bounty_amount = round(platform_net * RECRUITER_BOUNTY_RATE, 4)
            platform_net = round(platform_net - bounty_amount, 4)
            recruiter_txn = self.treasury.credit(
                recruiter_id, bounty_amount,
                reason="recruiter_bounty", mission_id=mission_id,
            )

        # Credit platform remainder
        platform_txn = self.treasury.credit(
            "platform", platform_net,
            reason="platform_fee", mission_id=mission_id,
        )

        result = {
            "agent_id": agent_id,
            "mission_id": mission_id,
            "tier": fee_calc["tier"],
            "trial": False,
            "fee_breakdown": fee_calc,
            "fee_credit_used": fee_credit_used,
            "fee_credit_remaining": self.fee_credits.balance(agent_id),
            "originator_credit_applied": is_originator,
            "recruiter_bounty": {
                "recruiter_id": recruiter_id,
                "amount": bounty_amount,
                "missions_remaining": max(0, RECRUITER_BOUNTY_MISSIONS - agent_mission_count),
            } if recruiter_id else None,
            "agent_transaction": agent_txn,
            "platform_transaction": platform_txn,
            "agent_balance": self.treasury.balance(agent_id),
        }
        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            span.set_attribute("civitae.economy.agent_id", agent_id)
            span.set_attribute("civitae.economy.mission_id", mission_id)
            span.set_attribute("civitae.economy.tier", str(fee_calc.get("tier", "")))
            span.set_attribute("civitae.economy.gross_amount", str(gross_amount))
            span.set_attribute("civitae.economy.fee_rate", str(fee_calc.get("fee_rate", "")))
            span.set_attribute("civitae.economy.platform_fee", str(fee_calc.get("platform_fee", "")))
            span.set_attribute("civitae.economy.net_to_agent", str(fee_calc.get("net_to_agent", "")))
            span.set_attribute("civitae.economy.fee_credit_used", str(fee_credit_used))
            span.set_attribute("civitae.economy.recruiter_bounty", str(bounty_amount))
        except Exception:
            pass
        return result

    def process_slot_payment(self, agent_id: str, agent_metrics: dict, gross_amount: float, mission_id: str = "") -> dict:
        """Full payment processing: determine tier → calculate fee → credit agent → credit platform."""
        tier = self.determine_tier(agent_metrics)
        fee_calc = self.calculate_fee(tier, gross_amount)

        # Credit agent (net)
        agent_txn = self.treasury.credit(
            agent_id, fee_calc["net_to_agent"],
            reason="slot_payment", mission_id=mission_id,
        )

        # Credit platform (fee)
        platform_txn = self.treasury.credit(
            "platform", fee_calc["platform_fee"],
            reason="platform_fee", mission_id=mission_id,
        )

        return {
            "agent_id": agent_id,
            "tier": fee_calc["tier"],
            "fee_breakdown": fee_calc,
            "agent_transaction": agent_txn,
            "platform_transaction": platform_txn,
            "agent_balance": self.treasury.balance(agent_id),
        }

    def can_access(self, tier: str, resource: str) -> bool:
        """Check if a tier has access to a resource."""
        tier_config = TIERS.get(tier, TIERS["ungoverned"])
        return resource in tier_config["access"]

    def tier_info(self, tier: str) -> dict:
        """Get full tier information."""
        return TIERS.get(tier, TIERS["ungoverned"])

    def all_tiers(self) -> dict:
        """Return all tier definitions."""
        return TIERS

    def leaderboard(self) -> list:
        """Agent leaderboard sorted by balance."""
        balances = self.treasury.all_balances()
        return sorted(
            [{"agent_id": k, "balance": v} for k, v in balances.items() if k != "platform"],
            key=lambda x: x["balance"],
            reverse=True,
        )
