---
type: Coordination
title: SCRATCHPAD — the canonical multi-session coordination bus
description: THE one shared message bus + decision log for all sessions. Read the tail before doing anything; append your status/decisions/questions. OKF frontmatter convention applies to every doc in this directory.
tags: [coordination, scratchpad, protocol]
timestamp: 2026-01-01T00:00:00Z
last_touched: 2026-07-06 05:14 UTC
---

# SCRATCHPAD (canonical coordination bus)
**THE shared message bus + decision log for every session.**

> ## COORDINATION PROTOCOL (read before acting)
> 1. **This file is the one bus.** Before starting work, read the tail. Append your status/decisions/
>    questions here. Don't start a parallel log.
> 2. **Message format:** `### ⤷ <FROM> → <TO>: <subject>`
> 3. **OWNER mediates** decisions code/canon can't answer.
> 4. **OKF convention:** every doc in this directory carries YAML frontmatter
>    (`type/title/description/tags/timestamp`). New docs MUST include it.
> 5. **Lane discipline:** shared files = announce here before editing.
> 6. **Install hooks once per clone:** `bash scripts/install-hooks.sh`

---

### ⤷ PREVIOUS SESSION → NEXT SESSION: carry-forward items from SESSION_RESUME.md

> Extracted 2026-07-06 from `docs/archive/SESSION_RESUME.md` (last checkpoint 2026-05-05).
> These are the live actionable items that need to stay warm.

#### MCP Distribution — status

| Platform | Status |
|----------|--------|
| Official MCP Registry | ✅ `xyz.signomy/civitae` v1.1.2 active |
| Smithery | ✅ `burnmydays/civitae`, 100% quality, 19 tools, TS SDK published |
| Glama | ⏳ paused mid-Docker-config (see below) |
| PulseMCP | ✅ live |
| AI Agents Directory | ✅ listed (badge in README) |
| PyPI `civitae-mcp` | ✅ v0.2.0 live |
| Agentic.ai | ⏳ blocked on business email |

#### Immediate: finish Glama Docker build

Glama wants a Dockerfile config to host the server. Values to paste into the Glama form:

**Build steps:**
```json
["pip install --no-cache-dir -r requirements.txt"]
```

**CMD:**
```json
["sh", "-c", "python -m uvicorn app.server:app --host 0.0.0.0 --port ${PORT:-8300}"]
```

**Placeholder parameters:**
```json
{
  "CIVITAE_ADMIN_KEY": "dummy-admin-key-not-for-real-use",
  "KASSA_JWT_SECRET": "dummy-jwt-secret-replace-in-prod",
  "RESEND_API_KEY": "re_dummy_for_glama_build_check",
  "OPERATOR_EMAIL": "noreply@signomy.xyz",
  "STRIPE_SECRET_KEY": "sk_test_dummy_for_glama_build_check"
}
```

> Note: Glama auto-detected base image (debian:trixie-slim), Python 3.14, Node 25, and pulled the env var schema from the repo. The three fields above are what's missing.

#### After Glama: wait on Agentic.ai (blocked on business email)

#### Credentials reminders

- **MCP registry private key:** stored in password manager. The auth file at `signomy.xyz/.well-known/mcp-registry-auth` references the matching public key. To republish: `mcp-publisher login http --domain signomy.xyz --private-key <key>`, then `mcp-publisher publish`.
- **PyPI token:** used once and deleted from `.pypirc`. Create a new project-scoped token at pypi.org if you need to push another version.
- **CircleCI:** config at `.circleci/config.yml` — connect via dashboard if not already done.

#### Open backend backlog (not blocking)

- Fee Credit Pack purchase/balance/apply endpoints
- Seed Card (points, streaks, badges, 48h banking) — 953 lines on `devin/1775076305-seed-card-loyalty-system` branch, ready to merge
- Sliding Scale Reward Engine
- Phase transition logic (Day 1/8/31)
- Operator auth flow (login → JWT → console)
- Cascade Matcher (AGENTDASH Layer 1)
- Refinery (SIGRANK) — placeholder
- Switchboard (signal routing) — depends on Refinery

---

<!-- POST-COMMIT HOOK APPENDS BELOW THIS LINE -->
[HOOK] 2026-07-07 15:20 UTC · c1c723b · Deric · Repo cleanup: untrack runtime files, archive stale docs
[HOOK] 2026-07-07 14:29 UTC · 9f04880 · Deric · Replace hardcoded fictional agents with real API data
[HOOK] 2026-07-07 11:21 UTC · e2fcffa · Deric · fix: complete GEO/SEO gaps on 4 missed pages
[HOOK] 2026-07-07 10:59 UTC · 276b7e4 · Deric · geo: optimize content for AI citation on 20 priority pages (Step 8)
[HOOK] 2026-07-07 10:31 UTC · 2076de9 · Deric · fix: exempt /api/indexnow from admin key guard
[HOOK] 2026-07-07 10:28 UTC · ac57a93 · Deric · seo: add JSON-LD, llms-full.txt, IndexNow, internal links, UTM, sameAs
[HOOK] 2026-07-07 10:15 UTC · b2b9057 · Deric · seo: trim sitemap from 51 to 20 priority URLs
[HOOK] 2026-07-07 10:14 UTC · a0ddc74 · Deric · seo: optimize meta tags for 20 priority pages (fix 0-click problem)
[HOOK] 2026-07-07 10:11 UTC · cc513c9 · Deric · docs: update GEO/SEO/AEO plan — focus on 20 pages, add meta tag + GEO content steps
[HOOK] 2026-07-07 09:36 UTC · 70979d8 · Deric · docs: document admin review queue in OPERATOR-GUIDE.md
[HOOK] 2026-07-07 09:27 UTC · 927f35d · Deric · feat: split operator review queue to /admin, clean up user console
[HOOK] 2026-07-07 09:10 UTC · fe8cc76 · Deric · feat: unified review queue — lobby joins + agent signups in console
[HOOK] 2026-07-07 08:00 UTC · 8f76298 · Deric · feat: notify operator on agent signup + lobby join request
[HOOK] 2026-07-06 23:12 UTC · b2a7cbe · Deric · fix: delete .dockerignore that was blocking NIXPACKS build context
[HOOK] 2026-07-06 23:08 UTC · 89c64aa · Deric · fix: rename Dockerfile → Dockerfile.glama so Railway uses NIXPACKS
[HOOK] 2026-07-06 19:56 UTC · 8ee2eb7 · Deric · fix: restore requirements.txt for Railway/NIXPACKS + CI
[HOOK] 2026-07-06 19:39 UTC · 8dc381a · Deric · fix(ci): install deps from pyproject.toml instead of deleted requirements.txt
[HOOK] 2026-07-06 13:45 UTC · dbe6018 · Deric · chore: archive SESSION_RESUME.md — extract live items to SCRATCHPAD
[HOOK] 2026-07-06 13:43 UTC · 942c4bc · Deric · fix: replace dead COWORK_CLAUDE.md ref with v2 coordination protocol
[HOOK] 2026-07-06 13:41 UTC · ab5ab6b · Deric · feat: install multi-agent-coord v2 — 6-layer coordination system
