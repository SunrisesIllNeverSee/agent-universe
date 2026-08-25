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
