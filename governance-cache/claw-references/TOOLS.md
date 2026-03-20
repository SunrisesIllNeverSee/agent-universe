# MO§ES™ Tool Declarations
# Place this in ~/.openclaw/workspace/TOOLS.md (or merge with existing)

---

## moses_lineage_check

**When to use:** At the start of every governed loop, before any policy gate or action execution.

Verifies that the current MO§ES™ implementation carries a valid lineage anchor back to the origin filing. No anchor — nothing executes. The Second Law made operational.

Returns:
- `sovereign: true/false`
- `lineage_anchor: hash`
- `layers_verified: [archival, anchor, live-ledger]`
- `custody: Ello Cello LLC / Deric McHenry`

**Invoke as:**
```
<tool name="moses_lineage_check" />
```

---

## moses_check_governance

**When to use:** Before ANY tool use, state change, high-stakes response, or consequential action.

Loads current governance state from `~/.openclaw/governance/state.json` and evaluates whether the proposed action is permitted under the active mode and posture.

Returns:
- `permitted: true/false`
- `constraints: [list of active constraints]`
- `reason: explanation if blocked`

**Invoke as:**
```
<tool name="moses_check_governance">
  <action>description of proposed action</action>
</tool>
```

---

## moses_audit_log

**When to use:** After every governed action, immediately before final response.

Appends a new entry to `~/.openclaw/audits/moses/audit_ledger.jsonl` with SHA-256 hash chaining.

**Invoke as:**
```
<tool name="moses_audit_log">
  <agent>primary|secondary|observer</agent>
  <action>what was done</action>
  <detail>specifics</detail>
  <outcome>result or block reason</outcome>
</tool>
```

---

## moses_audit_verify

**When to use:** When operator runs `/audit verify` or when chain integrity is in question.

Reads full `audit_ledger.jsonl` and verifies every hash in the chain. Reports first broken link if found.

**Invoke as:**
```
<tool name="moses_audit_verify" />
```

---

## moses_get_status

**When to use:** When operator runs `/status` or when an agent needs to confirm current governance state.

Returns current mode, posture, role, vault contents, and last audit entry hash.

**Invoke as:**
```
<tool name="moses_get_status" />
```

---

## Governance Note

Every agent in this workspace operates under MO§ES™ constitutional governance. Before using any tool that changes state, executes a transaction, writes to a file, or makes an external call — invoke `moses_check_governance` first.

Skipping the governance check is itself a constitutional violation. It will be logged.
