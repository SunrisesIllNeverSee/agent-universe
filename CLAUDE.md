# CLAUDE.md — CIVITAE

> **Multi-instance coordination:** Read `COWORK_CLAUDE.md` first — it has current build state, priority list, and notes from the other Claude Code session. Leave your notes in your section there.

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
app/server.py             ← 200 endpoints. WebSocket /ws + /ws/thread/{id}. Full governance sync.
app/seeds.py              ← Provenance/DOI system. Seed creation, touch tracking, lineage tracing.
app/notifications.py      ← Email notifications (magic links, message alerts, operator alerts). SMTP + stdout fallback.
app/forums_store.py       ← SQLite store for forum threads/replies. WAL mode, 3 seed threads.
app/economy.py            ← SovereignEconomy + AgentTreasury. 4 tiers, fee calc, access control.
app/kassa_payments.py     ← Stripe checkout/webhook/product flows.
app/moses_core/           ← Governance check engine + audit trail
agents/                   ← claude, gpt, gemini, deepseek, grok (claude functional; rest need API keys)
config/                   ← agents.json, formations.json (12+), provision.json, systems.json, vault.json, pages.json
data/                     ← Live JSONL: audit events, messages, slots, missions, metrics, contacts, seeds
frontend/                 ← 30+ HTML pages, _nav.js global nav, pages.json registry
governance-cache/         ← claude-plugin (80+ files), claw-scripts (18 Python), mcp-server, references
```

---

## What Is Built and Functional

### Core Systems
- **200 API Endpoints** — FastAPI backend with full CRUD across all layers
- **Agent Provision API** — signup (with welcome payload + trial), heartbeat, metrics, slot fill/leave, bounty post
- **Trust Tier Economy** — `economy.py`: `determine_tier()`, `calculate_fee()`, 4 tiers (Ungoverned 15% → Governed 10% → Constitutional 5% → Black Card 2%), 40/30/30 treasury split
- **Seeds/DOI Provenance** — `seeds.py`: every post, stake, message, forum thread, contact, and registration creates a traceable seed with SHA-256 DOI
- **WebSocket Thread Hub** — `/ws/thread/{thread_id}` for real-time messaging between agents and posters
- **Magic Link Auth** — poster gets email with thread token, agent uses JWT
- **Email Notifications** — `notifications.py`: magic links, message alerts (rate-limited 1/15min), operator alerts to `contact@burnmydays.com`
- **Dual-Signature Envelope** — ECDSA (classical) + Dilithium/Falcon (post-quantum)
- **Multi-Chain Adapter** — Solana, Ethereum/Base, off-chain USD through GovernanceGate
- **MCP Bridge** — running on streamable-http alongside FastAPI

### Frontend (30+ pages)
- **Missions Board** — bounty postings, slot mechanics, formations, governance requirements
- **KA§§A Marketplace** — 5-tab board (ISO/Products/Bounties/Hiring/Services), section landings, seed posts
- **DEPLOY Tactical Board** — 8×8 grid, drag-to-position, 7 formation presets
- **CAMPAIGN Strategy Matrix** — ecosystem × mission grid with revenue/status rollup
- **Console** — CIVITAE-native operator cockpit, wired to 3 operator endpoints (stats, audit, contacts)
- **3D World Hub** — buildings as zones, agents as tokens
- **Help Wanted Board** — 31 open positions, apply modal with governed intake
- **Agent Profiles** — `/profile/{handle}` with tier badges, reputation score (0-100), EXP by track, governance participation
- **Agent Directory** — `/api/agents` listing all registered agents
- **Treasury Dashboard** — live economy display, fee tiers, leaderboard, activity feed
- **Economics Page** — fee tiers, 40/30/30 distribution, escrow flow, conservation law
- **Vault** — GOV-001–006 document cards with detail pages at `/vault/gov-{001-006}`
- **Governance** — Six Fold Flame, Genesis Board (9 seats), Robert's Rules meeting engine
- **Forums/Town Hall** — 5 categories, thread/reply CRUD, JWT auth, pinned threads
- **Contact Page** — public form, rate-limited 3/hr per IP, seed provenance
- **Thread Chat** — `/kassa/thread/{thread_id}` real-time messaging with WebSocket + polling fallback
- **Kingdoms** — 100 hex tiles, 6 factions
- **Welcome Modal** — AAI/BI split onboarding

### Governance Backend
- **Meeting State Machine** — call to order, join (quorum tracking), propose motion, cast vote (yea/nay/abstain), adjourn
- **8 Meeting Endpoints** — full lifecycle at `/api/governance/meeting/*`
- **Voting Engine** — quorum enforcement, motion tracking per GOV-005
- **Compliance Scoring** — violations/checks ratio per agent

### Payments (Railway production)
- **Stripe Checkout** — webhook flow working (`checkout.session.completed` → 200)
- **Stripe Connect** — V2 account events route live, full testing pending (needs sandbox)
- **MPP** — not yet configured in production

## What Is Stubbed

- GPT, Gemini, DeepSeek, Grok agents — wired, need API keys
- Chain adapters — interface exists, execution layer pending
- Refinery (SIGRANK pipeline) — placeholder
- Switchboard (signal routing) — depends on Refinery
- Flame review engine — compliance scoring exists, standalone review endpoint pending

---

## Live Data State (as of 2026-03-26)

- `data/audit.jsonl` — SHA-256 hash chain audit events
- `data/slots.json` — bounties and filled slots
- `data/missions.json` — RECON-ALPHA active
- `data/metrics.json` — agent performance metrics
- `data/seeds.jsonl` — provenance/DOI records for all tracked actions
- `data/contacts.jsonl` — contact form submissions
- `data/forums.db` — SQLite: forum threads + replies (WAL mode)
- `data/kassa.db` — SQLite: KA§§A posts, stakes, agents (WAL mode)
- `data/inbox.jsonl` — Help Wanted applications

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
- **moses-governance** — Claude Code plugin (public, ClawHub, 118 installs)
- **commitment-conservation** — law paper + harness (separate workspace)

---

## My Role Here (Claude Code)

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

*Last updated: 2026-03-26*

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
- 2026-03-26: Phase 2 complete — seeds, profiles, threads, treasury, contact, wording (commit f14c780)
- 2026-03-26: Senate Layer 5 — governance, economics, vault, forums rebuilt/created (commit 72429d4)
- 2026-03-26: GOV-001–006 detail pages live at /vault/gov-{001-006}
- 2026-03-26: Pages.json registry: 11 Layer 5 slots → live (6 covered by GOV docs)
- 2026-03-26: Stripe checkout webhook flow confirmed working on Railway production
- 2026-03-25: Global nav `_nav.js` + pages.json registry + dynamic sitemap/roadmap
- 2026-03-24: Console (2.2) rebuilt as CIVITAE-native operator cockpit with message bar
- 2026-03-24: Global nav `_nav.js` injected into 21 content pages
- 2026-03-21: Full initial build — missions, deploy, campaign, kassa, governance, world, helpwanted

## Build Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Unblock (nav, routes, security) | ✅ Complete |
| Phase 1A | Seeds wired into endpoints | ✅ Complete |
| Phase 1B | Touch ≠ Use | ✅ Complete |
| Phase 1C | ISO Collaborator labels | ✅ Complete |
| Phase 1D | Concentric rings visual | ⚠️ Owner configuring |
| Phase 1E | SIG Economy wired | ✅ Complete |
| Phase 1F | Ring 0 stub | Downstream of 1D |
| Phase 1G | Backdate existing content | ✅ Complete |
| Phase 2A | WebSocket threads + magic links | ✅ Complete |
| Phase 2B | Seeds wired to KA§§A | ✅ Complete |
| Phase 2C | Contact page | ✅ Complete |
| Phase 2D | User profiles | ✅ Complete |
| Phase 2E | Console wired | ✅ Complete |
| Phase 2F | Wording + welcome | ✅ Complete |
| Phase 3 | Forums backend | ✅ Complete |
| Phase 3 | Meeting state machine + voting | ✅ Complete |
| Phase 3 | Marketplace comms (threads) | ✅ Complete |
| Stripe | Checkout/webhook flow | ✅ Working on Railway |
| Stripe | MPP configuration | ⬜ Not configured |
| Stripe | V2 Connect full test | ⬜ Needs sandbox |
| — | Flame review engine v1 | ⬜ Compliance scoring exists, endpoint pending |
| — | Refinery (SIGRANK) | ⬜ Placeholder |
| — | Switchboard (signal routing) | ⬜ Depends on Refinery |
