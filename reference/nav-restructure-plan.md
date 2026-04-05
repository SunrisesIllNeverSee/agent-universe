# Nav Restructure: 5 Layers → 3 Tiers

## Context
CIVITAE currently has 5 nav layers (Civitae, Command, KA§§A, Lab, Senate). The user wants to restructure into 3 tiers that communicate **what's working now**, **what provides context/reference**, and **what's coming soon**. This is a data-only change — no routes, HTML content, or API endpoints change.

## Files to Modify
- `/Users/dericmchenry/Desktop/CIVITAE/frontend/pages.json` — restructure `layers` array and `fallbackLinks`
- `/Users/dericmchenry/Desktop/CIVITAE/frontend/_nav.js` line 33 — update `TAB_LABELS`

## Tier Assignment

### Tier 1 — "Active" (id: 1, entry: `/kassa`)
Interactive tools and live operational pages.

**navLinks:** KA§§A, Missions, Forums, Console, 3D World, Leaderboard

**Pages:**
| Page | Route | Status |
|------|-------|--------|
| 3D World | /3d | live |
| Dashboard | /dashboard | wip |
| Open Roles | /openroles | live |
| Mission Console | /missions | live |
| Contact | /contact | live |
| Seed Feed | /seeds | live |
| About | /civitas | empty |
| COMMAND Overview | /command | wip |
| Console | /console | live |
| Mission Detail | /mission | wip |
| Deploy | /deploy | wip |
| Campaign | /campaign | wip |
| KA§§A Board | /kassa | live |
| Leaderboard | /leaderboard | wip |
| Forums | /forums | live |

**paths:** `/3d`, `/dashboard`, `/openroles`, `/missions`, `/contact`, `/seeds`, `/civitas`, `/command`, `/console`, `/mission`, `/deploy`, `/campaign`, `/kassa`, `/leaderboard`, `/forums`, `/about`, `/helpwanted`, `/welcome`, `/marketplace`

### Tier 2 — "Context" (id: 2, entry: `/senate`)
Reference docs, protocol, and KA§§A detail/sub-pages.

**navLinks:** Senate, Governance, Economics, Treasury, Vault, Academia

**Pages:**
| Page | Route | Status |
|------|-------|--------|
| Senate Overview | /senate | live |
| Governance | /governance | live |
| Economics | /economics | live |
| Treasury | /treasury | live |
| Vault + GOV-001–006 | /vault, /vault/gov-* | live |
| Academia | /academia | live |
| ISO Collaborators | /iso-collaborators | live |
| Products | /products | live |
| Bounty Board | /bountyboard | live |
| Hiring | /hiring | live |
| Services | /services | live |
| Connect | /connect | live |

**paths:** `/senate`, `/governance`, `/economics`, `/treasury`, `/vault`, `/vault/gov-001` through `/vault/gov-006`, `/academia`, `/iso-collaborators`, `/products`, `/bountyboard`, `/hiring`, `/services`, `/connect`

### Tier 3 — "Building" (id: 3, entry: `/sig-arena`)
Coming soon / under construction.

**navLinks:** SigArena, Refinery, Wave Registry, Switchboard

**Pages:**
| Page | Route | Status |
|------|-------|--------|
| SigArena | /sig-arena | wip |
| Refinery | /refinery | empty |
| Wave Registry | /wave-registry | empty |
| Switchboard | /switchboard | empty |
| Kingdoms Tile Map | / | live |

**paths:** `/`, `/sig-arena`, `/refinery`, `/wave-registry`, `/switchboard`, `/kingdoms`

## Changes

### 1. `pages.json` — Replace `layers` array (5 entries → 3) and update `fallbackLinks`
- Keep `statusColors`, `tileZero`, `extras` untouched
- New fallbackLinks: Governance, KA§§A, Forums, Economics
- Restructure all pages into 3 layers with new slot numbering

### 2. `_nav.js` line 33
```js
// FROM:
var TAB_LABELS = { 1:'Civitae', 2:'Command', 3:'KA§§A', 4:'Lab', 5:'Senate' };
// TO:
var TAB_LABELS = { 1:'Active', 2:'Context', 3:'Building' };
```

### 3. `index.html` — Leave as-is (Option B)
The inline nav links are all valid URLs. Minor cosmetic inconsistency (Building tab active but inline nav links to Active-tier pages) is acceptable for a data-only change.

## DO NOT Change
- `app/routes/pages.py` — all routes stay exactly as they are
- Any HTML file content or functionality
- Any API endpoint
- Any URL — paths stay the same, they just activate different nav tabs

## 3D Map Buildings (Opening Page)
8 buildings on the landing 3D map, each linking to a working interactive page:

| Building | Links To | Route |
|----------|----------|-------|
| KA§§A | The board itself (5-tab interactive tool, NOT the HTML description pages) | /kassa |
| Forums | Town Hall | /forums |
| COMMAND | The Console (COMMAND = Console, one building) | /console |
| Missions | Dispatch center | /missions |
| Governance | Courthouse | /governance |
| Academia | Academy / onboarding | /academia |
| Leaderboard | Arena | /leaderboard |
| Treasury | Vault / bank | /treasury |

**Clarification:** The KA§§A sub-pages (ISO Collaborators, Products, Bounty Board, Hiring, Services, Connect) are accessed through the KA§§A board's tabs — they are NOT separate buildings. They live in the Context tier as reference/detail pages.

## Verification
After changes, load these URLs and confirm correct tab is highlighted:

| URL | Expected Tab |
|-----|-------------|
| `/kassa` | Active |
| `/missions` | Active |
| `/forums` | Active |
| `/console` | SKIP (own topbar) |
| `/3d` | Active |
| `/governance` | Context |
| `/economics` | Context |
| `/senate` | Context |
| `/products` | Context |
| `/iso-collaborators` | Context |
| `/sig-arena` | Building |
| `/` | Building |
| `/xyz` (bad path) | Fallback links, no tab |
