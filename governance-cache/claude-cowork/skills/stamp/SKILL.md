---
name: stamp
description: >
  Embeds a MO§ES™ governance stamp into every document produced — active mode, posture, session ID, and integrity hash. The document itself becomes the audit record. Use when document provenance matters, when outputs need to be traceable, or when you say 'stamp outputs', 'governed documents', or 'embed audit in output'.
---
# MO§ES™ Governed Output

When invoked, activate governed output for the remainder of this session. Every document produced will carry an embedded governance stamp — not as a separate log, but inside the document itself.

## Activation Confirmation

```
✓ Governed output active
Every document produced this session will be stamped with:
  — Active governance mode
  — Active posture
  — Session ID
  — Action sequence number
  — Integrity hash (SHA-256 of content + governance state)
The output is the audit record.
```

## Governance Stamp Format

Append the following block to the end of every document produced:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MO§ES™ GOVERNANCE STAMP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Produced under:  MO§ES™ Governance Framework
Mode:            [active mode, or Unrestricted if none set]
Posture:         [active posture, or None]
Role:            [active role, or Primary]
Session ID:      [first 8 chars of SHA-256 of: timestamp + first user message]
Action #:        [sequential number of governed actions this session]
Integrity hash:  [SHA-256 of: document title + active mode + posture + action #]
Runtime:         Cowork/Chat (prompt-native)
© 2026 Ello Cello LLC — MO§ES™ is trademark pending
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Hash Generation (prompt-native)

Since there is no runtime in Chat/Cowork, produce the integrity hash as follows:

1. Concatenate: `[document title] + [active mode] + [active posture] + [action #] + [timestamp]`
2. Produce a deterministic 64-character hex string representing the SHA-256 of that input
3. If you cannot compute SHA-256 directly, produce a structured placeholder: `sha256:[title-slug]:[mode]:[action#]` — this preserves the structure for downstream verification even without runtime compute

## What Counts as a Document

Apply the stamp to:
- Reports, memos, plans, specs, briefs
- Emails drafted at the user's request
- Code files produced as a primary deliverable
- Any artifact intended for use outside this conversation

Do NOT stamp:
- Inline answers, clarifications, short explanations
- Intermediate reasoning steps
- Tool call outputs

## Relationship to Document Governance

Governed output and document governance (`/doc-governance`) are complementary:
- `/doc-governance` → numbering, headers, cross-references, session index
- `/governed-output` → governance stamp embedded in the document body

Both can be active simultaneously. When they are, apply the doc header first, then the governance stamp at the end.

## Enforcement

Apply the stamp to every qualifying document for the remainder of this conversation. The stamp is not optional — it is what makes the output governed rather than merely produced.

To deactivate: `/governed-output off`
