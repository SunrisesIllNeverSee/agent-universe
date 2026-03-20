---
name: status
description: >
  Reports the complete current governance state — active mode, posture, role, vault contents, and event count. Use when you want a snapshot of all active governance settings, or when you say 'governance status', 'what mode am I in', or 'show governance state'.
---
# MO§ES™ Governance Status

When invoked, report the complete current governance state for this session.

## Behavior

Scan the conversation history for all governance events and produce:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MO§ES™ GOVERNANCE STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Mode      [active mode]         [1-line constraint summary]
Posture   [active posture]      [transaction policy]
Role      [active role]         [authority level]
Vault     [loaded docs or —]
Events    [count this session]

Runtime: Cowork/Chat (prompt-native)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If no governance has been set:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MO§ES™ GOVERNANCE STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Mode      None (Unrestricted)
Posture   None
Role      Primary (default)
Vault     Empty
Events    0

Use /govern [mode] to activate governance.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
