"""
escrow.py — funds held for a mission/Agreement until acceptance (P5).

States: funded -> held -> released | refunded, plus disputed (freezes only).
This store is the bound on the money: nothing can be released or refunded
beyond ``amount - released_total - refunded_total``, and nothing moves while
disputed. It holds no ledger; the routes credit the treasury after reserving
here, and un-reserve if the credit fails.

Durable on SQLite (the same pattern as workentry.db): every transition runs in one
BEGIN IMMEDIATE transaction that re-reads the row, so a release/refund cannot
double-apply across threads or replicas sharing the volume. A path ending in
``.json`` selects the legacy single-replica JSON file (local/dev fallback); an
existing JSON file is imported into the database on first start (kept on disk).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SOURCES = ("stripe_checkout", "operator")
LIVE_STATES = ("funded", "held", "disputed")
EPS = 1e-6


class EscrowError(Exception):
    def __init__(self, message: str, code: str = "escrow_error"):
        super().__init__(message)
        self.message = message
        self.code = code


def _now() -> str:
    return datetime.now(UTC).isoformat()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS escrows (
    escrow_id         TEXT PRIMARY KEY,
    state             TEXT NOT NULL,
    mission_id        TEXT,
    poster_id         TEXT,
    stripe_session_id TEXT,
    doc               TEXT NOT NULL,
    seq               INTEGER NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_escrows_session
    ON escrows(stripe_session_id) WHERE stripe_session_id IS NOT NULL AND stripe_session_id != '';
CREATE INDEX IF NOT EXISTS ix_escrows_mission ON escrows(mission_id);
CREATE TABLE IF NOT EXISTS escrow_meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
"""


class EscrowStore:
    def __init__(self, path: Path, *, import_json: Path | None = None):
        self._path = Path(path)
        self._lock = threading.RLock()
        self._json = self._path.suffix == ".json"
        self._depth = 0
        self._rows: dict[str, dict] = {}
        if self._json:
            self._conn = None
            if self._path.exists():
                try:
                    self._rows = json.loads(self._path.read_text())
                except Exception:  # noqa: BLE001 - a corrupt file must not stop boot; kept on disk
                    self._rows = {}
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None: transactions are managed explicitly.
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False,
                                     isolation_level=None, timeout=30)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        if import_json is not None:
            self._import_json(Path(import_json))

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()

    def _import_json(self, src: Path) -> int:
        """One-time startup import of legacy escrow.json records (the file is left in place).
        Existing ids are never overwritten, so a re-run cannot move money state."""
        if not src.exists():
            return 0
        try:
            rows = json.loads(src.read_text())
        except Exception:  # noqa: BLE001 - unreadable legacy file: leave it, do not block boot
            return 0
        n = 0
        with self._txn():
            if self._conn.execute("SELECT 1 FROM escrow_meta WHERE k='json_imported'").fetchone():
                return 0
            for eid, e in rows.items():
                if self._conn.execute("SELECT 1 FROM escrows WHERE escrow_id=?", (eid,)).fetchone():
                    continue
                self._put(e)
                n += 1
            self._conn.execute("INSERT INTO escrow_meta (k, v) VALUES ('json_imported', ?)", (_now(),))
        return n

    # ── internals ───────────────────────────────────────────────────────
    @contextmanager
    def _txn(self):
        """Serialize a read-modify-write. SQLite: one BEGIN IMMEDIATE (write lock held from
        the read), rolled back on any error. JSON: the process lock."""
        with self._lock:
            if self._json or self._depth:
                self._depth += 1
                try:
                    yield
                finally:
                    self._depth -= 1
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

    def _put(self, e: dict) -> None:
        if self._json:
            self._rows[e["escrow_id"]] = e
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._rows, indent=1))
            os.replace(tmp, self._path)
            return
        sid = e.get("stripe_session_id")
        cur = self._conn.execute(
            "UPDATE escrows SET state=?, mission_id=?, poster_id=?, stripe_session_id=?, doc=? WHERE escrow_id=?",
            (e["state"], e.get("mission_id"), e.get("poster_id"), sid, json.dumps(e), e["escrow_id"]))
        if cur.rowcount == 0:
            self._conn.execute(
                "INSERT INTO escrows (escrow_id, state, mission_id, poster_id, stripe_session_id, doc, seq)"
                " VALUES (?,?,?,?,?,?, (SELECT COALESCE(MAX(seq),0)+1 FROM escrows))",
                (e["escrow_id"], e["state"], e.get("mission_id"), e.get("poster_id"), sid, json.dumps(e)))

    def _all(self) -> list[dict]:
        if self._json:
            return list(self._rows.values())
        return [json.loads(r[0]) for r in self._conn.execute("SELECT doc FROM escrows ORDER BY seq")]

    @staticmethod
    def remaining_of(e: dict) -> float:
        return round(e["amount"] - e["released_total"] - e["refunded_total"], 4)

    def _log(self, e: dict, transition: str, **detail: Any) -> None:
        e["history"].append({"at": _now(), "transition": transition, **detail})
        e["updated_at"] = _now()

    def _get(self, escrow_id: str) -> dict:
        if self._json:
            e = self._rows.get(escrow_id)
        else:
            r = self._conn.execute("SELECT doc FROM escrows WHERE escrow_id=?", (escrow_id,)).fetchone()
            e = json.loads(r[0]) if r else None
        if e is None:
            raise EscrowError(f"escrow {escrow_id} not found", "not_found")
        return e

    def _view(self, e: dict) -> dict:
        return {**json.loads(json.dumps(e)), "remaining": self.remaining_of(e)}

    # ── reads ───────────────────────────────────────────────────────────
    def get(self, escrow_id: str) -> dict:
        with self._lock:
            return self._view(self._get(escrow_id))

    def list(self, *, mission_id: str | None = None, poster_id: str | None = None) -> list[dict]:
        with self._lock:
            return [self._view(e) for e in self._all()
                    if (mission_id is None or e["mission_id"] == mission_id)
                    and (poster_id is None or e["poster_id"] == poster_id)]

    def active_for_mission(self, mission_id: str) -> dict | None:
        """The live escrow bound to a mission (funded/held/disputed), if any."""
        with self._lock:
            for e in self._all():
                if e["mission_id"] == mission_id and e["state"] in LIVE_STATES:
                    return self._view(e)
        return None

    def by_session(self, stripe_session_id: str) -> dict | None:
        with self._lock:
            for e in self._all():
                if stripe_session_id and e.get("stripe_session_id") == stripe_session_id:
                    return self._view(e)
        return None

    # ── transitions ─────────────────────────────────────────────────────
    def fund(self, *, poster_id: str, amount: float, source: str, mission_id: str | None = None,
             agreement_id: str | None = None, stripe_session_id: str | None = None) -> dict:
        """Money received. Idempotent on stripe_session_id (webhook replays)."""
        if source not in SOURCES:
            raise EscrowError(f"source must be one of {SOURCES}", "bad_source")
        if not amount or amount <= 0:
            raise EscrowError("amount must be positive", "bad_amount")
        with self._txn():
            if stripe_session_id:
                dup = self.by_session(stripe_session_id)
                if dup:
                    return {**dup, "duplicate": True}
            e = {"escrow_id": f"esc-{uuid.uuid4().hex[:12]}", "state": "funded",
                 "poster_id": poster_id, "amount": round(float(amount), 4), "currency": "usd",
                 "released_total": 0.0, "refunded_total": 0.0, "source": source,
                 "stripe_session_id": stripe_session_id, "mission_id": mission_id,
                 "agreement_id": agreement_id, "created_at": _now(), "updated_at": _now(),
                 "releases": [], "history": []}
            self._log(e, "funded", amount=e["amount"], source=source)
            self._rows[e["escrow_id"]] = e
            self._put(e)
            return self._view(e)

    def hold(self, escrow_id: str, *, mission_id: str | None = None,
             agreement_id: str | None = None) -> dict:
        """Bind to a mission/Agreement; funded -> held. Held funds wait for acceptance."""
        with self._txn():
            e = self._get(escrow_id)
            if e["state"] not in ("funded", "held"):
                raise EscrowError(f"cannot hold an escrow in state '{e['state']}'", "bad_state")
            if mission_id:
                e["mission_id"] = mission_id
            if agreement_id:
                e["agreement_id"] = agreement_id
            if not e["mission_id"]:
                raise EscrowError("an escrow must be bound to a mission before it is held", "unbound")
            if e["state"] == "funded":
                e["state"] = "held"
                self._log(e, "held", mission_id=e["mission_id"], agreement_id=e["agreement_id"])
            self._put(e)
            return self._view(e)

    def reserve_release(self, escrow_id: str, *, agent_id: str, gross: float) -> dict:
        """Reserve a release to ``agent_id``; bounded by held funds. Caller pays out
        and calls ``revert_release`` if that fails. Returns {escrow, release}."""
        with self._txn():
            e = self._get(escrow_id)
            if e["state"] == "disputed":
                raise EscrowError("escrow is disputed: funds are frozen", "disputed")
            if e["state"] != "held":
                raise EscrowError(f"cannot release from state '{e['state']}'", "bad_state")
            if gross <= 0:
                raise EscrowError("release amount must be positive", "bad_amount")
            if gross > self.remaining_of(e) + EPS:
                raise EscrowError(f"release {gross} exceeds held funds {self.remaining_of(e)}", "exceeds_held")
            rel = {"release_id": f"rel-{uuid.uuid4().hex[:10]}", "agent_id": agent_id,
                   "gross": round(float(gross), 4), "at": _now()}
            e["releases"].append(rel)
            e["released_total"] = round(e["released_total"] + rel["gross"], 4)
            if self.remaining_of(e) <= EPS:
                e["state"] = "released"
            self._log(e, "released", agent_id=agent_id, gross=rel["gross"])
            self._put(e)
            return {"escrow": self._view(e), "release": rel}

    def revert_release(self, escrow_id: str, release_id: str) -> dict:
        with self._txn():
            e = self._get(escrow_id)
            rel = next((r for r in e["releases"] if r["release_id"] == release_id), None)
            if rel is None:
                return self._view(e)
            e["releases"].remove(rel)
            e["released_total"] = round(e["released_total"] - rel["gross"], 4)
            if e["state"] == "released":
                e["state"] = "held"
            self._log(e, "release_reverted", release_id=release_id, gross=rel["gross"])
            self._put(e)
            return self._view(e)

    def reserve_refund(self, escrow_id: str) -> dict:
        """Everything still held goes back to the poster. Returns {escrow, amount}.
        State ends 'refunded' when nothing was released, else 'released' (settled)."""
        with self._txn():
            e = self._get(escrow_id)
            if e["state"] == "disputed":
                raise EscrowError("escrow is disputed: funds are frozen", "disputed")
            if e["state"] not in ("funded", "held"):
                raise EscrowError(f"cannot refund from state '{e['state']}'", "bad_state")
            amount = self.remaining_of(e)
            if amount <= EPS:
                raise EscrowError("nothing left to refund", "nothing_held")
            e["refunded_total"] = round(e["refunded_total"] + amount, 4)
            e["state"] = "refunded" if e["released_total"] <= EPS else "released"
            self._log(e, "refunded", amount=amount, to=e["poster_id"])
            self._put(e)
            return {"escrow": self._view(e), "amount": amount}

    def revert_refund(self, escrow_id: str, amount: float) -> dict:
        with self._txn():
            e = self._get(escrow_id)
            e["refunded_total"] = round(e["refunded_total"] - amount, 4)
            e["state"] = "held" if e["mission_id"] else "funded"
            self._log(e, "refund_reverted", amount=amount)
            self._put(e)
            return self._view(e)

    def dispute(self, escrow_id: str, *, by: str, reason: str = "") -> dict:
        """Freeze only. No money moves; the operator resolves."""
        with self._txn():
            e = self._get(escrow_id)
            if e["state"] not in ("funded", "held"):
                raise EscrowError(f"cannot dispute an escrow in state '{e['state']}'", "bad_state")
            e["frozen_from"] = e["state"]
            e["state"] = "disputed"
            self._log(e, "disputed", by=by, reason=reason[:500])
            self._put(e)
            return self._view(e)

    def resolve_dispute(self, escrow_id: str, *, by: str, note: str = "") -> dict:
        """Unfreeze back to the prior state; release/refund then proceed normally."""
        with self._txn():
            e = self._get(escrow_id)
            if e["state"] != "disputed":
                raise EscrowError("escrow is not disputed", "bad_state")
            e["state"] = e.pop("frozen_from", "held")
            self._log(e, "dispute_resolved", by=by, note=note[:500])
            self._put(e)
            return self._view(e)
