import csv
import json
from pathlib import Path

from tools.thread_journey_parser.analyze import analyze_thread
from tools.thread_journey_parser.csv_bundle import TABLE_COLUMNS, write_csv_bundle
from tools.thread_journey_parser.evolution import enrich_evolution
from tools.thread_journey_parser.normalize import load_thread_with_archive, normalize_messages
from tools.thread_journey_parser.review_contract import build_moses_review_packet, load_review_response


def _ledger(messages):
    turns = normalize_messages(messages)
    return enrich_evolution(analyze_thread("test", turns, thread_id="THREAD-CSV")), turns


def _chatgpt_tree_fixture():
    def msg(role, text, t):
        return {
            "author": {"role": role},
            "content": {"content_type": "text", "parts": [text]},
            "create_time": t,
            "metadata": {},
        }

    return {
        "id": "conv-tree-1",
        "title": "Branched conversation",
        "current_node": "n5",
        "mapping": {
            "n1": {"id": "n1", "parent": None, "children": ["n2"], "message": msg("user", "Build a parser.", 1)},
            "n2": {"id": "n2", "parent": "n1", "children": ["n3", "n4"], "message": msg("assistant", "I would use a turn ledger.", 2)},
            "n3": {"id": "n3", "parent": "n2", "children": [], "message": msg("user", "Abandoned branch: use one giant summary instead.", 3)},
            "n4": {"id": "n4", "parent": "n2", "children": ["n5"], "message": msg("user", "Then add flow transitions and documents.", 4)},
            "n5": {"id": "n5", "parent": "n4", "children": [], "message": msg("assistant", "Implemented and verified the active-path parser.", 5)},
        },
    }


def test_chatgpt_archive_preserves_tree_without_parsing_abandoned_branch(tmp_path: Path):
    source = tmp_path / "conversation.json"
    source.write_text(json.dumps(_chatgpt_tree_fixture()), encoding="utf-8")

    title, active_turns, all_turns, meta = load_thread_with_archive(source)
    assert title == "Branched conversation"
    assert len(all_turns) == 5
    assert len(active_turns) == 4
    assert meta["branch_count"] == 1

    inactive = next(turn for turn in all_turns if turn.source_node_id == "n3")
    assert inactive.is_active_path is False
    assert inactive.branch_id.startswith("branch-")

    ledger = enrich_evolution(analyze_thread(title, active_turns, thread_id="THREAD-TREE"))
    assert all("giant summary" not in turn.raw_text for turn in ledger.turns)

    out = tmp_path / "canonical"
    write_csv_bundle(ledger, all_turns, out, meta)

    with (out / "turns.csv").open(encoding="utf-8", newline="") as handle:
        turns = list(csv.DictReader(handle))
    assert len(turns) == 5
    inactive_row = next(row for row in turns if row["source_node_id"] == "n3")
    assert inactive_row["parse_scope"] == "ARCHIVE_BRANCH"
    assert inactive_row["parent_turn_id"] == "T002"

    with (out / "edges.csv").open(encoding="utf-8", newline="") as handle:
        edges = list(csv.DictReader(handle))
    assert any(
        row["from_turn_id"] == "T002"
        and row["to_turn_id"] == inactive.turn_id
        and row["edge_type"] == "PARENT_CHILD"
        for row in edges
    )


def test_csv_bundle_writes_all_canonical_tables(tmp_path: Path):
    ledger, turns = _ledger([
        {"role": "user", "content": "Build the parser and use SPEC.md.", "attachments": [{"name": "SPEC.md", "content": "spec body"}]},
        {"role": "assistant", "content": "Implemented the parser and verified tests passed."},
    ])
    meta = {
        "source_platform": "generic_json",
        "raw_source_path": "fixture.json",
        "raw_source_hash": "abc123",
        "branch_count": 0,
    }
    written = write_csv_bundle(ledger, turns, tmp_path, meta)
    assert set(TABLE_COLUMNS).issubset(written)
    for filename, columns in TABLE_COLUMNS.items():
        with (tmp_path / filename).open(encoding="utf-8", newline="") as handle:
            header = next(csv.reader(handle))
        assert header == columns
    manifest = json.loads((tmp_path / "schema-manifest.json").read_text(encoding="utf-8"))
    assert manifest["semantics"]["raw_source"] == "immutable archival evidence"
    assert manifest["semantics"]["canon_promotion"] == "disabled"


def test_moses_review_packet_is_independent_and_read_only():
    ledger, _turns = _ledger([
        {"role": "assistant", "content": "I would use a turn ledger."},
        {"role": "user", "content": "Then add flow transitions and build on that."},
    ])
    packet = build_moses_review_packet(ledger, raw_source_hash="rawhash")
    assert packet["relationship"] == "independent_third_party_review"
    assert packet["read_only"] is True
    assert packet["review_target"]["raw_source_hash"] == "rawhash"
    assert "Do not mutate parser output." in packet["required_review_rules"]
    assert "Do not promote parser or reviewer inference into canon." in packet["required_review_rules"]
    assert packet["review_target_hash"]


def test_external_review_response_populates_reviews_csv_without_mutating_items(tmp_path: Path):
    ledger, turns = _ledger([
        {"role": "user", "content": "Let's use a turn ledger."},
        {"role": "assistant", "content": "Implemented the turn ledger."},
    ])
    statuses_before = {item.item_id: item.status for item in ledger.items}
    response = tmp_path / "review.json"
    response.write_text(json.dumps({
        "reviews": [{
            "review_id": "REV-X",
            "reviewer": "MO§ES",
            "target_type": "thread_parse",
            "target_id": ledger.thread_id,
            "overall_disposition": "WARNING",
            "verifiability": "WARNING",
            "concern": "One implementation claim needs stronger tool evidence.",
            "review_evidence": ["T002"],
        }]
    }), encoding="utf-8")
    reviews = load_review_response(response)
    write_csv_bundle(ledger, turns, tmp_path / "canonical", {"source_platform": "generic_json"}, reviews=reviews)

    assert {item.item_id: item.status for item in ledger.items} == statuses_before
    with (tmp_path / "canonical" / "reviews.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["reviewer"] == "MO§ES"
    assert rows[0]["overall_disposition"] == "WARNING"
