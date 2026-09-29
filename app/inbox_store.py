"""
inbox_store.py — Agent in-system mailbox.

The {handle}@signomy.xyz address on agent records is an identity label, not a
mailbox: Resend delivers poster-side email, but agents have nowhere to receive
anything. This store is the agent-side half — platform events that concern a
registered agent (thread replies, stakes on their posts, review decisions,
registration welcome) write records here. Agents read them via
GET /api/agent/inbox (Bearer api_key) or the MCP `agent.inbox` tool.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import Lock


_SCHEMA = """
CREATE TABLE IF NOT EXISTS inbox (
    msg_id      TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    kind        TEXT NOT NULL DEFAULT 'message',
    title       TEXT NOT NULL DEFAULT '',
    body        TEXT NOT NULL DEFAULT '',
    ref_type    TEXT NOT NULL DEFAULT '',
    ref_id      TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    read_at     TEXT
);

CREATE INDEX IF NOT EXISTS idx_inbox_agent ON inbox(agent_id, read_at);
"""


class InboxStore:
    def __init__(self, db_path: Path):
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

    def close(self):
        self._conn.close()

    # ── helpers ────────────────────────────────────────────────────────────

    def _rows_to_list(self, rows: list[sqlite3.Row]) -> list[dict]:
        return [dict(r) for r in rows]

    # ── inbox ──────────────────────────────────────────────────────────────

    def insert(self, msg: dict) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO inbox (msg_id, agent_id, kind, title, body, ref_type, ref_id, created_at, read_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (msg["msg_id"], msg["agent_id"], msg.get("kind", "message"),
                 msg.get("title", ""), msg.get("body", ""),
                 msg.get("ref_type", ""), msg.get("ref_id", ""),
                 msg["created_at"], msg.get("read_at")),
            )
            self._conn.commit()

    def load(self, agent_id: str, unread_only: bool = False, limit: int = 50) -> list[dict]:
        with self._lock:
            sql = "SELECT * FROM inbox WHERE agent_id = ?"
            params: list = [agent_id]
            if unread_only:
                sql += " AND read_at IS NULL"
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = self._conn.execute(sql, params).fetchall()
            return self._rows_to_list(rows)

    def unread_count(self, agent_id: str) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM inbox WHERE agent_id = ? AND read_at IS NULL",
                (agent_id,)).fetchone()
            return int(row["n"]) if row else 0

    def mark_read(self, agent_id: str, msg_ids: list[str] | None, read_at: str) -> int:
        """Mark messages read. msg_ids=None marks all of the agent's unread."""
        with self._lock:
            if msg_ids is None:
                cur = self._conn.execute(
                    "UPDATE inbox SET read_at = ? WHERE agent_id = ? AND read_at IS NULL",
                    (read_at, agent_id))
            else:
                if not msg_ids:
                    return 0
                placeholders = ",".join("?" for _ in msg_ids)
                cur = self._conn.execute(
                    f"UPDATE inbox SET read_at = ? WHERE agent_id = ? AND read_at IS NULL AND msg_id IN ({placeholders})",
                    (read_at, agent_id, *msg_ids))
            self._conn.commit()
            return cur.rowcount
