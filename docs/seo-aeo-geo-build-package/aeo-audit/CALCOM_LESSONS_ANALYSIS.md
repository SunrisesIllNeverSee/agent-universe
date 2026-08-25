# Cal.com AEO Playbook — Review Analysis & Lessons for SigRank

> How Cal.com engineered themselves into the #1 ChatGPT-recommended scheduling tool,
> and what SigRank can learn from it.

---

## The Cal.com Playbook (5 pillars)

| Pillar | What Cal.com did | Why it works |
|--------|-----------------|--------------|
| 1. Comparison pages | 47 "Cal vs X" blog posts | Captures every "X vs Y" query AI chatbots receive |
| 2. Answer-formatted content | Every post structured as a direct answer to the exact question | AI models extract and cite the answer directly |
| 3. Niche directories | 23 directories competitors ignored | Multiplies surface area for crawlers and LLM training data |
| 4. GitHub stars | 45,000+ | Social proof + signals "this is the canonical project" |
| 5. Reddit mentions | 200+ with upvotes in relevant subreddits | Reddit is heavily weighted in AI training data and Perplexity citations |

**Core insight:** ChatGPT recommends Cal.com because the internet already talks about Cal.com in all the places AI models pull from. It's not luck — it's engineered visibility.

---

## SigRank's Current Position (honest assessment)

| Pillar | Cal.com | SigRank | Gap |
|--------|---------|---------|-----|
| 1. Comparison pages | 47 | 30 (16 on signalaf.com + 14 on sigeconomy.com) | 17 fewer, but in the right ballpark |
| 2. Answer-formatted content | Every post | Partially done (Tiers 1-5 just shipped) | Structure exists, needs more direct-answer formatting |
| 3. Niche directories | 23 | 2-3 (whatsthebigdata, npm, Glama) | **Massive gap — 20+ directories missing** |
| 4. GitHub stars | 45,000+ | 5 (sigrank-app) + 0 (mcp) + 0 (sigarena) | **Massive gap — needs organic momentum** |
| 5. Reddit mentions | 200+ with upvotes | ~0 | **Massive gap — zero Reddit presence** |

### Additional SigRank assets Cal.com doesn't have

- 98 content pages on signalaf.com (vs Cal.com's ~47 blog posts)
- 27 content pages on sigeconomy.com
- A published Zenodo dataset with DOI (academic credibility)
- An MCP server (AI-native distribution channel)
- A satellite leaderboard site (sigeconomy.com) for double SERP coverage

### What SigRank is missing that Cal.com has

- **Directory coverage** — Cal.com is in 23 directories; we're in 2-3
- **Reddit presence** — Cal.com has 200+ organic mentions; we have ~0
- **GitHub social proof** — Cal.com has 45K stars; we have 5
- **Comparison page count** — Cal.com has 47; we have 30 (close but not enough)
- **Direct-answer formatting** — our /vs/ pages have FAQ JSON-LD but the body isn't always structured as "the answer to the exact question"

---

## What We Can Learn — Pillar by Pillar

### Pillar 1: Comparison pages (we're close, need more)

**Cal.com's approach:** 47 "Cal vs X" posts covering every competitor a user might compare against.

**Our current state:** 30 comparison pages (16 on signalaf.com, 14 on sigeconomy.com). Both sites have FAQ JSON-LD with direct Q&A pairs. The structure is good.

**The gap:** We're missing comparison pages for competitors people actually search for:

Missing on signalaf.com:
- `vs/savvycal` — N/A (scheduling tool, not relevant)
- `vs/cursor` — exists already
- `vs/github-copilot` — exists as `vs/copilot`
- `vs/aider` — missing (AI coding tool, people ask "aider vs sigrank")
- `vs/cline` — missing (AI coding tool)
- `vs/continue` — missing (AI coding tool)
- `vs/roo-code` — missing (AI coding tool)
- `vs/windsurf` — missing (AI coding tool)
- `vs/zed` — missing (AI coding tool)
- `vs/tabnine` — missing (AI coding tool)
- `vs/amazon-q` — missing (AI coding tool)
- `vs/sourcegraph-cody` — missing (AI coding tool)

Missing on sigeconomy.com:
- `vs/aider` — missing
- `vs/cline` — missing
- `vs/continue` — missing
- `vs/copilot` — missing (exists on signalaf.com but not sigeconomy)
- `vs/cursor` — missing (exists on signalaf.com but not sigeconomy)

**Action:** Add ~10-12 more comparison pages for AI coding tools that people compare against token-tracking/operator-eval tools. Each one structured as a direct answer to "SigRank vs X" or "What's the best AI coding efficiency tool?"

**Priority:** Medium. We're at 30, Cal.com is at 47. Closing to ~40 would match their coverage.

### Pillar 2: Answer-formatted content (partially done)

**Cal.com's approach:** Every blog post is structured as a direct answer to the exact question people ask AI chatbots. The answer comes first, then the elaboration.

**Our current state:** Tiers 1-5 just shipped — hero subtitles now use natural query language. FAQ JSON-LD exists on most pages. But the body content doesn't always lead with the direct answer.

**The gap:** Our /vs/ pages have comparison tables (good for humans, hard for AI to extract). Cal.com's posts lead with a one-sentence verdict ("Cal.com is better than X if you need Y") before the table.

**Action:** Audit each /vs/ page and ensure the first paragraph is a direct answer to "SigRank vs X — which is better for [use case]?" The comparison table stays, but the opening needs to be extractable as a standalone answer.

**Priority:** High. This is the cheapest fix with the highest AEO return.

### Pillar 3: Niche directories (massive gap)

**Cal.com's approach:** 23 niche directories that competitors ignored. These are AI tool directories, SaaS directories, productivity tool directories, open-source directories.

**Our current state:** 2-3 directories:
- whatsthebigdata.com (badge on site)
- npmjs.com (package page)
- Glama.ai (MCP directory, unverified)

**The gap:** We need ~20 more directory listings. Relevant directories for SigRank:

AI/LLM tool directories:
- futurepedia.io
- theresanaiforthat.com
- toolify.ai
- ai-tools.directory
- aicollection.com
- futuretools.io
- insidr.ai
- supertools.ai

Developer tool directories:
- devhunt.org
- producthunt.com (we may have launched, need to check)
- slant.co
- alternative.me

MCP-specific directories:
- glama.ai/mcp (verify listing)
- mcp.so
- smithery.ai

Open-source directories:
- awesome-lists (awesome-ai-tools, awesome-developer-tools, etc.)
- libhunt.com

SaaS directories:
- g2.com
- capterra.com
- saashub.com
- alternativeto.net

**Action:** Submit to 20+ directories. Each listing should use the category language from our AEO work: "AI operator evaluation leaderboard" + "token cascade efficiency."

**Priority:** High. This is the biggest gap and the most mechanical to fix. Each directory is a new surface for AI crawlers.

### Pillar 4: GitHub stars (massive gap, organic only)

**Cal.com's approach:** 45,000+ stars. This is organic momentum from being a popular open-source project. You can't fake this.

**Our current state:** 5 stars across all repos.

**The gap:** 44,995 stars. This is not a gap you close with a PR. It requires:
- Organic adoption (people using `npx sigrank` and starring the repo)
- Community building (contributing to discussions, helping users)
- Content that drives GitHub traffic (blog posts, tutorials, conference talks)
- Possibly: a "star us" call-to-action on the site (Cal.com does this)

**Action:**
1. Add a subtle "Star on GitHub" CTA to the signalaf.com footer or about page
2. Ensure the GitHub README is compelling (Tier 5 just improved this)
3. Focus on organic growth — this metric follows adoption, not the other way around
4. Consider: the MCP server is the distribution channel. Every agent that uses SigRank MCP is a potential starrer.

**Priority:** Low (can't be forced, follows from other pillars).

### Pillar 5: Reddit mentions (massive gap)

**Cal.com's approach:** 200+ Reddit mentions with upvotes in relevant subreddits (r/productivity, r/selfhosted, r/opensource, etc.). These are organic — users sharing, recommending, comparing.

**Our current state:** ~0 Reddit mentions.

**The gap:** This is the hardest pillar because it requires organic community engagement. Spamming Reddit backfires. But there are legitimate approaches:

Relevant subreddits for SigRank:
- r/ChatGPTCoding
- r/ClaudeAI
- r/cursor
- r/LocalLLaMA
- r/programming
- r/webdev
- r/ExperiencedDevs
- r/devops
- r/SaaS
- r/opensource
- r/IndieHackers

**Legitimate approaches:**
1. **Share the dataset** — r/MachineLearning or r/datascience would be interested in the 1,628-operator Zenodo dataset. This is genuinely novel research.
2. **Share the methodology** — "How we measure AI coding efficiency" posts in r/ChatGPTCoding or r/ClaudeAI
3. **Respond to relevant threads** — when someone asks "how do I measure my AI coding efficiency?" or "ccusage vs other tools?", SigRank is a legitimate answer
4. **Share the blog posts** — the "Volume Isn't Yield" and "Why Yield Beats Tokenmaxxing" posts are genuinely interesting to AI coding communities
5. **Open-source community** — r/opensource for the MCP server and CLI tool

**What NOT to do:**
- Don't create fake accounts
- Don't spam
- Don't post the same thing to 10 subreddits
- Don't upvote your own posts

**Action:** Start with 2-3 legitimate Reddit posts sharing the dataset and methodology. Engage in relevant threads where SigRank is a genuine answer. Build organically.

**Priority:** Medium-high. Reddit is heavily weighted in AI training data and Perplexity citations. But it must be organic.

---

## Priority Matrix

| Pillar | Effort | Impact | Priority | Timeline |
|--------|--------|--------|----------|----------|
| 3. Directories | Low (mechanical submission) | High (new surfaces for AI) | **P0** | This week |
| 2. Answer formatting | Low (edit existing pages) | High (better AI extraction) | **P0** | This week |
| 1. More comparison pages | Medium (write 10-12 pages) | Medium (capture more queries) | **P1** | Next 2 weeks |
| 5. Reddit | Medium (organic engagement) | High (AI training data weight) | **P1** | Ongoing |
| 4. GitHub stars | High (organic momentum) | Medium (social proof) | **P2** | Follows from adoption |

---

## What We're Already Doing Right

1. **Comparison page structure** — 30 /vs/ pages with FAQ JSON-LD is a strong foundation
2. **AEO Tier 1-5 work** — hero subtitles now use natural query language
3. **Two-site strategy** — signalaf.com + sigeconomy.com = double SERP coverage
4. **Zenodo dataset** — academic credibility that Cal.com doesn't have
5. **MCP server** — AI-native distribution channel that didn't exist when Cal.com built their strategy
6. **98 content pages** — more content than Cal.com's ~47 blog posts
7. **llms.txt + llms-full.txt** — explicit AI discovery surface that most competitors don't have

## The Honest Assessment

Cal.com's strategy works because they have **breadth + depth**: breadth across directories and Reddit, depth in comparison content. SigRank has depth (98 pages, dataset, MCP) but lacks breadth (2 directories, 0 Reddit, 5 GitHub stars).

The highest-ROI moves are:
1. **Directories** — 20 submissions, ~1 hour each, permanent surface for AI crawlers
2. **Answer formatting** — audit and fix the opening paragraph on /vs/ pages
3. **Reddit** — start with the dataset and methodology, build organically

The GitHub stars gap is real but not fixable with a tactic. It follows from adoption, which follows from the other pillars.

---

## Next Steps

1. **This week:** Submit to 20 directories (P0)
2. **This week:** Audit /vs/ page openings for direct-answer formatting (P0)
3. **Next 2 weeks:** Write 10-12 missing comparison pages (P1)
4. **Ongoing:** Reddit engagement starting with dataset + methodology (P1)
5. **After audit re-run:** Measure whether broad-query retrieval improved from 11.1% toward 50%+
