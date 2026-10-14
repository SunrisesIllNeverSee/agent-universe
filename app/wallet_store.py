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
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

MAX_LINKED_WALLETS = 3

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
"""


class WalletError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


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


class WalletStore:
    def __init__(self, db_path: Path):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)

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

    def link(self, agent_id: str, chain: str, address: str, label: str = "", actor: str = "") -> dict:
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
