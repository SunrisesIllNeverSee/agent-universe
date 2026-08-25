---
type: Strategy
title: Academic + Governance GEO/SEO/AEO Convergence Strategy
description: Phase 2 strategy document. Defines the convergence thesis (every surface points back to the owner as canonical source), per-surface action plans, and the JSON-LD + llms.txt + /science page architecture for signalaf.com. Adapted from the master SEO_GEO_PLAN methodology for academic surfaces.
tags: [strategy, geo, seo, aeo, academic, governance, convergence, phase-2]
timestamp: 2026-06-30T18:30:00Z
---

# Academic + Governance GEO/SEO/AEO Convergence Strategy

> Phase 2 output. Built on the `ECOSYSTEM_INVENTORY.md` audit (45 gaps, 16
> resolved, 29 remaining). This document defines the convergence architecture
> and per-surface action plans. The signalaf.com-side implementation is
> documented in
> `~/Desktop/SigRank/Devins_Plans/growth/academic-geo-signalf-implementation.md`.
> Owner-only actions are in `OWNER_CHECKLIST.md`.

---

## 1. The Convergence Thesis

### The problem

The owner's ecosystem is fragmented across 22 public GitHub repos, 3 live
sites, 6 Zenodo deposits, npm, PyPI, and HuggingFace. Today these surfaces
barely cross-link. An AI engine that encounters the Conservation Law on Zenodo
has no path to SigRank. A search engine that finds a MO§ES™ repo on GitHub
can't trace it to the patent or the published law. The ORCID record has an
outdated paper version. The live product (signalaf.com) doesn't reference its
theoretical foundation at all.

### The thesis

**Every surface should point to the owner as the canonical source, and the
citation graph should be a hub-and-spoke with three hubs:**

```
                    ┌─────────────────┐
                    │   ORCID         │
                    │ 0009-0002-      │  ← identity hub
                    │ 9904-5390       │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │ signalaf.com│  │   Zenodo    │  │  GitHub org │
    │ (live data  │  │  (DOIs,     │  │  (code,     │
    │  product)   │  │   papers)   │  │   repos)    │
    │             │  │             │  │             │
    │ = product   │  │ = academic  │  │ = tooling   │
    │   hub       │  │   hub       │  │   hub       │
    └─────────────┘  └─────────────┘  └─────────────┘
```

**The four pillars and their roles:**

| Pillar | Role | Canonical surface | License |
|--------|------|-------------------|---------|
| Conservation Law | Theoretical root | Zenodo DOI `20029607` + `commitment-conservation` repo | CC-BY-4.0 |
| SigRank | Live data product | signalaf.com + `sigrank-app` repo | MIT (code) / CC-BY-4.0 (data) |
| MO§ES™ | Enforcement engine | mos2es.com + 7 governance repos | Patent pending 63/877,177 |
| CIVITAE | Governance runtime | signomy.xyz + `agent-universe` repo | All Rights Reserved |

**All four should cross-link.** An AI engine encountering any one should be
able to trace to all four + the owner's ORCID.

### The mechanism

The convergence is achieved through three layers of structured data:

1. **Identity layer (ORCID):** The owner's canonical author ID. Every Zenodo
   deposit should carry it. Every paper should reference it. signalaf.com
   Organization `sameAs` should include it.

2. **Distribution layer (Zenodo + GitHub):** Zenodo deposits carry DOIs and
   should cross-link via `relatedIdentifiers`. GitHub repos carry descriptions,
   topics, and homepage URLs that point to the canonical surfaces.

3. **Product layer (signalaf.com):** The live product carries JSON-LD
   (`Organization.sameAs`, `Dataset.citation`, `ScholarlyArticle`,
   `CreativeWork` for patent) + `llms.txt` + a `/science` page that teaches
   AI engines about the academic foundation.

### What "convergence" looks like when done

- ChatGPT asks "What is the Conservation Law of Commitment?" → finds the
  Zenodo DOI → sees `relatedIdentifiers` pointing to the Experimental Record
  + signalaf.com → traces to SigRank as the live implementation
- Perplexity asks "Who published the Conservation Law?" → finds ORCID
  `0009-0002-9904-5390` → sees all 7 works → traces to the patent via The Lens
- Google AI Overviews shows "SigRank" → reads signalaf.com Organization
  `sameAs` → sees Zenodo DOI + ORCID + GitHub org → recognizes SigRank as
  built on a published conservation law
- A researcher finds `commitment-conservation` on GitHub → sees homepage →
  resolves DOI → finds the paper → sees related-identifier to signalaf.com →
  discovers the live data product

---

## 2. Per-Surface Action Plan

### 2A. signalaf.com (ship via sigrank-app — plan in RNS)

**Status:** 🟡 Strong JSON-LD foundation but no academic/governance connections.

**Actions (documented in `academic-geo-signalf-implementation.md` in RNS):**

| # | Action | JSON-LD / file | Priority |
|---|--------|----------------|----------|
| 1 | Add `sameAs` to `organization()` | `lib/jsonld.ts` | 🔴 Critical |
| 2 | Add `citation` to `sigrankDataset()` | `lib/jsonld.ts` | 🔴 Critical |
| 3 | Add `conservationLawArticle()` builder | `lib/jsonld.ts` | 🟡 High |
| 4 | Add `mosesPatent()` builder | `lib/jsonld.ts` | 🟡 High |
| 5 | Create `/science` page | `app/science/page.tsx` | 🔴 Critical |
| 6 | Expand `llms.txt` with academic + governance context | `app/llms.txt/route.ts` | 🟡 High |
| 7 | Add `/science` to sitemap | `app/sitemap.ts` | 🟢 Medium |

**The `sameAs` array (verified values):**
```
https://orcid.org/0009-0002-9904-5390
https://github.com/SunrisesIllNeverSee
https://doi.org/10.5281/zenodo.20029607
https://doi.org/10.5281/zenodo.19105225
https://signomy.xyz
https://mos2es.com
```

**The `/science` page content:**
- Conservation Law statement: C(T(S)) ≈ C(S) with enforcement; C(T(S)) < C(S) without it
- DOI link to `10.5281/zenodo.20029607`
- Empirical record summary (EXP-001 through EXP-007, 13/20 signals at NLI=1.00 under gate)
- CT architecture (5-layer stack, plain English)
- Patent reference (63/877,177, MO§ES™)
- Links to all Zenodo deposits
- JSON-LD: ScholarlyArticle + CreativeWork (patent) + Breadcrumb

**Gates before ship:** `tsc 0` + `node --test .../canonical.test.mjs` = 11/11 (Υ 18436.98)

### 2B. Zenodo deposits (owner action — in OWNER_CHECKLIST.md)

**Status:** 🔴 6 deposits, zero ORCID in creators, zero related-identifiers.

| # | Action | Priority |
|---|--------|----------|
| 1 | Add ORCID `0009-0002-9904-5390` to creator field on all 6 deposits | 🔴 Critical |
| 2 | Add `relatedIdentifiers` cross-links (Conservation Law ↔ Experimental Record ↔ Harness; all → signalaf.com) | 🟡 High |

**The related-identifier graph to build:**
```
Conservation Law (20029607)
  ├─ isDocumentedBy → Experimental Record (19105225)
  ├─ isSupplementedBy → Harness (19109397)
  ├─ isReferencedBy → signalaf.com
  └─ isSupplementedBy → github.com/.../commitment-conservation

Experimental Record (19105225)
  ├─ documents → Conservation Law (20029607)
  └─ isSupplementedBy → Harness (19109397)

Harness (19109397)
  ├─ isSupplementTo → Conservation Law (20029607)
  └─ isSupplementTo → Experimental Record (19105225)

P-000 Propositions (20031715)
  └─ references → Conservation Law (20029607)
```

### 2C. ORCID (owner action — in OWNER_CHECKLIST.md)

**Status:** 🟡 Set up with 5 works, but has V.03 not V.05, and 2 deposits missing.

| # | Action | Priority |
|---|--------|----------|
| 1 | Update Conservation Law work: V.03 (`18274930`) → V.05 (`20029607`) | 🔴 Critical |
| 2 | Add Financial Signals (`19102589`) and FMS-2.0 (`18841110`) | 🟡 High |

### 2D. GitHub repos (✅ mostly done — 14 fixed in this audit)

**Status:** ✅ 14 of 18 repos fixed. 4 blank repos remain.

| Repo | What's done | What remains |
|------|-------------|--------------|
| `commitment-conservation` | ✅ desc + 11 topics + homepage → DOI | Add link to signalaf.com in README |
| `Commitment_Theory` | ✅ desc + 11 topics + homepage → DOI | Add LICENSE file (CC-BY-4.0) |
| 7 MO§ES repos | ✅ homepages + topics | — |
| 5 SigRank/research repos | ✅ homepages + topics | — |
| `KASSA` | ❌ blank | Owner: add desc + home + topics |
| `FMS-2.0-Package` | ❌ blank | Owner: add desc + home + topics |
| `qaapplication` | ❌ blank | Owner: add desc + home + topics |
| `application-hub` | 🟡 has home, no desc/topics | Owner: add desc + topics |

**README cross-link action for `commitment-conservation`:**
Add a line to the README linking to signalaf.com as the live implementation:
```
## Live Implementation
SigRank (signalaf.com) is the first live product built on Conservation Law
principles — on-device verification, signed snapshots, commitment preservation
under transformation.
```

### 2E. signomy.xyz + mos2es.com (owner action — future)

**Status:** 🔴 Neither site has JSON-LD.

| Site | Action | Priority |
|------|--------|----------|
| signomy.xyz | Add Organization JSON-LD with `sameAs` → signalaf.com, ORCID, GitHub org | 🟢 Medium (CIVITAE is ARR — lower GEO priority) |
| mos2es.com | Add Organization JSON-LD with `sameAs` → signalaf.com, Zenodo, patent, GitHub org | 🟢 Medium |

**Why medium priority:** These are governance surfaces, not academic citation
surfaces. The academic convergence (Conservation Law → SigRank → ORCID) is
higher leverage. But signomy.xyz and mos2es.com should eventually carry
structured data so AI engines can trace the governance ecosystem back to the
owner.

### 2F. npm + PyPI (owner action — in OWNER_CHECKLIST.md)

| Surface | Action | Priority |
|---------|--------|----------|
| npm `sigrank` | Republish with keywords (0.13.0 has `keywords: []`) | 🟡 High |
| PyPI `sigrank-agent` | Add homepage URL | 🟢 Low |

---

## 3. New JSON-LD Builders Needed on signalaf.com

### 3.1 `organization()` — add `sameAs`

```ts
export function organization() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    '@id': ORG_ID,
    name: SITE_NAME,
    url: SITE_ORIGIN,
    description: SITE_TAGLINE,
    logo: `${SITE_ORIGIN}/og.png`,
    sameAs: [
      'https://orcid.org/0009-0002-9904-5390',
      'https://github.com/SunrisesIllNeverSee',
      'https://doi.org/10.5281/zenodo.20029607',
      'https://doi.org/10.5281/zenodo.19105225',
      'https://signomy.xyz',
      'https://mos2es.com',
    ],
  }
}
```

### 3.2 `sigrankDataset()` — add `citation`

Add inside the existing `sigrankDataset()` return object:
```ts
citation: 'https://doi.org/10.5281/zenodo.20029607',
```

### 3.3 `conservationLawArticle()` — new builder

ScholarlyArticle for the Conservation Law paper. Linked from `/science` page.
Carries the DOI as `@id`, the author with ORCID `sameAs`, CC-BY-4.0 license,
V.05 version, and `isPartOf` pointing to the CT research program.

### 3.4 `mosesPatent()` — new builder

CreativeWork for the MO§ES™ patent. schema.org has no `Patent` type —
`CreativeWork` is the closest valid type. Carries the patent serial number in
the description, the author with ORCID, and `about: 'AI governance enforcement
architecture'`.

> **Constraint:** Do NOT use `@type: 'Patent'` — it won't validate in the
> Schema.org validator or Google Rich Results Test. `CreativeWork` is the
> correct type for patent-adjacent works.

---

## 4. The `/science` Page

### Purpose

`/science` is the academic foundation page on signalaf.com. It exists to make
SigRank credible as a data source: "this data is governed by a published
conservation law with an empirical record." Quarterly reports (`/research`)
are data outputs; `/science` is the theoretical root.

### Content

1. **The Conservation Law** — the law statement, the DOI link, the empirical
   record summary (7 experiments, 13/20 signals at NLI=1.00 under gate, 9
   failure modes documented)
2. **CT architecture** — the 5-layer stack in plain English:
   - Layer -1: McHenry Axioms (proprietary constitutional foundation)
   - Layer 0: Six-Gate Protocol
   - Layer 0.5: MO§ES™ Architecture (patent-pending enforcement engine)
   - Layer 1: Physical Laws — Conservation Law (published) + Second Law (candidate)
   - Layer 2: Measurement Science (Papers 1-5, planned)
   - Layer 3: Applications (Legal Theory, MISC)
   - Layer 4: Extensions (SIGSYSTEM, Post-Turing Test, Channel Capacity)
3. **Patent reference** — Serial No. 63/877,177, MO§ES™ enforcement architecture
4. **Links to Zenodo deposits** — Conservation Law, Experimental Record, Harness, P-000
5. **JSON-LD:** `conservationLawArticle()` + `mosesPatent()` + `breadcrumb()`

### What NOT to include

- RS.xx weights (proprietary — the moat)
- McHenry Axioms details (Layer -1 is proprietary)
- MO§ES™ implementation specifics (patent-pending, not open)
- Never call it "McHenry's Law"

---

## 5. ORCID Wiring

**Current state:** ORCID `0009-0002-9904-5390` is set up with 5 works, manually
added. Zenodo deposits don't carry ORCID in creator metadata.

**The wiring plan:**

1. **Owner: add ORCID to Zenodo deposit creators** (6 deposits) → enables
   Zenodo → DataCite → ORCID auto-push for future versions
2. **Owner: update ORCID Conservation Law work** V.03 → V.05
3. **Ship: add ORCID to signalaf.com Organization `sameAs`** → AI engines
   connect the live product to the author identity
4. **Ship: add ORCID to `conservationLawArticle()` builder** → the
   ScholarlyArticle schema carries the author's ORCID
5. **Owner: verify The Lens profile** connects to ORCID (for patent indexing)

**Why ORCID is the highest-leverage fix:** Without ORCID wired to Zenodo, every
new paper version requires manual ORCID maintenance. With it, the
identity→distribution→discovery chain is automatic. One hour of owner time
fixes the entire academic identity layer.

---

## 6. llms.txt Expansion

### Current state

`signalaf.com/llms.txt` covers only SigRank product pages (leaderboard, boards,
hall, compare, methodology, APIs, wiki concepts, tooling).

### What to add

```
## Academic foundation
- [The Conservation Law of Commitment](https://signalaf.com/science): the
  theoretical foundation. C(T(S)) ≈ C(S) with enforcement; C(T(S)) < C(S)
  without it.
- Conservation Law paper (Zenodo, CC-BY-4.0):
  https://doi.org/10.5281/zenodo.20029607
- Experimental Record (Zenodo): https://doi.org/10.5281/zenodo.19105225
- Commitment Theory (34-paper research program):
  https://github.com/SunrisesIllNeverSee/Commitment_Theory

## Governance
- MO§ES™ governance framework (patent pending 63/877,177):
  https://mos2es.com
- SIGNOMY governed agent marketplace: https://signomy.xyz
- GitHub org: https://github.com/SunrisesIllNeverSee
- ORCID: https://orcid.org/0009-0002-9904-5390
```

### Why

An AI engine reading `/llms.txt` should learn that SigRank is built on a
published conservation law, which has a Zenodo DOI, which connects to a
34-paper research program. Currently it learns none of this.

---

## 7. Academic Repo SEO (per-repo checklist)

The master SEO/GEO plan methodology (from `SEO_GEO_PLAN.md`) was built for
`sigrank-mcp`. The same treatment applies to the academic repos:

| Repo | Topics ✅ | Homepage ✅ | Description ✅ | README cross-links | Social preview |
|------|----------|------------|----------------|-------------------|----------------|
| `commitment-conservation` | ✅ 11 | ✅ → DOI | ✅ | Needs signalaf.com link | ❌ Missing |
| `Commitment_Theory` | ✅ 11 | ✅ → DOI | ✅ | Needs README | ❌ Missing |
| `MOS2ES` | ✅ 9 | ✅ | ✅ | — | ❌ Missing |
| `moses-governance` | ✅ 8 | ✅ | ✅ | — | ❌ Missing |
| `moses-claw-gov` | ✅ 7 | ✅ | ✅ | — | ❌ Missing |
| (other repos) | ✅ | ✅ | ✅ | — | ❌ Missing |

**Remaining per-repo actions (owner):**
- `commitment-conservation`: add "Live Implementation" section to README linking to signalaf.com
- `Commitment_Theory`: add a README (currently has none), add LICENSE file
- All academic repos: add social preview images (1200×630 PNG) — same convention as sigrank-app

---

## 8. Execution Priority

### Already done (this session)
- ✅ 14 GitHub repos: descriptions, topics, homepages fixed
- ✅ 5 CT repo files: superseded DOI corrected to V.05
- ✅ CITATION.cff: updated to V.05
- ✅ PROFILES.md: ORCID status updated
- ✅ DEPOSITS.md: 4 missing deposits added
- ✅ signalaf.com implementation plan saved to RNS

### Next: ship signalaf.com changes (Devin can do this)
1. Extend `organization()` with `sameAs`
2. Add `citation` to `sigrankDataset()`
3. Add `conservationLawArticle()` + `mosesPatent()` builders
4. Create `/science` page
5. Expand `llms.txt`
6. Add `/science` to sitemap
7. Run gates (tsc 0 + canonical 11/11)
8. Push main → Vercel → verify live

### Owner actions (in OWNER_CHECKLIST.md, ~70 min)
1. ORCID: update Conservation Law V.03 → V.05
2. ORCID: add 2 missing deposits
3. Zenodo: add ORCID to 6 deposit creators
4. Zenodo: add related-identifier cross-links
5. npm: republish sigrank with keywords
6. GitHub: fill 4 blank repos
7. GitHub: Commitment_Theory license
8. PyPI: add homepage to sigrank-agent

### Future (lower priority)
- signomy.xyz JSON-LD
- mos2es.com JSON-LD
- Social preview images for academic repos
- `commitment-conservation` README: add signalaf.com link
- `Commitment_Theory` README: write one

---

## Key Facts (verified 2026-06-30 — bake into all implementations)

| What | Value |
|------|-------|
| ORCID | `https://orcid.org/0009-0002-9904-5390` (set up, 5 works, manually added) |
| Conservation Law DOI (V.05, current) | `10.5281/zenodo.20029607` |
| Conservation Law concept DOI | `10.5281/zenodo.18267278` |
| Experimental Record DOI | `10.5281/zenodo.19105225` |
| Harness DOI | `10.5281/zenodo.19109397` |
| P-000 Propositions DOI | `10.5281/zenodo.20031715` |
| Financial Signals DOI | `10.5281/zenodo.19102589` |
| FMS-2.0 DOI | `10.5281/zenodo.18841110` |
| Patent | Serial No. 63/877,177 (Provisional, pending) |
| GitHub org | `https://github.com/SunrisesIllNeverSee` |
| SigRank live | `https://signalaf.com` |
| SIGNOMY live | `https://signomy.xyz` |
| MO§ES site | `https://mos2es.com` |
| License (papers + dataset) | CC-BY-4.0 |
| License (code) | MIT |
| License (CIVITAE) | All Rights Reserved |
| Gates | `tsc --noEmit` = 0 · canonical = 11/11 (Υ 18436.98) |
| Moat | RS.xx weights NEVER exposed. McHenry Axioms (Layer -1) proprietary. |
| Naming | "Commitment Theory" (CT), not "CCT". Never "McHenry's Law." |
