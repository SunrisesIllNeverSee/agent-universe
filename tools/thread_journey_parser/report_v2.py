from __future__ import annotations

from collections import Counter

from .evolution import enrich_evolution
from .models import ExtractedItem, ThreadLedger


def cite(turns: list[str]) -> str:
    unique: list[str] = []
    for turn_id in turns:
        if turn_id and turn_id not in unique:
            unique.append(turn_id)
    return "[" + ", ".join(unique) + "]" if unique else ""


def _item_line(item: ExtractedItem) -> str:
    related = item.source_turns + item.related_turns
    supersedes = f"; supersedes {', '.join(item.supersedes)}" if item.supersedes else ""
    return (
        f"- **{item.item_id} · {item.category} / {item.status}:** {item.statement} "
        f"— authority `{item.authority}` ({item.authority_weight:.2f}){supersedes} {cite(related)}"
    )


def _evolution_line(item: ExtractedItem) -> str:
    if not item.evolution:
        return _item_line(item)
    steps = []
    for event in item.evolution:
        steps.append(
            f"{event.turn_id} `{event.event}` → `{event.status}` / "
            f"`{event.authority}` {event.authority_weight:.2f}"
        )
    return (
        f"- **{item.item_id} · {item.category}:** {item.statement}  \n"
        f"  Evolution: " + " → ".join(steps) + f"  \n"
        f"  Current: **{item.status}**, authority **{item.authority} ({item.authority_weight:.2f})** "
        f"{cite(item.source_turns + item.related_turns)}"
    )


def _phases(ledger: ThreadLedger) -> list[tuple[str, list[str]]]:
    phases: list[tuple[str, list[str]]] = []
    current: list[str] = []
    phase_no = 1
    for idx, turn in enumerate(ledger.turns):
        if idx > 0:
            flow = ledger.flows[idx - 1]
            if flow.relation == "PIVOT" and current:
                phases.append((f"Phase {phase_no}", current))
                phase_no += 1
                current = []
        current.append(turn.turn_id)
    if current:
        phases.append((f"Phase {phase_no}", current))
    return phases


def _phase_summary(ledger: ThreadLedger, turn_ids: list[str]) -> str:
    selected = [turn for turn in ledger.turns if turn.turn_id in turn_ids]
    user = next((turn for turn in selected if turn.speaker == "USER"), selected[0])
    cats = Counter(cat for turn in selected for cat in turn.categories)
    leading = ", ".join(category for category, _ in cats.most_common(3))
    return f"{user.summary} Main signals: {leading or 'continuation'}."


def _current_authoritative_items(ledger: ThreadLedger) -> list[ExtractedItem]:
    allowed_status = {"ACCEPTED", "IMPLICITLY_ACCEPTED", "VERIFIED", "IMPLEMENTED_REPORTED"}
    return sorted(
        [
            item for item in ledger.items
            if item.status in allowed_status and item.authority_weight >= 0.75
        ],
        key=lambda item: (item.authority_weight, int(item.introduced_at[1:])),
        reverse=True,
    )


def render_report(ledger: ThreadLedger) -> str:
    ledger = enrich_evolution(ledger)
    foundation = ledger.foundation
    lines: list[str] = [
        f"# Thread Journey Report — {ledger.title}",
        "",
        f"**Thread:** `{ledger.thread_id}`  ",
        f"**Turns parsed:** {len(ledger.turns)}  ",
        f"**Parser schema:** {ledger.schema_version}  ",
        "**Canon promotion:** disabled — parser output remains reviewable thread-local evidence.",
        "",
        "## 1. Thread foundation",
        "",
        f"**Purpose:** {foundation.purpose} {cite(foundation.source_turns[:1])}",
        "",
        f"**Initial goal:** {foundation.initial_goal} {cite(foundation.source_turns[:1])}",
    ]
    if foundation.starting_state:
        lines.extend(["", "**Starting state:**"] + [f"- {item}" for item in foundation.starting_state])
    if foundation.initial_requests:
        lines.extend(["", "**Initial requests:**"] + [f"- {item}" for item in foundation.initial_requests])

    lines.extend(["", "## 2. Journey", ""])
    for name, ids in _phases(ledger):
        lines.append(f"### {name} — {ids[0]} to {ids[-1]}")
        lines.append("")
        lines.append(_phase_summary(ledger, ids) + " " + cite([ids[0], ids[-1]]))
        important_flows = [
            flow for flow in ledger.flows
            if flow.to_turn in ids and flow.relation in {
                "PIVOT", "CORRECTION", "DEFERRED_ERROR", "ACCEPT_BY_CONTINUATION",
                "BUILD_ON", "RECOVERY", "RETURN",
            }
        ]
        for flow in important_flows:
            temporal = f"; temporal signal `{flow.temporal_signal}`" if flow.temporal_signal else ""
            lines.append(
                f"- **{flow.relation}:** {flow.from_turn} → {flow.to_turn}; "
                f"{'; '.join(flow.evidence) or 'transition classified from local flow'}{temporal} "
                f"{cite([flow.from_turn, flow.to_turn])}"
            )
        lines.append("")

    implemented = [item for item in ledger.items if item.status in {"IMPLEMENTED_REPORTED", "VERIFIED"}]
    open_actions = [item for item in ledger.items if item.category == "ACTION" and item.status == "OPEN"]
    decisions = [
        item for item in ledger.items
        if (item.category in {"DECISION", "CANON_UPDATE"} and item.status == "ACCEPTED")
        or item.status == "IMPLICITLY_ACCEPTED"
    ]
    deferred = [item for item in ledger.items if item.category == "DEFERRED_ERROR" and item.status == "OPEN"]
    errors = [item for item in ledger.items if item.category in {"ERROR", "MISDIRECTION", "CORRECTION", "DEFERRED_ERROR"}]

    lines.extend(["## 3. Actions taken", ""])
    lines.extend([_item_line(item) for item in implemented] or ["- No action has sufficient implementation/verification evidence in the parsed thread."])

    lines.extend(["", "## 4. Actions still needed", ""])
    lines.extend([_item_line(item) for item in open_actions] or ["- No open actions detected."])
    if deferred:
        lines.extend(["", "### Deferred issues", ""])
        lines.extend([_item_line(item) for item in deferred])

    lines.extend(["", "## 5. Decisions and canon changes", ""])
    lines.extend([_item_line(item) for item in decisions] or ["- No explicit or continuation-supported decisions detected."])

    lines.extend(["", "## 6. Authority and evolution", ""])
    lines.append(
        "This section preserves where an idea/decision/action started, how later turns changed its authority or status, "
        "and where it stands at thread close. Continuation can strengthen a specific assistant proposal, but never turns the whole prior assistant response into user-approved canon."
    )
    lines.append("")
    evolved = [
        item for item in ledger.items
        if item.category in {"IDEA", "SUGGESTION", "DECISION", "CANON_UPDATE", "CORRECTION", "ACTION"}
        and (len(item.evolution) > 1 or item.supersedes or item.authority_weight >= 0.75)
    ]
    lines.extend([_evolution_line(item) for item in evolved] or ["- No item crossed the evolution-reporting threshold."])

    current = _current_authoritative_items(ledger)
    lines.extend(["", "### Current authoritative thread-local state", ""])
    if current:
        for item in current[:20]:
            lines.append(
                f"- **{item.item_id}:** {item.statement} — `{item.status}` / `{item.authority}` "
                f"({item.authority_weight:.2f}) {cite(item.source_turns + item.related_turns)}"
            )
    else:
        lines.append("- No current high-authority item detected.")

    lines.extend(["", "## 7. Errors, corrections, and misdirection", ""])
    lines.extend([_item_line(item) for item in errors] or ["- No errors/corrections detected."])

    lines.extend(["", "## 8. Documents and artifacts", ""])
    if ledger.documents:
        for document in ledger.documents:
            extra = f"; content hash `{document.content_hash[:12]}…`" if document.content_hash else ""
            lines.append(
                f"- **{document.document_id} — {document.name}**: introduced by {document.introduced_by}; "
                f"status `{document.status}`; referenced at {cite(document.references)}{extra}"
            )
    else:
        lines.append("- No documents or file artifacts detected.")

    lines.extend(["", "## 9. Where the thread finished", ""])
    tail = ledger.turns[-min(6, len(ledger.turns)):]
    for turn in tail:
        lines.append(f"- **{turn.turn_id} {turn.speaker}:** {turn.summary} {cite([turn.turn_id])}")

    lines.extend(["", "## 10. Parser commentary / new observations", ""])
    observations: list[str] = []
    flow_counts = Counter(flow.relation for flow in ledger.flows)
    authority_lifts = sum(
        1 for item in ledger.items for event in item.evolution
        if event.event == "AUTHORITY_LIFT_BY_CONTINUATION"
    )
    supersessions = sum(len(item.supersedes) for item in ledger.items)
    if authority_lifts:
        observations.append(
            f"Detected {authority_lifts} scoped authority lift(s) where later user behavior adopted a specific assistant-originated item."
        )
    if supersessions:
        observations.append(
            f"Detected {supersessions} conservative supersession/evolution link(s). These remain parser inferences pending human review."
        )
    if flow_counts["PIVOT"]:
        observations.append(
            f"The thread contains {flow_counts['PIVOT']} explicit pivot(s); phase boundaries are meaningful context resets rather than ordinary continuation."
        )
    if deferred:
        observations.append(
            f"There are {len(deferred)} unresolved issue(s) explicitly deferred to preserve flow; later continuation must not erase those objections."
        )
    if ledger.documents:
        observations.append(
            f"{len(ledger.documents)} document/artifact record(s) participate in the thread history and remain attached to their introducing/referencing turns."
        )
    if not observations:
        observations.append("No additional structural observation crossed the parser's conservative threshold.")
    for observation in observations:
        lines.append(f"- **Parser inference — not canon:** {observation}")

    lines.extend([
        "", "---", "", "### Citation convention", "",
        "`[T###]` references normalized turn IDs in `thread-ledger.json`. Raw turn text is retained there. "
        "Authority scores order evidence; they are not truth probabilities."
    ])
    return "\n".join(lines) + "\n"
