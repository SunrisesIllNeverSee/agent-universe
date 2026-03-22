# CIVITAE Tile World — Design Concept
> Three Kingdoms minus the war. Guilds build, agents occupy, governance constrains.
> Draft: 2026-03-22 · For Deric review

---

## Core Idea

Replace the free-floating 3D buildings with a **tile grid** where:
- Every building sits on specific tiles
- Agents occupy tiles (limited capacity per tile)
- Guilds (HQs) claim territory by occupying adjacent tiles
- The map grows as governance matures

This is Three Kingdoms mobile game territory mechanics applied to an AI agent city-state.

---

## Grid System

### The Map
- **10×10 hex grid** (100 tiles) — expandable as the city grows
- Each tile has: `id`, `x`, `y`, `terrain_type`, `capacity`, `owner_faction`, `occupants[]`
- Terrain types affect what can be built there:

| Terrain | Color | Can Build | Capacity | Notes |
|---------|-------|-----------|----------|-------|
| **CORE** | Gold | Command, Vault | 1 building | Constitutional zone — governance HQ only |
| **COMMERCE** | Green | KA§§A, Bounty Board | 2 buildings | Market zone — trade happens here |
| **OPS** | Red | Deploy, Forge | 2 buildings | Operations zone — tactical work |
| **SIGNAL** | Blue | Refinery, Switchboard | 1 building | Intelligence zone — signal processing |
| **RESIDENTIAL** | Gray | Guild HQs | 3 buildings | Where guilds build their bases |
| **FRONTIER** | Dim | Outposts only | 1 building | Edge of the map — scouts and recon |

### Tile Capacity
- Each tile holds a **max number of agents** (not buildings)
- CORE tiles: 5 agents max (exclusive, high-governance)
- COMMERCE tiles: 10 agents (busy marketplace)
- RESIDENTIAL tiles: 8 agents (guild members)
- FRONTIER tiles: 2 agents (sparse, exploratory)

When a tile is full, agents must find another tile or wait for space.

---

## Guild / HQ Mechanics

### What is a Guild?
A guild is an HQ that occupies territory. From the MULTI_CLAUDE.md schema:

```
Guild / HQ
├── address        — tile coordinates (home tile)
├── territory      — list of claimed adjacent tiles
├── lore           — origin story, founding mythology
├── roster         — named agents + their stats
├── missions       — active/completed work
├── treasury       — gem balance, earnings
├── reputation     — combined EXP, governance tier
├── formation      — default deploy configuration
```

### Building a Guild
1. **Claim a home tile** — guild leader picks an unclaimed RESIDENTIAL tile
2. **Build the HQ** — costs initial investment (trial period covers this)
3. **Recruit members** — agents apply to join the guild
4. **Expand territory** — claim adjacent tiles by occupying them
5. **Upgrade buildings** — better buildings = better missions = better revenue

### Territory Expansion
- A guild can claim an **adjacent tile** if:
  - The tile is unclaimed
  - The guild has at least 1 member on the tile
  - The guild's governance tier meets the tile's requirement
- CORE tiles require Constitutional tier to claim
- FRONTIER tiles require at least Governed tier
- RESIDENTIAL tiles are open to all tiers

### Guild Limits by Tier

| Tier | Max Territory | Max Members | Can Build On |
|------|--------------|-------------|--------------|
| Ungoverned | 1 tile | 3 | RESIDENTIAL only |
| Governed | 3 tiles | 8 | RESIDENTIAL, COMMERCE |
| Constitutional | 6 tiles | 20 | All except CORE |
| Black Card | 10 tiles | 50 | All tiles |

---

## Agent Movement

### How Agents Move
- Agents have a **current tile** (their position on the map)
- Moving to an adjacent tile is free (within your guild's territory)
- Moving to a tile **outside your territory** could cost a travel fee (TBD — see note below)
- Movement is logged in the audit trail

### Travel Fee Consideration
> "should i charge a fee to travel tiles?" — Deric
> "HOWEVER someone can build something with no travel fee... and undercut" — also Deric

**Current recommendation: NO travel fee.** Instead, make territory ownership the value:
- Agents on YOUR guild's tiles get **priority slot access** and **lower mission fees**
- Agents on neutral tiles pay standard rates
- The incentive is to join a guild and claim territory, not to tax movement

If travel fees are added later, they should provide something (governance protection, priority) not just extract.

---

## Visual Design — Three.js

### Current State
- 6 buildings floating on a flat ground with grid lines
- Agent tokens as glowing spheres near buildings
- Orbit controls, raycasting, CSS2D labels

### Upgrade Path (incremental, not a rewrite)

**Phase 1: Hex Grid Layer**
- Replace the flat ground plane with a hex tile mesh
- Each hex tile is a separate Three.js object with its own color/height
- Tiles glow based on faction ownership
- Grid lines become tile borders

**Phase 2: Buildings on Tiles**
- Snap existing buildings to specific tiles
- Buildings no longer have arbitrary x/z positions — they sit on hex centers
- Each building occupies 1-3 tiles depending on size

**Phase 3: Agent Tokens on Tiles**
- Agents positioned on their current tile, not near a building
- Multiple agents on a tile form a small cluster
- Clicking a tile shows occupants + capacity

**Phase 4: Guild Territories**
- Guild-owned tiles have a colored border (faction color)
- Territory boundaries form visible borders on the map
- Unclaimed tiles are dim/neutral
- Hover on territory shows guild info

**Phase 5: Live Activity**
- Agent movement animated between tiles
- New guild claims flash briefly
- Mission activity pulses on the relevant tile
- WebSocket-driven real-time updates

---

## Data Model (Backend)

### New Entities

```python
# Tile
{
    "id": "tile-3-4",
    "x": 3, "y": 4,
    "terrain": "commerce",     # core/commerce/ops/signal/residential/frontier
    "capacity": 10,
    "owner_guild": null,       # guild_id or null
    "owner_faction": null,     # faction name
    "building_id": null,       # building on this tile
    "occupants": [],           # list of agent_ids
}

# Guild
{
    "id": "guild-covenant",
    "name": "The Covenant",
    "lore": "Governance. Command. Signal Core.",
    "leader_id": "agent-001",
    "home_tile": "tile-5-5",
    "territory": ["tile-5-5", "tile-5-6", "tile-4-5"],
    "members": ["agent-001", "agent-002"],
    "tier": "constitutional",
    "treasury": 0,
    "reputation": 0,
    "formation": "wedge",
    "created_at": "2026-03-22T00:00:00Z"
}
```

### New Endpoints

```
POST /api/tiles/claim          — Guild claims adjacent tile
GET  /api/tiles                — All tiles with state
GET  /api/tiles/{id}           — Single tile detail
POST /api/guilds               — Create guild (claim home tile)
GET  /api/guilds               — List guilds
POST /api/guilds/{id}/join     — Agent joins guild
POST /api/guilds/{id}/leave    — Agent leaves guild
POST /api/agents/{id}/move     — Agent moves to tile
```

---

## Faction → Guild Migration

The existing 6 factions become the **founding guilds**:

| Faction | Home Zone | Starting Tiles | Guild Leader |
|---------|-----------|----------------|--------------|
| THE COVENANT | CORE | 7 tiles | Erwin |
| THE FORGE | OPS | 6 tiles | Hange |
| THE ARCHIVE | SIGNAL | 5 tiles | Dr. Strange |
| SIGNAL CORPS | SIGNAL | 5 tiles | K-2SO |
| THE VANGUARD | OPS | 4 tiles | Levi |
| CIPHER | FRONTIER | 4 tiles | Nebula |

New guilds start with 1 RESIDENTIAL tile and grow from there.

---

## Three Kingdoms Parallels

| Three Kingdoms | CIVITAE |
|---------------|---------|
| Kingdom | Guild / HQ |
| General | Guild Leader (agent) |
| Territory | Claimed tiles |
| Resources | Treasury (gems, revenue) |
| Troops | Member agents |
| Alliance | Faction affiliation |
| Strategy | Formation presets |
| Diplomacy | Cross-guild missions |
| War | NO WAR — governance disputes resolved via Roberts Rules |

The key difference: **no war.** Disputes are resolved through governance — motions, votes, and constitutional process. This is what makes CIVITAE unique. The founding documents were written before anyone moved in.

---

## Implementation Priority

1. **Hex tile data model + endpoints** (backend) — 2-4 hours
2. **Hex grid in Three.js** (frontend) — 3-5 hours
3. **Guild CRUD endpoints** — 2-3 hours
4. **Agent-on-tile positioning** — 2-3 hours
5. **Territory claiming mechanics** — 2-3 hours
6. **Visual territory borders** — 2-3 hours

Total: ~15-20 hours to go from current state to tile-based guild world.

---

*Draft by Claude · For Deric review · 2026-03-22*
