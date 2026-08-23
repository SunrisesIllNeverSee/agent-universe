from tools.thread_journey_parser.analyze import analyze_thread
from tools.thread_journey_parser.normalize import normalize_messages
from tools.thread_journey_parser.report import render_report


def parse(messages):
    return analyze_thread("test", normalize_messages(messages), thread_id="THREAD-TEST")


def test_continuation_promotes_only_assistant_suggestion():
    ledger = parse([
        {"role": "user", "content": "I need a thread parser."},
        {"role": "assistant", "content": "I would use a turn ledger and track documents."},
        {"role": "user", "content": "Good. Then add a flow ledger between turns."},
    ])
    assert ledger.flows[1].relation in {"ACCEPT_BY_CONTINUATION", "CONTINUATION"}
    suggestion_items = [i for i in ledger.items if i.introduced_at == "T002" and i.category == "SUGGESTION"]
    assert suggestion_items
    assert suggestion_items[0].authority_weight <= 0.85


def test_build_on_implicitly_accepts_assistant_proposal():
    ledger = parse([
        {"role": "user", "content": "I need a parser."},
        {"role": "assistant", "content": "I would create a turn ledger."},
        {"role": "user", "content": "Then add documents and build on that with flow transitions."},
    ])
    assert ledger.flows[1].relation == "ACCEPT_BY_CONTINUATION"
    suggestion = next(i for i in ledger.items if i.introduced_at == "T002" and i.category == "SUGGESTION")
    assert suggestion.status == "IMPLICITLY_ACCEPTED"
    assert suggestion.authority == "USER_BUILDS_ON_ASSISTANT_PROPOSAL"


def test_explicit_pivot_creates_phase_boundary():
    ledger = parse([
        {"role": "user", "content": "Audit the API."},
        {"role": "assistant", "content": "Checked the API."},
        {"role": "user", "content": "New topic: build the thread parser."},
        {"role": "assistant", "content": "I would start with turns."},
    ])
    assert ledger.flows[1].relation == "PIVOT"
    report = render_report(ledger)
    assert "Phase 2" in report


def test_deferred_error_is_not_acceptance():
    ledger = parse([
        {"role": "assistant", "content": "I would make the global system first."},
        {"role": "user", "content": "That's wrong, but leave it for later and keep going so I don't lose flow."},
        {"role": "assistant", "content": "Continuing."},
    ])
    assert ledger.flows[0].relation == "DEFERRED_ERROR"
    deferred = [i for i in ledger.items if i.category == "DEFERRED_ERROR"]
    assert deferred and deferred[0].status == "OPEN"


def test_documents_are_first_class_records():
    ledger = parse([
        {"role": "user", "content": "Use the spec.", "attachments": [{"name": "SPEC.md", "url": "file://SPEC.md"}]},
        {"role": "assistant", "content": "I reviewed SPEC.md."},
    ])
    assert len(ledger.documents) == 1
    doc = ledger.documents[0]
    assert doc.name == "SPEC.md"
    assert doc.references == ["T001", "T002"]


def test_user_correction_has_max_authority():
    ledger = parse([
        {"role": "assistant", "content": "The cap is 50 total agents."},
        {"role": "user", "content": "No, that's wrong. The limit is active lobby occupancy."},
    ])
    correction = next(i for i in ledger.items if i.introduced_at == "T002" and i.category == "CORRECTION")
    assert correction.authority_weight == 1.0
    assert correction.status == "ACCEPTED"


def test_report_contains_turn_citations():
    ledger = parse([
        {"role": "user", "content": "Build the parser."},
        {"role": "assistant", "content": "Implemented the parser and verified tests passed."},
    ])
    report = render_report(ledger)
    assert "[T001" in report or "[T001]" in report
    assert "[T002]" in report
    assert "Actions taken" in report


def test_misdirection_and_recovery_are_tracked():
    ledger = parse([
        {"role": "assistant", "content": "I would build a global memory system first."},
        {"role": "user", "content": "No, that's not what I asked. Start with one thread."},
        {"role": "assistant", "content": "Corrected it and verified the single-thread parser now runs."},
    ])
    assert "MISDIRECTION" in ledger.turns[1].categories
    assert ledger.flows[0].relation == "CORRECTION"
    assert ledger.flows[1].relation == "RECOVERY"


def test_attachment_content_is_captured_with_hash():
    ledger = parse([
        {"role": "user", "content": "Use this.", "attachments": [{"name": "notes.md", "content": "canonical note body"}]},
    ])
    doc = ledger.documents[0]
    assert doc.content_hash
    assert doc.content_excerpt == "canonical note body"
