from __future__ import annotations

import argparse
import json

from .search_index import ArchiveIndex


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search, tag, and organize parsed historical threads.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("index", help="Index one parser output directory")
    p.add_argument("db")
    p.add_argument("run")

    p = sub.add_parser("search", help="Search indexed turns/items/documents")
    p.add_argument("db")
    p.add_argument("query")
    p.add_argument("--thread-id")
    p.add_argument("--type", dest="record_type")
    p.add_argument("--tag")
    p.add_argument("--limit", type=int, default=50)

    p = sub.add_parser("tag", help="Attach a manual tag to one indexed record")
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

    p = sub.add_parser("collection-show", help="List records in a collection")
    p.add_argument("db")
    p.add_argument("name")

    p = sub.add_parser("stats", help="Show archive index statistics")
    p.add_argument("db")
    return parser


def main() -> int:
    args = build_parser().parse_args()
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
        elif args.command == "tag":
            index.add_tag(args.record_key, args.tag)
            print(json.dumps({"tagged": args.record_key, "tag": args.tag}, indent=2))
        elif args.command == "collection-create":
            index.create_collection(args.name, args.description)
            print(json.dumps({"collection": args.name, "created": True}, indent=2))
        elif args.command == "collection-add":
            index.add_to_collection(args.name, args.record_key)
            print(json.dumps({"collection": args.name, "added": args.record_key}, indent=2))
        elif args.command == "collection-show":
            print(json.dumps(index.collection(args.name), indent=2, ensure_ascii=False))
        elif args.command == "stats":
            print(json.dumps(index.stats(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
