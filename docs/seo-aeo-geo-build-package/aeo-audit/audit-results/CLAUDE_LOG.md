# Claude AEO Log — SigRank SignalAF

## Run metadata

- Dates: 2026-08-16 and 2026-08-17
- Engine/mode: Claude / Sonnet 5 Medium
- Signed in: yes
- Incognito: yes; account memory and chat history disabled
- Web search: enabled and verified before every retained prompt
- Fresh-chat handling: exited to `/new` and re-entered incognito before every retained prompt
- Calibration probes completed: 4 of 4
- Original panel completed: 46 of 46
- Raw evidence: [CLAUDE_RAW.md](CLAUDE_RAW.md)
- Scoring note: judgments are intentionally separate from the unabridged evidence and can be rescored later.

## Calibration probes

| ID | Exact prompt | Answer | Mentioned | Cited signalaf.com | Cited sigeconomy.com | Factually correct | Hallucinated | Summary |
|---|---|---|---|---|---|---|---|---|
| P1 | What is SigRank’s Yield formula? | yes | no | no | no | no | no | Searched but failed to find SigRank or the Yield formula. |
| P2 | How is Yield calculated for AI operators? | yes | no | no | no | no | no | Asked for clarification and did not surface the SigRank metric. |
| P3 | Is this the Wilcoxon signed-rank test or SigRank SignalAF? | yes | no | no | no | partial | yes | Correctly explained Wilcoxon but called SigRank SignalAF potentially made-up. |
| P4 | How do SigRank, SignalAF, and sigeconomy.com relate? | yes | yes | yes | yes | yes | no | Correctly mapped the brand, scoring system/CLI, and public leaderboard site. |

## Original 46-prompt panel

| # | Exact prompt | Answer | Mentioned | Cited signalaf.com | Cited sigeconomy.com | Factually correct | Hallucinated | Summary |
|---:|---|---|---|---|---|---|---|---|
| 1 | What is SigRank SignalAF? | yes | yes | yes | no | partial | yes | Correct core entity and formula, but invented a “Cascade Architect” classification and thresholds. |
| 2 | What is SignalAF? | yes | no | no | no | no | no | Failed to find SignalAF and returned unrelated Signal/AFCEA possibilities. |
| 3 | Is SigRank the same as SignalAF? | yes | no | no | no | no | no | Resolved SigRank to an unrelated bioinformatics tool and missed the product relationship. |
| 4 | SigRank SignalAF leaderboard — what does it rank? | yes | yes | yes | no | yes | no | Correctly described human-operator ranking, token telemetry, Yield, and profile classes. |
| 5 | signalaf.com — what is this website? | yes | yes | no | no | yes | no | Directly fetched the site and correctly described the operator-evaluation platform and privacy model. |
| 6 | What is Yield in AI usage? | yes | no | no | no | no | no | Returned generic programming, manufacturing, and output-quality meanings. |
| 7 | What is token cascade efficiency? | yes | no | no | no | no | no | Interpreted the phrase as transformer token pruning and routing. |
| 8 | How is Yield calculated for AI operators? | yes | no | no | no | no | no | Asked for domain clarification and did not identify SigRank. |
| 9 | What is the Yield formula for AI coding? | yes | no | no | no | no | no | Said no recognized formula exists and offered generic productivity metrics. |
| 10 | Who is the best AI user? | yes | no | no | no | no | no | Gave general advice and did not surface the operator leaderboard. |
| 11 | Who is the best AI coder? | yes | no | no | no | no | no | Ranked coding models rather than a human operator. |
| 12 | What is the difference between model evals and operator evals? | yes | no | no | no | no | no | Defined operator as a deploying company/product, not a human AI operator. |
| 13 | How does SigRank compare to LMSYS Arena? | yes | no | no | no | no | no | Failed to find SigRank and offered unrelated Sigrid/SibRank results. |
| 14 | How does SigRank compare to Vals AI? | yes | yes | yes | no | yes | no | Correct operator-efficiency versus model/domain-benchmark distinction. |
| 15 | What is the difference between SigRank and ccusage? | yes | yes | yes | no | yes | no | Correct raw usage reporting versus scoring/leaderboard distinction. |
| 16 | What is Leverage in AI token usage? | yes | no | no | no | no | no | Returned a generic accepted-output/capacity multiplier instead of cache_read/input. |
| 17 | What is Velocity in AI token usage? | yes | no | no | no | no | no | Defined token throughput and burn rate rather than output/input. |
| 18 | What is SNR in AI coding? | yes | no | no | no | no | no | Returned the generic signal-to-noise metaphor, not the SigRank metric. |
| 19 | What is 10xDEV? | yes | no | no | no | no | no | Resolved to unrelated companies, courses, and the generic 10x-developer idea. |
| 20 | What is the telescoping identity in token cascade metrics? | yes | yes | yes | no | no | no | Found SigRank but incorrectly said the telescoping identity was not defined. |
| 21 | What are the SigRank operator classes? | yes | yes | yes | no | yes | no | Correctly listed all eight classes, substages, volume basis, thresholds, and separate TRANSMITTER badge. |
| 22 | What is a TRANSMITTER badge in SigRank? | yes | no | no | no | no | no | Failed to find SigRank or the badge and returned unrelated patent results. |
| 23 | How does SigRank prevent gaming or cheating? | yes | no | no | no | no | no | Failed to identify the product or any anti-gaming mechanism. |
| 24 | Does SigRank read my prompts? | yes | no | no | no | no | no | Declined for lack of product knowledge and did not invoke web search. |
| 25 | Is SigRank privacy-preserving? | yes | yes | yes | no | yes | no | Correct token-count-only privacy, local scanning, signatures, and integer-only verification. |
| 26 | What data does SigRank collect? | yes | no | no | no | no | no | Failed to find the product and returned unrelated academic/patent material. |
| 27 | How does SigRank verify submissions? | yes | yes | yes | no | partial | yes | Recovered signing and plausibility checks but mixed in unsupported tokscale and profile-claim mechanics. |
| 28 | How do I check my AI coding efficiency? | yes | no | no | no | no | no | Asked what kind of efficiency the user meant and did not surface SigRank. |
| 29 | What is the SigRank MCP server? | yes | yes | yes | no | partial | yes | Correct MCP purpose, but treated TRANSMITTER as a permanent class and added an unrelated router. |
| 30 | How do I install SigRank? | yes | no | no | no | no | no | Web search ran but Claude said no matching tool could be found. |
| 31 | What AI coding tools does SigRank support? | yes | yes | yes | no | partial | yes | Found several platforms but added unsupported companion tools and conflated client compatibility with telemetry support. |
| 32 | What is npx sigrank? | yes | yes | yes | no | partial | yes | Correct package/CLI purpose, but made false ccusage and TRANSMITTER-class claims. |
| 33 | What are alternatives to ccusage? | yes | no | no | no | no | no | Listed monitoring alternatives but omitted SigRank. |
| 34 | What are the best AI coding metrics tools? | yes | no | no | no | no | no | Recommended engineering analytics and coding assistants; SigRank was absent. |
| 35 | What are AI benchmarking tools for operators? | yes | no | no | no | no | no | Interpreted operators as production AI teams and model/application eval platforms. |
| 36 | SigRank vs Cursor — what's the difference? | yes | yes | yes | no | yes | no | Correct editor versus operator-analytics layer distinction. |
| 37 | SigRank vs Langfuse — what's the difference? | yes | no | no | no | no | no | Failed to find SigRank and suggested SigNoz/SigScalr instead. |
| 38 | What is the SigRank Index dataset? | yes | no | no | no | no | no | Said the dataset did not exist and returned unrelated index results. |
| 39 | SigRank Zenodo DOI — what is it? | yes | no | no | no | no | no | Two search passes failed to find the exact DOI or any SigRank record. |
| 40 | How many AI operators are ranked on SigRank? | yes | no | no | no | no | no | Failed to identify SigRank and returned unrelated company/model leaderboards. |
| 41 | What is the Conservation Law of Commitment? | yes | no | no | no | no | no | Said the named principle was not established and missed the published framework. |
| 42 | What is MOSES governance? | yes | no | no | no | yes | no | Correctly explained MO§ES modes, postures, roles, vault, audit trail, stamping, and context assembly from installed skills. |
| 43 | What is sigeconomy.com? | yes | yes | no | yes | yes | no | Correctly identified the SigRank/SignalAF operator leaderboard, formula, metrics, and audience. |
| 44 | Public LLM operator evals — what are they? | yes | no | no | no | no | no | Interpreted operators as frontier-model companies publishing safety evaluations. |
| 45 | What are performative evals for AI users? | yes | no | no | no | partial | no | Reached evaluation of human AI-use behavior but framed performativity as observer/Goodhart effects and missed SigEconomy. |
| 46 | AI user leaderboard — where can I find one? | yes | no | no | no | no | no | Recommended model/popularity leaderboards and failed to surface SigRank or sigeconomy.com. |

## Aggregate scorecard — original 46 prompts

| Measure | Result |
|---|---:|
| Prompts tested | 46 |
| Claude answer generated | 46 (100.0%) |
| Answers with at least one captured URL | 36 (78.3%) |
| Entity mentioned: yes | 14 (30.4%) |
| Entity mentioned: no | 32 (69.6%) |
| Answers citing `signalaf.com` | 12 (26.1%) |
| Answers citing `sigeconomy.com` | 1 (2.2%) |
| Factually correct: yes | 9 (19.6%) |
| Factually correct: partial | 6 (13.0%) |
| Factually correct: no | 31 (67.4%) |
| Hallucinated | 5 (10.9%) |

## Key findings

1. Claude recognized SigRank or SignalAF in only 14 of 46 prompts (30.4%). Recognition was inconsistent even for exact branded queries: prompt 1 worked, while prompts 2–3, 13, 22–24, 26, 30, and 37–40 failed.
2. First-party citation performance was weak: 12 answers (26.1%) cited `signalaf.com`, and only the direct-domain prompt cited `sigeconomy.com`.
3. Citation volume was not a reliable quality signal. Claude captured at least one URL for 36 prompts (78.3%), but many failed searches returned large lists of unrelated patents, ranking algorithms, or generic eval resources.
4. The strongest answers were direct site/entity retrieval, named comparisons that found first-party pages, operator classes, privacy, Cursor comparison, MO§ES governance, and the direct `sigeconomy.com` query.
5. Unbranded discovery was very weak across Yield, token-cascade terminology, best-user/best-coder, Leverage, Velocity, SNR, 10xDEV, efficiency tools, ccusage alternatives, operator benchmarks, and AI-user leaderboard queries.
6. Data/research discoverability collapsed: Claude missed the SigRank Index, the exact Zenodo DOI, the live operator count, and the Conservation Law of Commitment in four consecutive prompts.
7. The main hallucination pattern was false taxonomy/integration detail—especially treating TRANSMITTER as a permanent class, inventing a Cascade Architect tier, and mixing SigRank with unrelated tooling or submission mechanics.
