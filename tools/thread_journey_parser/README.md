# Thread Parser v0.4

A local developer tool for parsing historical AI conversations into **source-preserving, turn-level analytical records**.

Thread Parser is not a website product, not a Signomy runtime feature, and not a global memory system. It is intended to live as a standalone developer utility.

Its core job is to reconstruct:

- where a thread started,
- what happened turn by turn,
- how the flow continued, pivoted, broke, recovered, or returned,
- how ideas, decisions, canon candidates, actions, errors, and documents evolved,
- what was implemented versus merely proposed,
- where the thread finished,
- and which exact turns support each conclusion.

It also provides a local archive/search/browser layer across many parsed threads.

## Core architectural rule

```text
IMMUTABLE RAW SOURCE
        │
        ▼
NORMALIZATION
chronology + parent/child topology
        │
        ▼
PRIMARY PARSE
turns + flow + authority + items + evidence
        │
        ▼
CANONICAL ANALYTICAL CSV
        │
        ├── reports
        ├── search
        ├── tags / projects
        ├── comparisons
        ├── path maps
        └── independent MO§ES review
```

Raw source is archival evidence. Parser output is derived analytical state. Reports and reviews are projections.

## What v0.4 includes

### Historical import and topology

- Generic JSON conversations
- ChatGPT export conversations
- Markdown transcripts
- ChatGPT parent/child tree preservation
- Active path separated from abandoned branches
- Chronology kept separate from topology
- Raw source hash and source manifest

Only the active path participates in continuation/authority inference. Inactive branches are preserved for archive/search/path analysis.

### Turn-level parse

Categories include:

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

### Authority and evolution

User statements are weighted more heavily than assistant proposals.

Continuation is treated as scoped behavioral evidence: if the user builds directly on a specific assistant suggestion without objection, that item can gain authority without converting the entire prior assistant turn into canon.

Tracked item evolution may include:

```text
INTRODUCED
→ AUTHORITY_LIFT_BY_CONTINUATION
→ CHALLENGED
→ IMPLEMENTATION_REPORTED
→ VERIFIED
→ SUPERSEDED
```

Superseded records remain in history.

Automatic global canon promotion is disabled.

### Rethread-style descriptive extraction

The enrichment layer conservatively extracts source-bound observations:

- `FACT`
- `PREFERENCE`
- `CONSTRAINT`
- `DEFINITION`
- `OBJECTIVE`
- `CONTEXT`

These remain `OBSERVED` records. They do not become decisions or canon automatically.

### Documents and evidence

Documents are first-class records with:

- introducing turn
- references
- role
- URI when available
- optional content excerpt
- SHA-256 content hash when content is available

Implementation and verification remain separate from proposals/actions.

### Canonical CSV foundation

Each parse can emit:

```text
canonical/
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

The CSV layer is the canonical **analytical interchange layer**, not the immutable source of truth.

Spreadsheet formula injection is neutralized in CSV outputs without mutating raw source or the JSON ledger.

### Full-text search

Parsed runs can be indexed into a local SQLite archive:

```bash
thread-parser-archive index archive.sqlite ./thread-parser-output
thread-parser-archive search archive.sqlite "migration manifest"
```

SQLite FTS5 is used when available, with a LIKE fallback.

Search indexes thread records, turns, extracted items, and documents. Search never reparses or changes meaning.

### Semantic search

Semantic search is optional and local:

```bash
pip install 'thread-parser[semantic]'
thread-parser-archive semantic archive.sqlite "where did the architecture change?"
```

The default backend uses `sentence-transformers` and caches embeddings by record/model in SQLite.

The core package does not require an embedding dependency.

### Tags and projects / collections

Manual organization is stored separately from parser state:

```bash
thread-parser-archive tag archive.sqlite THREAD-X:turn:T042 architecture
thread-parser-archive collection-create archive.sqlite upsilon-step23
thread-parser-archive collection-add archive.sqlite upsilon-step23 THREAD-X:thread:THREAD-X
```

Collections may contain entire threads or individual records and can span multiple threads.

### Multi-thread comparison

```bash
thread-parser-archive compare archive.sqlite THREAD-A THREAD-B --format markdown
```

Comparison currently reports:

- record / turn / item / document counts
- category distributions
- authority distributions
- status distributions
- common and unique tags
- decisions
- canon updates
- open actions
- shared decision/canon vocabulary

Comparison is descriptive. It does not resolve cross-thread canon conflicts.

### Branch and path visualization

Each parser run can emit:

```text
maps/
├── thread-tree.mmd
├── thread-tree.dot
├── path-map.md
├── thread-map.mmd
├── thread-map.dot
└── thread-map.html
```

`thread-map.html` is a dependency-free interactive SVG tree:

- parent/child topology
- active-path emphasis
- abandoned branch preservation
- clickable turns
- raw text and parser metadata
- path filtering

### Local archive browser UI

Run:

```bash
thread-parser-browser archive.sqlite --open
```

or:

```bash
thread-parser-archive browse archive.sqlite --open
```

The browser binds to `127.0.0.1` by default and provides:

- thread browsing
- full-text search
- optional semantic search
- record-type filtering
- tag filtering
- raw record inspection
- manual tag add/remove
- project / collection creation
- record membership management
- entire-thread project membership
- thread profiles
- multi-thread comparison
- direct branch/path visualization

Enable semantic search in the browser with:

```bash
thread-parser-browser archive.sqlite --semantic-model all-MiniLM-L6-v2 --open
```

### Append-only run archive

A parse can be frozen with the original raw source and all outputs:

```bash
thread-parser conversation.json \
  --out ./runs/latest \
  --archive-root ./archive
```

Frozen layout:

```text
archive/
└── YYYY-MM-DD/
    └── THREAD-ID/
        └── TIMESTAMP/
            ├── raw/
            ├── output/
            └── manifest.json
```

Every frozen file receives a SHA-256 hash. Existing runs are never overwritten.

## Independent MO§ES third-party review

The parser produces a review packet after the primary parse.

```text
PRIMARY PARSE
     │
     ▼
freeze/hash review target
     │
     ▼
MO§ES INDEPENDENT REVIEW
     │
     ▼
reviews.csv / report annotation
```

MO§ES does not become parser logic, does not alter the primary parse, and does not promote canon.

See `MOSES-GOVERNANCE-REVIEW.md`.

## Run the parser

```bash
thread-parser conversation.json \
  --out ./thread-parser-output \
  --index-db ./archive.sqlite \
  --archive-root ./archive
```

Primary outputs:

```text
thread-ledger.json
thread-report.md
source-manifest.json
moses-review-request.json
canonical/*.csv
maps/*
```

## Standalone packaging

The install/package name is already `thread-parser`.

The current temporary repository directory still uses the historical folder name until the tool is moved out of `agent-universe`.

After extraction, the intended standalone shape is approximately:

```text
thread-parser/
├── pyproject.toml
├── README.md
├── src/thread_parser/
├── tests/
├── schemas/
├── data/
├── reports/
└── archive/
```

## Design references

The architecture borrows useful patterns from several adjacent tools without treating any one as the product model:

- historical memory extraction / state timelines: Rethread-like pattern
- exact conversation-tree preservation: ChatGPT Browser-like pattern
- search, tagging, organization, export: ChatLocker-like pattern
- row-grain analytical reports / episodes: Paxel-like pattern

Thread Parser adds its own core differentiators:

- continuation as evidence
- turn-by-turn documentation and review
- authority weighting
- pivot / deferred-error / recovery tracking
- item evolution and supersession
- exact turn citations
- independent MO§ES review

## Not yet claimed as solved

- perfect semantic interpretation
- automatic cross-thread canon reconciliation
- automatic public/private projection policy
- cryptographic authentication of speaker identity
- a hosted multi-user product

Those should remain separate decisions from the local parser/archive tool.
