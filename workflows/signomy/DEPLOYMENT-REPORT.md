# Roadmap Engine v0.2 — Deployment Report

Date: 2026-10-09 · Installer lane: DREP2 · Commit: `cf8ac1c`

## Install location

`1_agent-universe` repo root:

- `roadmap_engine/` — vendored controller (stdlib-only, Python ≥3.10)
- `workflows/signomy/` — SIGNOMY workflow: `roadmap.json` (18 tasks),
  `settings.json`, `steps/signomy.py`, `inputs/` (established status,
  visual delta register, shell brief), `evidence/`
- `tests/roadmap_engine/` — 12 engine tests, run under the repo suite
- `workflows/signomy/.gitignore` keeps `.roadmap/` receipts, `out/`,
  `tracking/` local — receipts exist on disk; contracts are tracked.

Commands run from repo root:
`python3 -m roadmap_engine --project workflows/signomy {validate,refresh,run,status,verify,blockers}`

## Validation results

- Engine self-tests: **12/12 PASS** (`python3 -m unittest discover -s tests`,
  or `pytest tests/roadmap_engine/` in-repo)
- `validate`: VALID schema/DAG — 18 tasks, dependencies enforced
- `refresh`: completed — writes `tracking/OBSERVED_STATUS.{json,md}`,
  does not mutate pass/approval state
- `verify`: PASS — all recorded completions have consistent contracts,
  dependency receipts and output hashes
- Repo suite: **490/490** (478 + 12 engine tests)

## Gate / task states after first run

PASSED (receipts in `.roadmap/receipts/`, artifacts in `out/`):

| Task | Artifact |
|---|---|
| T0_BIND | `out/t0-source-binding.json` — frozen 1A–1G SHA256 snapshot |
| H5_RECORD | `out/h5-evidence.json` |
| VOTE_RECORD | `out/vote-evidence.json` |
| P2_INVENTORY | `out/p2-original-asset-inventory.json` |
| P2_DELTA | `out/p2-visual-deltas.json` |
| P3_SHELL_PREP | `out/p3-shell-preparation.json` — bounded host-first shell work order |

BLOCKED (owner-attestation gates, correctly held): `T0_ADVERSARIAL`,
`P2_PROVISIONAL`.

PENDING (dependency-gated): `T0_GATE`, `P2_FINAL`, `P3_AUTHORIZE`,
`P3_SHELL_VERIFIED`, `P4_WORKENTRY_VERIFIED`, `P5_HARDENING_VERIFIED`,
`P6_DERIVED_VERIFIED`, `P7_IA_VERIFIED`, `P8_RELEASE_EVIDENCE`, `R_LIVE`.

## Positive/negative verification

- Successful task → receipt with contract + output SHA-256 ✔
- `verify` → PASS on live workflow ✔
- Scratch-project proof: failed task HELD, dependent never ran; re-run
  executed 0 tasks (resume-safe, no duplicate execution) ✔
- `refresh` updates observation only; no task promoted without evidence ✔
- Owner gates not attested by installer — `T0_ADVERSARIAL` and
  `P2_PROVISIONAL` await `attest --evidence` from the owner ✔

## Remaining blockers

Owner gates (real authorization, not simulated): `T0_ADVERSARIAL`,
`P2_PROVISIONAL`; then `P3_AUTHORIZE` before any Phase 3 code.

## Next eligible task

None automatic — both open heads are owner attestations. After
attestation, `run` picks up newly-eligible successors.

## Missing automation hooks (not claimed)

No git-event sync, no background watcher, no Devin/agent orchestrator
launch — `refresh` is explicit-invocation only.
