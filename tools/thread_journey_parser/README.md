# Thread Journey Parser v0.2

A deliberately **single-thread** parser. It does not attempt global memory, cross-thread canon reconciliation, or autonomous truth promotion.

It converts one conversation into:

1. a **thread foundation** — where the conversation actually started,
2. a **turn ledger** — what each turn contains,
3. a **flow ledger** — continuation, build-on, pivot, correction, deferred error, recovery, return,
4. an **item lifecycle + authority history** — where an idea/decision/action began and how later turns changed its status or authority,
5. a **document registry** tied to introducing/referencing turns, and
6. a **cited journey report** using `[T###]` references.

## Core rules

- User statements outrank assistant suggestions.
- Assistant proposals do not become decisions merely because they were written.
- **Continuation matters:** when the user builds directly on a specific assistant proposal without objection, that item may become `IMPLICITLY_ACCEPTED`; this is a scoped authority lift, not blanket approval of the assistant turn.
- **Evolution matters:** items retain an event history such as `INTRODUCED → AUTHORITY_LIFT_BY_CONTINUATION → SUPERSEDED` rather than exposing only final state.
- **Supersession is additive:** later high-authority decisions/canon updates may link to materially overlapping earlier items, but older records remain intact.
- **Pivots matter:** explicit topic/direction changes create phase boundaries.
- **Deferred errors matter:** if the user flags something as wrong but defers repair to preserve flow, the objection remains open and subsequent continuation must not erase it.
- `IMPLEMENTED` is distinct from `ACTION`; implementation/verification evidence advances an action lifecycle.
- Documents are first-class records and retain turn provenance. Inline attachment content is hashed and excerpted when present.
- Parser commentary is explicitly labeled **inference, not canon**.
- Timestamps support flow interpretation (`rapid`, `same_session_likely`, `session_break`, `multi_day_gap`) but do not override semantic evidence.
- **Automatic canon promotion is disabled.** The parser can produce canon/supersession candidates only.

## Authority model

Weights are evidence-ordering hints, not truth probabilities:

| Source / behavior | Default weight |
|---|---:|
| User explicit decision/correction/canon statement | 1.00 |
| Tool evidence | 0.90 |
| User builds on a specific assistant proposal | 0.75–0.85 |
| User statement | 0.80 |
| Assistant reported implementation/verification | 0.65 |
| Assistant suggestion | 0.30 |
| Assistant inference | 0.15 |

Each tracked item may include an `evolution` list recording when its status or authority changed and which turn caused that change.

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

Each message can also include `timestamp`, `created_at`, `attachments`, or `files`.

Attachment objects may include `name`, `url`/`uri`/`path`, and optional `content`/`text`. When content is available the ledger records a SHA-256 hash plus an excerpt.

### ChatGPT export JSON

A single exported conversation object containing `mapping` and `current_node` is supported. The parser follows the active parent chain when possible so abandoned branches are not silently mixed into the active journey.

### Markdown transcript

```text
[2026-08-23T10:00:00-04:00] User: We need a parser.
[2026-08-23T10:01:00-04:00] Assistant: I would use a turn ledger.
[2026-08-23T10:02:00-04:00] User: Then add flow transitions and build on that.
```

## Run inside agent-universe

```bash
python -m tools.thread_journey_parser.cli path/to/thread.json --out /tmp/thread-report
```

Outputs:

```text
thread-ledger.json
thread-report.md
```

## Standalone packaging

This directory is now an independent Python subproject with its own `pyproject.toml`.

To pull it out later, copy only:

```text
tools/thread_journey_parser/
```

Then install it independently:

```bash
pip install ./thread_journey_parser
thread-journey-parser path/to/thread.json --out ./thread-report
```

No Signomy runtime import is required. The package has no runtime dependencies beyond Python 3.10+.

## Classification taxonomy

Turn categories include:

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

Flow relations include:

- `CONTINUATION`
- `BUILD_ON`
- `ACCEPT_BY_CONTINUATION`
- `PIVOT`
- `CORRECTION`
- `DEFERRED_ERROR`
- `RECOVERY`
- `RETURN`

The parser remains intentionally conservative. More ambiguous semantic reconciliation should be a later model-assisted pass, not a hidden rule in the deterministic ledger.

## Report sections

`thread-report.md` contains:

1. Thread foundation
2. Journey/phases
3. Actions taken
4. Actions still needed
5. Decisions and canon changes
6. Authority and evolution
7. Errors, corrections, and misdirection
8. Documents and artifacts
9. Where the thread finished
10. Parser commentary / new observations

Every substantive report item cites normalized turns with `[T###]`. The raw turn text remains in `thread-ledger.json`.

## MO§ES™ governance review

See `MOSES-GOVERNANCE-REVIEW.md` for the read-only governance assessment against:

- the public Six Fold Flame,
- `app/moses_core/governance.py`, and
- the CIVITAE MCP governance model.

Core rule: **the parser may measure and reconstruct authority, but it cannot manufacture authority.**

## Not in v0.2

- Cross-thread canon.
- Embeddings/vector database.
- Global user model.
- Automatic canon promotion.
- Perfect semantic supersession resolution.
- Automatic external document materialization when only a filename/URL is present.

Those should only be added after the per-thread ledger produces reliable reports on real long-form threads.
