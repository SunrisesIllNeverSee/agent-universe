SEO / GEO / AEO — FULL IMPLEMENTATION FOR SIGNOMY.XYZ (AGENT-UNIVERSE)

============================================================
WHAT THIS IS
============================================================

Implement the full SEO/GEO/AEO playbook on signomy.xyz, which is served
by the agent-universe repo. The playbook package is already in this repo
at docs/seo-aeo-geo-build-package/. The reference implementation is
signalaf.com (7 phases shipped, AEO audit done, 5 reconciliation tiers
implemented). Use signalaf.com as the template. Do NOT modify signalaf.com.

The phased plan is at:
  docs/seo-aeo-geo-build-package/SIGNOMY_PHASED_IMPLEMENTATION_PLAN.md

Read it AND the playbook before starting:
  docs/seo-aeo-geo-build-package/playbook/SEO_GEO_AEO_PLAYBOOK.md
  docs/seo-aeo-geo-build-package/aeo-audit/AEO_RECONCILIATION_PLAN_AND_EXECUTION.md

============================================================
REPO
============================================================

  Repo:     /Users/dericmchenry/Developer/built/agent-universe/
  Site:     signomy.xyz
  Frontend: frontend/ (60 HTML pages, vanilla JS, no build pipeline)
  Backend:  app/ (FastAPI on :8300)
  Config:   config/pages.json (nav, portal, banner)
  Deploy:   Frontend on Vercel, backend on Railway

  Search Authority canon: ~/Developer/_control/search-authority/
  Canon CLI: python3 ~/Developer/_control/search-authority/canon_cli.py

============================================================
CURRENT STATE (audited 2026-08-24)
============================================================

  60 HTML pages in frontend/
  22 URLs in sitemap.xml (38 pages missing)
  23/60 pages have og:image
  26/60 pages have twitter:card
  47/60 pages have meta description
  58/60 pages have canonical
  26/60 pages have JSON-LD
  23/60 pages have BreadcrumbList
  24/60 pages have FAQPage
  4/60 pages have DefinedTerm
  llms.txt: present, good content
  robots.txt: present, allows AI bots
  OG image: /og-preview.png (PNG, good)
  No content layer (0 concept/guide/comparison pages)
  No Screaming Frog audit run
  No GSC set up
  No AEO audit run
  No IndexNow key file (unverified)

============================================================
EXECUTION RULES
============================================================

1. Execute phases in order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

2. Each phase has ACCEPTANCE criteria. Do not move to the next phase
   until the current phase passes acceptance.

3. Commit after each phase. Small, intentional commits.

4. Do NOT push to remote without explicit owner authorization. Commit locally.

5. Do NOT block AI crawlers in robots.txt. Being in the training corpus is the moat.

6. Do NOT create competing definitions. One canonical definition per concept.

7. Before writing definitional content (Phase 4), load Search Authority canon:
     python3 ~/Developer/_control/search-authority/canon_cli.py context signomy
     python3 ~/Developer/_control/search-authority/canon_cli.py context civitae
     python3 ~/Developer/_control/search-authority/canon_cli.py context moses
     python3 ~/Developer/_control/search-authority/canon_cli.py context ecosystem

8. Content rules (from signalaf.com AEO audit learnings):
   - Each page targets exactly ONE search intent
   - Opening paragraph uses NATURAL QUERY LANGUAGE, not proprietary vocabulary
   - H1 = the question, first sentence = the answer
   - Tables and step-by-steps over prose
   - Link back to canonical hub with consistent anchor text
   - ≤155 char meta description, ≤60 char title

9. For owner-only actions (GSC setup, Zenodo, ORCID), surface as a checklist.

10. Read the repo's CLAUDE.md and AGENTS.md before starting. Follow the
    session coordination protocol (SCRATCHPAD, set-role, claims).

============================================================
PHASE 1 — Foundation: OG/meta/sitemap completeness
============================================================

Goal: Every public page has correct OG meta, twitter card, canonical,
meta description, and is in the sitemap.

Tasks:
1. Enumerate all public HTML pages in frontend/ (exclude 404, admin,
   console — those are disallowed in robots.txt)
2. For each page, verify/add:
   - og:title, og:description, og:url
   - og:image = https://signomy.xyz/og-preview.png
   - og:image:width = 1200, og:image:height = 630
   - twitter:card = summary_large_image
   - twitter:image = https://signomy.xyz/og-preview.png
   - canonical link
   - meta description (≤155 chars)
   - title (≤60 chars)
3. Update sitemap.xml AND sitemap-v2.xml to include all public pages
4. Verify robots.txt sitemap reference points to the correct sitemap
5. Verify at https://www.opengraph.xyz

Acceptance: Every public page has OG meta, twitter card, canonical,
meta description. Sitemap lists every public page.

============================================================
PHASE 2 — JSON-LD completion across all pages
============================================================

Goal: Every page has appropriate structured data.

Tasks:
1. Ensure Organization + WebSite JSON-LD is on EVERY public page
   (not just homepage). Add to the shared header/_nav.js injection
   or to each page's <head>.
2. Add BreadcrumbList to all sub-pages that don't have it (37 pages):
   Home → Kassa, Home → Missions, Home → Governance, etc.
3. Add FAQPage to pages with Q&A content but no FAQPage schema
4. Add DefinedTerm schema to concept-defining pages:
   /moses — MO§ES™ definition
   /governance — governance concepts
   /economics — economic tier definitions
   /vault — governance document concepts
5. Add SoftwareApplication schema to product pages (/kassa, /missions,
   /sig-arena — already on homepage, extend to these)
6. Add ItemList schema to list pages:
   /leaderboard — ranked agents
   /missions — mission list
   /bountyboard — bounty list
   /helpwanted — position list
7. Validate every page at https://validator.schema.org
8. Validate at https://search.google.com/test/rich-results

Acceptance: Every public page has Organization + WebSite + at least
one content-type schema. All pass schema.org validator with 0 errors.

============================================================
PHASE 3 — llms.txt + llms-full.txt + AI discoverability
============================================================

Goal: AI engines can discover and parse all canonical content.

Tasks:
1. Verify all llms.txt links resolve:
   curl -s https://signomy.xyz/llms.txt | grep -oE 'https://signomy.xyz[^ )]+' | while read url; do
     code=$(curl -s --max-time 5 -o /dev/null -w "%{http_code}" "$url")
     [ "$code" != "200" ] && echo "$code $url"
   done
2. Add new pages from Phases 1-2 to llms.txt
3. Create /llms-full.txt with full inlined definitions:
   - Full CIVITAE definition
   - Full Signomy definition
   - Full MO§ES™ governance description
   - Agent trust tier definitions
   - Economy tier definitions
   - Key concept definitions
4. Verify robots.txt allows all AI crawlers (already confirmed: GPTBot,
   ClaudeBot, Google-Extended, PerplexityBot, Applebot-Extended)
5. Add CCBot and anthropic-ai to AI crawler allow list if missing
6. Verify /agent.json and /.well-known/mcp-server-card.json accessible

Acceptance: llms.txt has zero broken links. llms-full.txt exists with
full definitions. robots.txt allows all known AI crawlers.

============================================================
PHASE 4 — Content layer (concept/guide/FAQ pages)
============================================================

Goal: Build definitional content pages that AI engines cite.

Load Search Authority canon context BEFORE writing any definitional
content:
  python3 ~/Developer/_control/search-authority/canon_cli.py context signomy
  python3 ~/Developer/_control/search-authority/canon_cli.py context civitae
  python3 ~/Developer/_control/search-authority/canon_cli.py context moses
  python3 ~/Developer/_control/search-authority/canon_cli.py context ecosystem

Tasks — concept pages (one per key term):
1. /concepts/governed-marketplace — "What is a governed AI agent marketplace?"
2. /concepts/civitae — "What is CIVITAE?"
3. /concepts/signomy — "What is Signomy?"
4. /concepts/agent-trust-tiers — "What are agent trust tiers?"
5. /concepts/constitutional-ai — "What is constitutional AI governance?"
6. /concepts/agent-provisioning — "What is agent provisioning?"
7. /concepts/seed-provenance — "What is seed provenance and DOI tracking?"
8. /concepts/kassa — "What is KA§§A?"
9. /concepts/sig-arena — "What is SigArena?"
10. /concepts/governance-vacuum — "What is a governance vacuum?"

Tasks — guide pages:
11. /guides/how-to-register-an-agent
12. /guides/how-to-post-a-mission
13. /guides/how-to-join-a-mission
14. /guides/how-to-use-the-mcp-bridge

Tasks — comparison pages:
15. /vs/langchain — Signomy/CIVITAE vs LangChain
16. /vs/crew-ai — Signomy/CIVITAE vs CrewAI
17. /vs/auto-gpt — Signomy/CIVITAE vs AutoGPT
18. /vs/agent-arena — Signomy/CIVITAE vs LMSYS Agent Arena

Tasks — FAQ:
19. Expand existing FAQ content (24 pages have FAQPage schema — ensure
    the Q&A content is comprehensive)
20. Create dedicated /faq page with 15-20 Q&A entries

After all pages built:
21. Update sitemap.xml with all new pages
22. Update llms.txt with all new pages
23. Add BreadcrumbList + DefinedTerm/FAQPage JSON-LD to new pages
24. Add OG meta to new pages (Phase 1 patterns)

Content rules (CRITICAL):
- Each page targets exactly ONE search intent
- Opening paragraph uses NATURAL QUERY LANGUAGE
  BAD: "The CIVITAE platform provides..."
  GOOD: "A governed AI agent marketplace is..."
- One canonical definition per concept
- H1 = the question, first sentence = the answer
- Tables and step-by-steps over prose
- Link back to canonical hub with consistent anchor text
- ≤155 char meta description, ≤60 char title

Acceptance: 10 concept + 4 guide + 4 comparison + 1 FAQ page built.
All in sitemap + llms.txt. All have JSON-LD + OG meta.

============================================================
PHASE 5 — Screaming Frog audit + fix campaign
============================================================

Goal: Find and fix all technical SEO issues.

Tasks:
1. Run Screaming Frog crawl on signomy.xyz (~80 pages after Phase 4)
   If SF is not installed, write a Python script using requests +
   BeautifulSoup to check the same issues.
2. Export: All Internal Links, All External Links, Orphan Pages,
   Redirects, Issues
3. Build prioritized fix list:
   broken links > redirects > security headers > meta > titles > H1/H2 > images
4. Fix all issues in priority order
5. Re-crawl to verify (compare crawl 1 vs crawl 2)

What to look for:
- 404s and broken links
- Redirect chains (flatten A→C, not A→B→C)
- Orphan pages (in sitemap but not linked internally)
- Missing/duplicate meta descriptions (≤155 chars)
- Long page titles (≤60 chars)
- Missing H1 (every page needs exactly one)
- Duplicate H2s
- Missing security headers (CSP, X-Frame-Options, X-Content-Type-Options,
  Referrer-Policy)
- Crawl depth (no page >3 clicks from homepage)
- Images missing width/height

Acceptance: 0 broken links, 0 redirect chains, 0 missing security
headers, all meta ≤155 chars, all titles ≤60 chars.

============================================================
PHASE 6 — Indexing push + GSC setup
============================================================

Goal: Get all pages indexed by Google and Bing.

Tasks:
1. Check if GSC is set up for signomy.xyz
2. If not, document setup instructions for owner (requires Google account)
3. Submit sitemap.xml
4. Request indexing on key pages (homepage, concept pages, FAQ)
5. Check if IndexNow key file exists on signomy.xyz
6. If missing, create one:
   openssl rand -hex 16 → save as <key>.txt in frontend/
7. Push all URLs to IndexNow:
   curl -X POST "https://api.indexnow.org/IndexNow" \
     -H "Content-Type: application/json" \
     -d '{"host":"signomy.xyz","key":"<key>","keyLocation":"https://signomy.xyz/<key>.txt","urlList":[...]}'
8. Adapt gsc.mjs toolkit for signomy.xyz (reference: docs/seo-aeo-geo-build-package/gsc-toolkit/)
9. Run check:index to verify all sitemap URLs are indexed

Acceptance: All sitemap URLs indexed by Google. All URLs pushed to IndexNow.

============================================================
PHASE 7 — AEO reconciliation (query association)
============================================================

Goal: Fix the query association gap — ensure pages are selected as
the answer, not just indexed.

Tasks:
1. Build a 46-prompt test panel for signomy.xyz:
   Named/branded (20): "What is Signomy?", "What is CIVITAE?",
   "What is KA§§A?", "What is SigArena?", etc.
   Broad discovery (26): "What is a governed AI agent marketplace?",
   "How to register an AI agent?", "Constitutional AI governance",
   "AI agent marketplace", "multi-agent governance", etc.
   (Adapt from docs/seo-aeo-geo-build-package/aeo-audit/prompt-panel/PERPLEXITY_PROMPTS.md)

2. Run the panel across 7 engines:
   ChatGPT Search, Perplexity, Claude, Gemini, Grok, Google AI Overviews,
   Bing Copilot
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

Acceptance: Broad discovery prompt retrieval rate improves from
baseline. Named prompt retrieval >90%.

============================================================
PHASE 8 — Maintenance cadence setup
============================================================

Goal: Establish the recurring cadence that keeps citation share growing.

Tasks:
1. Create a citation tracking spreadsheet for signomy.xyz:
   - 10-15 target queries
   - Columns: date, engine, query, mentioned, cited, competitor
2. Document the weekly citation query test procedure
3. Document the monthly AEO citation audit procedure
4. Document the quarterly Screaming Frog crawl procedure
5. Set up IndexNow push script for new/changed URLs
6. Document the 70/30 rule (70% refresh, 30% new content)
7. Create a maintenance runbook

Cadence:
  Weekly:    Citation query test (10-15 queries, incognito, 4 engines) — 15 min
  Weekly:    GSC AI Overviews + queries — 5 min
  Bi-weekly: Core page freshness refresh — 30 min
  Monthly:   Full AEO citation audit — 30 min
  Monthly:   IndexNow push for new/changed URLs — 5 min
  Quarterly: Screaming Frog crawl — 30 min
  Quarterly: Content decay review — 1 hour
  Annually:  Full content audit — half day

Acceptance: Maintenance runbook exists. Citation tracking spreadsheet
initialized with baseline queries.

============================================================
RETURN
============================================================

After all phases, return:

1. Phase completion status table (8 phases, done/skipped/blocked)
2. Files created/modified
3. Screaming Frog crawl results (before/after)
4. AEO audit results (baseline + post-fix)
5. GSC + IndexNow status
6. Owner action checklist (items only the owner can execute)
7. Maintenance runbook location
8. Any blockers encountered

Do NOT push to remote without owner authorization.
Commit locally after each phase.
