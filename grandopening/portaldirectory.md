The current entry points are all immersive experiences — the hex map (`kingdoms.html` at `/`), the 3D world (`world.html` at `/world`), and the About page (`civitas.html` at `/civitas`). None of them function as a scannable directory. The `sitemap.html` is the closest thing, but it's an admin tool (site editor with iframe preview), not a public-facing portal page. [11-cite-0](#11-cite-0) [11-cite-1](#11-cite-1) 

The good news: `pages.json` already has the complete hierarchy data — Tile Zero, Layer 1 (Active with subsections), Layer 2 (Context with subsections), Layer 3 (Building). Every page has `slot`, `name`, `route`, `file`, `status`, `note`, and `indent` fields. Both `_nav.js` and `sitemap.html` already fetch and parse this file dynamically. [11-cite-2](#11-cite-2) [11-cite-3](#11-cite-3) 

Here's what the directory page should be:

```
┌──────────────────────────────────────────────────────────────┐
│                         SIG NOMY                             │
│          Constitutional Agent Economy · Directory            │
│                                                              │
│  ┌─ TILE ZERO ─────────────────────────────────────────────┐ │
│  │  ● Kingdoms (Landing)  /           Hex map directory    │ │
│  │  ● About               /civitas                         │ │
│  │  ● Contact             /contact                         │ │
│  │  ● Grand Opening       /grand-opening                   │ │
│  │    ● Black Card        /black-card                      │ │
│  │    ● Early Believers   /early-believers                 │ │
│  │    ● Fee Credit Packs  /fee-credits                     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ ACTIVE — LIVE & INTERACTIVE ───────────────────────────┐ │
│  │  LIVE AND INTERACTIVE                                   │ │
│  │  ● 3D World (Hub)     /world    3D hub — buildings...   │ │
│  │  ● KA§§A Board        /kassa    5-tab marketplace       │ │
│  │  ...                                                    │ │
│  │  USER                                                   │ │
│  │  ● Earnings Matrix    /earnings-matrix                  │ │
│  │  ...                                                    │ │
│  │  TOOLS                                                  │ │
│  │  ● Console            /console  Operator cockpit        │ │
│  │  ...                                                    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ CONTEXT — PROTOCOL & REFERENCE ────────────────────────┐ │
│  │  ...                                                    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─ BUILDING — COMING ONLINE ──────────────────────────────┐ │
│  │  ...                                                    │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```