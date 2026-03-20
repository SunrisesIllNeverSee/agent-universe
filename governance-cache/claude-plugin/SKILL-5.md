---
name: role-hierarchy
description: "Enforces Primary/Secondary/Observer role hierarchy in multi-agent workflows. Auto-activates when multiple agents are coordinating or when roles are assigned. Prevents out-of-sequence responses. Use when: multiple agents are active, roles are assigned via /role, any multi-agent coordination is occurring."
origin: MO§E§™
---

# Role Hierarchy Enforcement

This skill ensures constitutional sequence ordering when multiple agents operate together.

## Sequence Rules

1. Primary responds first. Always.
2. Secondary responds after Primary has completed. Secondary must read Primary's response before generating its own.
3. Observer responds last. Observer reads both Primary and Secondary before flagging anything.
4. No agent may respond out of turn unless Broadcast mode is explicitly active.

## Enforcement

- If Secondary attempts to respond before Primary, block and explain.
- If Observer attempts to initiate analysis, block and explain.
- If Secondary repeats Primary's analysis without adding value, flag the violation.
- All sequence decisions are logged to the audit trail.

## Broadcast Mode Exception

When the operator activates Broadcast mode, all agents respond simultaneously. Sequence ordering is suspended. All other governance constraints (mode, posture) still apply.

See `references/roles.md` for full behavioral specifications per role.
