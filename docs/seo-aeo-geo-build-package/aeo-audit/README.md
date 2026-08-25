# AEO / SEO / GEO — Audit Results, Testing & Reconciliation

> Central location for all AI-search-engine audit results, prompt panels,
> raw evidence, and reconciliation work. Separate from product code
> (which lives in the SigRank repos) and separate from tools (which live
> in `_01_sigrank-app` and `_03_sigarena`).

## Implementation status

**All 5 tiers implemented (2026-08-17). Audit re-run pending (Codex usage limit).**

| Tier | Status | What |
|------|--------|------|
| 1 | Done | Hero subtitle rewrites on 11 pages |
| 2 | Done | Class taxonomy + seed dataset clarity |
| 3 | Done | Entity collision disambiguation |
| 4 | Done | Footer + homepage category-language nav |
| 5 | Done | GitHub + npm + README descriptions |
| Audit re-run | Pending | Blocked by Codex usage limit — re-run when available |

Full implementation details: `AEO_RECONCILIATION_PLAN_AND_EXECUTION.md`

## Folder structure

```
aeo-seo-geo/
├── README.md                  ← this file
├── prompt-panel/              ← the fixed 46-prompt test panel
│   └── PERPLEXITY_PROMPTS.md
├── audit-results/             ← scored logs (judgments per prompt)
│   ├── PERPLEXITY_LOG.md
│   ├── GEMINI_LOG.md
│   ├── GROK_LOG.md
│   ├── CLAUDE_LOG.md
│   ├── GOOGLE_SEARCH_LOG.md
│   ├── COPILOT_LOG.md
│   └── CHATGPT_SEARCH_LOG_0817.md
├── audit-raw/                 ← full rendered responses (unabridged)
│   ├── CHATGPT_SEARCH_RAW.md
│   ├── GEMINI_RAW.md
│   ├── GROK_RAW.md
│   ├── CLAUDE_RAW.md
│   ├── GOOGLE_SEARCH_RAW.md
│   └── COPILOT_RAW.md
└── reconciliation/            ← query-to-page reconciliation
    └── RECONCILIATION_SHEET.md
```

## Audit runs

| Run | Date | Engines | Prompts | Results |
|-----|------|---------|---------|---------|
| 1 | 2026-08-16 | Perplexity, Gemini, Grok, Google, Copilot | 46 each | `audit-results/` (5 logs) |
| 1 | 2026-08-16/17 | Claude, ChatGPT Search | 46 each | `audit-results/` (2 logs) |

Total: 322 prompt results across 7 engines.

## Key finding

The audit does **not** prove content is missing. It proves existing
content is not consistently being selected as the answer.

- Named/direct prompts: **94.4% retrieval**
- Broad discovery prompts: **11.1% retrieval**
- `signalaf.com` appeared in 32 of 46 Google result sets

Diagnosis: **query association, canonicalization, and authority problem**
— not a page-count problem.

## Reconciliation

The reconciliation sheet in `reconciliation/RECONCILIATION_SHEET.md`
maps each failed broad prompt to:
1. The existing URL that should answer it
2. Whether it is indexed
3. Whether its opening paragraph uses natural query language
4. Whether a competing SignalAF page exists
5. What the engines selected instead
6. The specific required change

Implementation priority:
- **Tier 1:** Rewrite opening paragraphs (11 pages)
- **Tier 2:** Canonicalize shared facts (operator count, classes, DOI)
- **Tier 3:** Disambiguate entity collisions (Signal Messenger, Wilcoxon, gig economy)
- **Tier 4:** Strengthen internal category paths (nav labels)
- **Tier 5:** Align external descriptions (GitHub, npm, Zenodo)

## Prompt panel

The fixed 46-prompt panel lives in `prompt-panel/PERPLEXITY_PROMPTS.md`.
Run weekly across all engines after deploying AEO improvements. Log
results in a new dated subfolder under `audit-results/`.
