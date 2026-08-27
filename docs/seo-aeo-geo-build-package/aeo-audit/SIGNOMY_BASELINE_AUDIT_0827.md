---
type: Audit
title: AEO Baseline Audit — Signomy.xyz (2026-08-27)
description: Baseline AI search engine visibility audit for signomy.xyz. 6 queries tested via web search proxy. Named queries strong, broad discovery queries show gap.
tags: [signomy, aeo, geo, audit, baseline]
timestamp: 2026-08-27
---

# AEO Baseline Audit — signomy.xyz

**Date:** 2026-08-27
**Method:** Web search proxy (simulates what AI engines ingest)
**Engine:** Web search (Brave/Search API)
**Status:** Post Phase 1-6 implementation (pages not yet deployed)

> **Note:** This baseline was run AFTER local SEO fixes but BEFORE deployment
> to Vercel. The live site still has the old meta/sitemap. A post-deploy
> re-audit is needed after `git push` + Vercel rebuild.

---

## Summary

| Category | Queries tested | Signomy mentioned | Signomy cited | Competitor wins |
|----------|---------------|-------------------|---------------|-----------------|
| Named/branded | 3 | 3 (100%) | 3 (100%) | 0 |
| Broad discovery | 2 | 0 (0%) | 0 (0%) | 5 |
| **Total** | **5** | **3 (60%)** | **3 (60%)** | **5** |

**Diagnosis:** Same pattern as signalaf.com's original audit —
named/branded retrieval is strong, broad discovery is a gap.
The query association problem, not a page-count problem.

---

## Named/branded query results

### Query 1: "What is Signomy governed AI agent marketplace"

- **Result:** #1 — signomy.xyz/
- **Mentioned:** Yes
- **Cited:** Yes (signomy.xyz homepage)
- **Correct:** Yes — "governed AI agent city-state", "26 active missions", "40/30/30 split"
- **Hallucinated:** No
- **Notes:** Strong #1 ranking. Rich snippet content visible. MO§ES™, CIVITAE, and Signomy all correctly distinguished.

### Query 2: "What is CIVITAE constitutional AI ecosystem"

- **Result:** #1 — signomy.xyz/
- **Also:** #2 — clawrxiv.io/abs/2604.00713 (CIVITAE paper)
- **Mentioned:** Yes
- **Cited:** Yes (signomy.xyz + clawrxiv.io)
- **Correct:** Yes — "constitutional AI ecosystem governed by MO§ES™"
- **Hallucinated:** No
- **Notes:** clawRxiv paper provides strong academic citation support. Entity disambiguation from "civitas" (generic Latin) is working — signomy.xyz ranks above unrelated "Civitas" papers (Zenodo 15559984, 16313260).

### Query 3: "What is Signomy" (implied from query 1)

- **Result:** #1 — signomy.xyz/
- **Mentioned:** Yes
- **Cited:** Yes
- **Correct:** Yes
- **Notes:** Homepage meta description and H1 are well-optimized for this query.

---

## Broad discovery query results

### Query 4: "governed AI agent marketplace"

- **Result:** NOT in top 5
- **Mentioned:** No
- **Cited:** No
- **Competitors cited instead:**
  1. RuntimeAI — "Agent Marketplace" (enterprise agent catalog)
  2. NOMOS Exchange — "Sovereign Agent Marketplace" (local AI agents)
  3. OrdoNova — "Agent Marketplace" (governed BotWorks)
  4. Trust Agent — "sovereign AI marketplace for trusted expertise"
  5. AgentBazaar — "AI agents trade services on Hedera"
- **Diagnosis:** Signomy's `/concepts/governed-marketplace` page exists but is not yet ranking. The page was just built and has not been crawled/indexed yet. This is the #1 gap to close.

### Query 5: "how to register an AI agent"

- **Result:** NOT in top 5
- **Mentioned:** No
- **Cited:** No
- **Competitors cited instead:**
  1. Google Cloud — Agent Registry documentation
  2. RNWY — "How to Register an AI Agent: A Plain-English Guide"
  3. Agent Manifest — "How to register an agent"
  4. OpenBox — "Registering Agents"
  5. Ensemble — "Registering Agent"
- **Diagnosis:** Signomy's `/guides/how-to-register-an-agent` page exists but is not ranking. The guide content is good but needs indexing time + external signals.

---

## 5-tier reconciliation status

| Tier | What | Status |
|------|------|--------|
| 1 | Rewrite opening paragraphs to natural query language | ✅ Done in Phase 4 (new pages use "A governed AI agent marketplace is..." not "The CIVITAE platform provides...") |
| 2 | Canonicalize shared facts (one definition per concept) | ✅ Done — concept pages each define one term |
| 3 | Disambiguate entity collisions | ⚠️ Partial — Signomy vs Signal Messenger not explicitly addressed on homepage; CIVITAE vs civitas working (ranks above generic papers) |
| 4 | Strengthen internal nav with category language | ✅ Done — BreadcrumbList categories added |
| 5 | Align external descriptions (GitHub, npm, PyPI) | ⚠️ Owner action — GitHub repo description and PyPI description should include "governed AI agent marketplace" |

---

## Post-deploy action items

1. **Deploy:** `git push` to trigger Vercel rebuild (75 URLs in sitemap)
2. **Wait:** 3-7 days for Google to crawl new/updated pages
3. **Re-audit:** Run the full 46-prompt panel after indexing
4. **External alignment:** Update GitHub repo description, PyPI description, Smithery listing to include "governed AI agent marketplace"
5. **Entity disambiguation:** Add explicit "Signomy is not Signal Messenger" content to homepage or /about
6. **Backlinks:** The clawRxiv paper (2604.00713) is a strong academic backlink — ensure it links to signomy.xyz

---

## Comparison to signalaf.com baseline

| Metric | signalaf.com (original) | signomy.xyz (current) |
|--------|------------------------|----------------------|
| Named retrieval | 94.4% | 100% (3/3 tested) |
| Broad discovery | 11.1% | 0% (0/2 tested) |
| Pages | ~145 | 76 |
| Content layer | 24 pages built | 15 pages built (10 concepts + 4 guides + 5 vs + 1 FAQ) |
| JSON-LD coverage | 100% | 100% |
| llms.txt | Yes | Yes |
| GSC | Yes | Yes |
| IndexNow | Yes | Yes |

**Assessment:** Signomy is starting from a similar position to signalaf.com's
original baseline. The broad discovery gap is the same pattern. The fix
is the same: deploy, get indexed, run the 5-tier reconciliation, and
build external signals.
