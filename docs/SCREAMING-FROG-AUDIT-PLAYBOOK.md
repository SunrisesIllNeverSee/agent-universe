# Screaming Frog Audit Playbook — signomy.xyz

> Adapted from the SigRank SF playbook (`~/Desktop/SigRank/Devins_Plans/growth/seo-geo-plan.md` Phase 7
> and `SEO_AEO_GEO_MAINTENANCE.md` Section 10) for the agent-universe site. Run this against
> **https://signomy.xyz** to get a baseline crawl, find orphan pages, broken links, redirect chains,
> and internal linking gaps.

## Site facts (verify before crawling)

| Item | Value | Source |
|------|-------|--------|
| Canonical domain | `https://signomy.xyz` | sitemap.xml, canonical tags |
| Sitemap URLs | 20 | `frontend/sitemap.xml` |
| Frontend HTML files | 57 | `frontend/*.html` |
| Vercel 301 redirects | 9 | `vercel.json` → `redirects[]` |
| Vercel rewrites (internal) | ~20 | `vercel.json` → `rewrites[]` |
| Backend page routes | ~80 | `app/routes/pages.py` |
| robots.txt | allows all + AI bots, disallows `/api/operator/`, `/admin`, `/console` | `frontend/robots.txt` |
| llms.txt | yes | served at `/llms.txt` |
| Free SF tier limit | 500 URLs | well within range for this site |

### Architecture note (matters for crawl interpretation)

signomy.xyz is a **split deploy**:
- **Vercel** serves `frontend/` static HTML + applies `vercel.json` redirects/rewrites + proxies `/api/*`, `/mcp/*`, `/docs/*`, `/ws/*`, `/health` to Railway.
- **Railway** runs the FastAPI backend (`app/server.py`) which *also* serves most page routes directly from `app/routes/pages.py` (so the same page is reachable via two paths — Vercel rewrite and Railway direct).

When Screaming Frog crawls `https://signomy.xyz`, it hits Vercel. The Railway-direct URLs
(`agent-universe-production.up.railway.app/...`) are a **different origin** and won't be crawled
unless you add them as a second crawl. Recommended: crawl only the Vercel origin first.

### Known redirect map (verify SF sees the same)

| Source | → Destination | Type |
|--------|---------------|------|
| `/openroles` | `/helpwanted` | 301 |
| `/marketplace` | `/products` | 301 |
| `/3d` | `/world` | 301 |
| `/economy` | `/economics` | 301 |
| `/civitae-roadmap` | `/portal` | 301 |
| `/join` | `/#collaborate` | 301 |
| `/agent-earnings-matrix` | `/earnings-matrix` | 301 (then rewrite serves the file) |
| `/agent-earnings-journey` | `/earnings-journey` | 301 (then rewrite serves the file) |
| `/fee-credit-packs` | `/fee-credits` | 301 (then rewrite serves the file) |

The earnings/fee-credits pairs are **redirect + rewrite** combos: the 301 sends the file-name URL
to the short alias, then a Vercel rewrite internally maps the short alias back to the file-name to
serve content. This is intentional (short alias is canonical, file-name is the actual file). SF
should report the 301 but NOT a loop — if it reports a loop, that's a bug.

---

## Setup

1. Download Screaming Frog SEO Spider (free, 500 URL limit): https://www.screamingfrog.co.uk/seo-spider/
2. Open it, enter `https://signomy.xyz` as the URL.
3. **Config → Spider → Crawl → check "Crawl Sitemap"** and add `https://signomy.xyz/sitemap.xml`
   (ensures SF discovers the 20 sitemap URLs even if they're orphaned internally).
4. **Config → Robots.txt → Respect** (we want to see what crawlers see — but also note what's
   disallowed so we can confirm `/admin`, `/console`, `/api/operator/` are NOT crawled).
5. Click **Start**.
6. Wait for the crawl to finish (20–80 URLs, under a minute).

### Recommended SF settings for this site

- **Config → Spider → Rendering → JavaScript** — set to "Render" (some pages inject `_nav.js`
  and fetch `pages.json` at load; we want SF to see the rendered nav links).
- **Config → Limits → Max URI Limit** — leave at 500 (free tier). We're at ~80 URLs max.
- **Config → Advanced → Crawl External Links** — yes (we want to find broken outbound links to
  Railway, Stripe, MCP registries, GitHub, etc.).

---

## What to export

Save all exports to a folder you can share back (e.g. `~/Desktop/agent-universe/docs/sf-crawl-{date}/`).

| Export | Where in Screaming Frog | What it gives us |
|--------|-------------------------|------------------|
| Force-directed crawl diagram | Visualisations → Force-Directed Crawl Diagram | Internal linking graph — clusters, hubs, orphan pages (disconnected nodes) |
| Tree graph site visualization | Visualisations → Tree Graph → Site Structure | URL/directory hierarchy — site architecture at a glance |
| All internal links | File → Export → All Internal Links (CSV) | Every internal link: source, target, anchor text, status |
| All external links | File → Export → All External Links (CSV) | Every external link — find broken outbound links |
| Orphan pages | Reports → Orphan Pages (CSV) | Pages in the sitemap but not linked from anywhere |
| Redirects | Reports → Redirects (CSV) | Redirect chains and loops — flatten targets |
| Page titles & meta | Reports → Page Titles & Meta (CSV) | Missing/duplicate/too-long titles and descriptions |
| Broken links | Reports → Broken Links (CSV) | 404s and server errors — fix or remove |
| Response codes | Reports → Response Codes (CSV) | Full status code breakdown per URL |
| Canonicals | Reports → Canonical (CSV) | Verify canonical tags match the sitemap URL |

---

## What to look for (signomy.xyz-specific)

### 1. Orphan pages (highest priority for this site)

The sitemap has 20 URLs but `frontend/` has 57 HTML files and `pages.py` has ~80 routes. That
means **~37 pages are not in the sitemap** — some intentionally (admin, console, thread/post
detail pages with path params), some possibly by oversight.

**Action:** cross-reference SF's orphan pages report against `config/pages.json` (the portal
directory source of truth). Any page that's in `pages.json` as `live` but shows up as an orphan
in SF is an internal-linking gap — add a link to it from the portal, sitemap, or a related page.

### 2. Broken links (404s)

Likely sources on this site:
- Links to old `/openroles`, `/marketplace`, `/3d`, `/economy`, `/join` paths that should have
  been updated to the canonical alias when the 301s were added (2026-04-30 work). SF will show
  the 301, but if any internal link still points at the old path, that's a needless hop.
- Links to Railway-direct URLs (`agent-universe-production.up.railway.app/...`) from frontend
  pages — these should be relative (`/api/...`) so Vercel proxies them.
- External links to MCP registries (Smithery, PulseMCP, Glama), GitHub repos, Stripe docs —
  verify none have rotted.

### 3. Redirect chains

Each known redirect (table above) should be a **single hop**. SF's Redirects report will show
the chain length. If any chain is 2+ hops, flatten it.

**Specifically verify:** the `/agent-earnings-matrix` → `/earnings-matrix` pair does NOT form a
loop with the rewrite that serves `/agent-earnings-matrix.html`. SF should report one 301 and
a 200 on the destination.

### 4. Duplicate content / canonical mismatches

The 2026-04-30 audit added canonical tags to 56 pages. SF's Canonical report will show whether
every page's `rel=canonical` matches its own URL (self-referencing) or correctly points to a
preferred alias. Any "canonical mismatch" or "no canonical" flags are fix targets.

**Specifically verify:**
- `agent-earnings-matrix.html` canonical → `/earnings-matrix` (not self)
- `agent-earnings-journey.html` canonical → `/earnings-journey` (not self)
- `fee-credit-packs.html` canonical → `/fee-credits` (not self)
- `kingdoms.html` canonical → `/kingdoms` (the 2026-04-30 fix corrected this from `/`)
- `join.html` → should have `noindex,follow` (it's an orphan, the `/join` route 301s away)

### 5. Title / meta gaps

The 2026-07-07 work optimized meta tags on 20 priority pages. The other ~37 pages may still have
weak/missing titles or descriptions. SF's Page Titles & Meta report will flag:
- Missing `<title>`
- Duplicate titles
- Titles > 60 chars
- Missing meta description
- Descriptions > 155 chars

### 6. Internal linking depth

SF's tree graph shows click-depth from the homepage. Anything at depth 4+ is a candidate for a
direct link from a higher-level page (portal, sitemap, or a related hub page).

**Hub pages to verify are well-linked:** `/portal` (directory of all pages), `/sitemap` (the HTML
sitemap, separate from sitemap.xml), `/kassa` (marketplace hub), `/missions` (missions hub).

### 7. External link targets

The site links out to:
- Railway backend (should be proxied via Vercel, not direct)
- Stripe (checkout, docs)
- MCP registries (Smithery `smithery.ai`, PulseMCP, Glama, ClawHub)
- GitHub repos (SunrisesIllNeverSee/*)
- Resend, Vercel, FastAPI docs

Any 404/timeout on these is a rot signal.

---

## After the crawl

Drop the exported files (CSVs + diagram images) into `docs/sf-crawl-{date}/` and tell Devin.
Devin will:

1. Generate a Mermaid diagram of the site structure from the internal links CSV.
2. Cross-reference orphan pages against `config/pages.json` to find pages that are `live` but
   not linked internally.
3. Identify internal linking gaps (pages that should link to each other but don't).
4. Produce a fix list — which pages need internal links added, which redirects to flatten, which
   orphans to surface, which titles/meta to write.
5. Compare the SF-generated sitemap against `frontend/sitemap.xml` to find sitemap gaps.

### Fix-list format (what Devin will produce)

```
| Page | Issue | Fix | Priority |
|------|-------|-----|----------|
| /seeds | Orphan (not linked from any page) | Add link from /portal + /kassa | High |
| /openroles (internal link on /foo) | Points at redirect source | Update to /helpwanted | Med |
| /refinery | Title missing | Write <title> + meta description | Med |
```

---

## Cadence

- **First crawl:** baseline (this run).
- **Quarterly:** re-crawl and compare to baseline (SF has a "Compare Crawls" feature — load the
  previous crawl's save file and diff).
- **After any redirect/canonical/page-add change:** ad-hoc crawl to verify.

---

## SF features reference (for this site)

| Feature | Use it for on signomy.xyz |
|---------|--------------------------|
| Find Broken Links | 404s on old redirect paths, rotted external links |
| Audit Redirects | Verify the 9 known 301s are single-hop, no loops |
| Analyse Page Titles & Meta | Find the ~37 non-priority pages with weak meta |
| Discover Duplicate Content | Verify earnings/fee-credits consolidation worked |
| Review Robots & Directives | Confirm `/admin`, `/console`, `/api/operator/` are noindex/disallowed |
| Generate XML Sitemaps | Compare SF-generated sitemap vs `frontend/sitemap.xml` |
| Visualise Site Architecture | Find isolated clusters (e.g. /vault + /vault/{doc} subgraph) |
| Crawl JavaScript | See rendered nav links injected by `_nav.js` |
| Compare Crawls | Track issue count over time (quarterly) |

---

*Adapted 2026-07-12 from SigRank SF playbook. Source: `~/Desktop/SigRank/Devins_Plans/growth/seo-geo-plan.md` Phase 7 + `SEO_AEO_GEO_MAINTENANCE.md` Section 10.*
