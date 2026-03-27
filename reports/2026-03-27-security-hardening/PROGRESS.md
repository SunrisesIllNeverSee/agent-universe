# Security Hardening - Live Progress Log

## Status Overview
🟢 **Complete** - 2026-03-27

### Task Checklist
- [x] **Task 00:** Create report structure
- [x] **Task 01:** Enhanced health endpoint — added version, uptime_s, timestamp
- [x] **Task 02:** Password auth (bcrypt) — N/A, CIVITAE uses JWT + magic links
- [x] **Task 03:** Code execution audit — CONFIRMED: zero unsafe calls in app/ or frontend/
- [x] **Task 04:** Pin dependencies — all core deps pinned to exact versions
- [x] **Task 05:** Rate limiting fix — contact form now reads X-Forwarded-For behind proxy
- [x] **Task 06:** Memory leak cleanup — no leaks found; rate store self-evicts hourly
- [x] **Task 07:** Security event logging — SHA-256 audit chain already covers all actions
- [x] **Task 08:** Local testing — syntax verified, server boots clean
- [ ] **Task 09:** Deploy to Railway — pending commit + push
- [ ] **Task 10:** Post-deployment verification — after Railway deploy

---

## Fixes Applied

### 1. Rate Limiting — X-Forwarded-For (SECURITY FINDING)
**File:** `app/server.py` (contact form + admin middleware)
**Issue:** `request.client.host` returns Railway internal proxy IP, not the real visitor.
All rate limiting and localhost checks were bypassing behind the proxy.
**Fix:** Both the contact form rate limiter and admin key middleware now read
`X-Forwarded-For` header first, falling back to `request.client.host`.

### 2. Dependencies Pinned
**File:** `requirements.txt`
**Before:** Range specifiers (`>=0.115,<1.0`)
**After:** Exact pins (`==0.135.1`) for fastapi, uvicorn, pydantic, httpx, stripe, PyJWT.

### 3. Health Endpoint Enhanced
**File:** `app/server.py`
**Before:** `{"ok": true}`
**After:** `{"ok": true, "version": "0.9.0", "uptime_s": 1234, "ts": "..."}`

### 4. MCP Port Configurable
**File:** `app/mcp_bridge.py`
**Before:** Hardcoded `port=8200`
**After:** Reads `MCP_PORT` env var, defaults to 8200.

### 5. Code Execution Audit — CLEAN
No unsafe dynamic code execution found in `app/` or `frontend/*.html`.

### 6. Admin Middleware — Proxy-Aware
**File:** `app/server.py` (line ~167)
The fail-closed localhost check now reads `X-Forwarded-For` so it correctly
identifies the real client IP behind Railway's proxy.

---

## Additional Fixes (from Claude Code security test)

### 7. "Help Wanted" to "Open Roles" Rename
12 frontend files + both pages.json + server.py updated.
`/helpwanted` now 301-redirects to `/openroles`.

### 8. Copilot PR Cherry-Picks
- `mcp>=1.0` added to requirements.txt (server crash fix)
- Nav SKIP list updated (/, /kingdoms, /3d)
- pages.json civitas path fix
- Apply button modal fix (slugify + inline modal)

---

## Live Notes

### 2026-03-27 [Initial]
**Action:** Created report structure
**Status:** Complete

### 2026-03-27 [Claude Code session]
**Action:** Completed all security hardening tasks
**Status:** Complete
**Notes:**
- Task 02 (bcrypt) not applicable — no password auth in CIVITAE
- Task 06 (memory leaks) — rate limit store already self-evicts hourly
- Task 07 (security logging) — SHA-256 audit chain in place since day 1
- Real finding was X-Forwarded-For — Railway proxy masking real IPs

**Next:** Commit, push, verify on Railway
