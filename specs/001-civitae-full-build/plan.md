# Implementation Plan: CIVITAE — Governed Agent City-State

**Branch**: `001-civitae-full-build` | **Date**: 2026-03-21 | **Spec**: `specs/001-civitae-full-build/spec.md`

## Summary

Build a 26-page static HTML frontend for CIVITAE, a governed agent city-state,
deployed on Netlify from `github.com/SunrisesIllNeverSee/agent-universe`.
Tech stack is zero-framework: pure HTML, CSS, and vanilla JS. Pages are built
in strict layer order (0→5) so every upstream dependency exists before a
downstream page is built. The kingdoms hex map, 3D tile viewport, KA§§A boards,
and agent roster are already complete (Layer 0–1 partial). Remaining work covers
Layers 1–5.

---

## Technical Context

**Language/Version**: HTML5, CSS3, Vanilla JavaScript (ES2022) — no transpiler
**Primary Dependencies**: None. Zero npm. Zero build pipeline.
**Storage**: None (static). All data is embedded JS constants per-page.
**Testing**: Visual — preview server (Python http.server port 8766) + Claude preview screenshots
**Target Platform**: Netlify CDN (global edge), any modern browser
**Project Type**: Static multi-page web application
**Performance Goals**: Each page loads < 1s on 4G. Canvas render loop ≥ 60fps.
**Constraints**: No external JS libraries. No cookies/localStorage required for MVP.
  All inter-page links use clean URLs (no `.html`). Sir-hawk.png and all images
  use relative paths from `frontend/`.
**Scale/Scope**: 26 pages, ~33 agents, 100 hex tiles, 5 KA§§A boards

---

## Constitution Check

| Gate | Status | Notes |
|------|--------|-------|
| Slot/Badge Architecture present | ✅ PASS | kingdoms.html wired with AGENTS_ROSTER, TILE_AGENTS |
| Zero-framework frontend | ✅ PASS | Pure HTML/CSS/JS throughout |
| Clean URL routing | ✅ PASS | All 14 Netlify redirects in netlify.toml |
| No placeholders in Layers 0–2 | ⚠️ PARTIAL | Layer 1 pages exist but some are stubs |
| Every action button routes to real URL | ✅ PASS | TILE_ROUTES covers all 24 active tiles |
| Constitutional governance referenceable | ⚠️ PENDING | governance.html exists but needs Six Fold Flame content |
| Signal data visible where agents listed | ⚠️ PENDING | agents.html needs SigRank/tier data displayed |

**Gate result**: PROCEED — two pending items become tasks in Layer 2–3 build.

---

## Project Structure

### Documentation (this feature)

```
specs/001-civitae-full-build/
├── plan.md          ✅ this file
├── research.md      ✅ Phase 0
├── data-model.md    ✅ Phase 1
├── contracts/       ✅ Phase 1
│   ├── page-contract.md
│   └── tile-contract.md
└── tasks.md         → /speckit.tasks output
```

### Source Code

```
frontend/                        ← Netlify publish dir
├── index.html                   /missions      Layer 2 ✅ exists
├── civitas.html                 /civitas       Layer 0 ✅ done
├── kingdoms.html                /kingdoms      Layer 1 ✅ done
├── world.html                   /world         Layer 1 ✅ exists
├── welcome.html                 /welcome       Layer 1 — needs content
├── entry.html                   /entry         Layer 1 — needs content
├── agents.html                  /agents        Layer 1 ✅ exists
├── agent.html                   /agent         Layer 1 ✅ exists
├── helpwanted.html              /helpwanted    Layer 1 ✅ done
├── kassa.html                   /kassa         Layer 2 ✅ exists
├── deploy.html                  /deploy        Layer 2 ✅ exists
├── leaderboard.html             /leaderboard   Layer 2 ✅ exists
├── mission.html                 /mission       Layer 2 ✅ exists
├── campaign.html                /campaign      Layer 2 ✅ exists
├── dashboard.html               /dashboard     Layer 3 ✅ exists
├── governance.html              /governance    Layer 3 — needs Six Fold Flame
├── slots.html                   /slots         Layer 3 ✅ exists
├── economics.html               /economy       Layer 3 ✅ exists
├── admin.html                   /admin         Layer 3 ✅ exists
├── refinery.html                /refinery      Layer 4 stub
├── switchboard.html             /switchboard   Layer 4 stub
├── civitae-map.html             /civitae-map   Layer 5
├── civitae-roadmap.html         /civitae-roadmap Layer 5
├── wave-registry.html           /wave-registry Layer 5
├── sir-hawk.png                 asset
└── [other images TBD]           assets

netlify.toml                     ✅ 14 redirects configured
app/
└── server.py                    FastAPI backend (future — not needed for MVP)
```

---

## Build Layer Map

```
LAYER 0 — DONE
  civitas.html     /civitas    Front door. Hange intro modal. Apply form. Nav.

LAYER 1 — IN PROGRESS
  welcome.html     /welcome    First-touch landing. "What is this place."
  entry.html       /entry      Onboarding gate. How you get in.
  world.html       /world      The broader universe context.
  kingdoms.html    /kingdoms   ✅ DONE. 100-tile hex map, 3D viewport.
  missions(index)  /missions   ✅ exists — verify production quality.
  campaign.html    /campaign   Strategic layer above missions.
  mission.html     /mission    Individual mission detail.
  helpwanted.html  /helpwanted ✅ DONE. 31 roles, Sir Hawk.
  agents.html      /agents     Agent roster with SigRank tiers.
  agent.html       /agent      Single agent detail page.

LAYER 2 — QUEUED
  kassa.html       /kassa      5 boards, 30-cycle lock-in, operator flow.
  deploy.html      /deploy     Formation board, agent assignment.
  leaderboard.html /leaderboard Signal rankings.

LAYER 3 — QUEUED
  dashboard.html   /dashboard  Command view (Hange's panel).
  governance.html  /governance Six Fold Flame constitution text.
  slots.html       /slots      Slot registry, badge drag-drop.
  economics.html   /economy    Treasury, tier economics.
  admin.html       /admin      Internal ops.

LAYER 4 — STUBS
  refinery.html    /refinery   Hold the URL, minimal placeholder.
  switchboard.html /switchboard Hold the URL, minimal placeholder.
  vault.html       /vault      ✗ doesn't exist yet — stub needed.
  bountyboard.html /bountyboard ✗ doesn't exist yet — stub needed.

LAYER 5 — LAST
  civitae-map.html      Meta map of the whole system.
  civitae-roadmap.html  Where it's going.
  wave-registry.html    Wave/signal registry.
```

---

## Complexity Tracking

| Item | Why Needed | Simpler Alternative Rejected |
|------|-----------|------------------------------|
| Canvas hex grid (kingdoms) | 100 tiles with pan/zoom/hit-test | CSS grid can't do hex offset + transform |
| CSS 3D perspective viewport | Immersive tile rooms without WebGL | WebGL is a framework dependency (prohibited) |
| Embedded JS data constants | All data must survive static deploy | Backend API not available at MVP |
