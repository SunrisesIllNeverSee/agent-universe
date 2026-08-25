---
type: Runbook
title: Maintenance Runbook — mos2es.com
description: Recurring SEO/GEO/AEO maintenance cadence for mos2es.com. Follow this runbook to keep citation share growing.
tags: [moses, mos2es, runbook, maintenance, seo, geo, aeo]
timestamp: 2026-08-25
---

# Maintenance Runbook — mos2es.com

## Site profile

| Field | Value |
|-------|-------|
| URL | https://mos2es.com |
| Host | Netlify |
| Framework | Eleventy (11ty) static site generator |
| Pages | ~49 public pages |
| Sitemap | https://mos2es.com/sitemap.xml |
| llms.txt | https://mos2es.com/llms.txt |
| llms-full.txt | https://mos2es.com/llms-full.txt |
| IndexNow key | 3cb9dad60ebc43248d4ec58b2d9b4aca.txt |
| GA4 | G-SDGZRVRKKS |
| Repo | ~/Developer/built/mos2es-site |

## Citation tracking queries (10-15 target queries)

Run these weekly in incognito mode across 4 engines (ChatGPT, Perplexity, Claude, Google AI Overviews):

1. what is conservation law of commitment
2. what is MO§ES governance
3. AI governance framework
4. multi-agent governance protocol
5. commitment conservation AI
6. semantic meaning preservation AI
7. SHA-256 audit trail AI agents
8. lineage bound artifacts
9. recursive compression AI governance
10. governance vacuum AI
11. sovereign signal governance
12. how to enforce commitment conservation
13. what is lineage claw
14. what is origin binding
15. constitutional AI governance

## Cadence

| Frequency | What | Time | Tool |
|-----------|------|------|------|
| Weekly | Citation query test (15 queries, incognito, 4 engines) | 15 min | Manual |
| Weekly | GSC AI Overviews + queries | 5 min | GSC API |
| Bi-weekly | Core page freshness refresh | 30 min | Manual edit |
| Monthly | Full AEO citation audit | 30 min | Prompt panel |
| Monthly | IndexNow push for new/changed URLs | 5 min | curl script |
| Monthly | AI crawler access check | 5 min | `curl robots.txt` |
| Quarterly | Screaming Frog crawl | 30 min | SF or Python script |
| Quarterly | Content decay review | 1 hour | GSC + manual |
| Quarterly | llms.txt + sitemap audit | 15 min | Manual |
| Annually | Full content audit | Half day | GSC + SF + manual |

## Weekly: Citation Query Test

1. Open incognito browser
2. For each of the 15 target queries:
   - Search in ChatGPT, Perplexity, Claude, Google AI Overviews
   - Record: mentioned? cited? correct? hallucinated? competitor cited?
3. Log in citation tracking spreadsheet
4. Compare to previous week

## Bi-weekly: Core Page Freshness Refresh

1. Review the 10 most important pages:
   - / (homepage)
   - /concepts/conservation-law
   - /concepts/sovereign-signal-governance
   - /concepts/governance-vacuum
   - /papers
   - /architecture
   - /benchmarks
   - /faq
   - /guides/how-to-enforce-commitment-conservation
   - /vs/rlhf
2. Check for:
   - New experimental results to add
   - New citations or DOIs
   - Updated benchmark numbers
   - New FAQ entries from user questions
3. Apply the 70/30 rule: 70% refresh existing content, 30% new content

## Monthly: Full AEO Citation Audit

1. Run the full 46-prompt panel (see MOS2ES_PROMPT_PANEL.md)
2. Score each query: mentioned, cited, correct, hallucinated
3. Apply 5-tier reconciliation if needed:
   - Tier 1: Rewrite opening paragraphs to use natural query language
   - Tier 2: Canonicalize shared facts (one definition per concept)
   - Tier 3: Disambiguate entity collisions (MO§ES vs biblical Moses)
   - Tier 4: Strengthen internal nav with category language
   - Tier 5: Align external descriptions (GitHub, npm, Zenodo)
4. Track citation share trend

## Monthly: IndexNow Push

```bash
# Get all sitemap URLs
URLS=$(curl -s https://mos2es.com/sitemap.xml | grep -oE 'https://mos2es.com[^<]+' | python3 -c "import sys,json; urls=[l.strip() for l in sys.stdin]; print(json.dumps(urls))")

curl -X POST "https://api.indexnow.org/IndexNow" \
  -H "Content-Type: application/json" \
  -d "{\"host\":\"mos2es.com\",\"key\":\"3cb9dad60ebc43248d4ec58b2d9b4aca\",\"keyLocation\":\"https://mos2es.com/3cb9dad60ebc43248d4ec58b2d9b4aca.txt\",\"urlList\":$URLS}"
```

## Quarterly: Screaming Frog Crawl

1. Run the Python crawl audit script:
```bash
cd ~/Developer/built/mos2es-site
npx eleventy --quiet
python3 -c "
# Run the crawl audit script (see Phase 6 implementation)
# Check: titles ≤60, descriptions ≤155, H1 present, OG meta, canonical, JSON-LD
"
```
2. Or use Screaming Frog SEO Spider (free, 500 URL limit)
3. Compare issue count to previous quarter — should never increase
4. Fix any new issues in priority order:
   broken links > redirects > security headers > meta > titles > H1/H2 > images

## Quarterly: Content Decay Review

1. Check GSC for pages with declining impressions
2. Review pages that haven't been updated in 3+ months
3. Refresh stale content with new data, citations, or examples
4. Check for broken external links (DOIs, GitHub links)

## Build and deploy

```bash
cd ~/Developer/built/mos2es-site
npx eleventy --quiet    # build
# Netlify auto-deploys from git push
```
