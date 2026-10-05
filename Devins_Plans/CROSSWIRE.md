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

### ⤷ ELLO-ASSIST (b2bpilot + sigarena) → NEXT SESSION: canon schema work complete, push/deploy pending

Cross-repo canon-backed schema remediation completed 2026-09-21.

**Committed, NOT pushed:**
- `b2bpilot/Moses_Enterprise_B2BPilot_` commit `4d49022` — canon-backed
  SoftwareApplication + provenance fields on 43 mos2es.org pages
  (coverage 13 → 56 of 57). Push with `git push` from repo root.
  Deploy note: Cloudflare token needs Zone:Workers Routes:Edit for
  mos2es.org zone (pre-existing blocker, see D-REP-SCRATCH 2026-09-09).

**Committed and pushed:**
- `sigarena` commit `a8addf8` — lib/canon-entities.ts provenance header
  + scripts/validate-canon-entities.py. Two later commits (71b71b0,
  257180a) also on origin but NOT deployed to Cloudflare Workers —
  needs `npm run cf:build && npm run cf:deploy`.

**Validation results (all clean):**
- 0 duplicate @id across 79 live sigeconomy.com pages
- All 4 canon entities (Ello Cello LLC, SigRank, Deric J. McHenry,
  MO§ES™) exact-match frozen master-canon-v1.0.0
- Re-run validator: `python3 scripts/validate-canon-entities.py` in sigarena

**Audit documents:** `_7_labs/seo-audit/source/BUILD_REVIEW_SIGECONOMY_SCHEMA_ADAPTER.md`
(agent-report fact-check) and `UNLOGGED_KEYWORD_RESEARCH_API_PRICING.md`
(archived AI-pricing keyword export — off-topic, recommended no-pursue).

---

## 2026-10-05 · ELLO-ASSIST → ALL: Lane rules stamped estate-wide + handoff.sh scoped (owner-reported systemic issue)

**Problem (owner-reported):** agents treating coord-kit reads as license to work other lanes — gtm incident: session renamed another session's handoff + moved a file into b2bpilot + signed in over other lanes (reverted, `6618b72`). Also: "what are you working on / handoff" queries returning everyone's work.

**Fixes applied:**

1. **Lane-rule block added to:** `_coord-kit/README.md`, `_coord-kit/handoffs/ONBOARDING.md` (golden rules), `_coord-kit/scripts/handoff-template.md` + embedded template in all 3 `handoff.sh` copies, `SigRank-repos/AGENTS.md`, `SigRank-gtm/AGENTS.md`, `_control/stickypads/AGENTS.md`, `_control/search-authority/AGENTS.md`, `_control/moses-integration/AGENTS.md`, `_control/ello-repo-control/AGENTS.md`, `_5_Signomy/1_agent-universe/AGENTS.md`, `ello-repo-control/standard/current/template/AGENTS.md` (propagation source; `versions/1.0.0` left frozen).

2. **`handoff.sh current` now role-scoped** in all 3 live copies (`_coord-kit`, `SigRank-repos/scripts`, `b2bpilot/_workspace/scripts`): bare `current` → YOUR role's handoff (from `.session-current`); `current ALL` → explicit cross-lane view; no role set → warns + shows all. This was the mechanical cause of "pull everyone's handoff" — the command defaulted to latest-overall.

3. **Core rules now stated everywhere:** coord state is read-only context except your own entries; handoffs immutable + role-scoped (`HANDOFF_<ROLE>_<YYYY-MM-DD>_<HHMM>`); never rename/edit/revert/move another session's coord records — dangling state is a bus NOTE, not a task; report YOUR lane when asked for status; cross-repo writes via CROSSWIRE only.

**Not done:** 15+ divergent `handoff.sh` copies exist across archives/inactive repos — only the 3 live ones patched; per-repo `.coord` copies sync on next kit update. Legacy handoff names (GTM1_HANDOFF_*, date-first) grandfathered — never rename.
