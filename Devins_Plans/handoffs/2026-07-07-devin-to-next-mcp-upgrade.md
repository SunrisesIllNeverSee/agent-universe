---
type: handoff
title: MCP Upgrade Complete — Next Steps
description: Handoff from Devin session 2026-07-07. MCP upgraded to 27 tools + 7 resources. Repo cleaned up. Pending items for next session.
tags: [mcp, handoff, cleanup, deployment]
timestamp: 2026-07-07T12:00:00Z
---

# Handoff: MCP Upgrade + Repo Cleanup

**From:** Devin (2026-07-07 session)
**To:** Next session (any agent)
**Topic:** MCP upgrade complete, repo cleanup done, pending items

---

## What Was Done This Session

### 1. agents.html + leaderboard.html (from prior session, completed)
- Fixed `agents.html` to fetch real agent data from `/api/agents`
- Fixed `leaderboard.html` to show real agent rankings from API
- Removed "DEMO — SIMULATED DATA" badge, changed to "LIVE DATA"
- Deployed to Railway + Vercel

### 2. Kassa marketplace cleanup (from prior session, completed)
- Archived 17 old Kassa posts using admin key
- Fixed unverified claims on K-00002 and K-00003
- Created 20 new realistic R&D posts (K-00049 through K-00068)

### 3. Repo structure cleanup (this session)
- `git rm --cached` 4 runtime files (.playwright-mcp/*, data/forums.db, data/lobby.db) — 240KB of junk in git
- Moved `data/minutes_20260321_002336.md` to `docs/archive/sessions/` (governance session record)
- Deleted `docs/archive/agent-onboarding.zip` (duplicate of `docs/agent-onboarding/` directory)
- Moved 4 stale root docs to `docs/archive/` (ASSESSMENT.md, STATUS.md, two SEO plans)
- Deleted stale `railway.toml` (Railway uses `railway.json`)
- Deleted `frontend/pages.json` (duplicate of `config/pages.json`) — updated 4 frontend files to fetch `/api/pages` instead
- Fixed path bug in `/api/pages` route (`parent.parent` → `parent.parent.parent`)
- Deleted dead `frontend/agents.json` (not referenced by any code)
- Moved 7 sim scripts from `tests/` to `scripts/experiments/`
- Moved MCP entry points (`civitae_mcp_server.py`, `run_mcp_command.py`) to `packages/civitae-mcp/`
- Fixed `sys.path` in `run_mcp_command.py` for new location

### 4. MCP upgrade (this session)
- **Bridge** (`app/mcp_bridge.py`): 19 → 27 tools, added 7 MCP resources
- **PyPI package** (`packages/civitae-mcp/`): 15 → 23 tools, v0.2.0 → v0.3.0
- **Deleted** stale `civitae_mcp_server.py` (was duplicate of package with wrong env var names)
- Updated `server.json` (v1.2.0), `mcp-server-card.json` (v1.2.0, 27 tool definitions)
- Updated `MCP_INSTRUCTIONS` to reflect 5 domains, 27 tools
- All verified live on signomy.xyz/mcp

**Full plan document:** `docs/plans/MCP-UPGRADE-PLAN.md`

---

## Current State

### MCP Bridge (live at signomy.xyz/mcp)
- **27 tools** across 5 domains:
  - CHAT (4): chat.join, chat.read, chat.send, chat.status
  - MARKETPLACE (10): agent.register, agent.status, market.browse, market.post, market.stake, market.message, agent.profile, mission.list, forum.thread, agent.cashout
  - DISCOVERY (8): agent.leaderboard, agent.lookup, govern.sessions, govern.meetings, economy.tiers, economy.treasury, platform.health, platform.seeds
  - GOVERNANCE (1): govern.vote
  - OPERATOR (4): admin.reviews, admin.stakes, admin.audit, admin.stats
- **7 resources**: governance://GOV-001 through GOV-006, manifest://agent.json

### PyPI package (repo only, not published)
- **23 tools** (same as bridge minus 4 chat tools that need in-process access)
- Version 0.3.0 in `packages/civitae-mcp/pyproject.toml`
- Tool names use underscore convention: `civitae_register`, `civitae_browse`, etc.

### Live data
- 51 agents registered
- 161 seeds (158 planted, 3 grown)
- Treasury at 0 (no real transactions yet)
- 20 R&D posts in Kassa marketplace

### Commits this session
1. `c1c723b` — Repo cleanup: untrack runtime files, archive stale docs
2. `6d79fe4` — Repo structure cleanup: dedupe configs, move MCP + sim scripts
3. `22c1d28` — MCP upgrade: 27 tools, 7 resources, package v0.3.0

All pushed to `main` and deployed.

---

## Pending TODO — Pick Up Next Time

### High Priority

- [ ] **Publish civitae-mcp v0.3.0 to PyPI**
  - Package is at `packages/civitae-mcp/`, version 0.3.0, 23 tools
  - Build: `cd packages/civitae-mcp && python -m build`
  - Publish: `twine upload dist/*` (needs PyPI credentials)
  - Last published version was 0.2.0

- [ ] **Update Smithery listing**
  - Currently shows 19 tools, needs to show 27
  - Smithery listing: `burnmydays/civitae` (100% quality score)
  - May need to re-submit or update via Smithery CLI/dashboard

- [ ] **Update PulseMCP listing**
  - Currently live but may show old tool count
  - Check if it auto-discovers or needs manual update

- [ ] **Mobile UI viewing**
  - Frontend is 30+ HTML pages designed for desktop — no responsive/mobile CSS
  - Need to audit all pages on mobile viewport (375px width)
  - Key pages to fix first: index.html (home), kassa.html (marketplace), agents.html, leaderboard.html, portal.html, console.html
  - Likely needs: viewport meta tag audit, responsive grid breakpoints, mobile nav (hamburger), font-size scaling, touch-friendly buttons
  - _nav.js two-tier nav probably breaks on mobile — needs collapsible/hamburger variant
  - Fixed-viewport pages (console, deploy, campaign, world) may need separate mobile layouts or a "desktop only" notice

### Medium Priority

- [ ] **Add MCP prompts** (templates for guided flows)
  - `register-agent` — guided registration flow
  - `post-bounty` — guided marketplace posting flow
  - `join-mission` — guided mission discovery + slot fill flow
  - Deferred from this session per plan

- [ ] **Update CLAUDE.md** to reflect 27 tools + new directory structure
  - CLAUDE.md still references old paths (civitae_mcp_server.py at root, 19 tools, etc.)

- [ ] **Update docs/agent-onboarding/PLUGIN-BLUEPRINT.md**
  - Still references `civitae_mcp_server.py` (line 514)
  - Should point to `packages/civitae-mcp/` or `pip install civitae-mcp`

- [ ] **Update docs/CIVITAE-STATE-OF-THE-UNION-APRIL-2026.md**
  - Line 33 still says "civitae_mcp_server.py, 15 tools"
  - Should say "27 tools, 7 resources"

### Low Priority

- [ ] **Tool name unification consideration**
  - Bridge uses dot notation (`agent.register`), package uses underscores (`civitae_register`)
  - Current decision: keep both (see MCP-UPGRADE-PLAN.md P1)
  - May want to revisit if agents report confusion

- [ ] **MCP eval for CIVITAE**
  - The `mcp_eval` folder on Desktop is for `application-hub-mcp-server`, NOT CIVITAE
  - Could run a similar eval against CIVITAE's MCP to score it
  - Would need to install `plugin-eval` tool or use a similar framework

- [ ] **Seed card loyalty system branch**
  - `devin/1775076305-seed-card-loyalty-system` (953 lines unique, unmerged)
  - Still sitting as the only non-main branch
  - Either merge or delete

---

## Key Files Changed This Session

| File | What changed |
|------|-------------|
| `app/mcp_bridge.py` | +8 tools, +7 resources, updated instructions, +Path import |
| `packages/civitae-mcp/src/civitae_mcp/__init__.py` | +8 tools, version 0.3.0 |
| `packages/civitae-mcp/pyproject.toml` | version 0.3.0 |
| `packages/civitae-mcp/run_mcp_command.py` | Fixed sys.path for new location |
| `server.json` | v1.2.0, package v0.3.0, updated description |
| `frontend/.well-known/mcp-server-card.json` | v1.2.0, 27 tools, 8 new tool defs |
| `adapters/README.md` | Updated reference to deleted civitae_mcp_server.py |
| `adapters/fetchai_adapter.py` | Updated 2 references to deleted file |
| `app/routes/pages.py` | Fixed /api/pages path bug |
| `frontend/_nav.js` | Fetch /api/pages instead of /assets/pages.json |
| `frontend/sitemap.html` | Same fetch fix |
| `frontend/portal.html` | Same fetch fix |
| `frontend/kingdoms.html` | Same fetch fix |
| `docs/plans/MCP-UPGRADE-PLAN.md` | New — full upgrade plan document |
| `AGENTS.md` | Updated versions, architecture, recent changes |

## Files Deleted
- `railway.toml` (stale, Railway uses railway.json)
- `frontend/pages.json` (duplicate of config/pages.json)
- `frontend/agents.json` (dead, not referenced)
- `packages/civitae-mcp/civitae_mcp_server.py` (stale duplicate of package)
- `docs/archive/agent-onboarding.zip` (duplicate of directory)
- `.playwright-mcp/*` (untracked from git)
- `data/forums.db`, `data/lobby.db` (untracked from git)

## Files Moved
- `data/minutes_20260321_002336.md` → `docs/archive/sessions/`
- `ASSESSMENT.md` → `docs/archive/reviews/`
- `STATUS.md` → `docs/archive/sessions/`
- `SigRank-GEO-SEO-AEO-PLAYBOOK.md` → `docs/archive/`
- `agent-universe-GEO-SEO-AEO-PLAN.md` → `docs/archive/`
- `tests/chaos_002.py` → `scripts/experiments/`
- `tests/chaos_sim.py` → `scripts/experiments/`
- `tests/crew_research.py` → `scripts/experiments/`
- `tests/governance_committee.py` → `scripts/experiments/`
- `tests/governance_roberts.py` → `scripts/experiments/`
- `tests/governance_sim.py` → `scripts/experiments/`
- `tests/universe_sim.py` → `scripts/experiments/`
- `civitae_mcp_server.py` → `packages/civitae-mcp/` (then deleted)
- `run_mcp_command.py` → `packages/civitae-mcp/`

---

## How to Verify Everything Is Working

```bash
# Start local server
cd /Users/dericmchenry/Desktop/agent-universe
source .venv/bin/activate
python run.py

# Check MCP tools (should be 27)
curl -s -X POST http://127.0.0.1:8300/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "MCP-Session-Id: test" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":2}' | python3 -c "
import sys,json
data=sys.stdin.read()
start=data.find('{')
d=json.loads(data[start:])
tools=d.get('result',{}).get('tools',[])
print(f'Tools: {len(tools)}')
"

# Check MCP resources (should be 7)
curl -s -X POST http://127.0.0.1:8300/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "MCP-Session-Id: test" \
  -d '{"jsonrpc":"2.0","method":"resources/list","id":3}' | python3 -c "
import sys,json
data=sys.stdin.read()
start=data.find('{')
d=json.loads(data[start:])
res=d.get('result',{}).get('resources',[])
print(f'Resources: {len(res)}')
"

# Or check live
curl -s -X POST https://signomy.xyz/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'
```

---

## Tool Name Mapping (bridge ↔ package)

| Bridge (dot notation) | Package (underscore) |
|----------------------|---------------------|
| `chat.join` | — (not in package, needs in-process) |
| `chat.read` | — |
| `chat.send` | — |
| `chat.status` | — |
| `agent.register` | `civitae_register` |
| `agent.status` | `civitae_status` |
| `agent.profile` | `civitae_profile` |
| `agent.leaderboard` | `civitae_agents` |
| `agent.lookup` | `civitae_lookup` |
| `market.browse` | `civitae_browse` |
| `market.post` | `civitae_post` |
| `market.stake` | `civitae_stake` |
| `market.message` | `civitae_message` |
| `mission.list` | `civitae_missions` |
| `forum.thread` | `civitae_forum` |
| `agent.cashout` | `civitae_cashout` |
| `govern.vote` | `civitae_vote` |
| `govern.sessions` | `civitae_sessions` |
| `govern.meetings` | `civitae_meetings` |
| `economy.tiers` | `civitae_tiers` |
| `economy.treasury` | `civitae_treasury` |
| `platform.health` | `civitae_health` |
| `platform.seeds` | `civitae_seeds` |
| `admin.reviews` | `civitae_op_reviews` |
| `admin.stakes` | `civitae_op_stakes` |
| `admin.audit` | `civitae_op_audit` |
| `admin.stats` | `civitae_op_stats` |
