import tomllib
from pathlib import Path

from tools.thread_journey_parser.analyze import analyze_thread
from tools.thread_journey_parser.evolution import enrich_evolution
from tools.thread_journey_parser.normalize import normalize_messages
from tools.thread_journey_parser.report_v2 import render_report


def parse(messages):
    ledger = analyze_thread("evolution-test", normalize_messages(messages), thread_id="THREAD-EVOLUTION")
    return enrich_evolution(ledger)


def test_continuation_records_authority_lift_history():
    ledger = parse([
        {"role": "user", "content": "I need a parser."},
        {"role": "assistant", "content": "I would create a turn ledger."},
        {"role": "user", "content": "Then add documents and build on that with flow transitions."},
    ])
    item = next(i for i in ledger.items if i.introduced_at == "T002" and i.category == "SUGGESTION")
    assert item.status == "IMPLICITLY_ACCEPTED"
    assert item.evolution[0].authority == "ASSISTANT_PROPOSED"
    assert any(e.event == "AUTHORITY_LIFT_BY_CONTINUATION" for e in item.evolution)
    assert item.evolution[-1].authority == "USER_BUILDS_ON_ASSISTANT_PROPOSAL"


def test_later_user_canon_update_links_supersession_without_deleting_history():
    ledger = parse([
        {"role": "user", "content": "Let's use a five active stake limit for agents."},
        {"role": "assistant", "content": "Understood."},
        {"role": "user", "content": "Actually the active stake limit for agents should be three, not five."},
    ])
    earlier = next(i for i in ledger.items if i.introduced_at == "T001" and i.category == "DECISION")
    newer = next(i for i in ledger.items if i.introduced_at == "T003" and i.category == "CANON_UPDATE")
    assert earlier.status == "SUPERSEDED"
    assert earlier.item_id in newer.supersedes
    assert any(e.event == "SUPERSEDED" for e in earlier.evolution)
    assert any(e.event == "SUPERSEDES_PRIOR" for e in newer.evolution)


def test_parser_never_enables_automatic_canon_promotion():
    ledger = parse([
        {"role": "assistant", "content": "I would make this global canon."},
        {"role": "user", "content": "Then build on the parser, but keep this thread-local."},
    ])
    assert ledger.metadata["canon_promotion"] == "disabled"


def test_v2_report_surfaces_authority_evolution_and_current_state():
    ledger = parse([
        {"role": "user", "content": "Build a parser."},
        {"role": "assistant", "content": "I would track authority and evolution."},
        {"role": "user", "content": "Then add documents and keep going with that."},
    ])
    report = render_report(ledger)
    assert "## 6. Authority and evolution" in report
    assert "Current authoritative thread-local state" in report
    assert "AUTHORITY_LIFT_BY_CONTINUATION" in report


def test_subproject_has_independent_package_metadata():
    package_root = Path(__file__).parents[1] / "tools" / "thread_journey_parser"
    config = tomllib.loads((package_root / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["project"]["name"] == "thread-parser"
    assert config["project"]["scripts"]["thread-parser"] == "thread_parser.cli:main"
    assert config["project"]["scripts"]["thread-parser-archive"] == "thread_parser.archive_cli:main"
    assert config["project"]["scripts"]["thread-parser-browser"] == "thread_parser.browser:main"
    assert config["tool"]["setuptools"]["package-dir"]["thread_parser"] == "."
