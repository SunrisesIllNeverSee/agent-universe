from __future__ import annotations

from collections import Counter

from .models import ExtractedItem, ThreadLedger


def cite(turns: list[str]) -> str:
    unique = []
    for t in turns:
        if t and t not in unique:
            unique.append(t)
    return "[" + ", ".join(unique) + "]" if unique else ""


def _item_line(item: ExtractedItem) -> str:
    related = item.source_turns + item.related_turns
    return f"- **{item.category} / {item.status}:** {item.statement} {cite(related)}"


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
    selected = [t for t in ledger.turns if t.turn_id in turn_ids]
    user = next((t for t in selected if t.speaker == "USER"), selected[0])
    cats = Counter(cat for t in selected for cat in t.categories)
    leading = ", ".join(c for c, _ in cats.most_common(3))
    return f"{user.summary} Main signals: {leading or 'continuation'}."


def render_report(ledger: ThreadLedger) -> str:
    f = ledger.foundation
    lines: list[str] = [
        f"# Thread Journey Report — {ledger.title}",
        "",
        f"**Thread:** `{ledger.thread_id}`  ",
        f"**Turns parsed:** {len(ledger.turns)}  ",
        f"**Parser schema:** {ledger.schema_version}",
        "",
        "## 1. Thread foundation",
        "",
        f"**Purpose:** {f.purpose} {cite(f.source_turns[:1])}",
        "",
        f"**Initial goal:** {f.initial_goal} {cite(f.source_turns[:1])}",
    ]
    if f.starting_state:
        lines.extend(["", "**Starting state:**"] + [f"- {x}" for x in f.starting_state])
    if f.initial_requests:
        lines.extend(["", "**Initial requests:**"] + [f"- {x}" for x in f.initial_requests])

    lines.extend(["", "## 2. Journey", ""])
    for name, ids in _phases(ledger):
        lines.append(f"### {name} — {ids[0]} to {ids[-1]}")
        lines.append("")
        lines.append(_phase_summary(ledger, ids) + " " + cite([ids[0], ids[-1]]))
        important_flows = [
            fl for fl in ledger.flows
            if fl.to_turn in ids and fl.relation in {
                "PIVOT", "CORRECTION", "DEFERRED_ERROR", "ACCEPT_BY_CONTINUATION",
                "BUILD_ON", "RECOVERY"
            }
        ]
        for fl in important_flows:
            lines.append(
                f"- **{fl.relation}:** {fl.from_turn} → {fl.to_turn}; "
                f"{'; '.join(fl.evidence) or 'transition classified from local flow'} "
                f"{cite([fl.from_turn, fl.to_turn])}"
            )
        lines.append("")

    implemented = [i for i in ledger.items if i.status in {"IMPLEMENTED_REPORTED", "VERIFIED"}]
    open_actions = [i for i in ledger.items if i.category == "ACTION" and i.status == "OPEN"]
    decisions = [
        i for i in ledger.items
        if (i.category in {"DECISION", "CANON_UPDATE"} and i.status == "ACCEPTED")
        or i.status == "IMPLICITLY_ACCEPTED"
    ]
    deferred = [i for i in ledger.items if i.category == "DEFERRED_ERROR" and i.status == "OPEN"]
    errors = [i for i in ledger.items if i.category in {"ERROR", "MISDIRECTION", "CORRECTION", "DEFERRED_ERROR"}]

    lines.extend(["## 3. Actions taken", ""])
    lines.extend([_item_line(i) for i in implemented] or ["- No action has sufficient implementation/verification evidence in the parsed thread."])

    lines.extend(["", "## 4. Actions still needed", ""])
    lines.extend([_item_line(i) for i in open_actions] or ["- No open actions detected."])
    if deferred:
        lines.extend(["", "### Deferred issues", ""])
        lines.extend([_item_line(i) for i in deferred])

    lines.extend(["", "## 5. Decisions and canon changes", ""])
    lines.extend([_item_line(i) for i in decisions] or ["- No explicit or continuation-supported decisions detected."])

    lines.extend(["", "## 6. Errors, corrections, and misdirection", ""])
    lines.extend([_item_line(i) for i in errors] or ["- No errors/corrections detected."])

    lines.extend(["", "## 7. Documents and artifacts", ""])
    if ledger.documents:
        for d in ledger.documents:
            extra = f"; content hash `{d.content_hash[:12]}…`" if d.content_hash else ""
            lines.append(
                f"- **{d.document_id} — {d.name}**: introduced by {d.introduced_by}; "
                f"status `{d.status}`; referenced at {cite(d.references)}{extra}"
            )
    else:
        lines.append("- No documents or file artifacts detected.")

    lines.extend(["", "## 8. Where the thread finished", ""])
    tail = ledger.turns[-min(6, len(ledger.turns)):]
    for t in tail:
        lines.append(f"- **{t.turn_id} {t.speaker}:** {t.summary} {cite([t.turn_id])}")

    lines.extend(["", "## 9. Parser commentary / new observations", ""])
    observations: list[str] = []
    flow_counts = Counter(f.relation for f in ledger.flows)
    if flow_counts["ACCEPT_BY_CONTINUATION"]:
        observations.append(
            f"Detected {flow_counts['ACCEPT_BY_CONTINUATION']} case(s) where a user built on an assistant proposal without explicit confirmation. "
            "These were weighted as implicit, scoped acceptance rather than blanket approval."
        )
    if flow_counts["PIVOT"]:
        observations.append(
            f"The thread contains {flow_counts['PIVOT']} explicit pivot(s); phase boundaries should be treated as meaningful context resets."
        )
    if deferred:
        observations.append(
            f"There are {len(deferred)} unresolved issue(s) explicitly deferred to preserve conversational flow; later continuation should not be interpreted as acceptance of those points."
        )
    challenged = [i for i in ledger.items if i.status == "CHALLENGED"]
    if challenged:
        observations.append(
            f"{len(challenged)} assistant-originated item(s) were later challenged by the user, reinforcing the need to down-weight assistant proposals unless the user explicitly or behaviorally adopts them."
        )
    if ledger.documents:
        observations.append(
            f"{len(ledger.documents)} document/artifact record(s) participate in the thread history and should remain attached to their introducing/referencing turns rather than summarized away."
        )
    if not observations:
        observations.append("No additional structural observation crossed the parser's conservative threshold.")
    for obs in observations:
        lines.append(f"- **Parser inference — not canon:** {obs}")

    lines.extend([
        "", "---", "", "### Citation convention", "",
        "`[T###]` references the normalized turn IDs in `thread-ledger.json`. The raw text of every turn is retained there for auditability."
    ])
    return "\n".join(lines) + "\n"
