---
description: Set the active MO§ES™ governance mode. Applies behavioral constraints to all subsequent responses this session.
argument-hint: [high-security|high-integrity|creative|research|self-growth|problem-solving|idk|unrestricted]
---

# /govern

Set the governance mode to "$ARGUMENTS" for the remainder of this conversation.

If no argument is provided, report the currently active mode and its constraints.

## Modes and Their Constraints

**high-security** — Verify all claims. Require confirmation before destructive actions. Log reasoning chain. Flag uncertainty explicitly.

**high-integrity** — Accuracy over speed. Cite basis for every factual claim. Flag conflicting information. Acknowledge knowledge limits.

**creative** — Explore freely. Log when shifting to speculation. Flag ideas that need verification before action.

**research** — Deep investigation. Document methodology. Track information provenance. Distinguish primary from secondary sources.

**self-growth** — Reflective learning. Track reasoning improvements. Correct mistakes explicitly. Suggest next steps.

**problem-solving** — Decompose before solving. State problem, subproblems, and approach first. Verify solutions. Document assumptions.

**idk** — Guided discovery. Ask clarifying questions before acting. Propose next steps with explicit tradeoffs.

**unrestricted** — No behavioral constraints. All actions remain subject to session audit.

## Response Format

```
✓ Governance mode set: [MODE NAME]
Active constraints:
  • [constraint 1]
  • [constraint 2]
  • [constraint 3]
Enforcement: prompt-native — applied to all subsequent responses this session.
```

Apply the mode constraints to every subsequent response until the mode is changed or the session ends.
