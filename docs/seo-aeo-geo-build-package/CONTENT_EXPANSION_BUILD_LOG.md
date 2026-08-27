---
type: Build Log
title: Content Expansion Build Log — Phases 9-14
description: Documentation of the 42-page content expansion + footer build for signomy.xyz. Executed with 5 parallel agents on 2026-08-27.
tags: [signomy, content, build-log, seo, geo, aeo]
timestamp: 2026-08-27
---

# Content Expansion Build Log — Phases 9-14

**Date:** 2026-08-27
**Method:** 5 parallel subagents
**Duration:** ~15 minutes (parallel execution)

---

## What was built

### Phase 9: Footer (Agent A)
- **File:** `frontend/_footer.js` (230 lines)
- **Links:** 49 internal + external links across 6 columns
- **Injection:** Added `<script src="/assets/_footer.js?v=1"></script>` to 76 pages
- **Design:** Dark/gold theme, CSS Grid, mobile-responsive (6→2→1 columns)
- **Bottom bar:** "© 2026 Ello Cello LLC · Patent Pending 63/877,177 · MO§ES™ governs CIVITAE"

### Phase 10: Blog Posts (Agent B)
- **Files:** 12 pages in `frontend/blog/`
- **Schema:** Article JSON-LD with datePublished, dateModified, author
- **Content:** 800-1500 words each, tables/lists over prose, 6-9 internal links per post
- **Topics:** listicles, how-to guides, explainers, entity disambiguation

### Phase 11: /vs/ Comparison Pages (Agent C)
- **Files:** 15 new pages in `frontend/vs/` (20 total with existing 5)
- **Structure:** Comparison table (7 rows: Governance, Registration, Trust Tiers, Marketplace, Economics, Audit Trail, Constitutional Framework)
- **Fairness:** Each page includes "When to choose [Competitor]" section

### Phase 12: /alternatives/ Pages (Agent D)
- **Files:** 8 new pages in `frontend/alternatives/` (9 total with existing 1)
- **Schema:** ItemList JSON-LD on each page
- **Content:** Comparison tables of 4-7 alternatives per page

### Phase 13: /metrics/ Pages (Agent D)
- **Files:** 4 pages in `frontend/metrics/`
- **Schema:** DefinedTerm JSON-LD on each page
- **Content:** Formulas, calculation tables, score ranges

### Phase 13: /tools/ Pages (Agent E)
- **Files:** 3 pages in `frontend/tools/`
- **Schema:** SoftwareApplication JSON-LD on each page
- **Interactivity:** Vanilla JS calculators (no dependencies)

---

## Page inventory (before → after)

| Category | Before | After | Delta |
|----------|--------|-------|-------|
| Root | 57 | 57 | 0 |
| Concepts | 10 | 10 | 0 |
| Guides | 4 | 4 | 0 |
| /vs/ | 5 | 20 | +15 |
| /blog/ | 0 | 12 | +12 |
| /alternatives/ | 1 | 9 | +8 |
| /tools/ | 0 | 3 | +3 |
| /metrics/ | 0 | 4 | +4 |
| Footer | 0 | 1 | +1 |
| **Total pages** | **77** | **120** | **+43** |
| **Sitemap URLs** | **75** | **119** | **+44** |

---

## Quality verification

All 119 pages pass:
- og:image: 119/119
- twitter:card: 119/119
- meta description: 119/119 (all ≤155 chars)
- canonical: 119/119 (all clean URLs)
- Organization JSON-LD: 119/119
- BreadcrumbList: 119/119
- FAQPage: 119/119
- H1 (exactly 1): 119/119
- Title length: 119/119 (all ≤60 chars)
- Clean URLs: 119/119 (no .html in canonical/OG)

---

## Indexing pushes

- **GSC Indexing API:** 42 new pages pushed (12 blog + 15 vs + 8 alternatives + 3 tools + 4 metrics), all OK
- **GSC Sitemap:** sitemap-v2.xml resubmitted (119 URLs)
- **IndexNow:** Will push after deploy (key file needs to be live on Vercel first)

---

## Backlink strategy

Separate document created: `BACKLINK_STRATEGY_SIGNOMY.md`

Key findings from signalaf.com audit:
- 18 external backlinks found (16 replicable)
- Primary channels: GitHub repos, npm, PyPI, Smithery, Glama, SaaSHub
- Missing: AI tool directories, social platforms, academic citations
- Immediate actions: Update GitHub repo description, PyPI description, submit to Glama/SaaSHub

---

## What needs to happen next

1. **Deploy:** `git push` to trigger Vercel rebuild
2. **Post-deploy IndexNow:** Push 119 URLs after key file is live
3. **External alignment:** Update GitHub, PyPI, Smithery descriptions
4. **Directory submissions:** Submit to Glama, SaaSHub, aiagentsdirectory, pulsemcp
5. **Re-audit:** Run 46-prompt AEO panel 3-7 days after indexing
6. **Monitor:** Track citation share in CITATION_TRACKING_SIGNOMY.csv
