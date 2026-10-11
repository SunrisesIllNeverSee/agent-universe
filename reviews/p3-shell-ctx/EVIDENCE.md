# P3 shell: context derivation + authority falsifier (branch claude/p3-shell-ctx)

## Task A: object-context derivation
**Result: no change to frontend/shell.html.** Extending deriveContext() for /deploy and /slots would require URL params those pages do not use.

REPO-VERIFIED:
- frontend/slots.html: no URLSearchParams / location.search / location.hash. `location` appears only at :278 (`API = window.location.origin`) and :620 (hostname check). Slot identity is in-memory (`slots[]`, `slotCounter`, ids `'slot-'+n`, :279-322); badge ids are static lists (:286-300).
- frontend/deploy.html: only `window.location.origin` (:302). Grid state is in-memory `placed` (:304); formations load from /config/formations.json (:508); missions are created via POST /api/missions (:590) with server-generated ids, never reflected in the URL.
- Shared scripts (_nav.js :34,:138; _footer.js :24; ai-beacon.js :8; _auth.js :53-60) read only location.pathname, plus search for a login `?next=` redirect.
- Consequence: the existing `?slot=`/`?id=` read for /deploy and /slots (shell.html ~line 245) matches no hosted-page emission today. It is kept (harmless, cleared every navigation) and pinned by tests. Adding Inspector rows would invent objects.
- Related shapes seen: kassa-thread.html:337 uses URLSearchParams (not inspected further; out of scope, INFERRED to be a candidate for a later key). mission.html uses only `#team` view hash (:574-576); no id param.

Tests added to tests/test_p3_shell.py (5, static-HTML style like the existing ones): hosted deploy/slots expose no URL params (tripwire), keys cleared at top and in catch and every set key is cleared, PHASE-4 rows stay placeholders and deriveContext never touches them, Inspector uses textContent only, known param shapes pinned.
LIMITATION: static assertions only, no browser/JS execution (no behavioral DOM test; no JS runtime harness in repo).

## Task B: authority falsifier
Probes: live uvicorn on :8941 (`CIVITAE_ADMIN_KEY=dev-admin`, no admin key sent in any probe; killed afterwards) and TestClient. Conditions: A=anonymous, B=anon + Referer/Origin `http://localhost:8941/shell?route=/kassa`, C=forged Authorization/X-Agent-Key/X-Admin-Key, D=B+C. All REPO-VERIFIED (live), identical in TestClient.

| Endpoint (route file) | A | B | C | D |
|---|---|---|---|---|
| POST /api/kassa/posts/{id}/stake (kassa.py:291) | 401 | 401 | 401 | 401 |
| DELETE /api/kassa/stakes/{id} (kassa.py:443) | 401 | 401 | 401 | 401 |
| POST /api/kassa/posts (kassa.py:896) | 401 | 401 | 401 | 401 |
| POST /api/kassa/posts/{id}/upvote (kassa.py:989) | 404* | 404* | 404* | 404* |
| POST /api/kassa/threads/{id}/messages (kassa.py:683) | 404* | 404* | 404* | 404* |
| POST /api/kassa/threads/{id}/close (kassa.py:648) | 404* | 404* | 404* | 404* |
| POST /api/slots/fill, /leave (missions.py:833,927) | 401 | 401 | 401 | 401 |
| POST /api/slots/create, /bounty (missions.py:750,982) | 403 | 403 | 403 | 403 |
| POST /api/missions, /{id}/end, /{id}/update (missions.py:243,313,368) | 403 | 403 | 403 | 403 |
| POST /api/governance/meeting/{id}/vote (governance.py:282) | 403 | 403 | 403 | 403 |
| POST /api/economy/withdraw (economy.py:435) | 403 | 403 | 403 | 403 |
| POST /api/forums/threads (forums.py:91) | 401 | 401 | 401 | 401 |
| POST /api/availability/{agent_id} (availability.py:60) | 200 | 200 | 200 | 200 (TestClient only; not probed live to avoid a write) |

*404 (original probe) comes from resource lookup before the claim check, so these three prove uniformity but not the rejection path (no real post/thread was created).

Conclusion: no shell-origin bypass. Referer/Origin never changed any status. The server has no code keyed on the shell origin (INFERRED from uniform results; CORS allow-list is only :8300 origins, server.py ~270).

### DEFECT (pre-existing, NOT shell-induced)
POST /api/availability/{agent_id} (+ /toggle, availability.py:60,:101): `/api/availability/` is in `_PUBLIC_WRITE_PREFIXES` (server.py ~310) and the handlers perform no agent-claim check. Anonymous (and forged-credential) callers get 200 and overwrite any agent's availability record. Expected 401/403. Recorded as strict xfail `test_availability_write_requires_authority`. Backend not modified. /toggle not separately tested.

Tests: tests/test_p3_shell_authority.py = 33 passed + 1 xfailed (16 endpoints x 2 + aggregate + xfail).

## Counts
Baseline 530. After: 568 passed + 1 xfailed. New: 5 (shell ctx) + 33 + 1 xfail.

## Limitations
- No browser execution; iframe-in-shell behaviour (cookies/localStorage tokens sent by hosted pages) not tested. Shell grants no credentials itself (it only reads tokens for the principal display), but that is static analysis.
- Authenticated-success paths not tested (needs minted agents); only rejection parity.
- Roadmap controller state untouched.

## Update: pre-mutation denial against EXISTING entities (tests/test_p3_shell_authority_fixtures.py)
Fixtures are seeded into the conftest tmp data dir (asserted `civitae_root` in path; never real data/): agents A and B via
/api/provision/signup, a post, stake, two open threads, mission, slots (one filled by A), a meeting with a pending motion.
Per endpoint: anonymous / forged / shell-origin / shell+forged -> 401|403 AND a snapshot of slots/missions/meetings json,
kassa posts/stakes/thread/messages, forum thread count and treasury ledger is unchanged. Wrong-principal (agent B) denial
for the 6 identity-bound verbs. Authorized success: owner JWT (stake, message, close, withdraw stake, post, forum thread),
owner api_key (leave, fill, vote, bounty), admin (mission update/end).
Result: 28 tests passed in that file; full suite 596 passed + 1 strict xfail.
- True pre-mutation denial on existing entities: all 15 cases (14 consequential + withdraw) except as noted.
- Withdraw: denial-only (admin path reaches the chain router / money movement; not exercised with credentials).
- Upvote: the 404-era probe was misleading. With a real post, anonymous/forged/shell calls ALL return 200: upvote is public
  by design (rate limit only). Removed from the "auth-protected" claim; covered by test_upvote_is_public_by_design_and_shell_neutral.
- Route -> guard file:line: ROUTE-GUARD-MAP.md.

### Falsifier RED -> GREEN (not committed to app/)
Guard removed in-process via monkeypatch of the denial suite:
- `require_agent_claim` stubbed in missions+governance and kassa `_get_agent_from_token` stubbed: 6 RED
  (stake, slot_fill, slot_leave anon; wrong-principal slot_leave, slot_bounty, vote). Anonymous vote stays GREEN
  because middleware still blocks it (defence in depth, correct).
- `server.admin_key_matches` stubbed True: 5 RED (slot_create, mission_create/end/update, withdraw).
- Committed canaries (test_canary_*) assert the probe observes breach when each guard is patched away and not when intact.
Restored: 28/28 GREEN, full suite 596 passed + 1 xfailed.

### Browser evidence (Playwright via MCP; python playwright not installed)
Local server on :8957 (CIVITAE_ADMIN_KEY set, throwaway tmp root + data dir, killed afterwards).
screenshots/01-guest-kassa.png, 04-authed-kassa.png, 02-after-nav.png, 03-after-back.png.
- Guest: shell principal "guest / no credential in this browser"; iframe localStorage has no kassa_jwt/civitas_auth; an
  anonymous fetch from inside the iframe to /api/kassa/posts/x/stake -> 401.
- With kassa_jwt placed in same-origin localStorage: shell shows "bshot-agent agent-... active"; iframe sees the same token
  (shared origin storage, not shell-granted); /api/kassa/agent/me -> 200. Credential came from the user, shell added none.
- History: clicking DEPLOY as a guest loaded /dashboard?next=%2Fdeploy (frontend login redirect); history grew by 3 entries
  (nav push, iframe-reconcile push, plus iframe's own entry) and one browser Back left the shell URL unchanged (joint
  session history pops the iframe entry first). INFERRED cosmetic quirk, not authority-related; not further characterised.
  LIMITATION: the shared Playwright browser was concurrently driven/closed by other sessions (first attempt hit a closed
  context), so history coverage is one run, not a matrix.

### Open gaps
- availability write xfail unchanged (other branch).
- Any active agent api_key can end/update any mission and create slots (no ownership check); see ROUTE-GUARD-MAP.md.
- Layer-1-only protection on missions/slots/withdraw: no handler-level check behind the middleware.
- P3_SHELL_VERIFIED not claimed; remains a manual gate.
