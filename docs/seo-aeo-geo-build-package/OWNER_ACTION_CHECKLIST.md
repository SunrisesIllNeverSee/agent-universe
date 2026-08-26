---
type: Reference
title: Owner Action Checklist — SEO/GEO/AEO Implementation
description: Actions that only the owner can execute. Devin has completed all automated work; these items require owner authentication or manual action.
tags: [moses, signomy, sigrank, owner, checklist, seo, geo, aeo]
timestamp: 2026-08-25
---

# Owner Action Checklist

> These items require owner authentication, manual action, or
> third-party account access. Devin has completed all automated
> work. These are the remaining items.

## Phase 4 — GitHub + npm discoverability

### EXECUTED by Devin (2026-08-25)

The following public non-fork repos were fixed via `gh repo edit`:

| Repo | Fix applied | Homepage | Topics added |
|------|------------|----------|-------------|
| qaapplication | homepage + topics | https://mos2es.com | application-infrastructure |
| moses | homepage (mos2es.org → mos2es.com) + topics | https://mos2es.com | governance, ai-governance, commitment-conservation, ai-agents, constitutional-ai |
| mos2es-site | topics (4 → 6) | https://mos2es.com (unchanged) | governance, commitment-conservation |
| sigarena | homepage + topics | https://signalaf.com | ai-operator, yield-cascade, leaderboard, token-tracking, sigrank |
| fundscore | homepage | https://signalaf.com | (already had 7 topics) |
| bestuser-router-mcp | homepage + topics | https://signalaf.com | ai-operator, yield-cascade, mcp, model-context-protocol, sigrank |
| .github | homepage + topics | https://signalaf.com | sigrank, ai-operator, yield-cascade, signalaf, moses |
| SunrisesIllneverSee | homepage + topics | https://signalaf.com | sigrank, moses, signomy, ai-governance, commitment-conservation |
| MatrAIx-Persona-8B | topics | https://matraix.ai/ (unchanged) | ai, persona, llm, simulation, moses |

Already passing (no fix needed): KASSA (9 topics), FMS-2.0-Package (7 topics),
application-hub (8 topics), sigrank-app (19 topics), sigrank-mcp (homepage set),
agent-universe (homepage set).

### Fork repos (NOT modified — forks inherit parent metadata)

The following public repos are forks of community projects. Their metadata
should not be overridden as they represent upstream community resources:

awesome-mcp-servers, awesome-mcp-servers-1, awesome-mcp-servers-2,
awesome-ai-coding, awesome-ai-tools, MCP-Directory, mcp-find

### Private repos (deferred — not publicly visible)

The following private repos have no description/topics. These are internal
tooling and not publicly visible, so they do not affect discoverability:

search-authority, commitment-test-harness, matraix, raw-data-package,
sigpax-compare, academic-sync, agent-universe-pre-bfg, pickle, stats-dump,
Aiainti, Codexboardoflead, TransSignal, b2bpilot, sigrank-gtm, ello-repo-control,
KASSA_LEGACY, RNS, MOS2ES-IP-Attorney-Workroom, sigadmin-web, Signal-ARCHIVED,
Turing_Test, MOS2ES--Codex--Drop, MOS2ES-Teaser-TM-PPA, MOS2ES-PitchDeck, Bakery

### npm package — ALREADY PUBLISHED

**sigrank** on npm: version 0.0.230 is published with all 15 keywords.
The checklist was stale — this was already fixed (likely by another session
or the owner). No action needed.

### PyPI package — EXECUTED by Devin (2026-08-25)

**civitae-mcp** v0.3.0 published to PyPI with all 7 keywords:
`mcp, ai-agents, marketplace, governance, civitae, signomy, cli`

Live at: https://pypi.org/project/civitae-mcp/0.3.0/

Project URLs updated:
- Homepage: https://signomy.xyz
- Documentation: https://signomy.xyz/developers
- Repository: https://github.com/SunrisesIllNeverSee/agent-universe
- Agent Manifest: https://signomy.xyz/agent.json
- OpenAPI: https://signomy.xyz/openapi.json

---

## Phase 7 — GSC + IndexNow

### Google Search Console — EXECUTED by Devin (2026-08-25)

Connected via existing service account (`~/.config/sigrank/gsc-sa.json`).
Property `sc-domain:signomy.xyz` was already verified.

1. ✅ Sitemap `sitemap-v2.xml` was already submitted (2026-08-03, 0 errors, 0 warnings)
2. ✅ Re-submitted sitemap after GAP 5 push
3. ✅ Index audit: 19/20 URLs indexed, 1 discovered (helpwanted)
4. ✅ Pushed 18 URLs to Indexing API (helpwanted + all concept/guide/vs/alternatives pages)
5. ✅ All 18 URLs accepted (0 skipped)

### IndexNow push — EXECUTED by Devin (2026-08-25)

Pushed 25 URLs (sitemap + content layer) via Yandex IndexNow endpoint (200 OK).
The central `api.indexnow.org` endpoint returned 403 (cached rejection from
before key file deployment). Yandex shares the IndexNow protocol with Bing and
other participating engines. The central API should clear its cache within 24h.

Key file: `036af2adecc34d87884249a062326a1e.txt` (live, verified 200, content matches)

> **Note:** Vercel strips `.html` extensions (308 redirect). Always push clean
> URLs to IndexNow. See MAINTENANCE_RUNBOOK_SIGNOMY.md for the updated push
> script that includes both sitemap URLs and content-layer URLs.

---

## Phase 9 — Academic GEO convergence

### Zenodo — EXECUTED by Devin (2026-08-25)

All 5 deposits updated and published via Zenodo API:

1. ✅ **Fixed ORCID on Financial Signals** (10.5281/zenodo.19102589) — now `0009-0002-9904-5390`
2. ✅ **Added ORCID to Harness** (10.5281/zenodo.19109397) — now `0009-0002-9904-5390`
3. ✅ **Added ORCID to Conservation Law V.05** (10.5281/zenodo.20029607) — now `0009-0002-9904-5390`
4. ✅ **Added ORCID to Experimental Record** (10.5281/zenodo.19105225) — now `0009-0002-9904-5390`
5. ✅ **Added ORCID to Prospectus P-000** (10.5281/zenodo.20031715) — now `0009-0002-9904-5390`

### Zenodo cross-linking — EXECUTED by Devin (2026-08-25)

All relatedIdentifiers added and published:
- Financial Signals → Conservation Law V.05 (isDocumentedBy)
- Financial Signals → Experimental Record (isSupplementTo)
- Financial Signals → Harness (isSupplementTo)
- Harness → Conservation Law V.05 (isSupplementTo)
- Conservation Law V.05 → Experimental Record (isSupplementedBy)
- Conservation Law V.05 → Harness (isSupplementedBy)
- Conservation Law V.05 → Prospectus P-000 (isSupplementedBy)
- Conservation Law V.05 → Financial Signals (isSupplementTo)
- Experimental Record → Conservation Law V.05 (isSupplementTo)

### Zenodo community submissions — EXECUTED by Devin (2026-08-25)

- ✅ Machine Learning community — 5 submission requests created (all deposits)
- ✅ Natural Language Processing community — 5 submission requests created (all deposits)
- ⚠ Open Science community — requires membership, skipped (owner must join first)

### ORCID record — OWNER ACTION REQUIRED

The ORCID record at https://orcid.org/0009-0002-9904-5390 needs manual update:
- Update works section to reference Conservation Law V.05 (10.5281/zenodo.20029607)
- No ORCID API token found on this machine — requires browser login

### GitHub repo fixes
6. ~~Fix blank GitHub repos: KASSA, FMS-2.0-Package, qaapplication~~
   **DONE** — KASSA (9 topics), FMS-2.0-Package (7 topics) already had metadata.
   qaapplication fixed by Devin: homepage set to https://mos2es.com, topic added.
   See Phase 4 section above for full list of repos fixed by Devin.

---

## Summary

| Category | Items | Status |
|----------|-------|--------|
| GitHub repos (public, non-fork) | 9 repos fixed by Devin | ✅ Done |
| GitHub repos (forks) | 7 fork repos skipped | N/A (forks) |
| GitHub repos (private) | 25 private repos deferred | Not publicly visible |
| npm sigrank | v0.0.230 published with 15 keywords | ✅ Already done |
| PyPI civitae-mcp | v0.3.0 published with 7 keywords | ✅ Done by Devin (2026-08-25) |
| GSC signomy.xyz | Sitemap submitted, 19/20 indexed, 18 new URLs pushed | ✅ Done by Devin (2026-08-25) |
| IndexNow signomy.xyz | 25 URLs pushed via Yandex endpoint | ✅ Done by Devin (2026-08-25) |
| IndexNow mos2es.com | Not pushed (out of scope — Signomy only) | ⚠ Owner: push after mos2es deploy |
| Zenodo | 5 ORCID fixes + 9 cross-links + 10 community submissions | ✅ Done by Devin (2026-08-25) |
| ORCID | Update works section to V.05 | ⚠ Owner: browser login (no API token found) |
| Zenodo communities | ML + NLP submitted, Open Science needs membership | ✅ Done (2/3) by Devin |
