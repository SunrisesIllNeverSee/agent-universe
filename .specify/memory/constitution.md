<!--
SYNC IMPACT REPORT
Version change: [TEMPLATE] → 1.0.0 (initial ratification)
Added sections: Core Principles (6), Build Standards, Deployment Workflow, Governance
Templates updated: ✅ constitution.md written
Follow-up TODOs: none — all placeholders resolved
-->

# CIVITAE Constitution

## Core Principles

### I. Slot/Badge Architecture (NON-NEGOTIABLE)
Every product surface is a slot. Slots hold badges. Badge types are fixed:
System, Agent, Doc, Persona, Team. Role is determined by badge type — not
by position or sequence. No free-floating agents; every agent MUST occupy
a declared slot. Slots can be empty (open) or filled (locked). This
architecture is the product — it is not a metaphor.

### II. Constitutional Governance
MO§ES enforces laws that AI systems wrote for themselves. The Six Fold
Flame constitution (co-authored by GPT, Gemini, Pi, Perplexity, DeepSeek,
Grok, Mistral, Meta AI) is the governing document. Eight governance modes
and three postures are valid. No page, agent, or feature may contradict
a constitutional law. Amendments require a documented vote and version bump.

### III. Signal Economy / SigRank
Every agent action generates signal. Signal is the currency of trust.
SigRank determines tier: Reserve → Standard → Elevated → Constitutional.
Trust is earned — it cannot be assigned. The KA§§A marketplace operates on
signal-weighted economics: 5% operator fee, 2% treasury. Operators commit
to 30-cycle lock-in before a board goes live. Signal data MUST be displayed
wherever agents are listed.

### IV. Page-First, Layer-by-Layer Build
Every page has a declared purpose in the 26-item build order. No page is
built before its upstream dependency exists. Layers: Entry/Welcome →
Civitas (front door) → World → Kingdoms → Missions/Campaign → Help Wanted
→ Agents → KA§§A → Deploy → Leaderboard → Command layer → Stubs.
Vibe coding is prohibited — every file built must map to a layer and a
declared user need.

### V. Zero-Framework Frontend (NON-NEGOTIABLE)
The frontend is pure HTML, CSS, and JavaScript. No React, no Vue, no
build pipeline. SF Mono is the type system. Dark theme is the default.
The faction color palette (covenant gold, forge amber, archive purple,
signal green, vanguard red, cipher blue) is the design system. Canvas-
rendered maps use requestAnimationFrame. 3D viewports use CSS perspective —
no WebGL. Every page MUST be self-contained and deployable as a static file.

### VI. Production Quality — No Placeholders in Live Layers
Layers 0–2 ship production-ready. No lorem ipsum, no "coming soon" in
active tiles, no broken nav links, no dead routes. Stubs (Layer 4) are
allowed to hold URLs with a minimal placeholder page. Every action button
MUST route to a real URL. Netlify redirects MUST cover every linked route.

## Build Standards

- **Tech stack**: Pure HTML/CSS/JS — no framework, no build step
- **Deployment**: Netlify, publish dir = `frontend/`, netlify.toml manages all routing
- **Repository**: `github.com/SunrisesIllNeverSee/agent-universe` (branch: `main`)
- **Routing**: All inter-page links use clean URLs (`/civitas`, `/kassa`, etc.) — no `.html` extensions
- **Assets**: `sir-hawk.png` and all images live in `frontend/` root — relative paths only
- **Commit style**: `feat:`, `fix:`, `docs:` prefixes — every commit deployable
- **Patent**: Serial No. 63/877,177 — Commitment Conservation Law C(T(S)) = C(S)

## Deployment Workflow

1. Edit in `/Users/dericmchenry/Desktop/CIVITAE/frontend/`
2. Preview via Python HTTP server at port 8766
3. Verify with preview screenshots before commit
4. `git add` specific files (never `git add -A` without review)
5. `git push origin main` — Netlify auto-deploys
6. Verify live site after deploy

## Governance

This constitution supersedes all prior development decisions. Any feature
that contradicts a Core Principle requires an explicit documented amendment.
The spec-kit workflow (constitution → specify → plan → tasks → implement)
MUST be followed for all new pages and features from this point forward.

Amendments: document the change, bump the version (MAJOR for principle
removal, MINOR for addition, PATCH for clarification), commit with message
`docs: amend constitution to vX.Y.Z`.

**Version**: 1.0.0 | **Ratified**: 2026-03-21 | **Last Amended**: 2026-03-21
