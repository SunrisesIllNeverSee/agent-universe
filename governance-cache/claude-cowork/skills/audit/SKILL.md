---
name: audit
description: >
  Produces a structured summary of all governed actions, mode changes, and decisions made in this session. Use when reviewing what happened under governance, when you need a session log, or when you say 'show audit trail', 'what was governed', or 'session log'.
---
# MO§ES™ Audit Trail

Audit generates a structured summary of all governance events in this conversation — mode changes, posture shifts, role assignments, vault loads, and significant decisions made under active governance.

## Behavior

When invoked, scan the conversation history and produce a structured audit report:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MO§ES™ SESSION AUDIT TRAIL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Governance Events:
  [#]  [EVENT TYPE]     [DETAIL]

  01   MODE SET         high-security
  02   POSTURE SET      scout
  03   VAULT LOADED     operating-agreement.md
  04   ROLE SET         primary
  05   ACTION CHECKED   "delete production database" → FLAGGED (destructive, requires confirmation)
  06   MODE CHANGE      high-security → research

Current State:
  Mode:    [active mode or "None (Unrestricted)"]
  Posture: [active posture or "None"]
  Role:    [active role or "Primary (default)"]
  Vault:   [loaded documents or "Empty"]

Session Integrity:
  Audit method: conversation-native (prompt-based)
  Events logged: [count]
  Note: For cryptographic SHA-256 audit chains, use the Claude Code plugin.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Event Types to Track

- `MODE SET` — governance mode activated
- `MODE CHANGE` — mode switched mid-session
- `POSTURE SET` — operational posture activated
- `POSTURE CHANGE` — posture switched
- `ROLE SET` — agent role assigned
- `VAULT LOADED` — document loaded into context
- `ACTION CHECKED` — action evaluated against active governance (flag result)
- `ACTION BLOCKED` — action refused under active mode/posture
- `GOVERNANCE SUSPENDED` — operator explicitly suspended governance

If no governance events have occurred in this conversation, respond:
```
No governance events recorded this session.
Use /govern [mode] to activate governance.
```
