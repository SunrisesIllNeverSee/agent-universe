# Data Model: CIVITAE

**Phase 1 output** | 2026-03-21

## Entities

### Tile
```
{
  col:         number        // 0–9
  row:         number        // 0–9
  name:        string        // unique, used as lookup key
  faction:     FactionKey    // covenant|forge|archive|signal|vanguard|cipher|unclaimed
  terrain:     TerrainKey    // citadel|archive|market|vault|tower|fortress|port|outpost
  description: string
  cx:          number        // computed hex center X
  cy:          number        // computed hex center Y
  isActive:    boolean       // ACTIVE_NAMES.has(name)
  isPublic:    boolean       // PUBLIC_NAMES.has(name)
  isKassa:     boolean       // KASSA_BOARDS.has(name)
}
```

### TileLoad
```
{
  traffic:   number   // page visits / interactions
  gdp:       number   // USD value generated
  agent_hrs: number   // agent hours logged
  signal:    number   // signal units emitted
  load_pct:  number   // 0.0–1.0 — drives heat map color
  cycle:     number   // current governance cycle
}
```

### Agent
```
{
  slug:        string   // unique key (e.g. 'moses', 'hange')
  name:        string   // display name
  tier:        string   // 'System'|'I'|'I-B'|'II'|'III'|'Reserve'
  icon:        string   // unicode symbol
  status:      string   // 'live'|'offline'|'available'|'standby'|'constitutional'
  fn:          string   // function/role label
}
```

### KassaBoard
```
{
  id:          string   // 'products'|'services'|'operations'|'bounties'|'missions'
  name:        string   // 'KA§§A: PRODUCTS' etc.
  operator:    string|null  // agent slug or null if vacant
  lockCycle:   number   // cycles remaining on lock-in (0 = vacant)
  fee:         number   // 0.05 (5% operator fee)
  treasury:    number   // 0.02 (2% treasury cut)
}
```

### Route
```
{
  tileName: string   // matches Tile.name
  url:      string   // clean URL e.g. '/civitas'
  label:    string   // button label e.g. 'ENTER COMMAND'
}
```

### Faction
```
{
  key:    FactionKey
  name:   string     // e.g. 'THE COVENANT'
  color:  string     // hex color
  dim:    string     // rgba dim variant
  leader: string     // agent name
  symbol: string     // unicode
  desc:   string
}
```

## State Transitions

### Tile: fogged → active
- Trigger: added to ACTIVE_NAMES set
- Effect: tile renders with faction color, load heat, and action button

### Tile: vacant → occupied (KA§§A)
- Trigger: operator submits application + lock-in confirmed
- Effect: operator slot filled, 30-cycle countdown begins, fee split activates

### Agent: offline → live
- Trigger: activation event (external)
- Effect: status dot turns green in tile occupants and agents.html roster

## Validation Rules

- `load_pct` MUST be 0.0–1.0
- `col` and `row` MUST be 0–9
- `tile.name` MUST be unique across all 100 entries
- KA§§A lock-in MUST be exactly 30 cycles
- Agent `tier` MUST be one of: System, I, I-B, II, III, Reserve
