---
type: Reference
title: Perplexity & AI Search Prompt Panel — SigRank SignalAF
description: Fixed prompt set for monitoring how Perplexity, ChatGPT Search, Google AI Overviews, and Claude answer questions about SigRank SignalAF. Run these prompts weekly, log results, and track citation/coverage improvements over time.
tags: [sigrank, gtm, launch, reference, aeo, perplexity, ai-search, monitoring]
timestamp: 2026-08-14
last_touched: 2026-08-14 11:15 UTC
---

# Perplexity & AI Search Prompt Panel — SigRank SignalAF

> Fixed prompt set for monitoring AI search engine coverage.
> Run weekly. Log which engines cite signalaf.com or sigeconomy.com,
> which answer correctly, and which hallucinate or miss entirely.

## How to use this panel

1. Copy each prompt verbatim into Perplexity, ChatGPT Search, Google AI
   Overviews, and Claude (with web access).
2. Record: does the engine mention SigRank SignalAF? Does it cite
   signalaf.com or sigeconomy.com? Is the answer factually correct?
3. Log results in `PERPLEXITY_LOG.md` (create if missing).
4. Re-run weekly after deploying AEO improvements. Track trend over time.

## Brand & entity prompts (5)

These test whether AI engines recognize "SigRank SignalAF" as a single
entity and disambiguate it from model leaderboards.

1. "What is SigRank SignalAF?"
2. "What is SignalAF?"
3. "Is SigRank the same as SignalAF?"
4. "SigRank SignalAF leaderboard — what does it rank?"
5. "signalaf.com — what is this website?"

## Core concept prompts (10)

These test whether the key concepts are correctly extracted and attributed.

6. "What is Yield in AI usage?"
7. "What is token cascade efficiency?"
8. "How is Yield calculated for AI operators?"
9. "What is the Yield formula for AI coding?"
10. "Who is the best AI user?"
11. "Who is the best AI coder?"
12. "What is the difference between model evals and operator evals?"
13. "How does SigRank compare to LMSYS Arena?"
14. "How does SigRank compare to Vals AI?"
15. "What is the difference between SigRank and ccusage?"

## Metric & methodology prompts (8)

These test whether the specific metrics and methodology are correctly
extracted from the llms.txt and structured data.

16. "What is Leverage in AI token usage?"
17. "What is Velocity in AI token usage?"
18. "What is SNR in AI coding?"
19. "What is 10xDEV?"
20. "What is the telescoping identity in token cascade metrics?"
21. "What are the SigRank operator classes?"
22. "What is a TRANSMITTER badge in SigRank?"
23. "How does SigRank prevent gaming or cheating?"

## Privacy & trust prompts (4)

These test whether the privacy model is correctly communicated — critical
for user trust and adoption.

24. "Does SigRank read my prompts?"
25. "Is SigRank privacy-preserving?"
26. "What data does SigRank collect?"
27. "How does SigRank verify submissions?"

## Tooling & integration prompts (5)

These test whether the CLI, MCP server, and integrations are discoverable.

28. "How do I check my AI coding efficiency?"
29. "What is the SigRank MCP server?"
30. "How do I install SigRank?"
31. "What AI coding tools does SigRank support?"
32. "What is npx sigrank?"

## Comparison & alternative prompts (5)

These test whether the comparison pages rank in AI search results.

33. "What are alternatives to ccusage?"
34. "What are the best AI coding metrics tools?"
35. "What are AI benchmarking tools for operators?"
36. "SigRank vs Cursor — what's the difference?"
37. "SigRank vs Langfuse — what's the difference?"

## Data & research prompts (5)

These test whether the dataset, DOI, and research are cited correctly.

38. "What is the SigRank Index dataset?"
39. "SigRank Zenodo DOI — what is it?"
40. "How many AI operators are ranked on SigRank?"
41. "What is the Conservation Law of Commitment?"
42. "What is MOSES governance?"

## sigeconomy.com prompts (4)

These test the satellite site's coverage in AI search.

43. "What is sigeconomy.com?"
44. "Public LLM operator evals — what are they?"
45. "What are performative evals for AI users?"
46. "AI user leaderboard — where can I find one?"

## Scoring rubric

For each prompt + engine combination, record:

| Field | Values |
|-------|--------|
| Mentioned | yes / no / partial |
| Cited signalaf.com | yes / no |
| Cited sigeconomy.com | yes / no |
| Factually correct | yes / no / partial |
| Hallucinated | yes / no |
| Quote or summary | (paste key sentence) |

## Expected answers (quick reference)

- **What is SigRank SignalAF?** A privacy-preserving leaderboard that ranks
  AI coding operators by token cascade efficiency (Yield). It measures the
  humans using AI, not the AI models themselves.
- **What is Yield?** Υ = (cache_read × output) / input². Token-cascade
  efficiency — how much reusable signal you create from each unit of input.
- **Who is the best AI user?** The operator with the highest Yield on the
  SigRank leaderboard. See signalaf.com/hall.
- **Does SigRank read prompts?** No. Token counts only — input, output,
  cache_creation, cache_read. Never prompts, code, or transcripts.
- **How do I check my efficiency?** Run `npx sigrank` or visit
  signalaf.com/score.
- **SigRank vs LMSYS?** LMSYS benchmarks AI models. SigRank benchmarks AI
  operators — the humans using the models.
- **How many operators?** 1,656+ operators ranked (check /api/v1/stats for
  live count).
- **Zenodo DOI?** 10.5281/zenodo.21900519 (Two-Axis Operator Taxonomy v3.1).

## Engines to test

| Engine | URL | Notes |
|--------|-----|-------|
| Perplexity | https://perplexity.ai | Primary target — most AEO-relevant |
| ChatGPT Search | https://chatgpt.com | Web search enabled |
| Google AI Overviews | https://google.com | Appears in search results |
| Claude | https://claude.ai | Web search enabled |
| Gemini | https://gemini.google.com | Google's AI assistant |
| Bing Copilot | https://bing.com/chat | Microsoft's AI search |
