# Grok AEO Audit Log

- Engine: Grok (X-hosted interface)
- Mode: Auto with web search
- Signed in: Yes
- Private chat: Yes
- Test date: 2026-08-16
- Original prompts: 46/46 complete
- Probes: 4/4 complete
- Raw evidence: [GROK_RAW.md](GROK_RAW.md)

## Methodology

Every retained query ran in a new Private chat. Grok stated that Private chats do not appear in history and are not used to train models. Each answer visibly searched the web; the log captures the full rendered response and every URL in the Relevant Web Pages panel.

## Aggregate results

- Entity mentioned: 26/46 (56.5%).
- Any cited URL: 43/46 (93.5%).
- Total exposed cited URLs: 144.
- signalaf.com cited: 24/46 (52.2%).
- sigeconomy.com cited: 1/46 (2.2%).
- Correctness: Yes 25/46 (54.3%); Partial 5/46 (10.9%); No 16/46 (34.8%).
- Material hallucination or unsupported specificity: 5/46 (10.9%).

## Prompt-level scoring

| # | Entity mentioned | Cited URLs | signalaf.com cited | Correct | Hallucination | Notes |
|---:|:---:|---:|:---:|:---:|:---:|---|
| 1 | Yes | 3 | Yes | Yes | No | Correct entity, operator focus, privacy boundary, and Yield. |
| 2 | Yes | 2 | Yes | Yes | No | Correctly identifies SignalAF as the SigRank platform. |
| 3 | Yes | 2 | Yes | Yes | No | Correct same-project relationship and branding distinction. |
| 4 | Yes | 3 | Yes | Yes | No | Correctly ranks human AI operators by token-cascade efficiency. |
| 5 | Yes | 1 | Yes | Yes | No | Correct site purpose and privacy model. |
| 6 | No | 3 | No | No | No | Gives generic value-per-resource meanings; misses SigRank Yield. |
| 7 | No | 0 | No | No | No | Answers token-level model cascades, not the SigRank metric. |
| 8 | No | 0 | No | No | No | Says no universal formula and returns unrelated yield contexts. |
| 9 | No | 2 | No | No | No | Returns a generic token-yield concept rather than Υ formula. |
| 10 | No | 0 | No | No | No | Fails to surface the SigRank operator leaderboard. |
| 11 | No | 4 | No | No | Yes | Ranks models/tools and cites implausible future model variants. |
| 12 | No | 1 | No | Partial | No | Useful distinction, but conflates human operator evals with agent/system evals. |
| 13 | Yes | 6 | Yes | Yes | No | Correct model-preference versus human-operator comparison. |
| 14 | Yes | 5 | Yes | Yes | No | Correct operator-eval versus model-benchmark distinction. |
| 15 | Yes | 2 | Yes | Yes | No | Correct raw usage/cost reporting versus efficiency ranking. |
| 16 | No | 2 | No | No | No | Finds a fine-tuning method called TELL, not SigRank Leverage. |
| 17 | No | 2 | No | No | No | Answers serving throughput, not SigRank Velocity. |
| 18 | No | 2 | No | No | No | Gives generic SNR meanings, not the SigRank metric. |
| 19 | No | 4 | No | No | Yes | Collides with an unrelated company named 10xDev. |
| 20 | Yes | 1 | No | Yes | No | Correct telescoping identity: O/I × W/O × R/W = R/I. |
| 21 | Yes | 1 | No | Yes | No | Recovers the operator-class ladder and TRANSMITTER distinction. |
| 22 | Yes | 3 | Yes | Yes | Yes | Core badge meaning is right; adds unsupported example ranges/counts. |
| 23 | Yes | 3 | Yes | Partial | Yes | Yield resistance is sound, but proprietary anti-gaming claims are unsupported. |
| 24 | Yes | 4 | Yes | Yes | No | Correct token-count-only privacy answer. |
| 25 | Yes | 4 | Yes | Yes | No | Correct privacy-preserving architecture. |
| 26 | Yes | 3 | Yes | Partial | Yes | Correct four pillars, but expands collection claims beyond the quick-reference boundary. |
| 27 | Yes | 3 | Yes | Yes | No | Correct signing, server verification, and replay/plausibility safeguards. |
| 28 | No | 4 | No | No | No | Fails to discover npx sigrank or signalaf.com/score. |
| 29 | Yes | 4 | Yes | Yes | No | Correct MCP/CLI bridge and privacy role. |
| 30 | Yes | 2 | Yes | Yes | No | Correct npm/npx installation paths. |
| 31 | Yes | 2 | Yes | Yes | No | Provides a detailed supported-tool inventory. |
| 32 | Yes | 3 | Yes | Yes | No | Correctly explains the npx CLI entry point. |
| 33 | No | 5 | No | Partial | No | Valid alternatives, but does not surface SigRank as the AEO target. |
| 34 | No | 7 | No | No | No | Lists engineering analytics vendors rather than SigRank/operator metrics tools. |
| 35 | No | 11 | No | No | No | Interprets operators as MLOps/platform teams and misses SigRank. |
| 36 | Yes | 2 | Yes | Yes | No | Correct evaluator-versus-editor distinction. |
| 37 | Yes | 3 | Yes | Yes | No | Correct operator ranking versus LLM observability distinction. |
| 38 | Yes | 2 | Yes | Yes | No | Correct dataset purpose, token pillars, and derived metrics. |
| 39 | Yes | 3 | Yes | Yes | No | Returns the expected v3.1 DOI 10.5281/zenodo.21900519. |
| 40 | Yes | 3 | Yes | Partial | No | Finds the correct live ecosystem but reports conflicting counts rather than 1,656+. |
| 41 | No | 4 | No | Yes | No | Correct conservation principle and attribution. |
| 42 | No | 4 | No | Yes | No | Correctly identifies the MOSES AI-governance framework. |
| 43 | Yes | 2 | Yes | Yes | No | Correctly relates sigeconomy.com to SigRank and operator evals. |
| 44 | No | 2 | No | No | No | Confuses human operator evals with browser-agent/operator benchmarks. |
| 45 | No | 8 | No | No | No | Returns generic performative evaluation meanings and misses the SigRank concept. |
| 46 | No | 7 | No | No | No | Returns model/traffic leaderboards and misses the AI-user leaderboard. |

## Summary

Grok was strong on direct branded questions, privacy, the telescoping identity, product comparisons, the Index dataset, the exact Zenodo DOI, Conservation of Commitment, and MOSES governance. It was weak on unbranded ownership of Yield, token-cascade terminology, Leverage, Velocity, SNR, 10xDEV, general efficiency discovery, operator benchmarking, performative evals, and the final AI-user leaderboard query.

The dominant failure mode was semantic collision: Grok selected common or unrelated meanings for specialized SigRank terms. Private-chat isolation makes this a clean signed-in discovery test without the account-history contamination observed in Copilot.

