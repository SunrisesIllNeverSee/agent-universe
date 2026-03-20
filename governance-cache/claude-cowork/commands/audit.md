---
description: View the MO§ES™ governance audit trail for this session. Summarizes all mode changes, posture shifts, role assignments, and governed actions.
---

# /audit

Scan the conversation history and produce a structured audit report of all governance events this session.

## Output Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MO§ES™ SESSION AUDIT TRAIL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Governance Events:
  [#]  [EVENT TYPE]     [DETAIL]

Current State:
  Mode:    [active mode or "None (Unrestricted)"]
  Posture: [active posture or "None"]
  Role:    [active role or "Primary (default)"]
  Vault:   [loaded documents or "Empty"]

Session Integrity:
  Audit method: conversation-native (prompt-based)
  Events logged: [count]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Event types: MODE SET, MODE CHANGE, POSTURE SET, ROLE SET, VAULT LOADED, ACTION CHECKED, ACTION BLOCKED.

If no governance events exist, respond: "No governance events recorded this session. Use /govern [mode] to activate governance."
