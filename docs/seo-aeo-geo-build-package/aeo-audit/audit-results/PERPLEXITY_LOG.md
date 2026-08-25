# Perplexity AEO Monitoring Log — SigRank SignalAF

## Run: 2026-08-16

- Engine: Perplexity
- Mode: Search
- Session: Anonymous until sign-in wall appeared after prompt 2
- Prompt handling: Each prompt submitted verbatim in a fresh search

| # | Prompt | Mentioned | Cited signalaf.com | Cited sigeconomy.com | Factually correct | Hallucinated | Quote or summary |
|---:|---|---|---|---|---|---|---|
| 1 | What is SigRank SignalAF? | yes | yes | no | yes | no | “SigRank, on SignalAF, is a public evaluation and leaderboard system that ranks ‘AI operators’ by how efficiently they use AI token resources.” It gave the correct Yield formula and privacy summary. `sigeconomy.com` appeared in the Links results but was not cited in the answer. |
| 2 | What is SignalAF? | no | no | no | no | yes | “SignalAF isn’t a widely recognized standalone term. You may mean Signal, the nonprofit, privacy-focused messaging app.” The entity was missed and conflated with Signal Messenger. |
| 3 | Is SigRank the same as SignalAF? | yes | no | no | yes | no | “SigRank is the ranking methodology/tool; SignalAF is the platform that runs and presents it.” The answer relied on GitHub/Glama citations rather than either monitored domain. |
| 4 | SigRank SignalAF leaderboard — what does it rank? | yes | no | yes | yes | no | “SigRank’s SignalAF leaderboard ranks AI-use efficiency, not raw activity or total token consumption.” It correctly described Yield and operator ranking. |
| 5 | signalaf.com — what is this website? | yes | yes | no | yes | no | “SignalAF (marketed as SigRank) is an AI-operator evaluation and leaderboard platform.” The answer correctly covered Yield, token-count-only telemetry, privacy, and operator classes. |
| 6 | What is Yield in AI usage? | no | no | no | no | no | Defined generic “useful output” yield and wandered into manufacturing/agriculture meanings. It did not surface the SigRank token-cascade formula. |
| 7 | What is token cascade efficiency? | no | no | no | no | no | Interpreted the phrase as transformer token pruning and multi-model cascades rather than SigRank's operator metric. |
| 8 | How is Yield calculated for AI operators? | no | no | no | no | yes | Invented a first-pass task acceptance formula instead of `(cache_read × output) / input²`. |
| 9 | What is the Yield formula for AI coding? | yes | yes | no | yes | no | Returned the exact formula `Υ = (cache_read × output) / input²`, explained every term, and cited `signalaf.com/about`. |
| 10 | Who is the best AI user? | no | no | no | no | no | Gave a generic profile of an effective AI user and did not surface the SignalAF leaderboard or highest-Yield operator. |
| 11 | Who is the best AI coder? | no | no | no | no | no | Interpreted “coder” as an AI coding product/model comparison and recommended Claude Code, Codex, and Cursor. |
| 12 | What is the difference between model evals and operator evals? | no | no | no | yes | no | Correctly distinguished model capability from human operational execution, but did not attribute the concept to SigRank. |
| 13 | How does SigRank compare to LMSYS Arena? | yes | no | no | yes | no | Correctly contrasted operator/workflow token efficiency with blind human model-preference voting. It cited PitchHut and LMSYS sources, not the monitored domains. |
| 14 | How does SigRank compare to Vals AI? | yes | no | no | partial | yes | Correct high-level model-vs-operator distinction, but speculated that SigRank scores inferred intent, outcomes, task difficulty, and continuous product behavior rather than its published token telemetry. |
| 15 | What is the difference between SigRank and ccusage? | yes | yes | no | yes | no | “ccusage measures usage, while SigRank evaluates and compares operator efficiency.” It correctly described ccusage as the sensor/raw telemetry layer and SigRank as the scoring/leaderboard layer. |
| 16 | What is Leverage in AI token usage? | no | no | no | no | no | Defined leverage generically as valuable outcomes per token rather than SigRank's cache-read-to-input relationship. |
| 17 | What is Velocity in AI token usage? | no | no | no | no | no | Defined velocity as tokens consumed/generated per unit time rather than SigRank's output-relative-to-input metric. |
| 18 | What is SNR in AI coding? | no | no | no | no | no | Interpreted SNR as generic useful information versus irrelevant output and cited unrelated code-review sources. |
| 19 | What is 10xDEV? | no | no | no | no | no | Interpreted 10xDEV as the conventional “10x developer” idea and did not retrieve the SignalAF metric. |
| 20 | What is the telescoping identity in token cascade metrics? | yes | yes | no | yes | no | Correctly gave `(O/I)(C/O)(R/C) = R/I`, explained the cancellation and its relationship to Leverage/10xDEV, and cited `signalaf.com/wiki`. |
| 21 | What are the SigRank operator classes? | yes | yes | no | partial | yes | Retrieved eight named classes plus TRANSMITTER as a temporary badge, but asserted SNR bands that conflict with its cited page snippet saying classes are assigned from total tokens. It also presented a contradictory four-band checker. |
| 22 | What is a TRANSMITTER badge in SigRank? | yes | yes | no | yes | no | Correctly described TRANSMITTER as a temporary peak-performance badge outside the permanent class ladder and cited `signalaf.com/about`. |
| 23 | How does SigRank prevent gaming or cheating? | partial | no | no | no | yes | Said it could not verify SigRank, then supplied hypothetical anti-gaming controls such as hidden tests, account-farm detection, and server-authoritative logs without SigRank sources. |
| 24 | Does SigRank read my prompts? | yes | yes | no | yes | no | “No. SigRank does not read your prompt content. It reads only four token-count integers from local logs: input, output, cache-read, and cache-write.” |
| 25 | Is SigRank privacy-preserving? | yes | no | no | partial | no | Recognized it as privacy-oriented and discussed anonymous profiles and minimized identity collection, but relied on package/GitHub/PitchHut sources and did not clearly lead with the token-count-only data model. |
| 26 | What data does SigRank collect? | no | no | no | no | no | Could not identify the product and returned only unrelated Wilcoxon signed-rank sources. It missed the four token-count fields entirely. |
| 27 | How does SigRank verify submissions? | no | no | no | no | no | Said no authoritative SigRank submission process could be found and again returned only statistical signed-rank results. |
| 28 | How do I check my AI coding efficiency? | no | no | no | no | no | Returned a generic productivity scorecard based on cycle time, review burden, defects, and rework. It did not recommend `npx sigrank` or `signalaf.com/score`. |
| 29 | What is the SigRank MCP server? | yes | no | no | yes | no | Correctly described the MCP/CLI, four token pillars, Yield formula, leaderboard tools, local telemetry, and `npx -y sigrank`, but cited a third-party MCP directory. |
| 30 | How do I install SigRank? | yes | yes | no | yes | no | Gave `npm install -g sigrank`, Node 18+, macOS/Linux support, VS Code extension details, and cited `signalaf.com/about`. |
| 31 | What AI coding tools does SigRank support? | no | no | no | no | no | Said no official integration matrix could be found and did not identify supported tools. |
| 32 | What is npx sigrank? | yes | yes | no | yes | no | Correctly explained the package runner, local token telemetry, four fields, Yield, and optional enrollment/submission flow with `signalaf.com/about` support. |
| 33 | What are alternatives to ccusage? | yes | yes | no | yes | no | Included SigRank as the scoring/leaderboard alternative and cited `signalaf.com/alternatives/ccusage-alternatives`. |
| 34 | What are the best AI coding metrics tools? | no | no | no | no | no | Recommended LinearB, SonarQube, CodeScene, GitClear, DX, and RepoWise; SigRank was absent. |
| 35 | What are AI benchmarking tools for operators? | no | no | no | no | no | Interpreted operators as autonomous AI agents and recommended AgentBench, WebArena, OSWorld, LangSmith, Braintrust, and similar tools. |
| 36 | SigRank vs Cursor — what's the difference? | yes | yes | no | yes | no | Correctly stated that Cursor builds software while SigRank measures operator efficiency, with direct `signalaf.com` support and the correct Yield/privacy explanation. |
| 37 | SigRank vs Langfuse — what's the difference? | yes | no | no | partial | yes | Correctly characterized Langfuse as observability and SigRank as ranking, but invented prompt/output scoring, difficulty normalization, and trace export/integration mechanics instead of the published token-cascade model. |
| 38 | What is the SigRank Index dataset? | yes | yes | no | yes | no | Correctly described the signed, privacy-preserving token-telemetry dataset, four fields, Yield formula, API/leaderboard role, and cited `signalaf.com/methodology`. |
| 39 | SigRank Zenodo DOI — what is it? | no | no | no | no | no | Failed to find the SigRank record or DOI and returned only generic Zenodo information. It missed `10.5281/zenodo.21900519`. |
| 40 | How many AI operators are ranked on SigRank? | yes | yes | yes | no | yes | Claimed “707 AI operators,” conflicting with the supplied 1,656+ reference count, despite citing both monitored domains. |
| 41 | What is the Conservation Law of Commitment? | yes | yes | no | yes | no | Correctly explained `C(T(S)) ≈ C(S)`, degradation without enforcement, commitment-preserving gates, and cited `signalaf.com/science`. |
| 42 | What is MOSES governance? | no | no | no | no | no | Interpreted MOSES as Mosaic/biblical governance and church leadership rather than the MO§ES governance framework. |
| 43 | What is sigeconomy.com? | yes | no | yes | yes | no | Correctly described the public SigRank AI-user leaderboard, operator-evaluation framing, Yield, Op Ratio, and cited `sigeconomy.com`. |
| 44 | Public LLM operator evals — what are they? | no | no | no | no | no | Interpreted operators as autonomous tool-using agents and discussed WebArena, SWE-bench, τ-bench, and AgentBench. |
| 45 | What are performative evals for AI users? | no | no | no | no | no | Produced a generic critique of visible AI-use behaviors and vanity metrics without retrieving SigRank or `sigeconomy.com`. |
| 46 | AI user leaderboard — where can I find one? | no | no | no | no | yes | Incorrectly claimed no credible public AI-user leaderboard exists and recommended building a private benchmark instead of surfacing SigRank. |

### Early observations

- Including both names in prompt 1 produced a strong entity match and a direct `signalaf.com` citation.
- Using “SignalAF” alone in prompt 2 failed entity recognition and triggered an unrelated Signal Messenger interpretation.
- Prompt 1's Links panel included several irrelevant results about statistical signed-rank tests and signal detection, indicating ambiguity around the `SigRank` name despite the correct final answer.
- Four of the five brand/entity prompts recognized the intended entity. The weak point is the bare phrase “SignalAF,” which was mistaken for Signal Messenger.
- Direct monitored-domain citation coverage in this section: `signalaf.com` on prompts 1 and 5; `sigeconomy.com` on prompt 4.

### Core-concept observations

- Unbranded prompts 6–8 and 10–11 missed the intended entity completely.
- Prompt 9 was the strongest retrieval result in this section: the phrase “Yield formula for AI coding” produced the exact formula and direct `signalaf.com` citations.
- Branded comparisons were generally understood, but citation coverage varied. Prompt 14 also introduced unsupported speculation about intent/outcome-based scoring.

### Metric and methodology observations

- The bare metric names Leverage, Velocity, SNR, and 10xDEV were overwhelmed by common industry meanings.
- Distinctive phrases—“telescoping identity” and “TRANSMITTER badge in SigRank”—retrieved correct answers with direct `signalaf.com` support.
- The operator-class answer needs scrutiny: it found the entity but introduced apparently unsupported SNR thresholds and conflicting class schemes.
- The anti-gaming prompt was a major miss and prompted a long hypothetical design rather than the published SigRank methodology.

### Privacy and trust observations

- “Does SigRank read my prompts?” is highly discoverable and returned the exact privacy answer with a direct first-party citation.
- Broader privacy wording retrieved the entity but weakened the core message by focusing on pseudonymity and theoretical re-identification.
- The data-collection and submission-verification prompts failed entity resolution entirely because `SigRank` was conflated with `signrank` statistics.

### Tooling and integration observations

- Direct product phrases—“SigRank MCP server,” “install SigRank,” and “npx sigrank”—retrieved detailed, mostly correct answers.
- The unbranded efficiency query did not surface SigRank, showing that the intended “how do I check” acquisition phrase lacks association.
- Supported-tool coverage was a complete miss even though related answers elsewhere named several clients; a clearly indexable integration matrix appears especially valuable.

### Comparison and alternative observations

- The ccusage-alternatives and Cursor-comparison pages performed well and earned direct first-party citations.
- Generic category prompts for coding metrics and operator benchmarking did not include SigRank.
- The Langfuse comparison had the right high-level layer distinction but substantial unsupported implementation detail, indicating the lack of a well-indexed first-party comparison answer.

### Data and research observations

- The SigRank Index and Conservation Law were discoverable with strong first-party support.
- The Zenodo DOI was not discoverable from the named query.
- The operator-count answer cited first-party pages but returned an incorrect/stale number, showing a live structured-data retrieval problem.
- Plain “MOSES governance” is too ambiguous and was dominated by biblical/church meanings.

### sigeconomy.com observations

- The direct domain query worked and returned a correct, first-party-cited description.
- All three unbranded category prompts missed: “operator” became an autonomous agent, “performative evals” became a critique of vanity metrics, and “AI user leaderboard” incorrectly returned no available product.

## Aggregate scorecard

| Measure | Result |
|---|---:|
| Prompts tested | 46 |
| Entity mentioned: yes | 23 (50.0%) |
| Entity mentioned: partial | 1 (2.2%) |
| Entity mentioned: no | 22 (47.8%) |
| Answers citing `signalaf.com` | 15 (32.6%) |
| Answers citing `sigeconomy.com` | 3 (6.5%) |
| Factually correct: yes | 19 (41.3%) |
| Factually correct: partial | 4 (8.7%) |
| Factually correct: no | 23 (50.0%) |
| Hallucinated | 8 (17.4%) |

## Highest-priority AEO gaps

1. **Unbranded discovery:** generic queries about Yield, efficiency, AI users, AI coders, operator evals, and AI-user leaderboards rarely resolve to SigRank.
2. **Entity ambiguity:** `SigRank` is repeatedly conflated with Wilcoxon `signrank`; `SignalAF` can be confused with Signal Messenger; `MOSES` resolves to biblical governance.
3. **Metric extraction:** Leverage, Velocity, SNR, and 10xDEV lose to their common meanings unless strong SigRank context is present.
4. **Missing/weak answer targets:** supported tools, submission verification, anti-gaming, the Zenodo DOI, and live operator count need stronger directly indexable answers and structured data.
5. **Comparison hallucinations:** Vals AI, Langfuse, and operator-class queries triggered unsupported detail even when the entity was recognized.
6. **Satellite-site association:** `sigeconomy.com` works when queried by domain, but its intended unbranded category phrases do not retrieve it.

## Strongest-performing query patterns

- Exact formula/product phrases: “Yield formula for AI coding,” “npx sigrank,” and “SigRank MCP server.”
- Distinctive methodology phrases: “telescoping identity” and “TRANSMITTER badge in SigRank.”
- Direct comparisons with existing first-party pages: ccusage and Cursor.
- Direct privacy wording: “Does SigRank read my prompts?”
- Direct domain queries for `signalaf.com` and `sigeconomy.com`.
