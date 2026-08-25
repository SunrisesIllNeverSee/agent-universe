---
type: Runbook
title: Academic + Governance GEO/SEO/AEO Mapping — Execution Runbook
description: Idempotent, resumable, gate-then-ship runbook for the 7-step academic-geo workflow. A new Devin session (or the owner) follows this end-to-end. Each phase checks for its output artifact and skips if already done; the ship step hard-fails on any gate failure.
tags: [runbook, geo, seo, aeo, academic, sigrank, workflow, idempotent]
timestamp: 2026-06-30T15:00:00Z
---

# Academic + Governance GEO/SEO/AEO Mapping — Runbook

> **How to use this runbook.** A new Devin session (or the owner) starts at the
> top and works down. Each phase has an **idempotency check** at the top — if
> the phase's output artifact already exists and is non-empty, the phase is
> marked `[SKIP — already done]` and you move on. This makes the runbook safe
> to re-run after a crash, interruption, or partial completion.
>
> **Gates are hard.** Phase 3 ships to a live Vercel-deployed site. The two
> gates (`tsc 0`, canonical 11/11) MUST pass before any push to `sigrank-app`
> `main`. A gate failure stops the runbook — do not work around it.

---

## 0. Pre-flight (run every time)

These checks run on every invocation regardless of resume state.

### 0.1 Workspace

- [ ] CWD is `~/Desktop/academic-geo/` (this repo). If not, `cd` there.
- [ ] `git status` is clean (no uncommitted changes from a prior aborted run).
  - If dirty: `git stash` and note it — do NOT commit half-finished work.
- [ ] `git pull --ff-only origin main` succeeds (or repo is a fresh clone).

### 0.2 Source repos present

The 14 source files live across the Desktop. Verify each parent dir exists
before starting; a missing dir means the audit will have gaps.

- [ ] `~/Desktop/SigRank/` (RNS — brain + record)
- [ ] `~/Desktop/SigRank-repos/sigrank-app/` (deploy target)
- [ ] `~/Desktop/Commitment_Conservation/`
- [ ] `~/Desktop/Commitment_Theory/`
- [ ] `~/Desktop/ash_paper/`

### 0.3 Gate tooling available

- [ ] `node --version` (repo needs Node 22; machine may have 25 — `next dev`
      won't start, but `tsc` + tests work).
- [ ] `npx tsc --version` resolves.

> **If any pre-flight check fails:** stop and resolve before proceeding. Do
> not start Phase 1 with a broken workspace.

---

## 1. Read the prompt + methodology (always, even on resume)

These two files are in THIS repo. Read them first, every run — they define the
mission and the methodology you're adapting.

- [ ] **`SEO_GEO_PLAN.md`** — the master SEO/GEO methodology (adapt this for
      academic surfaces).
- [ ] **`PROMPT.md`** — the full mission, ecosystem map, and instructions.

> Reading these is not idempotent-skippable. Context is lost between sessions;
> re-reading is cheap and prevents drift.

---

## 2. Read the 14 source files across the Desktop

Read in the order below (matches `PROMPT.md` §STARTING POINT). These are the
primary sources the audit and strategy depend on.

| # | Path | What it gives you |
|---|------|-------------------|
| 1 | `~/Desktop/SigRank/CLAUDE.md` | Repo map + session protocol + gates |
| 2 | `~/Desktop/SigRank/Devins_Plans/growth/WS1_DEVIN_GOAL.md` | What's already done |
| 3 | `~/Desktop/SigRank/Devins_Plans/growth/sigrank-dataset-citation-plan.md` | The citation spec |
| 4 | `~/Desktop/Commitment_Conservation/CLAUDE.md` | The Conservation Law repo |
| 5 | `~/Desktop/Commitment_Conservation/README.md` | Public-facing, DOI badges + abstract |
| 6 | `~/Desktop/Commitment_Conservation/CITATION.cff` | Citation metadata |
| 7 | `~/Desktop/Commitment_Theory/academic-research/CLAUDE.md` | The 34-paper pipeline |
| 8 | `~/Desktop/Commitment_Theory/publishing/CLAUDE.md` | Identity/distribution/discovery |
| 9 | `~/Desktop/Commitment_Theory/publishing/DEPOSITS.md` | Zenodo DOIs |
| 10 | `~/Desktop/Commitment_Theory/publishing/PROFILES.md` | ORCID/Lens status |
| 11 | `~/Desktop/Commitment_Theory/publishing/PATENTS.md` | Patent filing log |
| 12 | `~/Desktop/ash_paper/CLAUDE.md` | The Schenck→Heppner paper |
| 13 | `~/Desktop/SigRank-repos/sigrank-app/lib/jsonld.ts` | The existing JSON-LD layer |
| 14 | `~/Desktop/SigRank-repos/sigrank-app/app/methodology/page.tsx` | The Dataset page |

- [ ] All 14 read. Note any that are missing or materially different from what
      `PROMPT.md` describes — those go into the inventory's "discrepancies"
      section.

> **Idempotency note:** reading is not skippable, but if you've already taken
> notes on a file in a prior phase's artifact, you can skim instead of
> re-reading in full.

---

## 3. Phase 1 — Audit + Map (output: `ECOSYSTEM_INVENTORY.md`)

### Idempotency check

- [ ] Does `ECOSYSTEM_INVENTORY.md` exist in this repo AND is it non-empty?
  - **Yes →** `[SKIP — Phase 1 already done]`. Jump to Phase 2.
  - **No →** proceed.

### Work

Per `PROMPT.md` §"Phase 1 — Audit + Map" (read-only, no changes to source repos):

1. **Inventory every public surface.** All 22 public GitHub repos (see the
   table in `PROMPT.md` §7), both live sites (signalaf.com, signomy.xyz,
   mos2es.com), Zenodo deposits, HuggingFace spaces, npm/PyPI packages. For
   each record: URL, what it is, license, current SEO state (README quality,
   topics, description, homepage URL, social preview), and whether it links to
   the others.

   **GitHub repo audit — run these for each of the 22 public repos:**
   ```
   gh repo view SunrisesIllNeverSee/<repo> --json description,homepageUrl,repositoryTopics
   gh api repos/SunrisesIllNeverSee/<repo>/readme   # check README presence
   ```
   For each repo, check and record:
   - [ ] README exists and is substantive (not empty/placeholder)
   - [ ] README links to signalaf.com (if relevant)
   - [ ] README links to the Conservation Law DOI (if relevant)
   - [ ] README links to signomy.xyz (if relevant)
   - [ ] GitHub topics are set (at least 5)
   - [ ] Homepage URL is configured
   - [ ] Description is accurate and keyword-rich
   - [ ] Social preview image exists

   **Zenodo deposit audit:**
   - [ ] Conservation Law paper (`10.5281/zenodo.20029607`) — ORCID present? (YES — confirmed)
   - [ ] Experimental Record (`10.5281/zenodo.19105225`) — ORCID present?
   - [ ] Do any Zenodo deposits have `related-identifier` links to signalaf.com? (likely no)
   - [ ] Are keywords aligned with sigrank-app Dataset keywords?

   **Live site audit:**
   - [ ] signalaf.com — Organization JSON-LD `sameAs` array (currently missing Zenodo, ORCID, signomy.xyz)
   - [ ] signomy.xyz — any JSON-LD? any cross-links to signalaf.com?
   - [ ] mos2es.com — any cross-links to signalaf.com, Zenodo, or the patent?

2. **Map the citation graph.** Which surfaces currently link to which? Cover
   the specific questions in `PROMPT.md` (Zenodo→signalaf? repos cross-link?
   ORCID referenced? signomy↔signalaf? papers↔signalaf? Conservation
   Law↔SigRank?). Identify:
   - [ ] Broken links
   - [ ] Missing cross-references (the gaps)
   - [ ] Missing `sameAs` properties
   - [ ] Missing ORCID connections on non-Conservation-Law deposits

3. **Identify the gaps.** Broken links, missing structured data, missing
   cross-references, missing `sameAs`, missing ORCID connections. (Folds into
   the citation graph above — record the gap list as inventory §3.)

4. **DOI discrepancy — already resolved (verify, don't re-investigate).** The
   Conservation Law paper DOI was listed as both `10.5281/zenodo.20029607` and
   `10.5281/zenodo.18792459` in different files. Prior session (c72761c)
   resolved it: **`10.5281/zenodo.20029607` is canonical** (latest version;
   supersedes 18792459, 18274930, 18271102, 18267279 via `isNewVersionOf`
   chain). Confirm this still holds (resolve the DOI) and record which files
   still carry a superseded DOI for the correction list.

### Output

- [ ] Write `ECOSYSTEM_INVENTORY.md` to this repo. Structure:
  - §1 Surface inventory (table: surface, URL, type, license, SEO state, cross-links)
  - §2 Citation graph (current state — who links to whom)
  - §3 Gaps (missing links, missing structured data, missing ORCID, etc.)
  - §4 DOI discrepancy reconciliation (canonical DOI + correction list)

### Gate

- [ ] `ECOSYSTEM_INVENTORY.md` exists, is non-empty, and covers all public
      surfaces listed in `PROMPT.md` §7.
- [ ] The DOI discrepancy is confirmed resolved (20029607 canonical) with a
      list of any files still carrying a superseded DOI.

> **Do not commit yet.** All three phase outputs commit together at the end
> (Phase 3, step 5) to keep the repo history clean. If you must checkpoint,
> commit with message `wip: phase 1 inventory` — but prefer to wait.

---

## 4. Phase 2 — Strategy Document (output: `ACADEMIC_GEO_STRATEGY.md`)

### Idempotency check

- [ ] Does `ACADEMIC_GEO_STRATEGY.md` exist in this repo AND is it non-empty?
  - **Yes →** `[SKIP — Phase 2 already done]`. Jump to Phase 3.
  - **No →** proceed.
- [ ] Does `ECOSYSTEM_INVENTORY.md` exist? If not, you cannot do Phase 2 — go
      back to Phase 1. (Phase 2 depends on Phase 1's gaps.)

### Work

Per `PROMPT.md` §"Phase 2 — Strategy Document", write
`ACADEMIC_GEO_STRATEGY.md` covering:

1. **The convergence thesis** — hub-and-spoke with signalaf.com + ORCID + Zenodo
   as hubs; Conservation Law = theoretical root, SigRank = live data product,
   MO§ES™ = enforcement engine, CIVITAE = governance runtime. All four
   cross-link.

2. **Per-surface action plan** — for each repo/site/deposit, specific changes
   that maximize GEO/AEO discoverability, adapting the master SEO/GEO plan
   methodology for each surface type (GitHub repos, Zenodo deposits,
   signalaf.com, signomy.xyz, mos2es.com, papers).

3. **New JSON-LD builders needed** on signalaf.com:
   - `organization()` with `sameAs: [GitHub org, Zenodo DOIs, ORCID, signomy.xyz, HuggingFace, mos2es.com]`
   - `CreativeWork`/`ScholarlyArticle` schema for the Conservation Law paper
   - `Patent` schema for MO§ES™ (63/877,177)
   - Dataset builder `citation` field → Conservation Law DOI

4. **The `/science` page** — academic foundation page on signalaf.com.

5. **ORCID wiring** — ORCID is **already set up** (`https://orcid.org/0009-0002-9904-5390`,
   confirmed on Zenodo per c72761c). The action is wiring, not setup: add it
   to signalaf.com Organization `sameAs`, verify it's on every Zenodo deposit,
   and link it from the CT publishing PROFILES.md.

6. **llms.txt expansion** — teach AI engines about the Conservation Law (DOI),
   CT research program, MO§ES™, the patent.

7. **Academic repo SEO** — per-repo checklist (topics, homepage URL, social
   preview, README cross-links) mirroring the sigrank-mcp treatment.

**Key facts (verified 2026-06-30, commit c72761c — bake these into the strategy,
do not re-investigate):**
- ORCID: `https://orcid.org/0009-0002-9904-5390` — SET UP, confirmed on Zenodo
- Conservation Law canonical DOI: `10.5281/zenodo.20029607` (latest version;
  supersedes 18792459, 18274930, 18271102, 18267279 via `isNewVersionOf` chain)
- Experimental Record DOI: `10.5281/zenodo.19105225`
- Patent: Serial No. 63/877,177 (Provisional, pending)
- License: CC-BY-4.0 (papers + dataset), MIT (code), All Rights Reserved (CIVITAE)

### Output

- [ ] Write `ACADEMIC_GEO_STRATEGY.md` to this repo.

### Gate

- [ ] Strategy covers all 7 items above.
- [ ] Every gap from `ECOSYSTEM_INVENTORY.md` §3 has a corresponding action in
      the strategy.

---

## 5. Phase 3 — Implementation + Owner Checklist

Phase 3 has two parallel outputs: (a) signalaf.com code changes shipped to
sigrank-app, and (b) `OWNER_CHECKLIST.md` for the non-sigrank surfaces.

### 5.1 Owner checklist (output: `OWNER_CHECKLIST.md`)

#### Idempotency check

- [ ] Does `OWNER_CHECKLIST.md` exist AND is it non-empty?
  - **Yes →** `[SKIP — checklist already done]`. Jump to 5.2.
  - **No →** proceed.

#### Work

Produce `OWNER_CHECKLIST.md` covering owner-action items for the surfaces you
cannot ship directly: GitHub repos (topics, homepage, social preview, README
cross-links), Zenodo deposits (ORCID, related-identifiers, keywords),
signomy.xyz, mos2es.com, ORCID wiring (verify on all deposits), PyPI keywords.
Each item: surface, specific action, step-by-step, expected result.

- [ ] `OWNER_CHECKLIST.md` written.

### 5.2 signalaf.com implementation (ship to sigrank-app)

#### Idempotency check

- [ ] Has the signalaf.com change already shipped? Check
      `~/Desktop/SigRank-repos/sigrank-app/` git log for a commit whose message
      references the academic-geo run (e.g. "academic-geo: organization sameAs
      + /science + Conservation Law schema").
  - **Yes →** `[SKIP — signalaf.com changes already shipped]`. Jump to 5.3.
  - **No →** proceed.

#### Work

Implement the signalaf.com-side changes per `PROMPT.md` §"Phase 3 —
Implementation":

1. Extend `organization()` in `lib/jsonld.ts` with `sameAs` array:
   - `https://orcid.org/0009-0002-9904-5390`
   - `https://github.com/SunrisesIllNeverSee` (org URL)
   - `https://zenodo.org/records/20029607` (Conservation Law)
   - `https://zenodo.org/records/19105225` (Experimental Record)
   - `https://signomy.xyz`
   - `https://mos2es.com`
   - `https://huggingface.co/spaces/SunrisesIllNeverSee/moses-sigrank` (if exists)
2. Add `ScholarlyArticle` or `CreativeWork` schema for the Conservation Law
   paper.
3. Add `Patent` schema for MO§ES™ (63/877,177).
4. Add `citation` field to the Dataset builder pointing to the Conservation Law
   DOI.
5. Add a `/science` page presenting the academic foundation. Create
   `app/science/page.tsx` with:
   - The Conservation Law (statement, DOI link, empirical record summary)
   - CT architecture (the 5-layer stack, plain English)
   - Patent reference (63/877,177, MO§ES™)
   - Links to Zenodo deposits
   - JSON-LD: ScholarlyArticle + Patent + Breadcrumb
6. Extend `llms.txt` (`app/llms.txt/route.ts`) with academic + governance
   context:
   - Conservation Law (DOI, statement)
   - CT research program (34-paper pipeline)
   - MO§ES™ governance framework (patent)
   - signomy.xyz
7. Add `/science` to `app/sitemap.ts` (priority 0.7, monthly) and add the
   Zenodo DOIs as `sameAs` references where relevant.
8. Any other JSON-LD builders the strategy identified.

> **Constraints (from `PROMPT.md` §CONSTRAINTS):**
> - Moat: RS.xx weights NEVER exposed. McHenry Axioms (Layer -1) proprietary.
> - Naming: "Commitment Theory" (CT), not "CCT". Never "McHenry's Law."
> - License clarity: SigRank code = MIT. Dataset + papers = CC-BY-4.0. CIVITAE = ARR.
> - NEVER push research/strategy to the public app repo — only the web code.

#### Gates (HARD — fail stops the runbook)

Run these from the RNS repo (`~/Desktop/SigRank/`), NOT sigrank-app:

- [ ] **Gate 1 — tsc 0:**
      `cd ~/Desktop/SigRank-repos/sigrank-app && npx tsc --noEmit`
      → 0 errors. On failure: STOP. Fix or revert. Do not push.
- [ ] **Gate 2 — canonical 11/11:**
      `cd ~/Desktop/SigRank && node --test sigrank-app/__tests__/ingest/canonical.test.mjs`
      → 11/11 pass, MO§ES Υ 18436.98. On failure: STOP. Fix or revert. Do not push.

> **If either gate fails:** do NOT push to `main`. Diagnose, fix, re-run both
> gates. Only proceed once both are green.

#### Ship

- [ ] From `~/Desktop/SigRank-repos/sigrank-app/`:
      `git add -A && git commit -m "academic-geo: organization sameAs + /science + Conservation Law schema + llms.txt expansion"`
- [ ] `git push origin main` → Vercel auto-builds → signalaf.com.
- [ ] Verify live: fetch `https://signalaf.com/science` (or the new page URL)
      and confirm the JSON-LD renders in page source.

### 5.3 Commit docs to this repo + report

- [ ] From `~/Desktop/academic-geo/`:
      `git add ECOSYSTEM_INVENTORY.md ACADEMIC_GEO_STRATEGY.md OWNER_CHECKLIST.md RUNBOOK.md`
      (plus any other docs produced).
- [ ] `git commit -m "academic-geo: phase 1 inventory + phase 2 strategy + phase 3 owner checklist"`
- [ ] `git push origin main`.
- [ ] Post status on the RNS bus (`~/Desktop/SigRank/Devins_Plans/SCRATCHPAD.md`):
      `### ⤷ ACADEMIC-GEO → LEAD: <status summary>`

---

## 6. Done — acceptance

All four deliverables from `PROMPT.md` §DELIVERABLES:

- [ ] `ACADEMIC_GEO_STRATEGY.md` — full strategy doc (this repo)
- [ ] `ECOSYSTEM_INVENTORY.md` — audit map (this repo)
- [ ] signalaf.com changes — committed + pushed + verified live
- [ ] `OWNER_CHECKLIST.md` — owner-action items for non-sigrank surfaces (this repo)

If all four are checked, the run is complete. Re-running the runbook from the
top should hit `[SKIP — already done]` at every phase.

---

## Resume quick-reference

If you're resuming an interrupted run, check which artifacts exist and jump to
the first missing one:

| Artifact exists? | Jump to |
|------------------|---------|
| `ECOSYSTEM_INVENTORY.md` missing | Phase 1 (§3) |
| `ACADEMIC_GEO_STRATEGY.md` missing | Phase 2 (§4) |
| `OWNER_CHECKLIST.md` missing | Phase 3 §5.1 |
| signalaf.com commit missing | Phase 3 §5.2 |
| Docs not committed to academic-geo | Phase 3 §5.3 |

Always run §0 (pre-flight) and §1–§2 (read prompt + 14 sources) regardless of
resume point — context is lost between sessions.

---

## Quick Reference

| What | Value |
|------|-------|
| ORCID | `https://orcid.org/0009-0002-9904-5390` (set up, on Zenodo) |
| Conservation Law DOI | `10.5281/zenodo.20029607` (canonical; supersedes 18792459/18274930/18271102/18267279) |
| Experimental Record DOI | `10.5281/zenodo.19105225` |
| Patent | Serial No. 63/877,177 (Provisional, pending) |
| SigRank live | `signalaf.com` |
| SIGNOMY live | `signomy.xyz` |
| MO§ES site | `mos2es.com` |
| GitHub org | `SunrisesIllNeverSee` |
| Ship web to | `~/Desktop/SigRank-repos/sigrank-app` (push main → Vercel) |
| Save docs to | this repo (`academic-geo`) |
| Gates | `tsc --noEmit` = 0 · `node --test .../canonical.test.mjs` = 11/11 (Υ 18436.98) |
| Moat | RS.xx weights NEVER exposed. McHenry Axioms (Layer -1) proprietary. |
| Naming | "Commitment Theory" (CT), not "CCT". Never "McHenry's Law." |
| License | CC-BY-4.0 (papers + dataset) · MIT (code) · All Rights Reserved (CIVITAE) |
