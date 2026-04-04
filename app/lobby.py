"""
lobby.py — Velvet Rope session store.

Manages the 100-seat live chamber. Tracks active sessions, FIFO queue,
and auto-expiry. SQLite-backed, persists across restarts.

Design: docs/VELVET-ROPE-LOBBY-DESIGN.md
"""
from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path


# ── Defaults ─────────────────────────────────────────────────────────────────
MAX_ACTIVE = 100
SESSION_TTL = 3600          # 1 hour in seconds
WARN_AT = 300               # warn at 5 min remaining
FINAL_WARN_AT = 60          # final warn at 1 min remaining


@dataclass
class SessionInfo:
    session_id: str
    user_id: str
    status: str              # "active" | "queued" | "expired"
    entered_at: float | None
    expires_at: float | None
    queue_position: int | None


class LobbyStore:
    """SQLite-backed lobby session manager."""

    def __init__(self, db_path: Path, max_active: int = MAX_ACTIVE, session_ttl: int = SESSION_TTL):
        self.db_path = db_path
        self.max_active = max_active
        self.session_ttl = session_ttl
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS approved_users (
                    user_id   TEXT PRIMARY KEY,
                    name      TEXT NOT NULL DEFAULT '',
                    email     TEXT NOT NULL DEFAULT '',
                    approved_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id    TEXT NOT NULL,
                    status     TEXT NOT NULL DEFAULT 'queued',
                    entered_at REAL,
                    expires_at REAL,
                    queued_at  REAL NOT NULL,
                    UNIQUE(user_id, status)
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
                CREATE INDEX IF NOT EXISTS idx_sessions_queued ON sessions(queued_at);

                CREATE TABLE IF NOT EXISTS join_requests (
                    id         TEXT PRIMARY KEY,
                    name       TEXT NOT NULL,
                    email      TEXT NOT NULL,
                    role       TEXT NOT NULL DEFAULT '',
                    message    TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL,
                    status     TEXT NOT NULL DEFAULT 'pending'
                );
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    # ── Join requests (public intake) ─────────────────────────────────────

    def submit_join(self, name: str, email: str, role: str = "", message: str = "") -> str:
        req_id = uuid.uuid4().hex[:12]
        now = time.time()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO join_requests (id, name, email, role, message, created_at) VALUES (?,?,?,?,?,?)",
                (req_id, name, email, role, message, now),
            )
        return req_id

    def list_join_requests(self, status: str = "pending") -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM join_requests WHERE status=? ORDER BY created_at DESC", (status,)
            ).fetchall()
        return [dict(r) for r in rows]

    def approve_join(self, req_id: str) -> str | None:
        """Approve a join request → creates an approved_user entry. Returns user_id."""
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM join_requests WHERE id=?", (req_id,)).fetchone()
            if not row:
                return None
            user_id = uuid.uuid4().hex[:16]
            conn.execute(
                "INSERT OR IGNORE INTO approved_users (user_id, name, email, approved_at) VALUES (?,?,?,?)",
                (user_id, row["name"], row["email"], time.time()),
            )
            conn.execute("UPDATE join_requests SET status='approved' WHERE id=?", (req_id,))
        return user_id

    # ── Approved users ────────────────────────────────────────────────────

    def is_approved(self, user_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM approved_users WHERE user_id=?", (user_id,)).fetchone()
        return row is not None

    # ── Session management ────────────────────────────────────────────────

    def _expire_stale(self, conn: sqlite3.Connection) -> int:
        """Expire sessions past their TTL. Returns count expired."""
        now = time.time()
        cursor = conn.execute(
            "UPDATE sessions SET status='expired' WHERE status='active' AND expires_at < ?",
            (now,),
        )
        return cursor.rowcount

    def _promote_queue(self, conn: sqlite3.Connection) -> int:
        """Promote queued users into active seats. Returns count promoted."""
        now = time.time()
        active_count = conn.execute("SELECT COUNT(*) FROM sessions WHERE status='active'").fetchone()[0]
        available = self.max_active - active_count
        if available <= 0:
            return 0

        # FIFO — oldest queued first
        queued = conn.execute(
            "SELECT session_id FROM sessions WHERE status='queued' ORDER BY queued_at ASC LIMIT ?",
            (available,),
        ).fetchall()

        for row in queued:
            conn.execute(
                "UPDATE sessions SET status='active', entered_at=?, expires_at=? WHERE session_id=?",
                (now, now + self.session_ttl, row["session_id"]),
            )
        return len(queued)

    def _housekeep(self, conn: sqlite3.Connection) -> None:
        """Run expiry + promotion in one pass."""
        self._expire_stale(conn)
        self._promote_queue(conn)

    def enter(self, user_id: str) -> SessionInfo:
        """Request entry to the live chamber. Returns session status."""
        with self._lock, self._connect() as conn:
            self._housekeep(conn)

            # Already active?
            existing = conn.execute(
                "SELECT * FROM sessions WHERE user_id=? AND status='active'", (user_id,)
            ).fetchone()
            if existing:
                return self._to_info(existing, conn)

            # Already queued?
            existing_q = conn.execute(
                "SELECT * FROM sessions WHERE user_id=? AND status='queued'", (user_id,)
            ).fetchone()
            if existing_q:
                return self._to_info(existing_q, conn)

            # Clean up any old expired sessions for this user
            conn.execute("DELETE FROM sessions WHERE user_id=? AND status='expired'", (user_id,))

            now = time.time()
            session_id = uuid.uuid4().hex[:16]
            active_count = conn.execute("SELECT COUNT(*) FROM sessions WHERE status='active'").fetchone()[0]

            if active_count < self.max_active:
                # Direct entry
                conn.execute(
                    "INSERT INTO sessions (session_id, user_id, status, entered_at, expires_at, queued_at) VALUES (?,?,?,?,?,?)",
                    (session_id, user_id, "active", now, now + self.session_ttl, now),
                )
            else:
                # Queue
                conn.execute(
                    "INSERT INTO sessions (session_id, user_id, status, queued_at) VALUES (?,?,?,?)",
                    (session_id, user_id, "queued", now),
                )

            row = conn.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
            return self._to_info(row, conn)

    def leave(self, user_id: str) -> bool:
        """Release a seat early. Returns True if a session was ended."""
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE user_id=? AND status IN ('active','queued')", (user_id,)
            )
            if cursor.rowcount > 0:
                self._promote_queue(conn)
                return True
            return False

    def status(self, user_id: str) -> SessionInfo | None:
        """Get current session info for a user."""
        with self._lock, self._connect() as conn:
            self._housekeep(conn)
            row = conn.execute(
                "SELECT * FROM sessions WHERE user_id=? AND status IN ('active','queued') ORDER BY queued_at DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            if not row:
                return None
            return self._to_info(row, conn)

    def chamber_status(self) -> dict:
        """Public stats: active count, queue length, capacity."""
        with self._lock, self._connect() as conn:
            self._housekeep(conn)
            active = conn.execute("SELECT COUNT(*) FROM sessions WHERE status='active'").fetchone()[0]
            queued = conn.execute("SELECT COUNT(*) FROM sessions WHERE status='queued'").fetchone()[0]
        return {
            "active": active,
            "capacity": self.max_active,
            "available": max(0, self.max_active - active),
            "queued": queued,
        }

    def _to_info(self, row: sqlite3.Row, conn: sqlite3.Connection) -> SessionInfo:
        queue_pos = None
        if row["status"] == "queued":
            ahead = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE status='queued' AND queued_at < ?",
                (row["queued_at"],),
            ).fetchone()[0]
            queue_pos = ahead + 1
        return SessionInfo(
            session_id=row["session_id"],
            user_id=row["user_id"],
            status=row["status"],
            entered_at=row["entered_at"],
            expires_at=row["expires_at"],
            queue_position=queue_pos,
        )
