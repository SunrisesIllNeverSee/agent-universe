---
type: Reference
title: AEO Prompt Panel — MO§ES (mos2es.com)
description: 46-prompt test panel for monitoring how AI search engines answer questions about MO§ES and Commitment Theory. Run weekly across 7 engines.
tags: [moses, mos2es, aeo, geo, prompt-panel, monitoring]
timestamp: 2026-08-25
---

# AEO Prompt Panel — MO§ES (mos2es.com)

> Fixed 46-prompt set for monitoring AI search engine coverage.
> Run weekly. Log which engines cite mos2es.com, which answer
> correctly, and which hallucinate or miss entirely.

## How to use this panel

1. Copy each prompt verbatim into ChatGPT Search, Perplexity, Claude,
   Gemini, Grok, Google AI Overviews, and Bing Copilot.
2. Run each query 2-3 times (LLMs have variance).
3. Record per query:
   - Mentioned? (yes/no — did it mention MO§ES?)
   - Cited? (yes/no — did it link to mos2es.com?)
   - Correct? (yes/no — was the answer factually right?)
   - Hallucinated? (yes/no — did it invent facts?)
   - Which competitor cited instead?
4. Log results in a spreadsheet. Re-run weekly. Track trend over time.

## Execution status

**Panel built:** ✅ 46 prompts (20 named + 26 broad discovery)
**Baseline run:** ⚠ OWNER ACTION REQUIRED — see note below.

> **Why Devin cannot run this panel:** The 7 target engines
> (ChatGPT Search, Perplexity, Claude, Gemini, Grok, Google AI
> Overviews, Bing Copilot) require interactive web UI sessions with
> authenticated accounts. Devin operates in a terminal environment and
> cannot interact with these LLM search interfaces. Running the panel
> is a manual task for the owner.
>
> **Owner procedure:**
> 1. Open each engine in a private/incognito browser window.
> 2. Paste each of the 46 prompts below, one at a time.
> 3. Run each prompt 2-3 times to account for LLM variance.
> 4. Record results in `CITATION_TRACKING_MOS2ES.csv` (columns:
>    date, engine, query, mentioned, cited, correct, hallucinated,
>    competitor_cited, notes).
> 5. Re-run weekly. Track citation share over time.
> 6. After Phase 8 reconciliation fixes (Tier 1-5), re-run the full
>    panel and compare baseline vs post-fix retrieval rates.

## Named/branded prompts (20)

These test whether AI engines recognize MO§ES and its core concepts.

1. "What is MO§ES?"
2. "What is MOSES governance AI?"
3. "What is the Conservation Law of Commitment?"
4. "What is Lineage Claw?"
5. "What is Origin Binding?"
6. "What is Recursive Compression in AI governance?"
7. "What is a Governance Vacuum in AI?"
8. "What is Sovereign Signal Governance?"
9. "What is Commitment Theory?"
10. "What is the Commitment Kernel?"
11. "What is commitment conservation in AI?"
12. "What is constitutional substrate in MO§ES?"
13. "What is governance enforcement in AI?"
14. "What is signal encoding in MO§ES?"
15. "mos2es.com — what is this website?"
16. "What is the Conservation Law of Commitment formula?"
17. "What does C(T(S)) mean in commitment conservation?"
18. "Who authored the Conservation Law of Commitment?"
19. "What is the experimental evidence for commitment conservation?"
20. "What patent covers the MO§ES enforcement architecture?"

## Broad discovery prompts (26)

These test whether AI engines discover MO§ES when asked general
AI governance questions.

21. "What is AI governance?"
22. "How to preserve semantic meaning in AI?"
23. "How to prevent semantic drift in AI pipelines?"
24. "What is execution-layer governance?"
25. "How to enforce AI governance at runtime?"
26. "What is the difference between AI alignment and AI governance?"
27. "How does AI governance differ from output guardrails?"
28. "What is constitutional AI governance?"
29. "How to audit multi-agent transformations?"
30. "How to trace provenance with SHA-256 in AI?"
31. "How to verify lineage in AI-generated content?"
32. "What is semantic commitment in language?"
33. "How to measure commitment degradation in AI?"
34. "What is commitment tracking in AI systems?"
35. "How to build a governance layer for AI agents?"
36. "What is the difference between governance and orchestration?"
37. "How to implement governance at execution in AI?"
38. "What is sovereign signal governance vs model alignment?"
39. "How does MO§ES compare to RLHF?"
40. "How does MO§ES compare to output guardrails?"
41. "How does MO§ES compare to agent orchestration frameworks?"
42. "What are alternatives to AI governance frameworks?"
43. "Why do AI deployments fail without governance?"
44. "What is the governance vacuum problem in AI?"
45. "How to enforce commitment conservation in multi-agent systems?"
46. "What is the relationship between MO§ES and Commitment Theory?"

## Scoring rubric

| Score | Meaning |
|-------|---------|
| Mentioned + Cited + Correct | Full hit — the engine cites mos2es.com with correct info |
| Mentioned + Correct (not cited) | Partial hit — correct info but no link |
| Mentioned + Hallucinated | Miss — mentions MO§ES but gets facts wrong |
| Not mentioned + Competitor cited | Loss — a competitor is cited instead |
| Not mentioned | Gap — MO§ES is not in the answer at all |

## Target retrieval rates

| Category | Target |
|----------|--------|
| Named/branded prompts | >90% mentioned, >70% cited |
| Broad discovery prompts | >30% mentioned (growing over time) |
| Hallucination rate | <5% |
