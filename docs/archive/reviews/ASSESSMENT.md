---
type: Reference
title: ASSESSMENT.md — Agent Universe / CIVITAE Repo Health Report
description: ASSESSMENT.md — Agent Universe / CIVITAE Repo Health Report — archived documentation in docs/.
tags: [documentation, archive, docs]
timestamp: 2026-08-19
---

# ASSESSMENT.md — Agent Universe / CIVITAE Repo Health Report

**Date:** 2026-07-06
**Assessor:** Devin (GLM-5.2 High), assessment pass
**Repo:** SunrisesIllNeverSee/agent-universe (branch: `main`, last commit `222a24a`)
**Last active session:** ~2026-05-05 (per `SESSION_RESUME.md`)
**Scope:** Assessment only — no fixes applied beyond trivial boot-blockers (none were needed; the app boots clean).

---

## 1. BOOT & DEPENDENCIES

### 1.1 Dependency Installation

**`requirements.txt` has been deleted** (commit `17bbd11`, message: "Glama auto-infers pip but sandbox only has uv"). Dependencies now live in `pyproject.toml` under `[project].dependencies`. There is **no `requirements.txt` at the repo root** — only `adapters/requirements.txt` (a separate, optional adapter dep set).

A fresh venv was created with Python 3.11.15 (the CI target of 3.13 was **not available** on this machine — only 3.11 and 3.14 are installed; see Finding F-1). Installing the pinned deps from `pyproject.toml` directly via `pip install <pkgs>` succeeded cleanly with **zero resolution failures, zero yanked packages, zero deprecation warnings**.

> Note: `pip install -e .` **fails** because `pyproject.toml` sets `packages = []` in `[tool.hatch.build.targets.wheel]` (line 33). This is intentional — the repo is a runtime application, not an installable package; the `civitae-mcp` PyPI package is the distributable artifact. But it means the only install paths are (a) `pip install -r requirements.txt` (file deleted) or (b) manually installing the dep list. **This is the single most important finding — see F-2.**

Installed versions (all resolved to the pinned specs):
- fastapi 0.136.1, starlette 1.0.0, uvicorn 0.46.0, pydantic 2.13.4, pydantic-core 2.46.4
- pytest 8.3.5, PyJWT 2.12.1, httpx 0.28.1, websockets 16.0, stripe 15.1.0
- opentelemetry-api/sdk 1.41.1, opentelemetry-instrumentation-fastapi/asgi 0.62b1
- fastmcp 3.4.0 (resolved down from 3.4.3 due to `mcp<2.0,>=1.24.0` constraint), civitae-mcp 0.2.0

### 1.2 Local Boot

Command: `export CIVITAE_DEV_MODE=1 && python run.py` (port 8300)

**Startup output (exact):**
```
KASSA_JWT_SECRET and JWT_SECRET not set -- using one ephemeral key for this process. All JWTs will expire on restart. Set one of these env vars in production.
WARNING: STRIPE_SECRET_KEY not set. Payment endpoints will return 503.
  Set it in your environment: export STRIPE_SECRET_KEY=sk_test_...
  Get your key at: https://dashboard.stripe.com/apikeys
```

**No import errors. No tracebacks.** Only the two expected benign warnings (ephemeral JWT key per `app/jwt_config.py:27-31`, missing Stripe key per `app/kassa_payments.py:77-82`). Uvicorn came up on 127.0.0.1:8300 and served traffic.

### 1.3 Smoke Endpoints

All endpoints from `.agents/skills/testing-local-server/SKILL.md`:

| Endpoint | Method | Expected | Result | Notes |
|----------|--------|----------|--------|-------|
| `/health` | GET | `{"ok":true,...}` 200 | **PASS** | `{"ok":true,"version":"0.9.0","uptime_s":50,...}` |
| `/api/state` | GET | JSON with mode/posture/role 200 | **PASS** | Full governance snapshot returned |
| `/` | GET | HTML 200 + security headers | **PASS** | All 5 security headers present (see below) |
| `/kassa` (no cookie) | GET | 307 → `/lobby` | **PASS** | 307 redirect to `/lobby` (Velvet Rope gate, `app/server.py:296-318`) |
| `/mcp` | POST | MCP JSON-RPC response | **PASS** | 200, `event: message` SSE with `initialize` result, 19 tools, serverInfo `command-runtime` v1.28.1 |
| `ws://127.0.0.1:8300/ws` | WS | 101 upgrade, stays connected | **PASS** | 101 upgrade succeeded, connection held. (Sending plain-text "hello" triggered a server-side `JSONDecodeError` because the endpoint calls `receive_json()` at `app/routes/core.py:646` — this is expected; the endpoint expects JSON frames. The 101+connect smoke criterion passes.) |

**Security headers verified on `/`** (all present, per `app/server.py:321-337`):
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' ...` (full directive)

**Boot verdict: The app boots and serves cleanly. No boot-blockers found.**

---

## 2. TEST SUITE

### 2.1 Test Run

Command: `PYTHONPATH=. pytest tests/ -x -q --tb=short` (Python 3.11.15, fresh venv)

```
305 passed in 1.68s
```

**305/305 pass.** This matches the documented "305+ expected" in the testing skill. Zero failures, zero errors, zero skipped. The suite uses `starlette.testclient.TestClient` and completes in under 2 seconds.

Test files present (26 files in `tests/`): `test_data_paths.py`, `test_economic_loop.py`, `test_economy.py`, `test_governance.py`, `test_jwt_config.py`, `test_routes_agents.py`, `test_routes_core.py`, `test_routes_economy.py`, `test_routes_forums.py`, `test_routes_governance.py`, `test_routes_kassa.py`, `test_routes_lobby.py`, `test_routes_matcher.py`, `test_routes_misc.py`, `test_routes_missions.py`, `test_routes_operator.py`, `test_routes_pages.py`, `test_routes_provision.py`, plus `conftest.py` and several sim/script files (`chaos_sim.py`, `governance_sim.py`, `universe_sim.py`, etc.).

### 2.2 CI Configuration vs. Reality

**GitHub Actions** (`.github/workflows/ci.yml`):
```yaml
python-version: "3.13"
- run: pip install -r requirements.txt   # ← BROKEN: file deleted
- run: python -m pytest tests/ -x -q
```
**Status: BROKEN.** The `pip install -r requirements.txt` step will fail on every push/PR because `requirements.txt` no longer exists. CI has been broken since commit `17bbd11` (2026-05-05 era). This is F-2.

**CircleCI** (`.circleci/config.yml`):
```yaml
tag: "3.13"
pip-dependency-file: requirements.txt   # ← BROKEN: same file deleted
```
**Status: BROKEN** for the same reason. Both the `test` and `lint` jobs reference `requirements.txt`.

Additionally, the CircleCI `lint` job runs `py_compile app/server.py app/mcp_bridge.py app/economy.py` — these files still exist and are valid, so the lint step itself is fine *if* deps install. But the install step fails first.

**CI does not match how the app builds.** The app now installs from `pyproject.toml` deps (or not at all, since `pip install -e .` fails on `packages = []`). Both CI configs need to switch to `pip install` of the explicit dep list or a regenerated `requirements.txt` / `requirements-lock.txt`.

---

## 3. DEPLOYMENT & CONFIG DRIFT

### 3.1 Start Command Mismatch

Four files specify start commands, and they disagree:

| File | Start Command | Workers | Entry |
|------|---------------|---------|-------|
| `railway.json` | `/opt/venv/bin/python -m uvicorn app.server:app --host 0.0.0.0 --port $PORT` | **4** | `app.server:app` (module-level `create_app()` at `server.py:412`) |
| `Procfile` | `uvicorn app.server:app --host 0.0.0.0 --port $PORT` | default (1) | `app.server:app` |
| `run_prod.py` | `uvicorn.run(app, host="0.0.0.0", port=port)` | 1 | `run_prod.py` (calls `create_app()` itself) |
| `run.py` | `uvicorn.run(app, host="127.0.0.1", port=8300)` | 1 | `run.py` (local only, 127.0.0.1) |
| `adapters/railway.toml` | `python adapters/fetchai_adapter.py` | — | **Different service** (FetchAI adapter, not CIVITAE) |

**Railway uses `railway.json`** → 4 workers, `app.server:app`. The `Procfile` and `run_prod.py` are stale alternatives that would run with 1 worker. The 4-worker config is **intentional and correct** for MCP: `app/mcp_bridge.py:121-128` sets `stateless_http=True` specifically because "Railway runs multiple workers (--workers 4) since session state can't be shared across processes." The `Procfile` and `run_prod.py` are not actively used by Railway but create confusion. See F-4.

### 3.2 Dockerfile Drift

The `Dockerfile` is **not a deployment artifact for the CIVITAE backend** — it is a Glama introspection surface only. It installs `civitae-mcp==0.2.0` from PyPI and runs `python -m civitae_mcp` (stdio MCP). The core FastAPI platform is not included. This is by design (comment at line 4-7). **No drift issue**, but worth noting: the Dockerfile uses Python 3.12-slim while CI targets 3.13 and `pyproject.toml` requires `>=3.10`.

### 3.3 Environment Variables — Full Inventory

Cross-referencing `CLAUDE.md` env table (lines 160-172) against actual `os.environ.get` calls in `app/server.py`, `app/notifications.py`, `app/jwt_config.py`, `app/kassa_payments.py`, `app/data_paths.py`, and route modules:

| Env Var | Read In | Default | Breaks If Unset | Verdict |
|---------|---------|---------|-----------------|---------|
| `CIVITAE_DEV_MODE` | `server.py:223` | `""` | Nothing — local dev convenience only | Safe |
| `CIVITAE_ADMIN_KEY` | `server.py:131`, routes/operator, kassa, forums, connect, advisory, provision | `""` | **All non-public writes blocked (403) in prod**; localhost allowed in dev mode | **Required for prod** — fail-closed by design |
| `KASSA_JWT_SECRET` | `jwt_config.py:14`, routes/kassa, provision, agents, economy | `""` → falls back to `JWT_SECRET` → ephemeral key | **RuntimeError on Railway** (`jwt_config.py:20-24`) — app refuses to boot | **Required for prod** — fail-loud by design |
| `JWT_SECRET` | `jwt_config.py:14` (fallback) | `""` | Same as above | Fallback only |
| `KASSA_JWT_SECRET_PREV` | `jwt_config.py:37` | `""` | Nothing — graceful rotation only | Optional |
| `RAILWAY_ENVIRONMENT` | `jwt_config.py:20`, `server.py:222`, `data_paths.py:41` | Auto-set by Railway | JWT check becomes lenient; admin-key guard becomes dev-mode | Auto on Railway |
| `RESEND_API_KEY` | `notifications.py:32` (also checks `SMTP_PASS`) | `""` | Emails log to stdout instead of sending (`notifications.py:83-102`) — **silent degradation, no error** | See F-5 |
| `OPERATOR_EMAIL` | `notifications.py:35` | `""` (empty string) | `send_operator_alert()` sends to `""` — Resend API will reject, returns `False`; no crash | **F-6: flagged** |
| `SMTP_FROM` | `notifications.py:33` | `noreply@signomy.xyz` | Uses default | Safe |
| `CIVITAE_BASE_URL` | `notifications.py:36`, `kassa_payments.py:871` | `http://localhost:8300` / `https://signomy.xyz` | Magic link emails point to wrong host | Should set on Railway |
| `STRIPE_SECRET_KEY` | `kassa_payments.py:31` | `""` | Payment endpoints return 503/`{"error":"Stripe not configured"}` | Required for payments |
| `STRIPE_WEBHOOK_SECRET` | `kassa_payments.py:37` | `""` | Webhook signature verification skipped | Should set for prod |
| `MPP_SECRET_KEY` | `kassa_payments.py:39` | `""` | MPP endpoints inactive | Optional |
| `MPP_RECIPIENT` | `kassa_payments.py:40` | `""` | MPP uses `"civitae-treasury"` fallback | Optional |
| `ALLOWED_ORIGIN` | `server.py:204` | `""` | CORS only allows localhost origins | Must set to Vercel origin for prod |
| `RAILWAY_VOLUME_MOUNT_PATH` | `data_paths.py:22` | `""` | **Warning logged but continues** — no strict volume validation | See F-7 |

**`OPERATOR_EMAIL` flag (F-6):** `notifications.py:35` defaults to `""`. `CLAUDE.md:172` says "Must be set — no default" but the code gives it an empty-string default. If unset on Railway, `send_operator_alert()` calls `_send_email("", ...)` which will hit the Resend API with an empty recipient and return `False` (HTTP error). No crash, but operator alerts silently fail. The Pre-Launch Checklist item "Set `OPERATOR_EMAIL` on Railway" (`CLAUDE.md:181`) is still open.

**`RESEND_API_KEY` behavior when unset (F-5):** When the key is absent, `_send_email_inner()` (`notifications.py:83-102`) logs the email to stdout and returns `True` — it **pretends to succeed**. This means callers (magic link, message notification, operator alert) believe the email was sent when it was not. In dev this is fine; in prod with the key set but rate-limited/rejected, `_send_email_inner` returns `False` and callers handle it (e.g., `send_message_notification` only marks notified on success). The silent-success-on-missing-key behavior is a minor footgun but not a crash.

---

## 4. DATA & PERSISTENCE

### 4.1 Store-to-File Map

All stores are initialized in `app/server.py:create_app()` (lines 99-125) and `app/runtime.py:RuntimeState.__init__` (lines 27-80). The data directory is resolved by `app/data_paths.py:resolve_data_dir()` → `(root / "data").resolve()` and validated by `ensure_data_dir()`.

| Store | Backing File | Type | Init Location | Persists Across Restart? |
|-------|-------------|------|---------------|--------------------------|
| `MessageStore` | `data/messages.jsonl` | JSONL (append-only, loaded into memory) | `server.py:106` | **Yes** if volume mounted — file is appended to and reloaded on boot (`store.py:19-28`) |
| `KassaStore` | `data/kassa.db` | SQLite (WAL mode, `check_same_thread=False`) | `server.py:107`, `kassa_store.py:161-165` | **Yes** if volume mounted |
| `ForumsStore` | `data/forums.db` | SQLite (WAL mode) | `server.py:108` | **Yes** if volume mounted |
| `AuditSpine` / `AuditLedger` | `data/audit.jsonl` | JSONL (hash chain, loaded into memory) | `server.py:109`, `moses_core/audit.py:12-25` | **Yes** if volume mounted |
| `LobbyStore` | `data/lobby.db` | SQLite (WAL mode, per-connection) | `server.py:125`, `lobby.py:39-44` | **Yes** if volume mounted |
| `RuntimeState` (governance, systems, deploy, presence) | `data/runtime_state.json` + `data/mcp_cursors.json` | JSON (atomic write) | `runtime.py:40-41, 82-104` | **Yes** if volume mounted |
| `RuntimeState.provision` / `registry` | `data/provision.json` | JSON (atomic write, fcntl-locked) | `runtime.py:54-63, 115-137` | **Yes** if volume mounted (migrated from `config/provision.json` on first run) |
| `RuntimeState.vault` | `config/vault.json` (read-only) | JSON | `runtime.py:64-66` | **Yes** (committed to repo) |
| `SovereignEconomy` / `FeeCreditLedger` | `data/fee_credits.json` | JSON | `economy.py:479, 540` | **Yes** if volume mounted |
| Seeds / DOI provenance | `data/seeds.jsonl` | JSONL (atomic append, file-locked) | `seeds.py:32, 112` | **Yes** if volume mounted |
| Missions | `data/missions.json` | JSON (read/write per request) | `routes/missions.py:151` | **Yes** if volume mounted |
| Slots | `data/slots.json` | JSON | `routes/missions.py:163` | **Yes** if volume mounted |
| Campaigns | `data/campaigns.json` | JSON | `routes/missions.py:155` | **Yes** if volume mounted |
| Tasks | `data/tasks.json` | JSON | `routes/missions.py:159` | **Yes** if volume mounted |
| Metrics | `data/metrics.json` | JSON (corruption-guarded load) | `metrics_io.py:42-46` | **Yes** if volume mounted |
| Contacts | `data/contacts.jsonl` | JSONL (append) | `routes/operator.py:189, 234` | **Yes** if volume mounted |
| Inbox (Help Wanted applications) | `data/inbox.jsonl` | JSONL (append) | `routes/operator.py:292-335` | **Yes** if volume mounted |
| MPP challenges | **In-memory** `dict` | Ephemeral | `kassa_payments.py:44` | **No** — lost on restart (acceptable per comment line 45: "Cleared on restart (acceptable for stateless pay flow)") |
| `ConnectionHub` / `ThreadHub` (WebSocket) | **In-memory** | Ephemeral | `server.py:34-95` | **No** — connections drop on restart (expected) |

### 4.2 Volume Mount & Persistence (F-7)

**`LobbyStore(data_dir / "lobby.db")` persists to the volume** — `server.py:125` constructs it as `data_dir / "lobby.db"`, and `data_dir` is `resolve_data_dir(root)` = `<root>/data`. On Railway, root is the repo checkout (`/app`), so the path is `/app/data/lobby.db`. **This persists if and only if the Railway volume is mounted at `/app/data`.**

**The validation is soft.** `app/data_paths.py:ensure_data_dir()` (lines 26-69) checks `RAILWAY_VOLUME_MOUNT_PATH` — a **custom env var that Railway does not set automatically** (comment at line 47). If it is unset, the function logs a warning (line 51-56) and **continues anyway**. If it is set but `data_dir` is not in the mount list, it raises `RuntimeError` (line 58-61). The danger: if the operator hasn't mounted a volume at `/app/data`, the app will boot, write state to ephemeral container storage, and **lose everything on redeploy** — with only a log warning.

`railway.json` contains **no volume mount declaration** (verified — only `build` and `deploy` keys). Volume mounts are configured in the Railway dashboard, not in `railway.json`, so this is not necessarily a problem — but there is no in-repo evidence that a volume is attached, and the soft validation means a missing volume won't be caught at boot.

**State that would be lost on a Railway container restart without a volume:** all SQLite DBs (kassa, forums, lobby), all JSONL files (messages, audit, seeds, contacts, inbox), all JSON state (runtime, provision, missions, slots, campaigns, tasks, metrics, fee_credits). Essentially **the entire application state**. The only exception is `config/vault.json` which is read from `config/` (committed to repo).

---

## 5. KNOWN BACKLOG & STALE MARKERS

Reconciling `CLAUDE.md` "Recent Changes", "Pre-Launch Checklist", and "After-Launch Backend" tables against `SESSION_RESUME.md` and actual code state:

### 5.1 Pre-Launch Checklist (`CLAUDE.md:178-182`)

| Item | Status | Evidence |
|------|--------|----------|
| Run `bfg` to scrub git history | **STILL OPEN** | `git log --all` still shows `config/provision.json`, `.env` files in history (commits `0fdd8b9`, `78f91ee`, `0f9a856`, `5ecd424`). Repo is private, so no leak yet, but must be done before going public. |
| Set `OPERATOR_EMAIL` on Railway | **STILL OPEN (cannot verify from repo)** | Code defaults to `""` (`notifications.py:35`). No way to confirm Railway env from here. |
| Verify Vercel redeploy | **STALE** | No date; likely done long ago. OG tags/copy-link/auth fixes referenced in `CLAUDE.md:251-253`. |

### 5.2 After-Launch Backend Backlog (`CLAUDE.md:306-320` vs `STATUS.md:357-365` vs code)

| Item | CLAUDE.md says | STATUS.md says | Code reality | Verdict |
|------|---------------|----------------|--------------|---------|
| Fee Credit Pack endpoints | "Not started" | "PARTIAL" | **PARTIAL** — `FeeCreditLedger` class at `economy.py:471-510` (credit/consume/balance), webhook crediting at `connect.py:551-567`, consumption at settlement at `economy.py:678-686`. No purchase/balance-query API endpoint found, but the ledger + Stripe webhook + settlement integration exist. | **Partially done** — CLAUDE.md is stale |
| Seed Card | "Not started" | "MISSING" | No code found | **Still open** |
| Sliding Scale Reward Engine | "Not started" | "MISSING" | No code found | **Still open** |
| Phase transition logic (Day 1/8/31) | "Not started" | "MISSING" | No code found | **Still open** |
| Founding Contributor badge auto-assign | "Not started" | "MISSING" | No code found | **Still open** |
| Cascade Matcher (AGENTDASH Layer 1) | "Not started" | "MISSING" | `routes/matcher.py` exists but is a stub/placeholder | **Still open** |
| Operator auth flow (login → JWT → console) | "Not started" | "MISSING" | No login endpoint in `routes/operator.py` — console is gated by Velvet Rope + admin key, no JWT login | **Still open** |
| GPT/Gemini/DeepSeek/Grok agents | "Not started" | — | Wired in `config/agents.json`, need API keys | **Still open** (config-only) |
| Chain adapter execution layer | "Not started" | "PARTIAL" | `app/chains.py` exists with interface, execution pending | **Still open** (interface only) |
| Refinery (SIGRANK) | "Not started" | "PARTIAL" | `seeds_otel.py`, `routes/matcher.py` — placeholder | **Still open** |
| Switchboard (signal routing) | "Not started" | "PARTIAL" | `routes/pages.py` references only | **Still open** |

### 5.3 SESSION_RESUME.md Open Items

| Item | Status |
|------|--------|
| Glama Docker build | **Stale/paused** — Dockerfile exists and is self-contained (commits `47b1192`, `347cb31`). Glama listing status unknown from repo. |
| Agentic.ai listing | **Blocked** (needs business email) — no code action |
| MCP registry / Smithery / PulseMCP / PyPI | **Done** per SESSION_RESUME — `civitae-mcp` v0.2.0 on PyPI confirmed (installed in this assessment) |

### 5.4 Stale Documentation Markers

- `CLAUDE.md:316` says Fee Credit Pack "Not started" but code shows PARTIAL — **stale**.
- `CLAUDE.md` "Last updated: 2026-04-07" (line 324) — 3 months stale.
- `AGENTS.md` "Last updated: 2026-03-24" (line) — 4 months stale, references old `app/server.py` as "40+ endpoints" when it's now 412 lines with 18 route modules.
- `STATUS.md` is the most accurate backlog source (lines 357-365 match code).

---

## 6. PRIORITIZED FINDINGS

| # | Finding | Severity | Blocks Boot? | Blocks Feature? | Recommended Action |
|---|---------|----------|-------------|-----------------|-------------------|
| **F-1** | CI targets Python 3.13 but no 3.13 interpreter is installed locally; tests verified on 3.11 only | degraded | No | No | Install Python 3.13 locally or add a 3.11 fallback matrix in CI. Low priority — 3.11 tests pass clean. |
| **F-2** | `requirements.txt` deleted (commit `17bbd11`) but both CI configs (`ci.yml`, `config.yml`) still run `pip install -r requirements.txt` → **CI is broken on every push/PR** | **blocker** (for CI) | No (app boots) | Yes (CI) | **Must-fix:** Either regenerate `requirements.txt` from `pyproject.toml` deps (e.g., `pip freeze` or a lock file) or update both CI configs to install from `pyproject.toml` deps directly. This has been broken since ~May 2026. |
| **F-3** | `pip install -e .` fails — `pyproject.toml` has `packages = []` so hatchling can't build a wheel | degraded | No | No | Intentional (repo is not a pip package). Document this in README or add a `requirements-lock.txt` for reproducible installs. |
| **F-4** | Start command drift: `railway.json` (4 workers), `Procfile` (1 worker), `run_prod.py` (1 worker, no `/opt/venv`) — confusing but Railway uses `railway.json` | cosmetic | No | No | Delete or annotate `Procfile` and `run_prod.py` as deprecated, or align them with `railway.json`. The 4-worker config is correct (`mcp_bridge.py:121-128` depends on `stateless_http=True`). |
| **F-5** | `RESEND_API_KEY` unset → `_send_email` logs to stdout and returns `True` (silent fake success) | degraded | No | Yes (email) | Add a prod-mode guard: if `RAILWAY_ENVIRONMENT` is set and `RESEND_API_KEY` is missing, log a warning at boot (like the Stripe key warning). Don't fake success in prod. |
| **F-6** | `OPERATOR_EMAIL` defaults to `""` — operator alerts silently fail (Resend rejects empty recipient) | degraded | No | Yes (alerts) | **Must-fix for prod:** Set `OPERATOR_EMAIL` on Railway. Code could also fail-loud at boot on Railway if empty (matching the JWT secret pattern). |
| **F-7** | `RAILWAY_VOLUME_MOUNT_PATH` is a custom env var (not auto-set by Railway); if unset, `ensure_data_dir` only logs a warning — **all state could silently write to ephemeral storage and be lost on redeploy** | **degraded** (blocker if volume missing) | No | Yes (data loss) | **Must-verify:** Confirm a Railway volume is mounted at `/app/data`. Consider making the warning louder or requiring `RAILWAY_VOLUME_MOUNT_PATH` to be set on Railway (fail-loud). |
| **F-8** | `bfg` history scrub not run — `config/provision.json`, `.env` files still in git history | **blocker** (for going public) | No | No | **Must-fix before making repo public:** Run `bfg --delete-files provision.json` etc., then force-push. Repo is currently private so no active leak. |
| **F-9** | `CLAUDE.md` backlog table says Fee Credit Pack "Not started" but code shows PARTIAL (`FeeCreditLedger` at `economy.py:471`, webhook crediting at `connect.py:551`) | cosmetic | No | No | Update `CLAUDE.md:310` to "Partial — ledger + Stripe webhook done, purchase/balance API endpoints pending." |
| **F-10** | `CLAUDE.md` and `AGENTS.md` "Last updated" dates are 3-4 months stale; `AGENTS.md` describes old architecture ("40+ endpoints", no mention of 18 route modules) | cosmetic | No | No | Refresh both files or add a "see STATUS.md for current state" pointer. |
| **F-11** | Operator auth flow (login → JWT → console) not built — console is gated only by Velvet Rope + admin key | degraded | No | Yes (operator UX) | Feature gap, not a bug. Build operator login endpoint issuing JWTs, gate console on JWT instead of admin key. |
| **F-12** | MPP challenge store is in-memory (`kassa_payments.py:44`) — lost on restart | cosmetic | No | No | Acceptable per code comment ("stateless pay flow"). No action needed unless MPP goes live. |

### Summary by Priority

**Must-fix to boot and serve (blockers):**
- None. The app boots clean and all smoke endpoints pass. ✅

**Must-fix for CI/CD and prod safety:**
- **F-2:** Fix CI — `requirements.txt` deleted but CI still references it. Both GitHub Actions and CircleCI are broken.
- **F-7:** Verify Railway volume is mounted at `/app/data` — or state is lost on every redeploy.
- **F-8:** Run `bfg` before making repo public — sensitive files still in git history.
- **F-6:** Set `OPERATOR_EMAIL` on Railway — operator alerts silently fail otherwise.

**Needed for full feature parity:**
- **F-5:** Don't fake email success when `RESEND_API_KEY` is missing in prod.
- **F-11:** Build operator auth flow (login → JWT → console).
- Backlog items per Section 5.2 (Seed Card, Sliding Scale, Phase transitions, Cascade Matcher, Refinery, Switchboard, chain execution).

**Nice-to-have (cosmetic/stale):**
- **F-1:** Python 3.13 local install or CI matrix.
- **F-3:** Document the non-installable `pyproject.toml` or add a lock file.
- **F-4:** Reconcile/deprecate `Procfile` and `run_prod.py`.
- **F-9, F-10:** Update stale docs (`CLAUDE.md`, `AGENTS.md`).
- **F-12:** No action (MPP in-memory is by design).

---

**Bottom line:** The repo is **healthy at the boot-and-serve level** — 305 tests pass, all smoke endpoints respond correctly, no import errors or tracebacks. The two real problems are (1) **CI is broken** because `requirements.txt` was deleted without updating CI configs, and (2) **Railway volume persistence must be verified** because the validation is soft. Everything else is either a documented feature gap or stale documentation. No code changes were needed or applied.
