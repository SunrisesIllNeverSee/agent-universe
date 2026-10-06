# SIGNOMY Control Surface Design

Status: active design work
Runtime baseline: CIVITAE 0.4.0

Canonical detailed working package lives in the labs workspace
(`~/Developer/_7_labs/signomy-control-surface/`, outside this repo).

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
