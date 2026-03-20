---
name: docs
description: >
  Activates session-wide document governance: sequential numbering (001_, 002_...), structured headers, and cross-reference tracking on every document produced. Use when starting a governed work session, when you need traceable document output, or when you say 'track documents', 'number my docs', or 'document governance on'.
---
# MO§ES™ Document Governance

When invoked, activate document governance for the remainder of this session. Confirm activation, then apply the rules to every document produced.

## Activation Confirmation

```
✓ Document governance active
Numbering: 001_, 002_, 003_... (sequential, no skips)
Headers:   Required on every document
Cross-refs: Tracked — new docs referencing earlier ones use parent + alpha suffix
Session index: maintained — call /docs to view
```

## Numbering Rules

- Every new document gets a 3-digit sequential prefix: `001_`, `002_`, `003_`...
- Incrementing by 1 per new document
- Cross-references (new doc referencing an earlier doc): parent number + alpha suffix (`001a_`, `001b_`). Does NOT consume the next sequential number.
- Versions of the same document: append `v2`, `v3` before the extension (`001_report-v2.md`)
- Never skip or reuse numbers

## Required Header

Every document produced under active governance must open with:

```
──────────────────────────────────────
DOC [SEQ] | [TOPIC/THEME TAG]
[YYYY-MM-DD HH:MM] | Session: [session description]
──────────────────────────────────────
```

Cross-references add: `Refs: DOC [parent]`
Pivots add: `Pivot: [from → to]`

## First Document = Session Header (DOC 001)

If no documents have been created yet this session, DOC 001 is the session header:
- Operator: [user name or org]
- Timestamp and session theme
- TOC table: `Doc | Name | Topic | Time`
- TOC updates as documents are created — never recreated

## Final Document = After Action Review

The last document of a session is the After Action Review:
- What was accomplished
- Complete document index
- Pivots tracked
- What carries forward
- Key decisions

## Session Index

Track every document created this session. When `/docs` is called, output the full index:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MO§ES™ DOCUMENT INDEX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
001  [name]    [topic]    [time]
002  [name]    [topic]    [time]
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Enforcement

Apply these rules to every document produced for the remainder of this conversation — reports, memos, plans, specs, emails, briefs, code files. No exceptions while document governance is active.

To deactivate: `/doc-governance off`
