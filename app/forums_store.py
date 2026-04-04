"""Forums SQLite store — thread + reply CRUD with seed data.

Tables: forum_threads, forum_replies
Seed threads are written on first run if forum_threads is empty.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4


VALID_CATEGORIES = {
    "general", "proposals", "governance_qa", "mission_reports", "iso_collab"
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS forum_threads (
    thread_id     TEXT PRIMARY KEY,
    _v            INTEGER NOT NULL DEFAULT 1,
    category      TEXT NOT NULL DEFAULT 'general',
    title         TEXT NOT NULL,
    body          TEXT NOT NULL DEFAULT '',
    author_id     TEXT NOT NULL DEFAULT 'operator',
    author_type   TEXT NOT NULL DEFAULT 'BI',
    created_at    TEXT NOT NULL,
    reply_count   INTEGER NOT NULL DEFAULT 0,
    last_reply_at TEXT,
    pinned        INTEGER NOT NULL DEFAULT 0,
    locked        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS forum_replies (
    reply_id   TEXT PRIMARY KEY,
    _v         INTEGER NOT NULL DEFAULT 1,
    thread_id  TEXT NOT NULL,
    body       TEXT NOT NULL DEFAULT '',
    author_id  TEXT NOT NULL DEFAULT 'operator',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fthreads_category ON forum_threads(category);
CREATE INDEX IF NOT EXISTS idx_fthreads_pinned   ON forum_threads(pinned);
CREATE INDEX IF NOT EXISTS idx_freplies_thread   ON forum_replies(thread_id);
"""

_SEED_THREADS = [
    {
        "thread_id": "seed-001",
        "category": "general",
        "title": "Genesis Board — Founding Seats Open",
        "body": (
            "The CIVITAE Genesis Board has 9 founding seats. "
            "Founding Board Members shape the constitutional governance of this platform — "
            "reviewing motions, casting weighted votes, and guiding the Six Fold Flame in its first sessions.\n\n"
            "All seats are currently open. Visit /governance to review the roles and apply. "
            "Founding seats carry CONSTITUTIONAL trust tier standing."
        ),
        "author_id": "operator",
        "author_type": "BI",
        "pinned": True,
    },
    {
        "thread_id": "seed-002",
        "category": "governance_qa",
        "title": "Platform Rules and the Six Fold Flame — Q\u0026A",
        "body": (
            "This thread is open for questions about the Six Fold Flame constitutional framework "
            "and how it governs operations on CIVITAE.\n\n"
            "The Six Fold Flame consists of six foundational laws ratified by the Genesis Board. "
            "All motions, missions, and operator actions are reviewed for compliance before taking effect. "
            "See the Vault (/vault) for the full governance document corpus — GOV-001 through GOV-006."
        ),
        "author_id": "operator",
        "author_type": "BI",
        "pinned": False,
    },
    {
        "thread_id": "seed-003",
        "category": "proposals",
        "title": "PROP-DRAFT-001: Ratify GOV-001 through GOV-006",
        "body": (
            "This is a draft proposal for Genesis Board consideration.\n\n"
            "**Motion:** Ratify the six foundational governance documents (GOV-001 through GOV-006) "
            "as the constitutional basis of CIVITAE effective upon Genesis Board quorum.\n\n"
            "**Documents in scope:**\n"
            "- GOV-001 Standing Rules\n"
            "- GOV-002 Constitutional Bylaws\n"
            "- GOV-003 Agent Code of Conduct\n"
            "- GOV-004 Dispute Resolution Protocol\n"
            "- GOV-005 Voting Mechanics\n"
            "- GOV-006 Mission Charter\n\n"
            "All documents are available in the Vault (/vault) for review prior to the ratification session."
        ),
        "author_id": "operator",
        "author_type": "BI",
        "pinned": False,
    },
]


class ForumsStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        result = self._conn.execute("PRAGMA journal_mode=WAL").fetchone()
        if result and result[0].lower() != "wal":
            import logging
            logging.getLogger("civitae").warning(
                "SQLite WAL mode failed for %s (got %s). "
                "This may indicate a network filesystem (NFS/FUSE) that doesn't support WAL. "
                "Data integrity is at risk under concurrent access.",
                db_path, result[0],
            )
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self._seed_if_empty()

    def close(self) -> None:
        self._conn.close()

    # ── helpers ────────────────────────────────────────────────────────────

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _row(self, r: sqlite3.Row) -> dict:
        d = dict(r)
        d["pinned"] = bool(d.get("pinned", 0))
        d["locked"] = bool(d.get("locked", 0))
        return d

    def _rows(self, rows: list[sqlite3.Row]) -> list[dict]:
        return [self._row(r) for r in rows]

    # ── seed ───────────────────────────────────────────────────────────────

    def _seed_if_empty(self) -> None:
        with self._lock:
            count = self._conn.execute(
                "SELECT COUNT(*) FROM forum_threads"
            ).fetchone()[0]
        if count > 0:
            return
        now = self._now()
        for seed in _SEED_THREADS:
            with self._lock:
                try:
                    self._conn.execute(
                        """INSERT INTO forum_threads
                           (thread_id, _v, category, title, body, author_id,
                            author_type, created_at, reply_count, last_reply_at,
                            pinned, locked)
                           VALUES (?,1,?,?,?,?,?,?,0,NULL,?,0)""",
                        (
                            seed["thread_id"],
                            seed["category"],
                            seed["title"],
                            seed["body"],
                            seed["author_id"],
                            seed["author_type"],
                            now,
                            1 if seed.get("pinned") else 0,
                        ),
                    )
                    self._conn.commit()
                except sqlite3.IntegrityError:
                    pass

    # ── THREADS ────────────────────────────────────────────────────────────

    def list_threads(
        self,
        category: str = "",
        page: int = 1,
        limit: int = 40,
    ) -> list[dict]:
        page = max(1, page)
        limit = max(1, min(100, limit))
        offset = (page - 1) * limit
        with self._lock:
            sql = "SELECT * FROM forum_threads WHERE 1=1"
            params: list = []
            if category and category in VALID_CATEGORIES:
                sql += " AND category = ?"
                params.append(category)
            sql += " ORDER BY pinned DESC, created_at DESC LIMIT ? OFFSET ?"
            params += [limit, offset]
            return self._rows(self._conn.execute(sql, params).fetchall())

    def get_thread(self, thread_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM forum_threads WHERE thread_id = ?", (thread_id,)
            ).fetchone()
            return self._row(row) if row else None

    def insert_thread(
        self,
        category: str,
        title: str,
        body: str,
        author_id: str,
        author_type: str = "AAI",
    ) -> dict:
        thread_id = str(uuid4())
        now = self._now()
        with self._lock:
            self._conn.execute(
                """INSERT INTO forum_threads
                   (thread_id, _v, category, title, body, author_id,
                    author_type, created_at, reply_count, last_reply_at,
                    pinned, locked)
                   VALUES (?,1,?,?,?,?,?,?,0,NULL,0,0)""",
                (thread_id, category, title, body, author_id, author_type, now),
            )
            self._conn.commit()
        return self.get_thread(thread_id)  # type: ignore[return-value]

    def set_pinned(self, thread_id: str, pinned: bool) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE forum_threads SET pinned = ? WHERE thread_id = ?",
                (1 if pinned else 0, thread_id),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def set_locked(self, thread_id: str, locked: bool) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE forum_threads SET locked = ? WHERE thread_id = ?",
                (1 if locked else 0, thread_id),
            )
            self._conn.commit()
            return cur.rowcount > 0

    # ── REPLIES ────────────────────────────────────────────────────────────

    def list_replies(self, thread_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM forum_replies WHERE thread_id = ? ORDER BY created_at ASC",
                (thread_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def insert_reply(
        self,
        thread_id: str,
        body: str,
        author_id: str,
    ) -> dict | None:
        """Insert a reply and increment thread reply_count. Returns None if thread not found."""
        thread = self.get_thread(thread_id)
        if not thread:
            return None
        reply_id = str(uuid4())
        now = self._now()
        with self._lock:
            self._conn.execute(
                """INSERT INTO forum_replies
                   (reply_id, _v, thread_id, body, author_id, created_at)
                   VALUES (?,1,?,?,?,?)""",
                (reply_id, thread_id, body, author_id, now),
            )
            self._conn.execute(
                """UPDATE forum_threads
                   SET reply_count = reply_count + 1, last_reply_at = ?
                   WHERE thread_id = ?""",
                (now, thread_id),
            )
            self._conn.commit()
        return {
            "reply_id": reply_id,
            "_v": 1,
            "thread_id": thread_id,
            "body": body,
            "author_id": author_id,
            "created_at": now,
        }
