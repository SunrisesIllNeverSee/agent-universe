# SEO / AEO / GEO Build Package v2.0

> **Updated 2026-08-25.** Consolidates the full SEO/GEO/AEO implementation
> playbook, the 7-engine AEO audit results, the query reconciliation plan,
> the Google Search Console toolkit, and the academic GEO strategy into one
> portable package.
>
> **Purpose:** Apply this to any site. The reference implementation is
> signalaf.com (Next.js 15, Vercel). The playbook was originally written for
> mos2es.com (static HTML, Netlify) but the principles are framework-agnostic.

---

## What's in this package

```
seo-aeo-geo-build-package/
├── README.md                          ← you are here
├── playbook/
│   └── SEO_GEO_AEO_PLAYBOOK.md        ← 606 lines. The master 7-phase strategy.
├── aeo-audit/
│   ├── README.md                      ← audit overview (7 engines, 46 prompts, 322 results)
│   ├── AEO_RECONCILIATION_PLAN_AND_EXECUTION.md  ← 681 lines. Complete fix plan (5 tiers, all implemented)
│   ├── CONTENT_BUILD_QUEUE.md         ← 24/25 pages built. vs/ pages, listicles, niche posts
│   ├── CALCOM_LESSONS_ANALYSIS.md     ← Cal.com SEO lessons analysis
│   ├── PERPLEXITY_PROMPTS.md          ← the fixed 46-prompt test panel
│   ├── audit-results/                ← scored logs from 7 engines
│   │   ├── CHATGPT_SEARCH_LOG_0817.md
│   │   ├── CLAUDE_LOG.md
│   │   ├── COPILOT_LOG.md
│   │   ├── GEMINI_LOG.md
│   │   ├── GOOGLE_SEARCH_LOG.md
│   │   ├── GROK_LOG.md
│   │   └── PERPLEXITY_LOG.md
│   ├── audit-raw/                     ← full rendered responses (unabridged)
│   │   ├── CHATGPT_SEARCH_RAW.md
│   │   ├── CLAUDE_RAW.md
│   │   ├── COPILOT_RAW.md
│   │   ├── GEMINI_RAW.md
│   │   ├── GOOGLE_SEARCH_RAW.md
│   │   └── GROK_RAW.md
│   └── reconciliation/
│       └── RECONCILIATION_SHEET.md    ← query-to-page reconciliation
├── gsc-toolkit/
│   ├── README.md                      ← GSC setup guide (service account, APIs, property)
│   └── gsc.mjs                        ← 387 lines. Full GSC + Indexing API toolkit
└── academic-geo/
    ├── ACADEMIC_GEO_STRATEGY.md       ← 455 lines. Academic + governance convergence strategy
    ├── SEO_GEO_PLAN.md                ← 452 lines. Full SEO + GEO implementation plan
    ├── ECOSYSTEM_INVENTORY.md         ← 382 lines. Inventory of all surfaces (22 repos, 3 sites, 6 Zenodo)
    ├── OWNER_CHECKLIST.md             ← 386 lines. Owner action items
    └── RUNBOOK.md                     ← 412 lines. Operational runbook
```

---

## How to use this package

### Phase 1: Foundation (playbook/)
Read `playbook/SEO_GEO_AEO_PLAYBOOK.md` first. It walks through the 7-phase
implementation shipped on signalaf.com:

1. Fix OG image (SVG → PNG)
2. JSON-LD structured data (Organization, WebSite, DefinedTerm, BreadcrumbList, FAQPage)
3. llms.txt (AI discoverability)
4. Per-page dynamic OG images
5. npm + GitHub discoverability (keywords, topics, repo website)
6. Content layer (comparison, alternatives, guides, metrics, tools, topic hubs, blog)
7. Screaming Frog site audit + fix campaign

### Phase 2: AEO Audit (aeo-audit/)
Run the 46-prompt test panel across 7 engines. The audit results and
reconciliation sheet show exactly what's working and what's not.

Key finding from the signalaf.com audit:
- Named/branded prompts: 94.4% retrieval
- Broad discovery prompts: 11.1% retrieval
- Diagnosis: query association problem, not a page-count problem

The reconciliation plan (5 tiers) shows how to fix the gap:
- Tier 1: Rewrite opening paragraphs to use natural query language
- Tier 2: Canonicalize shared facts (operator count, classes, DOI)
- Tier 3: Disambiguate entity collisions
- Tier 4: Strengthen internal nav with category language
- Tier 5: Align external descriptions (GitHub, npm, Zenodo)

### Phase 3: Google Search Console (gsc-toolkit/)
Set up programmatic GSC access using the service account toolkit.

**Service account key location:** `~/.config/sigrank/gsc-sa.json`
**GCP project:** 694528229435
**Property:** `sc-domain:signalaf.com` (Domain property)

Commands:
```bash
export GSC_SA_KEY=~/.config/sigrank/gsc-sa.json
node gsc.mjs sitemaps:list          # registered sitemaps + error counts
node gsc.mjs sitemaps:submit        # resubmit sitemap.xml
node gsc.mjs index <url> [url...]   # push URLs to Indexing API
node gsc.mjs inspect <url>          # URL inspection (verdict + coverage)
node gsc.mjs analytics 28           # clicks/impressions last N days
node gsc.mjs check:index --push     # inspect all sitemap URLs + auto-push unindexed
```

### Phase 4: Academic GEO (academic-geo/)
For sites with academic/research foundations (DOIs, Zenodo, ORCID). The
convergence strategy ensures every surface points back to the owner as
canonical source.

---

## Maintenance cadence

| Frequency | What | Time |
|-----------|------|------|
| Weekly | Citation query test (10-15 queries, incognito) | 15 min |
| Weekly | GSC AI Overviews + queries | 5 min |
| Bi-weekly | Core page freshness refresh | 30 min |
| Monthly | Full AEO citation audit | 30 min |
| Monthly | IndexNow push for new/changed URLs | 5 min |
| Quarterly | Screaming Frog crawl | 30 min |
| Quarterly | Content decay review | 1 hour |
| Annually | Full content audit | Half day |

---

## What NOT to do

1. Don't block AI crawlers — being in the training corpus is the moat
2. Don't audit once and never re-run — citation share shifts weekly
3. Don't trust a single LLM snapshot — run queries 2-3 times
4. Don't create new content before refreshing existing — 70/30 rule
5. Don't push already-indexed URLs to GSC — wastes API quota
6. Don't change robots.txt without verifying AI bot access after
7. Don't forget llms.txt is manual — new pages need to be added by hand
8. Don't ignore Perplexity — it's the most citation-heavy engine
9. Don't skip the feedback loop — every finding needs an action item
10. Don't use SVG for OG images — most platforms don't render them

---

## Reference implementations

| Site | Framework | Host | Pages | Status |
|------|-----------|------|-------|--------|
| signalaf.com | Next.js 15 | Vercel | ~145 URLs | 7 phases shipped, audit complete, 5 tiers implemented |
| mos2es.com | Static HTML | Netlify | 11 pages | Playbook written, partial implementation |
| sigeconomy.com | Next.js | Cloudflare | ~20 URLs | 16 vs/ pages built |

---

## Tools

| Tool | Price | What |
|------|-------|------|
| Screaming Frog SEO Spider | Free (500 URLs) | Full site crawl |
| Google Search Console | Free | Index status, AI Overviews, queries, sitemaps |
| IndexNow | Free | Instant Bing/Yandex/Naver indexing |
| validator.schema.org | Free | JSON-LD validation |
| search.google.com/test/rich-results | Free | Rich results test |
| opengraph.xyz | Free | OG card preview |
| GSC API (gsc.mjs) | Free | Programmatic index/queries/sitemaps |

---

*Built from the signalaf.com SEO/GEO/AEO implementation (July-August 2026).
7 phases shipped, 7-engine audit run, 5 reconciliation tiers implemented,
24 content pages built, 2 Screaming Frog crawls (B- → A-).*
