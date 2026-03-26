"""KA§§A SQLite store — replaces JSONL files with a single SQLite database.

Tables: posts, reviews, stakes, referrals, threads, thread_messages, contact_messages
All functions return plain dicts to match the existing server.py interface.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from threading import Lock


_SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id          TEXT PRIMARY KEY,
    _v          INTEGER DEFAULT 1,
    tab         TEXT NOT NULL,
    title       TEXT NOT NULL,
    tag         TEXT NOT NULL DEFAULT '',
    body        TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'open',
    urgency     TEXT NOT NULL DEFAULT 'normal',
    upvotes     INTEGER NOT NULL DEFAULT 0,
    reply_count INTEGER NOT NULL DEFAULT 0,
    reward      TEXT,
    from_name   TEXT NOT NULL DEFAULT '',
    from_email  TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id   TEXT PRIMARY KEY,
    post_json   TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    submitted_at TEXT NOT NULL,
    reviewed_at  TEXT
);

CREATE TABLE IF NOT EXISTS stakes (
    stake_id    TEXT PRIMARY KEY,
    post_id     TEXT NOT NULL,
    agent_id    TEXT NOT NULL,
    agent_name  TEXT,
    status      TEXT NOT NULL DEFAULT 'active',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS referrals (
    referral_id    TEXT PRIMARY KEY,
    agent_id       TEXT NOT NULL,
    agent_name     TEXT,
    source_post_id TEXT NOT NULL,
    target_post_id TEXT NOT NULL,
    source_tab     TEXT NOT NULL DEFAULT '',
    target_tab     TEXT NOT NULL DEFAULT '',
    reason         TEXT NOT NULL DEFAULT '',
    status         TEXT NOT NULL DEFAULT 'active',
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS threads (
    thread_id     TEXT PRIMARY KEY,
    post_id       TEXT NOT NULL,
    post_tab      TEXT NOT NULL DEFAULT '',
    post_title    TEXT NOT NULL DEFAULT '',
    agent_id      TEXT NOT NULL,
    agent_name    TEXT,
    poster_name   TEXT NOT NULL DEFAULT '',
    poster_email  TEXT NOT NULL DEFAULT '',
    magic_token   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'open',
    message_count INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS thread_messages (
    msg_id      TEXT PRIMARY KEY,
    thread_id   TEXT NOT NULL,
    sender_type TEXT NOT NULL,
    sender_name TEXT NOT NULL DEFAULT '',
    text        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contact_messages (
    id          TEXT PRIMARY KEY,
    post_id     TEXT NOT NULL DEFAULT '',
    tab         TEXT NOT NULL DEFAULT '',
    from_name   TEXT NOT NULL DEFAULT '',
    from_email  TEXT NOT NULL DEFAULT '',
    message     TEXT NOT NULL DEFAULT '',
    timestamp   TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'new'
);

CREATE INDEX IF NOT EXISTS idx_posts_tab    ON posts(tab);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_stakes_post  ON stakes(post_id);
CREATE INDEX IF NOT EXISTS idx_stakes_agent ON stakes(agent_id);
CREATE INDEX IF NOT EXISTS idx_referrals_agent ON referrals(agent_id);
CREATE INDEX IF NOT EXISTS idx_threads_post ON threads(post_id);
CREATE INDEX IF NOT EXISTS idx_thread_msgs_thread ON thread_messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status);
"""


class KassaStore:
    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self):
        self._conn.close()

    # ── helpers ────────────────────────────────────────────────────────────

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        return dict(row)

    def _rows_to_list(self, rows: list[sqlite3.Row]) -> list[dict]:
        return [dict(r) for r in rows]

    # ── POSTS ──────────────────────────────────────────────────────────────

    def load_posts(self, tab: str = "", status: str = "") -> list[dict]:
        with self._lock:
            sql = "SELECT * FROM posts WHERE 1=1"
            params: list = []
            if tab:
                sql += " AND tab = ?"
                params.append(tab)
            if status:
                sql += " AND status = ?"
                params.append(status)
            sql += " ORDER BY created_at DESC"
            rows = self._conn.execute(sql, params).fetchall()
            return self._rows_to_list(rows)

    def get_post(self, post_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
            return self._row_to_dict(row) if row else None

    def insert_post(self, post: dict) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO posts (id, _v, tab, title, tag, body, status, urgency,
                   upvotes, reply_count, reward, from_name, from_email, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (post["id"], post.get("_v", 1), post["tab"], post["title"],
                 post.get("tag", ""), post.get("body", ""), post.get("status", "open"),
                 post.get("urgency", "normal"), post.get("upvotes", 0),
                 post.get("reply_count", 0), post.get("reward"),
                 post.get("from_name", ""), post.get("from_email", ""),
                 post["created_at"], post["updated_at"]))
            self._conn.commit()

    def update_post(self, post_id: str, updates: dict) -> None:
        with self._lock:
            sets = ", ".join(f"{k} = ?" for k in updates)
            vals = list(updates.values()) + [post_id]
            self._conn.execute(f"UPDATE posts SET {sets} WHERE id = ?", vals)
            self._conn.commit()

    def increment_upvotes(self, post_id: str) -> int:
        with self._lock:
            self._conn.execute(
                "UPDATE posts SET upvotes = upvotes + 1 WHERE id = ?", (post_id,))
            self._conn.commit()
            row = self._conn.execute(
                "SELECT upvotes FROM posts WHERE id = ?", (post_id,)).fetchone()
            return row["upvotes"] if row else 0

    def next_k_serial(self) -> str:
        """Generate next K-serial across posts and reviews."""
        with self._lock:
            max_n = 0
            # check posts
            for row in self._conn.execute("SELECT id FROM posts").fetchall():
                pid = row["id"]
                if pid.startswith("K-"):
                    try:
                        max_n = max(max_n, int(pid[2:]))
                    except ValueError:
                        pass
            # check reviews
            for row in self._conn.execute("SELECT post_json FROM reviews").fetchall():
                try:
                    p = json.loads(row["post_json"])
                    pid = p.get("id", "")
                    if pid.startswith("K-"):
                        max_n = max(max_n, int(pid[2:]))
                except (ValueError, json.JSONDecodeError):
                    pass
            return f"K-{max_n + 1:05d}"

    # ── REVIEWS ────────────────────────────────────────────────────────────

    def load_reviews(self, status: str = "") -> list[dict]:
        with self._lock:
            if status:
                rows = self._conn.execute(
                    "SELECT * FROM reviews WHERE status = ? ORDER BY submitted_at DESC",
                    (status,)).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM reviews ORDER BY submitted_at DESC").fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["post"] = json.loads(d.pop("post_json"))
                result.append(d)
            return result

    def insert_review(self, review: dict) -> None:
        with self._lock:
            post_json = json.dumps(review["post"])
            self._conn.execute(
                """INSERT INTO reviews (review_id, post_json, status, submitted_at)
                   VALUES (?, ?, ?, ?)""",
                (review["review_id"], post_json, review.get("status", "pending"),
                 review["submitted_at"]))
            self._conn.commit()

    def update_review(self, review_id: str, updates: dict) -> None:
        with self._lock:
            if "post" in updates:
                updates["post_json"] = json.dumps(updates.pop("post"))
            sets = ", ".join(f"{k} = ?" for k in updates)
            vals = list(updates.values()) + [review_id]
            self._conn.execute(f"UPDATE reviews SET {sets} WHERE review_id = ?", vals)
            self._conn.commit()

    def get_review(self, review_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM reviews WHERE review_id = ?", (review_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["post"] = json.loads(d.pop("post_json"))
            return d

    # ── STAKES ─────────────────────────────────────────────────────────────

    def load_stakes(self, post_id: str = "", agent_id: str = "") -> list[dict]:
        with self._lock:
            sql = "SELECT * FROM stakes WHERE 1=1"
            params: list = []
            if post_id:
                sql += " AND post_id = ?"
                params.append(post_id)
            if agent_id:
                sql += " AND agent_id = ?"
                params.append(agent_id)
            sql += " ORDER BY created_at DESC"
            return self._rows_to_list(self._conn.execute(sql, params).fetchall())

    def insert_stake(self, stake: dict) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO stakes (stake_id, post_id, agent_id, agent_name, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (stake["stake_id"], stake["post_id"], stake["agent_id"],
                 stake.get("agent_name"), stake.get("status", "active"),
                 stake["created_at"]))
            self._conn.commit()

    def update_stake(self, stake_id: str, updates: dict) -> None:
        with self._lock:
            sets = ", ".join(f"{k} = ?" for k in updates)
            vals = list(updates.values()) + [stake_id]
            self._conn.execute(f"UPDATE stakes SET {sets} WHERE stake_id = ?", vals)
            self._conn.commit()

    # ── REFERRALS ──────────────────────────────────────────────────────────

    def load_referrals(self, agent_id: str = "") -> list[dict]:
        with self._lock:
            if agent_id:
                rows = self._conn.execute(
                    "SELECT * FROM referrals WHERE agent_id = ? ORDER BY created_at DESC",
                    (agent_id,)).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM referrals ORDER BY created_at DESC").fetchall()
            return self._rows_to_list(rows)

    def insert_referral(self, ref: dict) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO referrals (referral_id, agent_id, agent_name,
                   source_post_id, target_post_id, source_tab, target_tab,
                   reason, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ref["referral_id"], ref["agent_id"], ref.get("agent_name"),
                 ref["source_post_id"], ref["target_post_id"],
                 ref.get("source_tab", ""), ref.get("target_tab", ""),
                 ref.get("reason", ""), ref.get("status", "active"),
                 ref["created_at"]))
            self._conn.commit()

    def update_referral(self, referral_id: str, updates: dict) -> None:
        with self._lock:
            sets = ", ".join(f"{k} = ?" for k in updates)
            vals = list(updates.values()) + [referral_id]
            self._conn.execute(f"UPDATE referrals SET {sets} WHERE referral_id = ?", vals)
            self._conn.commit()

    # ── THREADS ────────────────────────────────────────────────────────────

    def load_threads(self, post_id: str = "", agent_id: str = "") -> list[dict]:
        with self._lock:
            sql = "SELECT * FROM threads WHERE 1=1"
            params: list = []
            if post_id:
                sql += " AND post_id = ?"
                params.append(post_id)
            if agent_id:
                sql += " AND agent_id = ?"
                params.append(agent_id)
            sql += " ORDER BY updated_at DESC"
            return self._rows_to_list(self._conn.execute(sql, params).fetchall())

    def get_thread(self, thread_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM threads WHERE thread_id = ?", (thread_id,)).fetchone()
            return self._row_to_dict(row) if row else None

    def get_thread_by_token(self, magic_token: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM threads WHERE magic_token = ?", (magic_token,)).fetchone()
            return self._row_to_dict(row) if row else None

    def insert_thread(self, thread: dict) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO threads (thread_id, post_id, post_tab, post_title,
                   agent_id, agent_name, poster_name, poster_email,
                   magic_token, status, message_count, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (thread["thread_id"], thread["post_id"],
                 thread.get("post_tab", ""), thread.get("post_title", ""),
                 thread["agent_id"], thread.get("agent_name"),
                 thread.get("poster_name", ""), thread.get("poster_email", ""),
                 thread["magic_token"], thread.get("status", "open"),
                 thread.get("message_count", 0),
                 thread["created_at"], thread["updated_at"]))
            self._conn.commit()

    def update_thread(self, thread_id: str, updates: dict) -> None:
        with self._lock:
            sets = ", ".join(f"{k} = ?" for k in updates)
            vals = list(updates.values()) + [thread_id]
            self._conn.execute(f"UPDATE threads SET {sets} WHERE thread_id = ?", vals)
            self._conn.commit()

    # ── THREAD MESSAGES ────────────────────────────────────────────────────

    def load_thread_messages(self, thread_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM thread_messages WHERE thread_id = ? ORDER BY created_at ASC",
                (thread_id,)).fetchall()
            return self._rows_to_list(rows)

    def insert_thread_message(self, msg: dict) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO thread_messages (msg_id, thread_id, sender_type, sender_name, text, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (msg["msg_id"], msg["thread_id"], msg["sender_type"],
                 msg.get("sender_name", ""), msg.get("text", ""),
                 msg["created_at"]))
            self._conn.commit()

    # ── CONTACT MESSAGES ───────────────────────────────────────────────────

    def load_contact_messages(self, tab: str = "", status: str = "") -> list[dict]:
        with self._lock:
            sql = "SELECT * FROM contact_messages WHERE 1=1"
            params: list = []
            if tab:
                sql += " AND tab = ?"
                params.append(tab)
            if status:
                sql += " AND status = ?"
                params.append(status)
            sql += " ORDER BY timestamp DESC"
            return self._rows_to_list(self._conn.execute(sql, params).fetchall())

    def insert_contact_message(self, msg: dict) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO contact_messages (id, post_id, tab, from_name, from_email, message, timestamp, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (msg["id"], msg.get("post_id", ""), msg.get("tab", ""),
                 msg.get("from_name", ""), msg.get("from_email", ""),
                 msg.get("message", ""), msg["timestamp"],
                 msg.get("status", "new")))
            self._conn.commit()

    # ── MIGRATION ──────────────────────────────────────────────────────────

    def migrate_from_jsonl(self, data_dir: Path) -> dict[str, int]:
        """Import existing JSONL data into SQLite. Skips rows that already exist."""
        counts: dict[str, int] = {}

        def _read_jsonl(filename: str) -> list[dict]:
            fp = data_dir / filename
            if not fp.exists():
                return []
            out = []
            for line in fp.read_text().splitlines():
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            return out

        # posts
        posts = _read_jsonl("kassa_posts.jsonl")
        n = 0
        for p in posts:
            try:
                self.insert_post(p)
                n += 1
            except sqlite3.IntegrityError:
                pass
        counts["posts"] = n

        # reviews
        reviews = _read_jsonl("kassa_reviews.jsonl")
        n = 0
        for r in reviews:
            try:
                self.insert_review(r)
                n += 1
            except sqlite3.IntegrityError:
                pass
        counts["reviews"] = n

        # stakes
        stakes = _read_jsonl("kassa_stakes.jsonl")
        n = 0
        for s in stakes:
            try:
                self.insert_stake(s)
                n += 1
            except sqlite3.IntegrityError:
                pass
        counts["stakes"] = n

        # referrals
        referrals = _read_jsonl("kassa_referrals.jsonl")
        n = 0
        for r in referrals:
            try:
                self.insert_referral(r)
                n += 1
            except sqlite3.IntegrityError:
                pass
        counts["referrals"] = n

        # threads
        threads = _read_jsonl("kassa_threads.jsonl")
        n = 0
        for t in threads:
            try:
                self.insert_thread(t)
                n += 1
            except sqlite3.IntegrityError:
                pass
        counts["threads"] = n

        # thread messages
        msgs = _read_jsonl("kassa_thread_msgs.jsonl")
        n = 0
        for m in msgs:
            try:
                self.insert_thread_message(m)
                n += 1
            except sqlite3.IntegrityError:
                pass
        counts["thread_messages"] = n

        # contact messages
        contacts = _read_jsonl("kassa_messages.jsonl")
        n = 0
        for c in contacts:
            try:
                self.insert_contact_message(c)
                n += 1
            except sqlite3.IntegrityError:
                pass
        counts["contact_messages"] = n

        return counts
