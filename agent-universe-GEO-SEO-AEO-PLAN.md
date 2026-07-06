# agent-universe (signomy.xyz) — GEO/SEO/AEO Revival Plan

> **What this is:** Step-by-step instructions for the agent-universe internal
> session to bring signomy.xyz back from the dead on GEO/SEO/AEO. Built from
> the same playbook that shipped signalaf.com. Every step has verification
> commands and file paths.
>
> **Stack:** FastAPI + vanilla HTML (no build pipeline, no npm, no transpiler)
> **Site:** signomy.xyz
> **Repo:** ~/Desktop/agent-universe
> **Frontend:** frontend/ (57 HTML pages, served by FastAPI routes in app/routes/pages.py)
>
> **Created:** 2026-07-15
> **Updated:** 2026-07-15 — lean sitemap strategy (owner directive)
> **Author:** DEVIN (from the SigRank GEO/SEO/AEO session)
>
> **⚠️ INDEXING STRATEGY (owner directive 2026-07-15):**
> 200+ endpoints with no sitemap is rough for any crawler. Don't try to map
> everything. A **lean sitemap pointing at 10-15 key URLs** will do more than
> trying to index all 51+ pages. Focus on the pages that actually matter for
> discovery: seeds explainer, advisory board, governance docs, the main
> marketplace view. Crawl budget is finite — spend it on the pages that
> convert and cite.

---

## Current State (audited 2026-07-15)

| Layer | Status | Details |
|---|---|---|
| **robots.txt** | ✅ Good | Allows all crawlers + AI bots (GPTBot, ClaudeBot, PerplexityBot, etc.) |
| **sitemap.xml** | ⚠️ Too fat | 51 URLs — should be trimmed to 10-15 key pages (owner directive). Crawl budget is finite. |
| **canonical URLs** | ✅ Good | All 57 HTML pages have `<link rel="canonical">` |
| **OG tags** | ✅ Good | All pages have og:title, og:description, og:image, twitter:card |
| **llms.txt** | ✅ Good | 157 lines, covers agents + operators + governance |
| **Bing site auth** | ✅ Good | frontend/BingSiteAuth.xml present |
| **JSON-LD** | ❌ 4 of 57 pages | Only index.html, economics.html, academia.html, kingdoms.html have structured data |
| **llms-full.txt** | ❌ Missing | No expanded version with inline definitions |
| **IndexNow** | ❌ Missing | No /api/indexnow endpoint, no key file |
| **GSC** | ⚠️ Mid | Root indexed, 51 URLs pushed Jun 16, last crawl Jun 16 (~2 wks stale at audit). 78 impressions/28d. Interior pages unknown to Google. |
| **Bing** | ⚠️ Unknown | BingSiteAuth.xml present but no IndexNow. Need to verify Bing index state. |
| **Internal linking** | ⚠️ Weak | Pages are mostly standalone — no cross-links between content pages |
| **UTM on AI URLs** | ❌ Missing | llms.txt links have no UTM params |

### GSC findings (from INDEXING_DIAGNOSTIC_DEVIN_BRIEF.md, 2026-06-30)

| Property | Root | Interior | Last crawl | 28d impressions | Blocker |
|---|---|---|---|---|---|
| signomy.xyz | PASS / indexed | 51 URLs pushed | 2026-06-16 | 78 | Mid. Crawl ~2 wks old. Diagnose interior coverage + whether the 51 pushed URLs land. |

Render is NOT the blocker — raw curl returns real `<title>` + content (server-rendered HTML, not SPA).

---

## The Plan — 8 Steps

### Step 0: Trim sitemap to 10-15 key URLs (owner directive)

The current sitemap has 51 URLs. That's too many for a site with 78 impressions/28d
and a 2-week-stale crawl. Google allocates crawl budget based on site authority —
a low-authority site with 51 URLs in the sitemap means Google samples a few and
ignores the rest. A lean sitemap of 10-15 key URLs concentrates crawl budget on
the pages that actually matter for discovery and citation.

**The 12 URLs to keep** (the pages that matter for discovery + citation + conversion):

| # | URL | Why it matters |
|---|---|---|
| 1 | `https://signomy.xyz/` | Homepage — already indexed, the entry point |
| 2 | `https://signomy.xyz/kassa` | Main marketplace view — the core product |
| 3 | `https://signomy.xyz/missions` | Missions board — core product |
| 4 | `https://signomy.xyz/governance` | Governance hub — MO§ES framework, citation target |
| 5 | `https://signomy.xyz/seeds` | Seeds explainer — provenance/DOI system, unique IP |
| 6 | `https://signomy.xyz/advisory` | Advisory board — recruiting + credibility |
| 7 | `https://signomy.xyz/vault` | Governance docs (GOV-001 through GOV-006) — citation target |
| 8 | `https://signomy.xyz/economics` | Economy page — trust tiers, 40/30/30 split, quotable |
| 9 | `https://signomy.xyz/helpwanted` | Help wanted board — 31 open roles, recruiting |
| 10 | `https://signomy.xyz/forums` | Forums — community + fresh content signal |
| 11 | `https://signomy.xyz/leaderboard` | Agent leaderboard — data surface |
| 12 | `https://signomy.xyz/llms.txt` | AI crawler map — discovery for AI engines |

**What to do:**

1. Edit `frontend/sitemap.xml` — replace the 51-URL version with the 12 URLs above
2. Edit `frontend/sitemap-v2.xml` — same 12 URLs (or delete this file if it's redundant)
3. Keep the other pages reachable via internal links (Step 5) — they're still
   crawlable, just not in the sitemap. This is intentional: Google follows links
   from indexed pages, and the sitemap is for priority signaling, not exhaustive
   enumeration.

**The lean sitemap template:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://signomy.xyz/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>
  <url><loc>https://signomy.xyz/kassa</loc><changefreq>daily</changefreq><priority>0.9</priority></url>
  <url><loc>https://signomy.xyz/missions</loc><changefreq>daily</changefreq><priority>0.9</priority></url>
  <url><loc>https://signomy.xyz/governance</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>
  <url><loc>https://signomy.xyz/seeds</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>
  <url><loc>https://signomy.xyz/advisory</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>
  <url><loc>https://signomy.xyz/vault</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>
  <url><loc>https://signomy.xyz/economics</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>
  <url><loc>https://signomy.xyz/helpwanted</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>
  <url><loc>https://signomy.xyz/forums</loc><changefreq>daily</changefreq><priority>0.6</priority></url>
  <url><loc>https://signomy.xyz/leaderboard</loc><changefreq>daily</changefreq><priority>0.6</priority></url>
  <url><loc>https://signomy.xyz/llms.txt</loc><changefreq>weekly</changefreq><priority>0.5</priority></url>
</urlset>
```

**Re-submit to GSC after deploy:**
```bash
cd ~/Desktop/SigRank
export GSC_SA_KEY=~/.config/sigrank/gsc-sa.json
export GSC_SITE="sc-domain:signomy.xyz"
node scripts/gsc/gsc.mjs sitemaps:submit https://signomy.xyz/sitemap.xml
```

**Verification:**
```bash
curl -s https://signomy.xyz/sitemap.xml | grep -c "<url>"  # should be 12
```

---

### Step 1: Add JSON-LD to the 53 pages that don't have it

This is the biggest job. 4 of 57 pages have JSON-LD. The other 53 need it.

**Approach:** Since this is vanilla HTML (no builders), JSON-LD blocks are
hardcoded `<script type="application/ld+json">` tags in each HTML file's `<head>`.

**Priority order** (by traffic/importance):

#### Tier 1 — Core content pages (do these first)

| Page | File | JSON-LD type | Why |
|---|---|---|---|
| /missions | missions.html | `ItemList` of bounties + `BreadcrumbList` | Core product page |
| /kassa | kassa.html | `Service` + `BreadcrumbList` | Marketplace page |
| /governance | governance.html | `GovernmentOrganization` + `BreadcrumbList` | Governance hub |
| /forums | forums.html | `WebPage` + `BreadcrumbList` | Community page |
| /helpwanted | helpwanted.html | `ItemList` of job postings + `BreadcrumbList` | 31 open roles |
| /treasury | treasury.html | `WebPage` + `BreadcrumbList` | Economy dashboard |
| /vault | vault.html | `ItemList` of GOV docs + `BreadcrumbList` | Governance documents |
| /economics | economics.html | Already has `Service` — add `BreadcrumbList` | Economy page |
| /leaderboard | leaderboard.html | `ItemList` of agents + `BreadcrumbList` | Agent ranking |
| /about | about.html | `AboutPage` + `BreadcrumbList` | About page |
| /contact | contact.html | `ContactPage` + `BreadcrumbList` | Contact page |
| /advisory | advisory.html | `WebPage` + `BreadcrumbList` | Advisory board |
| /world | world.html (or kingdoms.html) | Already has `Organization` — add `WebPage` | 3D world hub |

#### Tier 2 — Feature pages

| Page | File | JSON-LD type |
|---|---|---|
| /deploy | deploy.html | `WebApplication` + `BreadcrumbList` |
| /campaign | campaign.html | `WebApplication` + `BreadcrumbList` |
| /console | console.html | `WebApplication` (admin tool) |
| /agents | agents.html | `ItemList` of agents + `BreadcrumbList` |
| /agentdash | agentdash.html | `WebPage` + `BreadcrumbList` |
| /seeds | seeds.html | `WebPage` + `BreadcrumbList` (provenance/DOI system) |
| /civitas | civitas.html | `WebPage` + `BreadcrumbList` |
| /senate | senate.html | `WebPage` + `BreadcrumbList` |
| /academia | academia.html | Already has `ScholarlyArticle` + `Dataset` — add `BreadcrumbList` |
| /moses | moses.html | `WebPage` + `BreadcrumbList` (governance framework) |
| /black-card | black-card.html | `WebPage` + `BreadcrumbList` |
| /grand-opening | grand-opening.html | `Event` + `BreadcrumbList` |
| /early-believers | early-believers.html | `WebPage` + `BreadcrumbList` |
| /earnings-matrix | agent-earnings-matrix.html | `WebApplication` + `BreadcrumbList` |
| /earnings-journey | agent-earnings-journey.html | `WebPage` + `BreadcrumbList` |
| /wave-registry | wave-registry.html | `ItemList` + `BreadcrumbList` |
| /fee-credit-packs | fee-credit-packs.html | `ItemList` + `BreadcrumbList` |
| /portal | portal.html | `CollectionPage` + `BreadcrumbList` |
| /sitemap | sitemap.html | `CollectionPage` + `BreadcrumbList` |

#### Tier 3 — Detail/sub-pages (lower priority)

| Page | File | JSON-LD type |
|---|---|---|
| /vault/gov-001 through gov-006 | vault-doc.html (dynamic) | `Legislation` + `BreadcrumbList` |
| /agent-profile | agent-profile.html | `ProfilePage` + `BreadcrumbList` |
| /mission | mission.html (dynamic) | `WebPage` + `BreadcrumbList` |
| /kassa-post | kassa-post.html (dynamic) | `WebPage` + `BreadcrumbList` |
| /kassa-thread | kassa-thread.html (dynamic) | `WebPage` + `BreadcrumbList` |
| /join | join.html | `WebPage` + `BreadcrumbList` |
| /connect | connect.html | `WebPage` + `BreadcrumbList` |
| /connect-success | connect-success.html | `WebPage` + `BreadcrumbList` |
| /products | products.html | `ItemList` + `BreadcrumbList` |
| /services | services.html | `ItemList` + `BreadcrumbList` |
| /hiring | hiring.html | `ItemList` + `BreadcrumbList` |
| /iso-collaborators | iso-collaborators.html | `WebPage` + `BreadcrumbList` |
| /sig-arena | sig-arena.html | `WebPage` + `BreadcrumbList` |
| /refinery | refinery.html | `WebPage` + `BreadcrumbList` |
| /switchboard | switchboard.html | `WebPage` + `BreadcrumbList` |
| /slots | slots.html | `WebPage` + `BreadcrumbList` |
| /bountyboard | bountyboard.html | `ItemList` + `BreadcrumbList` |
| /dashboard | dashboard.html | `WebPage` + `BreadcrumbList` |
| /lobby | lobby.html | `WebPage` + `BreadcrumbList` |
| /entry | entry.html | `WebPage` + `BreadcrumbList` |
| /command | command.html | `WebApplication` + `BreadcrumbList` |
| /admin | admin.html | Skip (disallowed in robots.txt) |

#### How to add JSON-LD to a page

Insert this block in the `<head>` of each HTML file, after the existing `<meta>` tags and before `</head>`:

```html
<!-- JSON-LD: BreadcrumbList -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://signomy.xyz/"},
    {"@type": "ListItem", "position": 2, "name": "PAGE_NAME", "item": "https://signomy.xyz/PAGE_PATH"}
  ]
}
</script>
```

For pages that need a specific type (ItemList, Service, WebApplication, etc.), add a second JSON-LD block. See the existing blocks in `frontend/index.html` and `frontend/economics.html` for the pattern.

**Template for BreadcrumbList** (reuse for every page — just change PAGE_NAME and PAGE_PATH):

```html
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
{"@type":"ListItem","position":1,"name":"Home","item":"https://signomy.xyz/"},
{"@type":"ListItem","position":2,"name":"PAGE_NAME","item":"https://signomy.xyz/PAGE_PATH"}
]}
</script>
```

**Template for WebPage** (for content pages that don't need a specific type):

```html
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"WebPage","@id":"https://signomy.xyz/PAGE_PATH#page",
"name":"PAGE_TITLE","url":"https://signomy.xyz/PAGE_PATH",
"description":"PAGE_DESCRIPTION",
"isPartOf":{"@id":"https://signomy.xyz/#website"},
"publisher":{"@id":"https://signomy.xyz/#org"}}
</script>
```

**Template for ItemList** (for listing pages — missions, agents, leaderboard, etc.):

```html
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"ItemList","@id":"https://signomy.xyz/PAGE_PATH#list",
"name":"LIST_NAME","url":"https://signomy.xyz/PAGE_PATH",
"numberOfItems":COUNT,
"itemListElement":[
{"@type":"ListItem","position":1,"name":"ITEM_1","url":"https://signomy.xyz/ITEM_1_URL"}
]}
</script>
```

**Verification:**
```bash
cd ~/Desktop/agent-universe
# Count pages with JSON-LD
for f in frontend/*.html; do if grep -q "application/ld+json" "$f"; then echo "✓ $(basename $f)"; fi; done | wc -l
# Should be 56+ (all except admin.html)
```

---

### Step 2: Build llms-full.txt

The existing `frontend/llms.txt` is the map. Build `frontend/llms-full.txt` as
the expanded version — inlines everything an AI engine needs to cite CIVITAE
in a single fetch.

**What to inline:**

1. **What CIVITAE is** (2-3 paragraphs, quotable)
2. **The trust tier economy** (the 4-tier table — Ungoverned 15% → Black Card 2%)
3. **The 40/30/30 treasury split**
4. **MO§ES governance model** (constitutional constraints, audit trail, SHA-256 hash chain)
5. **The provision API** (signup, heartbeat, slot fill/leave — the 5-step quick start)
6. **The 12+ formations** (WEDGE, PINCER, VANGUARD, etc.)
7. **The seed/DOI provenance system** (SHA-256 DOI for every tracked action)
8. **The dual-signature envelope** (ECDSA + Dilithium/Falcon)
9. **The 30+ pages** (what each one is, with one-line descriptions)
10. **All page links with UTM params** (`?utm_source=ai&utm_medium=answer_engine`)
11. **Citation block** (how to cite CIVITAE)
12. **All Zenodo DOIs + ORCID**

**File:** Create `frontend/llms-full.txt`

**Route:** Add to `app/routes/pages.py`:
```python
@router.get("/llms-full.txt")
async def llms_full():
    return FileResponse(state.frontend_dir / "llms-full.txt", media_type="text/plain")
```

**Verification:**
```bash
curl -s https://signomy.xyz/llms-full.txt | head -20
```

---

### Step 3: Add UTM params to llms.txt

All AI-surfaced URLs in `frontend/llms.txt` should carry
`?utm_source=ai&utm_medium=answer_engine` so you can measure AI-driven
signups in PostHog (or whatever analytics you use).

**How:** Find-replace in `frontend/llms.txt`:
- `https://signomy.xyz/kassa` → `https://signomy.xyz/kassa?utm_source=ai&utm_medium=answer_engine`
- `https://signomy.xyz/missions` → `https://signomy.xyz/missions?utm_source=ai&utm_medium=answer_engine`
- (repeat for all signomy.xyz URLs in the file)

**Don't add UTM to:** the API endpoints (POST /api/provision/signup etc.) —
those are instructions, not click-through links.

---

### Step 4: Build IndexNow endpoint

Bing has BingSiteAuth.xml set up but no IndexNow for instant URL submission.
This is the same pattern as signalaf.com.

**4a. Create the key file:**

Create `frontend/indexnow-key.txt` with a random 32-char hex string:
```
b4e8c2a6f0d4e8c2a6f0d4e8c2a6f0d4e8c2a6f0d4e8c2a6f0d4e8c2a6f0d4e8c2
```

**4b. Add the route in `app/routes/pages.py`:**
```python
@router.get("/indexnow-key.txt")
async def indexnow_key():
    return FileResponse(state.frontend_dir / "indexnow-key.txt", media_type="text/plain")
```

**4c. Create the IndexNow POST endpoint:**

Add to `app/routes/core.py` (or a new `app/routes/indexnow.py`):
```python
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["indexnow"])

INDEXNOW_KEY = "b4e8c2a6f0d4e8c2a6f0d4e8c2a6f0d4e8c2a6f0d4e8c2a6f0d4e8c2a6f0d4e8c2"

@router.post("/api/indexnow")
async def indexnow_push(request: Request):
    body = await request.json()
    urls = body.get("urls", [])
    if not urls:
        return JSONResponse({"error": "No URLs provided"}, status_code=400)

    payload = {
        "host": "signomy.xyz",
        "key": INDEXNOW_KEY,
        "keyLocation": "https://signomy.xyz/indexnow-key.txt",
        "urlList": urls[:10000],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.indexnow.org/IndexNow",
            json=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

    return JSONResponse({
        "status": resp.status_code,
        "ok": resp.status_code in (200, 202),
        "submitted": len(urls),
        "key": INDEXNOW_KEY[:8] + "…",
    })
```

**4d. Wire the router in `app/server.py`** (follow the existing pattern for other routers).

**4e. Fire the push** (after deploy — only the 12 lean sitemap URLs, not all 51):
```bash
curl -X POST https://signomy.xyz/api/indexnow \
  -H 'Content-Type: application/json' \
  -d '{"urls":["https://signomy.xyz/","https://signomy.xyz/kassa","https://signomy.xyz/missions","https://signomy.xyz/governance","https://signomy.xyz/seeds","https://signomy.xyz/advisory","https://signomy.xyz/vault","https://signomy.xyz/economics","https://signomy.xyz/helpwanted","https://signomy.xyz/forums","https://signomy.xyz/leaderboard","https://signomy.xyz/llms.txt","https://signomy.xyz/llms-full.txt"]}'
```

**Verification:**
```bash
curl -s https://signomy.xyz/indexnow-key.txt  # should return the key
curl -s -X POST https://signomy.xyz/api/indexnow -H 'Content-Type: application/json' -d '{"urls":["https://signomy.xyz/"]}'
```

---

### Step 5: Add internal links between pages

Most pages are standalone — no cross-links. Google discovers pages via links.
Add a footer or sidebar with links to the core pages on every content page.

**5a. The simplest approach:** Add a "Explore" section to `_footer.js` (or
create one if it doesn't exist) with links to the 10 core pages:

```html
<nav class="explore-links">
  <a href="/missions">Missions</a>
  <a href="/kassa">KA§§A Marketplace</a>
  <a href="/governance">Governance</a>
  <a href="/forums">Forums</a>
  <a href="/helpwanted">Help Wanted</a>
  <a href="/treasury">Treasury</a>
  <a href="/vault">Vault</a>
  <a href="/economics">Economics</a>
  <a href="/leaderboard">Leaderboard</a>
  <a href="/about">About</a>
</nav>
```

**5b. Add cross-links in page content:**
- /missions → link to /kassa (post a bounty) and /helpwanted (find agents)
- /governance → link to /vault (governance documents) and /senate
- /economics → link to /treasury (live economy) and /leaderboard
- /about → link to /contact, /advisory, /helpwanted
- /kassa → link to /missions and /leaderboard
- /helpwanted → link to /kassa and /agents

**Why:** Google's crawler follows internal links. If /missions links to /kassa
and /kassa links to /leaderboard, Google discovers all three from any one of
them. Without internal links, Google only discovers pages that are in the
sitemap — and sitemap discovery is weaker than link discovery.

---

### Step 6: GSC re-inspect + re-push

**6a. Re-inspect the 51 URLs that were pushed Jun 16:**

```bash
cd ~/Desktop/SigRank
export GSC_SA_KEY=~/.config/sigrank/gsc-sa.json
export GSC_SITE="sc-domain:signomy.xyz"

# Check sitemap status
node scripts/gsc/gsc.mjs sitemaps:list

# Inspect key pages
node scripts/gsc/gsc.mjs inspect https://signomy.xyz/missions
node scripts/gsc/gsc.mjs inspect https://signomy.xyz/kassa
node scripts/gsc/gsc.mjs inspect https://signomy.xyz/governance
node scripts/gsc/gsc.mjs inspect https://signomy.xyz/forums
node scripts/gsc/gsc.mjs inspect https://signomy.xyz/helpwanted

# Check analytics
node scripts/gsc/gsc.mjs analytics 28
```

**6b. If pages are still "discovered, not indexed":**
- The internal links (Step 5) should help on the next crawl
- Re-push the URLs: `node scripts/gsc/gsc.mjs index https://signomy.xyz/missions https://signomy.xyz/kassa ...`
- Check the `google` canonical field in inspect output — make sure Google agrees with your canonical

**6c. If pages are "unknown to Google":**
- Verify the sitemap is submitted and 0 errors
- Verify the page is reachable from an indexed page (follow internal links from /)
- Submit the individual URL via the Indexing API

---

### Step 7: Expand Organization sameAs

The homepage Organization JSON-LD has 9 sameAs entries. Add the missing surfaces:

**Current (9):**
- ORCID, GitHub org, agent-universe repo, 3 Zenodo DOIs, signalaf.com, mos2es.com, mos2es.xyz

**Add:**
- `https://github.com/SunrisesIllNeverSee/sigrank-app` (the SigRank web app)
- `https://github.com/SunrisesIllNeverSee/sigrank-mcp` (the SigRank CLI)
- `https://www.npmjs.com/package/sigrank` (npm package)
- `https://www.npmjs.com/package/civitae-mcp` (the CIVITAE MCP package, if published)
- `https://doi.org/10.5281/zenodo.19105225` (Experimental Record — if not already there)
- `https://doi.org/10.5281/zenodo.19109397` (Transformation Harness — if not already there)
- `https://doi.org/10.5281/zenodo.20031715` (Propositions Prospectus — if not already there)

**File:** `frontend/index.html` — edit the Organization JSON-LD block's `sameAs` array.

**Verification:**
```bash
curl -s https://signomy.xyz/ | python3 -c "
import sys, re, json
html = sys.stdin.read()
blocks = re.findall(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL)
for b in blocks:
    d = json.loads(b)
    if d.get('@type') == 'Organization':
        print('sameAs count:', len(d.get('sameAs',[])))
        for s in d.get('sameAs',[]): print(' ', s)
"
```

---

## Verification (after all steps)

```bash
# === JSON-LD coverage ===
cd ~/Desktop/agent-universe
for f in frontend/*.html; do if grep -q "application/ld+json" "$f"; then echo "✓ $(basename $f)"; else echo "✗ $(basename $f)"; fi; done
# Should show ✓ for all except admin.html

# === llms-full.txt ===
curl -s https://signomy.xyz/llms-full.txt | head -20

# === IndexNow ===
curl -s https://signomy.xyz/indexnow-key.txt
curl -s -X POST https://signomy.xyz/api/indexnow -H 'Content-Type: application/json' -d '{"urls":["https://signomy.xyz/"]}'

# === UTM params in llms.txt ===
curl -s https://signomy.xyz/llms.txt | grep -c "utm_source=ai"
# Should be > 0

# === Internal links ===
curl -s https://signomy.xyz/missions | grep -c 'href="/kassa"'
# Should be > 0

# === Organization sameAs ===
curl -s https://signomy.xyz/ | python3 -c "
import sys, re, json
html = sys.stdin.read()
blocks = re.findall(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL)
for b in blocks:
    d = json.loads(b)
    if d.get('@type') == 'Organization':
        print('sameAs count:', len(d.get('sameAs',[])))
"

# === GSC ===
cd ~/Desktop/SigRank
export GSC_SA_KEY=~/.config/sigrank/gsc-sa.json
export GSC_SITE="sc-domain:signomy.xyz"
node scripts/gsc/gsc.mjs sitemaps:list
node scripts/gsc/gsc.mjs inspect https://signomy.xyz/missions
node scripts/gsc/gsc.mjs analytics 28
```

---

## Firing Order

| Step | What | Time | Depends on |
|---|---|---|---|
| 0 | Trim sitemap to 12 key URLs | 10 min | — |
| 1 | Add JSON-LD to 53 pages | 2-3 hours | — |
| 2 | Build llms-full.txt | 30 min | — |
| 3 | Add UTM to llms.txt | 10 min | — |
| 4 | Build IndexNow endpoint | 30 min | — |
| 5 | Add internal links | 1 hour | — |
| 7 | Expand Organization sameAs | 10 min | — |
| — | Deploy to Railway + Vercel | 5 min | Steps 0-5, 7 |
| 4e | Fire IndexNow push (13 URLs) | 1 min | Deploy done |
| 0b | Re-submit lean sitemap to GSC | 1 min | Deploy done |
| 6 | GSC re-inspect | 10 min | Deploy done, wait 24-48h |

**Total:** ~4-5 hours of work + 24-48h wait for Bing/Google to crawl.

---

## What NOT to do

- **Don't add JSON-LD to admin.html** — it's disallowed in robots.txt
- **Don't change the canonical URLs** — they're already correct
- **Don't change the OG tags** — they're already correct
- **Don't change the sitemap** — it's already correct (51 URLs)
- **Don't block any AI crawlers** — robots.txt already allows them all
- **Don't add PostHog** — that's a separate track (and agent-universe uses a different analytics stack)
- **Don't touch the backend logic** — this is frontend + routes only

---

## Reference: The SigRank playbook

The full GEO/SEO/AEO playbook (with all 10 portable patterns) is at:
`~/Desktop/SigRank-GEO-SEO-AEO-PLAYBOOK.md`

Read it for the strategy, the patterns, and the verification commands. This plan
adapts those patterns for the agent-universe stack (FastAPI + vanilla HTML
instead of Next.js + React).
