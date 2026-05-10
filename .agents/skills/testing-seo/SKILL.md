---
name: testing-seo
description: Test SEO changes (meta tags, canonicals, sitemaps, redirects) on signomy.xyz. Use when verifying frontend HTML head changes or Vercel config updates.
---

# Testing SEO Changes — signomy.xyz

## Architecture
- **Frontend:** Vercel (`signomy.xyz` DNS) — serves static HTML from `frontend/` with `cleanUrls: true`
- **Backend:** Railway — only handles `/api/*`, `/mcp`, `/health`, `/ws/*`, `/docs/*` via Vercel rewrites
- **Velvet Rope middleware** runs on Railway only — does NOT affect Googlebot crawling pages on Vercel

## Vercel Preview Limitation
Vercel preview deployments may have deployment protection (SSO) enabled, returning 401. If this happens:
- Test source files directly via grep/inspection
- Curl production to establish a baseline (confirm the problem exists today)
- After merge, spot-check production via `curl -s https://signomy.xyz/<page> | grep 'name="description"'`

## Key Test Commands

### Check meta descriptions exist
```bash
for f in frontend/*.html; do
  name=$(basename "$f" .html)
  desc=$(grep -oP 'name="description" content="\K[^"]+' "$f" | head -1)
  echo "$name: ${desc:-MISSING}"
done
```

### Check canonicals
```bash
for f in frontend/*.html; do
  name=$(basename "$f" .html)
  canonical=$(grep -oP 'rel="canonical" href="\K[^"]+' "$f" | head -1)
  echo "$name: ${canonical:-NO CANONICAL}"
done
```

### Verify redirects on production
```bash
curl -sI -o /dev/null -w "%{http_code} %{redirect_url}" "https://signomy.xyz/<path>"
```

### Check robots.txt
```bash
curl -s https://signomy.xyz/robots.txt | grep -i sitemap
```

## Common Issues
- `sitemap.html` canonical was broken (pointed to `/mapsite` which 404'd on Vercel). The canonical should match the actual serving URL.
- `sitemap.xml` and `sitemap-v2.xml` were identical duplicates. Keep only one in `robots.txt`.
- Pages with `og:description` but no `<meta name="description">` — Google uses the standard meta tag, not OG.
- `www.signomy.xyz` redirects with 307 (temporary) instead of 301. This is a Vercel dashboard setting, not configurable in `vercel.json`.

## Devin Secrets Needed
None — SEO testing uses only public curl requests and source file inspection.
