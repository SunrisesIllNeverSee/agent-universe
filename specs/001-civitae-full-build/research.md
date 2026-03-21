# Research: CIVITAE Frontend Build

**Phase 0 output** | 2026-03-21

## Decisions

### Static vs. Framework
- **Decision**: Pure HTML/CSS/JS, zero framework
- **Rationale**: No build step = instant Netlify deploy. No dependency rot.
  Pages load in < 1s. Canvas rendering doesn't need React.
- **Alternatives considered**: Next.js (rejected — overkill, adds build pipeline),
  Astro (rejected — adds complexity), vanilla with module bundler (rejected — still
  requires Node toolchain)

### Routing
- **Decision**: Netlify redirects (netlify.toml) for clean URLs
- **Rationale**: 14 routes already wired. `/*` SPA fallback to civitas catches
  anything missing. Zero server-side logic.
- **Alternatives considered**: Hash routing (rejected — ugly URLs), server-side
  routing via FastAPI (rejected — not needed for static MVP)

### Data Layer
- **Decision**: Embedded JS constants per page (AGENTS_ROSTER, TILE_LOAD, etc.)
- **Rationale**: No backend required for MVP. All data visible in source.
  Easy to update manually. Agents, tiles, and routes are stable enough.
- **Alternatives considered**: JSON files fetched at runtime (rejected — adds
  latency and CORS complexity for static host), Supabase (rejected — overkill
  for MVP, adds auth/billing)

### Map Rendering
- **Decision**: HTML5 Canvas with requestAnimationFrame
- **Rationale**: 100 hex tiles with pan/zoom/hit-test requires pixel-level control.
  Canvas handles transform matrix natively.
- **Alternatives considered**: SVG (rejected — 100 elements slow with transform),
  CSS grid (rejected — can't do offset hex geometry)

### 3D Viewport
- **Decision**: CSS perspective transform (`perspective: 1100px`, `rotateX(62deg)`)
- **Rationale**: Zero-framework constraint rules out Three.js/WebGL. CSS 3D is
  sufficient for the floor grid illusion.
- **Alternatives considered**: WebGL (rejected — framework dependency),
  isometric CSS (rejected — less immersive)

### Image Assets
- **Decision**: Relative paths from `frontend/` root (`sir-hawk.png`)
- **Rationale**: Python http.server serves from `frontend/` dir. Netlify
  publishes `frontend/`. Absolute paths (`/sir-hawk.png`) resolve correctly
  on both.
- **Alternatives considered**: CDN hosting (deferred to post-MVP)

### Typography
- **Decision**: `'SF Mono', monospace` — no external font load
- **Rationale**: SF Mono is system font on macOS/iOS. Falls back to monospace
  everywhere else. Zero network request.
- **Alternatives considered**: Google Fonts (rejected for kingdoms.html —
  latency on map load), Geist Mono (future consideration)
