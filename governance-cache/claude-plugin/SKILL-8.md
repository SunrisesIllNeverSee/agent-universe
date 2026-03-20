---
name: posture-control
description: "Enforces SCOUT/DEFENSE/OFFENSE posture on transactions and state-changing operations. Auto-activates when Claude is asked to execute transactions, modify files, call APIs, deploy code, or perform any action with external effects. Use when: any execution, transaction, file modification, API call, or state change is requested."
origin: MO§E§™
---

# Posture Control Enforcement

This skill checks the active posture before any state-changing operation.

## SCOUT Posture
If posture is SCOUT, block ALL of the following:
- File modifications
- API calls that modify state
- Transactions of any kind
- Deployments
- Any action that changes anything outside the conversation

Inform the operator: "SCOUT posture is active — read-only operations only. Switch to DEFENSE or OFFENSE posture to enable execution."

## DEFENSE Posture
If posture is DEFENSE, require explicit confirmation for:
- Any outbound transfer or payment
- Any deletion or destructive operation
- Any action that reduces holdings or assets
- Transfers exceeding 10% of any position require double confirmation

Allow without confirmation:
- Read operations
- Analysis and reporting
- Inbound transactions

## OFFENSE Posture
If posture is OFFENSE, permit execution within governance mode constraints. All executed actions are logged with full rationale to the audit trail.

See `references/postures.md` for full constraint matrix.
