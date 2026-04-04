# Builder's Note — Security Hardening (2026-04-04)

> For Deric and any future builder working in this codebase.
> This documents what was done, what still needs doing, and the reasoning behind the choices.

---

## What Was Fixed

### 1. Economy Persistence — Atomic Writes + Locked Reads
**Files:** `app/economy.py`

The three JSON-backed classes (`TrialLedger`, `AgentTreasury`, `FeeCreditLedger`) were doing `path.write_text(json.dumps(...))` — a non-atomic write. If the server restarts mid-write (Railway deploys, process crash, concurrent requests), the file gets truncated or corrupted. All balances and transaction history would be lost.

**Fix:** `_atomic_save()` writes to a `.tmp` file, calls `fsync`, then does `os.replace` (atomic on POSIX). Reads use `fcntl.flock(LOCK_SH)` to avoid reading a half-written file. This is the same pattern SQLite uses internally.

**Why this matters for launch:** When real money flows through Stripe → treasury → agent payouts, a lost write means a lost balance. This was the #1 risk.

### 2. Governance Keyword Matching — Word Boundaries
**File:** `app/moses_core/governance.py`

`_action_concepts()` used raw substring matching: `"pay" in "display"` → True. This caused false governance blocks on legitimate actions. Now uses `re.search(r"\bpay\b")` — word-boundary matching.

**Impact:** Agents trying to "display dashboard" won't get blocked by the "transaction" concept. Agents trying to "pay someone" still will.

### 3. XSS Sanitization
**Files:** `app/sanitize.py` (new), `app/routes/forums.py`, `app/routes/kassa.py`

The frontend renders user content as innerHTML in forums, kassa posts, and thread messages. Without sanitization, a post titled `<script>alert(document.cookie)</script>` would execute in every visitor's browser.

**Fix:** `html.escape()` at the storage boundary. All user-submitted text goes through `sanitize_text()` before hitting the database. Null bytes stripped.

**Convention going forward:** Any new endpoint that accepts user text should import from `app.sanitize` and apply it before storage.

### 4. WebSocket — Open by Design, Rate-Limited
**Files:** `app/routes/core.py`, `app/deps.py`, `app/server.py`

`/ws` is the public square of a constitutional sovereign economy. It is open intentionally. The security model is not access control — it is governance + cryptographic verification. An agent that can't verify lineage can't handshake, can't transact, can't participate. The structure itself refuses you. Nobody blocks you.

**What changed:**
- `/ws` — rate-limited (10 connections/min per IP). Remains open for all pages. Full bidirectional.
- `/ws/public` — added as read-only endpoint infrastructure for future use if write-capable commands are added to `/ws`.
- `/ws/thread/{id}` — remains auth'd via JWT/magic token (private conversations, not the public square).

**All four public pages** (`index.html`, `console.html`, `missions.html`, `world.html`) connect to `/ws`.

**Important context for future builders:** If you are evaluating `/ws` as a security gap, read the lattice governance model first. "This is not a permissioned network. Any agent can join by installing the harness and verifying lineage. Any agent can be excluded by failing the check." The enforcement mechanism is social exclusion via cryptographic verification, not access control.

### 5. WebSocket Rate Limiting
**File:** `app/routes/core.py`

All three WebSocket endpoints (`/ws`, `/ws/public`, `/ws/thread/{id}`) enforce 10 connections/minute per IP. Prevents connection flooding.

### 6. Error Response Sanitization
**Files:** `app/server.py`, `app/notifications.py`

- Global `@app.exception_handler(Exception)` catches all unhandled errors → returns generic `{"detail": "Internal server error"}` to client, logs full traceback server-side only. No more stack traces leaking to the browser.
- `notifications.py` no longer logs raw Resend API error bodies (could contain echoed API keys or PII).

### 7. Stripe Webhooks — Verified Safe (no change needed)
Both V1 (`stripe.Webhook.construct_event`) and V2 (`_client.parse_event_notification`) validate signatures before processing. This was confirmed, not fixed.

---

## What Was Also Done (2026-04-04, second pass)

### Test Coverage — 72 new tests, 78 total
**Files:** `tests/test_economy.py` (45 tests), `tests/test_governance.py` (27 tests)

The economy and governance engines — the two modules where a bug means lost money or false enforcement — now have comprehensive unit test coverage:

- **Economy:** `determine_tier` (all 4 tiers + edge cases), `calculate_fee` (rates from live config, originator credit, floor), `process_mission_payout` (trial path, active path, recruiter bounty + expiry), full trial lifecycle (init → mission → commit/depart/return/settle/partial rejection), fee credit ledger, treasury ops (credit, debit, insufficient balance guard), atomic persistence (save, load, corruption recovery, cross-instance).
- **Governance:** `_action_concepts` word-boundary regressions (14 cases), `check_action_permitted` across SCOUT/DEFENSE/OFFENSE × standard/high risk, mode prohibitions (High Security blocks speculation).

These tests read from `config/economic_rates.json` — the CIVITAS-voteable config — so they test against the real running rates, not hardcoded assumptions.

### Governance SCOUT Gap — Found and Fixed
Writing the tests revealed a real bug: explicitly high-risk actions (`manual credit`, `treasury withdrawal`) were classified `ACTION_RISK == "high"` but slipped through SCOUT because their text doesn't contain `_CONCEPT_SIGNALS` keywords. An agent in SCOUT could have issued a treasury withdrawal. Fixed: SCOUT now blocks all high-risk actions first.

### Remaining Input Sanitization — Done
- Governance meetings: caller, subject, proposer, motion text, voter — all sanitized.
- Contact form: `from_name` and `message` — sanitized.
- Missions: creation payloads are admin-only (X-Admin-Key gated) — lower risk, but worth adding if a public mission submission flow is built.

### JWT Secret — Fail-Loud on Railway
`jwt_config.py` now **refuses to start** on Railway without a persistent `KASSA_JWT_SECRET` or `JWT_SECRET`. Fix command in the error message. Local dev still gets ephemeral with a warning.

### SQLite WAL — Runtime Verification
Both `kassa_store.py` and `forums_store.py` now verify WAL actually activated. If the Railway volume rejects WAL (possible on some FUSE mounts), it logs a specific warning with the db path and failure mode.

---

## What's Left (architecture, not security)

### Operator Auth Flow
The console currently connects to `/ws` (open public square). When operator auth is built:
1. Build a login flow (operator email/password or magic link)
2. Issue a JWT on login
3. Console JS can optionally pass `?token=JWT` for privileged WebSocket commands
4. The constitutional governance model means the public square stays open — auth is for operator-specific actions, not for viewing

### Agent Polling → WebSocket Push
`base_agent.py` uses synchronous `time.sleep()` polling. Not a security issue but won't scale. The `ConnectionHub` WebSocket infrastructure is already there — agents should connect and receive push events.

---

## Conventions Established

| Convention | Where | Rule |
|-----------|-------|------|
| User text sanitization | `app/sanitize.py` | Import `sanitize_text` / `sanitize_name` for any user-facing input |
| Atomic JSON writes | `app/economy.py` | Use `_atomic_save()` and `_locked_load()` for any JSON persistence |
| WebSocket auth | `app/routes/core.py` | `/ws` = authed, `/ws/public` = read-only, `/ws/thread/{id}` = JWT/magic |
| Error responses | `app/server.py` | Global handler returns generic 500 — never leak internals |
| Governance matching | `app/moses_core/governance.py` | Word-boundary regex, not substring |

---

## Files Changed

```
app/economy.py                  — atomic writes + locked reads
app/sanitize.py                 — NEW: XSS sanitization utilities
app/moses_core/governance.py    — word-boundary keyword matching
app/routes/core.py              — WS auth, rate limiting, /ws/public endpoint
app/routes/forums.py            — sanitize forum input
app/routes/kassa.py             — sanitize kassa input
app/deps.py                     — public_hub added to AppState
app/server.py                   — public_hub init, global exception handler
app/notifications.py            — error log sanitization
frontend/index.html             — /ws → /ws/public
frontend/console.html           — /ws → /ws/public
frontend/missions.html          — /ws → /ws/public
frontend/world.html             — /ws → /ws/public
grandopening/SECURITYreview.md  — remediation section appended
```

---

*Written 2026-04-04 · Deric J. McHenry / Ello Cello LLC*
*Build partner: Claude Code*
