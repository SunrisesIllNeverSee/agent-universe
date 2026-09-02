from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .models import NormalizedTurn, ThreadLedger


CSV_SCHEMA_VERSION = "0.3.0"

TABLE_COLUMNS: dict[str, list[str]] = {
    "threads.csv": [
        "thread_id", "title", "source_platform", "source_conversation_id",
        "root_turn_id", "active_leaf_turn_id", "active_turn_count", "archive_turn_count",
        "branch_count", "document_count", "initial_purpose", "initial_goal",
        "raw_source_path", "raw_source_hash", "parser_schema", "csv_schema",
        "canon_promotion",
    ],
    "turns.csv": [
        "thread_id", "turn_id", "source_node_id", "parent_turn_id", "parent_source_node_id",
        "branch_id", "is_active_path", "sequence_index", "speaker", "timestamp",
        "elapsed_from_previous_seconds", "raw_text", "summary", "primary_category",
        "secondary_categories", "authority_type", "authority_weight", "phase_id",
        "items", "documents", "signals", "parse_scope",
    ],
    "edges.csv": [
        "thread_id", "edge_id", "from_turn_id", "to_turn_id", "edge_type", "relation",
        "confidence", "is_active_path", "temporal_signal", "elapsed_seconds", "evidence",
    ],
    "items.csv": [
        "thread_id", "item_id", "introduced_turn_id", "item_type", "statement",
        "origin_authority", "current_authority", "authority_weight", "current_status",
        "confidence", "source_turns", "related_turns", "supersedes", "notes",
    ],
    "item_events.csv": [
        "thread_id", "event_id", "item_id", "turn_id", "event_type", "status",
        "authority", "authority_weight", "confidence", "note",
    ],
    "documents.csv": [
        "thread_id", "document_id", "introduced_turn_id", "name", "file_type", "source_uri",
        "content_hash", "introduced_by", "status", "roles", "references", "content_excerpt",
        "metadata",
    ],
    "evidence.csv": [
        "thread_id", "evidence_id", "turn_id", "item_id", "evidence_type", "evidence_state",
        "source", "details",
    ],
    "reviews.csv": [
        "thread_id", "review_id", "reviewer", "target_type", "target_id", "review_version",
        "review_timestamp", "sovereignty", "compression", "purpose", "modularity",
        "verifiability", "reciprocal_resonance", "overall_disposition", "concern",
        "recommendation", "review_evidence",
    ],
    "tags.csv": [
        "thread_id", "tag_id", "target_type", "target_id", "tag", "tag_source", "confidence",
    ],
    "episodes.csv": [
        "thread_id", "episode_id", "title", "start_turn_id", "end_turn_id", "turn_ids",
        "dominant_categories", "pivot_in", "status",
    ],
}


def _json(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _csv_cell(value: Any) -> str:
    """Serialize analytical CSV safely without changing immutable raw archive data.

    Spreadsheet programs can execute cells beginning with formula markers even when the
    CSV field is quoted. Prefixing an apostrophe neutralizes those cells when opened in
    Excel/Sheets. The exact source text remains unchanged in the raw archive and ledger.
    """
    text = _json(value)
    visible = text.lstrip(" \t\r")
    if visible and visible[0] in {"=", "+", "-", "@"}:
        return "'" + text
    return text


def _write(path: Path, rows: Iterable[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_cell(row.get(column, "")) for column in columns})


def _resolve_parent_turn(turn: NormalizedTurn, all_turns: list[NormalizedTurn], source_meta: dict[str, Any]) -> str:
    by_source = {turn.source_node_id: turn.turn_id for turn in all_turns if turn.source_node_id}
    parents = source_meta.get("node_parents") or {}
    cursor = turn.parent_source_node_id
    seen: set[str] = set()
    while cursor and cursor not in seen:
        seen.add(cursor)
        if cursor in by_source:
            return by_source[cursor]
        cursor = parents.get(cursor)
    return ""


def _phase_rows(ledger: ThreadLedger) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if not ledger.turns:
        return [], {}
    flow_by_to = {flow.to_turn: flow for flow in ledger.flows}
    episodes: list[list[str]] = []
    current: list[str] = []
    for turn in ledger.turns:
        flow = flow_by_to.get(turn.turn_id)
        if flow and flow.relation == "PIVOT" and current:
            episodes.append(current)
            current = []
        current.append(turn.turn_id)
    if current:
        episodes.append(current)

    turn_map = {turn.turn_id: turn for turn in ledger.turns}
    turn_to_episode: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    for index, ids in enumerate(episodes, start=1):
        episode_id = f"E-{index:03d}"
        for turn_id in ids:
            turn_to_episode[turn_id] = episode_id
        selected = [turn_map[turn_id] for turn_id in ids]
        first_user = next((turn for turn in selected if turn.speaker == "USER"), selected[0])
        counts = Counter(category for turn in selected for category in turn.categories)
        pivot_flow = flow_by_to.get(ids[0])
        rows.append({
            "thread_id": ledger.thread_id,
            "episode_id": episode_id,
            "title": first_user.summary[:180],
            "start_turn_id": ids[0],
            "end_turn_id": ids[-1],
            "turn_ids": ids,
            "dominant_categories": [category for category, _ in counts.most_common(4)],
            "pivot_in": pivot_flow.relation if pivot_flow and pivot_flow.relation == "PIVOT" else "",
            "status": "CURRENT" if index == len(episodes) else "CLOSED",
        })
    return rows, turn_to_episode


def _elapsed_by_turn(ledger: ThreadLedger) -> dict[str, float | None]:
    return {flow.to_turn: flow.elapsed_seconds for flow in ledger.flows}


def _thread_row(ledger: ThreadLedger, all_turns: list[NormalizedTurn], source_meta: dict[str, Any]) -> dict[str, Any]:
    active = [turn for turn in all_turns if turn.is_active_path]
    return {
        "thread_id": ledger.thread_id,
        "title": ledger.title,
        "source_platform": source_meta.get("source_platform", "unknown"),
        "source_conversation_id": source_meta.get("source_conversation_id", ""),
        "root_turn_id": active[0].turn_id if active else (all_turns[0].turn_id if all_turns else ""),
        "active_leaf_turn_id": active[-1].turn_id if active else (all_turns[-1].turn_id if all_turns else ""),
        "active_turn_count": len(ledger.turns),
        "archive_turn_count": len(all_turns),
        "branch_count": source_meta.get("branch_count", 0),
        "document_count": len(ledger.documents),
        "initial_purpose": ledger.foundation.purpose,
        "initial_goal": ledger.foundation.initial_goal,
        "raw_source_path": source_meta.get("raw_source_path", ""),
        "raw_source_hash": source_meta.get("raw_source_hash", ""),
        "parser_schema": ledger.schema_version,
        "csv_schema": CSV_SCHEMA_VERSION,
        "canon_promotion": ledger.metadata.get("canon_promotion", "disabled"),
    }


def _turn_rows(
    ledger: ThreadLedger,
    all_turns: list[NormalizedTurn],
    source_meta: dict[str, Any],
    turn_to_episode: dict[str, str],
) -> list[dict[str, Any]]:
    parsed = {turn.turn_id: turn for turn in ledger.turns}
    elapsed = _elapsed_by_turn(ledger)
    rows: list[dict[str, Any]] = []
    for turn in all_turns:
        record = parsed.get(turn.turn_id)
        categories = list(record.categories) if record else []
        rows.append({
            "thread_id": ledger.thread_id,
            "turn_id": turn.turn_id,
            "source_node_id": turn.source_node_id or "",
            "parent_turn_id": _resolve_parent_turn(turn, all_turns, source_meta),
            "parent_source_node_id": turn.parent_source_node_id or "",
            "branch_id": turn.branch_id,
            "is_active_path": turn.is_active_path,
            "sequence_index": turn.sequence_index,
            "speaker": turn.speaker,
            "timestamp": turn.timestamp or "",
            "elapsed_from_previous_seconds": elapsed.get(turn.turn_id, "") if record else "",
            "raw_text": turn.content,
            "summary": record.summary if record else turn.content[:220],
            "primary_category": categories[0] if categories else "",
            "secondary_categories": categories[1:],
            "authority_type": record.authority if record else "ARCHIVE_UNPARSED",
            "authority_weight": record.authority_weight if record else "",
            "phase_id": turn_to_episode.get(turn.turn_id, ""),
            "items": record.items if record else [],
            "documents": record.documents if record else [],
            "signals": record.signals if record else [],
            "parse_scope": "ACTIVE_PATH" if record else "ARCHIVE_BRANCH",
        })
    return rows


def _edge_rows(ledger: ThreadLedger, all_turns: list[NormalizedTurn], source_meta: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    active_ids = {turn.turn_id for turn in all_turns if turn.is_active_path}
    edge_num = 0
    for turn in all_turns:
        parent_turn = _resolve_parent_turn(turn, all_turns, source_meta)
        if not parent_turn:
            continue
        edge_num += 1
        rows.append({
            "thread_id": ledger.thread_id,
            "edge_id": f"EDGE-{edge_num:04d}",
            "from_turn_id": parent_turn,
            "to_turn_id": turn.turn_id,
            "edge_type": "PARENT_CHILD",
            "relation": "TREE",
            "confidence": 1.0,
            "is_active_path": parent_turn in active_ids and turn.turn_id in active_ids,
            "temporal_signal": "",
            "elapsed_seconds": "",
            "evidence": "source conversation topology",
        })
    for flow in ledger.flows:
        edge_num += 1
        rows.append({
            "thread_id": ledger.thread_id,
            "edge_id": f"EDGE-{edge_num:04d}",
            "from_turn_id": flow.from_turn,
            "to_turn_id": flow.to_turn,
            "edge_type": "SEMANTIC_FLOW",
            "relation": flow.relation,
            "confidence": flow.confidence,
            "is_active_path": True,
            "temporal_signal": flow.temporal_signal or "",
            "elapsed_seconds": flow.elapsed_seconds if flow.elapsed_seconds is not None else "",
            "evidence": flow.evidence,
        })
    return rows


def _item_rows(ledger: ThreadLedger) -> list[dict[str, Any]]:
    return [{
        "thread_id": ledger.thread_id,
        "item_id": item.item_id,
        "introduced_turn_id": item.introduced_at,
        "item_type": item.category,
        "statement": item.statement,
        "origin_authority": item.evolution[0].authority if item.evolution else item.authority,
        "current_authority": item.authority,
        "authority_weight": item.authority_weight,
        "current_status": item.status,
        "confidence": item.confidence,
        "source_turns": item.source_turns,
        "related_turns": item.related_turns,
        "supersedes": item.supersedes,
        "notes": item.notes,
    } for item in ledger.items]


def _item_event_rows(ledger: ThreadLedger) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    counter = 0
    for item in ledger.items:
        for event in item.evolution:
            counter += 1
            rows.append({
                "thread_id": ledger.thread_id,
                "event_id": f"EV-{counter:05d}",
                "item_id": item.item_id,
                "turn_id": event.turn_id,
                "event_type": event.event,
                "status": event.status,
                "authority": event.authority,
                "authority_weight": event.authority_weight,
                "confidence": event.confidence,
                "note": event.note,
            })
    return rows


def _document_rows(ledger: ThreadLedger) -> list[dict[str, Any]]:
    return [{
        "thread_id": ledger.thread_id,
        "document_id": document.document_id,
        "introduced_turn_id": document.introduced_at,
        "name": document.name,
        "file_type": document.kind,
        "source_uri": document.uri or "",
        "content_hash": document.content_hash or "",
        "introduced_by": document.introduced_by,
        "status": document.status,
        "roles": document.roles,
        "references": document.references,
        "content_excerpt": document.content_excerpt or "",
        "metadata": document.metadata,
    } for document in ledger.documents]


def _evidence_rows(ledger: ThreadLedger) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    counter = 0
    for turn in ledger.turns:
        evidence_types: list[tuple[str, str]] = []
        if turn.speaker == "TOOL":
            evidence_types.append(("TOOL_OUTPUT", "OBSERVED"))
        if "VERIFICATION" in turn.categories:
            evidence_types.append(("VERIFICATION", "REPORTED_OR_OBSERVED"))
        if "IMPLEMENTED" in turn.categories:
            evidence_types.append(("IMPLEMENTATION", "REPORTED"))
        for _document_id in turn.documents:
            evidence_types.append(("DOCUMENT_REFERENCE", "OBSERVED"))
        for evidence_type, state in evidence_types:
            counter += 1
            rows.append({
                "thread_id": ledger.thread_id,
                "evidence_id": f"EVD-{counter:05d}",
                "turn_id": turn.turn_id,
                "item_id": turn.items[0] if turn.items else "",
                "evidence_type": evidence_type,
                "evidence_state": state,
                "source": turn.speaker,
                "details": turn.summary,
            })
    return rows


def _review_rows(ledger: ThreadLedger, reviews: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, review in enumerate(reviews or [], start=1):
        rows.append({
            "thread_id": ledger.thread_id,
            "review_id": review.get("review_id") or f"REV-{index:04d}",
            "reviewer": review.get("reviewer", "MO§ES"),
            "target_type": review.get("target_type", "thread_parse"),
            "target_id": review.get("target_id", ledger.thread_id),
            "review_version": review.get("review_version", ""),
            "review_timestamp": review.get("review_timestamp", ""),
            "sovereignty": review.get("sovereignty", ""),
            "compression": review.get("compression", ""),
            "purpose": review.get("purpose", ""),
            "modularity": review.get("modularity", ""),
            "verifiability": review.get("verifiability", ""),
            "reciprocal_resonance": review.get("reciprocal_resonance", ""),
            "overall_disposition": review.get("overall_disposition", ""),
            "concern": review.get("concern", ""),
            "recommendation": review.get("recommendation", ""),
            "review_evidence": review.get("review_evidence", []),
        })
    return rows


def _tag_rows(ledger: ThreadLedger) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    counter = 0
    for entity in ledger.foundation.key_entities:
        counter += 1
        rows.append({
            "thread_id": ledger.thread_id,
            "tag_id": f"TAG-{counter:05d}",
            "target_type": "thread",
            "target_id": ledger.thread_id,
            "tag": entity,
            "tag_source": "foundation_entity",
            "confidence": 0.9,
        })
    for turn in ledger.turns:
        for category in turn.categories:
            counter += 1
            rows.append({
                "thread_id": ledger.thread_id,
                "tag_id": f"TAG-{counter:05d}",
                "target_type": "turn",
                "target_id": turn.turn_id,
                "tag": category,
                "tag_source": "parser_category",
                "confidence": 0.88,
            })
    return rows


def write_csv_bundle(
    ledger: ThreadLedger,
    all_turns: list[NormalizedTurn],
    out_dir: str | Path,
    source_meta: dict[str, Any],
    reviews: list[dict[str, Any]] | None = None,
) -> dict[str, Path]:
    """Write the canonical analytical CSV layer.

    Raw source remains the archival evidence. These tables are normalized analytical
    interchange, not a replacement for the raw conversation. Every downstream report,
    graph, search index, or external review should be reproducible from the raw source +
    this bundle + parser/reviewer versions.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    episode_rows, turn_to_episode = _phase_rows(ledger)
    tables: dict[str, list[dict[str, Any]]] = {
        "threads.csv": [_thread_row(ledger, all_turns, source_meta)],
        "turns.csv": _turn_rows(ledger, all_turns, source_meta, turn_to_episode),
        "edges.csv": _edge_rows(ledger, all_turns, source_meta),
        "items.csv": _item_rows(ledger),
        "item_events.csv": _item_event_rows(ledger),
        "documents.csv": _document_rows(ledger),
        "evidence.csv": _evidence_rows(ledger),
        "reviews.csv": _review_rows(ledger, reviews),
        "tags.csv": _tag_rows(ledger),
        "episodes.csv": episode_rows,
    }
    written: dict[str, Path] = {}
    for filename, rows in tables.items():
        path = out / filename
        _write(path, rows, TABLE_COLUMNS[filename])
        written[filename] = path

    manifest = {
        "csv_schema_version": CSV_SCHEMA_VERSION,
        "thread_id": ledger.thread_id,
        "raw_source_hash": source_meta.get("raw_source_hash"),
        "semantics": {
            "raw_source": "immutable archival evidence",
            "csv_bundle": "normalized analytical interchange layer",
            "thread_report": "derived projection",
            "reviews": "independent third-party assessments; never parser-authored authority",
            "canon_promotion": "disabled",
        },
        "tables": {name: columns for name, columns in TABLE_COLUMNS.items()},
    }
    manifest_path = out / "schema-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    written["schema-manifest.json"] = manifest_path
    return written
