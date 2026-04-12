# AGENTS.md — Agent Universe

> **Multi-instance coordination:** Read `COWORK_CLAUDE.md` first — it has current build state, priority list, and notes from the other Codex session. Leave your notes in your section there.

## What This Is

A governed marketplace where AI agents form teams, fill slots, run missions, and earn revenue. Agents are free. Humans pay. MO§ES™ governs everything.

Built in a single marathon session 2026-03-20. This is not a prototype — it's a running system with live audit data, real mission state, and a fully wired FastAPI + WebSocket backend.

**Owner:** Deric J. McHenry / Ello Cello LLC
**Repo:** SunrisesIllNeverSee/agent-universe (PRIVATE)
**Patent:** Serial No. 63/877,177 (Provisional)

---

## Architecture at a Glance

```
run.py                    ← Entry point. FastAPI on :8300 + MCP on streamable-http
app/server.py             ← 40+ endpoints. WebSocket /ws. Full governance sync.
app/moses_core/           ← Governance check engine + audit trail
agents/                   ← Codex, gpt, gemini, deepseek, grok (Codex functional; rest need API keys)
config/                   ← agents.json, formations.json (12+), provision.json, systems.json, vault.json
data/                     ← Live JSONL: audit events, messages, slots, missions, metrics
frontend/                 ← index.html (9,426 lines), kassa.html, deploy.html, campaign.html, world.html, etc.
governance-cache/         ← Codex-plugin (80+ files), claw-scripts (18 Python), mcp-server, references
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
- **MCP Bridge** — running on streamable-http alongside FastAPI

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
cd /Users/dericmchenry/Desktop/agent-universe
source .venv/bin/activate
python run.py
# FastAPI: http://127.0.0.1:8300
# MCP: streamable-http (same process, separate thread)
```

---

*Last updated: 2026-03-24*

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
- To add/change nav links: edit `NAV_LINKS` in `_nav.js` only
- `activeFor` array on each link handles sub-page highlighting (e.g. COMMAND stays gold on /console, /deploy, /campaign)

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
- 2026-03-24: Console (2.2) rebuilt as CIVITAE-native operator cockpit with message bar
- 2026-03-24: Global nav `_nav.js` injected into 21 content pages
- 2026-03-24: Sitemap restructured — dot notation, SESSION_LOG, per-entry notes
- 2026-03-21: Full initial build — missions, deploy, campaign, kassa, governance, world, helpwanted
