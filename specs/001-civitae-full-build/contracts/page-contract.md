# Page Contract

Every HTML page in `frontend/` MUST satisfy this contract.

## Required Elements

| Element | Requirement |
|---------|------------|
| `<title>` | Descriptive — includes "Agent Universe" or "CIVITAE" |
| HUD nav or equivalent nav | Links to at least: `/civitas`, `/kingdoms`, `/kassa` |
| All `href` values | Clean URLs only — no `.html` extensions |
| No broken images | All `src=` paths resolve from `frontend/` root |
| Dark background | `#080812` or darker — no light theme in active pages |
| Mobile viewport meta | `<meta name="viewport" content="width=device-width, initial-scale=1.0">` |

## Layer Compliance

| Layer | Quality Gate |
|-------|-------------|
| 0–2 (live) | No placeholder text, no lorem ipsum, no "coming soon" |
| 3 (command) | Functional UI — may have limited real data |
| 4 (stubs) | Minimal page with title, nav, and "in development" notice |
| 5 (meta) | Can be incomplete until all other layers ship |

## Nav Link Standard

All pages use one of:
- `.hud-nav` (kingdoms-style dark HUD)
- `.nav-right` / `.nav-links` (civitas/kassa light nav)

Active page link MUST have `class="active"` or equivalent highlight.
