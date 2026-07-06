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
[HOOK] 2026-07-06 13:43 UTC · 942c4bc · Deric · fix: replace dead COWORK_CLAUDE.md ref with v2 coordination protocol
[HOOK] 2026-07-06 13:41 UTC · ab5ab6b · Deric · feat: install multi-agent-coord v2 — 6-layer coordination system
