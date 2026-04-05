Here's what we haven't covered yet — a mix of security gaps, operational risks, and launch-readiness items:

---

## 1. No dependency manifest exists

There is no `requirements.txt`, no `pyproject.toml`, no `setup.py`, no `Pipfile` — nothing that pins your Python dependencies. Anyone deploying this (including Railway) gets whatever version of FastAPI, httpx, PyJWT, uvicorn, etc. happens to resolve that day. A single breaking change in any dependency breaks your production deploy with no way to reproduce the working state. [7-cite-0](#7-cite-0) 

**Fix:** Create a `pyproject.toml` or at minimum a `requirements.txt` with pinned versions. Run `pip freeze > requirements.txt` from your working venv today.

---

## 2. No CI/CD pipeline

No `.github/workflows/`, no `ci.yml`, no test runner config of any kind. Your 12 test files never run automatically. You could push a commit that breaks the economy engine and not know until a user hits it in production.

**Fix:** Add a GitHub Actions workflow that runs `pytest` on push. Even a 5-line YAML file catches regressions.

---

## 3. The `/docs` directory is served as static files in production

This line mounts your entire `docs/` directory as a public static file server: [7-cite-1](#7-cite-1) 

That means `review_devin.md`, every session report, every TODO list, and every vulnerability map in `docs/` is accessible at `https://your-domain/docs/review_devin.md`. This is the same content I told you to remove from the repo — but even if it's in the repo, it shouldn't be *served*.

**Fix:** Either remove the mount entirely, or create a `docs/public/` subdirectory and only mount that.

---

## 4. CORS allows all methods and all headers

```python
allow_methods=["*"],
allow_headers=["*"],
``` [7-cite-2](#7-cite-2) 

The origins are locked down (localhost + one env var), which is good. But `allow_methods=["*"]` and `allow_headers=["*"]` is overly permissive. In practice this means any origin that gets through (or any misconfiguration of `ALLOWED_ORIGIN`) has full method access including DELETE and PATCH.

**Fix:** Restrict to `allow_methods=["GET", "POST", "PATCH", "DELETE"]` and `allow_headers=["Content-Type", "Authorization", "X-Admin-Key"]`.

---

## 5. WebSocket endpoints have no authentication

The `_verify_jwt()` helper exists in `core.py`, but I found no evidence that the main WebSocket endpoints (`/ws/`, the ConnectionHub, the public hub) require JWT verification before accepting connections. The admin key guard middleware explicitly exempts `/ws/` paths: [7-cite-3](#7-cite-3) [7-cite-4](#7-cite-4) 

This means anyone can open a WebSocket connection and receive all real-time messages without authenticating. For a governed platform, this is a gap.

---

## 6. The `_PUBLIC_WRITE_PREFIXES` list is very generous

These endpoints bypass the admin key guard entirely: [7-cite-5](#7-cite-5) 

Notable inclusions:
- `/api/kassa/posts` — anyone can create marketplace posts without auth
- `/api/forums/threads` — anyone can create forum threads without auth
- `/api/slots/fill` — anyone can fill a mission slot without auth
- `/api/connect/` — all Stripe Connect endpoints are public writes
- `/api/lobby/` — all lobby operations are public

Some of these are intentionally public (signup, heartbeat, contact). But `slots/fill` and `kassa/posts` being fully public means an unauthenticated actor can fill slots and post to the marketplace. These should require at minimum a valid JWT from a registered agent.

---

## 7. `vercel.json` exposes your Railway backend URL

```json
{ "source": "/api/:path*", "destination": "https://agent-universe-production.up.railway.app/api/:path*" }
``` [7-cite-6](#7-cite-6) 

Your Railway backend URL (`agent-universe-production.up.railway.app`) is in a committed file. Anyone can hit it directly, bypassing Vercel's edge caching and any future CDN-level protections. This also means if you ever add Vercel-level rate limiting or WAF rules, attackers just go around them.

**Fix:** Not easily fixable without Railway custom domains, but be aware that your backend is directly addressable.

---

## 8. `README.md` has your personal email

```
contact@burnmydays.com
``` [7-cite-7](#7-cite-7) 

Same email is hardcoded in `notifications.py`. If this repo ever becomes public (even briefly), that email is scraped instantly. Use a role-based address like `operator@signomy.xyz` or `hello@signomy.xyz`.

---

## 9. `.gitignore` misses `data/*.md` and `data/*.db`

Your `.gitignore` covers `data/*.jsonl` and `data/*.json` and specifically `data/kassa.db`, but there's a governance meeting minutes file sitting in the data directory right now: [7-cite-8](#7-cite-8) 

`data/minutes_20260321_002336.md` is committed and visible. Any future `.md` or `.db` files created in `data/` will also be committed by default.

**Fix:** Add `data/*.md` and `data/*.db` to `.gitignore` (or just use `data/*` with `!data/.gitkeep`).

---

## 10. No LICENSE file at the repo root

The only license file is `governance-cache/claude-plugin/LICENSE.md` — which covers the plugin, not the platform. The repo root has no license, which means legally, no one has permission to use, modify, or distribute any of the code. That's actually *correct* for a proprietary platform with a pending patent — but you should add an explicit `LICENSE` file that says so, rather than relying on the absence of one.

**Fix:** Add a root `LICENSE` file: "All Rights Reserved. © 2026 Ello Cello LLC. Patent Pending." This makes the proprietary status explicit rather than implied.

---

## 11. JWT secret is cached at module import time in `provision.py`

```python
_JWT_SECRET = get_kassa_jwt_secret()
``` [7-cite-9](#7-cite-9) 

This runs at import time, not at request time. If the env var isn't set when the module first loads, the ephemeral fallback is used and cached forever (via `@lru_cache`). The `jwt_config.py` has a `clear_kassa_jwt_secret_cache()` function, but `provision.py` captures the value into a module-level variable that won't update even if the cache is cleared. [7-cite-10](#7-cite-10) 

Not a launch blocker on Railway (env vars are set before boot), but it's a latent bug.

---

## 12. `netlify.toml` and `vercel.json` both exist

You have deployment configs for both Netlify and Vercel committed. The `README.md` says "Vercel (frontend) + Railway (backend)." If you're on Vercel, the `netlify.toml` is dead weight that could confuse contributors or, worse, accidentally deploy to Netlify if someone connects the repo there. The redirect rules between the two files are also inconsistent (Netlify routes `/` to `civitas.html`, Vercel routes `/` to `kingdoms.html`). [7-cite-11](#7-cite-11) [7-cite-12](#7-cite-12) 

**Fix:** Delete whichever one you're not using.

---

## 13. Root-level clutter

These files are in the repo root and probably shouldn't be:

| File | Issue |
|------|-------|
| `civitae-wireframe.excalidraw` | Design artifact — belongs in `docs/` or `reference/` |
| `kassa-review.html` | One-off review page — belongs in `reference/` |
| `make_report.py` | Utility script — belongs in `scripts/` |
| `nav-restructure-plan.md` | Internal planning doc — belongs in `reference/` |
| `stress-test.sh` + `stress_test.py` | Testing tools — belong in `tests/` |
| `AGENTS.md` | Could be in `docs/` |

The root should be: `README.md`, `LICENSE`, `CONTRIBUTING.md`, `ONTOLOGY.md`, `CHANGELOG.md`, `run.py`, `run_prod.py`, `pyproject.toml`, `.gitignore`, and the main directories.

---

## Priority summary

| # | Issue | Severity | Effort |
|---|-------|----------|--------|
| 1 | No dependency pinning | **High** | Low |
| 2 | No CI/CD | **High** | Low |
| 3 | `/docs` served as static files | **High** | Low (1 line) |
| 4 | CORS too permissive | Medium | Low |
| 5 | WebSocket no auth | Medium | Medium |
| 6 | Public write prefixes too broad | **High** | Medium |
| 7 | Railway URL exposed | Low | N/A |
| 8 | Personal email in README | Medium | Low |
| 9 | `.gitignore` gaps | Medium | Low |
| 10 | No root LICENSE | Medium | Low |
| 11 | JWT import-time capture | Low | Low |
| 12 | Dual deploy configs | Low | Low |
| 13 | Root clutter | Low | Low |

Items 1, 2, 3, and 6 are the ones I'd fix before launch day. The rest can follow.