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

**2026-03-23 (copilot/open-positions-for-agents session):**

Fixed the broken Apply flow in `helpwanted.html` so agents can actually submit applications:

1. **DOMContentLoaded patch** (`helpwanted.html` line ~1638): The condition `btn.href.includes('/api/provision/signup')` was wrong — all hardcoded buttons link to `/entry`. Changed to `if (btn)` so every Apply button in every `.job-card` gets patched to open the inline modal.

2. **`buildLiveCard` function** (`helpwanted.html` line ~1533): The dynamically-rendered slot cards from `/api/slots/open` created plain `<a href="/entry">` buttons. Updated to wire `onclick` → `openApply(slotId, slotTitle)` unless the slot has an explicit non-entry `apply_url`.

The inbox endpoints (`/api/inbox/apply`, `/api/inbox`, `/api/inbox/{id}/review`) and admin panel inbox view were already wired — no changes needed there.

The Three.js world (`frontend/world.html`) was already built with OrbitControls, agent tokens, and live slot polling — no changes needed there either.

