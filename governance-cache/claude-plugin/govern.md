---
description: Set the active MO§E§™ governance mode. Controls behavioral constraints for all subsequent Claude actions.
argument-hint: [high-security|high-integrity|creative|research|self-growth|problem-solving|idk|unrestricted]
---

# /govern

Set the governance mode to "$ARGUMENTS". If no argument provided, show the current active mode.

Apply the constraints from `references/modes.md` for the selected mode. Log the mode change to the audit trail.

## Modes

- `high-security` — Verify all claims, require confirmation before destructive actions, log reasoning chain
- `high-integrity` — Accuracy above all, cite sources, flag uncertainty
- `creative` — Explore freely, log reasoning, flag when shifting to speculation
- `research` — Deep investigation, document methodology, track provenance
- `self-growth` — Reflective learning, track improvements, identify gaps
- `problem-solving` — Decompose before solving, verify solutions, document assumptions
- `idk` — Guided discovery, clarifying questions, propose next steps with tradeoffs
- `unrestricted` — No constraints, all actions still audited

## Usage

```
/govern high-security
/govern research
/govern creative
/govern                  # shows current mode
```

## Behavior

When a mode is set, Claude follows its constraints on every subsequent action until changed. All mode changes are logged to the audit trail with timestamp and previous mode.

See `references/modes.md` for full constraint definitions per mode.
