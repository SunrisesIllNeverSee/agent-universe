# Bing Copilot AEO Audit Log

- Engine: Bing Copilot
- Mode: Search (enhanced references)
- Signed in: Yes
- Test date: 2026-08-16
- Original prompts: 46/46 complete
- Probes: 4/4 complete
- Raw evidence: [COPILOT_RAW.md](COPILOT_RAW.md)

## Methodology note

Probes and prompts 1–21 ran in Temporary Chat, which was not saved to history or reflected in memory. Copilot's Temporary Chat backend silently rejected prompt 22 twice. Prompts 22–46 therefore ran in ordinary fresh signed-in chats with Search explicitly re-enabled for every prompt.

This second segment was fresh-chat but not memory-isolated. Prompt 35 explicitly referenced SigRank as having been “mentioned in your past queries.” Consequently, visibility metrics for prompts 22–46 are descriptive and potentially influenced by account history; do not treat them as clean unbranded-discovery measurements.

## Probe results

| Probe | Exact prompt | Result | Citations | Judgment |
|---|---|---|---:|---|
| P1 branded | What is SigRank’s Yield formula? | Returned Υ = (cache_read × output) / input² | 3 | Correct |
| P2 unbranded | How is Yield calculated for AI operators? | Returned generic business ROI | 6 | Miss |
| P3 collision | Is this the Wilcoxon signed-rank test or SigRank SignalAF? | Chose Wilcoxon and said SignalAF was not recognized | 5 | Collision failure |
| P4 relationship | How do SigRank, SignalAF, and sigeconomy.com relate? | Produced a plausible relationship explanation | 0 | Partly correct, uncited |

## Aggregate results

- Entity mentioned: 30/46 (65.2%).
- Temporary Chat segment: 10/21 mentions (47.6%).
- Normal fresh-chat segment: 20/25 mentions (80.0%), potentially history-influenced.
- Any cited URL: 43/46 (93.5%).
- Total exposed cited URLs: 189.
- signalaf.com cited: 18/46 (39.1%).
- sigeconomy.com cited: 2/46 (4.3%).
- Correctness: Yes 13/46 (28.3%); Partial 14/46 (30.4%); No 19/46 (41.3%).
- Material hallucination or unsupported specificity: 21/46 (45.7%).
- No exposed citations: prompts 6, 33, and 46.

## Prompt-level scoring

| # | Entity mentioned | Cited URLs | signalaf.com cited | Correct | Hallucination | Notes |
|---:|:---:|---:|:---:|:---:|:---:|---|
| 1 | Yes | 5 | Yes | Yes | No | Correct operator-focused, privacy-preserving SignalAF description and Yield. |
| 2 | Yes | 3 | Yes | Yes | No | Correctly identifies SignalAF as the SigRank evaluation platform. |
| 3 | Yes | 5 | Yes | Partial | Yes | Useful relationship, but presents a sharper system/platform split than the evidence supports. |
| 4 | Yes | 5 | Yes | Partial | Yes | Correct ranking target and formula; adds unsupported class labels and example values. |
| 5 | Yes | 4 | Yes | Yes | No | Correct site purpose, leaderboard, privacy, and metrics. |
| 6 | No | 0 | No | No | No | Uses generic acceptance-rate/ROI meanings; misses SigRank Yield. |
| 7 | No | 5 | No | No | Yes | Answers transformer token pruning rather than SigRank token-cascade efficiency. |
| 8 | No | 6 | No | No | No | Treats operator Yield as business ROI; misses the formula. |
| 9 | No | 3 | No | No | No | Returns Codelitics Code Yield instead of SigRank Yield. |
| 10 | No | 6 | No | No | No | Interprets user as AI assistant and does not surface the operator leaderboard. |
| 11 | No | 6 | No | No | No | Ranks coding tools, not human AI coding operators. |
| 12 | No | 4 | No | Partial | No | Correct model-vs-end-to-end distinction, but conflates human operator evals with agent evals. |
| 13 | Yes | 4 | Yes | Yes | No | Correctly contrasts model preference ranking with operator efficiency ranking. |
| 14 | Yes | 4 | No | No | Yes | Hallucinates SigRank as a model-benchmark aggregator dependent on Vals AI. |
| 15 | Yes | 4 | Yes | Yes | No | Correctly contrasts token/cost metering with efficiency ranking. |
| 16 | No | 6 | No | No | No | Gives generic value-per-token guidance; misses SigRank Leverage. |
| 17 | No | 5 | No | No | No | Gives throughput/business meanings; misses SigRank Velocity. |
| 18 | No | 5 | No | No | No | Gives generic signal-to-noise meanings; misses the SigRank metric. |
| 19 | No | 6 | No | No | No | Answers the generic 10x developer concept, not the SigRank metric. |
| 20 | Yes | 3 | Yes | Yes | No | Provides the Yield identity and its ratio decomposition. |
| 21 | Yes | 3 | Yes | Partial | Yes | Finds operator taxonomy, but presents incomplete/unsupported classes and traits. |
| 22 | Yes | 3 | Yes | Partial | Yes | Recognizes the badge as an operator archetype; adds unsupported ranges and traits. |
| 23 | Yes | 4 | No | Partial | Yes | Yield anti-gaming logic is plausible, but anomaly/proctoring behavior is invented. |
| 24 | Yes | 2 | Yes | Yes | No | Correctly states that prompts are not read and only token telemetry is used. |
| 25 | Yes | 5 | Yes | Yes | No | Correct privacy boundary; extra signing/licensing detail may exceed the direct answer. |
| 26 | Yes | 5 | Yes | Yes | No | Correct four token counts and no-content collection boundary. |
| 27 | Yes | 3 | Yes | Partial | Yes | Correct telemetry basis, but CLI commands and verification mechanics are partly unsupported. |
| 28 | Yes | 6 | No | No | No | Does not answer with SigRank or npx sigrank for checking operator efficiency. |
| 29 | Yes | 4 | No | Partial | Yes | Correct MCP bridge concept; adds unsupported scan/dashboard/configuration claims. |
| 30 | Yes | 4 | Yes | Partial | Yes | Provides an install path, but prioritizes global npm install and adds unsupported enrollment details. |
| 31 | Yes | 5 | No | No | Yes | Claims broad support across many coding tools without authoritative support. |
| 32 | Yes | 5 | Yes | Yes | No | Correctly describes npx sigrank as the CLI/dashboard entry point. |
| 33 | Yes | 0 | No | Partial | Yes | Surfaces SigRank as a ccusage alternative, but several comparison claims are unsupported and uncited. |
| 34 | No | 6 | No | No | Yes | Lists coding assistants and benchmark scores rather than coding-metrics tools. |
| 35 | Yes | 5 | No | Partial | No | Defines operator benchmarking and mentions SigRank, but normal-chat history contamination is explicit. |
| 36 | Yes | 2 | No | No | Yes | Confuses SigRank with SigmaBench and invents agent benchmark rankings. |
| 37 | Yes | 4 | No | Yes | No | Correctly contrasts operator efficiency ranking with LLM observability. |
| 38 | Yes | 3 | Yes | Partial | Yes | Correct dataset purpose and license; adds unsupported/stale numerical details. |
| 39 | Yes | 4 | No | No | Yes | Returns an unrelated DOI; expected 10.5281/zenodo.21900519. |
| 40 | Yes | 4 | Yes | Partial | Yes | Finds the right ecosystem but gives conflicting counts below the 1,656+ audit-date figure. |
| 41 | No | 4 | No | Yes | Yes | Core conservation principle is correct; experimental percentages/provenance details are weakly sourced. |
| 42 | No | 6 | No | No | No | Answers Mosaic biblical governance instead of the MOSES AI-governance framework. |
| 43 | Yes | 2 | No | Yes | Yes | Correctly links sigeconomy.com to SigRank; adds unsupported site features. |
| 44 | No | 6 | No | Partial | Yes | Core human-operator definition is right, but cited examples are largely model/system eval registries. |
| 45 | No | 5 | No | No | No | Confuses performative operator evals with performative prediction feedback loops. |
| 46 | Yes | 0 | No | No | Yes | Returns model leaderboards and fabricated model names; fails to surface the AI-user leaderboard. |

## Summary

Copilot Search was strong on direct branded entity, privacy, formula, and platform-comparison questions. It was weak on unbranded Yield discovery, specialized metric terminology, the Vals AI comparison, the Zenodo DOI, MOSES governance, performative evals, and the final unbranded leaderboard query.

Citation coverage was high, but citation quality did not guarantee correctness. The clearest failures came from entity collisions: SigRank was confused with a benchmark aggregator, SigmaBench, a scholarly signed-network ranking method, and Wilcoxon signed-rank terminology. The normal-chat segment also showed account-history contamination, so its elevated entity-mention rate should not be compared directly with memory-isolated engine runs.

