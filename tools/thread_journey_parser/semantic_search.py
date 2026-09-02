from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from typing import Any, Protocol


class EmbeddingBackend(Protocol):
    name: str

    def encode(self, texts: list[str]) -> list[list[float]]:
        ...


class SentenceTransformerBackend:
    """Optional local embedding backend.

    No network/API key is required once the selected sentence-transformers model is
    available locally. The dependency is optional so the core parser remains small.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "Semantic search requires the optional 'semantic' extra: "
                "pip install 'thread-parser[semantic]'"
            ) from exc
        self.name = f"sentence-transformers:{model_name}"
        self._model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [list(map(float, row)) for row in vectors]


@dataclass
class SemanticHit:
    record_key: str
    thread_id: str
    record_type: str
    target_id: str
    title: str
    content: str
    score: float
    category: str = ""
    authority: str = ""
    status: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class SemanticSearch:
    """Semantic search over the archive index with cached local embeddings.

    Search operates on indexed analytical records. It never rewrites raw archives,
    parser records, authority, or canon state.
    """

    def __init__(self, connection: sqlite3.Connection, backend: EmbeddingBackend) -> None:
        self.conn = connection
        self.backend = backend
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS semantic_embeddings (
                   record_key TEXT NOT NULL,
                   model TEXT NOT NULL,
                   vector_json TEXT NOT NULL,
                   PRIMARY KEY(record_key, model)
               )"""
        )
        self.conn.commit()

    @staticmethod
    def _record_text(row: sqlite3.Row) -> str:
        title = row["title"] or ""
        content = row["content"] or ""
        category = row["category"] or ""
        return f"{title}\n{category}\n{content}".strip()

    def _vector_for(self, row: sqlite3.Row) -> list[float]:
        cached = self.conn.execute(
            "SELECT vector_json FROM semantic_embeddings WHERE record_key=? AND model=?",
            (row["record_key"], self.backend.name),
        ).fetchone()
        if cached:
            return list(map(float, json.loads(cached[0])))
        vector = self.backend.encode([self._record_text(row)])[0]
        self.conn.execute(
            "INSERT OR REPLACE INTO semantic_embeddings(record_key,model,vector_json) VALUES (?,?,?)",
            (row["record_key"], self.backend.name, json.dumps(vector, separators=(",", ":"))),
        )
        return vector

    def search(
        self,
        query: str,
        *,
        thread_id: str | None = None,
        record_type: str | None = None,
        limit: int = 30,
        minimum_score: float = 0.20,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if thread_id:
            clauses.append("thread_id=?")
            params.append(thread_id)
        if record_type:
            clauses.append("record_type=?")
            params.append(record_type)
        sql = "SELECT * FROM records"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        rows = self.conn.execute(sql, params).fetchall()
        if not rows:
            return []

        query_vector = self.backend.encode([query])[0]
        scored: list[SemanticHit] = []
        for row in rows:
            vector = self._vector_for(row)
            score = _cosine(query_vector, vector)
            if score < minimum_score:
                continue
            scored.append(SemanticHit(
                record_key=row["record_key"],
                thread_id=row["thread_id"],
                record_type=row["record_type"],
                target_id=row["target_id"],
                title=row["title"] or "",
                content=row["content"] or "",
                score=score,
                category=row["category"] or "",
                authority=row["authority"] or "",
                status=row["status"] or "",
                timestamp=row["timestamp"] or "",
            ))
        scored.sort(key=lambda hit: hit.score, reverse=True)
        self.conn.commit()
        return [hit.to_dict() for hit in scored[:limit]]
