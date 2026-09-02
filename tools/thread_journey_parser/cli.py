from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analyze import analyze_thread
from .archive_store import freeze_run
from .csv_bundle import write_csv_bundle
from .enrichment import enrich_context_records
from .evolution import enrich_evolution
from .normalize import load_thread_with_archive
from .path_map import write_path_maps
from .report_v2 import render_report
from .review_contract import load_review_response, write_moses_review_packet
from .search_index import ArchiveIndex
from .visualization import write_visualizations


PARSER_VERSION = "thread-parser-v0.4"
SCHEMA_VERSION = "0.4.0"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Parse one historical conversation into turn-level evidence, canonical CSV tables, maps, and independent review material."
    )
    p.add_argument("input", help="Thread JSON/ChatGPT export JSON/markdown transcript")
    p.add_argument("--out", default="thread-parser-output", help="Output directory")
    p.add_argument("--thread-id", default=None, help="Optional stable thread identifier")
    p.add_argument("--title", default=None, help="Override parsed thread title")
    p.add_argument(
        "--moses-review-response",
        default=None,
        help="Optional JSON response from an independent MO§ES reviewer. Imported as annotations only.",
    )
    p.add_argument(
        "--archive-root",
        default=None,
        help="Optional append-only archive root. If set, freezes raw source + complete output after parsing.",
    )
    p.add_argument(
        "--index-db",
        default=None,
        help="Optional SQLite archive index. If set, indexes the generated canonical tables for search/tagging/collections.",
    )
    p.add_argument(
        "--no-maps",
        action="store_true",
        help="Do not emit Mermaid/DOT/Markdown/HTML topology and flow maps.",
    )
    return p


def _append_review_section(report: str, reviews: list[dict]) -> str:
    if not reviews:
        return report
    lines = [report.rstrip(), "", "## Independent MO§ES third-party review", ""]
    lines.append(
        "These annotations were supplied by an external reviewer after the primary parse. "
        "They do not mutate parser records or promote canon."
    )
    lines.append("")
    for review in reviews:
        target = f"{review.get('target_type', 'thread_parse')}:{review.get('target_id', '')}"
        disposition = review.get("overall_disposition", "UNSPECIFIED")
        concern = review.get("concern") or "No concern supplied."
        evidence = review.get("review_evidence") or []
        evidence_text = f" [{', '.join(evidence)}]" if evidence else ""
        lines.append(f"- **{disposition} · {target}:** {concern}{evidence_text}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = build_parser().parse_args()
    title, active_turns, all_turns, source_meta = load_thread_with_archive(args.input)
    if args.title:
        title = args.title

    ledger = analyze_thread(title, active_turns, thread_id=args.thread_id)
    ledger = enrich_evolution(ledger)
    ledger = enrich_context_records(ledger)
    ledger.schema_version = SCHEMA_VERSION
    ledger.metadata["parser"] = PARSER_VERSION
    ledger.metadata["archive_turn_count"] = len(all_turns)
    ledger.metadata["branch_count"] = source_meta.get("branch_count", 0)
    ledger.metadata["canon_promotion"] = "disabled"
    ledger.metadata["primary_parse_scope"] = "active_path_only"
    ledger.metadata["archive_scope"] = "full_conversation_tree"

    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    canonical = out / "canonical"
    canonical.mkdir(parents=True, exist_ok=True)

    reviews = load_review_response(args.moses_review_response)
    ledger_path = out / "thread-ledger.json"
    ledger_path.write_text(json.dumps(ledger.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    report = _append_review_section(render_report(ledger), reviews)
    report_path = out / "thread-report.md"
    report_path.write_text(report, encoding="utf-8")

    review_packet_path = write_moses_review_packet(
        ledger,
        out / "moses-review-request.json",
        raw_source_hash=str(source_meta.get("raw_source_hash") or ""),
    )
    written = write_csv_bundle(ledger, all_turns, canonical, source_meta, reviews=reviews)

    source_manifest = {
        "raw_source_path": source_meta.get("raw_source_path"),
        "raw_source_hash": source_meta.get("raw_source_hash"),
        "source_platform": source_meta.get("source_platform"),
        "source_conversation_id": source_meta.get("source_conversation_id"),
        "active_leaf_source_node_id": source_meta.get("active_leaf_source_node_id"),
        "active_turn_count": len(active_turns),
        "archive_turn_count": len(all_turns),
        "branch_count": source_meta.get("branch_count", 0),
        "raw_source_semantics": "immutable archival evidence; never replaced by parser output",
        "topology_semantics": "full parent/child tree preserved; only active path influences continuation/authority inference",
    }
    source_manifest_path = out / "source-manifest.json"
    source_manifest_path.write_text(json.dumps(source_manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    maps: dict[str, Path] = {}
    if not args.no_maps:
        maps.update({f"legacy_{k}": v for k, v in write_path_maps(out).items()})
        maps.update({f"rich_{k}": v for k, v in write_visualizations(out, out / "maps").items()})

    indexed = 0
    if args.index_db:
        with ArchiveIndex(args.index_db) as index:
            indexed = index.ingest_run(out)

    frozen: Path | None = None
    if args.archive_root:
        frozen = freeze_run(
            input_path=args.input,
            run_output=out,
            archive_root=args.archive_root,
            thread_id=ledger.thread_id,
            parser_version=PARSER_VERSION,
            schema_version=SCHEMA_VERSION,
            source_meta=source_meta,
        )

    print(f"Parsed active path: {len(active_turns)} turns")
    print(f"Preserved archive: {len(all_turns)} turns across {source_meta.get('branch_count', 0)} branch(es)")
    print(ledger_path)
    print(report_path)
    print(review_packet_path)
    print(source_manifest_path)
    for path in written.values():
        print(path)
    for path in maps.values():
        print(path)
    if args.index_db:
        print(f"Indexed {indexed} searchable records into {args.index_db}")
    if frozen:
        print(f"Frozen archive run: {frozen}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
