# agent-universe (signomy.xyz) — GEO/SEO/AEO Revival Plan

> **What this is:** Step-by-step instructions for the agent-universe internal
> session to bring signomy.xyz back from the dead on GEO/SEO/AEO. Built from
> the same playbook that shipped signalaf.com, augmented with NotFair's
> GEO optimizer (Princeton/GA Tech KDD 2024) and meta-tags optimizer
> methodologies. Every step has verification commands and file paths.
>
> **Stack:** FastAPI + vanilla HTML (no build pipeline, no npm, no transpiler)
> **Site:** signomy.xyz
> **Repo:** ~/Desktop/agent-universe
> **Frontend:** frontend/ (57 HTML pages, served by FastAPI routes in app/routes/pages.py)
>
> **Created:** 2026-07-15
> **Updated:** 2026-07-07 — focus on 20 pages, add GEO content + meta tag steps
> **Author:** DEVIN (from the SigRank GEO/SEO/AEO session)
>
> **⚠️ INDEXING STRATEGY (owner directive 2026-07-07):**
> Focus everything on **20 priority pages** — the 19 GSC-indexed pages plus
> /helpwanted (high strategic value). Don't try to optimize all 57 pages.
> Crawl budget, JSON-LD, meta tags, GEO content, internal links — all
> concentrated on these 20. The other 37 pages remain crawlable via internal
> links but get no direct optimization.
>
> **GSC state (audited 2026-07-07):** 19 of 51 URLs indexed (37%).
> 68 impressions / 28 days, **0 clicks**. Root cause: brand-first titles
> ("CIVITAE —") not keyword-first, no numbers/power words/urgency,
> 3 pages missing meta descriptions entirely.

---

## Current State (audited 2026-07-07)

| Layer | Status | Details |
|---|---|---|
| **robots.txt** | ✅ Good | Allows all crawlers + AI bots (GPTBot, ClaudeBot, PerplexityBot, etc.) |
| **sitemap.xml** | ⚠️ Too fat | 51 URLs in sitemap-v2.xml — should be trimmed to 20 key pages |
| **canonical URLs** | ✅ Good | All 57 HTML pages have `<link rel="canonical">` |
| **OG tags** | ✅ Good | All pages have og:title, og:description, og:image, twitter:card |
| **llms.txt** | ✅ Good | 157 lines, covers agents + operators + governance |
| **Bing site auth** | ✅ Good | frontend/BingSiteAuth.xml present |
| **JSON-LD** | ❌ 4 of 57 pages | Only index.html, economics.html, academia.html, kingdoms.html have structured data |
| **llms-full.txt** | ❌ Missing | No expanded version with inline definitions |
| **IndexNow** | ❌ Missing | No /api/indexnow endpoint, no key file |
| **GSC** | ⚠️ Mid | 19 of 51 URLs indexed. 68 impressions/28d, **0 clicks**. Title tags are brand-first, not keyword-first. |
| **Bing** | ⚠️ Unknown | BingSiteAuth.xml present but no IndexNow. Need to verify Bing index state. |
| **Internal linking** | ⚠️ Weak | Pages are mostly standalone — no cross-links between content pages |
| **UTM on AI URLs** | ❌ Missing | llms.txt links have no UTM params |
| **Meta tags** | ❌ Weak | Brand-first titles, no numbers/power words, 3 pages missing descriptions entirely. 0 clicks from 68 impressions. |
| **GEO content** | ❌ Missing | No content optimized for AI citation (PAWC, evidence density, front-loaded answers) |

### GSC findings (from INDEXING_DIAGNOSTIC_DEVIN_BRIEF.md, 2026-06-30)

| Property | Root | Interior | Last crawl | 28d impressions | Blocker |
|---|---|---|---|---|---|
| signomy.xyz | PASS / indexed | 51 URLs pushed | 2026-06-16 | 78 | Mid. Crawl ~2 wks old. Diagnose interior coverage + whether the 51 pushed URLs land. |

Render is NOT the blocker — raw curl returns real `<title>` + content (server-rendered HTML, not SPA).

---

## The Plan — 10 Steps

### The 20 Priority Pages

All optimization effort (meta tags, JSON-LD, GEO content, internal links) is
concentrated on these 20 pages. Selected from GSC indexed pages + strategic value.

| # | URL | File | GSC impressions | Why it's in the top 20 |
|---|---|---|---|---|
| 1 | `/` | index.html | 20 | Homepage — entry point, highest impressions |
| 2 | `/kassa` | kassa.html | 10 | Main marketplace — core product |
| 3 | `/grand-opening` | grand-opening.html | 6 | Genesis Week event — time-sensitive |
| 4 | `/treasury` | treasury.html | 6 | Live economy dashboard — data surface |
| 5 | `/economics` | economics.html | 5 | Trust tiers, 40/30/30 split — quotable |
| 6 | `/kingdoms` | kingdoms.html | 5 | World hub — 100 districts, visual |
| 7 | `/missions` | missions.html | 4 | Missions board — core product |
| 8 | `/governance` | governance.html | 4 | MO§ES hub — citation target |
| 9 | `/contact` | contact.html | 3 | Contact — conversion page |
| 10 | `/seeds` | seeds.html | 2 | Provenance/DOI system — unique IP |
| 11 | `/leaderboard` | leaderboard.html | 1 | Agent rankings — data surface |
| 12 | `/moses` | moses.html | 1 | MO§ES framework — citation target |
| 13 | `/mission` | mission.html | 1 | Mission detail — dynamic page |
| 14 | `/vault` | vault.html | 0 (indexed) | GOV-001 through GOV-006 — citation target |
| 15 | `/bountyboard` | bountyboard.html | 0 (indexed) | Active bounties — conversion |
| 16 | `/products` | products.html | 0 (indexed) | Products marketplace — conversion |
| 17 | `/slots` | slots.html | 0 (indexed) | Slot mechanics — feature page |
| 18 | `/sig-arena` | sig-arena.html | 0 (indexed) | Eval arena — feature page |
| 19 | `/connect` | connect.html | 0 (indexed) | Connect — conversion page |
| 20 | `/helpwanted` | helpwanted.html | 0 (unindexed) | Open roles — high recruiting value |

---

### Step 0.5: Meta tag optimization for 20 pages (fix 0-click problem)

**Source:** NotFair meta-tags-optimizer methodology.

68 impressions, 0 clicks. Google is showing the pages but nobody clicks.
Root cause: brand-first titles ("CIVITAE —"), no numbers, no power words,
no urgency. 3 pages missing meta descriptions entirely.

**Title tag formula:** `Keyword | Benefit | Brand` or `Number + Keyword + Promise`
- Length: 50-60 characters
- Primary keyword near front (not brand name)
- Power words: Complete, Live, Open, Free, Active, Governed
- Numbers where relevant (26 missions, 14 seats, 40/30/30 split)

**Meta description formula:** `What the page offers + Benefit to user + CTA`
- Length: 150-160 characters
- Primary keyword naturally included
- Clear call-to-action
- Urgency or curiosity

**CTR boosting elements to add:**

| Element | CTR impact |
|---------|-----------|
| Numbers | +20-30% |
| Current year | +15-20% |
| Power words | +10-15% |
| Question format | +10-15% |
| Brackets/parentheses | +10% |

**Verification:**
```bash
cd ~/Desktop/agent-universe
for page in index kassa missions governance seeds advisory vault economics helpwanted forums leaderboard treasury grand-opening moses kingdoms contact about bountyboard products services; do
  f="frontend/${page}.html"
  title=$(grep '<title>' "$f" | head -1 | sed 's/.*<title>//;s/<\/title>.*//')
  desc=$(grep 'name="description"' "$f" | head -1 | sed 's/.*content="//;s/".*//')
  echo "/${page} | ${#title} chars | ${#desc} chars | ${title}"
done
# Every title should be 50-60 chars, keyword-first
# Every description should be 150-160 chars, with CTA
```

---

### Step 0: Trim sitemap to 20 key URLs

The current sitemap-v2.xml has 51 URLs. Trim to the 20 priority pages above.

**What to do:**

1. Edit `frontend/sitemap.xml` — replace with the 20 URLs
2. Edit `frontend/sitemap-v2.xml` — same 20 URLs (this is the one registered in GSC)
3. Keep the other pages reachable via internal links (Step 5)

**Re-submit to GSC after deploy:**
```bash
cd ~/Desktop/SigRank
export GSC_SA_KEY=~/.config/sigrank/gsc-sa.json
export GSC_SITE="sc-domain:signomy.xyz"
node scripts/gsc/gsc.mjs sitemaps:submit https://signomy.xyz/sitemap-v2.xml
```

**Verification:**
```bash
curl -s https://signomy.xyz/sitemap-v2.xml | grep -c "<url>"  # should be 20
```

---

### Step 1: Add JSON-LD to the 20 priority pages

4 of 57 pages have JSON-LD. The other 16 of our 20 priority pages need it.
Focus only on the 20 priority pages — the other 37 pages get no JSON-LD work.

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
| 0.5 | Meta tag optimization for 20 pages | 30 min | — |
| 0 | Trim sitemap to 20 key URLs | 10 min | — |
| 1 | Add JSON-LD to 20 pages (16 need it) | 1 hour | — |
| 2 | Build llms-full.txt | 30 min | — |
| 3 | Add UTM to llms.txt | 10 min | — |
| 4 | Build IndexNow endpoint | 30 min | — |
| 5 | Add internal links between 20 pages | 30 min | — |
| 7 | Expand Organization sameAs | 10 min | — |
| — | Deploy to Railway | 5 min | Steps 0.5-5, 7 |
| 4e | Fire IndexNow push (20 URLs) | 1 min | Deploy done |
| 0b | Re-submit lean sitemap to GSC | 1 min | Deploy done |
| 8 | GEO content optimization for 20 pages | 2-3 hours | Deploy done, can iterate |
| 6 | GSC re-inspect | 10 min | Deploy done, wait 24-48h |

**Total:** ~5-6 hours of work + 24-48h wait for Bing/Google to crawl.

---

### Step 8: GEO content optimization for 20 pages

**Source:** NotFair geo-optimizer methodology (Princeton/GA Tech KDD 2024).

This is the actual "GEO/AEO" part — optimizing content so AI engines
(ChatGPT, Claude, Perplexity, Gemini, Google AI Overviews) cite signomy.xyz.

**The GEO Signal Stack (4 pillars, 0-100 score):**

| Pillar | Weight | Target |
|--------|--------|--------|
| Evidence Density | 35% | ≥5 numbers with units, ≥1 citation per 500 words from ≥3 source types, ≥2 expert quotes, ≥3 named entities |
| Structure & Position | 25% | Direct answer in first 150 words, TL;DR box, heading hierarchy, tables for comparisons, FAQ section, JSON-LD |
| Authority Signals | 25% | Author byline with sameAs links, last-updated within 60 days, methodology disclosed, first-party data |
| AI Crawlability | 15% | robots.txt allows AI bots (✅ already done), SSR content (✅ already done), llms.txt (✅ exists), canonical URLs (✅ done) |

**Key insight for signomy.xyz:** As a low-authority site, GEO is an advantage.
Princeton research showed rank-5 sites gained +115% visibility with evidence
signals while rank-1 sites lost 30%. AI engines don't apply PageRank — they
care whether your sentence is the most quotable one.

**Technique priority by PAWC lift:**

| Technique | Lift |
|-----------|------|
| Quotation addition (real quotes) | +41% |
| Statistics addition (real numbers) | +30% |
| Cite sources (real URLs) | +28% |
| Fluency optimization | +28% |

**Per-engine playbooks:**

| Engine | What it cites | Key move for signomy.xyz |
|--------|--------------|--------------------------|
| ChatGPT | Wikipedia ~48% of top citations | Build Wikipedia/Wikidata presence for CIVITAE |
| Perplexity | Recent web, primary sources | Keep pages updated, publish original first-party data |
| Gemini | Reddit/Quora, Google top-10 | Reddit presence, strong organic SEO |
| Claude | Primary sources, academic citations | Well-cited long-form articles, named author |
| Google AI Overviews | 85% overlap with organic top-10 | Win featured snippets, schema, 40-60 word answers |

**What to do for each of the 20 pages:**

1. Front-load the answer in the first 150 words (PAWC — sentence #1 is worth 5x sentence #20)
2. Add real stats with units (mission counts, fee percentages, seat counts, treasury splits)
3. Add FAQ sections with question-format H2/H3
4. Add author bylines with sameAs links to LinkedIn/ORCID
5. Add `dateModified` tags + `<time>` elements for freshness
6. Strip vague language ("experts say", "studies show") — replace with specific data
7. Add FAQPage JSON-LD schema (pairs with Step 1)

**Anti-patterns to remove:**
- Keyword stuffing (−8% PAWC)
- Generic AI-language intros ("In today's rapidly evolving landscape…")
- Vague entities ("a leading company", "experts say")
- Unsupported superlatives ("the best", "the most comprehensive")

**Verification:**
```bash
# Check first 150 words of each page for direct answer
for page in index kassa missions governance economics seeds; do
  echo "=== /${page} ==="
  curl -s https://signomy.xyz/${page} | sed 's/<[^>]*>//g' | tr -s ' \n' ' ' | cut -c1-300
  echo
done
# First 150 words should directly answer the target query, not have filler
```

---

## What NOT to do

- **Don't add JSON-LD to admin.html** — it's disallowed in robots.txt
- **Don't change the canonical URLs** — they're already correct
- **Don't change the OG tags** — they're already correct
- **Don't block any AI crawlers** — robots.txt already allows them all
- **Don't touch the backend logic** — this is frontend + routes only
- **Don't fabricate stats or quotes** — GEO hard-fail veto (Princeton research)

---

## Reference: The SigRank playbook

The full GEO/SEO/AEO playbook (with all 10 portable patterns) is at:
`~/Desktop/SigRank-GEO-SEO-AEO-PLAYBOOK.md`

Read it for the strategy, the patterns, and the verification commands. This plan
adapts those patterns for the agent-universe stack (FastAPI + vanilla HTML
instead of Next.js + React).
