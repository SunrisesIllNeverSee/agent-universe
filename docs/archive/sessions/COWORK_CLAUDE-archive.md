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

**2026-03-26 (Senate Layer 5 session):**
Executed the full `mossy-inventing-tower` plan. All 10 steps complete. Commit: `72429d4`.

### What was built
- `app/forums_store.py` (NEW) — SQLite store (WAL mode, threading.Lock), `forum_threads` + `forum_replies` tables, 3 seed threads written on empty DB: Genesis Board (pinned), Flame Q&A, PROP-DRAFT-001
- `app/server.py` — 6 new forum endpoints: GET /api/forums/threads (paginated, filterable by category), GET /api/forums/threads/{id} (+ replies), POST threads (KASSA JWT), POST replies (KASSA JWT), PATCH pin/lock (admin key); GET /forums page route
- `frontend/governance.html` — replaced 1013-line Share-Tech-Mono terminal design. DM Sans dark theme, Six Fold Flame 6-card animated grid, Genesis Board 9 vacant seats, Robert's Rules meeting engine (call to order / join / propose / adjourn), live session log
- `frontend/economics.html` — replaced WIP (had internal competitive analysis exposed). Pure static: treasury hero 4-card row, fee tiers by trust tier (Ungoverned 15%→Governed 10%→Constitutional 5%→Black Card 2%), 40/30/30 distribution, 5-step escrow flow, SigRank tiers, conservation law C(T(S))=C(S), platform rules
- `frontend/vault.html` — replaced 167-line stub. GOV-001–006 document cards (DRAFT badge, 6/6 Flame, v1.0), Six Fold Flame origin block with 8 AI signatories, session archive empty state, sealed protocols section
- `frontend/forums.html` (NEW) — Town Hall page. Category tabs (general/proposals/governance_qa/mission_reports/iso_collab), thread list from fetch, pinned thread highlight, new thread modal with JWT auth. All DOM built with createElement/textContent (no innerHTML — security hook compliance)
- `frontend/pages.json` + `config/pages.json` — 5.1 live (note added), 5.5 wip→live, 5.7 empty→live, 5.9 planned→live (file="forums"), Forums added to Layer 5 navLinks
- `frontend/sitemap.html` — SESSION_LOG entry added

### Known issues / handoff notes
- `/vault/gov-001` through `/vault/gov-006` still 404 — Vault cards link to these but detail routes not built yet. High-value next step.
- Forums require KASSA JWT to post — the auth flow to acquire a token (agent login via `/api/kassa/auth/login`) isn't surfaced to new visitors. Needs onboarding path.
- Genesis Board 9 seats on governance.html are static renders — joining is visual only, no persistence endpoint yet.
- All JS in the 4 new pages uses createElement/textContent exclusively (security hook blocks innerHTML with variable interpolation). Keep this pattern for any new dynamic pages.

**2026-03-26 (Session continued — Treasury + Seeds + Contact):**

### What was built
- `frontend/treasury.html` (NEW) — Live dashboard fetching from `/api/treasury` + `/api/economy/leaderboard`. Hero row (net balance, fees, earnings, bounties), 8 Economic Flows grid (4 active, 4 planned), fee rate table, agent leaderboard top 15, recent activity feed, trial economy lifecycle cards.
- `app/server.py` — `GET /treasury` route, `treasury` added to `_ALLOWED_PAGES`
- `app/seeds.py` (NEW) — Provenance & DOI system. `create_seed()` for any endpoint, `record_touch()` for lightweight views, `trace_lineage()` for backward chain, `backdate_gov_documents()` for retroactive GOV-001–006 DOIs. JSONL storage with file locking. FastAPI router at `/api/seeds` with query/stats/lookup/lineage/backdate endpoints.
- `app/server.py` — `seed_router` wired at `/api/seeds`, `backdate_gov_documents()` runs on startup (idempotent), seeds wired into forum thread creation (`forum_thread` seed) and reply creation (`forum_reply` seed)
- `frontend/contact.html` (NEW) — Public contact form. Name/email/subject dropdown (General, Partnership, Press, Investment, Genesis Board, Other)/message. POSTs to `/api/contact`. Rate limited 3/hr per IP. Each submission creates a `contact` seed for provenance.
- `app/server.py` — `GET /contact` route, `POST /api/contact` endpoint, IP rate limiter, `contacts.jsonl` storage, `contact` added to `_ALLOWED_PAGES`
- `frontend/pages.json` + `config/pages.json` — Treasury 5.6 → live, Contact 1.7 → live (new entry), 6 Layer 5 slots mapped to GOV docs (5.2, 5.3, 5.4, 5.8, 5.10, 5.11 all → live)

### Phase 2 plan received
- DOC 01.2 Phase 2 build plan loaded (2A–2F). Seeds integration (2B foundation) and Contact page (2C) completed this session.

**2026-03-26 (Phase 2 completion session):**

### Phase 2D/2E/2F — delivered via parallel agents
- `frontend/agent-profile.html` (NEW) — API-driven agent profile at `/profile/{handle}`. Tier badges, reputation score (0-100 composite), missions, stakes, capabilities, EXP by track, governance participation. Responsive layout.
- `app/server.py` — `GET /api/agents` directory listing, `GET /api/agents/{handle}` full public profile with tier/reputation/EXP, `GET /profile/{handle}` page route
- `app/server.py` — 3 operator endpoints: `GET /api/operator/stats`, `GET /api/operator/audit`, `GET /api/operator/contacts`. Console.html wired to fetch real data.
- Welcome payload on `/api/provision/signup` — tier, trial info (5 missions, 30 days, 0% fee), navigation links, registration seed
- "Agent Universe" → "CIVITAE" in 5 frontend files, "CIVITAS" → "CIVITAE" in kingdoms.html (6 occurrences), AAI label corrected in forums.html

### Phase 2A — WebSocket Threads + Magic Links (the backbone)
- `app/notifications.py` (NEW) — Email notification module. SMTP-based with env var config (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`). Falls back to stdout logging when SMTP not configured. Three functions: `send_magic_link()`, `send_message_notification()` (rate-limited 1/15min per thread), `send_operator_alert()`. Operator email: `contact@burnmydays.com` default.
- `app/server.py` — `ThreadHub` class for per-thread WebSocket connections. `/ws/thread/{thread_id}` endpoint with JWT or magic token auth, typing indicators, auto-cleanup on disconnect.
- `app/server.py` — `GET /api/operator/threads` endpoint (admin-key protected), returns all threads sorted by update time.
- `app/server.py` — Seeds wired into stake (thread creation seed) and message posting (message seed). Email notifications wired: magic link on stake, message notification on agent reply, operator alert on new stake.
- `frontend/kassa-thread.html` (NEW) — Thread chat page. Poster access via magic link, agent access via JWT. WebSocket real-time with polling fallback. Message list with sender alignment (agent right, poster left), connection indicator, typing state, thread close state. All DOM via createElement/textContent.
- Route count: 200 (up from 198)

### Phase 2 status
All 6 sub-phases complete:
- 2A: WebSocket threads + magic links ✅
- 2B: Seeds wired to KA§§A ✅
- 2C: Contact page ✅
- 2D: Agent profiles ✅
- 2E: Console wired ✅
- 2F: Wording + Welcome ✅

**2026-04-01 (Railway persistence + JWT hardening):**
- Pushed rollback checkpoint tag before Railway persistence changes: `pre-railway-fix-20260401-131918`
- Canonicalized runtime persistence to Railway volume mount `/app/data`; detached legacy `/data` mount from active service wiring
- Added shared JWT secret resolver so `app/server.py`, `app/routes/kassa.py`, and `app/routes/agents.py` all use one secret source
- Resolver now prefers `KASSA_JWT_SECRET`, falls back to `JWT_SECRET`, and only generates one cached ephemeral secret per process if neither env var exists
- Added focused unit coverage for JWT secret fallback/cache behavior and verified `/health` returns `200 OK` on Railway deployment `d6f24b00-2e76-483d-8897-1c076906cb04`

**2026-04-04 (Codex session — lobby design only):**
- Added canonical lobby design brief at `docs/VELVET-ROPE-LOBBY-DESIGN.md`
- This is design-only, not implementation. It locks the CIVITAE velvet-rope model:
  - public front door stays public
  - `/join` remains intake/waitlist origin
  - `/lobby` is the approved-user waiting room
  - `100` active inside-platform users max
  - `1 hour` hard session window
  - FIFO queue
  - timeout removes active access, not user data

**2026-04-04 (Codex session — tile color design):**
- Added canonical tile color design brief at `docs/TILE-LAYER-COLOR-DESIGN.md`
- This locks the visual logic for the color-coded CIVITAE map:
  - layer color is primary
  - faction color becomes secondary
  - Tile Zero = gold, Layer 1 = green family, Layer 2 = blue family, Layer 3 = violet
  - load/heat is a secondary overlay, not the base identity
