---
type: Runbook
title: Handoff — GTM2 to Next Agent — Glama scoring, SEO/GEO/AEO, repo maintenance
description: Full state of Signomy after GTM2 session. Covers Glama MCP scoring, SEO/GEO/AEO build, repo security audit, README rewrite, and pending items.
tags: [handoff, glama, seo, geo, aeo, mcp, maintenance]
timestamp: 2026-08-26T17:00:00Z
last_touched: 2026-08-26 17:00 UTC
---

# Handoff: GTM2 → Next Agent — Signomy Glama/SEO/Repo Maintenance

---
from: GTM2 (Devin)
to: Next Agent (any role)
when: 2026-08-26T17:00:00Z
topic: Signomy Glama scoring, SEO/GEO/AEO completion, repo security audit, README rewrite, email setup
status: ready-for-pickup
---

## Onboarding instructions for the next agent

### Step 1: Read these files first (in order)

1. `CLAUDE.md` — session coordination protocol, current build state
2. `AGENTS.md` — repo operating instructions, architecture, frozen invariants
3. `Devins_Plans/SCRATCHPAD.md` (tail) — cross-session bus
4. `Devins_Plans/state/ROSTER.md` — who's working on what
5. This handoff file — full state of GTM2 work
6. `docs/plans/IDEAS.md` — future ideas (civitae-cli TUI)

### Step 2: Log in

```bash
cd /Users/dericmchenry/Developer/_5_Signomy/1_agent-universe
bash scripts/set-role.sh <YOUR_ROLE>
bash scripts/status.sh
```

### Step 3: Check current state

```bash
git log --oneline -15          # see recent commits
git status                     # should be clean
bash scripts/lanes.sh          # cross-repo sync check
curl -s https://signomy.xyz/health   # production health
```

### Step 4: Understand the scope boundaries

- **Only modify this repo** (`agent-universe` / signomy.xyz)
- **Do NOT modify** mos2es.com, signalaf.com, sigeconomy.com
- **Do NOT touch** `frontend/sitemap-v2.xml` — it is canonical
- **Do NOT modify** the canonical sitemap under any circumstances

### Step 5: Check the Glama state

Glama's API and score page may still be stale. Check:
- https://glama.ai/mcp/servers/SunrisesIllNeverSee/agent-universe/score
- https://glama.ai/api/mcp/v1/servers/SunrisesIllNeverSee/agent-universe

If `spdxLicense` is still `null` and `tools` is still `[]`, Glama has not
resynced. This is a Glama-side backlog issue, not a repo issue. GitHub
correctly detects MIT. The repo is correct.

---

## What's done (GTM2 session, 2026-08-26)

### Glama MCP scoring (all repo-side work complete)

| Item | Commit | Status |
|------|--------|--------|
| Root LICENSE swapped to MIT | `451ebbf` | Done — GitHub detects MIT |
| glama.json description + license added | `81a370b` | Done |
| Dockerfile.glama fixed for uv sync | `a3bbe83` | Done |
| Tool docstrings improved (12 low-scoring tools) | `b55c5bf` | Done — v0.3.1 published |
| MCP annotations added (all 23 tools) | `1de55ec` | Done — v0.3.2 published |
| Glama card + score badges in README | `e39bcf2` | Done |
| License badge simplified to MIT only | `bca9181` | Done |
| Tool count corrected (27→23) in glama.json | `f233a4f` | Done |

### README rewrite (SigRank-style structure)

| Item | Commit | Status |
|------|--------|--------|
| Full README rewrite with TOC, ecosystem table, stack section | `2f788dd` | Done |
| Smithery badge fixed (shields.io replacement) | `b1a4e91` | Done |
| All 14 badge URLs verified 200 | — | Done |
| All ecosystem repo links verified 200 | — | Done |
| All live surface routes verified 200 | — | Done |
| MCP tool count verified (27 live, 23 PyPI) | — | Done |

### Repo security audit and maintenance

| Item | Commit | Status |
|------|--------|--------|
| Personal email removed from ai-plugin.json, openapi.json | `4634af8` | Done |
| Personal email removed from 6 docs | `4634af8` | Done |
| Personal name removed from AGENTS.md, system-devin, test-reports | `4634af8` | Done |
| Local machine paths removed from 8 docs | `4634af8` | Done |
| Patent serial numbers removed from docs | `4634af8` | Done |
| REPOREVIEW docs sanitized | `4634af8` | Done |
| `nuild_outs/` typo → `build_outs/` | `4634af8` | Done |
| Stray hash file removed from frontend | `4634af8` | Done |
| 145 SF crawl CSV/SVG files removed from git | `4634af8` | Done |
| Old 0.2.0 dist wheels removed from git | `4634af8` | Done |
| .gitignore hardened (dist/, node_modules/, caches, SF crawl) | `4634af8` | Done |
| civitae-cli TUI idea stored | `4634af8` | Done — `docs/plans/IDEAS.md` |

### SEO/GEO/AEO (completed in prior sessions, verified this session)

| Item | Status |
|------|--------|
| Comparison pages (/vs/okx-ai, /vs/virtuals-protocol, /vs/olas) | 200, live |
| Alternatives page (/alternatives/agent-ai) | 200, live |
| Concept page (/concepts/governed-marketplace) | 200, live |
| Guide page (/guides/how-to-register-an-agent) | 200, live |
| llms.txt + llms-full.txt | 200, live |
| sitemap-v2.xml (canonical, untouched) | 200, live |
| agent.json, .well-known/agent.json | 200, live |
| mcp-server-card.json | 200, live |
| openapi.json | 200, live |
| GSC connected, 0 sitemap errors, 19/20 indexed | Done |
| IndexNow (Yandex) — 25 URLs submitted | Done |
| Google Indexing API — 18 URLs accepted | Done |
| Zenodo ORCID linked, cross-links, community submissions | Done |

### Production health (verified 2026-08-26 17:00 UTC)

| Surface | URL | Status |
|---------|-----|--------|
| Main site | signomy.xyz | 200 |
| Health | signomy.xyz/health | 200 |
| MCP endpoint | signomy.xyz/mcp | 406 (needs POST, correct) |
| Agent manifest | signomy.xyz/agent.json | 200 |
| OpenAPI | signomy.xyz/openapi.json | 200 |
| llms.txt | signomy.xyz/llms.txt | 200 |
| llms-full.txt | signomy.xyz/llms-full.txt | 200 |
| Sitemap v2 | signomy.xyz/sitemap-v2.xml | 200 |

### Publishing

| Package | Version | Registry |
|---------|---------|----------|
| civitae-mcp | 0.3.2 | PyPI (5 versions: 0.1.0–0.3.2) |
| sigrank | 0.0.231 | npm (sister project) |

---

## What's needed (pending items, ordered by priority)

### 1. Email setup — `hello@signomy.xyz` (owner action, not agent)

The owner wants `hello@signomy.xyz` as a public contact email. The domain
uses Porkbun for DNS and Google Workspace for mail (MX → smtp.google.com).

**Owner must do this in Porkbun dashboard:**
1. Go to https://porkbun.com/account/domains
2. Click signomy.xyz → Email tab
3. Add forwarding: `hello` → (owner's existing inbox)
4. Optionally add `operator` forwarding if not already set up

**After owner confirms it works, the agent should:**
- Update README contact section: `operator@signomy.xyz` → `hello@signomy.xyz`
- Update `frontend/.well-known/ai-plugin.json` contact_email
- Update `frontend/openapi.json` contact email
- Keep `operator@signomy.xyz` for internal/Railway `OPERATOR_EMAIL` env var
- Split: `hello@` = public-facing, `operator@` = internal notifications

### 2. Glama re-sync (Glama-side, not repo-side)

Glama's API still shows:
- `spdxLicense: null` (should be MIT)
- `tools: []` (should be 23 tools)
- Description with stale `"Description\t"` prefix

This is a **known Glama backend backlog** (confirmed via GitHub issues
#4929, #7471, #4225 on punkpeye/awesome-mcp-servers). Multiple users
report sync stuck for hours/days. The Glama team says: "After backlog
is cleared, it should be a few minutes after new changes are detected."

**What to do:**
- Wait for Glama to process (could be hours to days)
- If still stuck after 48h, ping Glama on Discord: https://glama.ai/discord
- Ask them to manually trigger sync/rescan for `SunrisesIllNeverSee/agent-universe`
- Do NOT make further repo changes to "fix" Glama — the repo is correct

**Evidence the repo is correct:**
- GitHub API: `spdx_id: MIT` (confirmed)
- Root LICENSE: MIT (confirmed)
- glama.json: `"license": "MIT"` (confirmed)
- PyPI: civitae-mcp 0.3.2 with 23 annotated tools (confirmed)
- Live MCP: 27 tools, all working (confirmed)

### 3. Glama tool quality score (will improve after re-sync)

Current: C, 3.3/5 average, lowest 2.2/5 (stale — scoring v0.3.0)
Expected after re-sync: B+ to A (v0.3.2 has rich docstrings + annotations)

All 23 PyPI tools now have:
- Purpose clarity (what the tool does)
- Usage guidelines (when to use it, when to use siblings)
- Behavioral transparency (read-only/mutating, auth requirements, side effects)
- Parameter semantics (constraints, defaults, formats)
- Conciseness and structure
- Contextual completeness (content-fencing, operator requirements)

### 4. Related-server associations (optional, discoverability)

If the owner wants to optimize Glama discoverability, associate Signomy
with high-activity related servers through Glama's web UI:
- Agent Ready (322 stars, A quality)
- BasedAgents (64 stars, agent identity/reputation)
- viridis-agent-fleet (100 stars, C quality, B maintenance)
- agentic-os-mcp (A quality, A maintenance)

This affects discoverability, not Signomy's own score.

### 5. Future: civitae-cli TUI (post-Glama, post-SEO)

Documented in `docs/plans/IDEAS.md`. A Python TUI for operator/developer
workflows (status, browse, missions, reviews, audit, stakes). Not a
marketplace client — MCP and web console cover that. Build only after
Glama and SEO work is fully closed.

---

## Pickup files

Read these first to understand current state:

1. `README.md` — public-facing README (rewritten this session)
2. `glama.json` — Glama server metadata
3. `packages/civitae-mcp/pyproject.toml` — MCP package config
4. `server.json` — MCP server manifest
5. `Dockerfile.glama` — Glama build config
6. `docs/plans/IDEAS.md` — future TUI idea
7. `docs/seo-aeo-geo-build-package/MAINTENANCE_RUNBOOK_SIGNOMY.md` — SEO runbook
8. `docs/seo-aeo-geo-build-package/OWNER_ACTION_CHECKLIST.md` — owner TODOs
9. `.gitignore` — hardened this session

## Open questions

1. **Is `operator@signomy.xyz` actually configured?** The repo references it
   but we didn't verify the inbox exists. Owner needs to confirm in Porkbun
   or Google Workspace.

2. **Does the owner want `hello@signomy.xyz` or `hello@signomy.com`?** The
   domain is `signomy.xyz`. The owner said `.com` in the request but the
   site is `.xyz`. Assume `.xyz` unless corrected.

3. **Glama Discord escalation** — if Glama is still stale after 48h, does
   the owner want to ping them on Discord, or wait longer?

## Authority limits

### What the next agent CAN do without checking back

- Update README, docs, and frontend HTML for content/copy improvements
- Update badge URLs and verify links
- Fix typos, formatting, and documentation
- Update `hello@signomy.xyz` references after owner confirms email is set up
- Run tests, health checks, and verification commands
- Commit and push to `main` (Vercel auto-deploys frontend)

### What the next agent CANNOT do without checking back

- **Do NOT modify `frontend/sitemap-v2.xml`** — it is canonical
- **Do NOT modify mos2es.com or signalaf.com** — out of scope
- **Do NOT change the LICENSE** — it is MIT, GitHub detects it correctly
- **Do NOT change pricing constants or MO§ES™ governance rules**
- **Do NOT bump civitae-mcp version without owner approval**
- **Do NOT make further Glama API calls trying to force a sync** — the
  public API is read-only, there is no sync endpoint, and Glama's backend
  is the bottleneck
- **Do NOT edit files in `docs/archive/`** — provenance-preserving, per AGENTS.md
- **Do NOT create new root directories** without checking REPO.yaml

## Context

### The two MCP surfaces (do not conflate)

1. **Live remote endpoint** (`https://signomy.xyz/mcp`)
   - 27 tools (chat, marketplace, missions, governance, discovery, operator)
   - Streamable HTTP, FastMCP
   - Rich annotations, server instructions
   - This is what users and agents connect to

2. **PyPI package** (`civitae-mcp`, v0.3.2)
   - 23 tools (civitae_* naming)
   - stdio transport
   - This is what Glama scores and what Smithery/MCP Registry install

The two surfaces intentionally have different tool counts and naming. The
live endpoint is richer. The PyPI package is the distributable artifact.

### Glama scoring system (TDQS)

Glama's Tool Definition Quality Score evaluates:
- Purpose Clarity
- Usage Guidelines
- Behavioral Transparency
- Parameter Semantics
- Conciseness & Structure
- Contextual Completeness

Server-level score = mean + minimum tool score. The lowest-scoring tool
matters most. All 23 tools were upgraded with rich docstrings + annotations
in v0.3.2.

### Glama API key

A Glama API key was provided by the owner and tested. It works with
`Authorization: Bearer <key>` for the public metadata endpoint. No admin
API endpoints exist for sync/rescan/deploy/release. The key is not stored
in the repo and should not be committed or exposed.

### Broken post-commit hook

The repo has a broken post-commit hook that emits a warning on every commit:
```
.git/hooks/post-commit: line 3: exec: /Users/dericmchenry/Developer/built/agent-universe/scripts/hooks/post-commit.sh: cannot execute: No such file or directory
```
This is non-blocking. Commits succeed. The hook references an old path that
no longer exists. To fix: `bash scripts/install-hooks.sh` (reinstalls hooks
from the current repo location). Low priority.

### GTM2 session role

This session was "GTM2" — Go-To-Market phase 2. The focus was:
1. Fix Glama MCP scoring (license, tools, annotations, build)
2. Rewrite README to match SigRank quality
3. Security audit and repo maintenance
4. Document everything for handoff

### Commit history this session

```
fdfab9b feat(exchange): add Contribution Exchange discovery surfaces
4634af8 chore: repo maintenance — security audit, folder cleanup, .gitignore hardening
b1a4e91 fix: replace broken Smithery badge with shields.io badge
7fa4357 feat: add PostHog analytics to signomy.xyz
addbd38 fix(seo): improve title tags for CTR on high-impression pages
2f788dd docs: rewrite README with ecosystem table, TOC, and SigRank-style structure
f233a4f fix: correct tool count in glama.json description (27 → 23)
bca9181 fix: simplify license badge to MIT only
1de55ec fix(glama): add MCP tool annotations (readOnly/destructive/idempotent) to all 23 tools
f0bfdd1 fix(seo): remove redirect URLs from sitemap (GSC fixes)
```

### External URLs

| What | URL |
|------|-----|
| Live site | https://signomy.xyz |
| MCP endpoint | https://signomy.xyz/mcp |
| GitHub repo | https://github.com/SunrisesIllNeverSee/agent-universe |
| PyPI package | https://pypi.org/project/civitae-mcp/ |
| Glama server page | https://glama.ai/mcp/servers/SunrisesIllNeverSee/agent-universe |
| Glama score page | https://glama.ai/mcp/servers/SunrisesIllNeverSee/agent-universe/score |
| Glama API | https://glama.ai/api/mcp/v1/servers/SunrisesIllNeverSee/agent-universe |
| Smithery | https://smithery.ai/servers/burnmydays/civitae |
| AI Agents Directory | https://aiagentsdirectory.com/agent/signomy |
| Glama Discord | https://glama.ai/discord |

---

*Generated by GTM2 (Devin) on 2026-08-26. All work committed and pushed to main.*
