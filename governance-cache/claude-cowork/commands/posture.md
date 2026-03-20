---
description: Set operational posture. Controls transaction scope and action boundaries for all Claude operations in this session.
argument-hint: [scout|defense|offense]
---

# /posture

Set the operational posture to "$ARGUMENTS" for the remainder of this conversation.

**scout** — Read-only. Gather, analyze, report. No state changes, no transactions, no writes.

**defense** — Protect existing positions. Only actions that preserve current state. Flag risks, reinforce what exists.

**offense** — Full action scope. Create, modify, transact, expand. Confirm irreversible actions before executing.

## Response Format

```
✓ Posture set: [POSTURE NAME]
Transaction policy: [NO transactions | defensive only | full scope]
Behavior: [one-line description]
Active mode: [current governance mode or "None (Unrestricted)"]
```

Apply posture constraints to all subsequent responses. If a requested action exceeds current posture scope, flag it and ask for explicit escalation before proceeding.
