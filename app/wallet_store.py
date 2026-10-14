"""
wallet_store.py — agent-linked on-chain wallets (P5g).

Owner decision: an on-chain withdrawal may only go to a wallet the agent has linked, and an
agent may link at most MAX_LINKED_WALLETS. The withdraw route resolves the destination from
this store; the request body only selects which linked wallet.

SQLite (wallets.db), one row per (agent, chain, address). Rows are never edited; unlinking
deletes the link row after writing a tombstone to ``wallet_link_events`` (append-only history).
"""
from __future__ import annotations

import re
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock

MAX_LINKED_WALLETS = 3

# Fail-safe defaults; the live values are config/economic_rates.json "wallets" (CIVITAS-voteable).
_DEFAULT_RULES = {"link_interval_hours": 12, "new_wallet_window_hours": 24, "new_wallet_cap_usd": 25.0,
                  "approval_stuck_minutes": 15}


def wallet_rules() -> dict:
    """Wallet safety limits, read from config/economic_rates.json each call (never from a request)."""
    from app.economy import _load_rates
    cfg = _load_rates().get("wallets") or {}
    out = dict(_DEFAULT_RULES)
    for k, default in _DEFAULT_RULES.items():
        try:
            v = float(cfg.get(k, default))
            out[k] = v if v >= 0 else default
        except (TypeError, ValueError):
            out[k] = default
    return out


# EVM chains share one address format; ethereum and base are both EVM.
_EVM = re.compile(r"^0x[0-9a-fA-F]{40}$")
_SOL = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")   # base58 alphabet, 32-44 chars
LINKABLE_CHAINS = {"solana": _SOL, "ethereum": _EVM, "base": _EVM}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS linked_wallets (
    wallet_id   TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    chain       TEXT NOT NULL,
    address     TEXT NOT NULL,
    addr_key    TEXT NOT NULL,
    label       TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    UNIQUE (agent_id, chain, addr_key)
);
CREATE INDEX IF NOT EXISTS idx_linked_wallets_agent ON linked_wallets(agent_id);
CREATE TABLE IF NOT EXISTS wallet_link_events (
    event_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id   TEXT NOT NULL,
    wallet_id  TEXT NOT NULL,
    chain      TEXT NOT NULL,
    address    TEXT NOT NULL,
    action     TEXT NOT NULL,
    actor      TEXT NOT NULL DEFAULT '',
    at         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_wallet_events_agent ON wallet_link_events(agent_id, action, at);
CREATE TABLE IF NOT EXISTS wallet_flags (
    flag_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    flag           TEXT NOT NULL,
    chain          TEXT NOT NULL,
    address        TEXT NOT NULL,
    addr_key       TEXT NOT NULL,
    agent_id       TEXT NOT NULL,
    wallet_id      TEXT NOT NULL,
    other_agent_id TEXT NOT NULL,
    at             TEXT NOT NULL,
    UNIQUE (flag, wallet_id, other_agent_id)
);
CREATE TABLE IF NOT EXISTS wallet_payouts (
    payout_id   TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    chain       TEXT NOT NULL,
    addr_key    TEXT NOT NULL,
    wallet_id   TEXT NOT NULL,
    amount      REAL NOT NULL,
    kind        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'counted',
    at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_wallet_payouts_dest ON wallet_payouts(agent_id, chain, addr_key);
CREATE TABLE IF NOT EXISTS payout_approvals (
    approval_id TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    wallet_id   TEXT NOT NULL,
    chain       TEXT NOT NULL,
    address     TEXT NOT NULL,
    amount      REAL NOT NULL,
    status      TEXT NOT NULL,
    payout_id   TEXT NOT NULL DEFAULT '',
    reserve_txn TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    decided_at  TEXT,
    decided_by  TEXT NOT NULL DEFAULT '',
    transfer    TEXT NOT NULL DEFAULT '',
    review_reason TEXT NOT NULL DEFAULT '',
    kind        TEXT NOT NULL DEFAULT 'chain',
    review_from TEXT NOT NULL DEFAULT '',
    transfer_attempt INTEGER NOT NULL DEFAULT 0,
    reject_confirmed_by TEXT NOT NULL DEFAULT '',
    reject_confirmed_at TEXT NOT NULL DEFAULT '',
    reject_confirmed_what TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS stripe_bindings (
    agent_id        TEXT NOT NULL,
    account_id      TEXT NOT NULL,
    first_bound_at  TEXT NOT NULL,
    PRIMARY KEY (agent_id, account_id)
);
CREATE INDEX IF NOT EXISTS idx_payout_approvals_status ON payout_approvals(status, created_at);
"""


class WalletError(Exception):
    def __init__(self, status: int, message: str, allowed_at: str | None = None):
        super().__init__(message)
        self.status, self.message, self.allowed_at = status, message, allowed_at


def validate_address(chain: str, address: str) -> str:
    """Return the cleaned address, or raise WalletError(400)."""
    chain = (chain or "").strip().lower()
    pattern = LINKABLE_CHAINS.get(chain)
    if pattern is None:
        raise WalletError(400, f"Chain '{chain}' cannot be linked. Linkable: {sorted(LINKABLE_CHAINS)}")
    address = (address or "").strip()
    if not pattern.match(address):
        raise WalletError(400, f"Invalid {chain} address format")
    return address


def _key(chain: str, address: str) -> str:
    return address.lower() if chain in ("ethereum", "base") else address


def _family(chain: str) -> tuple[str, ...]:
    """Chains that share one address space. The same 0x address on ethereum and base is the same
    destination, so cap windows, cap usage and shared-address flags must not be split per chain."""
    return ("ethereum", "base") if chain in ("ethereum", "base") else (chain,)


def _in(chains: tuple[str, ...]) -> str:
    return "(" + ",".join("?" * len(chains)) + ")"


class WalletStore:
    def __init__(self, db_path: Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        cols = {r[1] for r in self._conn.execute("PRAGMA table_info(payout_approvals)")}
        if "kind" not in cols:   # databases created before P5k (Stripe approvals)
            self._conn.execute("ALTER TABLE payout_approvals ADD COLUMN kind TEXT NOT NULL DEFAULT 'chain'")
        if "review_reason" not in cols:   # P5k: databases created before the recovery sweep
            self._conn.execute("ALTER TABLE payout_approvals ADD COLUMN review_reason TEXT NOT NULL DEFAULT ''")
        if "review_from" not in cols:   # P5l: which claim the sweep found stuck ('approving' / 'rejecting')
            self._conn.execute("ALTER TABLE payout_approvals ADD COLUMN review_from TEXT NOT NULL DEFAULT ''")
        if "transfer_attempt" not in cols:   # P5l: Stripe idempotency-key generation
            self._conn.execute("ALTER TABLE payout_approvals ADD COLUMN transfer_attempt INTEGER NOT NULL DEFAULT 0")
        for col in ("reject_confirmed_by", "reject_confirmed_at", "reject_confirmed_what"):   # P5m
            if col not in cols:
                self._conn.execute(f"ALTER TABLE payout_approvals ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")

    def close(self) -> None:
        self._conn.close()

    def list(self, agent_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT wallet_id, agent_id, chain, address, label, created_at FROM linked_wallets "
                "WHERE agent_id=? ORDER BY created_at, wallet_id", (agent_id,)).fetchall()
        return [dict(r) for r in rows]

    def get(self, agent_id: str, wallet_id: str) -> dict | None:
        with self._lock:
            r = self._conn.execute(
                "SELECT wallet_id, agent_id, chain, address, label, created_at FROM linked_wallets "
                "WHERE agent_id=? AND wallet_id=?", (agent_id, wallet_id)).fetchone()
        return dict(r) if r else None

    def find(self, agent_id: str, chain: str, address: str) -> dict | None:
        """The agent's own link for (chain, address), or None. Never matches another agent's link."""
        chain = (chain or "").strip().lower()
        with self._lock:
            r = self._conn.execute(
                "SELECT wallet_id, agent_id, chain, address, label, created_at FROM linked_wallets "
                "WHERE agent_id=? AND chain=? AND addr_key=?",
                (agent_id, chain, _key(chain, (address or "").strip()))).fetchone()
        return dict(r) if r else None

    def link(self, agent_id: str, chain: str, address: str, label: str = "", actor: str = "",
             bypass_interval: bool = False) -> dict:
        chain = (chain or "").strip().lower()
        address = validate_address(chain, address)
        label = (label or "").strip()[:80]
        wallet_id = "wal_" + uuid.uuid4().hex[:16]
        now = datetime.now(UTC).isoformat()
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")   # count + insert are one atomic step
            try:
                n = self._conn.execute("SELECT COUNT(*) FROM linked_wallets WHERE agent_id=?",
                                       (agent_id,)).fetchone()[0]
                if n >= MAX_LINKED_WALLETS:
                    self._conn.execute("ROLLBACK")
                    raise WalletError(409, f"Wallet limit reached ({MAX_LINKED_WALLETS} linked wallets per agent). "
                                           "Unlink one first.")
                # A duplicate is a 409 whatever the clock says (the 12h rule is for new links).
                if self._conn.execute("SELECT 1 FROM linked_wallets WHERE agent_id=? AND chain=? AND addr_key=?",
                                      (agent_id, chain, _key(chain, address))).fetchone():
                    self._conn.execute("ROLLBACK")
                    raise WalletError(409, "This wallet is already linked")
                # One new link per interval. Counted from the append-only event log, so an
                # unlink + relink cannot reset the clock.
                interval = timedelta(hours=wallet_rules()["link_interval_hours"])
                if not bypass_interval and interval.total_seconds() > 0:
                    last = self._conn.execute(
                        "SELECT MAX(at) FROM wallet_link_events WHERE agent_id=? AND action='link'",
                        (agent_id,)).fetchone()[0]
                    if last:
                        allowed = datetime.fromisoformat(last) + interval
                        if allowed > datetime.now(UTC):
                            self._conn.execute("ROLLBACK")
                            raise WalletError(429, f"One new wallet link per {interval.total_seconds() / 3600:g} hours. "
                                                   f"Next link allowed at {allowed.isoformat()}.",
                                              allowed_at=allowed.isoformat())
                try:
                    self._conn.execute(
                        "INSERT INTO linked_wallets (wallet_id, agent_id, chain, address, addr_key, label, created_at) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (wallet_id, agent_id, chain, address, _key(chain, address), label, now))
                except sqlite3.IntegrityError:
                    self._conn.execute("ROLLBACK")
                    raise WalletError(409, "This wallet is already linked") from None
                self._conn.execute(
                    "INSERT INTO wallet_link_events (agent_id, wallet_id, chain, address, action, actor, at) "
                    "VALUES (?,?,?,?,?,?,?)", (agent_id, wallet_id, chain, address, "link", actor, now))
                # Same address under another agent: allowed, but flagged for the operator.
                key = _key(chain, address)
                fam = _family(chain)
                others = {r[0] for r in self._conn.execute(
                    f"SELECT agent_id FROM linked_wallets WHERE chain IN {_in(fam)} AND addr_key=? AND agent_id<>?",
                    (*fam, key, agent_id))}
                for r in self._conn.execute(
                        f"SELECT agent_id, address FROM wallet_link_events WHERE chain IN {_in(fam)} AND action='link' AND agent_id<>?",
                        (*fam, agent_id)):
                    if _key(chain, r[1]) == key:
                        others.add(r[0])
                for other in sorted(others):
                    self._conn.execute(
                        "INSERT OR IGNORE INTO wallet_flags (flag, chain, address, addr_key, agent_id, wallet_id, "
                        "other_agent_id, at) VALUES ('shared_address',?,?,?,?,?,?,?)",
                        (chain, address, key, agent_id, wallet_id, other, now))
                self._conn.execute("COMMIT")
            except WalletError:
                raise
            except Exception:
                if self._conn.in_transaction:
                    self._conn.execute("ROLLBACK")
                raise
        return {"wallet_id": wallet_id, "agent_id": agent_id, "chain": chain, "address": address,
                "label": label, "created_at": now}

    def unlink(self, agent_id: str, wallet_id: str, actor: str = "") -> dict | None:
        now = datetime.now(UTC).isoformat()
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                row = self._conn.execute(
                    "SELECT wallet_id, agent_id, chain, address, label, created_at FROM linked_wallets "
                    "WHERE agent_id=? AND wallet_id=?", (agent_id, wallet_id)).fetchone()
                if row is None:
                    self._conn.execute("ROLLBACK")
                    return None
                self._conn.execute("DELETE FROM linked_wallets WHERE wallet_id=?", (wallet_id,))
                self._conn.execute(
                    "INSERT INTO wallet_link_events (agent_id, wallet_id, chain, address, action, actor, at) "
                    "VALUES (?,?,?,?,?,?,?)", (agent_id, wallet_id, row["chain"], row["address"], "unlink", actor, now))
                self._conn.execute("COMMIT")
            except Exception:
                if self._conn.in_transaction:
                    self._conn.execute("ROLLBACK")
                raise
        return dict(row)


    # ── Stripe destination (P5k): same cap window, keyed by the bound account ───
    def note_stripe_binding(self, agent_id: str, account_id: str) -> dict:
        """Record the first time this agent was bound to this Stripe account (idempotent) and return
        it as a cap "link". Re-binding the same account never restarts the window; a new account
        starts its own. An account first seen here (bound before P5k) starts its window now."""
        now = datetime.now(UTC).isoformat()
        with self._lock:
            self._conn.execute("INSERT OR IGNORE INTO stripe_bindings (agent_id, account_id, first_bound_at) "
                               "VALUES (?,?,?)", (agent_id, account_id, now))
            at = self._conn.execute("SELECT first_bound_at FROM stripe_bindings WHERE agent_id=? AND account_id=?",
                                    (agent_id, account_id)).fetchone()[0]
        return {"wallet_id": "", "chain": "stripe", "address": account_id, "created_at": at}

    # ── new-wallet payout cap (cumulative per agent + destination address) ──────
    def claim_cap(self, agent_id: str, link: dict, amount: float, rules: dict, kind: str = "direct", record: bool = True):
        """Decide a withdrawal against the new-wallet cap. Returns ("direct", payout_id|None) when it
        fits (or the window has passed) and the amount is recorded against the cap, else ("over", None).
        Window start is the first time this agent linked this address, so unlink/relink cannot restart it.
        ``record=False`` (P5m) only decides: nothing is written, so a request that moves no money (an MCP
        cashout that is merely queued) never consumes cap. Whatever later moves money must claim with record=True."""
        chain, key = link["chain"], _key(link["chain"], link["address"])
        fam = _family(chain)
        now = datetime.now(UTC)
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                first = self._conn.execute(
                    f"SELECT at, address FROM wallet_link_events WHERE agent_id=? AND chain IN {_in(fam)} AND action='link' ORDER BY event_id",
                    (agent_id, *fam)).fetchall()
                starts = [r[0] for r in first if _key(chain, r[1]) == key] or [link["created_at"]]
                start = datetime.fromisoformat(min(starts))
                if now >= start + timedelta(hours=rules["new_wallet_window_hours"]):
                    self._conn.execute("ROLLBACK")
                    return "direct", None
                used = self._conn.execute(
                    f"SELECT COALESCE(SUM(amount),0) FROM wallet_payouts WHERE agent_id=? AND chain IN {_in(fam)} AND addr_key=? "
                    "AND status='counted'", (agent_id, *fam, key)).fetchone()[0]
                if round(used + amount, 4) > round(float(rules["new_wallet_cap_usd"]), 4):
                    self._conn.execute("ROLLBACK")
                    return "over", None
                if not record:
                    self._conn.execute("ROLLBACK")
                    return "direct", None
                pid = "wpo_" + uuid.uuid4().hex[:16]
                self._conn.execute(
                    "INSERT INTO wallet_payouts (payout_id, agent_id, chain, addr_key, wallet_id, amount, kind, at) "
                    "VALUES (?,?,?,?,?,?,?,?)", (pid, agent_id, chain, key, link["wallet_id"], amount, kind, now.isoformat()))
                self._conn.execute("COMMIT")
                return "direct", pid
            except Exception:
                if self._conn.in_transaction:
                    self._conn.execute("ROLLBACK")
                raise

    def void_payout(self, payout_id: str | None) -> None:
        if not payout_id:
            return
        with self._lock:
            self._conn.execute("UPDATE wallet_payouts SET status='void' WHERE payout_id=?", (payout_id,))

    # ── payout approvals ───────────────────────────────────────────────────────
    def create_approval(self, agent_id: str, link: dict, amount: float, reserve_txn: str = "",
                        kind: str = "chain") -> dict:
        """Persist a pending approval with the destination snapshotted now; it also counts against the cap."""
        chain, key = link["chain"], _key(link["chain"], link["address"])
        now = datetime.now(UTC).isoformat()
        aid, pid = "apr_" + uuid.uuid4().hex[:16], "wpo_" + uuid.uuid4().hex[:16]
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                self._conn.execute(
                    "INSERT INTO wallet_payouts (payout_id, agent_id, chain, addr_key, wallet_id, amount, kind, at) "
                    "VALUES (?,?,?,?,?,?,?,?)", (pid, agent_id, chain, key, link["wallet_id"], amount, "approval", now))
                self._conn.execute(
                    "INSERT INTO payout_approvals (approval_id, agent_id, wallet_id, chain, address, amount, status, "
                    "payout_id, reserve_txn, created_at, kind) VALUES (?,?,?,?,?,?,'pending',?,?,?,?)",
                    (aid, agent_id, link["wallet_id"], chain, link["address"], amount, pid, reserve_txn, now, kind))
                self._conn.execute("COMMIT")
            except Exception:
                if self._conn.in_transaction:
                    self._conn.execute("ROLLBACK")
                raise
        return self.get_approval(aid)

    def get_approval(self, approval_id: str) -> dict | None:
        with self._lock:
            r = self._conn.execute("SELECT * FROM payout_approvals WHERE approval_id=?", (approval_id,)).fetchone()
        return dict(r) if r else None

    def list_approvals(self, status: str = "") -> list[dict]:
        q, args = "SELECT * FROM payout_approvals", ()
        if status:
            q, args = q + " WHERE status=?", (status,)
        with self._lock:
            rows = [dict(r) for r in self._conn.execute(q + " ORDER BY created_at, approval_id", args)]
        for a in rows:
            a["shared_address_agents"] = self.shared_with(a["agent_id"], a["chain"], a["address"])
        return rows

    def claim_approval(self, approval_id: str, to_status: str, actor: str) -> bool:
        """Atomically move pending (or an operator-reviewed 'needs_review') -> ``to_status``
        ('approving' / 'rejecting'). Exactly one caller wins."""
        with self._lock:
            cur = self._conn.execute(
                "UPDATE payout_approvals SET status=?, decided_by=?, decided_at=? WHERE approval_id=? "
                "AND status IN ('pending','needs_review')",
                (to_status, actor, datetime.now(UTC).isoformat(), approval_id))
            return cur.rowcount == 1

    def settle_approval(self, approval_id: str, status: str, transfer: str = "", ambiguous: bool = False) -> None:
        """Final state for a claimed approval: 'approved' / 'rejected', or back to 'pending' if the transfer
        did not happen. Rejection frees the cap usage; the reservation refund is the caller's job.
        ``ambiguous`` (P5n): a failure that does not prove the transfer did not go out (timeout, exception
        mid-transfer). The approval returns to 'pending' marked review_from='approving' so a reject still
        needs the operator's confirmation; a definitive failure clears the mark."""
        with self._lock:
            if status == "pending":
                self._conn.execute("UPDATE payout_approvals SET status=?, transfer=?, review_from=? WHERE approval_id=?",
                                   (status, transfer, "approving" if ambiguous else "", approval_id))
            else:
                self._conn.execute("UPDATE payout_approvals SET status=?, transfer=? WHERE approval_id=?",
                                   (status, transfer, approval_id))
            if status == "rejected":
                self._conn.execute(
                    "UPDATE wallet_payouts SET status='void' WHERE payout_id=(SELECT payout_id FROM payout_approvals "
                    "WHERE approval_id=?)", (approval_id,))

    def record_reject_confirmation(self, approval_id: str, actor: str, what: str) -> None:
        """P5m: the operator confirmed they checked Stripe / the chain before rejecting an approval
        that was stuck in 'approving' (a transfer may already have gone out). Who, when, and what."""
        with self._lock:
            self._conn.execute(
                "UPDATE payout_approvals SET reject_confirmed_by=?, reject_confirmed_at=?, reject_confirmed_what=? "
                "WHERE approval_id=?", (actor, datetime.now(UTC).isoformat(), what, approval_id))

    def bump_transfer_attempt(self, approval_id: str) -> None:
        """A Stripe transfer attempt that definitely did not happen: the next try uses a fresh idempotency key."""
        with self._lock:
            self._conn.execute("UPDATE payout_approvals SET transfer_attempt=transfer_attempt+1 WHERE approval_id=?",
                               (approval_id,))

    def sweep_stuck_approvals(self, minutes: float, now: datetime | None = None) -> list[dict]:
        """P5k recovery: an approval claimed ('approving'/'rejecting') longer than ``minutes`` ago means the
        process died mid-settlement. Move it to 'needs_review' with the reservation still held and the reason
        recorded. Never pays and never refunds: whether the transfer or refund went out is unknown."""
        now = now or datetime.now(UTC)
        cutoff = (now - timedelta(minutes=minutes)).isoformat()
        moved = []
        with self._lock:
            rows = self._conn.execute(
                "SELECT approval_id, status FROM payout_approvals WHERE status IN ('approving','rejecting') "
                "AND decided_at IS NOT NULL AND decided_at < ?", (cutoff,)).fetchall()
            for r in rows:
                reason = (f"stuck in '{r['status']}' for over {minutes:g} min (process died mid-settlement?); "
                          f"unknown whether the {'transfer' if r['status'] == 'approving' else 'refund'} went out. "
                          "Reservation still held. Check the chain/ledger before approving or rejecting.")
                cur = self._conn.execute(
                    "UPDATE payout_approvals SET status='needs_review', review_reason=?, review_from=? "
                    "WHERE approval_id=? AND status=?",
                    (reason, r["status"], r["approval_id"], r["status"]))
                if cur.rowcount == 1:
                    moved.append({"approval_id": r["approval_id"], "was": r["status"], "reason": reason})
        return moved

    def add_flag(self, flag: str, link_row: dict, ref: str) -> None:
        """Record an operator-visible flag against a destination (``ref`` keeps repeats distinct)."""
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO wallet_flags (flag, chain, address, addr_key, agent_id, wallet_id, "
                "other_agent_id, at) VALUES (?,?,?,?,?,?,?,?)",
                (flag, link_row["chain"], link_row["address"], _key(link_row["chain"], link_row["address"]),
                 link_row["agent_id"], link_row["wallet_id"], ref, datetime.now(UTC).isoformat()))

    # ── flags ──────────────────────────────────────────────────────────────────
    def shared_with(self, agent_id: str, chain: str, address: str) -> list[str]:
        key = _key(chain, address)
        with self._lock:
            rows = self._conn.execute(
                "SELECT other_agent_id FROM wallet_flags WHERE flag='shared_address' AND chain=? AND addr_key=? AND agent_id=? "
                "UNION SELECT agent_id FROM wallet_flags WHERE flag='shared_address' AND chain=? AND addr_key=? AND other_agent_id=?",
                (chain, key, agent_id, chain, key, agent_id)).fetchall()
        return sorted(r[0] for r in rows)

    def list_flags(self) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._conn.execute("SELECT * FROM wallet_flags ORDER BY flag_id")]
