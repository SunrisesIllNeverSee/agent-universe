# SIGNOMY BUILD STATUS — Phase 3 long-run checkpoint

As of: 2026-10-10 · Branch: `feat/signomy-p3-shell` · Base: `main` (incl. T0 corrections)

## Committed (isolated branch)

- `5efcec5`+rebase — `/shell` route + `frontend/shell.html` + 6 shell tests +
  conftest copy. Host-first: same-origin iframe hosts unchanged 0.4.0 routes;
  9-mode rail; context sidebar; read-only Inspector; `/api/state` HUD.
  Deep link `/shell?route=/kassa`. Suite 527/527 on branch.

## Committed (main, separate lane)

- T0 independent-falsifier corrections: advisory seats PII stripped from
  public projection; applicant name removed from public audit;
  `require_admin` on `/api/provision/key` + `/api/inbox/{id}/review`.
  Independent probe `reviews/t0_independent_rerun.py` → GREEN. 521/521.

## Controller state (23 tasks, schema v2)

PASSED: T0_BIND, H5_RECORD, VOTE_RECORD, T0_FALSIFIER_RERUN, P2_INVENTORY,
P2_DELTA, P3_SHELL_PREP, H2_ORPHAN_AUDIT, H5_CLOSE_RECORD, H3_OTEL_RECORD.
BLOCKED (owner): T0_ADVERSARIAL, P2_PROVISIONAL.
PENDING behind gates: T0_GATE, P2_FINAL, P3_AUTHORIZE → P3_SHELL_IMPL,
P3_SHELL_VERIFIED, P4..P8, R_LIVE.

## Honest blockers

- `P3_AUTHORIZE` structurally waits on T0_GATE + P2_PROVISIONAL + P3_SHELL_PREP
  attestations — the directive's owner authorization is real but downstream
  attestation prerequisites remain owner-side. Shell build proceeded on the
  isolated branch per the explicit authorization; the controller task will
  receipt once the gate chain is attested.
- H2 orphan backfill, atomic Seeds, WorkEntry, Refinery/Switchboard, escrow,
  enterprise nodes: NOT authorized — deferred.

## Falsifier status

- T0: independent rerun complete — real leak found (advisory seats) + fixed.
  Fresh verdict: PASS post-correction (reviews/T0-Independent-Falsifier-Verdict.md).
- Shell: falsifier FAIL → bounded corrections → re-verify PASS
  (reviews/P3-Shell-*): XFO/frame-src frameability, route allowlist,
  Inspector XSS sink, stale ctx, unmapped modes, history drift.
- Receipt integrity: T0_FALSIFIER_RERUN receipt invalidated (probe_exit=1
  recorded on PASS — system-python subprocess); producer now fails closed
  + venv interpreter; engine `invalidate` command added; receipt re-issued
  probe_exit=0/green. 3 regression tests.
- Browser QA (playwright): screenshots in reviews/p3-shell-qa/ — canvas
  rendering verified, auth-gate redirect preserved, responsive layout.
- api_key transport: X-Agent-Key header added (provision status);
  query-string path no longer used by shell.
- Audit backfill: local audit.jsonl has no advisory entries; production
  store unverifiable from here — REPORTED, no migration performed.
