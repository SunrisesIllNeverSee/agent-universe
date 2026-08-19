---
type: Reference
title: SigRank GEO/SEO/AEO Playbook — Complete Build Record
description: SigRank GEO/SEO/AEO Playbook — Complete Build Record — archived documentation in docs/.
tags: [documentation, archive, docs]
timestamp: 2026-08-19
---

# SigRank GEO/SEO/AEO Playbook — Complete Build Record

> **What this is:** The full record of every GEO (Generative Engine Optimization),
> SEO (Search Engine Optimization), and AEO (Answer Engine Optimization) action
> taken on signalaf.com — what was built, why, how to verify it, and what's left.
> Portable: the patterns apply to any project that needs to be cited by AI engines.
>
> **Last updated:** 2026-07-15
> **Site:** signalaf.com
> **Repo:** github.com/SunrisesIllNeverSee/sigrank-app

---

## Table of Contents

1. [The Strategy](#1-the-strategy)
2. [Structured Data (JSON-LD)](#2-structured-data-json-ld)
3. [llms.txt + llms-full.txt](#3-llmstxt--llms-fulltxt)
4. [OG Images + Social Cards](#4-og-images--social-cards)
5. [Sitemap + Robots](#5-sitemap--robots)
6. [Google Search Console (GSC)](#6-google-search-console-gsc)
7. [Bing / IndexNow](#7-bing--indexnow)
8. [Internal Linking](#8-internal-linking)
9. [PostHog Analytics](#9-posthog-analytics)
10. [npm + GitHub Discoverability](#10-npm--github-discoverability)
11. [Verification Commands](#11-verification-commands)
12. [What's Left (Owner Actions)](#12-whats-left-owner-actions)
13. [The Patterns (Portable)](#13-the-patterns-portable)

---

## 1. The Strategy

The goal: **get AI engines (ChatGPT, Perplexity, Claude, Google AI Overviews) to
cite SigRank as the canonical source for AI operator token-efficiency data.**

Three layers, in priority order:

| Layer | What | Why |
|---|---|---|
| **Indexing** | Get pages into Google + Bing's index | If the page isn't indexed, the structured data is invisible. This is the #1 blocker. |
| **Structured data** | JSON-LD (Dataset, FAQ, HowTo, SoftwareApplication, etc.) | Tells engines "this is a dataset, this is a tool, this is a FAQ" — machine-readable citation hooks |
| **Content** | llms.txt, llms-full.txt, quotable stats, Q1 report | Gives engines something to cite inline — definitions, formulas, headline numbers |

**The citation flywheel:** structured data → engines recognize you as a source →
third-party sites cite your numbers → those citations get scraped into training
data → AI engines cite you from training data → more third-party citations.

---

## 2. Structured Data (JSON-LD)

### What's live

All JSON-LD is built in `lib/jsonld.ts` and rendered via `<JsonLd>` component.

| Schema type | Where | Purpose |
|---|---|---|
| `Organization` | Every page (layout.tsx) | Entity identity — `sameAs` links to ORCID, GitHub, npm, 4 Zenodo DOIs, signomy.xyz, mos2es.com (11 entries) |
| `WebSite` | Every page (layout.tsx) | Site-level identity |
| `Dataset` | /methodology, /board/all, /research/q1-2026 | The citation play — marks the leaderboard as a formal citable dataset (CC-BY-4.0, 4 Zenodo DOI citations, distribution APIs) |
| `FAQPage` | /methodology | Quotable Q/A pairs AI engines lift verbatim |
| `HowTo` | /score | 3-step flow (paste → yield → class) — Google rich results |
| `WebApplication` | /score | The calculator is machine-readable as a tool |
| `SoftwareApplication` | /score, / | The `sigrank` CLI (npm) — machine-readable as a software product |
| `ItemList` | /board/[window] | Leaderboard rows as structured list items |
| `ProfilePage` | /user/[codename] | Operator profiles |
| `BreadcrumbList` | /methodology, /science, /research, /wiki/* | Navigation context |
| `DefinedTerm` + `DefinedTermSet` | /wiki/* | Definitional content AI engines lift verbatim |
| `ScholarlyArticle` | /science, /research/q1-2026 | Academic content |
| `Person` | /science | Author identity |
| `PublicationEvent` | /science, /research | Publication context |
| `CreativeWork` | /science | MO§ES enforcement architecture |

### Key design decisions

- **Dataset `citation` is an array of 4 Zenodo DOIs** — the full academic foundation, not just the Conservation Law paper
- **Dataset `sameAs` points to npm + GitHub** — connects the dataset to the tool that produces it
- **Organization `sameAs` has 11 entries** — ORCID, 2 GitHub repos, npm, 4 Zenodo DOIs, signomy.xyz, mos2es.com. This is the entity recognition layer.
- **All URLs are absolute** (SITE_ORIGIN) — relative URLs don't work in structured data per Schema.org spec
- **RS.xx weights are never exposed** — the Dataset describes the SHAPE of the scoring only

### How to verify

```bash
# Check what JSON-LD types are live on a page
curl -s https://signalaf.com/methodology | python3 -c "
import sys, re, json
html = sys.stdin.read()
blocks = re.findall(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL)
for b in blocks:
    d = json.loads(b)
    if isinstance(d, list):
        for item in d: print(item.get('@type'), '✓')
    else: print(d.get('@type'), '✓')
"

# Check the Dataset citation field
curl -s https://signalaf.com/methodology | python3 -c "
import sys, re, json
html = sys.stdin.read()
blocks = re.findall(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL)
for b in blocks:
    d = json.loads(b)
    items = d if isinstance(d, list) else [d]
    for item in items:
        if item.get('@type') == 'Dataset':
            print('citation:', json.dumps(item.get('citation'), indent=2))
            print('sameAs:', json.dumps(item.get('sameAs'), indent=2))
"
```

### Files

- `lib/jsonld.ts` — all builders (organization, website, sigrankDataset, faqPage, breadcrumb, leaderboardItemList, operatorProfile, definedTerm, researchArticle, conservationLawArticle, mosesPatent, experimentalRecordDataset, transformationHarnessDataset, propositionsDataset, scoreCalculator, cliTool, scoreHowTo)
- `components/seo/JsonLd.tsx` — serializer component

---

## 3. llms.txt + llms-full.txt

### llms.txt (`/llms.txt`)

The lightweight map for AI crawlers. Tells ChatGPT, Perplexity, Claude, Google
AI Overviews what SigRank is and where the canonical content lives.

- Site description (one paragraph AI engines can lift verbatim)
- Core pages (leaderboard, board windows, score, hall, compare)
- Data section (methodology, leaderboard API, metric leaders API, CC-BY-4.0 license)
- Research section (Q1 2026 report)
- Concepts (wiki definitions)
- Tooling (npm, GitHub)
- Academic foundation (4 Zenodo DOIs)
- Governance (MO§ES, SIGNOMY, GitHub org, ORCID)
- All AI-surfaced URLs carry `?utm_source=ai&utm_medium=answer_engine` for PostHog attribution

### llms-full.txt (`/llms-full.txt`)

The expanded version — inlines everything an AI engine needs to cite SigRank
in a single fetch, without crawling individual pages:

- The four token pillars (input, output, cache write, cache read)
- The yield formula: `Υ = (cache_read × output) / input²`
- All secondary metrics (Leverage, Velocity, SNR, 10xDEV, Compression Ratio, SIGNA RATE)
- The telescoping identity (anti-gaming proof)
- The 9-class ladder (IGNITER → TRANSMITTER)
- Headline stats (owner-verified): average ratio 3.5:1:0.5, power-user median 22:1:0.08, top operator 439:1:1.7
- The power-user paradox (median yield 1.57, power-user median 1.51)
- Privacy model (token counts only, ed25519-signed, dry-run mode)
- Anti-gaming defense stack
- Top-10 operators table (live from leaderboard API)
- All page links with UTM params
- Citation block (how to cite SigRank)
- All Zenodo DOIs

### How to verify

```bash
curl -s https://signalaf.com/llms.txt | head -20
curl -s https://signalaf.com/llms-full.txt | head -40
```

### Files

- `app/llms.txt/route.ts`
- `app/llms-full.txt/route.ts`

---

## 4. OG Images + Social Cards

### What's live

- `/og-v2.png` — 1200×630 PNG, served with `content-type: image/png`, `cache-control: public, immutable, max-age=31536000`
- Per-operator dynamic OG: `/user/[codename]/opengraph-image` → `image/png` (generated via `next/og`)
- Per-board dynamic OG: `/board/[window]/opengraph-image` → `image/png`
- Twitter card: `summary_large_image` with correct title/description/image
- All pages have `og:title`, `og:description`, `og:url`, `og:site_name`, `og:image`, `og:image:width`, `og:image:height`, `og:image:alt`, `og:type`

### How to verify

```bash
curl -s https://signalaf.com | grep -o '<meta property="og:[^"]*" content="[^"]*"'
curl -s https://signalaf.com | grep -o '<meta name="twitter:[^"]*" content="[^"]*"'
curl -s -o /dev/null -w "%{content_type} %{http_code}" https://signalaf.com/og-v2.png
```

### Files

- `lib/seo.ts` — `withOG()` helper (sets OG + Twitter meta on every page)
- `app/opengraph-image.tsx` (if exists) or `app/[route]/opengraph-image.tsx` — dynamic OG generators

---

## 5. Sitemap + Robots

### Sitemap (`/sitemap.xml`)

Dynamic, generated by `app/sitemap.ts`:
- Static routes (homepage, leaderboard, score, hall, methodology, science, research, compare, wiki pages, about, llms.txt, llms-full.txt, upgrade, login, submit)
- Board windows (7d, 30d, 90d, all, off)
- **Operator profiles** — fetched from `/api/v1/leaderboard?limit=100`, each gets a sitemap entry with `priority: 0.8, changeFrequency: 'daily'`

**Bug fixed 2026-07-15:** sitemap was reading `e.operator?.codename` but the API returns `codename` at the top level. Fixed to `e.codename ?? e.operator?.codename`. Operator profiles now appear in sitemap.

### Robots (`/robots.txt`)

```
User-Agent: *
Allow: /
Disallow: /api/
Disallow: /auth/

Sitemap: https://signalaf.com/sitemap.xml
```

All AI crawlers allowed (no GPTBot/ClaudeBot/PerplexityBot blocks).

### How to verify

```bash
curl -s https://signalaf.com/sitemap.xml | grep -c "<url>"  # URL count
curl -s https://signalaf.com/sitemap.xml | grep -o '<loc>[^<]*</loc>' | sed 's/<[^>]*>//g'  # list URLs
curl -s https://signalaf.com/robots.txt
```

### Files

- `app/sitemap.ts`
- `app/robots.ts`

---

## 6. Google Search Console (GSC)

### State (as of 2026-07-04)

| Status | Count | Pages |
|---|---|---|
| Indexed | 8 | homepage, /board/30d, /upgrade, /login, 4 wiki pages |
| Discovered, not indexed | 17 | /leaderboard, /score, /hall, /methodology, /compare, /submit, most board windows, /wiki, /about, /research, /science |
| Unknown | 1 | /llms.txt |

### Actions taken

- **Sitemap submitted** (2026-06-27, 0 errors)
- **18 URLs pushed** to Google Indexing API (2026-07-04, all 18 ok, 0 skipped)
- **Internal links added** (2026-07-15): homepage → /methodology, /research/q1-2026, /science. /methodology → /score, /research/q1-2026. Googlebot can now discover interior pages from the indexed homepage.
- **Re-inspect due:** ~2026-07-07 to 07-09 (check if the 18 pushed URLs flipped to indexed)

### GSC toolkit

The project has a GSC CLI tool at `scripts/gsc/gsc.mjs` (in the RNS repo):

```bash
export GSC_SA_KEY=~/.config/sigrank/gsc-sa.json  # service account key

node scripts/gsc/gsc.mjs sitemaps:list
node scripts/gsc/gsc.mjs sitemaps:submit [url]
node scripts/gsc/gsc.mjs index <url> [<url> ...]        # Indexing API URL_UPDATED
node scripts/gsc/gsc.mjs index:status <url>
node scripts/gsc/gsc.mjs analytics [days]               # top pages + totals
node scripts/gsc/gsc.mjs inspect <url>                  # URL inspection
```

Setup: see `scripts/gsc/README.md`. Requires a Google Cloud service account JSON key, added as Owner of the signalaf.com property in Search Console.

### What's left

- **Re-inspect** the 17 discovered-not-indexed pages (~07-07 to 07-09)
- If they don't flip, the internal links should help on the next crawl
- If still stuck after 2 weeks, consider submitting individual URLs via `gsc.mjs index <url>` again

---

## 7. Bing / IndexNow

### The problem

**Bing had ZERO signalaf.com pages indexed.** DuckDuckGo uses Bing's index, so
DDG only had the homepage. The GSC index push only helps Google — Bing has its
own protocol.

### The fix

Built an IndexNow endpoint (the open protocol Bing, Yandex, Seznam, Naver use
for instant URL submission):

- `POST /api/indexnow` — accepts `{ urls: [...] }`, forwards to `api.indexnow.org/IndexNow`
- `/indexnow-key.txt` — verification file (IndexNow engines fetch this to confirm ownership)
- The key is a static 32-char hex string, served as `text/plain`

### IndexNow push fired (2026-07-15)

19 URLs submitted, all accepted (HTTP 202). Bing should crawl within 24-48h.

```bash
# Fire the push (already done, but here's the command for re-use):
curl -X POST https://signalaf.com/api/indexnow \
  -H 'Content-Type: application/json' \
  -d '{"urls":["https://signalaf.com/","https://signalaf.com/methodology","https://signalaf.com/score","https://signalaf.com/research/q1-2026","https://signalaf.com/science","https://signalaf.com/board/all","https://signalaf.com/board/7d","https://signalaf.com/board/30d","https://signalaf.com/board/90d","https://signalaf.com/wiki/verification","https://signalaf.com/wiki/three-degrees","https://signalaf.com/wiki/signal-drift","https://signalaf.com/wiki/local-agent","https://signalaf.com/compare","https://signalaf.com/hall","https://signalaf.com/submit","https://signalaf.com/about","https://signalaf.com/llms.txt","https://signalaf.com/llms-full.txt"]}'
```

### How to verify

```bash
# Check the key file is live
curl -s https://signalaf.com/indexnow-key.txt
# Should return: a3f7b2c9e1d4f6a8b0c2e4d6f8a0b2c4e6d8f0a2b4c6d8e0f2a4b6c8d0e2f4a6

# Fire a test push
curl -s -X POST https://signalaf.com/api/indexnow \
  -H 'Content-Type: application/json' \
  -d '{"urls":["https://signalaf.com/"]}'
# Should return: {"status":202,"ok":true,"submitted":1,"key":"a3f7b2c9…"}
```

### Files

- `app/api/indexnow/route.ts` — POST endpoint
- `app/indexnow-key.txt/route.ts` — key verification file

---

## 8. Internal Linking

### Why

Google discovers pages via links + sitemap. If an interior page isn't linked
from an already-indexed page, Google may not crawl it even if it's in the
sitemap. The homepage is indexed — links from it are discovery signals.

### What was added (2026-07-15)

- **Homepage** → /methodology, /research/q1-2026, /science (3 new links at the bottom, before the MotionPause component)
- **/methodology** → /score (in the FAQ "How do I get listed?" answer) + /research/q1-2026 (new section at the bottom: "Looking for the quarterly findings?")
- Homepage already linked to /score via hero tiles + CTA band (3 existing links)

### The discovery path

```
/ (indexed) → /methodology (not indexed) → /research/q1-2026 (not indexed)
/ (indexed) → /score (not indexed)
/ (indexed) → /science (not indexed)
/methodology (not indexed) → /score (not indexed)
```

Once Google crawls the homepage (already indexed), it follows the new links
to the interior pages. This is the standard fix for "discovered but not indexed."

---

## 9. PostHog Analytics

### What's instrumented

**Client-side** (`lib/posthog/client.ts` + `lib/posthog/events.ts`):
- `$pageview` — automatic
- `board_viewed` — fires on LeaderboardTable mount (window, platform, view, total)
- `profile_viewed` — fires on operator profile view (is_own)
- `profile_shared` — fires on profile share (channel: copy/download)
- `compare_shared` — fires on compare share (channel: copy/download)
- `wrapped_viewed` — fires on /wrapped view
- `upgrade_viewed` — fires on /upgrade view
- `checkout_clicked` — fires on checkout click (kind, amount, price)

**Server-side** (`lib/posthog/server.ts` — `captureServer()`):
- `operator_enrolled` — fires on /api/v1/devices/enroll success
- `snapshot_submitted` — fires on /api/v1/snapshots + /api/v1/ingest-paste success
- `checkout_started` — fires on /api/v1/billing/create-checkout-session
- `device_rotated` — fires on /api/v1/devices/rotate

### The gap (owner action needed)

**Server-side events have ZERO events in PostHog.** `operator_enrolled`,
`snapshot_submitted`, `checkout_started`, `device_rotated` — none have ever fired.

**Root cause:** `POSTHOG_KEY` (the server-side key, no `NEXT_PUBLIC_` prefix)
appears to not be set in Vercel's environment variables. The `captureServer()`
function silently no-ops when the key is missing:

```ts
function ph(): PostHog | null {
  const key = process.env.POSTHOG_KEY
  if (!key) return null  // ← silently does nothing
  ...
}
```

**Fix:** Vercel → sigrank-app project → Settings → Environment Variables →
add `POSTHOG_KEY` (the value is in local `.env` line 38, starts with `phc_`).
This should be a **server** key (PostHog project settings → Project API key),
not the public key.

### UTM attribution

All AI-surfaced URLs in llms.txt + llms-full.txt carry
`?utm_source=ai&utm_medium=answer_engine`. When an AI engine surfaces a link
and a user clicks through, PostHog attributes the session to the AI channel.
This lets you measure whether AI engines are driving enrollments.

### Traffic data (2026-07-05)

```
Jun 5-29:  0 pageviews (PostHog not yet instrumented)
Jun 30:   14
Jul 1:     3
Jul 2:     9
Jul 3:    21
Jul 4:   618  ← launch spike (Show HN + GitHub)
Jul 5:   194  (partial day)
Total:  ~859 unique sessions in 6 days
```

Top pages: / (247), /board/all (217), /score (205), /methodology (198)
Top referrers: $direct (907), google.com (8), Android Google app (10), bing.com (2), github.com (2)

---

## 10. npm + GitHub Discoverability

### npm

- Package: `sigrank` (npmjs.com/package/sigrank)
- Keywords: `mcp`, `model-context-protocol`, `ai-agents`, `claude`, `token-telemetry`, `leaderboard`, `cli`, `yield-cascade`
- Version: 0.14.3

### GitHub

- `github.com/SunrisesIllNeverSee/sigrank-app` — the web app (public)
- `github.com/SunrisesIllNeverSee/sigrank-mcp` — the CLI + MCP server (public)
- Topics on both repos
- README with badges, install instructions, links to signalaf.com

### JSON-LD cross-links

The `SoftwareApplication` JSON-LD on the homepage + /score links to:
- `downloadUrl: https://www.npmjs.com/package/sigrank`
- `codeRepository: https://github.com/SunrisesIllNeverSee/sigrank-mcp`

The `Organization` JSON-LD `sameAs` links to both GitHub repos + npm.

---

## 11. Verification Commands

```bash
# === Build gates (run before every commit) ===
cd ~/Desktop/SigRank-repos/sigrank-app
npx tsc --noEmit                                          # 0 errors
node --test __tests__/ingest/canonical.test.mjs           # 11/11 pass
npm run build                                             # green, 49 routes

# === Live site checks ===
curl -s https://signalaf.com/llms.txt | head -10          # llms.txt live
curl -s https://signalaf.com/llms-full.txt | head -20     # llms-full.txt live
curl -s https://signalaf.com/robots.txt                   # robots live
curl -s https://signalaf.com/sitemap.xml | grep -c "<url>" # sitemap URL count

# === JSON-LD checks ===
curl -s https://signalaf.com/methodology | python3 -c "
import sys, re, json
html = sys.stdin.read()
blocks = re.findall(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL)
for b in blocks:
    d = json.loads(b)
    items = d if isinstance(d, list) else [d]
    for item in items: print(item.get('@type'), '✓')
"

# === OG checks ===
curl -s https://signalaf.com | grep -o '<meta property="og:[^"]*" content="[^"]*"'

# === IndexNow ===
curl -s https://signalaf.com/indexnow-key.txt              # key file
curl -s -X POST https://signalaf.com/api/indexnow -H 'Content-Type: application/json' -d '{"urls":["https://signalaf.com/"]}'

# === GSC (requires service account key) ===
cd ~/Desktop/SigRank
export GSC_SA_KEY=~/.config/sigrank/gsc-sa.json
node scripts/gsc/gsc.mjs sitemaps:list
node scripts/gsc/gsc.mjs inspect https://signalaf.com/methodology
node scripts/gsc/gsc.mjs analytics 28
```

---

## 12. What's Left (Owner Actions)

| # | Action | When | How |
|---|---|---|---|
| 1 | **Set `POSTHOG_KEY` in Vercel** | Now | Vercel → Settings → Environment Variables → add `POSTHOG_KEY` (server-side key from PostHog project settings) |
| 2 | **GSC re-inspect** | ~07-07 to 07-09 | `node scripts/gsc/gsc.mjs inspect https://signalaf.com/methodology` — check if the 18 pushed URLs flipped to indexed |
| 3 | **Profound AEO re-run** | When ready | 30-prompt set in `Devins_Plans/growth/profound-rerun-prompts.md`. Run with competitor overrides (ccusage/tokscale). Compare against baseline (7.2% visibility / 0% citation / #33). |
| 4 | **Distribute Q1 report** | When ready | Show HN → r/LocalLLaMA → r/ClaudeAI → newsletter emails → Medium/Dev.to → X thread. See Q1 distribution plan in SCRATCHPAD. |
| 5 | **Re-push IndexNow** | After major content changes | `curl -X POST https://signalaf.com/api/indexnow -H 'Content-Type: application/json' -d '{"urls":[...]}'` |

---

## 13. The Patterns (Portable)

These patterns apply to any project that needs to be cited by AI engines:

### Pattern 1: Dataset JSON-LD is the citation hook
If you have data, mark it up as `Dataset` with:
- `@id` (stable URI)
- `creator` + `publisher` (linked to Organization)
- `license` (CC-BY-4.0 for maximum citability)
- `citation` (array of DOI links to your academic foundation)
- `distribution` (API endpoints as `DataDownload`)
- `variableMeasured` (each metric as a `PropertyValue`)
- `measurementTechnique` (how the data is collected)

### Pattern 2: llms.txt + llms-full.txt
- `llms.txt` = the map (what + where)
- `llms-full.txt` = the content (inline definitions, formulas, stats, top entries)
- Both carry UTM params on AI-surfaced URLs for channel attribution

### Pattern 3: Organization sameAs is entity recognition
Link to every surface: ORCID, GitHub, npm, DOIs, related sites. When an AI
engine encounters your name anywhere, it can trace it to all surfaces.

### Pattern 4: IndexNow for Bing, Indexing API for Google
- Google: Indexing API (needs service account, `gsc.mjs index <url>`)
- Bing/Yandex/Seznam: IndexNow (needs key file + POST endpoint, `/api/indexnow`)
- Both are instant submission — don't wait for organic discovery

### Pattern 5: Internal links from indexed pages
If a page is "discovered but not indexed," add a link to it from an
already-indexed page. Google follows internal links as a discovery signal.

### Pattern 6: FAQPage + DefinedTerm for verbatim lifting
AI engines lift FAQ answers and term definitions verbatim. Put your most
quotable content in `FAQPage` and `DefinedTerm` JSON-LD.

### Pattern 7: HowTo + WebApplication for tool discovery
If you have a calculator or tool, mark it up as `WebApplication` + `HowTo`.
AI engines answering "X calculator" or "how to X" queries will surface it.

### Pattern 8: UTM params on AI-surfaced URLs
Add `?utm_source=ai&utm_medium=answer_engine` to URLs in llms.txt and
any surface AI engines might cite. This lets you measure AI-driven
conversions in PostHog.

### Pattern 9: Canonical URLs on every page
Every page must have `<link rel="canonical" href="https://yoursite.com/path">`.
Without it, Google may index duplicate URLs (with/without trailing slash,
http/https) and split authority.

### Pattern 10: Third-party citations move the needle
Structured data tells engines "this is a dataset." Third-party citations
(newsletters, blogs, Reddit) tell engines "this dataset is trustworthy."
You earn third-party citations by distributing quotable original findings
(quarterly reports, headline stats) to surfaces that will quote them.
