from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.thread_journey_parser.analyze import analyze_thread
from tools.thread_journey_parser.archive_store import freeze_run
from tools.thread_journey_parser.enrichment import enrich_context_records
from tools.thread_journey_parser.normalize import normalize_messages
from tools.thread_journey_parser.path_map import render_mermaid, render_path_report
from tools.thread_journey_parser.search_index import ArchiveIndex


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_context_enrichment_keeps_preferences_and_constraints_descriptive() -> None:
    turns = normalize_messages([
        {"role": "user", "content": "I prefer local-first parsing. Do not promote parser output to canon."},
        {"role": "assistant", "content": "We should store that as a constraint."},
    ])
    ledger = enrich_context_records(analyze_thread("Context", turns))
    preferences = [item for item in ledger.items if item.category == "PREFERENCE"]
    constraints = [item for item in ledger.items if item.category == "CONSTRAINT"]
    assert preferences
    assert constraints
    assert all(item.status == "OBSERVED" for item in preferences + constraints)
    assert all(item.authority.startswith("USER") for item in preferences + constraints)
    assert not any(item.status == "ACCEPTED" for item in preferences + constraints)


def test_archive_index_search_tags_and_collections(tmp_path: Path) -> None:
    run = tmp_path / "run"
    canonical = run / "canonical"
    _write_csv(canonical / "threads.csv", ["thread_id"], [{"thread_id": "THREAD-1"}])
    _write_csv(
        canonical / "turns.csv",
        ["turn_id", "speaker", "raw_text", "primary_category", "authority_type", "timestamp"],
        [{
            "turn_id": "T001",
            "speaker": "USER",
            "raw_text": "Preserve the conversation tree and active path.",
            "primary_category": "ACTION",
            "authority_type": "USER_STATEMENT",
            "timestamp": "2026-09-02T10:00:00-04:00",
        }],
    )
    _write_csv(
        canonical / "items.csv",
        ["item_id", "item_type", "statement", "current_authority", "current_status"],
        [{
            "item_id": "I-0001",
            "item_type": "DECISION",
            "statement": "Keep topology and chronology separate.",
            "current_authority": "USER_EXPLICIT",
            "current_status": "ACCEPTED",
        }],
    )
    _write_csv(
        canonical / "documents.csv",
        ["document_id", "name", "content_excerpt", "status"],
        [{"document_id": "DOC-001", "name": "spec.md", "content_excerpt": "Parser specification", "status": "INTRODUCED"}],
    )
    _write_csv(canonical / "tags.csv", ["target_type", "target_id", "tag", "tag_source"], [])

    db = tmp_path / "archive.sqlite3"
    with ArchiveIndex(db) as index:
        assert index.ingest_run(run) == 3
        results = index.search("conversation tree")
        assert any(row["record_key"] == "THREAD-1:turn:T001" for row in results)
        index.add_tag("THREAD-1:turn:T001", "topology")
        tagged = index.search("conversation", tag="topology")
        assert len(tagged) == 1
        index.create_collection("architecture", "Important architecture decisions")
        index.add_to_collection("architecture", "THREAD-1:item:I-0001")
        members = index.collection("architecture")
        assert [row["record_key"] for row in members] == ["THREAD-1:item:I-0001"]
        stats = index.stats()
        assert stats["records"] == 3
        assert stats["collections"] == 1


def test_path_map_renders_active_and_preserved_branch(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical"
    _write_csv(
        canonical / "turns.csv",
        ["turn_id", "speaker", "summary", "is_active_path", "parent_turn_id"],
        [
            {"turn_id": "T001", "speaker": "USER", "summary": "Start", "is_active_path": "True", "parent_turn_id": ""},
            {"turn_id": "T002", "speaker": "ASSISTANT", "summary": "Main answer", "is_active_path": "True", "parent_turn_id": "T001"},
            {"turn_id": "T003", "speaker": "ASSISTANT", "summary": "Abandoned branch", "is_active_path": "False", "parent_turn_id": "T001"},
        ],
    )
    _write_csv(
        canonical / "edges.csv",
        ["from_turn_id", "to_turn_id", "edge_type", "relation", "confidence"],
        [
            {"from_turn_id": "T001", "to_turn_id": "T002", "edge_type": "PARENT_CHILD", "relation": "CONTINUATION", "confidence": "0.8"},
            {"from_turn_id": "T001", "to_turn_id": "T003", "edge_type": "PARENT_CHILD", "relation": "PARENT_CHILD", "confidence": "1.0"},
        ],
    )
    mermaid = render_mermaid(tmp_path)
    report = render_path_report(tmp_path)
    assert "T003" in mermaid
    assert "branch" in mermaid
    assert "Preserved off-path turns: **1**" in report
    assert "T003" in report


def test_freeze_run_is_append_only_and_hashes_source(tmp_path: Path) -> None:
    source = tmp_path / "thread.json"
    source.write_text(json.dumps({"title": "x", "messages": []}), encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    (output / "thread-report.md").write_text("# report", encoding="utf-8")
    archive = tmp_path / "archive"

    first = freeze_run(
        input_path=source,
        run_output=output,
        archive_root=archive,
        thread_id="THREAD-X",
        parser_version="thread-parser-v0.4",
        schema_version="0.4.0",
    )
    second = freeze_run(
        input_path=source,
        run_output=output,
        archive_root=archive,
        thread_id="THREAD-X",
        parser_version="thread-parser-v0.4",
        schema_version="0.4.0",
    )
    assert first != second
    manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["immutable"] is True
    assert len(manifest["input"]["sha256"]) == 64
    assert (first / "raw" / "source.json").exists()
    assert (first / "output" / "thread-report.md").exists()


def test_package_is_named_thread_parser() -> None:
    text = Path("tools/thread_journey_parser/pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "thread-parser"' in text
    assert 'thread-parser = "thread_parser.cli:main"' in text
    assert 'thread-parser-archive = "thread_parser.archive_cli:main"' in text
