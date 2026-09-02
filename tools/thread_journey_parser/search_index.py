from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
  record_key TEXT PRIMARY KEY,
  thread_id TEXT NOT NULL,
  record_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  title TEXT,
  content TEXT,
  speaker TEXT,
  category TEXT,
  authority TEXT,
  status TEXT,
  timestamp TEXT,
  source_run TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_records_thread ON records(thread_id);
CREATE INDEX IF NOT EXISTS idx_records_type ON records(record_type);
CREATE TABLE IF NOT EXISTS tags (
  record_key TEXT NOT NULL,
  tag TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'manual',
  UNIQUE(record_key, tag)
);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
CREATE TABLE IF NOT EXISTS collections (
  name TEXT PRIMARY KEY,
  description TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS collection_members (
  collection_name TEXT NOT NULL,
  record_key TEXT NOT NULL,
  UNIQUE(collection_name, record_key)
);
"""


class ArchiveIndex:
    def __init__(self, db_path: str | Path):
        self.path = Path(db_path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._fts = self._ensure_fts()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "ArchiveIndex":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _ensure_fts(self) -> bool:
        try:
            self.conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS records_fts USING fts5(record_key UNINDEXED, title, content)"
            )
            return True
        except sqlite3.OperationalError:
            return False

    @staticmethod
    def _read_csv(path: Path) -> list[dict[str, str]]:
        if not path.exists():
            return []
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def _upsert_record(self, row: dict[str, Any]) -> None:
        values = (
            row["record_key"], row["thread_id"], row["record_type"], row["target_id"],
            row.get("title", ""), row.get("content", ""), row.get("speaker", ""),
            row.get("category", ""), row.get("authority", ""), row.get("status", ""),
            row.get("timestamp", ""), row["source_run"],
        )
        self.conn.execute(
            """INSERT INTO records
               (record_key,thread_id,record_type,target_id,title,content,speaker,category,authority,status,timestamp,source_run)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(record_key) DO UPDATE SET
                 title=excluded.title, content=excluded.content, speaker=excluded.speaker,
                 category=excluded.category, authority=excluded.authority, status=excluded.status,
                 timestamp=excluded.timestamp, source_run=excluded.source_run""",
            values,
        )
        if self._fts:
            self.conn.execute("DELETE FROM records_fts WHERE record_key = ?", (row["record_key"],))
            self.conn.execute(
                "INSERT INTO records_fts(record_key,title,content) VALUES (?,?,?)",
                (row["record_key"], row.get("title", ""), row.get("content", "")),
            )

    def ingest_run(self, run_dir: str | Path) -> int:
        """Index a parser output directory. Search/indexing never reinterprets raw text."""
        run = Path(run_dir).expanduser().resolve()
        canonical = run / "canonical"
        threads = self._read_csv(canonical / "threads.csv")
        thread_id = threads[0].get("thread_id", "UNKNOWN") if threads else "UNKNOWN"
        count = 0

        for turn in self._read_csv(canonical / "turns.csv"):
            key = f"{thread_id}:turn:{turn.get('turn_id','')}"
            self._upsert_record({
                "record_key": key,
                "thread_id": thread_id,
                "record_type": "turn",
                "target_id": turn.get("turn_id", ""),
                "title": f"{turn.get('turn_id','')} {turn.get('speaker','')}",
                "content": turn.get("raw_text", ""),
                "speaker": turn.get("speaker", ""),
                "category": turn.get("primary_category", ""),
                "authority": turn.get("authority_type", ""),
                "timestamp": turn.get("timestamp", ""),
                "source_run": str(run),
            })
            count += 1

        for item in self._read_csv(canonical / "items.csv"):
            key = f"{thread_id}:item:{item.get('item_id','')}"
            self._upsert_record({
                "record_key": key,
                "thread_id": thread_id,
                "record_type": "item",
                "target_id": item.get("item_id", ""),
                "title": f"{item.get('item_type','')} {item.get('item_id','')}",
                "content": item.get("statement", ""),
                "category": item.get("item_type", ""),
                "authority": item.get("current_authority", ""),
                "status": item.get("current_status", ""),
                "source_run": str(run),
            })
            count += 1

        for doc in self._read_csv(canonical / "documents.csv"):
            key = f"{thread_id}:document:{doc.get('document_id','')}"
            self._upsert_record({
                "record_key": key,
                "thread_id": thread_id,
                "record_type": "document",
                "target_id": doc.get("document_id", ""),
                "title": doc.get("name", ""),
                "content": doc.get("content_excerpt", ""),
                "status": doc.get("status", ""),
                "source_run": str(run),
            })
            count += 1

        for tag in self._read_csv(canonical / "tags.csv"):
            target_type = tag.get("target_type", "")
            target_id = tag.get("target_id", "")
            key = f"{thread_id}:{target_type}:{target_id}"
            self.conn.execute(
                "INSERT OR IGNORE INTO tags(record_key,tag,source) VALUES (?,?,?)",
                (key, tag.get("tag", ""), tag.get("tag_source", "parser")),
            )
        self.conn.commit()
        return count

    def search(
        self,
        query: str,
        *,
        thread_id: str | None = None,
        record_type: str | None = None,
        tag: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if thread_id:
            clauses.append("r.thread_id = ?")
            params.append(thread_id)
        if record_type:
            clauses.append("r.record_type = ?")
            params.append(record_type)
        if tag:
            clauses.append("EXISTS (SELECT 1 FROM tags t WHERE t.record_key=r.record_key AND t.tag=?)")
            params.append(tag)

        where_extra = (" AND " + " AND ".join(clauses)) if clauses else ""
        if self._fts and query.strip():
            sql = (
                "SELECT r.* FROM records_fts f JOIN records r ON r.record_key=f.record_key "
                "WHERE records_fts MATCH ?" + where_extra + " LIMIT ?"
            )
            final_params = [query] + params + [limit]
        else:
            sql = (
                "SELECT r.* FROM records r WHERE (r.title LIKE ? OR r.content LIKE ?)"
                + where_extra + " LIMIT ?"
            )
            like = f"%{query}%"
            final_params = [like, like] + params + [limit]
        return [dict(row) for row in self.conn.execute(sql, final_params).fetchall()]

    def add_tag(self, record_key: str, tag: str, source: str = "manual") -> None:
        if not self.conn.execute("SELECT 1 FROM records WHERE record_key=?", (record_key,)).fetchone():
            raise KeyError(f"Unknown record: {record_key}")
        self.conn.execute(
            "INSERT OR IGNORE INTO tags(record_key,tag,source) VALUES (?,?,?)", (record_key, tag, source)
        )
        self.conn.commit()

    def create_collection(self, name: str, description: str = "") -> None:
        self.conn.execute(
            "INSERT INTO collections(name,description) VALUES (?,?) ON CONFLICT(name) DO UPDATE SET description=excluded.description",
            (name, description),
        )
        self.conn.commit()

    def add_to_collection(self, name: str, record_key: str) -> None:
        if not self.conn.execute("SELECT 1 FROM collections WHERE name=?", (name,)).fetchone():
            self.create_collection(name)
        if not self.conn.execute("SELECT 1 FROM records WHERE record_key=?", (record_key,)).fetchone():
            raise KeyError(f"Unknown record: {record_key}")
        self.conn.execute(
            "INSERT OR IGNORE INTO collection_members(collection_name,record_key) VALUES (?,?)",
            (name, record_key),
        )
        self.conn.commit()

    def collection(self, name: str) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.conn.execute(
                """SELECT r.* FROM collection_members m
                   JOIN records r ON r.record_key=m.record_key
                   WHERE m.collection_name=? ORDER BY r.timestamp, r.record_key""",
                (name,),
            ).fetchall()
        ]

    def stats(self) -> dict[str, Any]:
        by_type = {
            row["record_type"]: row["n"]
            for row in self.conn.execute("SELECT record_type, COUNT(*) n FROM records GROUP BY record_type")
        }
        return {
            "records": self.conn.execute("SELECT COUNT(*) FROM records").fetchone()[0],
            "threads": self.conn.execute("SELECT COUNT(DISTINCT thread_id) FROM records").fetchone()[0],
            "tags": self.conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0],
            "collections": self.conn.execute("SELECT COUNT(*) FROM collections").fetchone()[0],
            "by_type": by_type,
            "fts5": self._fts,
        }


def write_search_results(path: str | Path, results: list[dict[str, Any]]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    return target
