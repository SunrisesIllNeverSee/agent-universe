---
type: Plan + Execution
title: AEO Query Reconciliation — Plan & Execution
description: Complete plan and page-by-page execution for fixing the query association gap identified by the Aug 2026 7-engine audit. The content exists and is indexed; the problem is that existing pages don't use natural query language in their opening paragraphs, shared facts are inconsistent across pages, and entity names collide with common terms.
tags: [sigrank, aeo, seo, geo, reconciliation, plan, execution, signalaf, sigeconomy]
timestamp: 2026-08-17
last_touched: 2026-08-18 13:26 UTC
status: tiers-1-5-implemented-audit-rerun-pending
audit_basis: 7-engine, 46-prompt, 322-result audit (2026-08-16/17)
implementation:
  tier_1_complete: true
  tier_2_complete: true
  tier_3_complete: true
  tier_4_complete: true
  tier_5_complete: true
  audit_rerun_pending: true
  audit_rerun_blocked_by: "Codex usage limit — re-run when available"
commits:
  - "cc3b4287 (sigrank-app) — Tier 1: hero subtitle rewrites, 11 pages"
  - "3b9799b8 (sigrank-app) — Tier 2: class taxonomy + seed dataset clarity"
  - "a90821b3 (sigrank-app) — Tier 3: Signal Messenger / Wilcoxon / verification"
  - "487f850 (sigarena) — Tier 3: gig economy / human operator disambiguation"
  - "a7769c5d (sigrank-app) — Tier 4: footer + homepage category-language nav"
  - "3315fff6 (sigrank-app) — Tier 5: README category language"
  - "047facf (sigrank-mcp) — Tier 5: README + npm description category language"
external_updates:
  - "GitHub repo descriptions updated (sigrank-app, sigrank-mcp)"
  - "npm package.json description updated (reflects on next publish)"
  - "sigeconomy.com deployed to Cloudflare (live)"
  - "signalaf.com pushed to Vercel (auto-deploying)"
  - "IndexNow pinged for 19 updated URLs"
---

# AEO Query Reconciliation — Plan & Execution

## 1. Diagnosis

### What the audit proved

A 7-engine audit (Perplexity, Gemini, Grok, Claude, Google AI Overviews,
Bing Copilot, ChatGPT Search) ran 46 prompts per engine — 322 results
total. The finding is not that content is missing. The finding is that
existing content is not being selected as the answer.

| Prompt type | Retrieval rate |
|-------------|---------------:|
| Named/branded (e.g. "What is SigRank SignalAF?") | **94.4%** |
| Broad/unbranded (e.g. "What is Yield in AI usage?") | **11.1%** |

`signalaf.com` appeared in 32 of 46 Google result sets — the pages are
indexed. But they are associated with branded terminology, not with the
category language people use before they know the product name.

### Cross-engine scorecard

| Engine | Entity mentioned | Cited signalaf.com | Correct | Hallucinated |
|--------|----------------:|-------------------:|--------:|-------------:|
| ChatGPT Search | 65.2% | 39.1% | 58.7% | 2.2% |
| Grok | 56.5% | 52.2% | 54.3% | 10.9% |
| Google AI Overviews | 58.7% | 58.7% | 41.3% | 19.6% |
| Perplexity | 50.0% | 32.6% | 41.3% | 17.4% |
| Gemini | 60.9% | 26.1% | 28.3% | 39.1% |
| Bing Copilot | 65.2% | 39.1% | 28.3% | 45.7% |
| Claude | 30.4% | 26.1% | 19.6% | 10.9% |

### Root causes

1. **Opening paragraphs use proprietary vocabulary.** Pages open with
   "The headline SigRank metric..." instead of "Yield in AI usage
   measures...". Answer engines extract the first paragraph as the
   answer. If the first paragraph doesn't contain the query language,
   the page is not selected.

2. **Shared facts are inconsistent across pages.** Operator count
   appears as 707, 1,628, 1,642, 1,656, and ~1,700 depending on which
   page an engine scrapes. Class names vary — engines invent
   "Burner/Builder/10×er" tiers that don't exist in the taxonomy.

3. **Entity names collide with common terms.** "SigRank" collides with
   Wilcoxon signed-rank. "SignalAF" collides with Signal Messenger.
   "sigeconomy.com" collides with "gig economy." "MOSES" collides with
   biblical governance.

4. **Multiple pages define the same concept with different wording.**
   Yield is defined on `/metrics/yield-cascade`, `/methodology`,
   `/blog/volume-isnt-yield`, `/wiki/four-degrees`, and `/faq`. Engines
   combine incompatible fragments.

5. **sigeconomy.com is not associated with category language.** It works
   when queried by domain name but not for "AI user leaderboard" or
   "public LLM operator evals."

### What NOT to do

- **Do not create new pages.** More overlapping pages worsen
  fragmentation.
- **Do not add more definitions.** Multiple definitions cause engines
  to combine incompatible fragments.
- **Do not hardcode operator counts.** Use the live API.
- **Do not invent informal tier names.** "Burner/Builder/10×er" does not
  exist and engines are scraping it from somewhere.

---

## 2. Plan

### Principle

For each concept, designate:
- **One canonical definition URL**
- **One authoritative opening definition** (in natural query language)
- **One current formula or taxonomy**
- **One structured-data entity**
- **Supporting pages that link back using consistent anchor text**

Blog posts, calculators, and comparison pages should support the
canonical page — not compete with it.

### Implementation tiers

| Tier | What | Pages | Impact |
|------|------|------:|--------|
| 1 | Rewrite opening paragraphs to use natural query language | 11 | Fixes majority of failed broad prompts |
| 2 | Canonicalize shared facts (operator count, classes, DOI) | ~8 | Fixes hallucinations and conflicting numbers |
| 3 | Disambiguate entity collisions | 6 | Fixes entity resolution |
| 4 | Strengthen internal nav with category language | 2 | Helps engines understand page purpose |
| 5 | Align external descriptions (GitHub, npm, Zenodo) | 4+ | Cross-domain corroboration |

### Execution order

1. Tier 1 first (highest ROI — 11 pages, opening paragraph rewrites)
2. Tier 2 (canonicalize facts — fixes hallucinations)
3. Tier 3 (disambiguate collisions — fixes entity resolution)
4. Tier 4 (nav labels — quick, low-risk)
5. Tier 5 (external profiles — requires GitHub/npm/Zenodo edits)

### Verification

After implementation:
1. `npx tsc --noEmit` — 0 errors
2. `npm run test:canonical` — 11/11 pass
3. Push to `main` → Vercel auto-deploys
4. Verify live pages with `curl` (check for query language in HTML)
5. IndexNow ping updated URLs
6. Google Indexing API push updated URLs
7. GSC sitemap resubmit
8. Re-run the 46-prompt panel across all 7 engines
9. Log results in `audit-results/` with a new dated subfolder

---

## 3. Execution — Tier 1: Rewrite opening paragraphs

### Principle

Each page's hero subtitle and first visible `<section>` must answer the
unbranded query in natural language **before** introducing SigRank
branding. The pattern is:

> **Natural-language answer** (1-2 sentences using the query's exact
> words) → **SigRank term** (introduce the proprietary name) → **Formula
> / detail** (expand into the methodology)

### Page 1: `/metrics/yield-cascade` → "What is Yield in AI usage?"

**Current subtitle:**
> The headline SigRank metric. Measures whether your token cascade is
> compounding signal or burning tokens.

**New subtitle:**
> Yield in AI usage measures how efficiently you turn fresh input tokens
> into useful output, amplified by cached context reuse. The SigRank
> Yield formula (Υ) captures this in one number — whether your token
> cascade is compounding signal or burning tokens.

**Current first H2:** "The yield formula"
**New first H2:** "What is Yield in AI usage?" (keep "The yield formula" as H3 below it)

**File:** `app/metrics/yield-cascade/page.tsx`
**Change:** subtitle prop + add a natural-language `<section>` before the formula section

---

### Page 2: `/metrics/leverage` → "What is Leverage in AI token usage?"

**Current subtitle:**
> How much your cached context amplifies your fresh input. High leverage
> means you're building on a foundation, not starting over.

**New subtitle:**
> Leverage in AI token usage measures how much cached context you reuse
> relative to fresh input. High leverage means your cached context
> amplifies your input many times over — you're building on a foundation,
> not starting over.

**Current first H2:** "The leverage formula"
**New first H2:** "What is Leverage in AI token usage?"

**File:** `app/metrics/leverage/page.tsx`

---

### Page 3: `/metrics/velocity` → "What is Velocity in AI token usage?"

**Current subtitle:**
> How fast you produce output. A secondary metric — high velocity
> without yield is just fast waste.

**New subtitle:**
> Velocity in AI token usage measures how much output you generate
> relative to fresh input. It's the ratio of output tokens to input
> tokens — how much the model produces per unit of new context you
> provide. High velocity without yield is fast waste.

**Current first H2:** "The velocity formula"
**New first H2:** "What is Velocity in AI token usage?"

**File:** `app/metrics/velocity/page.tsx`

---

### Page 4: `/metrics/signal-to-noise-ratio` → "What is SNR in AI coding?"

**Current subtitle:**
> The share of fresh conversational traffic that is output versus input.
> A bounded view of Velocity.

**New subtitle:**
> SNR in AI coding measures the share of your fresh token traffic that
> is output versus input. A high signal-to-noise ratio means most of
> your fresh traffic is productive output; a low SNR means most is
> input. It's a bounded view of Velocity.

**Current first H2:** "The SNR formula"
**New first H2:** "What is SNR in AI coding?"

**File:** `app/metrics/signal-to-noise-ratio/page.tsx`

---

### Page 5: `/metrics/efficiency` → "What is 10xDEV?"

**Current subtitle:**
> Total operational amplification versus the AA 7:2:1 baseline. How much
> operating activity you generate per unit of fresh input.

**New subtitle:**
> 10xDEV is a logarithmic efficiency score that measures whether an
> operator's leverage exceeds 10x. It's the log₁₀ of Leverage — if your
> cached context amplifies your input by 10x or more, you're a 10xDEV
> operator. Total operational amplification versus the AA 7:2:1 baseline.

**Current first H2:** "The Efficiency formula"
**New first H2:** "What is 10xDEV?"

**File:** `app/metrics/efficiency/page.tsx`

---

### Page 6: `/token-cascade` → "What is token cascade efficiency?"

**Current subtitle:**
> Every AI coding session moves tokens through a cascade. Architecture —
> not volume — determines whether tokens compound or burn.

**New subtitle:**
> Token cascade efficiency measures how effectively tokens flow through
> an AI coding session. Every session moves tokens through four stages:
> input, output, cache-read, and cache-write. Architecture — not volume
> — determines whether tokens compound or burn.

**File:** `app/token-cascade/page.tsx`
**Note:** The phrase "token cascade efficiency" must appear in the first
sentence. The current opening uses "token cascade" but not "token
cascade efficiency."

---

### Page 7: `/hall` → "Who is the best AI user?" / "Who is the best AI coder?"

**Current HallHero:**
- eyebrow: "🏛️ Hall of Signal"
- title: "Triumphus Famae Et Gloriae"
- subtitle: "The permanent record — the highest marks ever set across the SigRank leaderboard."

**New HallHero:**
- eyebrow: "🏛️ Hall of Signal"
- title: "The Best AI Users — Hall of Signal"
- subtitle: "The best AI user is the operator with the highest Yield (Υ) score on the SigRank leaderboard. The permanent record of peak signal — the highest marks ever set across all-time, all metrics."

**File:** `components/hall/HallHero.tsx`
**Note:** The title "Triumphus Famae Et Gloriae" is Latin and invisible
to search engines as an answer. The H1 must contain "best AI user" or
"AI user leaderboard" in English.

---

### Page 8: `/ai-operator-scoring` → "What is the difference between model evals and operator evals?"

**Current subtitle:**
> Not the model. Not the clock. The operator. A performance layer that
> ranks who drives their AI best — built on real telemetry, not
> preference votes.

**New subtitle:**
> Model evaluation measures the AI model itself. Operator evaluation
> measures the human using the AI. SigRank is an operator evaluation
> system — it ranks who drives their AI best, built on real token
> telemetry, not preference votes.

**Current first H2:** (check — likely "What is AI operator scoring?")
**New first H2:** "Model evals vs operator evals"

**File:** `app/ai-operator-scoring/page.tsx`

---

### Page 9: `/score` → "How do I check my AI coding efficiency?"

**Current hero:**
- eyebrow: "◈ Score your cascade"
- h1: "How much signal does your token cascade actually compound?"
- subtitle: "Two paths. Both get you scored. Pick the one that fits."

**New hero:**
- eyebrow: "◈ Check your AI coding efficiency"
- h1: "How do I check my AI coding efficiency?"
- subtitle: "Run `bunx sigrank` to read your local logs and score your cascade automatically, or paste your four token counts below for an instant preview. Two paths — both get you scored."

**File:** `app/score/page.tsx`
**Note:** The `bunx sigrank` banner is already above the calculator.
The hero text still uses proprietary language. The H1 must match the
query.

---

### Page 10: `/ai-coding-metrics` → "What are the best AI coding metrics tools?"

**Current subtitle:**
> Six metrics, four token pillars, one cascade. The complete map of how
> SigRank measures AI coding efficiency — and which number to look at
> first.

**New subtitle:**
> AI coding metrics tools measure how efficiently you use AI to write
> code. SigRank defines six core metrics from four token pillars —
> yield, compression ratio, SNR, cache hit rate, leverage, and velocity.
> The complete map of AI coding efficiency — and which number to look at
> first.

**File:** `app/ai-coding-metrics/page.tsx`

---

### Page 11: `/ai-benchmarking` → "What are AI benchmarking tools for operators?"

**Current subtitle:**
> Model leaderboards rank the AI. Operator benchmarking ranks the human.
> A new category — built on real telemetry, not preference votes.

**New subtitle:**
> AI benchmarking tools for operators measure how effectively humans use
> AI — not the AI models themselves. Traditional AI benchmarking ranks
> models. SigRank introduces operator benchmarking: ranking the human
> driving the AI by token-cascade efficiency, built on real telemetry,
> not preference votes.

**File:** `app/ai-benchmarking/page.tsx`

---

## 4. Execution — Tier 2: Canonicalize shared facts

### Operator count

**Problem:** Engines return 707, 1,628, 1,642, 1,656, or ~1,700
depending on which page they scrape.

**Fix:** The operator count must come from ONE live source
(`/api/v1/stats`) and be rendered consistently on every page that
mentions it. No hardcoded counts in static content.

**Pages to check:**
- `/research` — uses `operatorCount` variable (already dynamic ✓)
- `/about` — check for hardcoded count
- `/methodology` — check for hardcoded count
- `/wiki` — check for hardcoded count
- `/faq` — check for hardcoded count
- Homepage `/` — check for hardcoded count

**Action:** `grep -rn "1,628\|1628\|1,642\|1642\|1,656\|1656\|1,700\|1700\|707" app/` and replace all hardcoded counts with a dynamic fetch or remove the count from pages where it's not essential.

### Operator classes

**Problem:** Engines invent "Burner/Builder/10×er" tiers. The permanent
taxonomy is IGNITER, SEEKER, BUILDER, TRANSMITTER, etc. (8 classes, 3
substages each).

**Fix:** Designate ONE canonical page for operator classes (likely
`/about` or `/methodology`). All other pages should link back using
consistent anchor text. Remove inline class definitions from blog posts
and comparison pages.

**Action:**
1. `grep -rn "Burner\|Builder\|10×er\|10xer" app/` — find and remove any informal tier language
2. Ensure `/about` has the complete, authoritative class taxonomy
3. Other pages should link to `/about#classes` or `/methodology#classes` instead of redefining

### Zenodo DOI

**Problem:** Gemini returned the wrong DOI. Copilot returned an
unrelated DOI. Claude failed to find any DOI.

**Fix:** The exact DOI `10.5281/zenodo.21900519` is already in
`/research` (line 28). Ensure it appears in plain text in the opening
paragraph, not just in structured data and BibTeX.

**File:** `app/research/page.tsx`
**Action:** Add the DOI to the subtitle or first visible paragraph.

### Dataset version

**Problem:** Dataset version and operator count are stated differently
across `/research`, `/methodology`, and `/wiki`.

**Fix:** `/research` is the canonical dataset page. Other pages should
link to it, not restate the numbers.

---

## 5. Execution — Tier 3: Disambiguate entity collisions

### `/about` → Signal Messenger collision

**Problem:** "What is SignalAF?" returns Signal Messenger on Perplexity
and Google.

**Fix:** Add explicit disambiguation to the `/about` hero:

**Current subtitle:**
> SigRank ranks the...

**New subtitle (add disambiguation prefix):**
> SignalAF is the web platform for SigRank, an AI operator evaluation
> leaderboard — not Signal Messenger. SigRank ranks the...

**File:** `app/about/page.tsx`

### `/privacy` → Wilcoxon signed-rank collision

**Problem:** "What data does SigRank collect?" fails because engines
conflate "SigRank" with "signrank" (Wilcoxon).

**Fix:** Strengthen the opening to answer the query directly.

**Current opening:**
> SigRank ("we", operated under MO§ES™ / Ello Cello LLC) is built
> privacy-first. This policy explains what we collect, what we never
> collect, and how your data is used.

**New opening:**
> SigRank collects four token counts: input, output, cache-read, and
> cache-write. No prompt content, no code, no conversation text. This
> policy explains what we collect, what we never collect, and how your
> data is used.

**File:** `app/privacy/page.tsx`

### `/methodology` → Wilcoxon signed-rank collision

**Problem:** "How does SigRank verify submissions?" fails because
engines conflate "SigRank" with "signrank."

**Fix:** Add an explicit H2: "How does SigRank verify submissions?"
with a direct answer in the first paragraph.

**File:** `app/methodology/page.tsx`
**Action:** Add `<h2>How does SigRank verify submissions?</h2>` with:
> SigRank verifies submissions using ed25519 cryptographic signatures,
> server-side rescoring, plausibility gates, and replay controls. Each
> device generates a keypair during enrollment; every snapshot is signed
> and the server verifies the signature before accepting.

### `/research` → Wrong DOI

**Problem:** Engines return the wrong DOI or fail to find any.

**Fix:** The DOI `10.5281/zenodo.21900519` is in the BibTeX and
structured data but not in the visible opening paragraph.

**File:** `app/research/page.tsx`
**Action:** Add to the subtitle or first visible paragraph:
> Available on Zenodo at DOI 10.5281/zenodo.21900519.

### `sigeconomy.com/` → Gig economy collision

**Problem:** Google misread the domain as "gig economy."

**Fix:** Add explicit disambiguation to the sigeconomy.com homepage.

**File:** `_03_sigarena/app/page.tsx`
**Action:** Add to the hero or opening:
> sigeconomy.com is the public AI operator leaderboard for SigRank
> SignalAF — not related to the gig economy.

### `sigeconomy.com/operator-evals` → Agent eval collision

**Problem:** "Public LLM operator evals" is interpreted as autonomous
agent benchmarks.

**Fix:** Rewrite opening to use "human operator" explicitly.

**File:** `_03_sigarena/app/operator-evals/page.tsx`
**Action:**
1. Open with: "Public LLM operator evals are public evaluations of human
   AI operators — the people who drive AI tools — not autonomous agents."
2. Add "performative evals" as a term: "Performative evals evaluate the
   AI user's behavior in real tasks, not just the model's output
   quality."

---

## 6. Execution — Tier 4: Strengthen internal category paths

### Homepage nav

The homepage and major navigation should link to canonical pages using
category language, not only product labels.

**Current nav labels → suggested additions:**
- "Leaderboard" → keep, but add "AI User Leaderboard" as a subtitle/aria
- "Field" → add "AI Power User Statistics" as a subtitle
- "Compare" → keep
- "Wiki" → keep
- "Blog" → keep

**Add category-language links to the homepage footer or content:**
- "AI Operator Evaluation" → `/ai-operator-scoring`
- "AI User Leaderboard" → `/board/all` or `/hall`
- "Benchmark Your AI Usage" → `/score`
- "AI Power User Statistics" → `/research`
- "Human vs Model Performance" → `/vs/lmsys-arena`
- "Privacy-Preserving AI Proficiency Measurement" → `/privacy`

**File:** `app/page.tsx` (homepage content sections)
**File:** `components/ui/Footer.tsx` (footer links)

### Internal anchor text

When pages link to canonical pages, the anchor text should use category
language:

- Links to `/metrics/yield-cascade` should use "Yield in AI usage" not
  just "Yield"
- Links to `/hall` should use "best AI user" or "AI user leaderboard"
  not just "Hall"
- Links to `/score` should use "check your AI coding efficiency" not
  just "Score"
- Links to `/ai-operator-scoring` should use "model evals vs operator
  evals" not just "Operator Scoring"

---

## 7. Execution — Tier 5: Align external descriptions

### GitHub README

**Repo:** `SunrisesIllNeverSee/sigrank-app`
**Action:** Ensure the README contains the same concise entity
definition as the homepage and links to the same canonical pages.

### npm package

**Package:** `sigrank`
**Action:** Ensure the npm description contains "AI operator evaluation"
and "token cascade efficiency" — the category language.

### Zenodo record

**DOI:** `10.5281/zenodo.21900519`
**Action:** Ensure the Zenodo metadata contains the same entity
definition and links to `signalaf.com/research`.

### MCP directories

**Action:** Ensure Glama.ai and other MCP directory listings contain
the same entity definition.

---

## 8. Verification checklist

After implementing all tiers:

- [ ] `npx tsc --noEmit` — 0 errors
- [ ] `npm run test:canonical` — 11/11 pass
- [ ] Push to `main` → Vercel auto-deploys
- [ ] Verify live pages with `curl` — check for query language in HTML
- [ ] IndexNow ping all updated URLs
- [ ] Google Indexing API push all updated URLs
- [ ] GSC sitemap resubmit
- [ ] Re-run the 46-prompt panel across all 7 engines
- [ ] Log results in `audit-results/` with a new dated subfolder
- [ ] Compare before/after retrieval rates for the 18 failed broad prompts

### Success criteria

The goal is to move the 18 failed broad prompts from **11.1% retrieval**
to **>50% retrieval** across engines, without creating any new pages.

---

## 9. File manifest

### Tier 1 — Opening paragraph rewrites (signalaf.com)

| File | Page | Target query |
|------|------|-------------|
| `app/metrics/yield-cascade/page.tsx` | `/metrics/yield-cascade` | "What is Yield in AI usage?" |
| `app/metrics/leverage/page.tsx` | `/metrics/leverage` | "What is Leverage in AI token usage?" |
| `app/metrics/velocity/page.tsx` | `/metrics/velocity` | "What is Velocity in AI token usage?" |
| `app/metrics/signal-to-noise-ratio/page.tsx` | `/metrics/signal-to-noise-ratio` | "What is SNR in AI coding?" |
| `app/metrics/efficiency/page.tsx` | `/metrics/efficiency` | "What is 10xDEV?" |
| `app/token-cascade/page.tsx` | `/token-cascade` | "What is token cascade efficiency?" |
| `components/hall/HallHero.tsx` | `/hall` | "Who is the best AI user?" |
| `app/ai-operator-scoring/page.tsx` | `/ai-operator-scoring` | "Model evals vs operator evals?" |
| `app/score/page.tsx` | `/score` | "How do I check my AI coding efficiency?" |
| `app/ai-coding-metrics/page.tsx` | `/ai-coding-metrics` | "What are the best AI coding metrics tools?" |
| `app/ai-benchmarking/page.tsx` | `/ai-benchmarking` | "What are AI benchmarking tools for operators?" |

### Tier 2 — Canonicalize shared facts (signalaf.com)

| File | Change |
|------|--------|
| All pages with hardcoded operator counts | Replace with dynamic fetch from `/api/v1/stats` |
| `app/about/page.tsx` | Ensure complete class taxonomy; remove informal tiers |
| `app/methodology/page.tsx` | Link to `/about#classes` instead of redefining |
| `app/research/page.tsx` | Add DOI to visible opening paragraph |
| Blog posts, wiki pages | Link to canonical pages instead of redefining |

### Tier 3 — Disambiguate collisions

| File | Change |
|------|--------|
| `app/about/page.tsx` | Add "not Signal Messenger" disambiguation |
| `app/privacy/page.tsx` | Rewrite opening to answer "What data does SigRank collect?" |
| `app/methodology/page.tsx` | Add "How does SigRank verify submissions?" H2 |
| `app/research/page.tsx` | Add DOI `10.5281/zenodo.21900519` to opening |
| `_03_sigarena/app/page.tsx` | Add "not gig economy" disambiguation |
| `_03_sigarena/app/operator-evals/page.tsx` | Add "human operator" language; add "performative evals" |

### Tier 4 — Internal nav

| File | Change |
|------|--------|
| `app/page.tsx` | Add category-language links to homepage |
| `components/ui/Footer.tsx` | Add category-language footer links |

### Tier 5 — External profiles

| Location | Change |
|----------|--------|
| `sigrank-app/README.md` | Align entity definition with homepage |
| npm `sigrank` package | Update description with category language |
| Zenodo record `10.5281/zenodo.21900519` | Align metadata with entity definition |
| Glama.ai MCP directory | Align listing with entity definition |

---

## 10. Audit data location

All audit results, raw evidence, and the prompt panel are stored in:

```
SigRank-gtm/launch/aeo-seo-geo/
├── README.md
├── prompt-panel/PERPLEXITY_PROMPTS.md
├── audit-results/          (7 engine logs)
├── audit-raw/              (6 raw evidence files)
└── reconciliation/RECONCILIATION_SHEET.md
```
