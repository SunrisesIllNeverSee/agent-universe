# Thread Journey Parser v0.3

A **historical single-thread conversation parser** for reconstructing how work, ideas, authority, decisions, documents, errors, and implementation state evolve from the beginning of a thread to its end.

It deliberately does **not** implement global memory or automatic canon promotion.

## Architectural layers

```text
RAW SOURCE
ChatGPT / generic JSON / Markdown
        │
        ▼
IMMUTABLE ARCHIVE EVIDENCE
raw hash + full conversation tree
        │
        ├───────────────┐
        ▼               ▼
ACTIVE PATH         ARCHIVE BRANCHES
interpreted         preserved/searchable
        │               │
        └───────┬───────┘
                ▼
       CANONICAL CSV FOUNDATION
                │
       ┌────────┼─────────┐
       ▼        ▼         ▼
   reports    search    graphs/analytics
       │
       ▼
PRIMARY PARSE RESULT
       │
       ▼
MO§ES THIRD-PARTY REVIEW
read-only annotations; no mutation
```

## What v0.3 adds

### Full conversation-tree preservation

ChatGPT exports retain:

- source node IDs,
- parent/child topology,
- the current active path,
- abandoned branches,
- chronological sequence,
- branch identifiers.

The **active path alone** drives continuation, authority, and journey interpretation. Abandoned branches are preserved in the CSV/archive layer but cannot silently influence the main parse.

### Canonical CSV analytical layer

Every run now emits `canonical/` containing:

```text
threads.csv
turns.csv
edges.csv
items.csv
item_events.csv
documents.csv
evidence.csv
reviews.csv
tags.csv
episodes.csv
schema-manifest.json
```

Semantics:

- **Raw source** = immutable archival evidence.
- **CSV bundle** = normalized analytical interchange layer.
- **Reports** = derived projections.
- **MO§ES reviews** = independent third-party annotations.
- **Canon promotion** = disabled.

This lets future search, tagging, dashboards, maps, graphs, decision timelines, Paxel-style analysis, and cross-thread tooling operate on a stable tabular foundation without reparsing the raw archive for every report.

### Authority + evolution

Tracked items preserve lifecycle events such as:

```text
INTRODUCED
→ AUTHORITY_LIFT_BY_CONTINUATION
→ CHALLENGED
→ CORRECTED
→ IMPLEMENTED
→ VERIFIED
→ SUPERSEDED
```

Older state is never deleted merely because a later state supersedes it.

### Continuation as evidence

User authority remains primary.

A specific assistant proposal can gain authority when the user clearly builds on it without objection, but this is **scoped behavioral adoption**, not blanket approval of the assistant turn.

Default evidence ordering:

| Source / behavior | Weight |
|---|---:|
| User explicit decision/correction/canon statement | 1.00 |
| Tool evidence | 0.90 |
| User builds on a specific assistant proposal | 0.75–0.85 |
| User statement | 0.80 |
| Assistant implementation/verification report | 0.65 |
| Assistant suggestion | 0.30 |
| Assistant inference | 0.15 |

Weights order evidence; they are **not truth probabilities**.

### Independent MO§ES review contract

Each parse emits:

```text
moses-review-request.json
```

The packet contains only high-impact parser claims, their lineage, source turns, and review questions under the Six Fold Flame.

MO§ES is architecturally a **third-party reviewer**:

```text
parser output
   ↓
MO§ES review
   ↓
reviews.csv / report annotation
```

It may flag authority inflation, lineage loss, over-compression, unresolved objections, or unverifiable conclusions. It cannot rewrite parser records or promote canon.

An externally produced review response can be imported with:

```bash
thread-journey-parser thread.json \
  --out ./thread-output \
  --moses-review-response ./moses-response.json
```

## Core turn taxonomy

- `FOUNDATION`
- `ACTION`
- `IMPLEMENTED`
- `IDEA`
- `DECISION`
- `CANON_UPDATE`
- `DIRECTION_CHANGE`
- `ERROR`
- `MISDIRECTION`
- `CORRECTION`
- `DEFERRED_ERROR`
- `CODE`
- `SUGGESTION`
- `VERIFICATION`
- `OPEN_QUESTION`
- `ARTIFACT`

## Flow taxonomy

- `CONTINUATION`
- `BUILD_ON`
- `ACCEPT_BY_CONTINUATION`
- `PIVOT`
- `CORRECTION`
- `DEFERRED_ERROR`
- `RECOVERY`
- `RETURN`

Timestamps support flow interpretation (`rapid`, `same_session_likely`, `session_break`, `multi_day_gap`) but semantic evidence remains primary.

## Documents

Documents/files are first-class records. The parser tracks:

- introducing turn,
- introducing actor,
- references,
- URI/path when supplied,
- content hash when inline content is available,
- content excerpt,
- document role/status.

## Input formats

### Generic JSON

```json
{
  "title": "Example",
  "messages": [
    {"role": "user", "content": "We need a parser."},
    {"role": "assistant", "content": "I would use a turn ledger."},
    {"role": "user", "content": "Then add flow transitions and build on that."}
  ]
}
```

### ChatGPT export JSON

A single exported conversation object containing `mapping` and `current_node` is supported. v0.3 preserves the full tree while analyzing the active path separately.

### Markdown transcript

```text
[2026-08-23T10:00:00-04:00] User: We need a parser.
[2026-08-23T10:01:00-04:00] Assistant: I would use a turn ledger.
[2026-08-23T10:02:00-04:00] User: Then add flow transitions and build on that.
```

## Run

Inside `agent-universe`:

```bash
python -m tools.thread_journey_parser.cli path/to/thread.json --out ./thread-output
```

Standalone installation:

```bash
pip install ./thread_journey_parser
thread-journey-parser path/to/thread.json --out ./thread-output
```

Output:

```text
thread-output/
├── source-manifest.json
├── thread-ledger.json
├── thread-report.md
├── moses-review-request.json
└── canonical/
    ├── threads.csv
    ├── turns.csv
    ├── edges.csv
    ├── items.csv
    ├── item_events.csv
    ├── documents.csv
    ├── evidence.csv
    ├── reviews.csv
    ├── tags.csv
    ├── episodes.csv
    └── schema-manifest.json
```

## Standalone boundary

The entire parser remains contained under:

```text
tools/thread_journey_parser/
```

It has its own `pyproject.toml`, standard-library-only runtime dependencies, and no Signomy application imports. The directory can be moved to a standalone repository later without untangling marketplace/runtime code.

## Current limits

- Single thread only; no cross-thread canon reconciliation.
- Search/tag **foundation** exists in CSV but no end-user search UI/index yet.
- Branches are preserved but only the active path receives full semantic parsing in v0.3.
- Supersession inference is conservative and reviewable.
- MO§ES review contract exists; a dedicated remote reviewer tool/service is the next integration step.
- Automatic canon promotion remains disabled.
- External documents referenced only by URL/path are not automatically materialized.

See `MOSES-GOVERNANCE-REVIEW.md` for the governance boundary.
