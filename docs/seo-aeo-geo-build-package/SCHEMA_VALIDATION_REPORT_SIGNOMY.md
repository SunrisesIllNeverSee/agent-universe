---
type: Report
title: Schema Validation Report — signomy.xyz
description: JSON-LD schema validation results for signomy.xyz key page types. All blocks parse as valid JSON with correct schema.org types.
tags: [signomy, seo, schema, json-ld, validation, phase-2]
timestamp: 2026-08-25
---

# Schema Validation Report — signomy.xyz

**Date:** 2026-08-25
**Method:** Python script validating JSON-LD blocks in frontend HTML files
**Scope:** 5 key page types per Phase 2 acceptance criteria

## Summary

| Metric | Value |
|--------|-------|
| Page types validated | 5 |
| Total JSON-LD blocks | 25 |
| Blocks valid JSON | 25/25 |
| Schema type errors | 0 |
| Canon violations | 0 |
| Breadcrumb issues fixed | 12 (2 vs + 7 concepts + 3 guides) |

## Results

### Homepage (index.html) — PASS

| Block | Type | Status |
|-------|------|--------|
| 0 | Organization | Valid — no alternateName CIVITAE |
| 1 | WebSite | Valid |
| 2 | SoftwareApplication | Valid — applicationCategory, offers present |
| 3 | Dataset | Valid |
| 4 | Dataset | Valid |
| 5 | ScholarlyArticle | Valid |
| 6 | FAQPage | Valid — mainEntity with acceptedAnswer |

**7 blocks, 0 errors.**

### Concept page (governed-marketplace.html) — PASS

| Block | Type | Status |
|-------|------|--------|
| 0 | BreadcrumbList | Valid — 2 items, sequential positions, no self-ref non-terminal |
| 1 | DefinedTerm | Valid — name + description present |
| 2 | FAQPage | Valid |
| 3 | Organization | Valid — no alternateName CIVITAE |
| 4 | WebSite | Valid |
| 5 | SoftwareApplication | Valid — added in GAP 3, distinct @id |

**6 blocks, 0 errors.**

### Guide page (how-to-register-an-agent.html) — PASS

| Block | Type | Status |
|-------|------|--------|
| 0 | BreadcrumbList | Valid — 2 items, sequential positions |
| 1 | HowTo | Valid — steps present |
| 2 | Organization | Valid — no alternateName CIVITAE |
| 3 | WebSite | Valid |

**4 blocks, 0 errors.**

### VS page (langchain.html) — PASS

| Block | Type | Status |
|-------|------|--------|
| 0 | BreadcrumbList | Valid — 2 items, fixed in GAP 4 |
| 1 | FAQPage | Valid |
| 2 | Organization | Valid — no alternateName CIVITAE |
| 3 | WebSite | Valid |

**4 blocks, 0 errors.**

### FAQ page (faq.html) — PASS

| Block | Type | Status |
|-------|------|--------|
| 0 | BreadcrumbList | Valid |
| 1 | FAQPage | Valid |
| 2 | Organization | Valid — no alternateName CIVITAE |
| 3 | WebSite | Valid |

**4 blocks, 0 errors.**

## Issues Found and Fixed

### BreadcrumbList self-referencing non-terminal crumbs (fixed)

During validation, discovered that 12 pages had BreadcrumbList with position 2
pointing to the page itself (self-referencing non-terminal crumb). This was
because no hub page exists for /vs/, /concepts/, or /guides/ directories.

**Pages fixed:**
- `vs/langchain.html` — 3 items → 2 items (GAP 4)
- `vs/crew-ai.html` — 3 items → 2 items (GAP 4)
- `concepts/governed-marketplace.html` — 3 items → 2 items
- `concepts/civitae.html` — 3 items → 2 items
- `concepts/signomy.html` — 3 items → 2 items
- `concepts/agent-trust-tiers.html` — 3 items → 2 items
- `concepts/constitutional-ai.html` — 3 items → 2 items
- `concepts/kassa.html` — 3 items → 2 items
- `concepts/governance-vacuum.html` — 3 items → 2 items
- `guides/how-to-register-an-agent.html` — 3 items → 2 items
- `guides/how-to-post-a-mission.html` — 3 items → 2 items
- `guides/how-to-join-a-mission.html` — 3 items → 2 items

**Fix:** Reduced to 2-item breadcrumbs (Home → page name as terminal crumb).
No hub pages created (would require sitemap-v2.xml modification, which is
canonical and immutable).

## Canon Compliance

- Zero Organization blocks have `alternateName: "CIVITAE"` (fixed in GAP 1)
- Signomy and CIVITAE are not collapsed in any schema
- All Organization blocks use `name: "SIGNOMY"` without CIVITAE alternateName

## Conclusion

All 5 key page types pass schema validation with 0 errors. All JSON-LD blocks
parse as valid JSON with correct schema.org types. Phase 2 acceptance criteria
met.
