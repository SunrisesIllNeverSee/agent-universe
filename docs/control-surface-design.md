# SIGNOMY Control Surface Design

Status: active design work
Runtime baseline: CIVITAE 0.4.0

Canonical detailed working package lives in the labs workspace
(`~/Developer/_7_labs/signomy-control-surface/`, outside this repo).

## Frozen contract set — PHASE 1 FROZEN (2026-10-07)

The authoritative specifications for runtime hardening lanes live at
`reports/phase-1/` in that package and are FROZEN — they are starting
specifications to implement against, not items to rediscover:

- `PHASE-1A-AGREEMENT-STACK.md`
- `PHASE-1B-ENTITLEMENT-MATRIX.md`
- `PHASE-1C-DELIVERY-EVIDENCE.md`
- `PHASE-1D-ENTITY-NODE.md`
- `PHASE-1E-ENTERPRISE-NODE.md`
- `PHASE-1F-WORKENTRY-UNBLOCK.md`
- `PHASE-1G-AUTHORITY-TABLE.md`

Closeout authority: `PHASE-1-CLOSEOUT.md` ("PHASE 1 FROZEN — PHASE 2 DESIGN
RE-BASELINE AUTHORIZED"). NOTE: some supporting documents in that package
(the H0–H7 crosswalk, reconciliation log, owner-decision readiness) still
carry pre-freeze headers — the contract files' `FROZEN` status and the
closeout are authoritative.

Current verified structural findings:

- `/dashboard` → `/agentdash` is parent/child, not duplication
- `/command` is an operational hub routing to `/console`, `/mission`, `/deploy`, `/campaign`
- KA§§A bountyboard is a real work-market surface
- `/switchboard` is gated — requires Refinery
- Runtime/security invariants in AGENTS.md remain authoritative

External design artifacts are maintained outside the repository; identifiers
intentionally omitted from source control.

This document is a pointer only. Do not infer implementation architecture from
earlier UX drafts.
