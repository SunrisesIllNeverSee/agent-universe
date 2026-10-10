# OWNER DECISION PACKET — Transition Gates (consolidated)

Generated: 2026-10-10 · Repo: `1_agent-universe @ main` · Controller: Roadmap Engine v0.3

Three related owner gates are open. This packet consolidates their evidence and the
exact decisions requested. Nothing here self-attests; each gate awaits your attestation
via `python3 -m roadmap_engine --project workflows/signomy attest <TASK> --evidence <file>`.

---

## Gate 1 — `T0_ADVERSARIAL` (BLOCKED, ready for review)

**Ask:** Accept the independent adversarial-verification evidence as satisfying the T0 red/green gate.

**Evidence prepared:**
- `reviews/T0-Adversarial-Verification-Report.md` — full report (hashes, commands, verdict)
- `reviews/T0-RedGreen-Transcript.md` — machine-checkable transcript
- `reviews/T0-Findings.csv` — findings ledger
- `reviews/t0_redgreen_probe.py` — the reusable probe
- `.devin/skills/adversarial-verification/SKILL.md` — canonical skill, byte-identical to frozen package

**What was proven:** the H5 inbox/contact-PII guard invariant went RED when the
guard was deliberately broken **inside a disposable worktree**, returned GREEN on
the real tree, and the real tree was provably unmutated.

**Reviewer independence — RESOLVED 2026-10-10:** a separate falsifier agent
re-traced every route→guard chain, invented six new probes the original missed,
and found a REAL leak (`GET /api/advisory/seats` returning applicant PII
anonymously — dynamically confirmed RED). Bounded corrections applied
(applicant stripped from public projection, name removed from public audit,
route-level `require_admin` on two middleware-only writes). Independent probe
now GREEN; verdict `reviews/T0-Independent-Falsifier-Verdict.md`; machine
evidence `reviews/t0_independent_rerun.py`. The falsifier caught a defect the
builder's probe missed — this is the strongest form of the gate's intent.

## Gate 2 — `T0_GATE` (PENDING, needs T0_ADVERSARIAL first)

**Ask:** Approve the formal successor-transition gate: frozen 1A–1G source
hashes + binding to runtime repo + adversarial proof, all current.

**Evidence prepared:** `out/t0-source-binding.json` (frozen-contract SHA256
snapshot + runtime pointer/ancestor checks, produced by `T0_BIND`, receipted).
Dependency: T0_ADVERSARIAL must pass first.

## Gate 3 — `P2_PROVISIONAL` (BLOCKED, ready for review)

**Ask:** Accept the original FigJam/MagicPath designs as the *provisional*
Phase 2 baseline — planning authority only.

**Evidence prepared:** `workflows/signomy/evidence/P2_PROVISIONAL-owner-review.md`
— original inventory + archive hashes (MANIFEST-SHA256, VERIFICATION.json), the
six outstanding delta groups, explicit limitations.

**What acceptance does NOT mean:** no production implementation authority,
no `P2_FINAL` (independent architecture-aligned visual QA remains open),
no architecture rewrite.

---

## Downstream effects of your decisions

- Attest `T0_ADVERSARIAL` → `T0_GATE` becomes eligible for attestation.
- Attest `P2_PROVISIONAL` → `P2_FINAL` prep unblocks; `P3_AUTHORIZE` remains a
  separate later decision (host-first shell implementation authority).
- Holding any gate does NOT block the H-lane hardening work packages
  (H2 audit, H5 close record, H3 otel record already receipted on engine v0.3).
