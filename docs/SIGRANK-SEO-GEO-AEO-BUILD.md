---
title: SigRank SEO/GEO/AEO Build — complete record + implementation reference
description: Full record of the SEO/GEO/AEO workstream built for signalaf.com. 6-phase implementation plan, 7-workstream growth roadmap, what shipped (14 JSON-LD types, llms.txt, dynamic OG cards, PostHog, GSC index push), and what's pending. Shared with agent-universe as a reference implementation for the same approach.
date: 2026-07-05
source: ~/Desktop/SigRank/Devins_Plans/growth/
---

# SigRank SEO/GEO/AEO Build — complete record

> Shared with agent-universe as a reference implementation. The same approach
> (JSON-LD structured data, llms.txt, dynamic OG cards, GSC index pushing,
> PostHog funnel measurement) applies to any agent marketplace that wants to
> be cited by AI engines and found via classic search.

## Thesis

SigRank is a **data company** that happens to ship a leaderboard. Its growth
comes from two things:

1. **Becoming the cited primary source** of AI-operator-efficiency data (GEO / AEO).
2. **Measuring its own funnel** so every channel (AI search, community, viral) is legible.

The Profound AEO report's verdict — **7.2% visibility, 0% citation, #33** — was
a *data-company-not-acting-like-one* problem. The entire build below was designed
to fix that.

---

## The 6-phase implementation plan (seo-geo-plan.md)

### Phase 1 — OG image fix (raster PNG via next/og)

**Problem:** OG image was `/og.svg`; most platforms don't render SVG → broken
link previews everywhere.

**Fix:** File-based `opengraph-image` convention using `next/og` (Satori) with
system fonts (no remote font fetch = no 500 errors). Generates real 1200×630 PNG.

**Shipped:**
- `public/og-v2.png` (1200×630, versioned filename for cache-busting)
- `app/user/[codename]/opengraph-image.tsx` — per-operator dynamic card (rank + codename + yield + class)
- `app/board/[window]/opengraph-image.tsx` — per-board-window card (window label + top 3)
- `lib/seo.ts` — `OG_IMAGE` constant pointing to `/og-v2.png`, `withOG()` helper

### Phase 2 — JSON-LD structured data (the biggest SEO + GEO lever)

**Problem:** Zero structured data anywhere. AI engines can't parse or cite the data.

**Fix:** Typed Schema.org builders + a tiny server component, wired to every
money page.

**Shipped — 14 JSON-LD builder functions in `lib/jsonld.ts` (447 lines):**

| Builder | Schema type | Where it's wired |
|---|---|---|
| `organization()` | Organization | `app/layout.tsx` (site-wide) |
| `website()` | WebSite | `app/layout.tsx` (site-wide) |
| `leaderboardItemList()` | ItemList | `app/board/[window]/page.tsx` |
| `operatorProfile()` | ProfilePage | `app/user/[codename]/page.tsx` |
| `breadcrumb()` | BreadcrumbList | All wiki pages, /about, /hall, /research, /methodology, /science |
| `definedTerm()` | DefinedTerm | All 6 wiki pages (signal-drift, three-degrees, verification, local-agent, measured-alongside, methodology-refinement) |
| `sigrankDataset()` | Dataset | `/methodology`, `/board/all`, `/research/[slug]` (the WS1 citation play) |
| `faqPage()` | FAQPage | `/methodology` |
| `researchArticle()` | ScholarlyArticle | `/research/[slug]` |
| `conservationLawArticle()` | ScholarlyArticle | `/science` |
| `mosesPatent()` | CreativeWork | `/science` |
| `experimentalRecordDataset()` | Dataset | `/science` |
| `transformationHarnessDataset()` | Dataset | `/science` |
| `propositionsDataset()` | Dataset | `/science` |

**Renderer:** `components/seo/JsonLd.tsx` — server-only component that renders
`<script type="application/ld+json">` with `<` escaped to prevent breakout.

**Coverage:** 15+ pages emit structured data. All pass schema.org validator.

### Phase 3 — llms.txt (GEO convention)

**What:** A curated plain-text map at `/llms.txt` telling AI crawlers what the
site is and where the canonical content lives.

**Shipped:** `app/llms.txt/route.ts` — includes site description, core pages
(leaderboard, board windows, hall, compare), concepts (wiki definitions),
tooling (npm, GitHub), and Dataset license (CC-BY-4.0). Added to sitemap.

### Phase 4 — Per-page dynamic OG cards

**Shipped:**
- `app/user/[codename]/opengraph-image.tsx` — fetches operator data, renders rank + codename + yield + class tier
- `app/board/[window]/opengraph-image.tsx` — renders window label + top 3 operators

File-convention route images automatically override the root OG image for those
segments. No `lib/seo.ts` change needed.

### Phase 5 — npm + GitHub discoverability

**Shipped:**
- `package.json` keywords (mcp, model-context-protocol, ai-agents, claude, llm, token-telemetry, leaderboard, cli, tui, yield-cascade, sigrank, agent-tools, on-device)
- GitHub topics on both repos
- Repo "Website" field set to signalaf.com

### Phase 6 — Final verification & submission

**Shipped:**
- `robots.ts` — allows all crawlers (incl. AI bots), references sitemap
- `sitemap.ts` — dynamic: static routes + board windows + every ranked operator
- GSC sitemap submitted
- Bing Webmaster Tools sitemap submitted (feeds ChatGPT search)
- Rich Results Test passes for home, /board/all, /user/<codename>, /wiki/*

---

## The 7-workstream growth roadmap

### WS1 — Dataset + "The Index" (highest leverage)

**Why first:** SigRank's unfair advantage — they own data nobody else has. Direct
fix for 0% citation.

**Shipped:**
- `sigrankDataset()` JSON-LD on `/methodology` + `/board/all` + `/research/[slug]`
- `/methodology` page — "The SigRank Index" with key figures rendered live from API
- `faqPage()` JSON-LD on `/methodology`
- `/methodology` added to sitemap + `llms.txt`

### WS2 — PostHog instrumentation (measurement)

**Why:** Without it, every channel is blind. Privacy guardrail: server-side
capture only, no CLI telemetry.

**Shipped:**
- `lib/posthog/client.ts` — posthog-js init with reverse proxy, autocapture disabled, masking
- `lib/posthog/server.ts` — server-side capture (`captureServer`)
- `lib/posthog/events.ts` — typed event tracker (`track`)
- `components/analytics/PostHogProvider.tsx` — client-side provider in `app/layout.tsx`
- Server events: `snapshot_submitted`, `checkout_started`, `device_rotated`, `device_enrolled`
- Client events: leaderboard interactions, split-flap card, checkout, pageviews

### WS3 — PostHog dashboards

**Shipped:** Dashboards built (activation funnel, channels, retention, revenue).
Per SCRATCHPAD: "WS3 dashboards built."

### WS4 — Profound recurring re-run

**Status:** 30-prompt AEO re-run set drafted (`profound-rerun-prompts.md`) with
competitor overrides (YouGov → ccusage/tokscale). Not yet scheduled.

### WS5 — Quarterly data report

**Status:** `/research/[slug]` page exists with `ScholarlyArticle` + `Dataset`
JSON-LD. Q1 report drafted (Parts A/B/C). Distribution (newsletters, HN,
r/LocalLLaMA) not yet done.

### WS6 — GTM tool wiring (Common Room, Clay)

**Status:** Not done. Common Room would connect GitHub + npm to track
stars/issues/installs. Clay would enrich stargazers for consent-first outbound.

### WS7 — Dev MCP for client work

**Status:** Not done. Independent of SigRank.

---

## GSC — Google Search Console

**Shipped:**
- `scripts/gsc/gsc.mjs` — GSC toolkit (check:index, push)
- 26 URLs from sitemap inspected (2026-07-04):
  - 8 indexed (homepage, /board/30d, /upgrade, /login, 4 wiki pages)
  - 17 discovered-but-not-indexed
  - 1 unknown (/llms.txt)
- 18 unindexed URLs pushed to Google Indexing API (all 18 ok, 0 skipped)
- Re-inspect due ~07-07 to 07-09 to see if they flip

**Gap:** `/score` is still discovered-not-indexed. This is the conversion-critical
page (ghost-rank preview). The index push should help, but if it doesn't flip,
may need internal links from already-indexed pages pointing to `/score`.

---

## What's not shipped (pending)

| Item | Status | Effort |
|---|---|---|
| Profound recurring re-run | Prompts drafted, not scheduled | ~30 min to schedule |
| Quarterly report distribution | Report drafted, not distributed | ~1 hour |
| GTM tool wiring (Common Room, Clay) | Not started | ~half day |
| Dev MCP for client work | Not started | Independent |

---

## Architecture reference (for agent-universe)

The same approach applies to any agent marketplace:

1. **JSON-LD structured data** — Organization, WebSite, ItemList (for marketplace
   listings), ProfilePage (for agent profiles), BreadcrumbList, DefinedTerm (for
   ontology/glossary), Dataset (if you publish data), FAQPage, SoftwareApplication
   (for each agent/tool listing).

2. **llms.txt** — curated plain-text map for AI crawlers. List the site, core
   pages, concepts, and tooling.

3. **Dynamic OG cards** — per-agent and per-category cards via `next/og`.

4. **GSC** — submit sitemap, request indexing on key pages, push unindexed URLs
   via the Indexing API.

5. **PostHog** — server-side capture only (privacy-safe), funnel events at API
   boundaries, client-side tracking on key interactions.

6. **Sitemap** — dynamic, includes every listing + every agent profile.

7. **Robots** — allow AI crawlers (GPTBot, ClaudeBot, PerplexityBot, etc.).

---

## Source documents

All planning docs live in `~/Desktop/SigRank/Devins_Plans/growth/`:

| Doc | Lines | What |
|---|---|---|
| `SIGRANK-MASTER-ROADMAP.md` | 120 | 7-workstream sequence by leverage |
| `seo-geo-plan.md` | 436 | The original 6-phase implementation plan |
| `sigrank-dataset-citation-plan.md` | — | Dataset JSON-LD + Index page + quarterly report |
| `sigrank-gtm-instrumentation-plan.md` | — | PostHog wiring plan |
| `sigrank-posthog-dashboards.md` | — | Dashboard definitions |
| `profound-rerun-prompts.md` | — | 30-prompt AEO re-run set |
| `INDEXING_DIAGNOSTIC_DEVIN_BRIEF.md` | — | GSC indexing diagnostic |
| `ACADEMIC_GEO_MAPPING_PROMPT.md` | 26K | Academic GEO mapping prompt |
| `academic-geo-signalf-implementation.md` | — | Academic/GEO implementation |
