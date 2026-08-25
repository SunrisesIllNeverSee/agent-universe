# GSC toolkit — `gsc.mjs`

Programmatic Google Search Console + Indexing for signalaf.com. One Node script, all ops.
Built because the owner already has a GCP account + submitted the sitemap once via the UI and wants the
repeatable CLI path (re-submit sitemaps on each new /research drop, push indexing, pull coverage).

## One-time setup (~10 min)

1. **GCP project** (use any existing one). Enable two APIs:
   - **Search Console API** (`searchconsole.googleapis.com`)
   - **Web Search Indexing API** (`indexing.googleapis.com`)
   Console → APIs & Services → Enable APIs → search each → Enable.
2. **Service account:** IAM & Admin → Service Accounts → Create. Name it `sigrank-gsc`. Grant it role
   **Service Usage Admin** (lets the toolkit enable required Google APIs itself — e.g. the Indexing API;
   without it you must enable each API by hand in the console).
   → Keys → Add key → JSON → download. Save it somewhere private, e.g. `~/.config/sigrank/gsc-sa.json`
   (NOT in the repo — it's a credential).
3. **Grant it on the property:** Search Console → signalaf.com → Settings → Users and permissions →
   Add user → paste the service account's **email** (`...@<project>.iam.gserviceaccount.com`) → role **Owner**.
   (Owner is required for the Indexing API; sitemaps/analytics need ≥ Full.)
4. **Install the one dep** (once): `cd scripts/gsc && npm install`
5. **Point the script at the key:** `export GSC_SA_KEY=~/.config/sigrank/gsc-sa.json`

## Property type
Default is the **Domain** property: `GSC_SITE=sc-domain:signalaf.com` (the script's default).
If yours is a URL-prefix property instead, `export GSC_SITE="https://signalaf.com/"`.

## Commands

```bash
node scripts/gsc/gsc.mjs sitemaps:list                          # registered sitemaps + error/warning counts
node scripts/gsc/gsc.mjs sitemaps:submit                        # (re)submit https://signalaf.com/sitemap.xml
node scripts/gsc/gsc.mjs sitemaps:submit https://signalaf.com/sitemap.xml
node scripts/gsc/gsc.mjs index https://signalaf.com/research/q1-2026   # push one/many URLs (Indexing API)
node scripts/gsc/gsc.mjs index https://signalaf.com/methodology https://signalaf.com/
node scripts/gsc/gsc.mjs index:status https://signalaf.com/research/q1-2026
node scripts/gsc/gsc.mjs inspect https://signalaf.com/methodology       # URL inspection: verdict + coverage
node scripts/gsc/gsc.mjs analytics 28                          # clicks/impressions + top 15 pages, last N days
node scripts/gsc/gsc.mjs check:index                           # inspect ALL sitemap URLs, report status
node scripts/gsc/gsc.mjs check:index --push                    # inspect + auto-push unindexed URLs
```

### `check:index` — automated indexing audit

Fetches the sitemap, inspects every URL via the URL Inspection API, and reports
which pages are indexed, discovered-but-not-indexed, or unknown to Google.
With `--push`, it also index-pushes every unindexed URL via the Indexing API.

```bash
# Inspect only (read-only):
GSC_SITE="sc-domain:signalaf.com" node gsc.mjs check:index

# Inspect + push unindexed:
GSC_SITE="sc-domain:signalaf.com" node gsc.mjs check:index --push

# Use a different sitemap:
GSC_SITE="sc-domain:signalaf.com" node gsc.mjs check:index --push --sm=https://signalaf.com/sitemap.xml
```

Exit code: **0** if all URLs indexed, **1** if any unindexed (useful for cron/CI).
Output: one line per URL with `✓` (indexed) / `○` (discovered) / `✗` (unknown/excluded),
then a summary with counts. When `--push` is used, each pushed URL is logged.

## Typical flow when you ship a new page (e.g. next quarterly report)
```bash
export GSC_SA_KEY=~/.config/sigrank/gsc-sa.json
node scripts/gsc/gsc.mjs sitemaps:submit                        # re-ping the (already-updated) sitemap
node scripts/gsc/gsc.mjs index https://signalaf.com/research/q2-2026   # fast-track the new URL
node scripts/gsc/gsc.mjs inspect https://signalaf.com/research/q2-2026 # confirm Google sees it
```

## Notes
- **Read-only & safe:** `sitemaps:list`, `analytics`, `index:status`, `inspect`, `check:index` (without `--push`). **Mutating:** `sitemaps:submit`, `index`, `check:index --push`.
- The Indexing API is officially scoped to JobPosting/BroadcastEvent but is widely used to nudge crawl of any
  page; treat it as a hint, not a guarantee. Don't spam it (quota: 200 URLs/day default).
- The key file is a **credential** — keep it out of git (it's not in the repo; `~/.config/...` is the convention here).
- No `gcloud` required — auth is the service-account JSON via `google-auth-library`.


## Self-enable APIs (if the SA has Service Usage Admin)
```bash
# enable any Google API the SA needs (project 694528229435):
node -e 'import("google-auth-library").then(async({GoogleAuth})=>{const c=await new GoogleAuth({keyFile:process.env.GSC_SA_KEY,scopes:["https://www.googleapis.com/auth/cloud-platform"]}).getClient();await c.request({method:"POST",url:"https://serviceusage.googleapis.com/v1/projects/694528229435/services/indexing.googleapis.com:enable"});console.log("enabled")})'
```
Project id: **694528229435**. Search Console API + Web Search Indexing API are the two this toolkit uses.
