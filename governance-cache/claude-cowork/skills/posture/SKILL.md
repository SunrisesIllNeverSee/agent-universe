---
name: posture
description: >
  Sets the operational posture for the session — Scout (read-only), Defense (protect existing state), or Offense (execute and act). Use when you need to control what Claude is allowed to do, when preparing for a transaction or risky action, or when you say 'set posture', 'read-only mode', or 'go on offense'.
---
# MO§ES™ Operational Posture

Posture controls how broadly Claude acts in this session — the scope of changes it will make, transactions it will initiate, and how cautiously it operates.

## Available Postures

### `scout`
**Read-only reconnaissance.**
- Gather, analyze, report — do not act
- No state changes, no transactions, no writes
- Information and recommendations only
- Ideal for: research, analysis, planning phases

### `defense`
**Protect existing positions.**
- Only actions that preserve or secure current state
- No new commitments or expansions
- Flag risks, reinforce what exists
- Ideal for: incident response, security review, stabilization

### `offense`
**Execute on opportunities.**
- Full action scope — create, modify, transact, expand
- Bias toward action over analysis
- Confirm irreversible actions before executing
- Ideal for: active development, deployment, growth operations

## Behavior

When invoked:

1. Confirm the posture with a status block:
```
✓ Posture set: [POSTURE NAME]
Transaction policy: [NO transactions / defensive only / full scope]
Behavior: [one-line description]
Active mode: [current governance mode or "None (Unrestricted)"]
```

2. Apply posture constraints immediately to all subsequent actions.

3. In `scout` posture: if asked to execute an action, explain what the action would do and ask for explicit posture escalation before proceeding.

4. In `defense` posture: if asked to create something new or make a commitment, flag it as outside current posture and ask to confirm or escalate to `offense`.

5. Track active posture — report it when `/status` is called.
