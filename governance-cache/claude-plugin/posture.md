---
description: Set operational posture. Controls transaction policy and action scope for all Claude operations.
argument-hint: [scout|defense|offense]
---

# /posture

Set the operational posture to "$ARGUMENTS". If no argument provided, show the current active posture.

## Stances

- `scout` — Read-only. Gather, analyze, report. NO transactions. NO state changes.
- `defense` — Protect existing positions. Outbound transfers require explicit confirmation.
- `offense` — Execute on opportunities. Within governance mode constraints. Fully logged.

## Usage

```
/posture scout
/posture defense
/posture offense
/posture                 # shows current posture
```

## Interaction with Governance Mode

Posture and governance mode combine. High Security + SCOUT = maximum caution, read-only, every data point verified. Creative + OFFENSE = experimental execution, audited. The mode sets the rules. The posture sets the throttle.

See `references/postures.md` for full constraint definitions.
