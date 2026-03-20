---
description: View the governance audit trail. Every governed action is logged with SHA-256 hash in a tamper-evident chain.
argument-hint: [number|verify|hash|agent name]
---

# /audit

Show audit trail. Argument: "$ARGUMENTS". If empty, show last 10 entries.

## Usage

```
/audit                   # show last 10 entries
/audit 20                # show last 20 entries
/audit verify            # verify integrity of entire hash chain
/audit hash              # show current session hash
/audit agent claude      # show entries for a specific agent
```

## What Gets Logged

Every governed action: mode changes, posture changes, role assignments, vault loads, messages sent, messages read, actions permitted, actions blocked, governance checks passed, governance checks failed.

## Integrity

Each entry is SHA-256 hashed with a reference to the previous entry's hash, forming a tamper-evident chain. `/audit verify` checks every link. If any entry has been modified, the chain breaks and the verification fails.
