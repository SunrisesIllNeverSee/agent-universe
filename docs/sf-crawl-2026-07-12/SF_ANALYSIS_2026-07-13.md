---
type: Audit
title: Screaming Frog Crawl Analysis — signomy.xyz (2026-07-13 04:57 UTC)
description: Full labeled analysis of the Screaming Frog SEO Spider crawl of signomy.xyz. 75 URLs encountered, 56 internal, 46 HTML pages. Identifies all issues, opportunities, and warnings with specific URLs and recommended fixes.
tags: [signomy, screaming-frog, seo, audit, crawl, analysis, agent-universe]
timestamp: 2026-07-13T05:10:00Z
---

# Screaming Frog Crawl Analysis — signomy.xyz

> **Crawl date:** 2026-07-13 04:48–04:57 UTC (9 minutes)
> **Site crawled:** `https://signomy.xyz/`
> **Total URLs encountered:** 75 (56 internal + 19 external)
> **Internal HTML pages:** 46
> **Crawl tool:** Screaming Frog SEO Spider
> **Source folder:** `docs/sf-crawl-2026-07-12/2026.07.13.04.57.24/`

---

## Executive Summary

| Metric | Value | Grade |
|--------|-------|-------|
| Total URLs | 75 | — |
| 4xx/5xx errors | 0 | A+ |
| Redirect chains | 0 | A+ |
| HTTPS compliance | 100% | A+ |
| Mixed content | 0 | A+ |
| Pages with H1 | 35/46 (76%) | C |
| Pages with canonical | 40/46 (87%) | B |
| Pages with meta description | 40/46 (87%) | B |
| Structured data (JSON-LD) | 0/46 (0%) | F |
| Exact duplicate pages | 6 (3 clusters) | D |
| Low content pages (<200 words) | 14 (30%) | C |
| robots.txt blocking | 2 (intentional) | A |

**Overall grade: B-** — No broken links or errors, but significant SEO gaps in structured data, H1s, canonicals, and duplicate content.

---

## 1. Issues (High Priority)

### 1.1 Exact Duplicate Content — 6 pages, 3 clusters (HIGH)

Three clusters of pages have identical HTML (same MD5 hash):

**Cluster 1: Vault documents (6 pages, all identical)**
- `/vault/gov-001`, `/vault/gov-002`, `/vault/gov-003`, `/vault/gov-004`, `/vault/gov-005`, `/vault/gov-006`
- All 6 pages serve the same HTML with title "Document — The Vault"
- **Root cause:** The vault page template is rendering the same content for all gov docs instead of loading the specific document content
- **Fix:** Each `/vault/gov-00X` page needs unique content (the actual governance document), unique title, unique H1, and unique meta description

**Cluster 2: KA§§A duplicate (2 pages)**
- `/kassa` and `/kassa?tab=hiring&role=genesis-council`
- Same HTML, same title
- **Status:** The `?tab=` URL is canonicalised to `/kassa` — this is correct behavior
- **Fix:** Already handled via canonical. No action needed.

**Cluster 3: Agent profile duplicate (2 pages)**
- `/agent/me` and `/agent`
- Same HTML, same title
- **Status:** `/agent/me` is canonicalised to `/agent` — this is correct behavior
- **Fix:** Already handled via canonical. No action needed.

### 1.2 Missing H1 — 11 pages (MEDIUM)

| URL | Notes |
|-----|-------|
| `signomy.xyz/` | Homepage — critical page, needs H1 |
| `signomy.xyz/portal` | Portal directory page |
| `signomy.xyz/vault/gov-001` | Vault doc (also duplicate) |
| `signomy.xyz/vault/gov-002` | Vault doc (also duplicate) |
| `signomy.xyz/vault/gov-003` | Vault doc (also duplicate) |
| `signomy.xyz/vault/gov-004` | Vault doc (also duplicate) |
| `signomy.xyz/vault/gov-005` | Vault doc (also duplicate) |
| `signomy.xyz/vault/gov-006` | Vault doc (also duplicate) |
| `signomy.xyz/world` | World/isometric hub page |
| `signomy.xyz/switchboard` | Signal switchboard page |
| `signomy.xyz/refinery` | SigRank refinery page |

**Fix:** Add a descriptive `<h1>` to each of these pages. The 6 vault pages are the biggest issue (they also have duplicate content + missing canonicals + missing meta descriptions).

### 1.3 robots.txt Blocking — 2 pages (INTENTIONAL)

| URL | Status | Notes |
|-----|--------|-------|
| `signomy.xyz/console` | Blocked by robots.txt | Intentional — private operator console |
| `signomy.xyz/admin` | Blocked by robots.txt | Intentional — admin panel |

**Status:** Correct. These should remain blocked.

---

## 2. Warnings (Medium Priority)

### 2.1 Missing Canonicals — 6 pages

All 6 vault pages (`/vault/gov-001` through `/vault/gov-006`) are missing canonical link elements.

**Fix:** Add `<link rel="canonical" href="https://signomy.xyz/vault/gov-00X" />` to each vault page. This is critical because the pages are currently exact duplicates — without canonicals, Google may index the wrong version.

### 2.2 Missing Meta Descriptions — 6 pages

Same 6 vault pages are missing meta descriptions.

**Fix:** Add unique meta descriptions to each vault page describing the specific governance document.

### 2.3 Duplicate Page Titles — 3 clusters

| Title | Pages | Fix |
|-------|-------|-----|
| "Document — The Vault" | 6 vault pages | Give each a unique title (e.g., "GOV-001: Genesis Charter — The Vault") |
| "AI Agent Marketplace — Bounties, Services & Hiring \| KA§§A" | `/kassa` + `/kassa?tab=...` | Already canonicalised — OK |
| "AI Agent Profile — Trust Tier, Reputation & Missions \| CIVITAE" | `/agent/me` + `/agent` | Already canonicalised — OK |

### 2.4 Missing H2 — 23 pages (50%)

Half the pages have no H2 heading. H2s help search engines understand page structure.

**Fix:** Add descriptive H2s to important pages, especially the ones that also have H1s.

### 2.5 Missing Content-Security-Policy Header — 53 URLs (95%)

Almost no pages have a CSP header. This is a security recommendation, not an SEO issue.

**Fix:** Add a CSP header at the Vercel/Railway proxy level. Low priority for SEO.

### 2.6 Canonicalised Pages — 2 (CORRECT)

| URL | Canonical target | Status |
|-----|-----------------|--------|
| `/kassa?tab=hiring&role=genesis-council` | `/kassa` | Correct |
| `/agent/me` | `/agent` | Correct |

These are working as intended.

---

## 3. Opportunities (Low Priority)

### 3.1 Low Content Pages — 14 pages (30%)

| URL | Word count | Notes |
|-----|-----------|-------|
| `/vault/gov-001` | 7 | Stub page (also duplicate) |
| `/vault/gov-002` | 7 | Stub page (also duplicate) |
| `/vault/gov-003` | 7 | Stub page (also duplicate) |
| `/vault/gov-004` | 7 | Stub page (also duplicate) |
| `/vault/gov-005` | 7 | Stub page (also duplicate) |
| `/vault/gov-006` | 7 | Stub page (also duplicate) |
| `/agent` | 5 | Profile redirect/stub |
| `/agent/me` | 5 | Profile redirect/stub |
| `/portal` | 10 | Directory page (JS-rendered) |
| `/deploy` | 40 | Tactical grid (visual page) |
| `/campaign` | 85 | Strategy matrix (visual page) |
| `/world` | 100 | Isometric hub (visual page) |
| `/refinery` | 112 | SigRank refinery (stub) |
| `/dashboard` | 175 | Agent dashboard (JS-rendered) |

**Note:** Many of these are visual/interactive pages where low word count is expected (deploy grid, isometric world, dashboard). The vault pages are the real problem — they should have substantial content.

### 3.2 Page Titles Too Short — 10 pages (22%)

10 pages have titles under 30 characters. These are likely short brand titles that could be expanded with keywords.

### 3.3 Page Titles Too Long — 4 pages (9%)

4 pages have titles over 60 characters. These may be truncated in search results.

### 3.4 Meta Descriptions Too Long — 6 pages (13%)

6 pages have meta descriptions over 155 characters. These may be truncated.

### 3.5 H2 Duplicates — 10 pages (22%)

10 pages have duplicate H2s. Likely the same section header across multiple pages.

---

## 4. What's Good

| Check | Result |
|-------|--------|
| 4xx errors | 0 |
| 5xx errors | 0 |
| Redirect chains | 0 |
| Redirect loops | 0 |
| HTTPS compliance | 100% |
| Mixed content | 0 |
| HTTP URLs | 0 |
| Broken bookmarks | 0 |
| Non-ASCII URLs | 0 |
| Underscore URLs | 0 |
| Uppercase URLs | 0 |
| JavaScript errors | 0 |
| Pages with blocked resources | 0 |
| Uncrawlable outlinks | 0 |
| Pages without internal outlinks | 0 |
| robots.txt intentional blocks | 2 (console, admin) |
| Canonicalised pages | 2 (correct) |
| llms.txt | Live (200 OK) |
| sitemap | Referenced |

---

## 5. Structured Data — CRITICAL GAP

**Zero structured data on any page.** No JSON-LD, no microdata, no RDFa.

This is the single biggest SEO gap. For a site with 46 HTML pages, having no structured data means:
- No rich results in Google
- No entity recognition
- No AI engine citation signals
- No Organization, WebSite, or Product schema

**Recommended schema types to add:**
- `Organization` (site-wide) — MO§ES™ / Ello Cello LLC
- `WebSite` (site-wide) — signomy.xyz
- `Product` or `Service` — for KA§§A marketplace, missions, governance
- `BreadcrumbList` — on all interior pages
- `Article` — on vault/governance docs (once they have unique content)
- `FAQPage` — on governance/about pages
- `Dataset` — on seeds/provenance page

---

## 6. External Links (19 total)

| Destination | Inlinks | Notes |
|-------------|---------|-------|
| `fonts.googleapis.com` (12 URLs) | 0 | Google Fonts CSS — expected |
| `orcid.org/0009-0002-9904-5390` | 24 | Your ORCID — good entity signal |
| `zenodo.org/records/18792459` | 3 | Zenodo deposit — good entity signal |
| `zenodo.org/records/19105225` | 2 | Zenodo deposit — good entity signal |
| `github.com/SunrisesIllNeverSee` | 1 | GitHub org |
| `github.com/SunrisesIllNeverSee/command-engine` | 1 | Public repo |
| `github.com/SunrisesIllNeverSee/moses-governance` | 2 | Public repo |
| `x.com/burnmydays` | 1 | X/Twitter profile |

**Assessment:** Good external link profile. ORCID + Zenodo + GitHub are strong entity signals for AI engines. No spammy or broken external links.

---

## 7. Comparison to Previous Crawl (2026-07-12 23:17)

| Metric | Previous (Jul 12) | Current (Jul 13) | Change |
|--------|-------------------|------------------|--------|
| Total URLs | 73 | 75 | +2 |
| Internal URLs | 56 | 56 | 0 |
| 4xx/5xx errors | 0 | 0 | 0 |
| Missing H1 | 11 | 11 | 0 |
| Missing canonical | 6 | 6 | 0 |
| Exact duplicates | 6 | 6 | 0 |
| Structured data | 0 | 0 | 0 |
| Low content | 14 | 14 | 0 |

**No change between crawls.** The two crawls are 6 hours apart — no content changes were made in between.

---

## 8. Priority Fix List

### Tier 1 — Fix Now (biggest SEO impact)

1. **Fix the 6 vault pages** — they're the single biggest issue:
   - Each `/vault/gov-00X` needs unique content (the actual governance document text)
   - Each needs a unique title (e.g., "GOV-001: Genesis Charter — The Vault")
   - Each needs a unique H1
   - Each needs a unique meta description
   - Each needs a self-referencing canonical
   - This fixes 4 issues at once: exact duplicates, missing H1, missing canonical, missing meta description, duplicate titles, low content

2. **Add H1 to homepage** (`/`) — the most important page on the site

3. **Add structured data** (JSON-LD) — at minimum Organization + WebSite in the layout

### Tier 2 — Fix Soon

4. Add H1 to `/portal`, `/world`, `/switchboard`, `/refinery`
5. Add H2s to pages missing them (23 pages)
6. Expand low-content pages where appropriate (refinery, switchboard)

### Tier 3 — Nice to Have

7. Add CSP headers (security, not SEO)
8. Fix page titles that are too short/long
9. Fix meta descriptions that are too long
10. Add hreflang (only if targeting multiple languages)

---

## 9. File Inventory

All 43 CSV exports from the crawl, labeled by category:

| File | What it contains |
|------|-----------------|
| `crawl_overview.csv` | Summary stats (URLs, response codes, content types) |
| `issues_overview_report.csv` | All issues with severity + recommendations |
| `url_all.csv` | Every URL with status, indexability, canonical |
| `response_codes_all.csv` | HTTP status for every URL |
| `redirects.csv` | Redirect chains (empty — no redirects) |
| `redirect_chains.csv` | Redirect chain details (empty) |
| `redirect_and_canonical_chains.csv` | Combined redirect/canonical chains |
| `redirects_to_error.csv` | Redirects ending in error (empty) |
| `page_titles_all.csv` | Every page title |
| `meta_description_all.csv` | Every meta description |
| `meta_keywords_all.csv` | Meta keywords (95% missing — expected, deprecated) |
| `h1_all.csv` | Every H1 |
| `h2_all.csv` | Every H2 |
| `canonicals_all.csv` | Canonical link elements |
| `canonical_chains.csv` | Canonical chain details |
| `canonicals_nonindexable_canonicals.csv` | Canonicals pointing to non-indexable URLs |
| `content_all.csv` | Content analysis (word count, duplicates, readability) |
| `internal_all.csv` | All internal links |
| `external_all.csv` | All external links |
| `links_all.csv` | Link summary per page |
| `link_metrics_all.csv` | Inlink/outlink counts per page |
| `directives_all.csv` | Robots meta directives (index/noindex/follow/nofollow) |
| `hreflang_all.csv` | Hreflang tags (100% missing) |
| `sitemaps_all.csv` | Sitemap URL presence per page |
| `structured_data_all.csv` | JSON-LD/microdata/RDFa (100% missing) |
| `validation_all.csv` | HTML validation issues |
| `accessibility_all.csv` | Accessibility checks |
| `mobile_all.csv` | Mobile-friendliness |
| `pagespeed_all.csv` | Page speed metrics |
| `pagination_all.csv` | Pagination detection (empty) |
| `pagination_non200_pagination_urls.csv` | Broken pagination (empty) |
| `pagination_unlinked_pagination_urls.csv` | Unlinked pagination (empty) |
| `javascript_all.csv` | JavaScript rendering analysis |
| `analytics_all.csv` | Analytics tags (GA, GTM, etc.) |
| `ai_all.csv` | AI crawler access (GPTBot, ClaudeBot, etc.) |
| `search_console_all.csv` | GSC data (if connected) |
| `security_all.csv` | Security headers (CSP, HSTS, etc.) |
| `security_http_urls.csv` | HTTP (non-HTTPS) URLs (empty — all HTTPS) |
| `security_https_urls.csv` | HTTPS URLs (all 56) |
| `amp_all.csv` | AMP detection (empty) |
| `segments_overview_report_issues.csv` | Segment-level issue summary (empty) |

---

_Analysis by Drep1. Source: Screaming Frog SEO Spider crawl 2026-07-13 04:57 UTC._
