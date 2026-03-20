---
name: doc-numbering
description: "Sequential document numbering and tracking for all files created in a conversation thread. Auto-activates whenever a file or document is created. Assigns 3-digit sequential prefix, timestamps, topic tags, and cross-reference suffixes. Use when: any file is being created, any document is being generated, any artifact is being produced."
origin: MO§E§™
---

# Document Numbering System

Every file Claude creates in a conversation thread gets a sequential number. No exceptions.

## Naming Format

```
[SEQ]_[descriptive-name].[ext]
```

Examples:
```
001_Session-Header.md
002_COMMAND-vs-AgentChattr-Analysis.md
003_COMMAND-Build-Recipe.md
004_KASSA-Architecture.mermaid
005_Governance-Plugin-README.md
003a_Build-Recipe-Revised.md        ← references doc 003
003b_Build-Recipe-Final.md          ← second reference to 003
006_After-Action-Review.md
```

## Rules

### Sequential Numbering
- Three-digit prefix: 001, 002, 003... 010, 011... 100
- Numbers increment by 1 for every new document created in the thread
- Never skip numbers
- Never reuse numbers

### Cross-Reference Suffix
- When a new doc references, revises, or extends an earlier doc, use the earlier doc's number + alphabetical suffix
- First reference: `a` (e.g., 003a)
- Second reference: `b` (e.g., 003b)
- The cross-reference doc does NOT consume the next sequential number — it branches from the parent
- The next new doc after 003a still gets 004 (unless 004 already exists)

### Versioning
- When a doc is a direct revision (same content updated), append version: `003_Build-Recipe_v2.md`
- Version goes after the name, before the extension
- v1 is implied and never written — only v2+ are marked

### Document Header

Every document gets this block at the top:

```
──────────────────────────────────────
DOC [SEQ] | [TOPIC/THEME TAG]
[YYYY-MM-DD HH:MM] | Thread: [brief thread description]
──────────────────────────────────────
```

Example:
```
──────────────────────────────────────
DOC 003 | COMMAND Build Strategy
2026-03-07 14:30 | Thread: agentchattr comparison + hackathon planning
──────────────────────────────────────
```

For cross-references:
```
──────────────────────────────────────
DOC 003a | COMMAND Build Strategy (revised)
2026-03-07 16:45 | Thread: agentchattr comparison + hackathon planning
Refs: DOC 003
──────────────────────────────────────
```

## Session Header (DOC 001)

First document in every thread. Created at the start of the conversation or when the first file is generated.

```markdown
──────────────────────────────────────
DOC 001 | SESSION HEADER
[YYYY-MM-DD HH:MM] | Thread: [topic]
──────────────────────────────────────

# [Thread Topic]

**Operator:** Luthen / Ello Cello LLC
**Started:** [timestamp]
**Theme:** [primary topic]

## Table of Contents

| Doc | Name | Topic | Time |
|-----|------|-------|------|
| 001 | Session Header | — | HH:MM |

## Pivots

[Updated when topic shifts]
```

### Updating the TOC

The TOC in DOC 001 is updated — NOT recreated — each time a new document is produced. Add a row. Don't rewrite the file.

If updating DOC 001 is not practical mid-thread (e.g., in claude.ai where files can't be edited after creation), maintain the TOC as a running note and produce the final version in the After Action Review.

## After Action Review (Final Doc)

Last document in a thread or at a major pivot point. Uses the operator's AAR template if one exists. At minimum includes:

```markdown
──────────────────────────────────────
DOC [SEQ] | AFTER ACTION REVIEW
[YYYY-MM-DD HH:MM] | Thread: [topic]
──────────────────────────────────────

# After Action Review

**Thread:** [topic]
**Duration:** [start time] → [end time]
**Docs produced:** [count]

## What was accomplished
[Summary of deliverables]

## Document Index
| Doc | Name | Topic | Time |
|-----|------|-------|------|
| 001 | ... | ... | ... |
| 002 | ... | ... | ... |
[complete list]

## Pivots
[Where did the thread change direction and why]

## What carries forward
[Open items, next steps, unresolved questions]

## Key Decisions
[Decisions made during the thread that affect future work]
```

## Pivot Tracking

When the conversation topic shifts significantly:
- Note the pivot in the next document's header with a `Pivot:` tag
- The AAR captures all pivots with context

```
──────────────────────────────────────
DOC 007 | KA§§A Bags Hackathon Plan
2026-03-07 15:20 | Thread: agentchattr comparison + hackathon planning
Pivot: from code comparison → hackathon submission strategy
──────────────────────────────────────
```
