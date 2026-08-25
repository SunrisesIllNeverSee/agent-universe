# ChatGPT Search AEO Log — SigRank SignalAF

## Run metadata

- Dates: 2026-08-16 and 2026-08-17
- Engine/mode: ChatGPT / Web search + High
- Signed in: yes
- Temporary Chat: yes; every retained prompt was submitted in a fresh Temporary Chat
- Original panel completed: 46 of 46
- Calibration probes completed: 4 of 4
- Raw evidence: [CHATGPT_SEARCH_RAW.md](CHATGPT_SEARCH_RAW.md)
- Scoring note: judgments are intentionally separate from the unabridged evidence and can be rescored later.

## Calibration probes

| ID | Exact prompt | Answer | Mentioned | Cited signalaf.com | Cited sigeconomy.com | Factually correct | Hallucinated | Summary |
|---|---|---|---|---|---|---|---|---|
| P1 | What is SigRank’s Yield formula? | yes | yes | no | no | yes | no | Gave the exact formula, variables, and equivalent Leverage × Velocity identity. |
| P2 | How is Yield calculated for AI operators? | yes | yes | yes | no | partial | yes | Gave the exact formula and a correct example, but invented operator score bands/classes. |
| P3 | Is this the Wilcoxon signed-rank test or SigRank SignalAF? | yes | yes | no | no | yes | no | Correctly disambiguated SigRank SignalAF from the Wilcoxon signed-rank test. |
| P4 | How do SigRank, SignalAF, and sigeconomy.com relate? | yes | yes | yes | yes | yes | no | Correctly described SigRank as the system, SignalAF as the main web property, and sigeconomy.com as a discovery/leaderboard site. |

## Original 46-prompt panel

| # | Exact prompt | Answer | Mentioned | Cited signalaf.com | Cited sigeconomy.com | Factually correct | Hallucinated | Summary |
|---:|---|---|---|---|---|---|---|---|
| 1 | What is SigRank SignalAF? | yes | yes | yes | no | yes | no | Correct operator-not-model definition, Yield formula, local CLI flow, and privacy framing. |
| 2 | What is SignalAF? | yes | yes | yes | no | yes | no | Correctly identified the SignalAF site/brand and operator-efficiency leaderboard. |
| 3 | Is SigRank the same as SignalAF? | yes | yes | no | no | yes | no | Correctly separated the SigRank instrument/scoring layer from the SignalAF leaderboard site. |
| 4 | SigRank SignalAF leaderboard — what does it rank? | yes | yes | yes | yes | partial | yes | Correctly said it ranks operators by Yield, but added unsupported Burner/Builder/10×er tiers. |
| 5 | signalaf.com — what is this website? | yes | yes | yes | no | yes | no | Correct site purpose, token telemetry, CLI participation, and content-privacy explanation. |
| 6 | What is Yield in AI usage? | yes | no | no | no | no | no | Resolved Yield to generic infrastructure/application efficiency and missed SigRank. |
| 7 | What is token cascade efficiency? | yes | yes | no | yes | yes | no | Found SigRank, gave the exact Yield formula, and explained context reuse versus fresh input. |
| 8 | How is Yield calculated for AI operators? | yes | yes | yes | no | yes | no | Exact formula, variables, worked example, and Leverage × Velocity identity. |
| 9 | What is the Yield formula for AI coding? | yes | yes | yes | no | yes | no | Exact SigRank formula with a correct worked example. |
| 10 | Who is the best AI user? | yes | no | no | no | no | no | Gave generic advice and did not surface the SigRank leaderboard. |
| 11 | Who is the best AI coder? | yes | no | no | no | no | no | Ranked coding models rather than a human AI operator. |
| 12 | What is the difference between model evals and operator evals? | yes | no | no | no | partial | no | Distinguished system-level action evals from model-output evals, but interpreted operator as a computer-use agent rather than a human operator. |
| 13 | How does SigRank compare to LMSYS Arena? | yes | yes | yes | no | yes | no | Correct operator/workflow efficiency versus model-preference distinction. |
| 14 | How does SigRank compare to Vals AI? | yes | yes | yes | no | yes | no | Correct operator telemetry versus controlled model/agent benchmark distinction. |
| 15 | What is the difference between SigRank and ccusage? | yes | yes | yes | no | yes | no | Correct usage-reporting versus scoring/leaderboard distinction. |
| 16 | What is Leverage in AI token usage? | yes | no | no | no | no | no | Returned a generic value-per-token concept and missed cache_read/input. |
| 17 | What is Velocity in AI token usage? | yes | no | no | no | no | no | Defined token consumption rate over time instead of output/input. |
| 18 | What is SNR in AI coding? | yes | no | no | no | no | no | Returned the generic signal-to-noise metaphor rather than the SigRank metric. |
| 19 | What is 10xDEV? | yes | no | no | no | no | no | Resolved to an unrelated software company and the generic 10x-developer idea. |
| 20 | What is the telescoping identity in token cascade metrics? | yes | yes | yes | no | yes | no | Correctly gave the three-factor cancellation, Leverage identity, and internal-consistency lock. |
| 21 | What are the SigRank operator classes? | yes | yes | no | no | yes | no | Correctly listed all eight classes, three substages each, and separated TRANSMITTER from permanent classes. |
| 22 | What is a TRANSMITTER badge in SigRank? | yes | yes | yes | no | yes | no | Correctly described a temporary peak-performance badge rather than a permanent class. |
| 23 | How does SigRank prevent gaming or cheating? | yes | yes | no | no | yes | no | Detailed signed submissions, server rescoring, plausibility gates, replay controls, attestation, and limitations. |
| 24 | Does SigRank read my prompts? | yes | yes | no | no | yes | no | Correctly said ordinary use does not upload prompt text and distinguished the optional proxy path. |
| 25 | Is SigRank privacy-preserving? | yes | yes | no | no | yes | no | Correct content-minimization answer with appropriate qualifications about linkability and telemetry. |
| 26 | What data does SigRank collect? | yes | yes | yes | no | partial | no | Correctly excluded prompts/code and covered account/device data, but broadened local telemetry beyond the canonical four-pillar summary. |
| 27 | How does SigRank verify submissions? | yes | yes | no | no | yes | no | Correct enrollment, Ed25519 signing, integrity gates, attestation, server rescoring, and trust-boundary caveat. |
| 28 | How do I check my AI coding efficiency? | yes | no | no | no | no | no | Supplied a generic productivity scorecard and missed `npx sigrank` and the score page. |
| 29 | What is the SigRank MCP server? | yes | yes | no | no | yes | no | Correct operator-efficiency MCP, formula, privacy, telemetry, and leaderboard workflow. |
| 30 | How do I install SigRank? | yes | yes | no | no | yes | no | Correct Node requirement plus global npm and `npx sigrank` installation paths. |
| 31 | What AI coding tools does SigRank support? | yes | yes | yes | no | yes | no | Detailed current adapters and correctly distinguished MCP-client compatibility from native telemetry support. |
| 32 | What is npx sigrank? | yes | yes | no | no | yes | no | Correctly described the package runner, local telemetry, enrollment, and submission commands. |
| 33 | What are alternatives to ccusage? | yes | no | no | no | no | no | Listed other usage monitors but failed to surface SigRank. |
| 34 | What are the best AI coding metrics tools? | yes | no | no | no | no | no | Recommended enterprise engineering-analytics products; SigRank was absent. |
| 35 | What are AI benchmarking tools for operators? | yes | no | no | no | no | no | Interpreted operators as AI application operators and missed human-operator benchmarking. |
| 36 | SigRank vs Cursor — what's the difference? | yes | yes | yes | no | yes | no | Correct editor/agent versus platform-neutral operator-analytics distinction. |
| 37 | SigRank vs Langfuse — what's the difference? | yes | yes | yes | yes | yes | no | Correct operator leaderboard versus application observability/evals distinction. |
| 38 | What is the SigRank Index dataset? | yes | yes | yes | no | partial | no | Correct dataset purpose, telemetry, Yield, and licensing; the dated operator count did not match the supplied reference. |
| 39 | SigRank Zenodo DOI — what is it? | yes | yes | yes | no | yes | no | Returned the exact expected dataset DOI and distinguished the concept and foundational-law DOIs. |
| 40 | How many AI operators are ranked on SigRank? | yes | yes | yes | yes | partial | no | Surfaced SigRank but reported conflicting live counts of about 1,700 and 1,642. |
| 41 | What is the Conservation Law of Commitment? | yes | no | no | no | yes | no | Correct commitment-preservation principle, degradation condition, example, and research-status caveat. |
| 42 | What is MOSES governance? | yes | no | no | no | yes | no | Correctly identified the MO§ES constitutional AI-governance framework and its modes, postures, roles, and audit trail. |
| 43 | What is sigeconomy.com? | yes | yes | no | yes | partial | no | Correctly identified the SigRank operator leaderboard and formula, but its live statistics conflicted with other answers in the run. |
| 44 | Public LLM operator evals — what are they? | yes | no | no | no | no | no | Interpreted operator evals as public browser/desktop-agent benchmarks rather than public human-operator evals. |
| 45 | What are performative evals for AI users? | yes | no | no | no | no | no | Defined realistic task-based evaluation of AI assistance, not performative evaluation of the AI user. |
| 46 | AI user leaderboard — where can I find one? | yes | yes | no | yes | yes | no | Surfaced SigRank first, cited sigeconomy.com, and recommended it for personal operator ranking. |

## Aggregate scorecard — original 46 prompts

| Measure | Result |
|---|---:|
| Prompts tested | 46 |
| ChatGPT answer generated | 46 (100.0%) |
| Answers with at least one citation URL | 42 (91.3%) |
| Entity mentioned: yes | 30 (65.2%) |
| Entity mentioned: no | 16 (34.8%) |
| Answers citing `signalaf.com` | 18 (39.1%) |
| Answers citing `sigeconomy.com` | 6 (13.0%) |
| Factually correct: yes | 27 (58.7%) |
| Factually correct: partial | 6 (13.0%) |
| Factually correct: no | 13 (28.3%) |
| Hallucinated | 1 (2.2%) |

## Key findings

1. ChatGPT recognized SigRank or SignalAF in 30 of 46 prompts (65.2%) and cited `signalaf.com` in 18 (39.1%), making first-party grounding materially stronger than raw entity recognition alone.
2. Branded entity, formula, privacy, installation, MCP, and named comparison prompts were the strongest cluster. Prompts 1–5, 8–9, 13–15, 20–27, 29–32, and 36–39 generally resolved correctly.
3. Unbranded discovery remains the main weakness. ChatGPT missed SigRank for generic Yield, best-user/best-coder, Leverage, Velocity, SNR, 10xDEV, efficiency-check, ccusage-alternative, metrics-tool, and operator-eval queries.
4. `sigeconomy.com` appeared in 6 answers (13.0%), including the successful final discovery prompt. It also appeared in the token-cascade, leaderboard, Langfuse-comparison, operator-count, and direct-domain answers.
5. Live numerical claims were inconsistent. Prompts 38, 40, and 43 reported different operator totals or site statistics, so those answers were scored partial even when source-linked.
6. Citation coverage was high at 91.3%, while explicit hallucination was low at 2.2%. The clearest unsupported invention was the Burner/Builder/10×er tier system in prompt 4; the calibration probe P2 also invented score bands.
7. The closing discovery prompt was a meaningful win: ChatGPT named SigRank first and pointed users to `sigeconomy.com` when asked where to find an AI-user leaderboard.
