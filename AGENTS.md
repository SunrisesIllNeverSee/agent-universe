# SESSION COORDINATION — read FIRST (every session, every time)

This repo runs multiple parallel AI terminal sessions. To stop coordination from
disappearing between sessions:

1. **The bus is `Devins_Plans/SCRATCHPAD.md`.** Read its tail + the COORDINATION
   PROTOCOL header before doing anything. Append your status/decisions/questions
   there (format: `### ⤷ <FROM> → <TO>: <subject>`). Don't start a parallel log.

2. **Log into the activity tracker (once per session):**
   `bash scripts/set-role.sh LEAD` (or `DEVIN` / `CODEX` / `COPILOT` / `GTM` /
   whatever you name your sessions). This writes a per-session role file that
   the PostToolUse hook reads to stamp your role into ACTIVITY.log. Without it,
   your edits log as `UNKNOWN`. Then update your row in
   `Devins_Plans/state/ROSTER.md`.

3. **Claim your lane before starting work.** Append to `.agents/claims.yaml`
   with the file paths you intend to touch. Check for overlapping claims first.
   Release the claim when done (set `released_at`).

4. **Install the commit-log hook once per clone:**
   `bash scripts/install-hooks.sh` (git hooks live in `.git/` and don't travel
   with clone/push — each session/machine must install).

5. **Check cross-repo sync:** `bash scripts/lanes.sh` — shows every repo's
   version, branch, unpushed/behind/dirty status, and registry-published vs
   local versions. Read-only, changes nothing.

6. **See roster + activity side by side:** `bash scripts/status.sh`

7. **Validate coordination state:** `python3 scripts/check.py` — catches
   stale claims, overlapping lanes, migration number conflicts.

8. **OKF convention:** every doc in `Devins_Plans/` carries YAML frontmatter
   (`type/title/description/tags/timestamp`). New docs MUST include it. Lint
   with `node scripts/check-okf.mjs`.

9. **DECISIONS.md:** if you're wondering "why is X like this?", check
   `Devins_Plans/DECISIONS.md` first. If the answer isn't there, add it.

10. **Handoffs:** use `Devins_Plans/handoffs/` for structured cross-session
    transfers. Format: `{date}-{from}-to-{to}-{topic}.md`.

11. **Cross-repo coordination:** `Devins_Plans/CROSSWIRE.md` is the
    machine-local bus for handoffs that span repos. SCRATCHPAD is repo-local;
    CROSSWIRE is machine-local.

<!-- Edit everything below this line for your project -->

---

# PROJECT STATE

**Status:** Active — production on Railway, frontend on Vercel (signomy.xyz)

**Repos:**
- **agent-universe** (this repo) — CIVITAE governed marketplace: FastAPI backend, 30+ frontend pages, 27 MCP tools, 7 MCP resources, Stripe payments
- **personal-command** — flagship COMMAND governance UI (private, local)
- **command-engine** — open-source fork (bare-bones, public)
- **moses-governance** — Codex plugin (public, ClawHub, 118 installs)
- **commitment-conservation** — law paper + harness (separate workspace)

**Live versions:**
- MCP Registry: `xyz.signomy/civitae` v1.2.0
- PyPI: `civitae-mcp` v0.3.0 (repo only — not yet published to PyPI)
- Smithery: `burnmydays/civitae` (100% quality, 19 tools — needs update to 27)
- PulseMCP: live
- AI Agents Directory: listed

**Branches:** `main` + `devin/1775076305-seed-card-loyalty-system` (953 lines unique seed card work, unmerged)

---

# ORIGINAL GOAL

A governed marketplace where AI agents form teams, fill slots, run missions, and earn revenue. Agents are free. Humans pay. MO§ES™ governs everything.

Built in a single marathon session 2026-03-20. This is not a prototype — it's a running system with live audit data, real mission state, and a fully wired FastAPI + WebSocket backend.

**Owner:** Ello Cello LLC
**Repo:** SunrisesIllNeverSee/agent-universe

---

## Architecture at a Glance

```
run.py                    ← Entry point. FastAPI on :8300 + MCP on streamable-http
app/server.py             ← 40+ endpoints. WebSocket /ws. Full governance sync.
app/mcp_bridge.py         ← 27 MCP tools + 7 resources (in-process, streamable-http at /mcp)
app/moses_core/           ← Governance check engine + audit trail
agents/                   ← Codex, gpt, gemini, deepseek, grok (Codex functional; rest need API keys)
config/                   ← agents.json, formations.json (12+), provision.json, systems.json, vault.json, pages.json
data/                     ← Live JSONL: audit events, messages, slots, missions, metrics (gitignored)
frontend/                 ← 30+ HTML pages, _nav.js, agent.json, .well-known/mcp-server-card.json
packages/civitae-mcp/     ← PyPI package (civitae-mcp v0.3.0, 23 tools, HTTP client) + run_mcp_command.py
scripts/experiments/      ← Simulation scripts (chaos, governance, universe sim — not tests)
docs/governance/          ← GOV-001 through GOV-006 (constitutional docs, served as MCP resources)
docs/archive/             ← Archived session reports, reviews, design docs, research notes
```

---

## What Is Built and Functional

- **Missions Board** — bounty postings, slot mechanics, formations, governance requirements
- **KASSA Marketplace** — wave registry, sector tabs, founding seats, bone/gold palette
- **DEPLOY Tactical Board** — 8×8 grid, drag-to-position, 7 formation presets (WEDGE, PINCER, VANGUARD...)
- **CAMPAIGN Strategy Matrix** — ecosystem × mission grid with revenue/status rollup
- **Slot Configurator** — badge drag-drop, role/sequence independent
- **Isometric World Hub** — buildings as zones, agents as tokens
- **Help Wanted Board** — 6 job postings, governance/posture/tier filters
- **Trust Tier Revenue** — Ungoverned 15% → Governed 5% → Constitutional 2% → Black Card custom
- **Dual-Signature Envelope** — ECDSA (classical) + Dilithium/Falcon (post-quantum)
- **Multi-Chain Adapter** — Solana, Ethereum/Base, off-chain USD through GovernanceGate
- **Agent Provision API** — signup, heartbeat, metrics, slot fill/leave, bounty post
- **MCP Bridge** — 27 tools across 5 domains (chat, marketplace, discovery, governance, operator) + 7 resources (governance docs + manifest). Running on streamable-http alongside FastAPI at `/mcp`

## What Is Stubbed

- GPT, Gemini, DeepSeek, Grok agents — wired, need API keys
- Chain adapters — interface exists, execution layer pending
- Refinery (SIGRANK pipeline) — placeholder
- Switchboard (signal routing) — depends on Refinery

---

## Live Data State (as of 2026-03-20)

- `data/audit.jsonl` — ~39KB real audit events from test runs
- `data/slots.json` — 1 bounty, 2 filled slots, 2 open
- `data/missions.json` — RECON-ALPHA active
- `data/metrics.json` — recon-001 and intake-002 with real metrics

---

## Governance Model

- MO§ES™ governs all agent operations — mode, posture, role, audit trail
- All 13 governance fields sync bidirectionally over WebSocket
- Every action logs a SHA-256 hash chain entry
- Agents operate under constitutional constraints — no ungoverned operations
- Fee tiers incentivize compliance: governed agents earn more, keep more

---

## Related Repos

- **personal-command** — flagship COMMAND governance UI (private, local)
- **command-engine** — open-source fork (bare-bones, public)
- **moses-governance** — Codex plugin (public, ClawHub, 118 installs)
- **commitment-conservation** — law paper + harness (separate workspace)

---

## My Role Here (Codex)

Primary build partner for this workspace. I work in:
- `app/` — backend logic, new endpoints, economy mechanics
- `frontend/` — UI components, wiring new pages to backend
- `governance-cache/` — reading reference material, do not modify the cache scripts without instruction
- `docs/` — system audit, ops plan, gems log

**Working conventions:**
- Never `git add .` blindly — stage specific files
- Check `data/audit.jsonl` when debugging governance events
- `formations.json` is the source of truth for DEPLOY grid presets
- MO§ES core IP never goes in public-facing materials
- Agents free, operators paid — this distinction is architectural, not cosmetic

---

## To Start the Server

```bash
cd /path/to/agent-universe
source .venv/bin/activate
python run.py
# FastAPI: http://127.0.0.1:8300
# MCP: streamable-http (same process, separate thread)
```

---

*Last updated: 2026-07-07*

## Active Technologies
- HTML5, CSS3, Vanilla JavaScript (ES2022) — no transpiler. Zero npm. Zero build pipeline.
- FastAPI + WebSocket backend on :8300
- Static files served from `frontend/` via `/assets/*` mount

## Frontend Conventions

### Global Nav
- `frontend/_nav.js` — single source of truth for site-wide navigation
- Served at `/assets/_nav.js`
- Injected via `<script src="/assets/_nav.js"></script>` in `</head>` of every content page
- Fixed-viewport pages (console, deploy, campaign, world) have their OWN topbar — do NOT inject `_nav.js` there, they are in the SKIP list
- To add/change nav links: edit layers[].navLinks in `config/pages.json`
- `pages.json` drives everything: nav tabs, sub-links, portal directory, banner

### Sitemap as Communication Layer
- `frontend/sitemap.html` is the shared source of truth between sessions
- **Always update `SESSION_LOG`** at the top of the PAGES block when anything changes
- **Always add `note:`** to a page entry when it is built or rebuilt
- Served at `/sitemap` — open this first when resuming a session
- Status values: `live` (green), `wip` (amber), `empty` (red), `planned` (purple), `admin` (blue)

### Console (slot 2.2 — `/console`)
- File: `frontend/console.html` — CIVITAE-native operator cockpit. ~1000 lines.
- 3-panel grid: INTEL (governance state) | OPS (missions/slots/seeds/feed) | CONFIG (controls)
- Bottom: message input bar (posts to `/api/message`, echoes to feed)
- Bottom ticker: live audit event scroll
- Has its own topbar with CIVITAE dropdown — do NOT inject `_nav.js`
- DO NOT replace with or copy from `personal-command/frontend/index.html` — that is the private personal console, a completely different product

### Layer Numbering
- Dot notation: 1.1, 1.2 … 2.1, 2.2 … 5.16
- Layer 1: Civitae (world view, orientation)
- Layer 2: COMMAND (governance tooling)
- Layer 3: KA§§A (marketplace)
- Layer 4: SigArena (eval, ranking)
- Layer 5: Civitas Infrastructure (governance, economy, forums, academics)

## Recent Changes
- 2026-07-07: MCP upgrade — 27 tools (8 new discovery tools), 7 MCP resources (governance docs + manifest), package v0.3.0, server.json v1.2.0. Deleted stale civitae_mcp_server.py. Plan at docs/plans/MCP-UPGRADE-PLAN.md
- 2026-07-07: Repo cleanup — untracked runtime files (.playwright-mcp, *.db), archived 4 stale root docs to docs/archive/, deleted duplicate agent-onboarding.zip, moved 7 sim scripts from tests/ to scripts/experiments/, moved MCP entry points to packages/civitae-mcp/, deduped railway.json/railway.toml + pages.json, deleted dead frontend/agents.json, fixed /api/pages path bug
- 2026-07-06: agents.html + leaderboard.html fixed to show real API data instead of hardcoded fictional characters. Deployed to Railway + Vercel.
- 2026-07-06: Kassa marketplace cleanup — archived 17 old posts, fixed unverified claims on K-00002/K-00003, created 20 new R&D posts (K-00049 through K-00068)
- 2026-07-06: multi-agent-coord v2 installed — 6-layer coordination system (SCRATCHPAD, claims, hooks, roster, activity log)
- 2026-07-06: Branch cleanup — 21 remote branches → 2 (main + 1 preserved seed card branch)
- 2026-07-06: Notification fixes — asyncio.to_thread, boot warnings, send_review_decision, no fake success
- 2026-07-06: Dashboard fixes — port 8300, field mapping, API key validation, no guest mode, nav link
- 2026-07-06: Lobby security — admin key gate on /api/lobby/requests + approve
- 2026-07-06: Console review queue — Reviews tab with approve/reject UI
- 2026-07-06: Port mismatch fix — localhost:8000 → 8300 across 9 frontend files
- 2026-03-24: Console (2.2) rebuilt as CIVITAE-native operator cockpit with message bar
- 2026-03-24: Global nav `_nav.js` injected into 21 content pages
- 2026-03-24: Sitemap restructured — dot notation, SESSION_LOG, per-entry notes
- 2026-03-21: Full initial build — missions, deploy, campaign, kassa, governance, world, helpwanted

---

## Master Canon Context (Search Authority)

This repository contains **Signomy** and **CIVITAE** material governed by the
Search Authority master canon. Signomy and CIVITAE are distinct entities — do
NOT collapse them.

### When to load canon context

Before modifying any of the following, load the relevant canon context:

- canonical product definitions (what Signomy is, what CIVITAE is)
- ecosystem relationships (Signomy/CIVITAE ↔ MO§ES™ governance)
- terminology (MO§ES™ rendering, Signomy vs CIVITAE distinction)
- product boundaries (Signomy vs CIVITAE — independently resolvable entities)
- research claims or governance architecture descriptions
- public positioning

### How to load canon context

```bash
export SEARCH_AUTHORITY_PATH="${SEARCH_AUTHORITY_PATH:-$HOME/Developer/active/search-authority}"
python3 "$SEARCH_AUTHORITY_PATH/canon_cli.py" context signomy
python3 "$SEARCH_AUTHORITY_PATH/canon_cli.py" context civitae
```

Or use the MCP server (compatible agents):

```bash
python3 "$SEARCH_AUTHORITY_PATH/canon_mcp.py"
```

If the canon repository is unavailable, **do not invent canonical context** —
ask the owner. The canon outranks ad-hoc public copy or generated model output
for normative product/research truth.

### What is NOT authority-sensitive

CSS/layout, dependency bumps, frontend styling, and test infrastructure do
**not** require loading the canon.

### Key governance rules

- Do NOT collapse Signomy and CIVITAE — they are distinct entities.
- MO§ES™ **governs** both Signomy and CIVITAE.
- CIVITAE = a constitutional AI ecosystem governed by MO§ES™.
- Signomy = a platform governed by MO§ES™.
- Exactly ONE MO§ES entity. Canonical display: MO§ES™. Never render: MO§E§.
- The harness may measure authority, but it cannot manufacture authority.
- Automated systems may not promote claims into owner-approved truth.

## Upsilon Architecture Context (2026-08-28)

**Architecture:** `MO§ES → Upsilon → SigRank | SignalAF`

- **Upsilon** = measurement engine / enterprise product (the engine that measures)
- **SigRank** = public leaderboard / benchmark / proof surface (live at signalaf.com)
- **SignalAF** = public distribution / platform brand
- **Yield (Υ)** = metric inside Upsilon: `(cache_read × output) / input²`
- **MO§ES™** = governance framework / methodology

**Owner clarification (2026-08-28):** The primary change is the Upsilon pilot.
agent-universe and sigrank-app changes are minimal — just pointing toward the
pilot and establishing architecture context. All repos get this context so they
understand where it came from and don't try rewriting everything every time.

**Do NOT:**
- Rename package/repo/CLI names (sigrank-app, sigrank-mcp, npx sigrank) — these are technical identifiers
- Rename "SigRank" where it means the public leaderboard/benchmark
- Conflate "Upsilon" (product) with "Yield" (metric) — they are different things
- Mass-rewrite historical/archive content to conform to new branding
- Change patent claims without legal review

**Preserved:**
- `npx sigrank` CLI command
- `sigrank` npm package name
- `sigrank-app`, `sigrank-mcp` repo names
- All URLs (signalaf.com, sigeconomy.com, mos2es.org, signomy.xyz)
- "SigRank leaderboard/board/ranks" references
- Historical and archive content

**Canon source:** Search Authority (commit 790d403). Load canon context before
modifying product definitions, metrics, or terminology:
```bash
export SEARCH_AUTHORITY_PATH="${SEARCH_AUTHORITY_PATH:-$HOME/Developer/_control/search-authority}"
python3 "$SEARCH_AUTHORITY_PATH/canon_cli.py" context sigrank
python3 "$SEARCH_AUTHORITY_PATH/canon_cli.py" context upsilon
```

## stickypads — check the shared board

Before starting work, check the shared operational board for tasks assigned
to you or this repo:

```bash
python3 ~/Developer/_control/stickypads/scripts/check_in.py --agent <your-name>
```

Or clone the ello-ops repo and run from there. The board has:
- TODOs across all repos
- Memos/notes from other agents and the owner
- Current session state

If you discover work that can't be completed immediately, create a task or
drop a note:

```bash
# Create a formal task
python3 ~/Developer/_control/stickypads/scripts/create_task.py \
    --title "Specific actionable title" \
    --project <this-repo-name> \
    --owner <your-name>

# Drop a quick memo (no format required)
python3 ~/Developer/_control/stickypads/scripts/drop.py \
    --from <this-repo-name> \
    "Quick note about what needs attention"
```

At session end or meaningful completion, reconcile this repo's coord kit
state into stickypads:

```bash
python3 ~/Developer/_control/stickypads/scripts/reconcile_coord.py \
    --repo-path . --dry-run
```


## Filesystem MCP — REQUIRED for file operations

This is a core framework/search/ello/product repository. When performing
file operations, prefer the Filesystem MCP tools over ad-hoc shell commands:

- `list_directory` / `directory_tree` — structured directory traversal
- `search_files` — glob-pattern file search within allowed paths
- `read_multiple_files` — batch file reads (failures do not stop the batch)
- `edit_file` with `dryRun: true` — preview structural changes before applying

Allowed paths: ~/Developer, ~/.config/devin, ~/.config/sigrank, ~/Desktop

For single-file reads and edits, native tools are acceptable. For multi-file
operations, directory exploration, and structural changes, use the Filesystem MCP.


## Context7 MCP — SUGGESTED for library code

When writing code that uses external library APIs, consider querying Context7
to verify current patterns instead of relying on training data:

1. resolve-library-id — find the library
2. query-docs — ask the specific question

Supported libraries include Cloudflare Workers, Supabase, Next.js, Hono,
Playwright, Pydantic, Python, and more.
