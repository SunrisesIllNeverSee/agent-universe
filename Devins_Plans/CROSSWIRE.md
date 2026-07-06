---
type: Coordination
title: CROSSWIRE — cross-repo coordination bus
description: Machine-local bus for handoffs that span repos. SCRATCHPAD is repo-local; CROSSWIRE is machine-local. Use when work in one repo needs to coordinate with work in another repo on the same machine.
tags: [coordination, crosswire, cross-repo, bus]
timestamp: 2026-01-01T00:00:00Z
last_touched: 2026-01-01 00:00 UTC
---

# CROSSWIRE (cross-repo coordination bus)

**For handoffs that span repos on the same machine.**

SCRATCHPAD.md is repo-local — it lives inside one repo and coordinates sessions
working on that repo. CROSSWIRE.md is machine-local — it coordinates work that
spans multiple repos.

## When to use CROSSWIRE vs SCRATCHPAD

| Situation | Use |
|-----------|-----|
| Two sessions on the same repo | SCRATCHPAD |
| Session A finishes work in repo X, hands off to session B in repo Y | CROSSWIRE |
| "I pushed to the app repo, the MCP repo needs a version bump" | CROSSWIRE |
| "The migration landed, the docs repo needs updating" | CROSSWIRE |
| Same repo, different features | SCRATCHPAD |

## Protocol

1. **Read the tail before acting.** Check if there are pending cross-repo handoffs.
2. **Message format:** `### ⤷ <FROM> (repo X) → <TO> (repo Y): <subject>`
3. **Include the repo paths** so the receiving session knows where to look.
4. **Link to handoff docs** in `Devins_Plans/handoffs/` for structured transfers.
5. **Mark resolved** when the receiving session picks up.

## Example

```
### ⤷ DEVIN (sigrank-app) → GTM (RNS): sandbox shipped

Sandbox UI shipped to sigrank-app main (commit abc123). The /sandbox page is
live on signalaf.com. GTM: you can now reference /sandbox in outreach.
Handoff doc: Devins_Plans/handoffs/2026-07-06-DEVIN-to-GTM-sandbox-shipped.md
```

---

<!-- Append cross-repo messages below this line -->
