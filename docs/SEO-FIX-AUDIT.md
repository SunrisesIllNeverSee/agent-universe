# SEO Audit and Fix Documentation

## Date: 2026-04-22 00:11:47 UTC

### Introduction
This document outlines the SEO audit conducted on the project and provides a comprehensive thought process, root cause analysis, architectural decisions, and implementation strategies to address issues identified in Google Search Console, particularly focusing on redirect chains, duplicate content, and missing canonical tags.

### Comprehensive Thought Process
1. **Identify Issues**: We began by analyzing the errors reported in Google Search Console. The focus was specifically on redirect chains, duplicate content, and missing canonical tags.
2. **Prioritize Problems**: Issues were prioritized based on their impact on SEO performance and user experience.
3. **Research Solutions**: Solutions were researched for each identified issue, considering best practices and latest SEO guidelines.

### Root Cause Analysis
1. **Redirect Chains**:
   - **Root Cause**: Several URLs were redirecting through multiple intermediary URLs before reaching the final destination. This often occurs due to outdated links or improper server configurations.
   - **Impact**: This negatively affects page loading times and search engine crawlers’ ability to index pages efficiently.

2. **Duplicate Content**:
   - **Root Cause**: Similar or identical content was being served at multiple URLs due to lack of proper content management and URL structure.
   - **Impact**: This dilutes page authority and confuses search engines regarding which version to prioritize.

3. **Missing Canonical Tags**:
   - **Root Cause**: Many pages did not have canonical tags, which are critical in guiding search engines to the preferred version of a page.
   - **Impact**: The absence of canonical tags contributes to issues with duplicate content and indexing errors.

### Architecture Decisions
- **URL Structure Revision**: A comprehensive review of the URL structure was necessary to eliminate redirect chains and establish clean, user-friendly URLs.
- **Content Audit**: A content audit was conducted to identify pages with duplicate content and determine which version of the content should be kept.
- **Implementation of Canonical Tags**: Proper canonical tags were to be added to pages that had multiple versions to ensure that search engines correctly understand the preferred version.

### Implementation Strategy
1. **Fix Redirect Chains**:
   - Identify and remove unnecessary redirects.
   - Establish direct routing for URLs whenever possible.

2. **Resolve Duplicate Content**:
   - Consolidate duplicated content into a single authoritative page.
   - Implement 301 redirects from duplicate pages to the preferred page.

3. **Add Canonical Tags**:
   - Review all pages, especially those identified in Search Console, and include canonical tags where necessary.
   - Validate the implementation using SEO tools and Google Search Console.

### Conclusion
Following this documentation, the necessary changes will be made to alleviate indexing issues reported in Google Search Console. Monitoring will continue post-implementation to ensure all fixes are addressing the identified concerns effectively.

---

## Implementation Log — 2026-04-30

Branch: `claude/fix-seo-audit-5f33q`

### 1. Redirect Chains
- **vercel.json**: All permanent redirects normalized to status code `301` (was `308`). Added 3 new redirects (`/agent-earnings-matrix`, `/agent-earnings-journey`, `/fee-credit-packs`) so the file-named URLs consolidate onto the short canonical aliases (`/earnings-matrix`, `/earnings-journey`, `/fee-credits`).
- **app/routes/pages.py**: Resolved direction conflicts where Railway and Vercel disagreed.
  - `/3d` no longer serves `world.html` directly — now `301 → /world` (matches Vercel).
  - `/openroles` and `/helpwanted` were inverted between layers. Now both layers agree: `/helpwanted` is canonical, `/openroles` redirects 301 to it.
  - Added 301 redirects on Railway for `/agent-earnings-matrix`, `/agent-earnings-journey`, `/fee-credit-packs` to mirror Vercel.

### 2. Duplicate Content
- **frontend/kingdoms.html**: `og:url` was set to `https://signomy.xyz/` (same as the homepage). Updated to `https://signomy.xyz/kingdoms`.
- **frontend/sitemap.xml**: Restored from the placeholder content that was committed in `614ba04`. Pruned all redirect-source URLs (`/openroles`, `/join`) so Google never crawls a URL that 301s. Lists only canonical URLs.
- **frontend/robots.txt**: Replaced `Allow: /openroles` with `Allow: /helpwanted`. Removed `Allow: /join` (it is a redirect).

### 3. Canonical Tags
- Added `<link rel="canonical" href="https://signomy.xyz/{path}" />` to **56 of 57** frontend HTML pages, immediately after the viewport meta tag.
- The 57th page, `frontend/join.html`, has no reachable URL (the `/join` route 301s to `/#collaborate`); it received `<meta name="robots" content="noindex,follow" />` instead so Google does not index orphan content.
- File-name URLs that share content with a short-form alias (`agent-earnings-matrix.html`, `agent-earnings-journey.html`, `fee-credit-packs.html`) declare canonical pointing to the short alias (`/earnings-matrix`, etc.) — combined with the new 301s, this consolidates duplicate content under one URL.

### Files Touched
- `vercel.json`
- `app/routes/pages.py`
- `frontend/sitemap.xml`
- `frontend/robots.txt`
- `frontend/kingdoms.html`
- `frontend/*.html` (56 pages with new canonical tag, 1 with noindex)

### Post-Deploy Validation
1. Submit updated sitemap at Search Console → Sitemaps.
2. Use URL Inspection on a redirect source (e.g. `signomy.xyz/openroles`) — should report 301 with target `/helpwanted` and "Indexed (canonical)" on the destination.
3. Inspect any canonical-protected page and verify "User-declared canonical" matches the canonical tag we set.
4. Watch Coverage report for "Duplicate without user-selected canonical" to drop to 0 over the next crawl cycle.