---
type: Checklist
title: Owner Checklist — Academic + Governance GEO Actions
description: Owner-only action items for surfaces Devin cannot ship directly. Covers ORCID updates, Zenodo deposit metadata, npm republish, and blank GitHub repos. Each item has step-by-step instructions and expected result.
tags: [checklist, owner-action, orcid, zenodo, npm, github, geo, phase-3]
timestamp: 2026-06-30T18:00:00Z
---

# Owner Checklist — Academic + Governance GEO Actions

> These are the items only the owner can execute — Devin doesn't have your
> ORCID login, Zenodo edit access, or npm publish credentials. The
> signalaf.com-side changes are documented separately in
> `~/Desktop/SigRank/Devins_Plans/growth/academic-geo-signalf-implementation.md`
> and will be shipped via sigrank-app.

## Prerequisite: Get your Zenodo token

Most items below can be automated via the `academic-sync` CLI, but it needs
a Zenodo personal access token:

1. Go to https://zenodo.org/account/settings/applications/
2. Scroll to **Personal access tokens** (not OAuth applications)
3. Click **New token**
4. Name it `academic-sync`
5. Scopes: check **deposit:write** and **deposit:actions**
6. Copy the token immediately (only shown once)
7. Set it in your shell:
   ```bash
   export ZENODO_TOKEN="paste-here"
   ```

Once the token is set, all items marked "(CLI)" can be run automatically.

---

## 1. ORCID — already up to date (DONE)

**Status:** ✅ Verified via `academic-sync audit`. ORCID `0009-0002-9904-5390`
has 7 works including Conservation Law V.05, all Zenodo deposits, and SSRN
P-000. No action needed.

---

## 2. Zenodo — fix wrong ORCID on Financial Signals (CRITICAL)

**Problem:** The Financial Signals deposit (`10.5281/zenodo.19102589`) has the
WRONG ORCID on the creator: `0009-0007-3367-9864` instead of
`0009-0002-9904-5390`. This is a different ORCID entirely.

**Steps:**
1. Log in to https://zenodo.org
2. Edit deposit `10.5281/zenodo.19102589`
3. In Creators section, fix ORCID to: `0009-0002-9904-5390`
4. Save

**Why it matters:** This deposit is attributed to a different person in
DataCite/Crossref indexing. AI engines following the ORCID won't find this
paper.

---

## 3. Zenodo — add ORCID to Harness deposit (HIGH)

**Problem:** The Harness deposit (`10.5281/zenodo.19109397`) is the only one
missing ORCID on the creator. The other 5 deposits all have correct ORCID.

**Steps:**
1. Log in to https://zenodo.org
2. Edit deposit `10.5281/zenodo.19109397`
3. In Creators section, add ORCID: `0009-0002-9904-5390`
4. Save

---

## 3b. Zenodo — resource types (DONE)

**Status:** ✅ Verified via Zenodo API + OpenAIRE. Experimental Record is now
"Dataset", Harness is "Software". OpenAIRE confirms both indexed with correct
types. Google Dataset Search will pick these up on next crawl.

---

## 3c. Zenodo — join communities (MEDIUM — do via web UI)

**Problem:** None of the 6 deposits are in any Zenodo communities. Communities
increase discoverability within Zenodo's own search and recommendation system.

**Note:** The Zenodo API has a metadata format migration issue that prevents
CLI-based community joining for old records. Use the Zenodo web UI instead.

**Communities to join (search by name in Zenodo UI):**

| Community | UUID | Relevance |
|-----------|------|-----------|
| Zenodo | `7647d230-c830-4664-a4c8-9afd95fc5003` | All deposits |
| OpenAIRE | `ba70ad9d-2576-43ee-a438-ad42b4249797` | All deposits (auto-indexing) |
| Natural Language Processing | `3eec7ae6-7230-439d-b9eb-58b23297fa67` | Conservation Law, Experimental Record, Harness |
| Machine Learning | `a08bc0ac-2893-4afd-870a-a77bd348c84c` | Conservation Law, Harness |
| Open Science | `8b1df34a-6496-448c-b109-7cff4f9572b1` | All deposits |

**Steps (per deposit):**
1. Go to https://zenodo.org/records/{deposit_id}
2. Click "Edit" → "Communities"
3. Search for each community name above
4. Add → Save

---

## 4. Zenodo — add related-identifier cross-links (HIGH — do via web UI)

**Problem:** Zero `relatedIdentifiers` on any deposit. The Conservation Law
doesn't link to the Experimental Record, the Harness, signalaf.com, or the
GitHub repo. The deposits are orphaned from each other and from the live
product.

**Note:** The Zenodo API has a metadata format migration issue that prevents
CLI-based cross-link addition for old records. Use the Zenodo web UI instead.

**Steps (per deposit):**
1. Go to https://zenodo.org/records/{deposit_id}
2. Click "Edit" → "Related identifiers"
3. Add each identifier below → Save

**The 10 cross-links to add:**

**Conservation Law (`20029607`) — add:**
- `10.5281/zenodo.19105225` → relation: `isDocumentedBy` (Experimental Record)
- `10.5281/zenodo.19109397` → relation: `isSupplementTo` (Harness)
- `10.5281/zenodo.20031715` → relation: `isReferencedBy` (P-000 Propositions)
- `https://github.com/SunrisesIllNeverSee/commitment-conservation` → relation: `isSupplementTo`
- `https://signalaf.com/science` → relation: `isReferencedBy` (live implementation)

**Experimental Record (`19105225`) — add:**
- `10.5281/zenodo.20029607` → relation: `documents` (Conservation Law)
- `10.5281/zenodo.19109397` → relation: `isSupplementTo` (Harness)

**Harness (`19109397`) — add:**
- `10.5281/zenodo.20029607` → relation: `isSupplementTo` (Conservation Law)
- `10.5281/zenodo.19105225` → relation: `isSupplementTo` (Experimental Record)

**P-000 Propositions (`20031715`) — add:**
- `10.5281/zenodo.20029607` → relation: `references` (Conservation Law)

**Expected result:** The deposits form a citation graph. An AI engine finding
the Conservation Law can trace to the Experimental Record, the Harness, and
signalaf.com.

---

## 5. npm — republish sigrank with keywords (HIGH)

**Problem:** `sigrank@0.13.0` on npm has `keywords: []` (empty). The
SEO_GEO_PLAN Phase 5 claimed 15 keywords were shipped, but they're not in the
published package.

**Steps:**
1. `cd ~/Desktop/SigRank-repos/sigrank-mcp`
2. Verify `package.json` has the keywords array (should have: `mcp`,
   `model-context-protocol`, `ai-agents`, `claude`, `anthropic`, `llm`,
   `token-telemetry`, `leaderboard`, `cli`, `tui`, `yield-cascade`,
   `sigrank`, `agent-tools`, `on-device`)
3. If keywords are missing from `package.json`, add them
4. Bump version: `npm version patch` (→ 0.13.1)
5. `npm publish` (from INSIDE the repo dir — a $HOME-cwd publish grabs the
   wrong package.json)
6. Verify: `npm view sigrank keywords` should list them

**Expected result:** `npm view sigrank keywords` returns the 14 keywords.
npm search and AI surfaces can discover the package.

---

## 6. GitHub — blank repos (MEDIUM)

Three repos are completely blank (no description, no homepage, no topics).
Devin can't set these without knowing what they are:

| Repo | Action needed |
|------|---------------|
| `KASSA` | Add description, homepage, topics. What is KASSA? |
| `FMS-2.0-Package` | Add description, homepage, topics. Related to the FMS-2.0 Zenodo deposit (`10.5281/zenodo.18841110`)? |
| `qaapplication` | Add description, homepage, topics. What is this? |
| `application-hub` | Has homepage (`application-hub-snowy.vercel.app`), needs description + topics. What is it? |

**Steps (for each):**
```
gh repo edit SunrisesIllNeverSee/<repo> --description "<desc>" --homepage "<url>" --add-topic <topic1> --add-topic <topic2> ...
```

---

## 7. GitHub — Commitment_Theory license (MEDIUM)

**Problem:** `Commitment_Theory` has no GitHub license set. The papers are
CC-BY-4.0, but GitHub shows "No license" (defaults to All Rights Reserved).

**Steps:**
- Option A: Add a `LICENSE` file with CC-BY-4.0 text to the repo
- Option B: If the "no license" is intentional (because it's a paper repo, not
  code), leave as-is but add a note in the README clarifying papers are CC-BY-4.0

---

## 8. PyPI — add homepage to sigrank-agent (LOW)

**Problem:** `sigrank-agent@0.1.1` on PyPI has no homepage URL.

**Steps:**
1. `cd ~/Desktop/SigRank-repos/sigrank-agent` (or wherever the agent repo is)
2. In `pyproject.toml` or `setup.py`, add `homepage = "https://signalaf.com"`
3. Bump version, republish: `python -m build && twine upload dist/*`

---

## Summary

| # | Action | Priority | Time est. |
|---|--------|----------|-----------|
| 1 | ORCID: already up to date | ✅ Done | 0 min |
| 2 | Zenodo: fix wrong ORCID on Financial Signals | 🔴 Critical (web UI) | 2 min |
| 3 | Zenodo: add ORCID to Harness deposit | 🟡 High (web UI) | 2 min |
| 3b | Zenodo: resource types for Dataset Search | ✅ Done | 0 min |
| 3c | Zenodo: join communities | 🟢 Medium (web UI) | 15 min |
| 4 | Zenodo: add related-identifier cross-links | 🟡 High (web UI) | 20 min |
| 5 | npm: republish sigrank with keywords | 🟡 High | 5 min |
| 6 | GitHub: fill in 4 blank repos | 🟢 Medium | 10 min |
| 7 | GitHub: Commitment_Theory license | 🟢 Medium | 5 min |
| 8 | PyPI: add homepage to sigrank-agent | 🟢 Low | 5 min |

**Total owner time: ~40 minutes** — items 2, 3, 3c, and 4 must be done via
the Zenodo web UI (the API has a metadata format migration issue that blocks
CLI-based edits on old records). The CLI still works for audits and new deposits.

**One-shot web UI session (do all 4 in one sitting):**

1. Go to https://zenodo.org and log in
2. For each of the 6 deposits, click Edit and:
   - **Fix ORCID** on 19102589 (wrong) and 19109397 (missing)
   - **Add related identifiers** (see the 10 cross-links in section 4)
   - **Join communities** (Zenodo, OpenAIRE, NLP, ML, Open Science)
3. Run `academic-sync audit` to verify

```bash
# After web UI edits, verify:
cd ~/Desktop/academic-sync && source .venv/bin/activate
academic-sync audit
```

## Tooling: academic-sync CLI + MCP server

A CLI and MCP server have been built to automate this audit going forward:
- **Repo:** https://github.com/SunrisesIllNeverSee/academic-sync
- **CLI:** `academic-sync audit` — full ecosystem audit (5 surfaces)
- **MCP:** exposes audit + fix + deposit operations as tools for AI agents

```bash
cd ~/Desktop/academic-sync
source .venv/bin/activate
academic-sync audit          # full audit (Zenodo + ORCID + Crossref + DataCite + OpenAIRE)
academic-sync status         # issues only
academic-sync audit --json   # machine-readable
```

For write operations, set `ZENODO_TOKEN` (see instructions at top of this file):
```bash
export ZENODO_TOKEN="your-token-from-zenodo-settings"
academic-sync add-related --deposit 20029607 --identifier 10.5281/zenodo.19105225 --relation isDocumentedBy
```

---

## Deposit Backlog — papers ready for DOI minting

These papers have drafts ready and can be deposited via `academic-sync deposit`:

| # | Paper | Status | Venue | CLI-ready? |
|---|-------|--------|-------|------------|
| 1 | **L-000 Legal Propositions** | CCT→CT fixed, ready | SSRN + Zenodo | ✅ YAML metadata at `deposits/L-000_legal-propositions.yaml` |
| 2 | CL-001 Failure Mode Taxonomy | Data complete, needs writing | CL / TACL / EMNLP | ❌ Needs draft first |
| 3 | IS-001 Preservation Principle | Can write from existing material | JASIST | ❌ Needs draft first |
| 4 | COM-001 Measuring Meaning | Can write from existing material | J. Communication | ❌ Needs draft first |

### Depositing L-000 (next up)

L-000 is unblocked — the CCT→CT naming fix has been applied. To deposit:

```bash
cd ~/Desktop/academic-sync && source .venv/bin/activate
export ZENODO_TOKEN="your-token"

# 1. Generate PDF from the markdown
# (manual — use pandoc or your preferred tool)
# pandoc ~/Desktop/Commitment_Theory/Legal_Theory/papers/L-000_legal-propositions/L-000-propositions-legal.md -o L-000.pdf

# 2. Preview the deposit
academic-sync deposit --metadata deposits/L-000_legal-propositions.yaml --dry-run

# 3. Create the deposit (with PDF)
academic-sync deposit --metadata deposits/L-000_legal-propositions.yaml --file L-000.pdf

# 4. Also upload to SSRN (manual — https://www.ssrn.com/)
# 5. Add the new Zenodo DOI to KNOWN_DEPOSITS in audit.py
# 6. Run audit to verify
academic-sync audit
```

The L-000 YAML already includes:
- ORCID on creator
- Cross-links to Conservation Law (20029607), P-000 (20031715), SSRN (6734283)
- Keywords for discoverability
- CC BY 4.0 license
- Zenodo community membership

---

## Website DOIs — give each site a persistent identifier (NEW)

**Problem:** The 3 websites (signalaf.com, mos2es.com, signomy.xyz) have no
DOIs. AI agents that follow DOI chains can't discover them from the academic
ecosystem. Creating Zenodo deposits with resource type "software" gives each
site a DOI that resolves to a landing page linking to the live site.

**Approach:** Create a Zenodo deposit for each website with:
- Resource type: `software`
- A README.md file describing the site
- Related identifiers linking to the live URL + GitHub repo
- ORCID on creator
- Cross-links to relevant academic deposits

**Metadata YAML files ready:**
- `academic-sync/deposits/signalaf-website.yaml`
- `academic-sync/deposits/mos2es-website.yaml`
- `academic-sync/deposits/signomy-website.yaml`

**To deposit (after ZENODO_TOKEN is set):**
```bash
cd ~/Desktop/academic-sync && source .venv/bin/activate
export ZENODO_TOKEN=$(cat ~/.zenodo_token)

# Create a README for each site
echo "# SignalAF\n\nLive at https://signalaf.com" > /tmp/signalaf-readme.md
echo "# MO§ES\n\nLive at https://mos2es.com" > /tmp/mos2es-readme.md
echo "# SigNomy\n\nLive at https://signomy.xyz" > /tmp/signomy-readme.md

# Deposit each (dry-run first, then for real)
academic-sync deposit --metadata deposits/signalaf-website.yaml --file /tmp/signalaf-readme.md --dry-run
academic-sync deposit --metadata deposits/signalaf-website.yaml --file /tmp/signalaf-readme.md

academic-sync deposit --metadata deposits/mos2es-website.yaml --file /tmp/mos2es-readme.md --dry-run
academic-sync deposit --metadata deposits/mos2es-website.yaml --file /tmp/mos2es-readme.md

academic-sync deposit --metadata deposits/signomy-website.yaml --file /tmp/signomy-readme.md --dry-run
academic-sync deposit --metadata deposits/signomy-website.yaml --file /tmp/signomy-readme.md
```

**Expected result:** 3 new DOIs, one per website. Each DOI resolves to a Zenodo
landing page that links to the live site. AI agents following the academic
citation graph can now reach the websites.

---

## NEXT SESSION — Indexing Diagnostic (after academic-sync items are cleared)

> **Handoff from LEAD.** Once the Zenodo/ORCID/cross-link items above are
> done, the next priority is **indexing** — getting Google to actually crawl
> and index interior pages across all 4 properties. This is a different
> workstream from academic metadata.

**Brief file:** `~/Desktop/SigRank/Devins_Plans/growth/INDEXING_DIAGNOSTIC_DEVIN_BRIEF.md`

Copy the contents of that brief (everything below the `---` line) into the
academic-geo Devin session as the next task. Summary of what it covers:

- **Live GSC findings** (pulled 2026-06-30) for all 4 properties:
  - `signalaf.com` — root indexed, `/methodology` + `/research/q1-2026` unknown to Google (discovery gap)
  - `mos2es.com` — healthiest, 226 impressions but concentrated on `poster.html`
  - `mos2es.xyz` — root crawled 7 weeks ago, 148 `/hub` URLs pushed but crawl-budget starved
  - `signomy.xyz` — mid, 51 URLs pushed, crawl ~2 wks old
- **Render is NOT the blocker** (verified via curl — all server-rendered)
- **Per-site fix punch-list** using `scripts/gsc/gsc.mjs` toolkit
- **Priority order:** discovery → sitemap coverage → canonicals → crawl budget → then content/CTR
- **Toolkit:** `~/Desktop/SigRank/scripts/gsc/gsc.mjs` (service-account auth, all 4 properties)

**Do this after** the academic-sync items (token, fix-orcid, fix-crosslinks,
join-communities, deposit L-000) are complete.
