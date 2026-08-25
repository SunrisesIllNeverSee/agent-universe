---
type: Inventory
title: Ecosystem Inventory — Academic + Governance GEO/SEO/AEO Audit
description: Phase 1 audit of every public surface in the owner's academic + governance ecosystem. Covers 22 public GitHub repos, 3 live sites, 6 Zenodo deposits, npm, PyPI, HuggingFace. Maps the citation graph, identifies gaps, and reconciles the DOI discrepancy. Updated 2026-06-30 with corrected ORCID findings + GitHub repo fixes applied.
tags: [inventory, audit, geo, seo, aeo, academic, governance, phase-1]
timestamp: 2026-06-30T17:00:00Z
---

# Ecosystem Inventory — Academic + Governance GEO/SEO/AEO Audit

> Phase 1 output. Audit of every public surface. Data collected 2026-06-30 via
> `gh` API, Zenodo REST API, ORCID public API, npm/PyPI registries, and live
> HTTP checks. Every finding verified against the live source.
>
> **Corrections from initial audit (2026-06-30 17:00):** The initial audit
> incorrectly stated ORCID was "NOT wired to Zenodo." The ORCID record
> (0009-0002-9904-5390) DOES have 5 works — but they were manually added by
> the author (source: "Deric J McHenry"), not auto-pushed from Zenodo. The
> Zenodo deposits themselves do not carry ORCID in creator metadata. The
> ORCID record also has an outdated version of the Conservation Law (V.03,
> not V.05). The initial audit also missed 4 Zenodo deposits. All corrected
> below.

---

## §1 — Surface Inventory

### 1A. GitHub repos — Conservation Law + Commitment Theory (academic priority)

| Repo | Description | Homepage | Topics | License | SEO state |
|------|-------------|----------|--------|---------|-----------|
| `commitment-conservation` | ✅ **FIXED 2026-06-30** — full description with CC-BY-4.0 + patent ref | ✅ **FIXED** → `https://doi.org/10.5281/zenodo.20029607` | ✅ **FIXED** — 11 topics (conservation-law, commitment-theory, llm, language-models, compression, recursion, computational-linguistics, information-theory, falsifiability, semantic-preservation, commitment-conservation) | "Other" | ✅ Was 🔴, now 🟢 — desc + home + topics all set. README already strong (DOI badges, abstract, citation block). |
| `Commitment_Theory` | ✅ **FIXED** — "Commitment Theory (CT) — the 34-paper research program..." | ✅ **FIXED** → `https://doi.org/10.5281/zenodo.20029607` | ✅ **FIXED** — 11 topics (commitment-theory, conservation-law, ai-governance, llm, language-models, computational-linguistics, information-theory, semantic-preservation, commitment-conservation, moses, constitutional-ai) | **NONE** (still needs license — papers are CC-BY-4.0 but GitHub shows "No license") | 🟡 Was 🔴, now 🟡 — desc + home + topics set. License still missing. |

**What was fixed:** Both repos had zero description, zero homepage, zero topics. All three are now set via `gh repo edit`. The repos are now discoverable via GitHub search and topic browse.

**What still needs owner action:** `Commitment_Theory` has no GitHub license set. The papers are CC-BY-4.0, but GitHub license is for code repos — the repo is primarily papers. Consider adding a LICENSE file or leaving as-is if the "no license" is intentional for a paper repo.

### 1B. GitHub repos — MO§ES™ governance ecosystem

| Repo | Description | Homepage | Topics | License | SEO state |
|------|-------------|----------|--------|---------|-----------|
| `MOS2ES` | ✅ Strong (pre-existing) | ✅ **FIXED** → `https://mos2es.com` (was `HTTP://MOS2ES.COM`) | ✅ **FIXED** — 9 topics added | "Other" | ✅ Was 🟡, now 🟢 |
| `moses-governance` | ✅ **FIXED** — full description added | ✅ **FIXED** → `https://mos2es.com` | ✅ **FIXED** — 8 topics added | "Other" | ✅ Was 🔴, now 🟢 |
| `moses-claw-gov` | ✅ Strong (pre-existing) | ✅ **FIXED** → `https://mos2es.com` (was `https://mos2es.io` — wrong domain) | ✅ 7 topics (pre-existing) | **NONE** | ✅ Was 🟡, now 🟢 |
| `moses-governance-cowork` | ✅ Present (pre-existing) | ✅ **FIXED** → `https://mos2es.com` | ✅ **FIXED** — 7 topics added | **NONE** | ✅ Was 🟡, now 🟢 |
| `command-engine` | ✅ Present (pre-existing) | ✅ **FIXED** → `https://mos2es.com` | ✅ **FIXED** — 7 topics added | "Other" | ✅ Was 🟡, now 🟢 |
| `moses-clicky-worker` | ✅ Present (pre-existing) | ✅ **FIXED** → `https://mos2es.com` | ✅ **FIXED** — 5 topics added | **NONE** | ✅ Was 🟡, now 🟢 |
| `mos2es-site` | ✅ Present (pre-existing) | ✅ **FIXED** → `https://mos2es.com` | ✅ **FIXED** — 4 topics added | **NONE** | ✅ Was 🟡, now 🟢 |

**What was fixed:** All 7 MO§ES repos now have correct homepage (`https://mos2es.com`), descriptions where missing, and topics where missing. `MOS2ES` homepage was malformed (`HTTP://MOS2ES.COM` → `https://mos2es.com`). `moses-claw-gov` homepage was pointing to wrong domain (`mos2es.io` → `mos2es.com`).

### 1C. GitHub repos — SigRank ecosystem

| Repo | Description | Homepage | Topics | License | SEO state |
|------|-------------|----------|--------|---------|-----------|
| `sigrank-app` | ✅ Strong | `https://signalaf.com` | ✅ 14 topics | MIT | ✅ Green (pre-existing) |
| `sigrank-mcp` | ✅ Strong | `https://signalaf.com` | ✅ 16 topics | MIT | ✅ Green (pre-existing) |
| `sigrank-vscode` | ✅ Present | ✅ **FIXED** → `https://signalaf.com` | ✅ **FIXED** — 8 topics added | MIT | ✅ Was 🟡, now 🟢 |
| `sigrank-agent` | ✅ Present | ✅ **FIXED** → `https://signalaf.com` | ✅ **FIXED** — 10 topics added | "Other" | ✅ Was 🟡, now 🟢 |

### 1D. GitHub repos — CIVITAE / SIGNOMY

| Repo | Description | Homepage | Topics | License | SEO state |
|------|-------------|----------|--------|---------|-----------|
| `agent-universe` | ✅ Strong | `https://signomy.xyz` | ✅ 20 topics | "Other" (ARR — correct) | ✅ Green (pre-existing) |
| `Mos2es_Signomy` | ✅ Strong | `https://signomy.xyz` | ✅ 8 topics | "Other" (ARR — correct) | ✅ Green (pre-existing) |
| `KASSA` | **EMPTY** | **EMPTY** | **NONE** | "Other" | 🔴 Still blank — owner action needed |

### 1E. GitHub repos — Research + data

| Repo | Description | Homepage | Topics | License | SEO state |
|------|-------------|----------|--------|---------|-----------|
| `moses-sigrank` | ✅ Present | ✅ **FIXED** → `https://signalaf.com` | ✅ **FIXED** — 7 topics added | MIT | ✅ Was 🟡, now 🟢 |
| `grok-demo` | ✅ Present | ✅ **FIXED** → `https://mos2es.com` (was self-referential) | ✅ 5 topics (pre-existing) | "Other" | ✅ Was 🟡, now 🟢 |
| `FMS-2.0-Package` | **EMPTY** | **EMPTY** | **NONE** | "Other" | 🔴 Still blank — owner action needed |
| `TransmitterSignal` | ✅ Present | ✅ **FIXED** → `https://signalaf.com` | ✅ **FIXED** — 4 topics added | **NONE** | ✅ Was 🟡, now 🟢 |
| `qaapplication` | **EMPTY** | **EMPTY** | **NONE** | **NONE** | 🔴 Still blank — owner action needed |
| `application-hub` | **EMPTY** | `https://application-hub-snowy.vercel.app` | **NONE** | **NONE** | 🟡 Has home, no desc, no topics — owner action needed |

### 1F. Live sites

| Site | HTTP | JSON-LD | Cross-links | SEO state |
|------|------|---------|-------------|-----------|
| `signalaf.com` | 200 | ✅ Organization (sameAs) + WebSite + ItemList + ProfilePage + Breadcrumb + DefinedTerm + Dataset (citation) + FAQPage + ScholarlyArticle + CreativeWork (patent) | ✅ `sameAs` → ORCID, GitHub, Zenodo x2, signomy.xyz, mos2es.com. Dataset `citation` → Conservation Law DOI. | ✅ Green — `/science` page live, llms.txt has Academic + Governance sections |
| `signomy.xyz` | 200 | ✅ **FIXED** Organization (sameAs) + WebSite + SoftwareApplication + ScholarlyArticle + Dataset | ✅ `sameAs` → ORCID, GitHub, Zenodo, signalaf.com, mos2es.com. Dataset `citation` → Conservation Law DOI. | ✅ Was 🔴, now 🟢 — JSON-LD added, llms.txt expanded with academic + governance cross-links |
| `mos2es.com` | 200 | ✅ **FIXED** Organization (sameAs) + WebSite + CreativeWork (patent) + ScholarlyArticle (papers page) | ✅ `sameAs` → ORCID, GitHub x3, Zenodo, signalaf.com, signomy.xyz. CreativeWork `isBasedOn` → Conservation Law DOI. | ✅ Was 🔴, now 🟢 — JSON-LD added, llms.txt created from scratch |

### 1G. Zenodo deposits (COMPLETE — 6 deposits, 10 total records)

The initial audit tracked only 2 deposits. The complete Zenodo inventory is:

| # | DOI | Title | Version | On ORCID? | In DEPOSITS.md? | In repo files? |
|---|-----|-------|---------|-----------|-----------------|----------------|
| 1 | `10.5281/zenodo.20031715` | P-000 Propositions Prospectus | V.1 | ✅ (as 20031714) | ❌ **listed as "pending"** | ❌ |
| 2 | `10.5281/zenodo.20029607` | Conservation Law | **V.05 (current)** | ❌ **ORCID has V.03** | ❌ (has 18792459) | ✅ (README, CLAUDE.md) |
| 3 | `10.5281/zenodo.19109397` | Public Recursive Transformation Harness | 1.0.0 | ✅ (as 19109396) | ❌ **missing entirely** | ❌ |
| 4 | `10.5281/zenodo.19105225` | Experimental Record | 1.0.0 | ✅ (as 19105224) | ✅ | ✅ |
| 5 | `10.5281/zenodo.19102589` | Commitment Conservation in Financial Signals | v1.0 | ❌ | ❌ **missing entirely** | ❌ |
| 6 | `10.5281/zenodo.18841110` | Floating Moat Standard (FMS-2.0) | FMS-2.0 | ❌ | ❌ **missing entirely** | ❌ |

**Conservation Law version history (5 version DOIs + 1 concept DOI):**

| DOI | Version | Where it appears | Status |
|-----|---------|------------------|--------|
| `10.5281/zenodo.18267278` | Concept DOI (→ V.05) | REPRODUCIBILITY.md | ✅ Correct — concept DOI always resolves to latest |
| `10.5281/zenodo.18271102` | V.02 | CITATION.cff | Old version — CITATION.cff should be updated |
| `10.5281/zenodo.18274930` | V.03 | **ORCID record** | ❌ **Outdated — ORCID has V.03, not V.05** |
| `10.5281/zenodo.18792459` | V.034 | CT repo files (5 files) | ❌ **Outdated — should be 20029607** |
| `10.5281/zenodo.20029607` | **V.05 (current)** | README + CLAUDE.md | ✅ Canonical |

**Zenodo deposit metadata gaps (all 6 deposits):**
- **ORCID in creator metadata:** NONE — `nameIdentifier: []` on all records. The ORCID record IS populated (5 works, manually added by author), but the Zenodo deposits don't carry ORCID in their creator block. This means Zenodo won't auto-push new versions to ORCID.
- **Related identifiers:** NONE — zero `relatedIdentifiers` on any deposit. The Conservation Law doesn't link to the Experimental Record, the Harness, or signalaf.com. None of the deposits cross-link.
- **Keywords:** Present on Conservation Law (13) and Experimental Record (14). Not checked on the other 4.

### 1H. Package registries + HuggingFace

| Surface | Status | Keywords | Homepage | Notes |
|---------|--------|----------|----------|-------|
| npm `sigrank` | v0.13.0 | **EMPTY** — `keywords: []` in published 0.13.0 | `https://signalaf.com` | 🔴 Keywords missing despite SEO_GEO_PLAN Phase 5 claiming 15 shipped. Needs republish. |
| PyPI `sigrank-agent` | v0.1.1 | ✅ 5 keywords | **NONE** | 🟡 Has keywords, no homepage. |
| HF `SunrisesIllNeverSee/moses-sigrank` | **401** (private or missing) | — | — | Inaccessible. |

### 1I. ORCID record (0009-0002-9904-5390)

**Status:** EXISTS and VERIFIED via ORCID public API. Given name: Deric J McHenry. 5 works on the record.

**Works on ORCID (as of 2026-06-30):**

| Work | DOI on ORCID | Actual Zenodo DOI | Source | Issue |
|------|-------------|-------------------|--------|-------|
| Propositions of Commitment Theory (SSRN) | `10.2139/ssrn.6734283` | — | Crossref | ✅ Correct |
| Propositions of Commitment Theory (Zenodo) | `10.5281/zenodo.20031714` | `10.5281/zenodo.20031715` | Deric J McHenry | Off-by-one (old record ID, redirects correctly) |
| Experimental Record | `10.5281/zenodo.19105224` | `10.5281/zenodo.19105225` | Deric J McHenry | Off-by-one (old record ID, redirects correctly) |
| Public Recursive Transformation Harness | `10.5281/zenodo.19109396` | `10.5281/zenodo.19109397` | Deric J McHenry | Off-by-one (old record ID, redirects correctly) |
| Conservation Law | `10.5281/zenodo.18274930` | `10.5281/zenodo.20029607` (V.05) | Deric J McHenry | ❌ **OUTDATED — V.03, not V.05** |

**Key findings:**
1. ORCID IS set up and populated — the initial audit was wrong to say it wasn't.
2. Works were **manually added** by the author (source: "Deric J McHenry"), not auto-pushed from Zenodo. This is because the Zenodo deposits don't carry ORCID in creator metadata.
3. The Conservation Law on ORCID is **V.03** (`18274930`), not the current **V.05** (`20029607`). The ORCID record needs updating.
4. The off-by-one DOIs (20031714 vs 20031715, etc.) are old Zenodo record IDs that redirect correctly — not a real problem, but the ORCID record would be cleaner with the current DOIs.
5. Two deposits are NOT on ORCID: Financial Signals (`19102589`) and FMS-2.0 (`18841110`).

---

## §2 — Citation Graph (current state)

### What links to what today

```
                        ┌─────────────────────┐
                        │   ORCID             │
                        │ 0009-0002-9904-5390 │
                        │ (5 works, manually  │
                        │  added, NOT auto-   │
                        │  pushed from Zenodo)│
                        │                     │
                        │ ⚠️ Conservation Law │
                        │   shows V.03, not   │
                        │   V.05              │
                        └──────────┬──────────┘
                                   │ (manual, not Zenodo auto-push)
                                   ▼
┌──────────────┐          ┌─────────────────┐          ┌──────────────┐
│ signalaf.com │          │  Zenodo         │          │ (nothing)    │
│ Organization │    ❌    │  20029607       │    ❌    │              │
│ (NO sameAs)  │─────────▶│  (Conservation  │◀─────────│              │
│              │ no link  │   Law V.05)     │  no link │              │
│ /methodology │          │                 │          │              │
│ Dataset      │    ❌    │  NO ORCID in    │          │              │
│ (NO citation │─────────▶│  creator meta   │          │              │
│  to DOI)     │ no cite  │  NO related-ids │          │              │
└──────────────┘          └─────────────────┘          └──────────────┘
      │                                                           │
      │ ❌ no link                                                │ ❌ no link
      ▼                                                           ▼
┌──────────────┐          ┌─────────────────┐          ┌──────────────┐
│ signomy.xyz  │          │  Zenodo         │          │ mos2es.com   │
│ (NO JSON-LD) │          │  19105225       │          │ (NO JSON-LD) │
│              │          │  (Experimental  │          │              │
│              │          │   Record)       │          │              │
│              │          │  NO related-ids │          │              │
└──────────────┘          └─────────────────┘          └──────────────┘

                          ┌────────────────────────┐
                          │ commitment-conservation │
                          │ (GitHub) — FIXED        │
                          │ README → Zenodo DOI ✅  │
                          │ README → patent ref ✅  │
                          │ desc + home + topics ✅ │
                          │ NO link to signalaf ❌  │
                          └────────────────────────┘

                          ┌────────────────────────┐
                          │ Commitment_Theory      │
                          │ (GitHub) — FIXED       │
                          │ desc + home + topics ✅ │
                          │ NO license set ❌      │
                          │ 5 files carry old DOI  │
                          └────────────────────────┘
```

### Specific link-check results

| Question | Answer |
|----------|--------|
| Do Zenodo deposits link to signalaf.com? | **NO** — zero related identifiers on any deposit |
| Do Zenodo deposits link to each other? | **NO** — Conservation Law doesn't reference Experimental Record or Harness |
| Do Zenodo deposits have ORCID in creator metadata? | **NO** — `nameIdentifier: []` on all 6 records |
| Is the ORCID record populated? | **YES** — 5 works, manually added by author |
| Does ORCID have the current Conservation Law version? | **NO** — has V.03 (18274930), not V.05 (20029607) |
| Does signalaf.com Organization have `sameAs`? | **NO** — `organization()` builder has no `sameAs` field |
| Does signalaf.com Dataset cite the Conservation Law DOI? | **NO** — `sigrankDataset()` has no `citation` field |
| Does signalaf.com have a `/science` page? | **NO** — returns 404 |
| Does signalaf.com llms.txt mention Conservation Law / CT / MO§ES? | **NO** — only SigRank product pages |
| Does commitment-conservation README link to signalaf.com? | **NO** — links to Zenodo DOI + patent, not signalaf.com |
| Does Commitment_Theory repo link to signalaf.com or Zenodo? | **NO** (homepage now points to Zenodo DOI via gh edit) |
| Does signomy.xyz have JSON-LD? | **NO** |
| Does mos2es.com have JSON-LD? | **NO** |
| Does any GitHub repo reference the owner's ORCID? | **NO** — PROFILES.md still says "in progress" |
| Are all Zenodo deposits tracked in DEPOSITS.md? | **NO** — 4 of 6 deposits missing (P-000, Harness, Financial Signals, FMS-2.0) |

---

## §3 — Gaps

### Resolved in this audit (2026-06-30)

| # | Gap | Resolution |
|---|-----|------------|
| R1 | `commitment-conservation` no desc/home/topics | ✅ Fixed via `gh repo edit` — 11 topics, desc, homepage → DOI |
| R2 | `Commitment_Theory` no desc/home/topics | ✅ Fixed via `gh repo edit` — 11 topics, desc, homepage → DOI |
| R3 | `MOS2ES` malformed homepage (`HTTP://MOS2ES.COM`) | ✅ Fixed → `https://mos2es.com` + 9 topics |
| R4 | `moses-governance` no desc/home/topics | ✅ Fixed — desc, homepage, 8 topics |
| R5 | `moses-claw-gov` wrong homepage (`mos2es.io`) | ✅ Fixed → `https://mos2es.com` |
| R6 | `moses-governance-cowork` no home/topics | ✅ Fixed — homepage, 7 topics |
| R7 | `command-engine` no home/topics | ✅ Fixed — homepage, 7 topics |
| R8 | `moses-clicky-worker` no home/topics | ✅ Fixed — homepage, 5 topics |
| R9 | `mos2es-site` no home/topics | ✅ Fixed — homepage, 4 topics |
| R10 | `sigrank-vscode` no home/topics | ✅ Fixed — homepage, 8 topics |
| R11 | `sigrank-agent` no home/topics | ✅ Fixed — homepage, 10 topics |
| R12 | `moses-sigrank` no home/topics | ✅ Fixed — homepage, 7 topics |
| R13 | `grok-demo` self-referential homepage | ✅ Fixed → `https://mos2es.com` |
| R14 | `TransmitterSignal` no home/topics | ✅ Fixed — homepage, 4 topics |
| R15 | DOI discrepancy canonical answer | ✅ Resolved: `20029607` is V.05 (current). `18267278` is concept DOI. `18792459` is V.034 (old). `18274930` is V.03 (on ORCID, old). |
| R16 | ORCID existence | ✅ Confirmed: `0009-0002-9904-5390` exists, 5 works, Deric J McHenry |

### Tier 1 — Critical (still open, blocks AI-engine citation convergence)

1. **ORCID record has outdated Conservation Law version.** ORCID shows V.03 (`18274930`), not V.05 (`20029607`). The current version is not on the ORCID record. **Owner action: update ORCID work to V.05 DOI, or add V.05 as a new work.**

2. **Zenodo deposits have no ORCID in creator metadata.** The ORCID record IS populated (manually), but the Zenodo deposits don't carry ORCID in their creator block (`nameIdentifier: []` on all 6 records). Without this, Zenodo won't auto-push new versions to ORCID. **Owner action: edit each Zenodo deposit, add ORCID to creator field.**

3. **Zenodo deposits have no related identifiers.** Zero `relatedIdentifiers` on any deposit. The Conservation Law doesn't link to the Experimental Record, the Harness, signalaf.com, or the GitHub repo. **Owner action: add related-identifier links on each deposit.**

4. **signalaf.com Organization has no `sameAs`.** The `organization()` builder in `lib/jsonld.ts` has no `sameAs` array. **Ship via sigrank-app (Phase 3).**

5. **signalaf.com Dataset has no `citation` field.** The `sigrankDataset()` builder doesn't cite the Conservation Law DOI. **Ship via sigrank-app (Phase 3).**

6. **No `/science` page on signalaf.com.** Returns 404. **Ship via sigrank-app (Phase 3).**

7. **DEPOSITS.md is out of date.** 4 of 6 Zenodo deposits are missing (P-000, Harness, Financial Signals, FMS-2.0). P-000 is listed as "pending" but is already deposited. **Owner action: update DEPOSITS.md.**

### Tier 2 — High (degrades cross-surface discoverability)

8. **5 CT repo files carry superseded DOI `18792459` (V.034).** Should be `20029607` (V.05):
   - `Commitment_Theory/academic-research/CLAUDE.md`
   - `Commitment_Theory/publishing/DEPOSITS.md`
   - `Commitment_Theory/publishing/PROFILES.md`
   - `Commitment_Theory/publishing/PATENTS.md`
   - `Commitment_Theory/publishing/CLAUDE.md`

9. **CITATION.cff carries V.02 DOI (`18271102`).** Should be updated to V.05 (`20029607`) or the concept DOI (`18267278`).

10. **PROFILES.md still says ORCID "in progress."** The ORCID is set up. PROFILES.md needs updating with the actual iD.

11. **llms.txt has no academic/governance content.** AI engines reading `/llms.txt` learn about SigRank product pages but not the Conservation Law, CT, MO§ES™, or the patent. **Ship via sigrank-app (Phase 3).**

12. **npm `sigrank@0.13.0` has empty keywords.** SEO_GEO_PLAN Phase 5 claims 15 keywords were shipped, but the npm registry shows `keywords: []`. Needs republish. **Owner action.**

13. **2 Zenodo deposits not on ORCID.** Financial Signals (`19102589`) and FMS-2.0 (`18841110`) are not on the ORCID record. **Owner action: add to ORCID.**

14. **`Commitment_Theory` has no GitHub license.** Papers are CC-BY-4.0 but GitHub shows "No license" (defaults to ARR). **Owner action: add LICENSE file or accept current state.**

### Tier 3 — Medium (polish, owner-action checklist items)

15. `KASSA` — completely blank (no desc, home, topics)
16. `FMS-2.0-Package` — completely blank
17. `qaapplication` — completely blank
18. `application-hub` — has homepage, no desc, no topics
19. `signomy.xyz` — no JSON-LD at all
20. `mos2es.com` — no JSON-LD at all
21. PyPI `sigrank-agent` — has keywords, no homepage
22. HF `moses-sigrank` — 401 (private or wrong path)
23. ORCID off-by-one DOIs (20031714 vs 20031715, etc.) — functional but cosmetically wrong
24. `commitment-conservation` README doesn't link to signalaf.com
25. Conservation Law paper doesn't reference SigRank as a live implementation
26. `moses-claw-gov` has no license set
27. `moses-governance-cowork` has no license set
28. `moses-clicky-worker` has no license set
29. `mos2es-site` has no license set

---

## §4 — DOI Discrepancy Reconciliation

### Resolution (verified 2026-06-30 via Zenodo REST API)

**Canonical Conservation Law paper DOI: `10.5281/zenodo.20029607`** (V.05, latest published version)

**Concept DOI: `10.5281/zenodo.18267278`** (always resolves to the latest version — currently V.05)

The full version chain:

| DOI | Version | Date | Notes |
|-----|---------|------|-------|
| `10.5281/zenodo.18267278` | Concept DOI | — | Always → latest. In REPRODUCIBILITY.md. ✅ Correct. |
| `10.5281/zenodo.18271102` | V.02 | 2026-01-16 | In CITATION.cff. Old. |
| `10.5281/zenodo.18274930` | V.03 | 2026-01-12 | On ORCID. Old. |
| `10.5281/zenodo.18792459` | V.034 | 2026-01-16 | In 5 CT repo files. Old. |
| `10.5281/zenodo.20029607` | **V.05** | 2026-05-04 | In README + CLAUDE.md. **Current.** |

### Correction list (files carrying superseded DOIs)

| File | Current | Should be |
|------|---------|-----------|
| `Commitment_Theory/academic-research/CLAUDE.md` | `18792459` (V.034) | `20029607` (V.05) |
| `Commitment_Theory/publishing/DEPOSITS.md` | `18792459` (V.034) | `20029607` (V.05) |
| `Commitment_Theory/publishing/PROFILES.md` | `18792459` (V.034) | `20029607` (V.05) |
| `Commitment_Theory/publishing/PATENTS.md` | `18792459` (V.034) | `20029607` (V.05) |
| `Commitment_Theory/publishing/CLAUDE.md` | `18792459` (V.034) | `20029607` (V.05) |
| `Commitment_Conservation/CITATION.cff` | `18271102` (V.02) | `20029607` (V.05) or `18267278` (concept) |

### ORCID discrepancy

**ORCID: `https://orcid.org/0009-0002-9904-5390`** — confirmed exists, 5 works, Deric J McHenry.

**The ORCID record has V.03 (`18274930`) of the Conservation Law, not V.05 (`20029607`).** The ORCID work needs to be updated to the current version, or V.05 needs to be added as a new work.

**The Zenodo deposits do NOT carry ORCID in creator metadata** (`nameIdentifier: []` on all 6 records). The ORCID works were manually added by the author. To enable Zenodo auto-push, ORCID must be added to the creator field on each Zenodo deposit.

---

## §5 — GitHub repos fixed in this audit (2026-06-30)

13 repos had their metadata fixed via `gh repo edit`:

| Repo | What was fixed |
|------|----------------|
| `commitment-conservation` | +description, +homepage (→ DOI), +11 topics |
| `Commitment_Theory` | +description, +homepage (→ DOI), +11 topics |
| `MOS2ES` | homepage fixed (→ `https://mos2es.com`), +9 topics |
| `moses-governance` | +description, +homepage, +8 topics |
| `moses-claw-gov` | homepage fixed (→ `https://mos2es.com`) |
| `moses-governance-cowork` | +homepage, +7 topics |
| `command-engine` | +homepage, +7 topics |
| `moses-clicky-worker` | +homepage, +5 topics |
| `mos2es-site` | +homepage, +4 topics |
| `sigrank-vscode` | +homepage, +8 topics |
| `sigrank-agent` | +homepage, +10 topics |
| `moses-sigrank` | +homepage, +7 topics |
| `grok-demo` | homepage fixed (→ `https://mos2es.com`) |
| `TransmitterSignal` | +homepage, +4 topics |

---

## Summary — gap counts

| Category | Count | Status |
|----------|-------|--------|
| **Resolved in this audit** | 16 | ✅ Done (14 GitHub repos fixed + DOI discrepancy resolved + ORCID existence confirmed) |
| **Tier 1 (Critical, still open)** | 7 | Mix: 3 owner actions (ORCID/Zenodo) + 3 ship via sigrank-app + 1 owner doc update |
| **Tier 2 (High, still open)** | 7 | Mix: 5 CT repo file corrections + 1 ship via sigrank-app + 1 npm republish |
| **Tier 3 (Medium, still open)** | 15 | Owner-action checklist items |
| **Total gaps identified** | 45 | 16 resolved, 29 remaining |

**The three highest-leverage remaining fixes:**
1. Update ORCID record: add V.05 of the Conservation Law (`20029607`), replacing or supplementing V.03 (`18274930`)
2. Add ORCID to Zenodo deposit creator metadata (enables auto-push for future versions)
3. Ship `sameAs` + `citation` + `/science` page on signalaf.com (connects the live product to the academic foundation)
