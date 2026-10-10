# T0 Independent Adversarial Verification — Report

Date: 2026-10-09 · Lane: DREP2 · Runtime HEAD at exercise: `f2c01a6`
Skill: `adversarial-verification` (installed verbatim from frozen package
`reports/next-agent-package/skills/adversarial-verification/SKILL.md` →
`.devin/skills/adversarial-verification/SKILL.md`, byte-identical, `diff -q` clean).

## Adopted skill confirmation

- Canonical source present in frozen package; installed unmodified at the
  prescribed location. No substitute invented; no prior skill file existed
  at `.devin/skills/` to overwrite (pre-existing skills live under
  `.agents/skills/` and were not touched).
- The same loop was already exercised end-to-end in this repo during H5:
  builder → independent falsifier (9 findings, 3 HIGH) → bounded
  corrections → re-verifier PASS, ledgers at `reviews/H5-Comms-*`.

## RED/GREEN falsification exercise

Invariant selected: **unauthenticated and forged-credential reads of the
application/contact inboxes fail closed and return no PII** — H5 security
invariant, deterministic, architecture-determined (1A §4.4, 1B D-role
authority, H5 contract doc).

Probe: `reviews/t0_redgreen_probe.py` — builds a fresh app from the
target tree, issues 3 checks (anonymous GET `/api/inbox`, forged
`X-Admin-Key` GET `/api/inbox`, anonymous GET `/api/kassa/messages`),
expects 4xx + no PII in body. Exit 0 GREEN / exit 1 RED.

| Step | Tree | Mutation | Result |
|---|---|---|---|
| Baseline | `1_agent-universe @ f2c01a6` | none | **GREEN** (3/3 fail closed) |
| RED | `git worktree /tmp/t0-wt @ f2c01a6` | `admin_key_matches()` → `return True` (single-function guard-disable) | **RED** — all 3 reads return 200; probe exits 1 naming each path |
| Restore | worktree removed (`git worktree remove --force`) | mutation never committed; `grep DELIBERATE app/auth.py` → absent | **GREEN** — probe exits 0 |
| Post-check | `1_agent-universe` | `git status` shows only intended new files; `git diff` on `app/` empty | runtime unchanged |

Reviewer identity/independence: falsification executed by the lane agent
(DREP2) but the probe is **independent of the builder harness** — it does
not call the pytest suite; it instantiates the app and probes HTTP paths
directly, and it proved it can go red for the intended reason
(guard-disabled → 200 leaks), not merely re-run builder tests.

## Findings ledger

`reviews/T0-Findings.csv` — no defects found; one informational note
(403 vs 401 status semantics — fail-closed either way, intentional).

## Frozen contract → runtime reconciliation confirmation

`docs/contracts/FROZEN-CONTRACT-IMPLEMENTATION-CROSSWALK.md` (`987c18e`,
owner-corrected `3d099dc`) remains the accurate contract↔runtime map:
7/7 contracts FROZEN, ~0 contract objects implemented, named gaps
enumerated. No drift detected during this exercise — the probed invariant
matches the crosswalk's H5 "CLOSED" row.

## Formal gate recommendation

**T0_ADVERSARIAL is ready for owner review and attestation.** Evidence:
skill installed byte-identical, genuine RED→GREEN demonstrated on a live
security invariant in a disposable worktree, zero mutation of main, ledgers
present. The installer deliberately does NOT self-attest — per the
controller's contract and the owner's operating rule, attestation requires
`attest T0_ADVERSARIAL --evidence <file>` executed under owner authority.
This report + probe + transcript + CSV constitute the evidence packet.
