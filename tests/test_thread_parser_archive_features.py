import json
from pathlib import Path

from tools.thread_journey_parser.analyze import analyze_thread
from tools.thread_journey_parser.archive_store import freeze_run
from tools.thread_journey_parser.browser import APP_HTML
from tools.thread_journey_parser.compare import compare_threads, profile_thread
from tools.thread_journey_parser.csv_bundle import write_csv_bundle
from tools.thread_journey_parser.enrichment import enrich_context_records
from tools.thread_journey_parser.evolution import enrich_evolution
from tools.thread_journey_parser.normalize import normalize_messages
from tools.thread_journey_parser.search_index import ArchiveIndex
from tools.thread_journey_parser.semantic_search import SemanticSearch
from tools.thread_journey_parser.visualization import write_visualizations


def _make_run(tmp_path: Path, thread_id: str, title: str, messages: list[dict]) -> Path:
    turns = normalize_messages(messages)
    ledger = analyze_thread(title, turns, thread_id=thread_id)
    ledger = enrich_evolution(ledger)
    ledger = enrich_context_records(ledger)
    ledger.schema_version = "0.4.0"
    ledger.metadata["parser"] = "thread-parser-v0.4"
    ledger.metadata["canon_promotion"] = "disabled"
    run = tmp_path / thread_id
    canonical = run / "canonical"
    canonical.mkdir(parents=True)
    write_csv_bundle(
        ledger,
        turns,
        canonical,
        {
            "source_platform": "fixture",
            "source_conversation_id": thread_id,
            "raw_source_path": f"{thread_id}.json",
            "raw_source_hash": f"hash-{thread_id}",
            "branch_count": 0,
        },
    )
    (run / "thread-ledger.json").write_text(json.dumps(ledger.to_dict()), encoding="utf-8")
    return run


def test_context_enrichment_is_descriptive_not_canon(tmp_path: Path):
    turns = normalize_messages([
        {"role": "user", "content": "For context, I prefer CSV outputs. Do not overwrite the raw source."},
        {"role": "assistant", "content": "I would add a searchable archive."},
    ])
    ledger = enrich_context_records(enrich_evolution(analyze_thread("context", turns, thread_id="THREAD-CONTEXT")))
    enriched = [item for item in ledger.items if item.category in {"PREFERENCE", "CONSTRAINT", "CONTEXT"}]
    assert enriched
    assert all(item.status == "OBSERVED" for item in enriched)
    assert all(item.category != "CANON_UPDATE" for item in enriched)
    assert ledger.metadata["context_enrichment"] is True


def test_archive_index_fulltext_tags_projects_and_thread_records(tmp_path: Path):
    run = _make_run(tmp_path, "THREAD-A", "CSV parser", [
        {"role": "user", "content": "Build a canonical CSV foundation and preserve raw evidence."},
        {"role": "assistant", "content": "Implemented the CSV bundle."},
    ])
    db = tmp_path / "archive.sqlite"
    with ArchiveIndex(db) as index:
        indexed = index.ingest_run(run)
        assert indexed >= 3
        assert index.stats()["by_type"]["thread"] == 1
        hits = index.search("CSV")
        assert any("CSV" in (hit["title"] + hit["content"]) for hit in hits)

        thread_key = "THREAD-A:thread:THREAD-A"
        index.add_tag(thread_key, "upsilon")
        assert index.search("", tag="upsilon")[0]["record_key"] == thread_key
        index.remove_tag(thread_key, "upsilon")
        assert index.search("", tag="upsilon") == []

        index.create_collection("Step23", "Upsilon Step 23 work")
        index.add_to_collection("Step23", thread_key)
        assert index.collection("Step23")[0]["record_key"] == thread_key
        assert index.collections()[0]["members"] == 1
        index.remove_from_collection("Step23", thread_key)
        assert index.collection("Step23") == []


class FakeEmbeddingBackend:
    name = "fake:keywords"

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            low = text.lower()
            vectors.append([
                1.0 if "csv" in low else 0.0,
                1.0 if "graph" in low or "branch" in low else 0.0,
                1.0 if "governance" in low else 0.0,
            ])
        return vectors


def test_semantic_search_uses_optional_backend_and_cached_vectors(tmp_path: Path):
    run = _make_run(tmp_path, "THREAD-S", "Semantic fixture", [
        {"role": "user", "content": "Create a canonical CSV table for every turn."},
        {"role": "assistant", "content": "Also preserve the conversation branch graph."},
    ])
    with ArchiveIndex(tmp_path / "semantic.sqlite") as index:
        index.ingest_run(run)
        engine = SemanticSearch(index.conn, FakeEmbeddingBackend())
        csv_hits = engine.search("csv", minimum_score=0.1)
        assert csv_hits
        assert "csv" in (csv_hits[0]["title"] + csv_hits[0]["content"]).lower()
        cached = index.conn.execute("SELECT COUNT(*) FROM semantic_embeddings").fetchone()[0]
        assert cached > 0


def test_multi_thread_comparison_is_descriptive(tmp_path: Path):
    run_a = _make_run(tmp_path, "THREAD-A", "Parser foundation", [
        {"role": "user", "content": "Let's use CSV and preserve decisions."},
        {"role": "assistant", "content": "Implemented CSV."},
    ])
    run_b = _make_run(tmp_path, "THREAD-B", "Parser governance", [
        {"role": "user", "content": "Let's use MO§ES review and preserve decisions."},
        {"role": "assistant", "content": "Implemented the review packet."},
    ])
    with ArchiveIndex(tmp_path / "compare.sqlite") as index:
        index.ingest_run(run_a)
        index.ingest_run(run_b)
        index.add_tag("THREAD-A:thread:THREAD-A", "parser")
        index.add_tag("THREAD-B:thread:THREAD-B", "parser")
        result = compare_threads(index.conn, ["THREAD-A", "THREAD-B"])
        assert result["thread_ids"] == ["THREAD-A", "THREAD-B"]
        assert result["common_tags"] == ["parser"]
        assert "does not reconcile conflicting canon" in result["interpretation_policy"]
        profile = profile_thread(index.conn, "THREAD-A")
        assert profile.turn_count == 2


def test_visualization_outputs_mermaid_dot_and_local_html(tmp_path: Path):
    run = _make_run(tmp_path, "THREAD-V", "Visualization", [
        {"role": "user", "content": "Build a path map."},
        {"role": "assistant", "content": "Implemented the map."},
    ])
    outputs = write_visualizations(run)
    assert set(outputs) == {"mermaid", "dot", "html"}
    assert "flowchart TD" in outputs["mermaid"].read_text(encoding="utf-8")
    html = outputs["html"].read_text(encoding="utf-8")
    assert "Thread Path Map" in html
    assert "active path" in html


def test_archive_browser_contains_requested_organization_surfaces():
    assert "semantic" in APP_HTML
    assert "Projects / collections" in APP_HTML
    assert "Compare threads" in APP_HTML
    assert "Path / branches" in APP_HTML
    assert "Tags" in APP_HTML


def test_freeze_run_preserves_source_and_hash_manifest(tmp_path: Path):
    source = tmp_path / "source.json"
    source.write_text('{"messages":[]}', encoding="utf-8")
    run = tmp_path / "run"
    run.mkdir()
    (run / "thread-report.md").write_text("# report", encoding="utf-8")
    archive = freeze_run(
        input_path=source,
        run_output=run,
        archive_root=tmp_path / "archive",
        thread_id="THREAD-FROZEN",
        parser_version="thread-parser-v0.4",
        schema_version="0.4.0",
        source_meta={"source_platform": "fixture"},
    )
    manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["immutable"] is True
    assert manifest["input"]["sha256"]
    assert (archive / "raw" / "source.json").exists()
    assert (archive / "output" / "thread-report.md").exists()
