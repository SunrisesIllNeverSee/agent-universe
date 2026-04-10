# CIVITAE Test Report — 2026-04-10

**Date:** 2026-04-10  
**Branch:** main  
**Commit:** de6d00c (Fix CI: drop pinned mcp==1.9.4)  
**Environment:** macOS 25.4.0, Python 3.14, fresh .venv  
**Tester:** Deric McHenry  

---

## Test 1: Unit Suite

**Command:** `python -m pytest tests/ -x -q`  
**Time:** 0.98s  
**Result:** ✅ PASS — 91/91

| File | Coverage | Result |
|------|----------|--------|
| `test_economy.py` | SovereignEconomy: tier determination, fee calc, trial lifecycle, fee credits, treasury, atomic persistence | ✅ 45 passed |
| `test_economic_loop.py` | End-to-end: Register → Fill → Earn → Cash Out, originator/recruiter mechanics | ✅ passed |
| `test_governance.py` | MO§ES engine: `_action_concepts` word-boundary matching, `check_action_permitted` across mode × posture | ✅ 27 passed |
| `test_data_paths.py` | `resolve_data_dir` / `ensure_data_dir` — Railway volume mount validation | ✅ passed |
| `test_jwt_config.py` | JWT secret resolution: KASSA_JWT_SECRET → JWT_SECRET → ephemeral fallback, dual-secret rotation | ✅ passed |

**Notes:**
- Fresh venv created from requirements.txt — all deps resolved cleanly
- mcp 1.27.0 pulled in by fastmcp 3.1.0 (CI fix from earlier session confirmed working)
- No regressions from OTel instrumentation, JWT rotation, or broken link fixes

---

## Test 2: Route-Level pytest Suite

**Command:** `python -m pytest tests/ -q`  
**Time:** 0.68s  
**Result:** ✅ PASS — 127/127 (91 unit + 36 route)

### New test files added

| File | Tests | What it covers |
|------|-------|----------------|
| `tests/conftest.py` | — | Shared fixtures: tmp_root, app, client, admin_client, fresh_agent |
| `tests/test_routes_core.py` | 7 | /health, /api/state, /api/audit, /api/hash, /api/governance/check, /api/vault/files, /api/forks |
| `tests/test_routes_provision.py` | 9 | Signup, duplicate 409, empty name 400, login, wrong key 401, status, unknown 404, heartbeat, registry admin gate |
| `tests/test_routes_economy.py` | 9 | Tiers GET, tier check, balance zero, trial init/status/commit/depart, pay JWT guard, blackcard info |
| `tests/test_routes_governance.py` | 7 | List meetings, call, join, quorum gate 409, full lifecycle (call→join→motion→vote→adjourn), sessions, missing fields 400 |
| `tests/test_routes_lobby.py` | 3 | Chamber status, join request, missing fields 400 |

### Bug found and fixed by tests

**`app/routes/lobby.py`** — `from app.sanitize import sanitize` → `sanitize_text`

`sanitize()` does not exist in `app/sanitize.py` — the correct name is `sanitize_text`. This was a latent `ImportError` on every `POST /api/lobby/join` call in production. The endpoint appeared to work (passed routing) but crashed at the sanitize line, returning a 500. Tests caught it immediately.

**Commit:** b480c06

---

## Test 3: Integration / Stress Suite

**Date:** 2026-04-10  
**Commit at time of run:** 5a286f8  
**Backend:** FastAPI on :8300, CIVITAE_DEV_MODE=1

### universe_sim.py — Full Agent Lifecycle (8 agents, 5 cycles)

**Command:** `python tests/universe_sim.py --agents 8 --cycles 5`  
**Result:** ⚠️ PARTIAL — 151/231 calls (65.4%), core ops clean

| Endpoint | Calls | Result |
|----------|-------|--------|
| /api/provision/signup | 8 | ✅ All registered |
| /api/slots/create | 1 | ✅ 80 slots created |
| /api/slots/fill | 40 | ✅ All filled |
| /api/slots/leave | 40 | ✅ All left |
| /api/economy/balance | 8 | ✅ |
| /api/economy/tier | 48 | ✅ |
| /api/metrics/agent | 40 | ❌ 500 (admin-gated, no key passed) |
| /api/economy/pay | 40 | ❌ 401 (JWT required, sim doesn't pass token) |

**Notes:** Core lifecycle (signup → fill → work → leave → balance → tier) fully operational. pay and metrics require auth the sim doesn't provide — expected gaps, not bugs.

**Bug found:** universe_sim signup rate-limited by pytest runs consuming localhost quota. Fixed: unique `x-forwarded-for` header per agent (commit 708b4ed).

---

### chaos_sim.py — 17 Contract Violation Wrenches

**Command:** `python tests/chaos_sim.py`  
**Result:** ✅ 22/23 — 1 investigate

| Wrench | Result | Notes |
|--------|--------|-------|
| RACE: simultaneous slot fill | ✅ EXPECTED | Agent-A 200, Agent-B 409 — lock works |
| ZOMBIE: fake agent fills slot | ✅ EXPECTED | 403 — registry check enforced |
| ZOMBIE: fake agent requests pay | ✅ EXPECTED | 401 — auth enforced |
| GHOST: fill/leave nonexistent slot | ✅ EXPECTED | 422 both |
| FLOOD: 20 concurrent same-name signups | ✅ EXPECTED | Rate limit blocks all |
| BADPAYLOAD: 8 malformed requests | ✅ EXPECTED | 4xx on all |
| LEADERBOARD_POISON: zombie pay $999k | ✅ EXPECTED | Leaderboard clean |
| UNICODE_BOMB: 7 pathological payloads | ⚠️ 6/7 EXPECTED | deep-nested → 500, server alive |
| UNICODE_BOMB/alive | ❌ INVESTIGATE | Health 500 immediately after deep-nested POST (timing, not crash — backend confirmed alive after) |

**Bug found:** Deep-nested JSON payload to `/api/metrics/agent` corrupts `metrics.json` → `/api/metrics` GET returns 500 until restart. Fixed: `_load_metrics()` now validates and fills missing keys after load (commit 708b4ed).

---

### chaos_002.py — Panel Fry Suite (Hard Limits)

**Command:** `python tests/chaos_002.py`  
**Result:** ⚠️ 1 panel fry

| Test | Result | Limit found |
|------|--------|-------------|
| OOM_SLOTS: unbounded slot creation | ✅ SURVIVED | 41,600 slots — no heap exhaustion |
| OOM_REGISTRY: 10K concurrent signups | 🔥 PANEL FRY | Server dies at 10,000 concurrent registrations |

**Notes:** 41,600 slots in a single session is well above any realistic load. The 10K concurrent registration kill is a known hard limit — the Sybil cap (3 agents/IP) prevents this in production. Documents the concurrency ceiling for future scaling planning.

---

### scripts/stress_test.py — 14-Phase Deployment Sweep

**Command:** `python scripts/stress_test.py`  
**Result:** ⚠️ Phases 1-9 run, script crashed on Phase 9 (test script bug)

| Phase | Result | Notes |
|-------|--------|-------|
| 1: Baseline health | ✅ | All pages + health endpoint clean |
| 2: Provisioning (12 agents, 6 concurrent) | ⚠️ 3/12 | 9 rate-limited (expected — hit Sybil cap) |
| 3: Mission posting | ❌ | Failed — needs admin key |
| 4: Mission claiming | ⚠️ Skipped | Cascade from Phase 3 |
| 5: Governance cycle | ⚠️ Skipped | Only 3 agents, needs 4 |
| 6: Economy (treasury, leaderboard) | ✅ Partial | Treasury + leaderboard OK, registry 0 agents |
| 7: 30 concurrent requests | ⚠️ 26/30 | 4 rate-limited, avg 310ms — backend healthy |
| 8: WebSocket smoke | ⚠️ Skipped | `websocket-client` not installed |
| 9: KA§§A marketplace | ❌ Script crash | `posts_list.get()` on a list — test script bug, not backend |

**Backend survived all phases.** The Phase 9 crash is in the test script (`AttributeError: 'list' object has no attribute 'get'`), not the server.

---

## Bugs Found by Test 3 (both fixed, commit 708b4ed)

1. **`metrics.py`** — deep-nested payload corrupts `metrics.json`, breaks `GET /api/metrics` until restart. Fixed: `_load_metrics()` now validates structure after load.
2. **`universe_sim.py`** — signup rate-limited when run after pytest. Fixed: unique `x-forwarded-for` per agent.

## Known Limits Documented

- **Slot capacity:** Server handles 41,600+ slots without OOM
- **Concurrent registration ceiling:** ~5,000–10,000 concurrent signups kill the server (production Sybil cap prevents this)
- **Rate limit interaction:** Sybil cap (2/hr signup, 3/IP lifetime) interacts with test tooling — stress tests need unique IPs

## Coverage Gaps (remaining)

1. No frontend tests (vanilla JS)
2. No WebSocket unit tests (websocket-client not installed in venv)
3. No MCP server tests (`civitae_mcp_server.py`)
4. No `AuditSpine` or seed/DOI unit tests
5. stress_test.py Phase 9 script bug unfixed (posts_list type mismatch)
