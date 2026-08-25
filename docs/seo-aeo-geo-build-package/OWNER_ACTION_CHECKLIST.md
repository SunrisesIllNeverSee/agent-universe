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

### Repos with blank descriptions (need description + homepage + topics)

| Repo | Description needed | Homepage | Suggested topics |
|------|-------------------|----------|-----------------|
| search-authority | Master canon for the owner's body of work | (internal) | canon, knowledge-graph, authority, semantic-web |
| commitment-test-harness | Test harness for commitment conservation experiments | https://mos2es.com | commitment-conservation, testing, ai-governance |
| matraix | MatrAIx persona model | https://mos2es.com | ai, persona, llm |
| raw-data-package | Raw data package for SigRank | https://signalaf.com | sigrank, data, dataset |
| sigpax-compare | SigRank comparison tool | https://signalaf.com | sigrank, comparison |
| academic-sync | Academic publication sync tool | (internal) | academic, sync, zenodo |
| agent-universe-pre-bfg | Pre-BFG archive of agent-universe | https://signomy.xyz | archive, signomy |
| pickle | (determine purpose) | (determine) | (determine) |
| stats-dump | Statistics dump repository | (internal) | stats, data |
| Aiainti | (determine purpose) | (determine) | (determine) |
| Codexboardoflead | (determine purpose) | (determine) | (determine) |
| TransSignal | (determine purpose) | (determine) | (determine) |
| awesome-mcp-servers-2 | MCP servers directory | https://signomy.xyz | mcp, model-context-protocol, servers |

### Repos with 0 topics (need ≥5 topics each)

b2bpilot, moses, sigarena, sigrank-gtm, ello-repo-control, bestuser-router-mcp,
KASSA_LEGACY, RNS, MOS2ES-IP-Attorney-Workroom, MatrAIx-Persona-8B,
awesome-mcp-servers, awesome-ai-tools, awesome-ai-coding, raw-data-package,
sigadmin-web, sigpax-compare, SunrisesIllneverSee, awesome-mcp-servers-2,
mcp-find, awesome-mcp-servers-1, MCP-Directory, .github, academic-sync,
signalaf, Signal-ARCHIVED, agent-universe-pre-bfg, pickle, Turing_Test,
MOS2ES--Codex--Drop, MOS2ES-Teaser-TM-PPA, MOS2ES-PitchDeck, Bakery,
stats-dump, Aiainti, Codexboardoflead, TransSignal

### Suggested topics for MO§ES repos
```
governance, ai-governance, commitment-conservation, ai-agents,
multi-agent, sha256, audit-trail, protocol, constitutional-ai,
semantic-preservation
```

### Commands to fix (run for each repo)
```bash
gh repo edit SunrisesIllneverSee/<repo> --description "..." --homepage "https://..."
gh repo edit SunrisesIllneverSee/<repo> --add-topic governance --add-topic ai-governance ...
```

### npm package keywords
- Verify `sigrank-mcp` package.json has keywords: `sigrank, mcp, ai-operator, yield-cascade, token-tracking, leaderboard, model-context-protocol, claude, anthropic`
- Verify `civitae-mcp` package.json has keywords: `civitae, signomy, mcp, agent-marketplace, governed-ai, moses, constitutional-ai`

### PyPI package metadata
- Verify `civitae-mcp` on PyPI has correct description, keywords, and homepage

---

## Phase 7 — GSC + IndexNow

### Google Search Console setup
1. Go to https://search.google.com/search-console
2. Add property for `mos2es.com` (if not already added)
3. Add property for `signomy.xyz` (if not already added)
4. Verify ownership (DNS TXT record or HTML file)
5. Submit `sitemap.xml` for each property
6. Request indexing on key pages (homepage, concept pages, FAQ)

### IndexNow push (mos2es.com)
The key file exists: `3cb9dad60ebc43248d4ec58b2d9b4aca.txt`
```bash
curl -X POST "https://api.indexnow.org/IndexNow" \
  -H "Content-Type: application/json" \
  -d '{"host":"mos2es.com","key":"3cb9dad60ebc43248d4ec58b2d9b4aca","keyLocation":"https://mos2es.com/3cb9dad60ebc43248d4ec58b2d9b4aca.txt","urlList":["https://mos2es.com/","https://mos2es.com/papers","https://mos2es.com/architecture","https://mos2es.com/benchmarks","https://mos2es.com/faq","https://mos2es.com/concepts/conservation-law","https://mos2es.com/concepts/lineage-claw","https://mos2es.com/concepts/origin-binding","https://mos2es.com/concepts/recursive-compression","https://mos2es.com/concepts/governance-enforcement","https://mos2es.com/concepts/commitment-conservation","https://mos2es.com/concepts/signal-encoding","https://mos2es.com/concepts/constitutional-substrate","https://mos2es.com/concepts/sovereign-signal-governance","https://mos2es.com/concepts/governance-vacuum"]}'
```

### IndexNow push (signomy.xyz)
Key file exists: `036af2adecc34d87884249a062326a1e.txt`
```bash
curl -X POST "https://api.indexnow.org/IndexNow" \
  -H "Content-Type: application/json" \
  -d '{"host":"signomy.xyz","key":"036af2adecc34d87884249a062326a1e","keyLocation":"https://signomy.xyz/036af2adecc34d87884249a062326a1e.txt","urlList":["https://signomy.xyz/","https://signomy.xyz/kassa","https://signomy.xyz/missions","https://signomy.xyz/governance","https://signomy.xyz/treasury","https://signomy.xyz/economics","https://signomy.xyz/moses","https://signomy.xyz/about","https://signomy.xyz/faq"]}'
```

> **Note:** IndexNow pushes are API calls with real-world side effects.
> Run these after deploying the updated sites.

---

## Phase 9 — Academic GEO convergence (owner-only)

### Zenodo fixes
1. **Fix wrong ORCID on Financial Signals deposit** (10.5281/zenodo.19102589)
   - Should be `0009-0002-9904-5390`, currently shows `0009-0007-3367-9864`
2. **Add ORCID to Harness deposit** (10.5281/zenodo.19109397)
   - No ORCID currently listed
3. **Update ORCID record** to Conservation Law V.05 (currently shows V.03)
   - Go to https://orcid.org/0009-0002-9904-5390
   - Update works section to reference V.05 (10.5281/zenodo.20029607)

### Zenodo community memberships
4. Join Zenodo communities: NLP, Machine Learning, Open Science

### Zenodo cross-linking (relatedIdentifiers)
5. Add relatedIdentifiers to Zenodo deposits to cross-link papers + datasets:
   - Conservation Law V.05 (10.5281/zenodo.20029607) → Experimental Record (10.5281/zenodo.19105225)
   - Conservation Law V.05 → Transformation Harness (10.5281/zenodo.19109397)
   - Conservation Law V.05 → Prospectus P-000 (10.5281/zenodo.20031715)
   - Experimental Record → Transformation Harness
   - Prospectus P-000 → Conservation Law V.05

### GitHub repo fixes
6. Fix blank GitHub repos: KASSA, FMS-2.0-Package, qaapplication
   (KASSA and FMS-2.0-Package already have descriptions — verify qaapplication)

---

## Summary

| Category | Items | Owner actions needed |
|----------|-------|---------------------|
| GitHub repos | 13 blank descriptions, 36 repos with 0 topics | `gh repo edit` commands |
| npm/PyPI | 2 packages | Verify keywords |
| GSC | 2 properties | Setup + sitemap submission |
| IndexNow | 2 sites | API push after deploy |
| Zenodo | 5 fixes | Manual edits on Zenodo |
| ORCID | 1 update | Manual edit on ORCID |
| Zenodo communities | 3 joins | Manual join requests |
