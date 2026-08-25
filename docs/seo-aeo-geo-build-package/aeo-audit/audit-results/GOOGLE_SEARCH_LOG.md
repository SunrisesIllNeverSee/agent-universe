# Google Search / AI Overviews AEO Log — SigRank SignalAF

## Run metadata

- Date: 2026-08-16
- Engine/mode: Google Search / AI Overviews
- Signed in: yes
- Personalized results: yes
- Search handling: every prompt submitted as a fresh Google search
- Raw evidence: [GOOGLE_SEARCH_RAW.md](GOOGLE_SEARCH_RAW.md)
- Important: human judgments below are intentionally separate from the unabridged evidence and can be rescored later.

## Calibration probes

| ID | Exact prompt | AI Overview | Mentioned | Cited signalaf.com | Cited sigeconomy.com | Factually correct | Hallucinated | Summary |
|---|---|---|---|---|---|---|---|---|
| P1 | What is SigRank’s Yield formula? | yes | yes | yes | yes | yes | no | Exact formula and correct token-cascade explanation; one irrelevant SimRank citation also appeared. |
| P2 | How is Yield calculated for AI operators? | yes | yes | yes | no | partial | yes | Exact formula was correct, but the answer added unsupported four-tier Yield thresholds. |
| P3 | Is this the Wilcoxon signed-rank test or SigRank SignalAF? | yes | no | no | no | no | yes | Incorrectly declared that the query referred to Wilcoxon and said SigRank SignalAF was not a recognized statistical method. |
| P4 | How do SigRank, SignalAF, and sigeconomy.com relate? | yes | yes | yes | yes | partial | yes | Correct ecosystem relationship and formula, but invented “Burners, Builders, and 10xs” class labels. |

## Original 46-prompt panel

| # | Exact prompt | AI Overview | Mentioned | Cited signalaf.com | Cited sigeconomy.com | Factually correct | Hallucinated | Summary |
|---:|---|---|---|---|---|---|---|---|
| 1 | What is SigRank SignalAF? | yes | no | no | no | no | yes | Answered with a generic definition of “signal” and Signal Messenger. |
| 2 | What is SignalAF? | yes | yes | yes | yes | partial | yes | Correct platform, formula, and privacy model, but invented “builders,” “10xers,” and “burners” as classes. |
| 3 | Is SigRank the same as SignalAF? | yes | yes | yes | no | yes | no | Correctly distinguished the CLI/protocol from the web platform and leaderboard. |
| 4 | SigRank SignalAF leaderboard — what does it rank? | yes | yes | yes | yes | yes | no | Correctly ranked human operators by token-cascade efficiency rather than models or raw usage. |
| 5 | signalaf.com — what is this website? | yes | yes | yes | no | yes | no | Correct product description and explicit disambiguation from Signal Messenger. |
| 6 | What is Yield in AI usage? | yes | no | no | no | no | no | Returned generic inference, task, compute, and industrial yield meanings. |
| 7 | What is token cascade efficiency? | yes | no | yes | no | partial | no | Described the correct four-pillar concept but did not identify SigRank or provide the canonical formula. |
| 8 | How is Yield calculated for AI operators? | yes | yes | yes | yes | yes | no | Exact formula, four token pillars, and correct interpretation. |
| 9 | What is the Yield formula for AI coding? | yes | yes | yes | no | yes | no | Exact formula and variable definitions with first-party sources. |
| 10 | Who is the best AI user? | yes | no | no | no | no | no | Recommended general prompting traits and AI products; no leaderboard. |
| 11 | Who is the best AI coder? | yes | no | no | no | no | no | Interpreted “coder” as the best coding assistant and recommended Claude Code/Cursor. |
| 12 | What is the difference between model evals and operator evals? | yes | no | no | no | partial | no | Correct model-vs-system distinction, but treated the operator as an application workflow rather than a human. |
| 13 | How does SigRank compare to LMSYS Arena? | yes | yes | yes | no | yes | no | Correct human-operator efficiency versus model-preference comparison. |
| 14 | How does SigRank compare to Vals AI? | yes | yes | yes | no | partial | yes | Correct layer distinction, but repeated unsupported class labels and several speculative details. |
| 15 | What is the difference between SigRank and ccusage? | yes | yes | yes | no | yes | no | Correct sensor/raw accounting versus efficiency scoring and leaderboard distinction. |
| 16 | What is Leverage in AI token usage? | yes | no | no | no | no | no | Defined business value per token rather than cache reads relative to input. |
| 17 | What is Velocity in AI token usage? | yes | no | no | no | no | no | Defined token burn rate over time rather than output relative to input. |
| 18 | What is SNR in AI coding? | yes | no | no | no | no | no | Returned the generic signal-to-noise mental model. |
| 19 | What is 10xDEV? | yes | no | no | no | no | no | Returned the conventional “10x developer” concept. |
| 20 | What is the telescoping identity in token cascade metrics? | yes | yes | yes | no | partial | no | Recognized it as an integrity invariant but omitted the actual telescoping equation. |
| 21 | What are the SigRank operator classes? | yes | yes | yes | no | partial | yes | Returned a contradictory four-tier Yield ladder instead of the permanent class taxonomy. |
| 22 | What is a TRANSMITTER badge in SigRank? | yes | yes | yes | no | yes | no | Correctly described a temporary peak badge separate from permanent classes. |
| 23 | How does SigRank prevent gaming or cheating? | yes | yes | yes | no | partial | yes | Correctly mentioned Yield and local telemetry but overstated their ability to prevent fabricated or spoofed submissions. |
| 24 | Does SigRank read my prompts? | yes | yes | yes | no | yes | no | Exact privacy answer with the four token fields and no prompt/code content. |
| 25 | Is SigRank privacy-preserving? | yes | yes | yes | no | yes | no | Correct token-only, local-processing, signed-submission privacy explanation. |
| 26 | What data does SigRank collect? | yes | yes | yes | yes | yes | no | Correctly listed the four aggregate token fields and no prompt/transcript collection. |
| 27 | How does SigRank verify submissions? | yes | yes | yes | no | yes | no | Correct Ed25519 enrollment, server verification, replay, and plausibility checks. |
| 28 | How do I check my AI coding efficiency? | yes | no | no | no | no | no | Returned a generic developer-productivity measurement framework instead of SigRank. |
| 29 | What is the SigRank MCP server? | yes | yes | yes | no | yes | no | Correct privacy-first MCP/telemetry description and leaderboard workflow. |
| 30 | How do I install SigRank? | yes | yes | yes | no | yes | no | Correct npm/npx commands, requirements, enrollment, and submission steps. |
| 31 | What AI coding tools does SigRank support? | yes | yes | yes | no | partial | yes | Found first-party integration material, but the “18+” count and several named platforms need official verification. |
| 32 | What is npx sigrank? | yes | yes | yes | no | yes | no | Correct CLI, local telemetry, TUI, privacy, leaderboard, and MCP explanation. |
| 33 | What are alternatives to ccusage? | yes | no | no | no | no | no | Listed other trackers and forks but omitted SigRank. |
| 34 | What are the best AI coding metrics tools? | yes | no | no | no | no | no | Recommended mainstream engineering analytics platforms; SigRank was absent. |
| 35 | What are AI benchmarking tools for operators? | yes | no | no | no | no | no | Interpreted operators as autonomous agents and production AI systems. |
| 36 | SigRank vs Cursor — what's the difference? | yes | yes | yes | no | yes | no | Correct coding-tool versus cross-tool operator-measurement distinction. |
| 37 | SigRank vs Langfuse — what's the difference? | yes | yes | yes | yes | yes | no | Correctly contrasted production observability with privacy-preserving operator scoring. |
| 38 | What is the SigRank Index dataset? | yes | yes | yes | no | yes | no | Correct dataset, token pillars, Yield, privacy, archival, and licensing description. |
| 39 | SigRank Zenodo DOI — what is it? | yes | yes | yes | no | partial | no | Recognized the SigRank research deposit but failed to provide DOI `10.5281/zenodo.21900519`. |
| 40 | How many AI operators are ranked on SigRank? | yes | yes | no | yes | no | yes | Returned 1,642, conflicting with the supplied 1,656+ reference count. |
| 41 | What is the Conservation Law of Commitment? | yes | yes | yes | no | yes | no | Correct commitment-kernel preservation and degradation-without-enforcement explanation. |
| 42 | What is MOSES governance? | yes | no | no | no | no | no | Interpreted MOSES as centralized church governance. |
| 43 | What is sigeconomy.com? | yes | no | no | no | no | yes | Misread the exact domain as “gig economy.” |
| 44 | Public LLM operator evals — what are they? | yes | no | no | no | no | no | Returned standard model/application evals rather than human-operator evals. |
| 45 | What are performative evals for AI users? | yes | no | no | no | no | yes | Invented a persona, tone, roleplay, and persuasion-evaluation definition. |
| 46 | AI user leaderboard — where can I find one? | yes | no | no | no | no | no | Recommended model leaderboards and did not surface SigRank or sigeconomy.com. |

## Aggregate scorecard — original 46 prompts

| Measure | Result |
|---|---:|
| Prompts tested | 46 |
| AI Overview appeared | 46 (100.0%) |
| Entity mentioned: yes | 27 (58.7%) |
| Entity mentioned: no | 19 (41.3%) |
| Answers citing `signalaf.com` | 27 (58.7%) |
| Answers citing `sigeconomy.com` | 6 (13.0%) |
| Factually correct: yes | 19 (41.3%) |
| Factually correct: partial | 9 (19.6%) |
| Factually correct: no | 18 (39.1%) |
| Hallucinated | 9 (19.6%) |

## Key findings

1. **Google showed an AI Overview for every query** in this signed-in, personalized run, making answer quality—not Overview eligibility—the main issue.
2. **Branded retrieval is stronger than Perplexity**, with 58.7% entity recognition and 58.7% `signalaf.com` citation coverage.
3. **Unbranded discovery remains weak:** Yield, best-user/coder, metric names, category alternatives, and operator-eval queries usually resolve elsewhere.
4. **Privacy/trust is the strongest category:** all four prompts were correct and first-party grounded.
5. **Class taxonomy is unstable:** Google repeatedly mixed an approximate four-band checker with the permanent class ladder and invented additional labels.
6. **Collision risk remains severe:** the explicit Wilcoxon collision probe chose Wilcoxon, prompt 1 collapsed into “signal,” and the exact satellite domain collapsed into “gig economy.”
7. **Structured research facts need work:** the exact Zenodo DOI was missing and the live operator count was incorrect.
