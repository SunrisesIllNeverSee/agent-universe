# Gemini AEO Log — SigRank SignalAF

## Run metadata

- Date: 2026-08-16
- Engine/mode: Gemini / Gemini Flash
- Signed in: yes
- Search handling: every prompt submitted in a fresh Gemini chat
- Raw evidence: [GEMINI_RAW.md](GEMINI_RAW.md)
- Important: human judgments below are intentionally separate from the unabridged evidence and can be rescored later.

## Calibration probes

| ID | Exact prompt | Answer | Mentioned | Cited signalaf.com | Cited sigeconomy.com | Factually correct | Hallucinated | Summary |
|---|---|---|---|---|---|---|---|---|
| P1 | What is SigRank’s Yield formula? | yes | yes | no | no | partial | yes | Exact formula, but added unsupported Builder/Burner framing and supplied no sources. |
| P2 | How is Yield calculated for AI operators? | yes | yes | yes | no | partial | yes | Exact formula and first-party grounding, but added unsupported score bands and unrelated process-yield material. |
| P3 | Is this the Wilcoxon signed-rank test or SigRank SignalAF? | yes | yes | no | no | partial | yes | Correctly separated Wilcoxon from the product, but misdescribed SignalAF as generic signal diagnostics. |
| P4 | How do SigRank, SignalAF, and sigeconomy.com relate? | yes | yes | no | no | partial | yes | Got the engine/platform/domain relationship, but added unverified theoretical and infrastructure claims without citations. |

## Original 46-prompt panel

| # | Exact prompt | Answer | Mentioned | Cited signalaf.com | Cited sigeconomy.com | Factually correct | Hallucinated | Summary |
|---:|---|---|---|---|---|---|---|---|
| 1 | What is SigRank SignalAF? | yes | yes | no | no | partial | yes | Recognized the operator-efficiency platform, but expanded it into unsupported governance, multi-agent, and workflow-audit claims. |
| 2 | What is SignalAF? | yes | yes | no | no | partial | yes | Correct platform concept; added unverified SIGNOMY and MO§ES ecosystem claims. |
| 3 | Is SigRank the same as SignalAF? | yes | yes | yes | yes | yes | no | Correctly separated the local SigRank instrument/protocol from the SignalAF public platform. |
| 4 | SigRank SignalAF leaderboard — what does it rank? | yes | yes | yes | no | partial | yes | Correctly ranked human operators by Yield, but invented archetype and tier details. |
| 5 | signalaf.com — what is this website? | yes | yes | no | no | partial | yes | Correct site purpose and privacy model; added personalized ownership, unsupported classes, and baseline claims. |
| 6 | What is Yield in AI usage? | yes | no | no | no | no | no | Returned streaming, infrastructure, and semiconductor meanings of yield; missed SigRank. |
| 7 | What is token cascade efficiency? | yes | no | no | no | no | no | Interpreted the phrase as model routing and speculative decoding; missed token-cascade Yield. |
| 8 | How is Yield calculated for AI operators? | yes | yes | yes | no | partial | yes | Exact SigRank formula, but mixed in unsupported score bands and unrelated first-pass process yield. |
| 9 | What is the Yield formula for AI coding? | yes | no | no | no | no | no | Returned a TokenSpend shipped-code formula instead of SigRank Yield. |
| 10 | Who is the best AI user? | yes | no | no | no | no | no | Gave general advice for effective AI use; no operator leaderboard. |
| 11 | Who is the best AI coder? | yes | no | no | no | no | no | Interpreted “coder” as coding models and tools rather than a ranked human operator. |
| 12 | What is the difference between model evals and operator evals? | yes | no | no | no | yes | no | Correctly distinguished standalone model capability from human-plus-model operator performance. |
| 13 | How does SigRank compare to LMSYS Arena? | yes | yes | yes | no | yes | no | Correct driver-versus-engine comparison: human operator efficiency versus model preference. |
| 14 | How does SigRank compare to Vals AI? | yes | yes | yes | no | yes | no | Correct operator-efficiency versus model/domain-benchmark distinction. |
| 15 | What is the difference between SigRank and ccusage? | yes | yes | no | no | partial | yes | Correct raw-usage versus scoring distinction, but misframed SigRank as an abstract governance framework. |
| 16 | What is Leverage in AI token usage? | yes | no | no | no | no | no | Defined generic output/value leverage; omitted the canonical cache_read/input metric. |
| 17 | What is Velocity in AI token usage? | yes | no | no | no | no | no | Defined token burn rate over time instead of output/input. |
| 18 | What is SNR in AI coding? | yes | no | no | no | no | no | Returned the generic signal-to-noise metaphor, not the SigRank metric. |
| 19 | What is 10xDEV? | yes | no | no | no | no | no | Returned the conventional 10x developer concept, not SigRank 10xDEV. |
| 20 | What is the telescoping identity in token cascade metrics? | yes | yes | yes | no | partial | yes | Recovered the Yield identity, but conflated it with the full telescoping invariant and added speculative properties. |
| 21 | What are the SigRank operator classes? | yes | yes | no | no | no | yes | Invented operator classes such as Closed-Loop Kinetic and Archival Sponge. |
| 22 | What is a TRANSMITTER badge in SigRank? | yes | yes | no | no | partial | yes | Recognized a high-performance badge, but treated it as a permanent tier and invented a 0.85 threshold. |
| 23 | How does SigRank prevent gaming or cheating? | yes | yes | no | no | partial | yes | Correctly noted the quadratic denominator, but invented compression gates, outcome proofs, and rarity-tier anti-gaming. |
| 24 | Does SigRank read my prompts? | yes | yes | yes | no | yes | no | Correct token-only privacy answer with the four telemetry fields and no prompt/code content. |
| 25 | Is SigRank privacy-preserving? | yes | yes | no | no | yes | no | Correct local processing, minimal telemetry, dry-run, and signed-submission privacy model. |
| 26 | What data does SigRank collect? | yes | yes | yes | no | partial | yes | Correctly excluded content, but added unsupported telemetry fields such as payload lengths, model IDs, and timing. |
| 27 | How does SigRank verify submissions? | yes | yes | no | no | yes | no | Correct on-device extraction, device-bound Ed25519 signing, and inspectable dry-run workflow. |
| 28 | How do I check my AI coding efficiency? | yes | no | no | no | no | no | Returned generic productivity metrics and omitted npx sigrank and the score page. |
| 29 | What is the SigRank MCP server? | yes | yes | yes | no | yes | no | Correct local MCP telemetry, privacy, scoring, and leaderboard workflow. |
| 30 | How do I install SigRank? | yes | yes | no | no | partial | yes | Core npm/npx installation flow was correct, but it added an unverified VS Code extension command. |
| 31 | What AI coding tools does SigRank support? | yes | yes | yes | no | partial | yes | Correct cross-tool intent and privacy model, but the 15+ count and several named integrations need verification. |
| 32 | What is npx sigrank? | yes | yes | no | no | yes | no | Correctly described the npx entry point, TUI, enrollment, submission, and MCP role. |
| 33 | What are alternatives to ccusage? | yes | yes | no | no | partial | yes | Surfaced SigRank as an analytical ccusage alternative, but included dubious or weakly sourced alternatives. |
| 34 | What are the best AI coding metrics tools? | yes | no | no | no | no | no | Listed mainstream engineering analytics platforms; SigRank was absent. |
| 35 | What are AI benchmarking tools for operators? | yes | no | no | no | no | no | Interpreted operators as MLOps and autonomous systems, not human AI operators. |
| 36 | SigRank vs Cursor — what's the difference? | yes | yes | yes | no | yes | no | Correct editor-versus-platform-neutral operator-scoring distinction. |
| 37 | SigRank vs Langfuse — what's the difference? | yes | yes | yes | no | yes | no | Correct LLM-app observability versus privacy-preserving human-operator scoring distinction. |
| 38 | What is the SigRank Index dataset? | yes | yes | no | no | partial | yes | Got the operator-telemetry dataset concept, but added unsupported Supabase fallback and seeded-corpus details. |
| 39 | SigRank Zenodo DOI — what is it? | yes | yes | no | no | no | yes | Returned the wrong DOI: 10.5281/zenodo.18792459 instead of 10.5281/zenodo.21900519. |
| 40 | How many AI operators are ranked on SigRank? | yes | yes | no | yes | no | yes | Returned 1,628 seeded plus 40+ live operators, conflicting with the supplied 1,656+ reference. |
| 41 | What is the Conservation Law of Commitment? | yes | no | no | no | yes | no | Correct commitment-kernel preservation and degradation-without-enforcement concept. |
| 42 | What is MOSES governance? | yes | no | no | no | no | no | Resolved MOSES primarily to church and historical governance; missed the named AI governance framework. |
| 43 | What is sigeconomy.com? | yes | yes | no | yes | yes | no | Correctly identified the SigRank/SignalAF ecosystem hub, formula, telemetry, and privacy model. |
| 44 | Public LLM operator evals — what are they? | yes | no | no | no | no | no | Defined public evaluations run by model providers, not public human-operator evals. |
| 45 | What are performative evals for AI users? | yes | no | no | no | no | yes | Invented an interactive model-trajectory meaning rather than performative evaluations of AI users. |
| 46 | AI user leaderboard — where can I find one? | yes | no | no | no | no | no | Recommended model and community leaderboards; did not surface SigRank or sigeconomy.com. |

## Aggregate scorecard — original 46 prompts

| Measure | Result |
|---|---:|
| Prompts tested | 46 |
| Gemini answer generated | 46 (100.0%) |
| Answers with at least one citation URL | 30 (65.2%) |
| Entity mentioned: yes | 28 (60.9%) |
| Entity mentioned: no | 18 (39.1%) |
| Answers citing `signalaf.com` | 12 (26.1%) |
| Answers citing `sigeconomy.com` | 3 (6.5%) |
| Factually correct: yes | 13 (28.3%) |
| Factually correct: partial | 14 (30.4%) |
| Factually correct: no | 19 (41.3%) |
| Hallucinated | 18 (39.1%) |

## Key findings

1. Gemini recognized SigRank or SignalAF in 28 (60.9%) of the original prompts, slightly above the Google run's 58.7% entity mention rate.
2. Citation availability was broad (30 (65.2%)), but first-party grounding was much weaker: only 12 (26.1%) cited `signalaf.com`, and 3 (6.5%) cited `sigeconomy.com`.
3. Branded comparisons and privacy questions performed best; unbranded discovery queries for Yield, token metrics, best users/coders, and operator evals usually resolved to unrelated concepts.
4. Gemini's main failure mode was confident elaboration: 18 (39.1%) included unsupported thresholds, classes, integrations, governance mechanics, or research facts.
5. The exact research facts were weak: the Zenodo DOI was wrong and the operator count conflicted with the supplied dated reference.
6. The collision probe distinguished Wilcoxon from the product, but still mischaracterized SignalAF; the relationship probe understood the ecosystem layering but was not source-grounded.

