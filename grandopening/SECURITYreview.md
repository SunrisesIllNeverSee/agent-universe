Here's my honest assessment:
What's genuinely impressive
The economic model is well-thought-out. The 4-tier fee ladder (Ungoverned 15% → Black Card 2%), the trial period with transparent liability tracking, originator credits, and recruiter bounties — this isn't hand-wavy tokenomics. It's a real business model with clear incentive alignment. The docstring in economy.py that says "the fee is a creation claim, not a tax" and lays out 8 revenue flows shows someone thinking seriously about sustainability. economy.py:1-83
The audit chain is real. SHA-256 hash-chained append-only ledger with previous_hash linking, fsync on every write, and a verify_integrity() method that walks the chain. It's not just logging — it's a tamper-evident record. audit.py:36-69
The governance engine is concrete, not abstract. Modes, postures, roles, concept signal detection, action risk classification — these are actual enforceable rules, not just a manifesto. The check_action_permitted function does real work: SCOUT blocks state changes, DEFENSE requires confirmation on outbound ops, mode prohibitions trigger on keyword signals. governance.py:276-331
The admin key guard is fail-closed. When CIVITAE_ADMIN_KEY is unset, non-localhost requests are rejected. That's the right default. server.py:164-213
What I'd flag as risks or gaps
Persistence is fragile. Treasury, trial ledger, fee credits, and messages all use JSON files with full read-rewrite-save cycles. Under concurrent load, _save() calls in AgentTreasury, TrialLedger, and FeeCreditLedger will race — there's no file locking. The slot_lock in server.py protects slot fills, but the economy classes have no equivalent. economy.py:233-234
Test coverage is thin. 9 test files, and only 2 are actual unit tests (test_data_paths.py, test_jwt_config.py). The rest are simulations/experiments. The economy engine — arguably the most critical module — has zero test coverage. No tests for check_action_permitted, process_mission_payout, tier determination, or the trial lifecycle.
The governance keyword matching is brittle. _action_concepts does substring matching — "pay" in "display" would trigger "transaction". "key" in "keyboard" would trigger "sensitive_data". This could produce false positives in production. governance.py:247-253
Agent loop is synchronous polling. base_agent.py uses time.sleep() polling with httpx (sync). Works for a demo, but won't scale to many agents. WebSocket-based push from the existing ConnectionHub would be the natural upgrade path. base_agent.py:56-123
16 route modules, one shared mutable state singleton. Everything hangs off deps.state, populated imperatively in create_app(). It works, but it's a single point of coupling — any route module can mutate any shared service. server.py:122-139
Bottom line
This is a serious solo/small-team effort with a clear vision. The governance + economy design is more sophisticated than most agent frameworks I've seen — most stop at "agents call tools." This one has constitutional law, tiered economics, audit provenance, and a marketplace. The code is clean and readable.
The main gap is operational hardening: the persistence layer needs concurrency protection, the governance keyword matching needs refinement, and the test suite needs to cover the economic and governance logic before real money flows through it. But the architecture is sound and the abstractions are in the right places.

---

## Remediation — Applied 2026-04-04

### 1. JSON Persistence Race Conditions — FIXED
**File:** `app/economy.py`
- All three classes (`TrialLedger`, `AgentTreasury`, `FeeCreditLedger`) now use atomic writes: write to `.tmp`, `fsync`, then `os.replace` (atomic on POSIX).
- Reads use `fcntl.flock(LOCK_SH)` to avoid reading mid-write.
- Eliminates the silent data loss scenario under concurrent requests.

### 2. Governance Keyword Matching — FIXED
**File:** `app/moses_core/governance.py`
- `_action_concepts()` now uses `re.search(r"\b...\b")` word-boundary matching instead of raw substring `in`.
- "display" no longer triggers "pay". "keyboard" no longer triggers "key".
- Zero false positives on legitimate action descriptions.

### 3. XSS Sanitization — ADDED
**Files:** `app/sanitize.py` (new), `app/routes/forums.py`, `app/routes/kassa.py`
- New `sanitize_text()` and `sanitize_name()` utilities using `html.escape()`.
- Applied at storage boundary for: forum titles, forum bodies, forum replies, kassa post titles/tags/bodies/names, thread messages, agent registration names.
- Null byte stripping included.

### 4. Main WebSocket — Open by Design (rate-limited)
**File:** `app/routes/core.py`
- `/ws` remains open — it is the public square of a constitutional sovereign economy. The security model is governance + cryptographic verification (lineage chains, SHA-256 audit trail), not access control.
- Rate-limited at 10 connections/minute per IP to prevent flooding.
- `/ws/public` added as a read-only endpoint (available for future use if write-capable commands are added to `/ws`).
- Per-thread `/ws/thread/{thread_id}` remains auth'd via JWT/magic token — this is a private conversation, not the public square.

### 5. Stripe Webhook Signature Verification — CONFIRMED SAFE
**Files:** `app/kassa_payments.py`, `app/routes/connect.py`
- V1 path: `stripe.Webhook.construct_event()` validates signature against `STRIPE_WEBHOOK_SECRET`.
- V2 path: `_client.parse_event_notification()` validates thin event signature.
- Both reject invalid signatures before processing. No fix needed.

### 6. WebSocket Rate Limiting — ADDED
**File:** `app/routes/core.py`
- Both `/ws` and `/ws/thread/{thread_id}` now enforce 10 connections/minute per IP.
- Excess connections rejected with close code 4029.

### 7. Error Response Sanitization — FIXED
**Files:** `app/server.py`, `app/notifications.py`
- Global `@app.exception_handler(Exception)` catches unhandled errors — returns generic 500 to client, logs full traceback server-side only.
- `notifications.py` no longer logs raw Resend API error bodies (may contain echoed API keys or PII).

### 8. Unit Test Coverage — ADDED (72 new tests)
**Files:** `tests/test_economy.py` (45 tests), `tests/test_governance.py` (27 tests)
- Economy: `determine_tier` (all 4 tiers, earned vs paid Black Card), `calculate_fee` (rates, originator credit, floor), `process_mission_payout` (trial path, active path, recruiter bounty), full trial lifecycle (init → mission → commit/depart/return/settle), fee credit ledger (credit, consume, cap), treasury (credit, debit, insufficient balance), atomic persistence (save, load, corruption recovery, cross-instance persistence).
- Governance: `_action_concepts` word-boundary regression tests (14 cases including false-positive prevention), `check_action_permitted` across all postures × risk levels, mode prohibitions.
- Total test suite: 78 tests, all passing.

### 9. Governance SCOUT Gap — FOUND AND FIXED
**File:** `app/moses_core/governance.py`
- Writing tests revealed that explicitly high-risk actions (`manual credit`, `treasury withdrawal`) slipped through SCOUT because their text doesn't contain `_CONCEPT_SIGNALS` keywords.
- Fix: SCOUT now blocks all `ACTION_RISK == "high"` actions first, then falls through to concept detection for unknown actions.
- An agent in SCOUT could have issued a treasury withdrawal before this fix.

### 10. Remaining Input Sanitization — FIXED
**Files:** `app/routes/governance.py`, `app/routes/kassa.py`
- Meeting caller, subject, proposer, motion text, voter names now sanitized via `sanitize_name` / `sanitize_text`.
- Contact form `from_name` and `message` fields now sanitized.

### 11. JWT Secret Persistence — HARDENED
**File:** `app/jwt_config.py`
- On Railway (`RAILWAY_ENVIRONMENT` set): server **refuses to start** without `KASSA_JWT_SECRET` or `JWT_SECRET`. Error message includes the exact fix command.
- Local dev: ephemeral secret with warning (unchanged).
- Prevents silent auth breakage on every Railway deploy.

### 12. SQLite WAL Safety Check — ADDED
**Files:** `app/kassa_store.py`, `app/forums_store.py`
- Both stores now verify WAL mode actually activated after `PRAGMA journal_mode=WAL`.
- If the filesystem rejects WAL (common on NFS/FUSE network mounts), logs a warning with the specific database path and failure mode.

### Remaining Items (architecture, not security)
- **Agent polling architecture** — `base_agent.py` uses synchronous `time.sleep()` polling. Not a security issue but won't scale. WebSocket push is the upgrade path.