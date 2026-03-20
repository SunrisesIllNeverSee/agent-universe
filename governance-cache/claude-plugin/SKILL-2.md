---
name: audit-trail
description: "Maintains a cryptographic audit trail for all governed actions. Auto-activates on any state change, file modification, command execution, or transaction. Generates SHA-256 hash chain. Use when: any action is taken, any configuration changes, any message is sent or received."
origin: MO§E§™
---

# Audit Trail

This skill logs every governed action to a tamper-evident SHA-256 hash chain.

## What Gets Logged

- Governance mode changes
- Posture changes
- Role assignments
- Vault document loads and unloads
- Messages sent and received
- Actions permitted and actions blocked
- Governance checks passed and failed
- COMMAND bar setting changes

## How It Works

1. On any state change or action, call `scripts/audit.py log_action()` with the component, action, detail, and current governance state.
2. The audit script generates a SHA-256 hash that includes a reference to the previous entry's hash, forming a chain.
3. The entry is appended to the ledger. The ledger is append-only — nothing is deleted, nothing is modified.
4. Use `/audit verify` to check the entire chain for tampering at any time.

## Integrity Guarantee

If any entry in the chain is modified after the fact, the hash chain breaks and `/audit verify` will report the exact entry where tampering occurred.
