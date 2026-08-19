---
type: Reference
title: Screaming Frog Crawl Analysis — signomy.xyz
description: Screaming Frog Crawl Analysis — signomy.xyz — documentation in docs/.
tags: [documentation, docs]
timestamp: 2026-08-19
---

# Screaming Frog Crawl Analysis — signomy.xyz

> Crawl date: 2026-07-12 23:07 UTC · 77 URLs encountered · 58 internal · 6 second crawl time
> Raw exports: `docs/sf-crawl-2026-07-12/2026.07.12.23.17.54/`

## Executive Summary

| Metric | Value | Grade |
|--------|-------|-------|
| Total URLs crawled | 77 (58 internal, 19 external) | — |
| Broken links (4xx/5xx) | **0** | A |
| Redirect chains/loops | **0** (all single-hop) | A |
| Canonical chains | **0** | A |
| HTTPS adoption | 100% | A |
| Mixed content | 0 | A |
| Redirects to fix (internal links to redirect sources) | **18 links across 11 pages** | D |
| Missing canonicals | **6** (all vault/gov-* pages) | C |
| Missing H1 | **19 pages** | D |
| Missing H2 | **23 pages** | C |
| Missing meta descriptions | **11 pages** | C |
| Duplicate titles | **6** (all vault/gov-* pages) | D |
| Exact duplicate content | **6** (all vault/gov-* pages) | F |
| Low content pages (<200 words) | **14** | C |
| Security headers missing | **53/58 URLs** (4 headers) | F |
| Structured data detected by SF | 0 (false negative — JSON-LD IS present) | N/A |

**Overall: the site is structurally healthy (no broken links, no redirect chains, no canonical chaos) but has two systemic clusters of issues: (1) the 6 vault document pages are all serving identical stub HTML, and (2) 18 internal links still point at redirect-source URLs instead of their canonical destinations.**

---

## Issue 1 — Internal links to redirect sources (HIGH priority, easy fix)

**18 internal links across 11 pages point to `/openroles` or `/join` — both 301 redirect.** Every one adds a needless hop for crawlers and users.

### `/openroles` → `/helpwanted` (15 inlinks across 9 pages)

| Page | Link location | Anchor text |
|------|--------------|-------------|
| `/` | `section#onboard` — bi-paths link 2 | "Open Roles 31 positions across 12 domains..." |
| `/` | `section#collaborate` — alt-links link 2 | "Browse open roles" |
| `/missions` | nav link 2 | "Open Roles" |
| `/missions` | eco-grid link 1 | "ACTIVE 6 POSITIONS Open Roles..." |
| `/civitas` | nav link 2 | "Open Roles" |
| `/civitas` | helpwanted-strip link | "View All Positions" |
| `/civitas` | footer link | "Open Roles" |
| `/helpwanted` | civitae-nav active link | "Open Roles" |
| `/agent/me` | nav link 2 | "Open Roles" |
| `/slots` | nav link 2 | "Open Roles" |
| `/dashboard` | quick-links link 2 | "📋 Open Roles 31 open positions" |
| `/leaderboard` | civitae-nav link 2 | "Open Roles" |
| `/world` | faction-panel qs-link 4 | "§ Open Roles" |
| `/mission` | nav link 2 | "Open Roles" |
| `/agent` | nav link 2 | "Open Roles" |

**Fix:** Find/replace `href="/openroles"` → `href="/helpwanted"` across all frontend HTML. The nav links are likely in `_nav.js` or a shared template — fixing one file may fix many pages at once.

### `/join` → `/` (3 inlinks across 2 pages)

| Page | Link location | Anchor text |
|------|--------------|-------------|
| `/kingdoms` | entry-modal em-btn-primary 2 | "Lets Collaborate" |
| `/lobby` | sp-not-approved link | "Apply to Join" |
| `/lobby` | sp-anonymous link | "Join the Waitlist" |

**Fix:** Update `href="/join"` → `href="/#collaborate"` (the redirect target) in `kingdoms.html` and `lobby.html`.

---

## Issue 2 — Vault document pages are broken (HIGH priority)

All 6 `/vault/gov-001` through `/vault/gov-006` pages are serving **identical stub HTML** — same hash (`b7b30b5fb9ce4657e8926cfb554d013d`), 7 words each, no canonical, no H1, no meta description, duplicate title "Document — The Vault".

| URL | Title | H1 | Meta desc | Canonical | Words | Hash |
|-----|-------|-----|-----------|-----------|-------|------|
| `/vault/gov-001` | Document — The Vault | missing | missing | missing | 7 | b7b30b5f... |
| `/vault/gov-002` | Document — The Vault | missing | missing | missing | 7 | b7b30b5f... |
| `/vault/gov-003` | Document — The Vault | missing | missing | missing | 7 | b7b30b5f... |
| `/vault/gov-004` | Document — The Vault | missing | missing | missing | 7 | b7b30b5f... |
| `/vault/gov-005` | Document — The Vault | missing | missing | missing | 7 | b7b30b5f... |
| `/vault/gov-006` | Document — The Vault | missing | missing | missing | 7 | b7b30b5f... |

**Root cause:** The `vault-doc.html` template is serving a shell with no document content loaded. This is 6 issues in one:
1. **6 exact duplicate content pages** (Google sees 6 identical pages)
2. **6 missing canonicals** (no canonical to consolidate)
3. **6 duplicate titles** (all "Document — The Vault")
4. **6 missing H1s**
5. **6 missing meta descriptions**
6. **6 low-content pages** (7 words each)

**Fix:** The vault doc page needs to load the actual GOV-001 through GOV-006 content. Each page needs:
- Unique `<title>` (e.g. "GOV-001: Constitutional Framework — The Vault | SIGNOMY")
- Unique `<meta description>` summarizing that document
- `<link rel="canonical" href="https://signomy.xyz/vault/gov-001" />` (self-referencing)
- `<h1>` with the document name
- The actual document content (from `docs/governance/`)

This single fix resolves 6 of the issue categories at once.

---

## Issue 3 — Missing canonicals (MEDIUM priority)

6 pages missing canonical — all are the vault/gov-* pages (covered in Issue 2).

No other canonical issues. The 2 canonicalised pages are correct:
- `/kassa?tab=hiring&role=genesis-council` → canonical to `/kassa` ✓
- `/agent/me` → canonical to `/agent` ✓

38 pages have self-referencing canonicals ✓

---

## Issue 4 — Missing H1 (MEDIUM priority)

19 pages have no H1. Breakdown:

**Vault pages (6) — covered by Issue 2 fix:**
`/vault/gov-001` through `/vault/gov-006`

**App/UI pages (8) — H1 may be intentionally absent (UI is the content):**
`/`, `/missions`, `/helpwanted`, `/dashboard`, `/leaderboard`, `/world`, `/deploy`, `/campaign`

**Content pages that should have H1 (5):**
`/entry`, `/portal`, `/refinery`, `/switchboard`, `/agent`

**Fix priority:** The 5 content pages + 6 vault pages. The 8 app/UI pages are lower priority — they have visual headers that aren't `<h1>` tags. Consider adding hidden `<h1>` tags for SEO without changing the visual design.

---

## Issue 5 — Missing meta descriptions (MEDIUM priority)

11 pages missing meta descriptions:

**Vault pages (6)** — covered by Issue 2 fix.

**Other pages (5):**
- `/entry` — CIVITAE entry/splash page
- `/campaign` — CIVITAE Campaign
- `/command` — COMMAND Overview
- `/deploy` — CIVITAE Deploy
- `/agent` — CIVITAE Agent Profile

**Fix:** Write unique meta descriptions for these 5 pages. The vault pages get descriptions as part of Issue 2.

---

## Issue 6 — Missing H2 (LOW priority)

23 pages have no H2. Many of these are the same pages missing H1 (vault pages, app pages). The GEO-optimized pages (helpwanted, seeds, vault, leaderboard, mission, slots, sig-arena) already have H2s in FAQ format — good.

**Pages with H2s that are working well:** `/civitas` (6 H2s), `/helpwanted` (5), `/vault` (5), `/leaderboard` (5), `/seeds` (5), `/grand-opening` (3), `/command` (3), `/forums` (6).

**Note:** 10 pages have "duplicate" H2s — this is because the FAQ section uses "Frequently Asked Questions" as an H2 on multiple pages. This is fine (it's a section label, not a content heading) but could be made unique per page if desired.

---

## Issue 7 — Low content pages (LOW priority)

14 pages under 200 words:

| Page | Words | Type | Action |
|------|-------|------|--------|
| `/vault/gov-001` through `gov-006` | 7 each | Broken stubs | Fix in Issue 2 |
| `/portal` | 10 | JS-rendered directory | Content loads via JS — SF can't see it. Consider SSR or noscript fallback. |
| `/deploy` | 33 | Interactive 8×8 grid UI | UI is the content. Add descriptive text for SEO. |
| `/campaign` | 77 | Interactive matrix UI | Same — add descriptive text. |
| `/world` | 100 | Isometric 3D hub | Same — add descriptive text. |
| `/refinery` | 112 | Placeholder page | Add content when feature is built. |
| `/dashboard` | 167 | Agent control panel | UI is the content. Add intro text. |
| `/switchboard` | 184 | Placeholder page | Add content when feature is built. |

**Fix:** Priority pages are `/deploy`, `/campaign`, `/world`, `/refinery`, `/switchboard` — add 100-200 words of descriptive content explaining what the page is/does. The vault pages are covered by Issue 2.

---

## Issue 8 — Pages with no internal outlinks (MEDIUM priority)

4 HTML pages have 0 internal outlinks (SF couldn't find any `<a>` tags to other internal pages):

| Page | Inlinks | Likely cause |
|------|---------|-------------|
| `/portal` | 1 | Links built by JavaScript from `pages.json` — SF didn't render them |
| `/refinery` | 1 | Likely JS-rendered content or genuinely no links |
| `/agentdash` | 2 | Likely JS-rendered content |
| `/switchboard` | 1 | Likely JS-rendered content |

**Fix:** Add at least 2-3 server-side `<a>` links in the raw HTML of each page (e.g. "Back to Portal", "View Missions", etc.) so crawlers can discover related pages without JS.

---

## Issue 9 — Security headers missing (LOW priority for SEO, MEDIUM for security)

53 of 58 internal URLs are missing 4 security headers:
- Content-Security-Policy
- X-Content-Type-Options
- X-Frame-Options
- Referrer-Policy

**Fix:** Add a `headers` block in `vercel.json` for all HTML routes:
```json
{
  "source": "/(.*)",
  "headers": [
    { "key": "X-Content-Type-Options", "value": "nosniff" },
    { "key": "X-Frame-Options", "value": "SAMEORIGIN" },
    { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
    { "key": "Content-Security-Policy", "value": "default-src 'self'; ..." }
  ]
}
```

The 5 URLs that DO have these headers are likely the `.well-known/*` and asset routes that already have custom header blocks in `vercel.json`.

Also: 1 unsafe cross-origin link (external `target="_blank"` without `rel="noopener"`) — find and add `rel="noopener noreferrer"`.

---

## Issue 10 — Structured data false negative

SF reports 0 pages with structured data. **This is wrong** — verified via curl that the homepage has 6 JSON-LD blocks (Organization, WebSite, SoftwareApplication, Dataset, ScholarlyArticle, FAQPage) and `/kassa` has BreadcrumbList. The JSON-LD is in the raw HTML, not JS-injected.

**Likely cause:** SF version or configuration issue. The JSON-LD is valid and present. No action needed on the site — possibly update SF or check its structured data parsing settings for the next crawl.

---

## Issue 11 — Short page titles (LOW priority)

19 pages have titles under 30 characters. Most are app-style pages where brevity is intentional:

| Page | Title | Pixels |
|------|-------|--------|
| `/entry` | CIVITAE — Entry | 143 |
| `/lobby` | Lobby — SIGNOMY | 167 |
| `/portal` | SIGNOMY — Portal | 168 |
| `/vault/gov-*` (6) | Document — The Vault | 204 each |
| `/world` | CIVITAE — World | 150 |
| `/deploy` | CIVITAE — Deploy | 158 |
| `/refinery` | CIVITAE — Refinery | 171 |
| `/campaign` | CIVITAE — Campaign | 189 |
| `/switchboard` | CIVITAE — Switchboard | 209 |
| `/agentdash` | AgentDash — SIGNOMY | 212 |
| `/agent` | CIVITAE — Agent Profile | 215 |
| `/dashboard` | Agent Dashboard — Civitas | 241 |

**Fix:** Expand titles to include keyword targets. E.g. "CIVITAE — Deploy" → "Deploy AI Agent Formations — 8×8 Tactical Grid | CIVITAE". The vault pages are covered by Issue 2.

---

## Issue 12 — Meta descriptions over 155 chars (LOW priority)

9 pages have meta descriptions over 155 characters. The longest:

| Page | Length | Pixels |
|------|--------|--------|
| `/moses` | 159 | 1033 |
| `/kassa` | 159 | 993 |
| `/contact` | 157 | 999 |
| `/slots` | 157 | 970 |
| `/seeds` | 156 | 979 |
| `/services` | 156 | 967 |
| `/forums` | 156 | 988 |
| `/mission` | 161 | 985 |
| `/about` | 154 | 939 (borderline) |

**Fix:** Trim each to ≤155 chars. These are all well-written descriptions that just need tightening by 2-6 words.

---

## What's working well

- **0 broken links** — no 404s anywhere
- **0 redirect chains** — all 9 redirects are single-hop, no loops
- **0 canonical chains** — canonical structure is clean
- **100% HTTPS** — no mixed content, no HTTP URLs
- **All external links alive** — 19 external URLs all return 200 (Google Fonts, ORCID, Zenodo, GitHub, X/Twitter)
- **robots.txt working** — `/admin` and `/console` correctly blocked
- **2 canonicalised URLs correct** — parameter URL and `/agent/me` properly canonicalised away
- **JSON-LD present** — 6 schema types on homepage, BreadcrumbList on subpages (SF false negative)
- **Sitemap clean** — 20 URLs, all canonical, no redirect sources
- **GEO-optimized pages** — helpwanted, seeds, vault, leaderboard, mission, slots, sig-arena all have FAQ-format H2s and rich content

---

## Prioritized Fix List

| # | Issue | Pages | Effort | Impact |
|---|-------|-------|--------|--------|
| 1 | Fix vault/gov-* stub pages (content + title + H1 + meta + canonical) | 6 | Med | High — fixes 6 issue categories at once |
| 2 | Update internal links from `/openroles` → `/helpwanted` | 11 pages | Low | High — removes 15 needless redirect hops |
| 3 | Update internal links from `/join` → `/#collaborate` | 2 pages | Low | Med — removes 3 redirect hops |
| 4 | Add meta descriptions to 5 non-vault pages | 5 | Low | Med |
| 5 | Add H1 to 5 non-vault content pages | 5 | Low | Med |
| 6 | Add security headers to vercel.json | 1 config | Low | Med |
| 7 | Add server-side outlinks to 4 JS-rendered pages | 4 | Low | Med |
| 8 | Expand short page titles | 13 | Low | Low |
| 9 | Trim long meta descriptions | 9 | Low | Low |
| 10 | Add descriptive content to low-word pages | 5 | Med | Low |
| 11 | Add `rel="noopener"` to unsafe cross-origin link | 1 | Trivial | Low |

---

*Analysis by Devin, 2026-07-12. Raw crawl data in `docs/sf-crawl-2026-07-12/2026.07.12.23.17.54/`.*
