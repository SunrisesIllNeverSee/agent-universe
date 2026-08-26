# SEO / GEO / AEO — Phased Implementation Plan for signomy.xyz (agent-universe)

**Date:** 2026-08-24
**Target:** signomy.xyz — served by the agent-universe repo
**Repo:** `/path/to/agent-universe/`
**Reference playbook:** `docs/seo-aeo-geo-build-package/` (in this same repo)
**Reference implementation:** signalaf.com (7 phases shipped — use as template, do not modify)

---

## Current state of signomy.xyz

| Element | Status | Detail |
|---------|--------|--------|
| OG image | ✅ PNG | `/og-preview.png` — but only 23/60 pages have og:image meta |
| Twitter card | ⚠️ Partial | Only 26/60 pages have twitter:card |
| Canonical | ✅ Good | 58/60 pages have canonical |
| Meta description | ⚠️ Partial | 47/60 pages have meta description |
| Organization JSON-LD | ✅ Present | On homepage |
| WebSite JSON-LD | ✅ Present | On homepage |
| SoftwareApplication JSON-LD | ✅ Present | On homepage |
| BreadcrumbList | ⚠️ Partial | 23/60 pages |
| FAQPage | ⚠️ Partial | 24/60 pages |
| DefinedTerm | ❌ Minimal | Only 4 pages |
| ScholarlyArticle | ✅ Present | On homepage (references Conservation Law) |
| llms.txt | ✅ Present | Good content, covers core pages |
| robots.txt | ✅ Good | Allows all crawlers + AI bots explicitly |
| sitemap.xml | ⚠️ Incomplete | 22 URLs in sitemap, 60 HTML pages exist — 38 pages missing |
| sitemap-v2.xml | ⚠️ Incomplete | 20 URLs — also missing most pages |
| IndexNow key | ❓ Unknown | Need to check |
| GSC | ❓ Unknown | Need to check |
| Screaming Frog audit | ❌ Not run | |
| AEO audit | ❌ Not run | |
| Content layer (concept/guide pages) | ❌ None | No /concepts/, /guides/, /vs/ pages |
| llms-full.txt | ❌ Missing | |

**Bottom line:** The foundation is partially built (JSON-LD on core pages, llms.txt, robots.txt). The big gaps are: 37 pages missing OG meta, 38 pages missing from sitemap, no content layer, no audit, no GSC, no AEO reconciliation.

---

## The 8 phases

Each phase is self-contained. Execute in order.

| Phase | What | Effort |
|-------|------|--------|
| 1 | Foundation: OG/meta/sitemap completeness | ~2 hrs |
| 2 | JSON-LD completion across all pages | ~3 hrs |
| 3 | llms.txt + llms-full.txt + AI discoverability | ~1 hr |
| 4 | Content layer (concept/guide/FAQ pages) | ~1 day |
| 5 | Screaming Frog audit + fix campaign | ~4 hrs |
| 6 | Indexing push + GSC setup | ~1 hr |
| 7 | AEO reconciliation (query association) | ~3 hrs |
| 8 | Maintenance cadence setup | ~1 hr |

---

## Phase 1 — Foundation: OG/meta/sitemap completeness

**Goal:** Every public page has correct OG meta, twitter card, canonical, meta description, and is in the sitemap.

**Current gaps:**
- 37 pages missing og:image
- 34 pages missing twitter:card
- 13 pages missing meta description
- 38 pages missing from sitemap.xml

**Tasks:**
1. Enumerate all public HTML pages in `frontend/` (exclude 404, admin, console — those are disallowed in robots.txt)
2. For each page, verify/add:
   - `<meta property="og:title" content="...">`
   - `<meta property="og:description" content="...">`
   - `<meta property="og:url" content="https://signomy.xyz/<page>">`
   - `<meta property="og:image" content="https://signomy.xyz/og-preview.png">`
   - `<meta property="og:image:width" content="1200">`
   - `<meta property="og:image:height" content="630">`
   - `<meta name="twitter:card" content="summary_large_image">`
   - `<meta name="twitter:image" content="https://signomy.xyz/og-preview.png">`
   - `<link rel="canonical" href="https://signomy.xyz/<page>">`
   - `<meta name="description" content="...">` (≤155 chars)
   - `<title>` (≤60 chars)
3. Update sitemap.xml (and sitemap-v2.xml) to include all public pages
4. Verify robots.txt sitemap reference points to the correct sitemap
5. Verify at https://www.opengraph.xyz

**Acceptance:** Every public page has OG meta, twitter card, canonical, meta description. Sitemap lists every public page.

---

## Phase 2 — JSON-LD completion across all pages

**Goal:** Every page has appropriate structured data.

**Current state:** Core pages (index, kassa, missions, governance, etc.) have Organization + WebSite + FAQPage + BreadcrumbList. Many secondary pages have none.

**Tasks:**
1. Ensure Organization + WebSite JSON-LD is on EVERY public page (not just homepage). This is typically done via a shared layout/header include.
2. Add BreadcrumbList to all sub-pages that don't have it (37 pages currently missing):
   - Home → Kassa, Home → Missions, Home → Governance, Home → Treasury, etc.
3. Add FAQPage to pages that have Q&A content but no FAQPage schema
4. Add DefinedTerm schema to pages that define concepts:
   - /moses — MO§ES™ definition
   - /governance — governance concepts
   - /economics — economic tier definitions
   - /vault — governance document concepts
5. Add SoftwareApplication schema to pages that describe product features (already on homepage — extend to /kassa, /missions, /sig-arena)
6. Add ItemList schema to list pages:
   - /leaderboard — list of ranked agents
   - /missions — list of missions
   - /bountyboard — list of bounties
   - /helpwanted — list of positions
7. Validate every page at https://validator.schema.org
8. Validate at https://search.google.com/test/rich-results

**Acceptance:** Every public page has Organization + WebSite + at least one content-type schema (BreadcrumbList/FAQPage/DefinedTerm/ItemList/SoftwareApplication). All pass schema.org validator with 0 errors.

---

## Phase 3 — llms.txt + llms-full.txt + AI discoverability

**Goal:** AI engines can discover and parse all canonical content.

**Tasks:**
1. Verify llms.txt links all resolve (no 404s):
   ```bash
   curl -s https://signomy.xyz/llms.txt | grep -oE 'https://signomy.xyz[^ )]+' | while read url; do
     code=$(curl -s --max-time 5 -o /dev/null -w "%{http_code}" "$url")
     [ "$code" != "200" ] && echo "$code $url"
   done
   ```
2. Add any new pages from Phases 1-2 to llms.txt
3. Create `/llms-full.txt` — inlines full definitions for maximum citation coverage:
   - Full CIVITAE definition
   - Full Signomy definition
   - Full MO§ES™ governance description
   - Agent trust tier definitions
   - Economy tier definitions
   - Key concept definitions
4. Verify robots.txt explicitly allows AI crawlers (already confirmed: GPTBot, ClaudeBot, Google-Extended, PerplexityBot, Applebot-Extended — all allowed)
5. Add CCBot and anthropic-ai to the AI crawler allow list if missing
6. Verify /agent.json and /.well-known/mcp-server-card.json are accessible

**Acceptance:** llms.txt has zero broken links. llms-full.txt exists with full definitions. robots.txt allows all known AI crawlers.

---

## Phase 4 — Content layer (concept/guide/FAQ pages)

**Goal:** Build definitional content pages that AI engines cite.

**Load Search Authority canon context BEFORE writing any definitional content:**
```bash
python3 ~/Developer/_control/search-authority/canon_cli.py context signomy
python3 ~/Developer/_control/search-authority/canon_cli.py context civitae
python3 ~/Developer/_control/search-authority/canon_cli.py context moses
python3 ~/Developer/_control/search-authority/canon_cli.py context ecosystem
```

**Tasks — concept pages (one per key term):**
1. `/concepts/governed-marketplace` — "What is a governed AI agent marketplace?"
2. `/concepts/civitae` — "What is CIVITAE?"
3. `/concepts/signomy` — "What is Signomy?"
4. `/concepts/agent-trust-tiers` — "What are agent trust tiers?"
5. `/concepts/constitutional-ai` — "What is constitutional AI governance?"
6. `/concepts/agent-provisioning` — "What is agent provisioning?"
7. `/concepts/seed-provenance` — "What is seed provenance and DOI tracking?"
8. `/concepts/kassa` — "What is KA§§A?"
9. `/concepts/sig-arena` — "What is SigArena?"
10. `/concepts/governance-vacuum` — "What is a governance vacuum?"

**Tasks — guide pages:**
11. `/guides/how-to-register-an-agent` — step-by-step agent registration
12. `/guides/how-to-post-a-mission` — step-by-step mission posting
13. `/guides/how-to-join-a-mission` — step-by-step slot filling
14. `/guides/how-to-use-the-mcp-bridge` — MCP integration guide

**Tasks — comparison pages:**
15. `/vs/langchain` — Signomy/CIVITAE vs LangChain
16. `/vs/crew-ai` — Signomy/CIVITAE vs CrewAI
17. `/vs/auto-gpt` — Signomy/CIVITAE vs AutoGPT
18. `/vs/agent-arena` — Signomy/CIVITAE vs LMSYS Agent Arena

**Tasks — FAQ:**
19. Expand the existing FAQ content (24 pages already have FAQPage schema — ensure the FAQ content itself is comprehensive)
20. Create a dedicated `/faq` page with 15-20 Q&A entries

**After all pages built:**
21. Update sitemap.xml with all new pages
22. Update llms.txt with all new pages
23. Add BreadcrumbList + DefinedTerm/FAQPage JSON-LD to new pages
24. Add OG meta to new pages (Phase 1 patterns)

**Content rules (CRITICAL — from signalaf.com AEO audit learnings):**
- Each page targets exactly ONE search intent
- Opening paragraph uses NATURAL QUERY LANGUAGE, not proprietary vocabulary
  BAD: "The CIVITAE platform provides..."
  GOOD: "A governed AI agent marketplace is..."
- One canonical definition per concept (no competing definitions across pages)
- H1 = the question, first sentence = the answer
- Tables and step-by-steps over prose (AI engines extract these preferentially)
- Link back to the canonical hub page with consistent anchor text
- ≤155 char meta description, ≤60 char title

**Acceptance:** 10 concept + 4 guide + 4 comparison + 1 FAQ page built. All in sitemap + llms.txt. All have JSON-LD + OG meta.

---

## Phase 5 — Screaming Frog audit + fix campaign

**Goal:** Find and fix all technical SEO issues.

**Tasks:**
1. Run Screaming Frog crawl on signomy.xyz (now ~80 pages after Phase 4)
   - If SF is not installed, use a Python script with requests + BeautifulSoup
2. Export: All Internal Links, All External Links, Orphan Pages, Redirects, Issues
3. Build prioritized fix list:
   broken links > redirects > security headers > meta > titles > H1/H2 > images
4. Fix all issues in priority order
5. Re-crawl to verify (compare crawl 1 vs crawl 2)
6. Track issue count — should never increase

**What to look for:**
- 404s and broken links
- Redirect chains (flatten A→C, not A→B→C)
- Orphan pages (in sitemap but not linked internally)
- Missing/duplicate meta descriptions (≤155 chars)
- Long page titles (≤60 chars)
- Missing H1 (every page needs exactly one)
- Duplicate H2s
- Missing security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
- Crawl depth (no page >3 clicks from homepage)
- Images missing width/height

**Acceptance:** 0 broken links, 0 redirect chains, 0 missing security headers, all meta ≤155 chars, all titles ≤60 chars.

---

## Phase 6 — Indexing push + GSC setup

**Goal:** Get all pages indexed by Google and Bing.

**Tasks:**
1. Check if GSC is set up for signomy.xyz (Search Console → properties)
2. If not set up, document setup instructions for owner
3. Submit sitemap.xml
4. Request indexing on key pages (homepage, concept pages, FAQ)
5. Check if IndexNow key file exists on signomy.xyz
6. If missing, set up IndexNow:
   ```bash
   openssl rand -hex 16  → save as <key>.txt in frontend/
   ```
7. Push all URLs to IndexNow:
   ```bash
   curl -X POST "https://api.indexnow.org/IndexNow" \
     -H "Content-Type: application/json" \
     -d '{"host":"signomy.xyz","key":"<key>","keyLocation":"https://signomy.xyz/<key>.txt","urlList":[...]}'
   ```
8. Adapt gsc.mjs toolkit for signomy.xyz property (reference: docs/seo-aeo-geo-build-package/gsc-toolkit/)
9. Run check:index to verify all sitemap URLs are indexed

**Acceptance:** All sitemap URLs indexed by Google. All URLs pushed to IndexNow.

---

## Phase 7 — AEO reconciliation (query association)

**Goal:** Fix the query association gap — ensure pages are selected as the answer.

**Tasks:**
1. Build a 46-prompt test panel for signomy.xyz:
   Named/branded (20): "What is Signomy?", "What is CIVITAE?", "What is KA§§A?", etc.
   Broad discovery (26): "What is a governed AI agent marketplace?", "How to register an AI agent?", "Constitutional AI governance", etc.
   (Adapt from signalaf.com's panel in docs/seo-aeo-geo-build-package/aeo-audit/prompt-panel/PERPLEXITY_PROMPTS.md)

2. Run the panel across 7 engines:
   ChatGPT Search, Perplexity, Claude, Gemini, Grok, Google AI Overviews, Bing Copilot
   (Run each query 2-3 times — LLMs have variance)

3. Score results per query:
   - Mentioned? (yes/no)
   - Cited? (yes/no — did it link to signomy.xyz?)
   - Correct? (yes/no)
   - Hallucinated? (yes/no)
   - Which competitor cited instead?

4. Apply the 5-tier reconciliation (proven on signalaf.com):
   Tier 1: Rewrite opening paragraphs to use natural query language
   Tier 2: Canonicalize shared facts (one definition per concept)
   Tier 3: Disambiguate entity collisions:
     - Signomy vs Signal Messenger
     - CIVITAE vs civitas (generic)
     - MO§ES vs biblical Moses
   Tier 4: Strengthen internal nav with category language
   Tier 5: Align external descriptions (GitHub, npm, PyPI)

5. Re-run the audit after fixes
6. Track citation share over time

**Acceptance:** Broad discovery prompt retrieval rate improves from baseline. Named prompt retrieval >90%.

---

## Phase 8 — Maintenance cadence setup

**Goal:** Establish the recurring cadence that keeps citation share growing.

**Tasks:**
1. Create a citation tracking spreadsheet for signomy.xyz:
   - 10-15 target queries
   - Columns: date, engine, query, mentioned, cited, competitor cited instead
2. Document the weekly citation query test procedure
3. Document the monthly AEO citation audit procedure
4. Document the quarterly Screaming Frog crawl procedure
5. Set up IndexNow push script for new/changed URLs
6. Document the 70/30 rule (70% refresh, 30% new content)
7. Create a maintenance runbook

**Cadence:**
| Frequency | What | Time |
|-----------|------|------|
| Weekly | Citation query test (10-15 queries, incognito, 4 engines) | 15 min |
| Weekly | GSC AI Overviews + queries | 5 min |
| Bi-weekly | Core page freshness refresh | 30 min |
| Monthly | Full AEO citation audit | 30 min |
| Monthly | IndexNow push for new/changed URLs | 5 min |
| Quarterly | Screaming Frog crawl | 30 min |
| Quarterly | Content decay review | 1 hour |
| Annually | Full content audit | half day |

**Acceptance:** Maintenance runbook exists. Citation tracking spreadsheet initialized with baseline queries.
