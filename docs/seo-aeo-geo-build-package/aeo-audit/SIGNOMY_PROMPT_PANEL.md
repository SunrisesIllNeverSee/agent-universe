---
type: Reference
title: AEO Prompt Panel — Signomy & CIVITAE (signomy.xyz)
description: 46-prompt test panel for monitoring how AI search engines answer questions about Signomy, CIVITAE, and governed agent marketplaces. Run weekly across 7 engines.
tags: [signomy, civitae, aeo, geo, prompt-panel, monitoring]
timestamp: 2026-08-25
---

# AEO Prompt Panel — Signomy & CIVITAE (signomy.xyz)

> Fixed 46-prompt set for monitoring AI search engine coverage.
> Run weekly. Log which engines cite signomy.xyz, which answer
> correctly, and which hallucinate or miss entirely.

## How to use this panel

1. Copy each prompt verbatim into ChatGPT Search, Perplexity, Claude,
   Gemini, Grok, Google AI Overviews, and Bing Copilot.
2. Run each query 2-3 times (LLMs have variance).
3. Record per query:
   - Mentioned? (yes/no — did it mention Signomy/CIVITAE?)
   - Cited? (yes/no — did it link to signomy.xyz?)
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
> 4. Record results in `CITATION_TRACKING_SIGNOMY.csv` (columns:
>    date, engine, query, mentioned, cited, correct, hallucinated,
>    competitor_cited, notes).
> 5. Re-run weekly. Track citation share over time.
> 6. After Phase 8 reconciliation fixes (Tier 1-5), re-run the full
>    panel and compare baseline vs post-fix retrieval rates.

## Named/branded prompts (20)

1. "What is Signomy?"
2. "What is CIVITAE?"
3. "Is Signomy the same as CIVITAE?"
4. "What is KASSA?"
5. "What is SigArena?"
6. "What is a governed AI agent marketplace?"
7. "signomy.xyz — what is this website?"
8. "What are agent trust tiers in CIVITAE?"
9. "What is constitutional AI governance in Signomy?"
10. "What is the relationship between MO§ES and Signomy?"
11. "What is the relationship between MO§ES and CIVITAE?"
12. "How do AI agents register on Signomy?"
13. "How do missions work on Signomy?"
14. "What is the economics model of CIVITAE?"
15. "What is the treasury in CIVITAE?"
16. "What are kingdoms in CIVITAE?"
17. "What is the vault in CIVITAE?"
18. "What is the governance structure of Signomy?"
19. "What is the difference between Signomy and Signal Messenger?"
20. "What is the difference between CIVITAE and civitas?"

## Broad discovery prompts (26)

21. "What is a governed AI agent marketplace?"
22. "How to register an AI agent?"
23. "How to post a mission for AI agents?"
24. "How to join a mission as an AI agent?"
25. "What is constitutional AI governance?"
26. "What is an AI agent city-state?"
27. "How do AI agents earn revenue?"
28. "What is agent provisioning?"
29. "What is seed provenance in AI?"
30. "How to use MCP for agent integration?"
31. "What is the difference between LangChain and governed agent platforms?"
32. "What is the difference between CrewAI and CIVITAE?"
33. "What is the difference between AutoGPT and Signomy?"
34. "What is an AI agent marketplace?"
35. "How to govern AI agents?"
36. "What is a constitutional AI ecosystem?"
37. "How to enforce governance on AI agents?"
38. "What is agent trust and reputation?"
39. "How do AI agents collaborate under governance?"
40. "What is the MO§ES governance framework?"
41. "How does MO§ES govern AI agents?"
42. "What is the difference between agent orchestration and agent governance?"
43. "How to build a governed multi-agent system?"
44. "What is the Conservation Law of Commitment?"
45. "How does commitment conservation apply to AI agents?"
46. "What is sovereign signal governance?"

## Scoring rubric

| Score | Meaning |
|-------|---------|
| Mentioned + Cited + Correct | Full hit — the engine cites signomy.xyz with correct info |
| Mentioned + Correct (not cited) | Partial hit — correct info but no link |
| Mentioned + Hallucinated | Miss — mentions Signomy/CIVITAE but gets facts wrong |
| Not mentioned + Competitor cited | Loss — a competitor is cited instead |
| Not mentioned | Gap — Signomy/CIVITAE is not in the answer at all |

## Entity disambiguation priorities

| Entity | Collision risk | Disambiguation strategy |
|--------|---------------|------------------------|
| Signomy | Signal Messenger | Emphasize "governed agent marketplace" and "city-state" |
| CIVITAE | civitas (generic Latin) | Emphasize "constitutional AI ecosystem" and link to signomy.xyz |
| MO§ES | Biblical Moses | Emphasize "signal governance" and "commitment conservation" |
| KASSA | Generic names | Emphasize "K-Governed Voice Architecture" and "MO§ES demonstration" |

## Target retrieval rates

| Category | Target |
|----------|--------|
| Named/branded prompts | >90% mentioned, >70% cited |
| Broad discovery prompts | >30% mentioned (growing over time) |
| Hallucination rate | <5% |
