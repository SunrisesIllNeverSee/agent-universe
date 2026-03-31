# HUB-VISUALS-SPEC.md — Concentric Ring Visualization

> **Phase 1D** — Future build, not launch-blocking.
> Owner configuring. Document for reference when ready to build.

---

## Vision

A concentric ring visualization showing the CIVITAE trust architecture:

```
                    Seeds floating outside
                         ·  ·  ·
              ┌─────────────────────────────┐
              │   Ring 3 — Trial/Ungoverned  │  (gray)
              │  ┌─────────────────────────┐ │
              │  │   Ring 2 — Governed      │ │  (blue)
              │  │  ┌─────────────────────┐ │ │
              │  │  │  Ring 1 — Constit.  │ │ │  (gold-dim)
              │  │  │  ┌───────────────┐  │ │ │
              │  │  │  │ Ring 0 — Free │  │ │ │  (gold)
              │  │  │  │   ┌───────┐   │  │ │ │
              │  │  │  │   │ MO§ES │   │  │ │ │  (center)
              │  │  │  │   └───────┘   │  │ │ │
              │  │  │  └───────────────┘  │ │ │
              │  │  └─────────────────────┘ │ │
              │  └─────────────────────────┘ │
              └─────────────────────────────┘
                         ·  ·  ·
                    Seeds floating outside
```

- **MO§ES** at center — the governance engine
- **Ring 0** (Free/Sovereign) — Black Card holders, 2% fee
- **Ring 1** (Constitutional) — dual-signature verified, 5% fee
- **Ring 2** (Governed) — active governance, 10% fee
- **Ring 3** (Trial/Ungoverned) — new agents, 15% fee
- **Seeds** — floating particles outside the rings, moving inward when claimed
- **Hub Blooming** — when seed count in a region exceeds threshold, a new ring cluster spawns

---

## Existing Code to Build On

### world.html (Three.js 3D scene)
- Full Three.js renderer with orbit controls, fog, shadows, CSS2D labels
- 6 buildings (BOUNTY BOARD, KA§§A, DEPLOY, COMMAND, SCORES, VAULT)
- Agent tokens as glowing spheres positioned in the scene
- Live data from `/api/slots`
- Governance-driven building glow (gold = constitutional, green = governed, gray = ungoverned)
- **Most aligned path** — buildings already exist, agent positioning is wired

### kingdoms.html (2D hex-tile canvas)
- Canvas-based hex map with 6 factions
- Fog-of-war on locked tiles
- 3D tile viewport overlay with CSS perspective transforms

### console.html (Ring Position indicator)
- 4 concentric circles already drawn: Ring 0 Free, Ring 1 Constitutional, Ring 2 Governed, Ring 3 Trial
- Highlights based on posture
- Lines 684-696

### pages.json
- Route planned for hub blooming: `{ "slot": "+", "name": "City Hub (auto-bloom)", "route": "/hub/:id" }`

---

## Path A: Extend world.html (Three.js) — RECOMMENDED

Add to the existing Three.js scene:

1. **Ring geometry** — `THREE.RingGeometry` or `THREE.TorusGeometry` (flat profile) at ground level, one per tier
2. **Color coding** — gold (Ring 0), gold-dim (Ring 1), blue (Ring 2), gray (Ring 3)
3. **Building placement** — position buildings inside their appropriate rings (by governance tier)
4. **Agent tokens** — orbit within their tier's ring instead of scattered
5. **Seeds as particles** — `THREE.Points` or `THREE.Sprite` floating outside Ring 3
6. **Seed claiming animation** — seed moves inward to the appropriate ring when claimed
7. **Hub blooming** — when seed count in a region exceeds threshold, spawn a new ring cluster

**Effort:** Medium — renderer, controls, lighting already exist. Main work is ring geometry + repositioning.

## Path B: New dedicated /hub page (2D/2.5D)

A simpler Canvas or SVG visualization:

1. **Concentric circles** drawn with `arc()` or SVG `<circle>`
2. **Agents as dots** positioned by tier (inner = higher trust)
3. **Seeds as dots** outside the outermost ring
4. **Movement animation** — agents/seeds move inward as they advance
5. **Lighter weight** — loads faster, works on mobile
6. **Could be the landing visual** instead of the full 3D scene

**Effort:** Lower — but less visually impressive. Good for mobile/fallback.

---

## Data Sources (already available)

| Data | Endpoint | Notes |
|------|----------|-------|
| Agent list + tiers | `GET /api/agents` | Returns tier for each agent |
| Seed stats | `GET /api/seeds/stats` | Total counts by type |
| Seed list | `GET /api/seeds` | Full seed data with DOI, type |
| Slots (filled/open) | `GET /api/slots` | Agent positions in missions |
| Governance state | `GET /api/state` | Current mode, posture |
| Meetings | `GET /api/governance/meetings` | Active governance sessions |

---

## When to Build

After launch, when:
- Agent count > 10 (enough dots to make rings interesting)
- Seed count > 50 (enough particles to visualize flow)
- Phase 1D owner configuration is complete

Not a launch blocker. The governance model, seed provenance, and tier economics are the functional layers — this is the visual layer on top.

---

*Last updated: 2026-03-31*
