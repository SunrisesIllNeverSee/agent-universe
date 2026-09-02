from __future__ import annotations

import argparse
import json
from pathlib import Path

from .browser import serve_archive
from .compare import compare_threads, render_markdown
from .search_index import ArchiveIndex
from .semantic_search import SemanticSearch, SentenceTransformerBackend


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search, tag, organize, compare, and browse parsed historical threads.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("index", help="Index one parser output directory")
    p.add_argument("db")
    p.add_argument("run")

    p = sub.add_parser("search", help="Full-text search indexed turns/items/documents")
    p.add_argument("db")
    p.add_argument("query")
    p.add_argument("--thread-id")
    p.add_argument("--type", dest="record_type")
    p.add_argument("--tag")
    p.add_argument("--limit", type=int, default=50)

    p = sub.add_parser("semantic", help="Semantic search with optional local sentence-transformers embeddings")
    p.add_argument("db")
    p.add_argument("query")
    p.add_argument("--thread-id")
    p.add_argument("--type", dest="record_type")
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--minimum-score", type=float, default=0.20)
    p.add_argument("--model", default="all-MiniLM-L6-v2")

    p = sub.add_parser("tag", help="Attach a manual tag to one indexed record")
    p.add_argument("db")
    p.add_argument("record_key")
    p.add_argument("tag")

    p = sub.add_parser("untag", help="Remove a manual tag from one indexed record")
    p.add_argument("db")
    p.add_argument("record_key")
    p.add_argument("tag")

    p = sub.add_parser("collection-create", help="Create/update a named collection")
    p.add_argument("db")
    p.add_argument("name")
    p.add_argument("--description", default="")

    p = sub.add_parser("collection-add", help="Add a record to a named collection")
    p.add_argument("db")
    p.add_argument("name")
    p.add_argument("record_key")

    p = sub.add_parser("collection-remove", help="Remove a record from a named collection")
    p.add_argument("db")
    p.add_argument("name")
    p.add_argument("record_key")

    p = sub.add_parser("collection-show", help="List records in a collection")
    p.add_argument("db")
    p.add_argument("name")

    p = sub.add_parser("collections", help="List named collections")
    p.add_argument("db")

    p = sub.add_parser("compare", help="Compare two or more indexed threads descriptively")
    p.add_argument("db")
    p.add_argument("thread_ids", nargs="+")
    p.add_argument("--format", choices=["json", "markdown"], default="json")
    p.add_argument("--out")

    p = sub.add_parser("browse", help="Run the local archive browser UI")
    p.add_argument("db")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--open", action="store_true", dest="open_browser")

    p = sub.add_parser("stats", help="Show archive index statistics")
    p.add_argument("db")
    return parser


def _write_or_print(text: str, path: str | None) -> None:
    if path:
        target = Path(path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(target)
    else:
        print(text)


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "browse":
        serve_archive(args.db, host=args.host, port=args.port, open_browser=args.open_browser)
        return 0

    with ArchiveIndex(args.db) as index:
        if args.command == "index":
            print(json.dumps({"indexed": index.ingest_run(args.run), "stats": index.stats()}, indent=2))
        elif args.command == "search":
            print(json.dumps(index.search(
                args.query,
                thread_id=args.thread_id,
                record_type=args.record_type,
                tag=args.tag,
                limit=args.limit,
            ), indent=2, ensure_ascii=False))
        elif args.command == "semantic":
            backend = SentenceTransformerBackend(args.model)
            engine = SemanticSearch(index.conn, backend)
            print(json.dumps(engine.search(
                args.query,
                thread_id=args.thread_id,
                record_type=args.record_type,
                limit=args.limit,
                minimum_score=args.minimum_score,
            ), indent=2, ensure_ascii=False))
        elif args.command == "tag":
            index.add_tag(args.record_key, args.tag)
            print(json.dumps({"tagged": args.record_key, "tag": args.tag}, indent=2))
        elif args.command == "untag":
            index.conn.execute("DELETE FROM tags WHERE record_key=? AND tag=?", (args.record_key, args.tag))
            index.conn.commit()
            print(json.dumps({"untagged": args.record_key, "tag": args.tag}, indent=2))
        elif args.command == "collection-create":
            index.create_collection(args.name, args.description)
            print(json.dumps({"collection": args.name, "created": True}, indent=2))
        elif args.command == "collection-add":
            index.add_to_collection(args.name, args.record_key)
            print(json.dumps({"collection": args.name, "added": args.record_key}, indent=2))
        elif args.command == "collection-remove":
            index.conn.execute(
                "DELETE FROM collection_members WHERE collection_name=? AND record_key=?",
                (args.name, args.record_key),
            )
            index.conn.commit()
            print(json.dumps({"collection": args.name, "removed": args.record_key}, indent=2))
        elif args.command == "collection-show":
            print(json.dumps(index.collection(args.name), indent=2, ensure_ascii=False))
        elif args.command == "collections":
            rows = index.conn.execute(
                """SELECT c.name,c.description,COUNT(m.record_key) members FROM collections c
                   LEFT JOIN collection_members m ON m.collection_name=c.name
                   GROUP BY c.name ORDER BY c.name"""
            ).fetchall()
            print(json.dumps([dict(row) for row in rows], indent=2, ensure_ascii=False))
        elif args.command == "compare":
            result = compare_threads(index.conn, args.thread_ids)
            text = render_markdown(result) if args.format == "markdown" else json.dumps(result, indent=2, ensure_ascii=False)
            _write_or_print(text + ("\n" if not text.endswith("\n") else ""), args.out)
        elif args.command == "stats":
            print(json.dumps(index.stats(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
