# Tile Layer Color Design

Source of truth: `docs/TILE-LAYER-COLOR-DESIGN.md` is the canonical design brief for the color-coded tile system used in the CIVITAE world map. It complements, but does not replace, `docs/TILE-WORLD-DESIGN.md`.

## Purpose

The color-coded tile system exists so a visitor can understand the structure of the platform at a glance.

The map should answer three questions immediately:

1. What architectural layer does this district belong to?
2. What kind of activity happens there?
3. How live, active, or overloaded is it right now?

This system should make the world easier to read, not busier. The color language needs to be structural first, atmospheric second.

## Core Principle

Each tile communicates multiple kinds of meaning, but those meanings should not compete.

The semantic stack is:

1. **Base tile family color** = platform layer
2. **Shade within the family** = subcategory inside that layer
3. **Border and selection behavior** = focus and interactivity
4. **Activity/load overlay** = current pressure or usage
5. **Faction identity** = lore and ownership flavor, not the primary fill logic

The most important shift is this:

Layer color becomes the primary organizing signal.

Faction color becomes secondary.

This keeps the map aligned with the CIVITAE information architecture rather than making it feel like six unrelated kingdoms with disconnected page logic.

## Design Goals

- Make Tile Zero feel sovereign, central, and unmistakable.
- Make Layer 1 feel alive and inhabited.
- Make Layer 2 feel cooler, procedural, and constitutional.
- Make Layer 3 feel experimental, unfinished, and future-facing.
- Keep locked/fogged territory visibly separate from live districts.
- Preserve enough visual restraint that the map still feels premium.

## Non-Goals

- Do not use tile color to communicate every concept at once.
- Do not make faction ownership and platform layer fight for dominance.
- Do not let load heat erase the underlying layer color.
- Do not introduce red as a base family color for normal layer identity; red should remain reserved for danger, overload, or special alert conditions.

## Color Language

The CIVITAE tile map should follow a family-based color system:

### Tile Zero

Tile Zero is the constitutional front door and origin point.

- Family: gold / bone / covenant light
- Emotional read: ceremonial, sovereign, anchoring
- Should feel older and more permanent than the rest of the map

Recommended base:

- `zero`: `#C8A96E`
- dim fill: `rgba(200,169,110,0.22)`

### Layer 1 — Active

Layer 1 is the working city. It should feel inhabited, economically alive, and operational.

Use a green family, but split it into three tones:

- `l1_user`: lighter sage-green for public/user/social districts
- `l1_market`: strong living green for marketplace and economic districts
- `l1_tools`: darker operational green for tactical and production tools

Recommended base:

- `l1_user`: `#A8D88A`
- `l1_market`: `#7EC86E`
- `l1_tools`: `#4E9E5E`

### Layer 2 — Context

Layer 2 is constitutional, archival, and reference-driven. It should feel cooler and more procedural than Layer 1.

Use a blue family, split into three tones:

- `l2_protocol`: pale governance blue for constitutional and protocol surfaces
- `l2_vault`: medium archive blue for document-heavy or record-heavy areas
- `l2_kassa`: deeper civic blue for marketplace detail/reference surfaces

Recommended base:

- `l2_protocol`: `#8AB8D8`
- `l2_vault`: `#6E9EC8`
- `l2_kassa`: `#4E7EA8`

### Layer 3 — Building

Layer 3 is not dead, but it is not fully alive either. It should feel promising, strange, and still under construction.

- Family: violet / muted purple
- Emotional read: future systems, experimental districts, unfinished machinery

Recommended base:

- `l3_building`: `#9C8EC8`

### Fogged / Locked

Fogged tiles should stay visibly outside the live city.

- Family: slate / indigo-black
- Emotional read: inaccessible, dormant, not yet entered into the governed field

Recommended base:

- `fogged`: `#1A1A2E`
- alternate border slate: `rgba(90,115,185,0.75)`

## Subcategory Meaning

The shade differences inside a layer must remain understandable:

- lighter tone = more public, more social, more readable
- middle tone = economically active, core use case
- darker tone = tooling, infrastructure, specialist surfaces

This should remain consistent across the map so a visitor learns the grammar once and keeps it.

## Recommended Active Tile Mapping

This design is for live/active districts first. Fogged and frontier tiles stay mostly neutral until they are promoted into the live city.

### Tile Zero

- `COMMAND CENTER`
- `Covenant Hall`

### Layer 1 — User / Social

- `THE FORUM`
- `OPEN ROLES`

### Layer 1 — Marketplace / Economic

- `KA§§A: PRODUCTS`
- `KA§§A: SERVICES`
- `KA§§A: OPERATIONS`
- `KA§§A: BOUNTIES`
- `KA§§A: MISSIONS`
- `THE BOUNTY BOARD`

### Layer 1 — Tools / Operations

- `DEPLOY`
- `Forge Outpost`
- `Forge Works`
- `Forge Lab`

### Layer 2 — Protocol / Governance

- `THE VAULT`
- `Archive Wing`
- `Archive Prime`

### Layer 2 — Reference / Detail

- `Cipher Station`
- `Vanguard Garrison`

### Layer 3 — Building / Experimental

- `THE LEADERBOARD`
- `The Refinery`
- `The Switchboard`
- `Signal Root`
- `Signal Station`

This mapping is allowed to evolve, but the principle should remain stable: the tile family color reflects the product layer first, not the faction story first.

## Faction Role In The New System

Factions should still matter, but they should no longer own the base fill color of every active tile.

Faction identity should instead appear through:

- tooltip copy
- district narrative text
- iconography
- special borders or badges in selected states
- side-panel information

This keeps the lore intact while letting the world map behave like a readable product surface.

## Load And Heat Behavior

Load is important, but it should not erase the layer system.

### Rule

Load should read as a **secondary activity layer**, not a replacement tile fill.

### Preferred Behavior

- Base hex stays visibly tied to its layer family at all times.
- Activity appears as an inner glow, inner hex, pulse, or rim treatment.
- At-capacity behavior can use amber-to-red warning accents.

### Important Constraint

Do not let a full-tile heat overlay override the layer family so aggressively that green, blue, and violet districts all collapse into the same traffic map.

The map needs both truths simultaneously:

- what kind of place this is
- how stressed it is

If only one can be read, the system is over-signaling.

## Public And Special Access Treatment

Some tiles need extra access signaling beyond the layer color.

### Public Tiles

Public entry districts should receive a subtle welcoming aura.

Use:

- soft green halo
- calm pulse
- clearer label visibility

This should feel permissive, not loud.

### Constitutional / Core Tiles

Constitutional anchors may receive a stronger gold inner ring or low, steady glow.

This visually says:

- central
- ratified
- weight-bearing

### At Capacity

Red should only appear when:

- a district is overloaded
- a system is under pressure
- a warning state is active

Red should never be the default identity of a healthy district.

## Legend Design

The legend should teach the grammar, not dump every tile name.

Recommended legend structure:

### Layer Families

- Tile Zero
- Layer 1 User
- Layer 1 Marketplace
- Layer 1 Tools
- Layer 2 Protocol
- Layer 2 Vault / Reference
- Layer 2 Detail
- Layer 3 Building
- Fogged

### Status Overlays

- Public access
- Hovered
- Selected
- High load
- At capacity

The visitor should be able to tell the difference between **what a district is** and **what condition it is in**.

## Hover And Selection Behavior

Hover and selection should intensify the existing family color rather than introduce a completely different one.

Recommended behavior:

- hover = brighter border, slightly richer fill
- selected = stronger border, subtle outer ring, more confident label
- capital/core = permanent soft aura even when idle

The tile should feel like the same district, just brought into focus.

## Label Behavior

Labels should stay readable against all family colors.

Principles:

- neutral bone text for primary names
- muted mono metadata
- no family color should destroy contrast
- fogged tiles should remain subdued until hovered

The label system should help the map feel editorial and high-trust, not gamey.

## Accessibility And Readability

The system should not rely on hue alone.

Support the color system with:

- consistent legends
- text labels
- hover detail panels
- border/intensity differences

Someone should still be able to navigate the architectural logic even if they do not distinguish every tone perfectly.

## Visual Tone

The map should feel like:

- a constitutional city
- a tactical atlas
- a living product architecture

It should not feel like:

- a generic strategy game
- a rainbow dashboard
- a faction heatmap with no product logic

The color system should make the site architecture feel embodied.

## Future Implementation Notes

This document is design-only.

When implementation happens, keep these priorities in order:

1. Preserve layer-family readability.
2. Keep faction identity secondary.
3. Prevent load heat from flattening the map.
4. Keep the legend explicit and teachable.
5. Extend the mapping only when new live districts are promoted from fogged territory.

The best outcome is simple:

Someone opens the CIVITAE world map and immediately understands where the living city is, where the constitutional machinery lives, where the future is being built, and where the frontier still waits.
