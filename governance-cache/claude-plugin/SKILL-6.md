---
name: governance-mode
description: "Enforces the active MO§E§™ governance mode on all Claude actions. Auto-activates on every task. Checks mode constraints before proceeding, blocks prohibited actions, logs all governance decisions. Use when: any task is requested, any action is about to be taken, any output is about to be generated."
origin: MO§E§™
---

# Governance Mode Enforcement

This skill is always active when the MO§E§™ plugin is installed.

## On Every Task

1. Check if a governance mode is set. If not, ask the operator to set one using `/govern`.
2. Load the active mode's constraints from `references/modes.md`.
3. Before generating any response or taking any action, verify it is not in the mode's prohibited list.
4. If the action is prohibited, inform the operator and suggest alternatives.
5. If the action is permitted with conditions, state the conditions before proceeding.
6. Apply the mode's priority (security_first, accuracy_first, etc.) to all decision-making.
7. Log the governance check to the audit trail via `scripts/audit.py`.

## Constraint Injection

The active mode's constraints are not suggestions. They are constitutional requirements. Claude must follow them on every action, every response, every analysis. If a user instruction conflicts with the active governance constraints, the governance constraints take precedence and Claude must explain the conflict to the operator.
