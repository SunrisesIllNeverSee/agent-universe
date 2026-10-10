# P3 Shell — Independent Falsifier Verdict

Initial: **FAIL** — headline invariant falsified unconditionally.
Post-correction re-verify: **PASS**.

## Broken, then corrected
- P3F-01/02 (critical): X-Frame-Options: DENY + frame-src stripe-only —
  the iframe could never render any hosted page. Builder tests never
  exercised a real frame load. → XFO SAMEORIGIN + frame-src 'self'.
- P3F-03 (high): unvalidated ?route= → arbitrary cross-origin iframe
  injection + API JSON in canvas. → allowlist vs pages registry/MODES.
- P3F-04 (high): raw ?route= reflected unescaped into Inspector innerHTML.
  → textContent-built rows.
- P3F-05/06/07 (medium): stale ctx keys, unmapped-route mode drift,
  in-iframe history drift. → per-nav ctx reset, UNMAPPED mode state,
  reconcile-on-load.

## Verified clean
No writes; noindex; census walk correct; separation semantics preserved;
credentials same-origin only.

## Limitations
Review is static+behavioral; visual QA against original designs is a
separate P2_FINAL surface.
