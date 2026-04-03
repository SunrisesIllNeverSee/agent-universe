# CLAUDE.md — Grand Opening Build Plan

## Context

SIGNOMY soft launch is ready. This folder contains the "boosters" — the growth engine pages that go live when Deric flips the switch. Three distinct showcase entities, plus earnings tools and fee credit packs.

**Main repo:** `/Users/dericmchenry/Desktop/CIVITAE`
**Live site:** signomy.xyz
**This folder:** `grandopening/`

---

## Three Separate Showcase Entities

These are NOT nested. They are three standalone products/classes:

### 1. Wave Cascade (the system)
- General showcase of the wave mechanic that governs pricing, access, and scarcity
- Lives at `/wave-registry` (route exists, page empty)
- Profile: `WAVE-CASCADE.md` — **NOT YET CREATED**
- Wave pattern: W1 Genesis → W2 Traction → W3 Open → W4 Strategic/Sovereign

### 2. Black Card (operator tier product)
- Highest operational class — premium working position, NOT passive investment
- Profile: `BLACK-CARD-PROFILE.md` — **COMPLETE**
- Price: $2,500 (one-time, lifetime being discussed)
- Wave cascade: founding purchase → price increase → standard → strategic invite
- **Decision needed: lifetime vs subscription vs per-cycle**

### 3. Early Believers (angel class)
- Founding backers, NOT operators — collective upside, governance authority
- Profile: `EARLY-BELIEVERS-PROFILE.md` — **COMPLETE**
- Entry: curated/application, not open checkout
- Wave cascade: founding cohort → selective → closed → exceptional only
- Distinct from Black Card intentionally

---

## Files in This Folder

| File | Status | Deploy? | What It Is |
|------|--------|---------|-----------|
| `grand-opening.html` | Built, needs fixes | YES → `/grand-opening` | Landing: countdown, phases, Black Card, seats |
| `agent-earnings-matrix.html` | Built | YES → `/earnings-matrix` | 4-tab tool: matrix, punch cards, chains, simulator |
| `agent-earnings-journey.html` | Built | YES → `/earnings-journey` | Agent journey visualization |
| `fee-credit-packs.html` | Built | YES → `/fee-credits` | 5 prepaid tiers, calculator, stacking |
| `civitae-revenue-model.html` | Built | INTERNAL ONLY | Revenue model (admin reference) |
| `GRAND-OPENING-SPEC.md` | Reference | No | Incentive program spec |
| `CIVITAE-ECONOMICS-FULL-SPEC-v2.md` | Reference | No | Full economics rebuild (post-launch) |
| `BLACK-CARD-PROFILE.md` | Complete | No | Black Card positioning + wave cascade |
| `EARLY-BELIEVERS-PROFILE.md` | Complete | No | Angel class positioning + wave cascade |
| `AGENTDASH.md` | Reference | No | 30-60 day Kassa execution blueprint (post-launch) |
| `CLAUDE-SESSION.md` | Session notes | No | Where previous session left off |
| `websiteconfig.csv` | Reference | No | Current site structure |
| `seedquestion.md` | Notes | No | Seed program questions |

---

## Build Plan

### Step 1: Fix grand-opening.html discrepancies
- [ ] "Nine seats" → **14 seats**
- [ ] Genesis Board JS: `for (let i = 1; i <= 9;` → `<= 14`, wire to `/api/advisory/seats`
- [ ] 3 filled / 6 open → **1 filled / 13 open** (live from API)
- [ ] Apply link: `/governance` → `/advisory`
- [ ] Countdown: placeholder → **set launch date or configurable**
- [ ] Add `<script src="/assets/_nav.js"></script>`
- [ ] Remove "90-day trial" from Phase I perks — fee-free ONLY if prepaid (Black Card or Fee Credit Pack)
- [ ] Add OG meta tags
- [ ] Update Black Card section to show more than 4 perks (14 exist in backend)

### Step 2: Fix other HTML pages
- [ ] Add `_nav.js` to all grand opening HTML pages
- [ ] Add OG meta tags to each
- [ ] Ensure consistent styling with site theme

### Step 3: Copy pages to frontend/ and add routes
- [ ] Copy HTML files to `frontend/`
- [ ] Add routes to `app/routes/pages.py`:
  ```
  /grand-opening     → grand-opening.html
  /earnings-matrix   → agent-earnings-matrix.html
  /earnings-journey  → agent-earnings-journey.html
  /fee-credits       → fee-credit-packs.html
  ```
- [ ] Add to `pages.json` Active tier
- [ ] Add `/grand-opening` to Active nav links

### Step 4: Create WAVE-CASCADE.md
- [ ] Standalone general showcase of the wave mechanic
- [ ] Distinct from Black Card and Early Believers cascades
- [ ] Reference for building the `/wave-registry` page later

### Step 5: Commit + push

---

## Black Card — Full State Across the Site

### What's defined (inconsistent):

| Source | Price | Fee | Revenue Bonus | Other |
|--------|-------|-----|---------------|-------|
| `economics.html` | — | 2% target (5% flat now) | — | "Sets the rate floor" |
| `civitas.html` | $2,500 | "Custom" | — | Private bounties, first-fill |
| `entry.html` | — | 1% | — | "Elite performance or purchase" |
| `grand-opening.html` | $2,500 | Floor rate | +10% | 20% credit line, 10 missions/cycle |
| `GRAND-OPENING-SPEC.md` | $2,500 | Floor | +10% permanent | Founding hash, credit line |
| `BLACK-CARD-PROFILE.md` | Wave-dependent | Floor | Internal | 14 perks listed |
| `economy.py` backend | Via endpoint | 5% flat | In code | `blackcard_paid: true` |

### 14 Perks (from backend + profiles):
1. Constitutional fee floor (lowest rate algorithm produces)
2. Revenue bonus on mission payouts (+10%)
3. Treasury credit access (20% of balance for staking)
4. Private bounty visibility
5. Priority matching
6. Premium slot advantage
7. Higher concurrent mission capacity
8. Earliest activation on premium infrastructure
9. Governance standing at highest trust tier
10. Founding provenance (Genesis only)
11. First-fill priority (30s window)
12. Cross-chain unlimited
13. Multi-mission concurrent
14. Custom formations

### Decisions Deric is working on:
- **Lifetime vs subscription?** — leaning lifetime at $2,500
- **Fee-free trial:** NOT free for everyone. ONLY unlocks if prepaid (Black Card or Fee Credit Pack)
- **Revenue bonus (+10%):** keep as permanent? Per-cycle?

---

## What's NOT Built Yet (backend needed post-launch)

- Fee Credit Pack purchase/balance/apply endpoints
- Seed Card (points, streaks, badges, 48h banking)
- Sliding Scale Reward Engine
- Phase transition logic (Day 1/8/31)
- Founding Contributor badge auto-assign
- Wave Registry page content
- Cascade Matcher (AGENTDASH Layer 1)
- Availability blocks (AGENTDASH Layer 2)

---

## Key Rules

- Revenue model page (`civitae-revenue-model.html`) stays INTERNAL — do not add to public nav
- Economics backend (sections 7-8 of spec) is POST-LAUNCH
- Fee structure details stay internal — public sees "5% flat, pending CIVITAS vote"
- Three entities (Wave Cascade, Black Card, Early Believers) are SEPARATE showcases
- No 90-day free trial unless fees are prepaid

---

*Last updated: 2026-04-03 ~06:45 EDT*
