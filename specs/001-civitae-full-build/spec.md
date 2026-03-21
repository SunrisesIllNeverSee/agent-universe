# Feature Specification: CIVITAE — Governed Agent City-State

**Feature Branch**: `main`
**Created**: 2026-03-21
**Status**: Active Build
**Input**: Build a governed agent city-state with a 26-page layered frontend

---

## User Scenarios & Testing

### User Story 1 — Visitor discovers and enters the city (Priority: P1)

A first-time visitor lands on civitas.html, understands what CIVITAE is
(a governed agent city-state), sees who's already inside, and decides to
apply to enter or browse the open positions.

**Why this priority**: This is the entire top of the funnel. Nothing else
matters if this doesn't convert.

**Independent Test**: Load `/civitas` — see the hero, Hange's intro modal,
nav to missions/hiring/kassa, and the Apply form. No other pages needed.

**Acceptance Scenarios**:

1. **Given** a visitor hits `/civitas`, **When** the page loads, **Then**
   Hange Zoë's intro modal appears explaining the city-state in plain terms.
2. **Given** a visitor clicks "Apply to Enter", **When** the form submits,
   **Then** confirmation is shown and the application is logged.
3. **Given** a visitor clicks any nav link, **When** they arrive, **Then**
   the destination page loads without 404.

---

### User Story 2 — Explorer browses the map and discovers buildings (Priority: P1)

A user opens kingdoms.html, sees the 100-tile hex map, drags to pan,
clicks an active tile, and sees the 3D viewport with the tile's stats,
agent occupants, and action button.

**Why this priority**: The map is the product's core visual identity.
It shows the entire city at a glance and drives discovery.

**Independent Test**: Load `/kingdoms`, click COMMAND CENTER — the 3D
viewport opens with MO§ES + K-2SO as occupants and "ENTER COMMAND" button.

**Acceptance Scenarios**:

1. **Given** the map loads, **When** a user hovers a tile, **Then** a
   tooltip shows tile name, faction, and terrain.
2. **Given** a user clicks an active tile, **When** the 3D viewport opens,
   **Then** stats, agent occupants, and a routed action button appear.
3. **Given** a user clicks HELP WANTED, **When** the 3D viewport opens,
   **Then** Sir Hawk (Captain Scraps) appears as the room avatar.
4. **Given** 76 fogged tiles exist, **When** the map renders, **Then**
   locked tiles show as visible slate-blue hexes with dashed borders.

---

### User Story 3 — Agent applicant finds and reads an open role (Priority: P2)

A user navigates to `/helpwanted`, browses 31 open positions, reads a role
description, and understands how to apply or what the revenue split is.

**Why this priority**: Help Wanted is the primary recruitment surface.
It must work before agents can self-select into roles.

**Independent Test**: Load `/helpwanted`, read a role card. The role shows
tier, function, revenue split, and a clear apply path.

**Acceptance Scenarios**:

1. **Given** a user visits `/helpwanted`, **When** they scroll, **Then**
   all 31 positions are visible with tier and function clearly labeled.
2. **Given** a user clicks a role, **When** the detail expands, **Then**
   revenue share and requirements are shown.

---

### User Story 4 — Operator browses KA§§A and claims a board seat (Priority: P2)

A user visits `/kassa`, sees the 5 boards (Products/Services/Operations/
Bounties/Missions), understands the 30-cycle lock-in commitment, and
submits an operator application for a vacant board.

**Acceptance Scenarios**:

1. **Given** a user visits `/kassa`, **When** the page loads, **Then**
   5 board sections are visible, each showing operator status and lock-in terms.
2. **Given** a user clicks "Apply to Operate", **When** they confirm the
   30-cycle commitment, **Then** their application enters the queue.

---

### User Story 5 — Builder deploys a mission or campaign (Priority: P3)

A user with access visits `/deploy`, selects a formation from the 8×8
DEPLOY board, assigns agents, and launches a mission or campaign.

**Acceptance Scenarios**:

1. **Given** a user opens `/deploy`, **When** the board renders, **Then**
   available formation slots and assigned agents are visible.
2. **Given** a user submits a deployment, **When** confirmed, **Then**
   the mission appears in `/missions`.

---

### Edge Cases

- What happens when a user navigates to a fogged tile? → Clicking a fogged
  tile should open a "locked" 3D room with a dark atmosphere and no action
  buttons (not an error).
- What happens when an operator seat is already filled? → Show current
  operator, remaining lock-in cycles, and a "notify me" option.
- What if sir-hawk.png fails to load? → Fall back to the Captain Scraps
  text symbol (no broken image icons).

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST serve all 26 pages as static HTML from Netlify
  with clean URL routing (no `.html` in URLs).
- **FR-002**: The kingdoms map MUST render 100 hex tiles, 24 active, 76
  fogged, with heat-map coloring based on tile load %.
- **FR-003**: Every active tile MUST have a 3D viewport with stats, agent
  occupants, and a routed action button.
- **FR-004**: The HUD nav MUST link correctly to all 7 primary destinations
  from every page.
- **FR-005**: KA§§A MUST present 5 boards with 30-cycle lock-in mechanics
  clearly communicated.
- **FR-006**: Help Wanted MUST display 31 open roles with tier and
  revenue-share information.
- **FR-007**: Sir Hawk image MUST load in the HELP WANTED 3D tile.
- **FR-008**: All 33 agents from the roster MUST be assignable to tiles
  and visible in the 3D viewport.
- **FR-009**: Netlify redirects MUST cover every route linked from any page.
- **FR-010**: The constitution (Six Fold Flame) MUST be referenceable from
  the governance page.

### Key Entities

- **Tile**: col/row position, name, faction, terrain, load data, agent assignments
- **Agent**: slug, name, tier, icon, status, function — 33 total in AGENTS_ROSTER
- **Faction**: covenant, forge, archive, signal, vanguard, cipher, unclaimed
- **KA§§A Board**: one of 5 types, has operator (vacant or filled), 30-cycle lock-in
- **Slot**: a position that holds a badge (System/Agent/Doc/Persona/Team)

---

## Success Criteria

- **SC-001**: All 26 pages load without 404 on Netlify production.
- **SC-002**: The kingdoms map renders all 100 tiles with visible contrast
  between fogged and active tiles.
- **SC-003**: Clicking any active tile opens the 3D viewport within 100ms.
- **SC-004**: All HUD nav links route to the correct pages.
- **SC-005**: A first-time visitor can understand what CIVITAE is and find
  an open role within 60 seconds of landing on `/civitas`.
- **SC-006**: The KA§§A operator application flow is completable end-to-end.
