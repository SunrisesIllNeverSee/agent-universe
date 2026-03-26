# COWORK_CLAUDE.md — Multi-Instance Coordination Brief
> **For:** Any Claude Code instance opening this workspace
> **Written by:** Claude Code (Grok_Agent session) — 2026-03-20
> **Protocol:** Read this before touching anything. Leave notes in your section at the bottom.

---

## What This Is

A governed AI agent marketplace. Agents are free. Humans pay. MO§ES™ governs everything.

- **Backend:** FastAPI on :8300 + MCP on streamable-http (:8200)
- **Frontend:** 14 HTML pages, pure HTML/CSS/JS, no build step
- **Governance:** SHA-256 hash chain audit trail, 8 modes, posture controls
- **Economy:** 4 trust tiers (Ungoverned 15% → Constitutional 2% → Black Card custom)
- **Start server:** `cd /Users/dericmchenry/Desktop/agent-universe && source .venv/bin/activate && python run.py`

---

## Current State (as of 2026-03-20)

### What's Built and Working
- All 14 frontend pages render and connect to live API
- 45+ API endpoints functional
- Governance state machine (mode/posture/role) fully wired
- Audit chain live (SHA-256, ~2,600 events in data/audit.jsonl)
- Trust tier economy complete
- Slot fill/leave mechanics working
- Claude agent functional (needs `ANTHROPIC_API_KEY`)
- MCP bridge operational
- Help Wanted board with 6 job postings
- Admin panel (Hange's panel at `/admin`)
- **NEW: Inbox system** — `POST /api/inbox/apply`, `GET /api/inbox`, `POST /api/inbox/{id}/review`
- **NEW: Apply modal** — helpwanted.html apply buttons now open a governed intake form

### What's Stubbed
- GPT, Gemini, Grok, DeepSeek agents (wired, need API keys)
- Refinery (SIGRANK pipeline) — placeholder UI, no backend
- Switchboard (signal routing) — depends on Refinery
- Chain adapters — governance gates work, execution layer pending

### Known Issues
- `data/slots.json` is 49MB — 2,500+ stress test records never archived. Needs cleanup before any deploy.
- 10 commits ahead of origin/main — not pushed yet
- WebSocket no auto-reconnect in frontend (low priority)
- MCP port (8200) hardcoded — make env-configurable eventually

---

## Priority Build List (24-hour target: UP AND RUNNING)

### P0 — Do These First
1. **Archive `data/slots.json`** — move test records to `data/archive/slots_stress_test.jsonl`, reset slots.json to `[]`. 49MB is a deployment blocker.
2. **Push to origin** — 10 commits ready, Railway config exists, just needs a push

### P1 — Core Feature Work
3. **Three.js world** — replace `frontend/world.html` CSS 2.5D isometric with real Three.js 3D. Same zones: COMMAND Tower, KASSA Marketplace, Bounty Board, DEPLOY Ops Floor, Scoreboard, Vault. Agent tokens animate across terrain in real time as slots fill. Buildings pulse with governance state (gold = constitutional, green = governed, gray = ungoverned). This is the flagship visual.
4. **Admin inbox panel** — wire `GET /api/inbox` into `frontend/admin.html`. Show pending applications with approve/reject/contact buttons that call `POST /api/inbox/{id}/review`.
5. **Live slot tokens in world** — fetch `/api/slots` on interval, place agent tokens at correct building zones based on current slot assignments

### P2 — Polish
6. **WebSocket auto-reconnect** — add exponential backoff in all frontend pages
7. **Refinery stub** — even a basic SNR scoring display would unlock the UI
8. **Environment config** — MCP port from env var, not hardcoded

### P3 — Stretch
9. **Wallet hookup** — chain adapters interface exists at `app/chains.py`. Solana and ETH/Base adapters need execution layer.
10. **Multi-agent activation** — once API keys are set, run 2-3 agents simultaneously through the full lifecycle

---

## Architecture Landmarks

```
run.py                    ← start here. FastAPI :8300 + MCP thread
app/server.py             ← 1,426 lines. All endpoints. WebSocket /ws.
app/economy.py            ← SovereignEconomy + AgentTreasury. 4 tiers.
app/chains.py             ← GovernanceGate + Solana/ETH/OffChain adapters
app/moses_core/           ← Governance check engine
agents/claude_agent.py    ← Only functional agent. Others stubbed.
config/formations.json    ← 12 formation presets (source of truth for DEPLOY)
data/audit.jsonl          ← Append-only SHA-256 chain. Never truncate.
data/inbox.jsonl          ← NEW. Application submissions from Help Wanted.
frontend/world.html       ← Current CSS 2.5D. Target: Three.js rebuild.
frontend/civitas.html     ← Isometric city hub (marketing/landing style)
frontend/admin.html       ← Hange's panel. Add inbox view here.
```

---

## What I've Done This Session (Grok_Agent Claude)
- Created `CLAUDE.md` with full workspace briefing
- Created `roster/MASTER_ROSTER.md` — 33 personas, activation leaderboard, tier breakdowns
- Created `roster/GEM_CATALOG.md` — 1,186 gems from GPT archive, ranked by weight
- Added inbox endpoints to `app/server.py` (`/api/inbox/apply`, `/api/inbox`, `/api/inbox/{id}/review`)
- Updated `frontend/helpwanted.html` — apply buttons now open governed intake modal, submissions POST to inbox
- Inbox data persists to `data/inbox.jsonl`, emits WebSocket `inbox_application` event

---

## Coordination Protocol

**One-writer rule:** Each Claude Code instance owns its section below. Don't overwrite each other's notes.

**Handoff signal:** When you finish a task, add it to "What I've Done" above AND note it in your section.

**Never:**
- `git add .` — stage specific files only
- Truncate `data/audit.jsonl` — it's the constitutional record
- Modify `governance-cache/` scripts without instruction
- Expose MO§ES core IP in public-facing materials

---

## Notes — Grok_Agent Claude

**2026-03-20:**
Working across two workspaces simultaneously. My primary workspace is `/Desktop/Grok_Agent` (law paper + system coordination). This workspace is the commercial layer.

The Three.js world is the right next move. The current CSS 2.5D is a solid foundation for the zone layout but it's not the vision. Three.js with:
- Perspective camera, orbitable
- Buildings as actual 3D meshes, not CSS boxes
- Agent tokens as glowing spheres or low-poly characters
- Real-time slot state driving token positions
- Governance tier reflected in building color/glow
- Fog of war as trust unlocks — buildings appear as trust increases

The inbox is wired. Hand off the admin panel integration to agent-universe Claude.

---

## Notes — Agent-Universe Claude

**2026-03-25:**

### What I built this session
- Created `config/pages.json` — single source of truth for all layer/page/nav data
- Added `GET /api/pages` endpoint to server.py
- Built `frontend/_nav.js` — global nav injected into all 21 content pages, fetches from API
- Rewrote `sitemap.html` — now dynamic from /api/pages, collapsible layer sections
- Rewrote `civitae-roadmap.html` — fully dynamic including Operator Tools / Inactive extras
- Committed: `8443e7a`

### Master build plan (saved to memory)
See: `/Users/dericmchenry/.claude/projects/-Users-dericmchenry-Desktop-CIVITAE/memory/project_build_phases.md`

North star: "Deploy. Wire Stripe. Pay the first agent. Then watch what happens."
Core loop: Register → Fill Slot → Earn → Cash Out → Repeat

Phase 0 (unblock): unified header, route collision /products, security basics
Phase 1 (launch identity): Seeds+Hash/DOI, ISO Collaborator, Concentric Rings, SIG Economy, Ring 0
Phase 2 (pages): Layer 1 wording, Console (2.2), Welcome Package, KA§§A wired
Phase 3 (connective): Forums, Payments/Stripe, Marketplace comms, User profiles
Future 12: Kettle Black, Farmland Rotation, Academy A-B-C, Hub Blooming, Smart contracts...

### Context
Full review/vision session documented in `docs/found.md` — includes xopilot review,
Grok vision (Ring 0, Academy, Kettle Black, ISO Collaborator), and the two-build framing.
Vanilla stack stays — no Next.js migration.

**2026-03-26 (Codex session):**
- Traced Stripe webhook failures in the normal `CIVITAE` workspace rather than `CIVITAE CODEX`.
- Confirmed `/api/connect/webhooks` is for V2 thin connected-account events only, while `checkout.session.completed` should hit `/api/kassa/webhooks/stripe`.
- Patched the admin-key middleware allowlist in `app/server.py` so `/api/kassa/webhooks/stripe` is publicly reachable and can rely on Stripe signature verification inside the webhook handler instead of being blocked with HTTP 403 first.
- Linked Railway CLI to the production `agent-universe` service and inspected the live container.
- Confirmed the deployed service had Stripe secrets set, but Railway was launching outside `/opt/venv` and the installed `stripe==15.0.0` SDK does not expose `StripeClient`.
- Patched `railway.json` to start with `/opt/venv/bin/python -m uvicorn ...` and updated `app/kassa_payments.py` so checkout/product/webhook V1 flows work with the installed Stripe SDK while V2 account endpoints fail explicitly unless `StripeClient` is available.
- Verified `checkout.session.completed` now succeeds end to end with HTTP 200 on `/api/kassa/webhooks/stripe`.
- Checked the V2 Connect path: `/api/connect/webhooks` is live and rejects unsigned probes with HTTP 400 as expected, but full Accounts V2 event testing is still blocked by Stripe because the current account is in test mode rather than a Stripe sandbox.
