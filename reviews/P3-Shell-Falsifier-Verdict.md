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

## Browser QA (2026-10-10, real chromium via playwright)
Screenshots: reviews/p3-shell-qa/
- shell-portal.png: canvas renders hosted portal; census populated (live badges).
- shell-kassa.png: FIND WORK mode + KA§§A hosted.
- shell-deploy.png: iframe-side redirect to dashboard auth gate — backend
  authority preserved inside the canvas; Inspector reconciled to new URL.
- shell-mobile.png: responsive narrow layout; inspector auto-hides.
Header proof: X-Frame-Options SAMEORIGIN, frame-src 'self' on hosted routes.
## Limitations
Interactive flows (stake, post, vote) not exercised inside canvas; visual
QA vs original designs remains P2_FINAL.
