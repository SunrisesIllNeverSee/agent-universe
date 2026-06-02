---
name: testing-seo
description: Test SEO changes (meta tags, canonicals, sitemaps, redirects, IndexNow) on signomy.xyz. Use when verifying frontend HTML head changes, Vercel config updates, or IndexNow ping script changes.
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

### IndexNow — Verify key file
```bash
# Check key file content matches filename
cat -A frontend/036af2adecc34d87884249a062326a1e.txt
# After deploy, verify it's accessible:
curl -s https://signomy.xyz/036af2adecc34d87884249a062326a1e.txt
```

### IndexNow — Test ping script
```bash
# Single URL mode
./scripts/indexnow-ping.sh /treasury

# Full sitemap mode (all URLs)
./scripts/indexnow-ping.sh

# Validate JSON payload structure
bash -c '
HOST="signomy.xyz"
KEY="036af2adecc34d87884249a062326a1e"
url="https://signomy.xyz/treasury"
payload="{\"host\":\"$HOST\",\"key\":\"$KEY\",\"keyLocation\":\"https://$HOST/$KEY.txt\",\"urlList\":[\"$url\"]}"
echo "$payload" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d)"
'
```

## IndexNow Expected Responses
- **Before key file is deployed:** `api.indexnow.org` and `www.bing.com` return 403 (cannot verify domain). `yandex.com` may return 202 (more lenient).
- **After key file is deployed:** All engines should return 200 or 202 (accepted).
- The script must be run from the repo root (or the fallback `$(dirname "$0")/../frontend/sitemap.xml` path must resolve).
- If sitemap.xml is not found, the script exits with code 1 and prints "Error: sitemap.xml not found".

## Common Issues
- `sitemap.html` canonical was broken (pointed to `/mapsite` which 404'd on Vercel). The canonical should match the actual serving URL.
- `sitemap-v2.xml` is the sitemap Google successfully fetches. `sitemap.xml` may show "Couldn't fetch" in Search Console. Both should be listed in `robots.txt`.
- Pages with `og:description` but no `<meta name="description">` — Google uses the standard meta tag, not OG.
- `www.signomy.xyz` redirects with 307 (temporary) instead of 301. This is a Vercel dashboard setting, not configurable in `vercel.json`.
- Google deprecated sitemap ping endpoints (`google.com/ping?sitemap=` returns 404). Use IndexNow for non-Google engines; Google requires Search Console UI submissions.

## Devin Secrets Needed
None — SEO testing uses only public curl requests and source file inspection.