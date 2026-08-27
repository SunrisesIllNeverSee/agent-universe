---
type: Runbook
title: Maintenance Runbook — signomy.xyz
description: Recurring SEO/GEO/AEO maintenance cadence for signomy.xyz. Follow this runbook to keep citation share growing.
tags: [signomy, civitae, runbook, maintenance, seo, geo, aeo]
timestamp: 2026-08-25
---

# Maintenance Runbook — signomy.xyz

## Site profile

| Field | Value |
|-------|-------|
| URL | https://signomy.xyz |
| Host | Vercel (frontend) + Railway (backend) |
| Framework | Static HTML + FastAPI |
| Pages | 76 public pages (10 concepts + 4 guides + 5 vs + content + app) |
| Sitemap | https://signomy.xyz/sitemap-v2.xml (75 URLs, clean) |
| llms.txt | https://signomy.xyz/llms.txt |
| llms-full.txt | https://signomy.xyz/llms-full.txt |
| IndexNow key | f3c2396010c02b3e0f6256b017c5df67.txt |
| GA4 | G-FD4VLSCHY8 |
| Repo | ~/Developer/_5_Signomy/1_agent-universe |

## Citation tracking queries (10-15 target queries)

Run these weekly in incognito mode across 4 engines:

1. what is signomy
2. what is civitae
3. governed AI agent marketplace
4. how to register an AI agent
5. constitutional AI governance
6. what is KASSA
7. what is SigArena
8. AI agent city-state
9. how to post a mission for AI agents
10. agent trust tiers
11. what is a governance vacuum in AI
12. MO§ES governance framework
13. sovereign signal governance
14. how do AI agents earn revenue
15. what is the difference between Signomy and CIVITAE

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
   - /kassa
   - /missions
   - /governance
   - /moses
   - /concepts/governed-marketplace
   - /concepts/civitae
   - /concepts/signomy
   - /faq
   - /about
2. Check for:
   - New missions or agents to reference
   - Updated governance rules
   - New FAQ entries from user questions
   - Updated economic model details
3. Apply the 70/30 rule: 70% refresh existing content, 30% new content

## Monthly: Full AEO Citation Audit

1. Run the full 46-prompt panel (see SIGNOMY_PROMPT_PANEL.md)
2. Score each query: mentioned, cited, correct, hallucinated
3. Apply 5-tier reconciliation if needed:
   - Tier 1: Rewrite opening paragraphs to use natural query language
   - Tier 2: Canonicalize shared facts (one definition per concept)
   - Tier 3: Disambiguate entity collisions:
     - Signomy vs Signal Messenger
     - CIVITAE vs civitas (generic Latin)
     - MO§ES vs biblical Moses
   - Tier 4: Strengthen internal nav with category language
   - Tier 5: Align external descriptions (GitHub, npm, PyPI)
4. Track citation share trend

## Monthly: IndexNow Push

The sitemap-v2.xml now contains all 75 public URLs with clean paths (no .html).
Push the full sitemap to IndexNow monthly or after significant content changes.

```bash
# Get all URLs from sitemap
URLS=$(curl -s https://signomy.xyz/sitemap-v2.xml | grep -oE 'https://signomy.xyz[^<]+' | python3 -c "import sys,json; urls=[l.strip() for l in sys.stdin]; print(json.dumps(urls))")

# Primary endpoint
curl -X POST "https://api.indexnow.org/IndexNow" \
  -H "Content-Type: application/json" \
  -d "{\"host\":\"signomy.xyz\",\"key\":\"f3c2396010c02b3e0f6256b017c5df67\",\"keyLocation\":\"https://signomy.xyz/f3c2396010c02b3e0f6256b017c5df67.txt\",\"urlList\":$URLS}"

# Fallback: Yandex endpoint (shares IndexNow protocol with Bing/others)
curl -X POST "https://yandex.com/indexnow" \
  -H "Content-Type: application/json" \
  -d "{\"host\":\"signomy.xyz\",\"key\":\"f3c2396010c02b3e0f6256b017c5df67\",\"keyLocation\":\"https://signomy.xyz/f3c2396010c02b3e0f6256b017c5df67.txt\",\"urlList\":$URLS}"
```

> **Note:** All sitemap URLs now use clean paths (no `.html`). Vercel's
> `cleanUrls: true` config handles this. Do not push `.html` URLs.

## Quarterly: Screaming Frog Crawl

1. Run the Python crawl audit script:
```bash
cd ~/Developer/_5_Signomy/1_agent-universe/frontend
python3 -c "
import os, re, glob
from html.parser import HTMLParser
# Check all HTML files for: titles ≤60, descriptions ≤155, H1, OG meta, canonical, JSON-LD
"
```
2. Or use Screaming Frog SEO Spider (free, 500 URL limit)
3. Compare issue count to previous quarter
4. Fix any new issues in priority order

## Entity disambiguation monitoring

Special attention to:
- **Signomy vs Signal Messenger** — ensure "governed agent marketplace" and "city-state" language is prominent
- **CIVITAE vs civitas** — ensure "constitutional AI ecosystem" is always paired with CIVITAE
- **MO§ES vs biblical Moses** — ensure "signal governance" and "commitment conservation" are always paired with MO§ES

## Build and deploy

```bash
cd ~/Developer/_5_Signomy/1_agent-universe
# Vercel auto-deploys from git push (main branch only)
```
