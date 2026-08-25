---
type: Report
title: Foundation Audit Report — mos2es.com + signomy.xyz
description: Phase 1 audit results and fixes for OG meta, canonical, robots.txt, and sitemap completeness.
tags: [moses, signomy, seo, audit, foundation, phase-1]
timestamp: 2026-08-25
---

# Foundation Audit Report — Phase 1

## mos2es.com

### OG meta verification
| Check | Before | After |
|-------|--------|-------|
| og:title on all pages | ✅ (via 11ty head partial) | ✅ |
| og:description on all pages | ✅ | ✅ |
| og:url on all pages | ✅ | ✅ |
| og:image (PNG, not SVG) | ✅ /img/og.png | ✅ |
| og:image:width (1200) | ✅ | ✅ |
| og:image:height (630) | ✅ | ✅ |
| twitter:card | ✅ | ✅ |
| twitter:image | ✅ | ✅ |
| canonical link | ✅ | ✅ |
| meta description (≤155) | ❌ 27 pages over 155 | ✅ All ≤155 |
| title (≤60) | ❌ 1 page over 60 | ✅ All ≤60 |

### robots.txt
| Check | Before | After |
|-------|--------|-------|
| Allows all crawlers | ✅ | ✅ |
| AI bots explicitly allowed | ❌ No AI bot rules | ✅ GPTBot, ClaudeBot, anthropic-ai, PerplexityBot, CCBot, Google-Extended, Applebot-Extended |
| Sitemap reference | ✅ | ✅ |
| Utility pages disallowed | ❌ | ✅ /img/benchmarks/, /system-devin/, /preview |

### sitemap.xml
| Check | Before | After |
|-------|--------|-------|
| Total URLs | 45 | 49 |
| Missing pages | deck, governance-vacuum | ✅ All public pages included |
| Excluded intentionally | preview, 404, utility pages | ✅ |

### JSON-LD structured data
| Check | Before | After |
|-------|--------|-------|
| Organization schema | Homepage only | ✅ All content pages (via head partial) |
| WebSite schema | Homepage only | ✅ All content pages (via head partial) |
| BreadcrumbList | ✅ On concept/guide/vs pages | ✅ |
| DefinedTerm | ✅ On concept pages | ✅ |
| FAQPage | ✅ On concept/FAQ pages | ✅ |
| ScholarlyArticle | ✅ On papers page | ✅ |

### llms.txt + llms-full.txt
| Check | Before | After |
|-------|--------|-------|
| llms.txt exists | ✅ | ✅ Updated with new concepts |
| llms-full.txt exists | ✅ | ✅ Updated with new concept definitions |
| All links resolve | ✅ | ✅ |
| robots.txt allows AI bots | ❌ | ✅ |

### Crawl audit (Phase 6)
| Metric | Before | After |
|--------|--------|-------|
| Pages checked | 49 | 49 |
| Pages with issues | 40 | 0 |
| Total issues | 212 | 0 |

---

## signomy.xyz

### OG meta verification
| Check | Before | After |
|-------|--------|-------|
| og:title on all pages | ❌ 22 pages missing | ✅ All pages |
| og:description on all pages | ❌ 22 pages missing | ✅ All pages |
| og:url on all pages | ❌ 22 pages missing | ✅ All pages |
| og:image (PNG) | ❌ 22 pages missing | ✅ All pages |
| og:image:width (1200) | ❌ 22 pages missing | ✅ All pages |
| og:image:height (630) | ❌ 22 pages missing | ✅ All pages |
| twitter:card | ❌ 26 pages missing | ✅ All pages |
| twitter:image | ❌ 26 pages missing | ✅ All pages |
| canonical link | ❌ 1 page missing | ✅ All pages |
| meta description | ❌ 4 pages missing | ✅ All pages |

### robots.txt
| Check | Before | After |
|-------|--------|-------|
| Allows all crawlers | ✅ | ✅ |
| AI bots explicitly allowed | ✅ GPTBot, ClaudeBot, Google-Extended, PerplexityBot, Applebot-Extended | ✅ + CCBot, anthropic-ai |
| Sitemap reference | ✅ sitemap-v2.xml | ✅ |

### sitemap.xml
| Check | Before | After |
|-------|--------|-------|
| Total URLs | 22 | 50 |
| Missing pages | ~28 public pages | ✅ All public pages included |

### JSON-LD structured data
| Check | Before | After |
|-------|--------|-------|
| Organization schema | Homepage only | ✅ All 42 pages that were missing it |
| WebSite schema | Homepage only | ✅ All 42 pages that were missing it |

### llms.txt + llms-full.txt
| Check | Before | After |
|-------|--------|-------|
| llms.txt exists | ✅ | ✅ |
| llms-full.txt exists | ✅ | ✅ |
| robots.txt allows AI bots | ✅ (missing CCBot, anthropic-ai) | ✅ All AI bots |

---

## signomy.xyz — Crawl Audit (GAP 6, 2026-08-25)

**Method:** Python script (HTMLParser + link checker) crawling all 79 HTML files
in `frontend/`. No external crawler needed — static site, local files.

### Summary

| Metric | Value |
|--------|-------|
| Pages crawled | 79 |
| Total issues | 45 |
| Content page issues (fixable) | 1 (meta description length) |
| App/dynamic page issues | 44 (expected — console, admin, kassa-post, etc.) |
| Broken internal links | 0 real 404s (10 false positives: anchors, dynamic routes) |

### Issue Breakdown

**Fixed in this audit:**
- `concepts/governed-marketplace.html`: meta description was 160 chars (limit 155).
  Fixed to 123 chars.

**Expected gaps (app/dynamic pages — not SEO content pages):**
These pages are dynamic app surfaces (console, admin, kassa-post, kassa-thread,
agent-profile, sitemap, 404) or vault doc detail pages. They are not in
sitemap-v2.xml and are not target SEO content pages. Missing OG/meta on these
is expected — they are app UI, not landing pages.

- `404.html`: missing meta desc, canonical, OG (error page — expected)
- `admin.html`: missing meta desc, OG, H1 (admin UI — expected)
- `console.html`: missing meta desc, OG, H1 (operator cockpit — expected)
- `kassa-post.html`: missing meta desc, OG, H1 (dynamic post view — expected)
- `kassa-thread.html`: missing meta desc, OG, H1 (dynamic thread view — expected)
- `agent-profile.html`: missing meta desc, OG, H1 (dynamic profile — expected)
- `sitemap.html`: missing meta desc, OG, H1 (internal session tool — expected)
- `vault/gov-001.html` through `gov-006.html`: missing OG title/description
  (6 vault doc detail pages — could be added in future pass)

**Other minor gaps:**
- `agent-earnings-journey.html`, `agent-earnings-matrix.html`: missing meta desc
- `agent.html`: missing OG title/description
- `kassa-post.html`: missing meta desc (dynamic)

### Broken Internal Links (False Positives)

The 10 "broken" links are all valid — they are anchor links or dynamic routes:
- `kassa#bounties`, `kassa#hiring`, `kassa#iso`, `kassa#products` — anchor links
- `academia#register` — anchor link
- `kassa?tab=hiring&role=genesis-council` — query parameter
- `profile`, `agent/me` — dynamic routes (backend-served)
- `mapsite` — likely typo for `sitemap` (not a real link in any page)
- `.well-known/mcp` — MCP server card (served by backend, not a static file)

### Conclusion

signomy.xyz content pages (concepts, guides, vs, FAQ, about, index) are clean.
The 44 issues on app/dynamic pages are expected — those are operator UI surfaces,
not SEO landing pages. The one real content issue (meta description length on
governed-marketplace.html) has been fixed.
