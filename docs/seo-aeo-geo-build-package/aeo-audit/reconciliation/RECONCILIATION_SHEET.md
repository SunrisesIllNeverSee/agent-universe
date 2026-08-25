---
type: Working document
title: AEO Query-to-Page Reconciliation Sheet — SigRank SignalAF
description: Maps each failed broad/unbranded prompt from the Aug 2026 multi-engine audit to the existing URL that should answer it, identifies why it fails, and specifies the required change.
tags: [sigrank, aeo, seo, geo, reconciliation, audit, signalaf, sigeconomy]
timestamp: 2026-08-17
last_touched: 2026-08-17 13:23 UTC
audit_sources:
  - Perplexity (2026-08-16): 46 prompts, 50.0% entity mention, 41.3% correct
  - Gemini (2026-08-16): 46 prompts, 60.9% entity mention, 28.3% correct
  - Grok (2026-08-16): 46 prompts, 56.5% entity mention, 54.3% correct
  - Claude (2026-08-16): 46 prompts, 30.4% entity mention, 19.6% correct
  - Google AI Overviews (2026-08-16): 46 prompts, 58.7% entity mention, 41.3% correct
  - Bing Copilot (2026-08-16): 46 prompts, 65.2% entity mention, 28.3% correct
  - ChatGPT Search (2026-08-17): 46 prompts, 65.2% entity mention, 58.7% correct
---

# AEO Query-to-Page Reconciliation Sheet

> Maps each failed broad/unbranded prompt to the existing URL that should
> answer it, identifies why it fails, and specifies the required change.
>
> Source: 7-engine audit (Perplexity, Gemini, Grok, Claude, Google AI
> Overviews, Bing Copilot, ChatGPT Search) — 322 prompt results total.
> Audit results in `../audit-results/`, raw evidence in `../audit-raw/`.

## Diagnosis

The audit does **not** prove content is missing. It proves existing content
is not consistently being selected as the answer.

- Named/direct prompts averaged **94.4% retrieval** across engines.
- Broad discovery prompts averaged only **11.1%**.
- `signalaf.com` appeared in **32 of 46** Google result sets but was
  associated with branded queries, not category language.

This is a **query association, canonicalization, and authority problem** —
not a page-count problem. More overlapping pages would worsen fragmentation.

## Cross-engine aggregate (46 prompts × 7 engines = 322 results)

| Engine | Entity mentioned | Cited signalaf.com | Cited sigeconomy.com | Correct | Hallucinated |
|--------|----------------:|-------------------:|---------------------:|--------:|-------------:|
| ChatGPT Search | 65.2% | 39.1% | 13.0% | 58.7% | 2.2% |
| Grok | 56.5% | 52.2% | 2.2% | 54.3% | 10.9% |
| Google AI Overviews | 58.7% | 58.7% | 13.0% | 41.3% | 19.6% |
| Perplexity | 50.0% | 32.6% | 6.5% | 41.3% | 17.4% |
| Gemini | 60.9% | 26.1% | 6.5% | 28.3% | 39.1% |
| Bing Copilot | 65.2% | 39.1% | 4.3% | 28.3% | 45.7% |
| Claude | 30.4% | 26.1% | 2.2% | 19.6% | 10.9% |

## Failed broad prompts — reconciliation map

### Category 1: Unbranded metric discovery (prompts 6, 16, 17, 18, 19)

These prompts test whether the metric names resolve to SigRank without
branding context. They fail across all engines.

| # | Failed prompt | Intended URL | Indexed? | Current title/H1 | Opening answer present? | Competing URL? | Selected competing sources | Required change |
|---|---|---|---|---|---|---|---|---|
| 6 | "What is Yield in AI usage?" | `/metrics/yield-cascade` | Yes | "Yield Cascade — AI Token Efficiency Metric" | **No** — opens with "Yield (Υ) is the headline metric of the SigRank SignalAF leaderboard" (branded, not category language) | `/methodology`, `/blog/volume-isnt-yield`, `/wiki/four-degrees` | TigerGraph (inference yield), generic AI infrastructure yield | Rewrite opening paragraph to answer "What is Yield in AI usage?" in natural language first, then introduce the SigRank formula. Add "AI usage yield" and "token efficiency yield" as aliases. |
| 16 | "What is Leverage in AI token usage?" | `/metrics/leverage` | Yes | "Leverage — Cache Reuse Efficiency" | **No** — opens with SigRank-branded definition | None | Generic value-per-token definitions | Rewrite opening to answer "What is Leverage in AI token usage?" with "Leverage measures how much cached context you reuse relative to fresh input" before introducing the SigRank term. Add "AI context-reuse efficiency" as a natural-language alias. |
| 17 | "What is Velocity in AI token usage?" | `/metrics/velocity` | Yes | "Velocity — Output Per Input Token" | **No** — opens with SigRank-branded definition | None | Token throughput/burn-rate definitions | Rewrite opening to answer "What is Velocity in AI token usage?" with "Velocity measures how much output you generate relative to fresh input" before the SigRank term. Add "output relative to fresh input" as a natural-language alias. |
| 18 | "What is SNR in AI coding?" | `/metrics/signal-to-noise-ratio` | Yes | "Signal-to-Noise Ratio — Cascade Quality" | **No** — opens with SigRank-branded definition | None | Generic signal-to-noise metaphor | Rewrite opening to answer "What is SNR in AI coding?" with "Signal-to-noise ratio measures the quality of your token cascade" before the SigRank term. |
| 19 | "What is 10xDEV?" | `/metrics/efficiency` | Yes | "Efficiency — 10xDEV Score" | **No** — opens with SigRank-branded definition | None | Unrelated company named 10xDev, generic 10x-developer concept | Rewrite opening to answer "What is 10xDEV?" with "10xDEV is a logarithmic efficiency score that measures whether an operator's leverage exceeds 10x" before the SigRank branding. Add "AI developer efficiency score" as a natural-language alias. |

### Category 2: Unbranded concept discovery (prompts 7, 10, 11, 12)

These prompts test whether core concepts resolve to SigRank without
branding. They fail across all engines.

| # | Failed prompt | Intended URL | Indexed? | Current title/H1 | Opening answer present? | Competing URL? | Selected competing sources | Required change |
|---|---|---|---|---|---|---|---|---|
| 7 | "What is token cascade efficiency?" | `/token-cascade` | Yes (new) | "Token Cascade — The Flow of Tokens Through AI Coding Sessions" | **Partial** — opens with "A token cascade is the flow of tokens through an AI coding session" (good natural language) but does not use the phrase "token cascade efficiency" in the opening paragraph | `/cascade-analysis`, `/token-telemetry` | Transformer token pruning, multi-model cascades | Add "Token cascade efficiency measures how effectively those tokens flow" to the opening paragraph. Ensure the phrase "token cascade efficiency" appears in the first 100 words and in the H1 or subtitle. |
| 10 | "Who is the best AI user?" | `/hall` | Yes | "Hall of Fame — SigRank SignalAF" | **No** — opens with SigRank-branded hall of fame | `/board/all`, `/faq` | Generic advice about effective AI use | Rewrite opening to answer "Who is the best AI user?" with "The best AI user is the operator with the highest Yield score on the SigRank leaderboard" — this is already in the FAQ JSON-LD but not on `/hall` itself. Add "AI user leaderboard" and "best AI user" to the page title/H1. |
| 11 | "Who is the best AI coder?" | `/hall` | Yes | Same as above | **No** — same issue | Same | Coding model rankings (Claude Code, Cursor, Codex) | Add "AI coder" as an alias for "AI user" on `/hall`. The page should answer "Who is the best AI coder?" with "The best AI coder is the operator with the highest Yield — see the hall of fame." Add "best AI coder" to metadata keywords. |
| 12 | "What is the difference between model evals and operator evals?" | `/ai-operator-scoring` | Yes | "AI Operator Scoring — SigRank SignalAF" | **No** — opens with SigRank-branded scoring | `/vs/lmsys-arena`, `/methodology` | Agent/system evals (AgentBench, WebArena, SWE-bench) | Rewrite opening to answer "What is the difference between model evals and operator evals?" with "Model evaluation measures the AI model itself. Operator evaluation measures the human using the AI." Add "model evals vs operator evals" to the page. |

### Category 3: Unbranded tool/category discovery (prompts 28, 33, 34, 35)

These prompts test whether SigRank surfaces for generic tool/category
searches. They fail across all engines.

| # | Failed prompt | Intended URL | Indexed? | Current title/H1 | Opening answer present? | Competing URL? | Selected competing sources | Required change |
|---|---|---|---|---|---|---|---|---|
| 28 | "How do I check my AI coding efficiency?" | `/score` | Yes | "Score your cascade" | **No** — opens with "How much signal does your token cascade actually compound?" (proprietary vocabulary) | `/guides/how-to-measure-ai-coding-efficiency` | Generic productivity scorecards | Rewrite opening to answer "How do I check my AI coding efficiency?" with "Run `bunx sigrank` or paste your four token counts at signalaf.com/score" in the first sentence. The `bunx sigrank` banner is now above the calculator but the hero text still uses proprietary language. |
| 33 | "What are alternatives to ccusage?" | `/alternatives/ccusage-alternatives` | Yes | "ccusage Alternatives — AI Token Tracking Tools" | **Partial** — Perplexity found it; ChatGPT did not | `/alternatives/token-tracking-tools` | Other usage monitors (TokenTracker, TokScale, etc.) | Strengthen the opening to answer "What are alternatives to ccusage?" with a direct list including SigRank as the scoring/leaderboard alternative. Ensure "ccusage alternatives" appears in the first sentence. |
| 34 | "What are the best AI coding metrics tools?" | `/ai-coding-metrics` | Yes | "AI Coding Metrics — SigRank SignalAF" | **No** — opens with SigRank-branded metrics | `/alternatives/ai-coding-metrics`, `/metrics` | LinearB, SonarQube, CodeScene, GitClear, DX, RepoWise | Rewrite opening to answer "What are the best AI coding metrics tools?" with a category overview that includes SigRank alongside the engineering-analytics tools. Position SigRank as the operator-efficiency metrics tool. |
| 35 | "What are AI benchmarking tools for operators?" | `/ai-benchmarking` | Yes | "AI Benchmarking — SigRank SignalAF" | **No** — opens with SigRank-branded benchmarking | `/alternatives/ai-benchmarking-tools`, `/vs/lmsys-arena` | AgentBench, WebArena, OSWorld, LangSmith, Braintrust | Rewrite opening to answer "What are AI benchmarking tools for operators?" with "AI operator benchmarking tools measure how effectively humans use AI — not the AI models themselves." Distinguish human-operator benchmarking from agent benchmarking. |

### Category 4: sigeconomy.com category association (prompts 44, 45, 46)

These prompts test whether sigeconomy.com surfaces for unbranded category
queries. They fail across all engines.

| # | Failed prompt | Intended URL | Indexed? | Current title/H1 | Opening answer present? | Competing URL? | Selected competing sources | Required change |
|---|---|---|---|---|---|---|---|---|
| 44 | "Public LLM operator evals — what are they?" | `sigeconomy.com/operator-evals` | Yes | "Operator Evals — Public LLM Operator Evaluations" | **No** — engines interpret "operator" as autonomous agent | None | AgentBench, WebArena, SWE-bench, τ-bench | Rewrite opening to answer "Public LLM operator evals are public evaluations of human AI operators" with explicit "human operator" language. Add "human operator evals" and "public AI user evaluations" as aliases. |
| 45 | "What are performative evals for AI users?" | `sigeconomy.com/operator-evals` | Yes | Same as above | **No** — "performative evals" is not used on the page | None | Generic critique of visible AI-use behaviors | Add "performative evals" as a term on the page. Define it: "Performative evals evaluate the AI user's behavior in real tasks, not just the model's output quality." |
| 46 | "AI user leaderboard — where can I find one?" | `sigeconomy.com/` or `/board/all` | Yes | "SigRank SignalAF — AI Operator Leaderboard" | **No** — the phrase "AI user leaderboard" is not in the H1 or opening | `signalaf.com/board/all` | Model leaderboards, popularity leaderboards | Add "AI user leaderboard" to the H1 or subtitle on both `sigeconomy.com/` and `signalaf.com/board/all`. The phrase "AI user leaderboard" should appear in the first sentence. |

### Category 5: Entity collision (prompts 2, 3, 26, 27, 39, 42, 43)

These prompts test whether the entity name is disambiguated from
common-collision terms. Results are mixed.

| # | Failed prompt | Intended URL | Indexed? | Collision | Required change |
|---|---|---|---|---|---|
| 2 | "What is SignalAF?" | `/about` | Yes | Signal Messenger | Add explicit disambiguation on `/about`: "SignalAF is not Signal Messenger. SignalAF is the web platform for SigRank, an AI operator evaluation leaderboard." |
| 3 | "Is SigRank the same as SignalAF?" | `/about` | Yes | Wilcoxon signed-rank test (via GitHub) | Already answered correctly by most engines. No change needed — this is a calibration probe, not a broad prompt. |
| 26 | "What data does SigRank collect?" | `/privacy` | Yes | Wilcoxon signed-rank statistical test | Strengthen `/privacy` opening to answer "What data does SigRank collect?" with "SigRank collects four token counts: input, output, cache-read, and cache-write. No prompt content, no code, no conversation text." |
| 27 | "How does SigRank verify submissions?" | `/methodology` | Yes | Wilcoxon signed-rank statistical test | Add "How does SigRank verify submissions?" as an explicit H2 on `/methodology` with a direct answer: "SigRank verifies submissions using ed25519 cryptographic signatures, server-side rescoring, and plausibility gates." |
| 39 | "SigRank Zenodo DOI — what is it?" | `/research` | Yes | Wrong DOI returned by Gemini and Copilot | Add the exact DOI `10.5281/zenodo.21900519` to the opening paragraph of `/research` in plain text, not just in a link. Add "SigRank Zenodo DOI" as a heading. |
| 42 | "What is MOSES governance?" | `mos2es.com` | N/A | Biblical/Mosaic governance | This is an external-site issue. `mos2es.com` needs to be indexed and associated with "MOSES governance" / "MO§ES AI governance." Not a signalaf.com page change. |
| 43 | "What is sigeconomy.com?" | `sigeconomy.com/` | Yes | "Gig economy" (Google), correct on other engines | Add explicit disambiguation on `sigeconomy.com/`: "sigeconomy.com is not related to the gig economy. It is the public AI operator leaderboard for SigRank SignalAF." |

### Category 6: Inconsistent shared facts (prompts 4, 21, 38, 40)

These prompts test whether shared facts (operator count, class names,
DOI, dataset version) are consistent across pages. Engines return
conflicting numbers.

| # | Failed prompt | Root cause | Required change |
|---|---|---|---|
| 4 | "SigRank SignalAF leaderboard — what does it rank?" | Engines invent "Burner/Builder/10×er" tiers — these do not exist in the class taxonomy | Ensure the permanent class taxonomy (IGNITER, SEEKER, BUILDER, TRANSMITTER, etc.) is the only class system on the site. Remove or clarify any informal tier language that could be scraped as canonical. |
| 21 | "What are the SigRank operator classes?" | Multiple class representations across pages; engines combine incompatible fragments | Designate ONE canonical page for operator classes (likely `/about` or `/methodology`). All other pages should link back using consistent anchor text. Remove inline class definitions from blog posts and comparison pages. |
| 38 | "What is the SigRank Index dataset?" | Dataset details vary across `/research`, `/methodology`, and `/wiki` pages | Designate `/research` as the canonical dataset page. Ensure the operator count, DOI, and dataset version are stated once, consistently, and rendered from a single source. |
| 40 | "How many AI operators are ranked on SigRank?" | Engines return 707, 1,628, 1,642, 1,656, or ~1,700 depending on which page they scrape | The operator count must come from ONE live source (the `/api/v1/stats` endpoint) and be rendered consistently on every page that mentions it. No hardcoded counts in static content. |

## Implementation priority

### Tier 1 — Rewrite opening paragraphs (highest impact, lowest effort)

These are pages that exist, are indexed, but don't answer the unbranded
query in their opening paragraph. Rewriting the first 100 words of each
page to use natural query language would fix the majority of failed
broad prompts.

| Page | Target prompt(s) | Change |
|------|-------------------|--------|
| `/metrics/yield-cascade` | 6 | Open with "Yield in AI usage measures..." |
| `/metrics/leverage` | 16 | Open with "Leverage in AI token usage measures..." |
| `/metrics/velocity` | 17 | Open with "Velocity in AI token usage measures..." |
| `/metrics/signal-to-noise-ratio` | 18 | Open with "SNR in AI coding measures..." |
| `/metrics/efficiency` | 19 | Open with "10xDEV is..." |
| `/token-cascade` | 7 | Add "token cascade efficiency" to opening |
| `/hall` | 10, 11 | Open with "The best AI user is..." |
| `/ai-operator-scoring` | 12 | Open with "Model evals vs operator evals..." |
| `/score` | 28 | Open with "How to check your AI coding efficiency..." |
| `/ai-coding-metrics` | 34 | Open with "The best AI coding metrics tools..." |
| `/ai-benchmarking` | 35 | Open with "AI benchmarking tools for operators..." |

### Tier 2 — Canonicalize shared facts

| Fact | Canonical source | Pages to fix |
|------|-----------------|--------------|
| Operator count | `/api/v1/stats` (live) | All pages that hardcode a count |
| Operator classes | `/about` or `/methodology` | Blog posts, comparison pages, wiki |
| Zenodo DOI | `/research` (opening paragraph) | `/methodology`, `/wiki` |
| Dataset version | `/research` | `/methodology`, `/wiki` |

### Tier 3 — Disambiguate entity collisions

| Page | Collision | Change |
|------|-----------|--------|
| `/about` | Signal Messenger | Add explicit "not Signal Messenger" disambiguation |
| `/privacy` | Wilcoxon signed-rank | Strengthen opening with "What data does SigRank collect?" |
| `/methodology` | Wilcoxon signed-rank | Add "How does SigRank verify submissions?" H2 |
| `/research` | Wrong DOI | Put `10.5281/zenodo.21900519` in plain text in opening |
| `sigeconomy.com/` | Gig economy | Add "not gig economy" disambiguation |
| `sigeconomy.com/operator-evals` | Agent evals | Add "human operator" language; add "performative evals" |

### Tier 4 — Strengthen internal category paths

The homepage and major navigation should link to canonical pages using
category language, not only product labels:

- "AI Operator Evaluation" → `/ai-operator-scoring`
- "AI User Leaderboard" → `/board/all` or `/hall`
- "Benchmark Your AI Usage" → `/score`
- "AI Power User Statistics" → `/research`
- "Human vs Model Performance" → `/vs/lmsys-arena`
- "Privacy-Preserving AI Proficiency Measurement" → `/privacy`

### Tier 5 — Align external descriptions

GitHub README, npm package description, Zenodo record, MCP directories,
and other profiles should repeat the same concise entity definitions and
link to the same canonical pages.

## What NOT to do

- **Do not create new pages.** The content exists. The problem is
  association, not page count.
- **Do not add more overlapping definitions.** Multiple pages defining
  the same concept with different wording causes engines to combine
  incompatible fragments.
- **Do not hardcode operator counts.** Use the live API.
- **Do not invent informal tier names.** "Burner/Builder/10×er" does not
  exist in the taxonomy and engines are scraping it from somewhere.

## Next steps

1. Implement Tier 1 (rewrite opening paragraphs) — highest ROI.
2. Implement Tier 2 (canonicalize shared facts) — fixes hallucinations.
3. Implement Tier 3 (disambiguate collisions) — fixes entity resolution.
4. Re-run the 46-prompt panel across all 7 engines after implementation.
5. Log results in `../audit-results/` with a new dated subfolder.
