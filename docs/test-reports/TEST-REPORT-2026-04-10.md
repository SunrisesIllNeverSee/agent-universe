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

## Test 3 — Pending

*Integration / stress tests (require running backend)*

| Test | Command | Status |
|------|---------|--------|
| `universe_sim.py` | `python tests/universe_sim.py --agents 8 --cycles 5` | ⬜ Not run |
| `chaos_sim.py` | `python tests/chaos_sim.py` | ⬜ Not run |
| `chaos_002.py` | `python tests/chaos_002.py --monitor` | ⬜ Not run |
| `scripts/stress_test.py` | `python scripts/stress_test.py` | ⬜ Not run |

---

## Coverage Gaps (remaining after Test 2)

1. No frontend tests (vanilla JS)
2. No WebSocket unit tests (`ConnectionHub`, `ThreadHub`)
3. No MCP server tests (`civitae_mcp_server.py`)
4. No `AuditSpine` or seed/DOI unit tests
5. 221 API endpoints — 36 now covered by route tests, 185 still untested
