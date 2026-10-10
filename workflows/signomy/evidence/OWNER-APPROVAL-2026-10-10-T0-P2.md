# SIGNOMY owner decision record — 2026-10-10

## Provenance and scope
Owner's instruction in the active ChatGPT conversation on 2026-10-10:
"yes sounds good... where are we on the roadmap"

This reply was given directly to an explicit request to approve three bounded gates together: T0_ADVERSARIAL, T0_GATE, and P2_PROVISIONAL. GPT transcribed the decision into the repository for controller use. This is **a contemporaneous transcription of owner approval**, not an independently signed or cryptographically verified owner statement.

## Approved gates

1. **T0_ADVERSARIAL — APPROVED.** Accept the independent adversarial-verification evidence for the specific tested privacy/security scope, including independent rerun, discovered advisory PII leak, corrected guards, and genuine GREEN. Supporting evidence: `reviews/T0-Adversarial-Verification-Report.md`, `reviews/T0-Independent-Falsifier-Verdict.md`, `reviews/t0_independent_rerun.py`, `workflows/signomy/out/t0-falsifier-verdict.json`.

2. **T0_GATE — APPROVED.** Accept the frozen 1A–1G source binding and formal successor-transition evidence as of this decision, conditional on T0_ADVERSARIAL having passed. Supporting evidence: `workflows/signomy/out/t0-source-binding.json` and `workflows/signomy/evidence/OWNER-DECISION-PACKET.md`.

3. **P2_PROVISIONAL — APPROVED.** Accept the original high-fidelity FigJam/MagicPath designs as a **provisional planning/visual baseline**, subject to the six tracked delta groups and later visual QA. Supporting evidence: `workflows/signomy/evidence/P2_PROVISIONAL-owner-review.md` and `workflows/signomy/inputs/visual_delta_register.json`.

## Explicit limits

- **P2_FINAL is NOT approved.** Independent architecture-aligned visual QA and owner visual signoff are still outstanding.
- No release, production deployment, protected merge, DNS cutover, data migration, orphan backfill, irreversible data change, financial-custody change, external submission, or new architecture phase is authorized by these three attestations.
- The owner's separately documented 2026-10-10 consent to bounded Phase 3 shell implementation in an isolated branch remains a **distinct authorization**, not a new decision made here.
- Passing gates records owner acceptance of the stated evidence and phase prerequisites; it does not attest untested runtime behavior or authorize unrelated work.
- Preserve the original frozen contracts and all prior controller receipts.

## Recording

The existing Roadmap Engine's `attest` command is to record these specific approvals with this evidence file, in dependency order: `T0_ADVERSARIAL` → `T0_GATE`, and `P2_PROVISIONAL`. No automatic `run` or future-gate attestation is part of this action.
