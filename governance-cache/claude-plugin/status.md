---
description: Show the full governance state — mode, posture, role, vault, audit count, and session integrity.
---

# /status

Display the complete governance state in one view.

## Output

Shows:
- Active governance mode + its priority
- Active posture + its transaction policy
- Current role + authority level
- Loaded vault documents (count + names)
- Audit trail entry count
- Last audit hash
- Session integrity hashes (config + content)
- Any active constraints or prohibitions

## Usage

```
/status
```

No arguments. Full snapshot of current governed state.
