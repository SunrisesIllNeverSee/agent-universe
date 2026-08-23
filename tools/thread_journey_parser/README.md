# Thread Journey Parser v1

A deliberately **single-thread** parser. It does not attempt global memory, cross-thread canon reconciliation, or autonomous truth promotion.

It converts one conversation into:

1. a **thread foundation** (where the conversation started),
2. a **turn ledger** (what each turn contains),
3. a **flow ledger** (continuation, build-on, pivot, correction, deferred error, return),
4. an **item lifecycle ledger** (proposed, accepted, implicitly accepted, implemented, challenged, open),
5. a **document registry** tied to introducing/referencing turns, and
6. a **cited journey report** using `[T###]` references.

## Core rules

- User statements outrank assistant suggestions.
- Assistant proposals do not become decisions merely because they were written.
- **Continuation matters:** when the user builds directly on a specific assistant proposal without objection, that item may become `IMPLICITLY_ACCEPTED`; the inference is scoped to the item, not the whole assistant turn.
- **Pivots matter:** explicit topic/direction changes create phase boundaries.
- **Deferred errors matter:** if the user flags something as wrong but defers repair to preserve flow, the objection remains open and subsequent continuation must not erase it.
- `IMPLEMENTED` is distinct from `ACTION`; implementation/verification evidence advances an action lifecycle.
- Documents are first-class records and retain turn provenance. Inline attachment content is hashed and excerpted when present.
- Parser commentary is explicitly labeled **inference, not canon**.
- Timestamps support flow interpretation (`rapid`, `same_session_likely`, `session_break`, `multi_day_gap`) but do not override semantic evidence.

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

## Run

From the repository root:

```bash
python -m tools.thread_journey_parser.cli path/to/thread.json --out /tmp/thread-report
```

Outputs:

```text
thread-ledger.json
thread-report.md
```

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

The v1 parser is intentionally conservative: semantic reconciliation beyond explicit local flow is left for a later model-assisted pass.

## Authority model

The weights are evidence-ordering hints, not truth scores:

| Source / behavior | Default weight |
|---|---:|
| User explicit decision/correction/canon statement | 1.00 |
| Tool evidence | 0.90 |
| User builds on a specific assistant proposal | 0.75–0.85 |
| User statement | 0.80 |
| Assistant reported implementation/verification | 0.65 |
| Assistant suggestion | 0.30 |
| Assistant inference | 0.15 |

These weights stay in the ledger so a later reasoning pass can distinguish user authority from assistant brainstorming.

## Report sections

`thread-report.md` contains:

1. Thread foundation
2. Journey/phases
3. Actions taken
4. Actions still needed
5. Decisions and canon changes
6. Errors, corrections, and misdirection
7. Documents and artifacts
8. Where the thread finished
9. Parser commentary / new observations

Every substantive report item cites normalized turns with `[T###]`. The raw turn text remains in `thread-ledger.json`.

## Not in v1

- Cross-thread canon.
- Embeddings/vector database.
- Global user model.
- Automatic canon promotion.
- Perfect semantic supersession resolution.
- Automatic external document materialization when only a filename/URL is present.

Those should only be added after the per-thread ledger produces reliable reports.
