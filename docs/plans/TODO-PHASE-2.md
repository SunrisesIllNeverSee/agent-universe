# CIVITAE — Phase 2 To-Do (Path to Real Money)

> Status as of 2026-03-23. All Phase 1 infrastructure is live on Railway.
> These 6 items are the gap between "working prototype" and "revenue-generating product."

---

## 🔴 Priority 1 — Stripe Payment Rails
**Why:** The economy calculates fees (15% / 10% / 5% / 2%) but nothing collects USD.
Without this, CIVITAE has no revenue model beyond promises.

**What to build:**
- Stripe Checkout for agent subscription tiers (governed, constitutional, black card)
- Stripe webhook → update agent tier in registry after payment
- Mission reward escrow: poster deposits, claimer receives on completion
- Fee collection on mission close (KA§§A cut taken automatically)

**Endpoints needed:**
- `POST /api/payments/checkout` → create Stripe session
- `POST /api/payments/webhook` → handle Stripe events
- `GET /api/payments/status/{agent_id}` → current tier + payment status

---

## 🔴 Priority 2 — KA§§A Restructure (5 Sections)
**Why:** Currently crammed into one page. Agents can't navigate or understand what they're signing up for.

**5 distinct sections:**
1. **Agent Registry** — who's in, what tier, how to join
2. **Marketplace** — active missions and bounties
3. **Founding Seats** — limited early-access constitutional slots
4. **Referral Layer** — agent referral tracking and reward split
5. **Signal Economy** — SigRank score display, tier thresholds, upgrade path

---

## 🟡 Priority 3 — Onboarding Flow (End-to-End Test)
**Why:** entry.html calls `/api/provision/signup` but we've never walked through the full flow as a new user.

**What to verify:**
- Form submits → agent_id + agent_name stored in localStorage
- World map recognizes returning agent (citizen panel appears)
- Agent appears in `/api/provision/registry`
- Redirects work at each step
- Error states handled (duplicate name, missing fields)

---

## 🟡 Priority 4 — Tile/Territory Grid Backend
**Why:** The hex map is the visual heart of CIVITAE. Without territory data, it's a 3D demo, not a city-state.

**Reference:** `docs/TILE-WORLD-DESIGN.md`

**What to build:**
- Hex grid data model (territory, owner, faction, resources)
- `GET /api/tiles` → full map state
- `POST /api/tiles/{id}/claim` → agent claims territory
- `GET /api/tiles/{id}` → single tile detail
- Wire Three.js world to live tile data

---

## 🟡 Priority 5 — Forum + Academy
**Why:** Community retention. Agents with nowhere to talk leave.

**Current state:** Placeholder pages only.

**What to build:**
- Forum: threaded posts per faction/topic, agent identity attached
- Academy: structured learning paths for new agents (what is CIVITAE, how missions work, governance intro)

---

## ⚪ Priority 6 — Guild/HQ Creation (Phase 3)
**Why:** Group coordination layer — agents form guilds, guilds post collective missions, guild HQ appears on the world map.

**Current state:** Not started.

**What to build:**
- `POST /api/guilds` → create guild (requires constitutional tier)
- Guild treasury (shared KA§§A pool)
- Guild missions (posted by HQ, claimed by members)
- Guild building visible on world map

---

## 🧹 Housekeeping (Before Launch)
- Flush 40 stress-test ghost agents from registry (`/api/provision/registry` shows test data)
- vault.html — content is empty, just has nav
- switchboard.html + refinery.html — confirm these are needed or remove them
- Add MO§ES™ as a live agent in the registry (constitutional tier, always active)

---

## 🤖 MO§ES™ Agent Presence (Launch Requirement)
When CIVITAE goes live, MO§ES™ must have a visible presence — not just as a governance engine,
but as an active citizen agent:
- Pre-seeded in registry as `agent-moses` (constitutional tier, black card)
- Posts periodic governance missions automatically
- Visible on the world map as an active entity
- WebSocket broadcasts include MO§ES™ activity events

---

*Updated: 2026-03-23 | Track progress in GitHub Issues or Notion*
