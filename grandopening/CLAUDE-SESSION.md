# CLAUDE SESSION — Wave Registry & Grand Opening Build

## What We Were Working On

Restructuring the **Grand Opening** showcase to properly separate three distinct entities:

1. **Wave Cascade** — the system itself, as a general showcase item
2. **Black Card** — operator tier product, standalone showcase
3. **Early Believers** — angel class product, standalone showcase

**Previous work:**
- Created BLACK-CARD-PROFILE.md with full wave cascade tables and entry/seats/bid-offer framework
- Created EARLY-BELIEVERS-PROFILE.md with distinct angel positioning and narrowing philosophy
- Discovered gap: grand-opening.html shows only 4 Black Card perks when 14 exist in backend (app/economy.py)
- Confirmed Wave Registry route exists at `/wave-registry` but is empty

## Where We Left Off

User clarification: These are **three separate showcase items**, not nested. No cross-referencing complexity.

- ✅ Markdown profiles created (BLACK-CARD-PROFILE.md, EARLY-BELIEVERS-PROFILE.md)
- ✅ Wave Registry route verified at `/wave-registry` with status="empty"
- ⏳ Wave Cascade markdown — not yet created (needs to be standalone general showcase)
- ⏳ Website reorder — grand opening docs structure still needs planning
- ⏳ Grand opening HTML — not yet updated with full perk list and separate items

## Build Order (For Reference)

1. **WEBSITE REORDER** — Determine structure: how Wave Cascade, Black Card, Early Believers sit in navigation/hierarchy
2. **GRAND OPENING DOCS** — Create WAVE-CASCADE.md standalone profile
3. **WAVE CASCADE** — Wire the general system showcase into Wave Registry route
4. **AGENTDASH** — Final layer integration (if applicable to this work)

## Active Files

| File | Status | Purpose |
|------|--------|---------|
| `BLACK-CARD-PROFILE.md` | ✅ Complete | Operator tier showcase with full perk list |
| `EARLY-BELIEVERS-PROFILE.md` | ✅ Complete | Angel class showcase with collective framing |
| `WAVE-CASCADE.md` | ⏳ TBD | System-level wave mechanic showcase (standalone) |
| `grand-opening.html` | ⏳ Needs update | Wire three items + full Black Card perks (14 items) |
| `websiteconfig.csv` | 📋 Reference | Current site structure |
| `AGENTDASH.md` | 📋 Reference | Agent dashboard (downstream work) |

## Key Technical Notes

- Black Card backend: 14 perks in `app/economy.py` (fee floor 2%, +10% revenue bonus, 20% credit line, etc.)
- Wave Cascade pattern: Already exists in COMMAND/DEPLOY systems (W1a/W1b/W2a/W2b/W3 gating)
- Trust tier system: Currently flattened to 5% fee cap during soft launch (normally Constitutional 5% → Black Card 2%)
- Three-phase grand opening: Phase I (1–7 days), Phase II (8–30 days), Phase III (31+)

## Next Action

Build WAVE-CASCADE.md as standalone general showcase, then wire website reorder structure.

---
*Last updated: 2026-04-03*
