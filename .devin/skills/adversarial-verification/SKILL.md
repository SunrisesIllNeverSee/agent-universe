---
name: adversarial-verification
description: >
  The integration gate proven on AQUA M03: builder → independent falsifier →
  bounded corrections → re-verifier sign-off. Use for any lane that claims an
  integration, migration, projection, import, auth, or multi-party boundary
  works. The falsifier never trusts the builder's harness; it invents new
  counterexamples, especially at transition points between layers.
---

# Adversarial Verification Loop

When an integration lane claims done, it is **not** done. The gate:

```
BUILDER → tests → INDEPENDENT FALSIFIER → bounded corrections → RE-VERIFIER → PASS
```

No lane completes on its own harness alone. Every harness must demonstrate it
can go red (a deliberate guard-disable/mutation check that fails as expected).

## The falsifier is a different agent

Same code review is not falsification. The falsifier:

- Reads the builder's code + claim, then **invents new counterexamples** —
  never merely re-runs the builder's harness.
- Writes findings to a ledger (`reviews/<lane>-Findings.csv` +
  `reviews/<lane>-Independent-Review.md`), not inline patches.
- Returns one of exactly three verdicts: `PASS` / `CONDITIONAL — bounded
  corrections` / `FAIL`.
- The builder then applies only the accepted findings, adds reproducers +
  regression checks, and a re-verifier (preferably same subagent resumed, or
  a fresh one) signs off.

## Attack taxonomy — where every real defect lives

All 29 defects found in AQUA M03 were transition-point failures. Always probe:

- **Schema-shape mismatch** — reader assumes a key the writer never produces
  (`rec['data']` vs actual `rec['row']` → every payload silently empty).
- **Stored-trust vs recomputation** — comparing stored fingerprint columns
  instead of recomputing `sha256(content)`.
- **Forged caller** — hand-built input carrying a real ID + wrong
  revision/fingerprint/record-set.
- **First-writer-wins poisoning** — a squatter commits under the replay key
  first, blocking the legitimate caller.
- **Replay semantics** — identical replay must return stored result; changed
  replay must reject; concurrent identical must converge.
- **Cross-role / cross-scope collisions** — global PK on `legacy_id` lets a
  foreign scope squat or collide; scope-key every derived ID.
- **Authority confusion** — a site/adapter receipt must never masquerade as
  canonical truth; check that projection output cannot write back.
- **Caller-asserted identity** — never trust `site_user_id`, `applicant_id`,
  `scope` from the caller; resolve server-side through a membership/identity
  table the caller cannot write.
- **Fabricated provenance** — don't invent IDs/text for unresolved
  references; emit explicit `UNRESOLVED`/`NULL` sentinels.
- **Silent approval/reward** — confidence/locked/certify metadata must never
  auto-produce canon decisions or reward writes; approval needs real human
  evidence.
- **Mutable lineage** — append-only triggers on pair/evidence tables;
  UPDATE/DELETE must fail.
- **Vacuous assertions** — a "negative test" that never calls the thing it
  claims to reject; every denial check must name the expected rejection.

## Minimal falsifier prompt contract

Give the falsifier: the claim, the code paths, the fixture paths, and:

> Attempt new counterexamples — do not re-run the builder's harness.
> Attack [list the taxonomy items relevant to the lane]. Write only under
> reviews/. Commit only review files. Verdict exactly one of:
> PASS | CONDITIONAL — bounded corrections | FAIL.

## Ledger schema (per finding)

`finding_id, severity, invariant, counterexample, evidence, reproduction,
affected_code, required_correction, retest, gate_impact, status`

Defects may become `closed` only after: correction + test + independent
re-verification. Advisory findings get documented as intentional-or-carried.

## What "PASS" means

Not "we didn't find anything" but "the falsifier tried every class in the
taxonomy and each held." A lane that has never been falsified is unverified,
not verified.

## Propagation

This skill is the gate, not a per-repo artifact. Any repo can adopt it by:
(1) `reviews/` directory, (2) a findings CSV, (3) a builder→falsifier
→corrections→re-verify loop. It does not require AQUA's harness shape.
