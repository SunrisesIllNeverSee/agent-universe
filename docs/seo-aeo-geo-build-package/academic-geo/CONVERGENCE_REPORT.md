---
type: Report
title: Academic GEO Convergence Report
description: Verification that every surface traces to every other surface + ORCID. The citation graph is a hub-and-spoke with ORCID as identity hub.
tags: [moses, signomy, sigrank, academic, geo, convergence, orcid]
timestamp: 2026-08-25
---

# Academic GEO Convergence Report

## Convergence graph

```
                    ORCID (0009-0002-9904-5390)
                   /     |        |          \
                  /      |        |           \
          mos2es.com  signalaf.com  signomy.xyz  GitHub
          (MO§ES)     (SigRank)    (Signomy)    (SunrisesIllneverSee)
              |           |            |           |
          Zenodo DOIs  Zenodo DOIs  Zenodo DOIs  repos
              |           |            |           |
          papers.html  research  llms.txt    README.md
```

## Verification results

### ORCID presence (identity hub)

| Surface | ORCID present | Status |
|---------|--------------|--------|
| mos2es.com Organization schema | ✅ 0009-0002-9904-5390 | Verified |
| signomy.xyz Organization schema | ✅ 0009-0002-9904-5390 | Verified |
| signalaf.com (reference) | ✅ 0009-0002-9904-5390 | Already done |
| GitHub profile | ✅ | Already set |

### Cross-linking (sameAs)

| Site | Links to mos2es.com | Links to signalaf.com | Links to signomy.xyz | Links to GitHub | Links to Zenodo |
|------|--------------------|-----------------------|---------------------|-----------------|-----------------|
| mos2es.com | — | ✅ | ✅ | ✅ | ✅ |
| signomy.xyz | ✅ | ✅ | — | ✅ | ✅ |
| signalaf.com | ✅ (ref) | — | ✅ (ref) | ✅ (ref) | ✅ (ref) |

### ScholarlyArticle schema

| Page | Schema type | DOI | ORCID | Status |
|------|------------|-----|-------|--------|
| mos2es.com/papers | ScholarlyArticle | 10.5281/zenodo.20029607 | ✅ | Verified |
| mos2es.com/financial-signals-paper | ScholarlyArticle | ✅ | ✅ | Verified |
| mos2es.com/concepts/conservation-law | DefinedTerm | — | ✅ (in text) | Verified |

### Zenodo DOI coverage

| DOI | Type | Referenced on | Status |
|-----|------|---------------|--------|
| 10.5281/zenodo.20029607 | Conservation Law V.05 | mos2es.com papers, concepts, llms.txt | ✅ |
| 10.5281/zenodo.19105225 | Experimental Record | mos2es.com papers, concepts | ✅ |
| 10.5281/zenodo.19109397 | Transformation Harness | mos2es.com papers, concepts | ✅ |
| 10.5281/zenodo.20031715 | Prospectus P-000 | mos2es.com papers | ✅ |

### GitHub repo → canonical surface

| Repo | Homepage | Status |
|------|----------|--------|
| mos2es-site | https://mos2es.com | ✅ |
| agent-universe | https://signomy.xyz | ✅ |
| sigrank-app | https://signalaf.com | ✅ |
| sigrank-mcp | https://signalaf.com | ✅ |

## Owner-only items (see OWNER_ACTION_CHECKLIST.md)

1. Fix wrong ORCID on Financial Signals Zenodo deposit (10.5281/zenodo.19102589)
2. Add ORCID to Harness Zenodo deposit (10.5281/zenodo.19109397)
3. Update ORCID record to Conservation Law V.05
4. Join Zenodo communities: NLP, Machine Learning, Open Science
5. Add relatedIdentifiers to Zenodo deposits (cross-link papers + datasets)
6. Fix blank GitHub repos

## Conclusion

The automated convergence is complete. All three sites cross-link via Organization sameAs.
ORCID is present in all site schemas. ScholarlyArticle schema with DOI is on paper pages.
Zenodo DOIs are referenced across content pages and llms.txt.

The remaining items are owner-only (Zenodo edits, ORCID updates, community joins)
and are documented in the OWNER_ACTION_CHECKLIST.md.
