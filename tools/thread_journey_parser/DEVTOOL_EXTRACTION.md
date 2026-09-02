# Thread Parser — Standalone Extraction Handoff

This branch is the developer-tool build source. It is intentionally **not** a Signomy/CIVITAE product feature.

## Copy from

Repository branch:

```text
SunrisesIllNeverSee/agent-universe
branch: codex/thread-parser-devtool-v04
```

Package source:

```text
tools/thread_journey_parser/
```

Tests to bring with it:

```text
tests/test_thread_journey_parser.py
tests/test_thread_journey_parser_evolution.py
tests/test_thread_journey_parser_csv.py
tests/test_thread_parser_devtool.py
tests/test_thread_parser_archive_features.py
```

## Intended standalone destination

```text
/Users/dericmchenry/Developer/active/thread-parser/
```

Suggested final layout:

```text
thread-parser/
├── pyproject.toml
├── README.md
├── MOSES-GOVERNANCE-REVIEW.md
├── src/
│   └── thread_parser/
├── tests/
├── schemas/
├── data/
│   ├── inbox/
│   ├── raw/
│   ├── normalized/
│   └── runs/
├── reports/
├── reviews/
└── archive/
```

When moving, rename the Python source directory from the temporary repository path to `src/thread_parser/`. The package metadata and CLI names are already `thread-parser` / `thread_parser`.

## Do not carry Signomy runtime code

The parser package does not require `app/`, `frontend/`, CIVITAE routes, KA§§A runtime, or Signomy deployment files.

MO§ES is consumed through the independent review contract; it is not imported as runtime parser logic.

## Current v0.4 feature surface

- historical ChatGPT/generic JSON/Markdown import
- preserved parent/child topology and inactive branches
- active-path-only continuation/authority inference
- canonical CSV bundle
- authority/evolution tracking
- documents/evidence
- fact/preference/constraint/definition/objective/context enrichment
- append-only archived parse runs with SHA-256 manifests
- SQLite full-text archive index
- optional local semantic search
- manual tags
- cross-thread projects/collections
- multi-thread comparison
- Mermaid/DOT/interactive-SVG path visualization
- local archive browser UI
- independent MO§ES review packets/responses

## Important authority boundary

Search, tagging, projects, comparisons, visualizations, and the archive browser consume parser outputs. They do not reinterpret raw source and do not write back into decision/canon state.
