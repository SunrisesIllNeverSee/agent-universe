---
type: Plan
title: Signomy Content Expansion Plan — Phases 9-14
description: Build 70+ pages (footer, blog, /vs/, /alternatives/, /tools/, /metrics/) plus backlink strategy to match signalaf.com's content footprint. Executed with parallel agents.
tags: [signomy, content, seo, geo, aeo, expansion, plan]
timestamp: 2026-08-27
---

# Signomy Content Expansion Plan — Phases 9-14

> **Goal:** Close the 70-page content gap between signomy.xyz (76 pages) and
> signalaf.com (146 pages). Build the missing content layer that captures
> broad discovery queries, competitor search traffic, and listicle intent.

## Current state (post Phase 1-8)

| Metric | Value |
|--------|-------|
| Total pages | 76 |
| Sitemap URLs | 75 |
| Concepts | 10 |
| Guides | 4 |
| /vs/ pages | 5 |
| Blog posts | 0 |
| /alternatives/ | 0 |
| /tools/ | 0 |
| /metrics/ | 0 |
| Footer | None |
| Named query retrieval | 100% (3/3) |
| Broad discovery retrieval | 0% (0/2) |

## Target state (post Phase 9-14)

| Metric | Target |
|--------|--------|
| Total pages | ~155 |
| Sitemap URLs | ~150 |
| Concepts | 10 (done) |
| Guides | 8 (+4) |
| /vs/ pages | 20 (+15 high-priority) |
| Blog posts | 12 (+12) |
| /alternatives/ | 8 (+8) |
| /tools/ | 3 (+3) |
| /metrics/ | 4 (+4) |
| Footer | 1 (70+ links) |
| Broad discovery retrieval | >30% |

> **Note:** We're building 50 new pages, not the full 70-page gap.
> Quality over quantity. The remaining 20 can be added in a later sprint.
> The /vs/ target is 20 (not 43) because signalaf's 43 includes many
> niche token-tracking tools that aren't relevant to signomy's category.

---

## Phase 9: Structured Footer (1 build, applied to all pages)

### What
Build a site-wide footer with 70+ organized internal links, matching
signalaf's pattern. The footer creates an internal linking mesh that:
- Distributes page authority across all content
- Gives crawlers a complete site map at the bottom of every page
- Improves user navigation to deep content
- Captures SEO value from every page's footer links

### Structure
```
FOOTER (6 columns):
  Column 1: Platform
    - Homepage, Kassa, Missions, Governance, Treasury, Vault, Agents, Forums
  Column 2: Concepts
    - All 10 concept pages
  Column 3: Guides
    - All 8 guide pages
  Column 4: Comparisons
    - All /vs/ pages
  Column 5: Resources
    - Blog, Alternatives, Tools, Metrics, FAQ, Developers, Privacy
  Column 6: Ecosystem
    - MO§ES (mos2es.com), SigArena (sigeconomy.com), SigRank (signalaf.com)
    - GitHub, PyPI, ORCID, Patent info
```

### Implementation
- Build as a JS-injected footer (like _nav.js) so it's maintained in one place
- Create `frontend/_footer.js`
- Inject via `<script src="/assets/_footer.js"></script>` in every page
- Style to match the dark/gold theme

### Acceptance
- Footer appears on all 76+ pages
- 70+ internal links
- All links use clean URLs
- Mobile-responsive (stacks on small screens)

---

## Phase 10: Blog / Listicles (12 pages)

### What
Build 12 blog posts targeting broad discovery and listicle queries.
These are the pages that capture "best AI agent marketplace", "how to
govern AI agents", and comparison-intent searches.

### Page list
| # | Slug | Target query |
|---|------|-------------|
| 1 | /blog/best-ai-agent-marketplaces | "best AI agent marketplaces" |
| 2 | /blog/governed-vs-ungoverned-agents | "governed vs ungoverned AI agents" |
| 3 | /blog/how-to-govern-ai-agents | "how to govern AI agents" |
| 4 | /blog/constitutional-ai-explained | "constitutional AI explained" |
| 5 | /blog/ai-agent-trust-tiers-explained | "AI agent trust tiers" |
| 6 | /blog/how-to-build-a-governed-multi-agent-system | "how to build governed multi-agent system" |
| 7 | /blog/ai-agent-provisioning-guide | "AI agent provisioning" |
| 8 | /blog/seed-provenance-and-audit-trails | "AI audit trail provenance" |
| 9 | /blog/moses-governance-framework-explained | "MO§ES governance framework" |
| 10 | /blog/ai-agent-economics-and-revenue-models | "AI agent revenue models" |
| 11 | /blog/conservation-law-of-commitment | "conservation law of commitment" |
| 12 | /blog/signomy-vs-signal-messenger | "signomy vs signal messenger" (disambiguation) |

### Content rules
- H1 = the question or listicle title
- First paragraph answers the question in natural language
- 800-1500 words
- Tables, step-by-steps, and lists over prose
- Internal links to concept pages, guides, and /vs/ pages
- Full OG/Twitter/JSON-LD metadata (Article schema)
- Each post links back to relevant canonical concept pages

### Acceptance
- 12 blog posts in /blog/ directory
- All in sitemap and llms.txt
- Article JSON-LD on each
- Internal links to at least 3 other signomy pages per post

---

## Phase 11: /vs/ Comparison Pages (15 new pages)

### What
Build 15 high-priority comparison pages targeting competitor search traffic.
Each page captures "[competitor] alternative" and "signomy vs [competitor]" queries.

### Page list (priority order)
| # | Slug | Competitor | Why |
|---|------|-----------|-----|
| 1 | /vs/autogpt | AutoGPT | Popular agent framework |
| 2 | /vs/openai-agents | OpenAI Agents SDK | Major platform |
| 3 | /vs/adept | Adept AI | Enterprise agents |
| 4 | /vs/agentgpt | AgentGPT | Open-source agent platform |
| 5 | /vs/superagi | SuperAGI | Agent framework |
| 6 | /vs/microsoft-autogen | Microsoft AutoGen | Microsoft's framework |
| 7 | /vs/google-adk | Google Agent Dev Kit | Google's framework |
| 8 | /vs/crewai | (already exists) | — |
| 9 | /vs/langchain | (already exists) | — |
| 10 | /vs/olas | (already exists) | — |
| 11 | /vs/okx-ai | (already exists) | — |
| 12 | /vs/virtuals-protocol | (already exists) | — |
| 13 | /vs/nomos | NOMOS Exchange | Agent marketplace competitor |
| 14 | /vs/runtimeai | RuntimeAI | Governed agent catalog |
| 15 | /vs/agentbazaar | AgentBazaar | Hedera agent marketplace |

### Content rules
- H1: "Signomy vs [Competitor]: [Differentiator]"
- Comparison table: Governance, Registration, Trust Tiers, Marketplace, Economics, Audit Trail
- "When to choose Signomy" section
- "When to choose [Competitor]" section (be fair, not just promotional)
- Link to relevant concept pages
- Full OG/Twitter/JSON-LD metadata

### Acceptance
- 15 new /vs/ pages (20 total with existing 5)
- All in sitemap and llms.txt
- Comparison table on each
- Fair and accurate competitor descriptions

---

## Phase 12: /alternatives/ Pages (8 pages)

### What
Build /alternatives/ pages that capture "[category] alternatives" queries.
These are high-intent pages for users searching for alternatives to
specific categories of tools.

### Page list
| # | Slug | Target query |
|---|------|-------------|
| 1 | /alternatives/ai-agent-marketplaces | "AI agent marketplace alternatives" |
| 2 | /alternatives/governed-agent-platforms | "governed agent platform alternatives" |
| 3 | /alternatives/ai-agent-registry | "AI agent registry alternatives" |
| 4 | /alternatives/multi-agent-frameworks | "multi-agent framework alternatives" |
| 5 | /alternatives/ai-governance-tools | "AI governance tools alternatives" |
| 6 | /alternatives/constitutional-ai-tools | "constitutional AI tools" |
| 7 | /alternatives/ai-agent-economics | "AI agent economics platforms" |
| 8 | /alternatives/langchain-alternatives | "LangChain alternatives for governed agents" |

### Content rules
- H1: "Best [Category] Alternatives in 2026"
- Table comparing 5-8 alternatives with columns: Tool, Governance, Marketplace, Audit Trail, Pricing
- Signomy positioned as one option (not the only one — be credible)
- "How to choose" section
- Link to relevant /vs/ pages and concept pages

### Acceptance
- 8 /alternatives/ pages
- All in sitemap and llms.txt
- Comparison table on each
- Credible competitor descriptions

---

## Phase 13: /tools/ and /metrics/ Pages (7 pages)

### What
Build interactive tool pages and metric definition pages.

### /tools/ (3 pages)
| # | Slug | What |
|---|------|------|
| 1 | /tools/trust-tier-calculator | Calculate fee rates by trust tier |
| 2 | /tools/earnings-calculator | Calculate agent earnings under 40/30/30 split |
| 3 | /tools/governance-checker | Check if an action passes the Six Fold Flame |

### /metrics/ (4 pages)
| # | Slug | What |
|---|------|------|
| 1 | /metrics/trust-tier | Trust tier definitions and fee rates |
| 2 | /metrics/seed-provenance | Seed provenance metric definition |
| 3 | /metrics/flame-score | Six Fold Flame scoring |
| 4 | /metrics/treasury-split | 40/30/30 treasury distribution |

### Content rules
- Tools: Simple HTML/JS calculators, no backend needed
- Metrics: Definitional pages with formulas, tables, and examples
- Full OG/Twitter/JSON-LD metadata

### Acceptance
- 3 tool pages with working calculators
- 4 metric pages with formulas
- All in sitemap and llms.txt

---

## Phase 14: Backlink Strategy + External Signals

### What
Audit and replicate signalaf.com's external backlink strategy for signomy.xyz.

### Audit targets
1. Academic papers (clawRxiv, Zenodo DOIs)
2. Package registries (npm, PyPI, Smithery)
3. AI tool directories (aiagentsdirectory, pulsemcp, opentools, toolify, futurepedia)
4. GitHub READMEs and repo descriptions
5. MCP registries (modelcontextprotocol.io, mcp.so, smithery.ai)
6. Social mentions (Reddit, HackerNews, Product Hunt)

### Action items
- Update GitHub repo description to include "governed AI agent marketplace"
- Update PyPI package description for civitae-mcp
- Submit to AI tool directories
- Ensure clawRxiv paper links to signomy.xyz
- Create/update Smithery listing
- Create/update MCP registry listings

### Deliverable
- `BACKLINK_STRATEGY_SIGNOMY.md` with:
  - Current backlink inventory
  - Gap analysis vs signalaf
  - Prioritized action list
  - Submission templates for directories

---

## Execution plan

### Agent swarm strategy
Run 5 parallel subagents:

| Agent | Task | Est. pages |
|-------|------|-----------|
| Agent A | Build footer (_footer.js) + inject into all pages | 1 component |
| Agent B | Build 12 blog posts | 12 pages |
| Agent C | Build 15 /vs/ pages | 15 pages |
| Agent D | Build 8 /alternatives/ + 4 /metrics/ pages | 12 pages |
| Agent E | Build 3 /tools/ pages | 3 pages |

After all agents complete:
- Update sitemap.xml + sitemap-v2.xml
- Update llms.txt + llms-full.txt
- Push all new URLs to IndexNow
- Push new URLs to GSC Indexing API
- Write build documentation

### Content authority
All agents must follow:
- Load Search Authority canon before writing definitions
- Use MO§ES™ (never MO§E§)
- Keep Signomy and CIVITAE distinct
- "Agents are free. Operators pay."
- Natural query language in opening paragraphs
- Link back to canonical concept pages
- Full OG/Twitter/JSON-LD on every page

### Documentation
After the build, create:
- `CONTENT_EXPANSION_BUILD_LOG.md` — what was built, by which agent, page count
- Update `MAINTENANCE_RUNBOOK_SIGNOMY.md` with new page counts
- Update `CITATION_TRACKING_SIGNOMY.csv` with new URLs for tracking
