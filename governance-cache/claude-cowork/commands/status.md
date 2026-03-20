---
description: Show full MO§ES™ governance state — active mode, posture, role, vault, and session event count.
---

# /status

Report the complete current governance state for this session.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MO§ES™ GOVERNANCE STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Mode      [active mode or "None (Unrestricted)"]    [1-line constraint summary]
Posture   [active posture or "None"]                [transaction policy]
Role      [active role or "Primary (default)"]      [authority level]
Vault     [loaded docs or "—"]
Events    [count this session]

Runtime: Cowork/Chat (prompt-native)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Derive all values from conversation history. If nothing has been set, show defaults with a prompt to activate governance.
