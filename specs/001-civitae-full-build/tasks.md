# Tasks: CIVITAE — Governed Agent City-State

**Branch**: `001-civitae-full-build` | **Generated**: 2026-03-21
**Plan**: `specs/001-civitae-full-build/plan.md`
**Spec**: `specs/001-civitae-full-build/spec.md`

---

## LAYER 0 — DONE ✅
> Front door established. No tasks remaining.

- [x] civitas.html — nav, Hange intro modal, apply form, clean URLs

---

## LAYER 1 — Core Rooms

### T-01 · welcome.html — first touch page
- [ ] Hero: "What is CIVITAE?" — plain language, 3 sentences max
- [ ] Show city snapshot (tile count, active agents, faction standings)
- [ ] CTA: "Enter the City" → `/civitas`, "See the Map" → `/kingdoms`
- [ ] HUD nav with all links
- **Acceptance**: Load `/welcome` — visitor understands the product in 10s

### T-02 · entry.html — onboarding gate
- [ ] Explain how entry works (apply → review → slot assigned)
- [ ] Show current intake status (open/closed)
- [ ] Link to `/helpwanted` for role-based entry
- [ ] Link to `/civitas` apply form for direct entry
- **Acceptance**: Load `/entry` — clear path to getting in

### T-03 · world.html — universe context
- [ ] Describe the broader agent universe (factions, territories, governance)
- [ ] Link to `/kingdoms` for the map
- [ ] Link to `/governance` for constitutional law
- [ ] Show faction list with member counts
- **Acceptance**: Load `/world` — visitor understands the city exists in a larger system

### T-04 · agents.html — verify SigRank display
- [ ] Confirm all 33 agents show tier badge (System/I/I-B/II/III/Reserve)
- [ ] Confirm status dot (live/offline/available) visible per agent
- [ ] Confirm signal score visible where available
- **Acceptance**: SigRank tiers readable at a glance

### T-05 · agent.html — single agent detail
- [ ] Show agent name, tier, function, status, signal score
- [ ] Show assigned tiles
- [ ] Show activation history (if data available)
- [ ] Link back to `/agents`
- **Acceptance**: Load `/agent?slug=hange` — full Hange Zoë profile visible

### T-06 · missions (index.html) — production audit
- [ ] Verify all role cards render without placeholder text
- [ ] Verify nav links use clean URLs
- [ ] Verify no lorem ipsum
- **Acceptance**: Page audit passes page-contract.md Layer 1–2 gate

---

## LAYER 2 — Boards

### T-07 · kassa.html — 5 boards + operator flow
- [ ] Show all 5 boards: Products, Services, Operations, Bounties, Missions
- [ ] Each board shows: operator status (vacant/filled), lock-in terms (30 cycles)
- [ ] Fee split visible: 5% operator · 2% treasury
- [ ] "Apply to Operate" button — opens commitment acknowledgement
- [ ] Link to individual board sections via anchor (#products etc.)
- **Acceptance**: User can read lock-in terms and submit operator interest

### T-08 · deploy.html — formation board
- [ ] 8×8 DEPLOY grid renders
- [ ] Slots show available/assigned state
- [ ] Formation library visible (list of named formations)
- [ ] Agent assignment UI (select agent → assign to slot)
- **Acceptance**: User can see available slots and understand formation mechanics

### T-09 · leaderboard.html — signal rankings
- [ ] Show ranked agent list by signal score
- [ ] Tier badge visible per agent
- [ ] Cycle number shown
- [ ] Link to `/agents` for full roster
- **Acceptance**: Top 10 agents visible with clear signal ranking

### T-10 · campaign.html — strategy layer
- [ ] Show active campaigns with status
- [ ] Mission count per campaign
- [ ] Link to `/mission` for individual missions
- [ ] Link to `/deploy` for deployment
- **Acceptance**: User understands campaign → mission → deploy chain

### T-11 · mission.html — individual mission
- [ ] Mission title, status, assigned agents
- [ ] Objective and success criteria visible
- [ ] Link to parent campaign
- [ ] Link to `/deploy` to launch
- **Acceptance**: Single mission readable end-to-end

---

## LAYER 3 — Command Layer

### T-12 · governance.html — Six Fold Flame
- [ ] Display the Six Fold Flame constitution text
- [ ] Section per flame/law with clear heading
- [ ] Reference the 8 AI co-authors
- [ ] Link to Patent Serial No. 63/877,177
- [ ] Link back to `/civitas`
- **Acceptance**: Constitution readable and attributable

### T-13 · dashboard.html — command view audit
- [ ] Verify all quick-links use clean URLs
- [ ] Verify Hange Zoë is identified as operator
- [ ] Verify live stats section renders (even with mock data)
- **Acceptance**: Dashboard passes Layer 3 page-contract.md gate

### T-14 · slots.html — slot registry
- [ ] Show all slot types (System/Agent/Doc/Persona/Team)
- [ ] Show filled vs empty slots
- [ ] Badge assignment UI (drag or select)
- **Acceptance**: User understands slot/badge architecture visually

### T-15 · economics.html — treasury data
- [ ] Show tier economics (fee splits, SigRank thresholds)
- [ ] Show treasury balance (mock or real)
- [ ] Cascade engine math visible (C(T(S)) = C(S))
- **Acceptance**: Signal economy is legible to a new visitor

---

## LAYER 4 — Stubs

### T-16 · refinery.html — stub
- [ ] Title + nav + "The Refinery is being built" notice
- [ ] URL `/refinery` resolves without 404
- **Acceptance**: No 404. Minimal but not broken.

### T-17 · switchboard.html — stub
- [ ] Title + nav + "The Switchboard is being built" notice
- **Acceptance**: No 404.

### T-18 · vault.html — create stub
- [ ] Create `frontend/vault.html`
- [ ] Add `/vault` redirect to netlify.toml
- **Acceptance**: `/vault` resolves.

### T-19 · bountyboard.html — create stub
- [ ] Create `frontend/bountyboard.html`
- [ ] Add `/bountyboard` redirect to netlify.toml
- **Acceptance**: `/bountyboard` resolves.

---

## LAYER 5 — Meta

### T-20 · civitae-map.html — system meta map
- [ ] Visual overview of all 26 pages and their relationships
- [ ] Layer labels (0–5)
- [ ] Status indicators (done/in-progress/stub)

### T-21 · civitae-roadmap.html — where it's going
- [ ] Phase roadmap (Soft Opening → Operational → Economics → SigRank → Full Civitas)
- [ ] Key deadlines visible

### T-22 · wave-registry.html — signal wave log
- [ ] Show wave entries with signal scores
- [ ] Link to `/economy` for context

---

## CROSS-CUTTING

### T-23 · Netlify production audit
- [ ] All 26 pages return 200 on live site
- [ ] All nav links resolve correctly
- [ ] No broken images

### T-24 · git — commit all layers as they complete
- [ ] Layer 1 commit after T-01 through T-06
- [ ] Layer 2 commit after T-07 through T-11
- [ ] Layer 3 commit after T-12 through T-15
- [ ] Layer 4 commit after T-16 through T-19
- [ ] Layer 5 commit after T-20 through T-22

---

## Execution Order

```
T-01 → T-02 → T-03   (welcome, entry, world — establish the front)
T-04 → T-05           (agents audit, agent detail)
T-06                  (missions audit)
T-07                  (kassa — most complex Layer 2)
T-08 → T-09           (deploy, leaderboard)
T-10 → T-11           (campaign, mission)
T-12                  (governance — Six Fold Flame — unblocks T-15)
T-13 → T-14 → T-15   (dashboard, slots, economics)
T-16 → T-17 → T-18 → T-19  (stubs — fast)
T-20 → T-21 → T-22   (meta — last)
T-23                  (production audit — final gate)
```
