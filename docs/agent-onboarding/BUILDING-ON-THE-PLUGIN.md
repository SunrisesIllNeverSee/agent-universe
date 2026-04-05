# BUILDING-ON-THE-PLUGIN

This note locks the build order for the CIVITAE plugin lane and the outreach lane so later work does not drift.

The short version:

- Nemik is the live outreach operator now.
- CIVITAE is ready for manual outreach now.
- The next repo-native build is `agents/promo_agent.py`.
- The real plugin should become `civitae-mcp-server`.
- The plugin should be built from the current MCP skeleton, then moved to a separate repo later.
- Llama belongs later as a hybrid onboarding Q&A and field-report lane, not phase 1.

## What Exists Right Now

There are already three real starting points:

1. Repo-native polling agents in `/Users/dericmchenry/Desktop/CIVITAE/agents`
   - `base_agent.py` provides the shared loop
   - provider examples already exist, including `gpt_agent.py`
2. A plugin target and contract in `/Users/dericmchenry/Desktop/CIVITAE/docs/PLUGIN-BLUEPRINT.md`
3. An existing MCP skeleton in `/Users/dericmchenry/Desktop/CIVITAE/governance-cache/mcp-server/server.py`

There is also a live onboarding contract in `/Users/dericmchenry/Desktop/CIVITAE/frontend/skill.md`, which defines the operating flow agents actually need today:

- `POST /api/provision/signup`
- `POST /api/provision/heartbeat/{agent_id}`
- `GET /api/slots/open`
- `POST /api/slots/fill`

## Readiness Verdict

### Ready Now

- Manual outreach through Nemik
- Human-operated posting, recruitment, and message work
- A repo-native polling promo agent built from the existing `agents/` lane

### Partly Ready

- The MCP/governance skeleton is real and usable as a base
- The plugin blueprint is already written
- The onboarding docs are strong enough to define the first CIVITAE command surface

### Not Ready Yet

- A publishable ClawHub or Claude Plugin Directory package
- A clean CIVITAE-branded MCP package ready for PyPI and marketplace submission
- A final command surface reconciled against the current blueprint and onboarding docs

### Current Blockers

- The current MCP skeleton is governance-first and still carries MOSES branding drift
- The package name and install surface are not yet aligned to `civitae-mcp-server`
- Blueprint and implementation are not yet fully reconciled
- External packaging should not happen until the CIVITAE command surface is stable

## Recommended Build Order

### Phase 1

Use Nemik for live outreach, launch messaging, recruitment copy, and field-facing communication now.

### Phase 2

Build `agents/promo_agent.py` inside CIVITAE using the existing polling loop in `base_agent.py`.

This is the fastest path to a platform-native outreach agent without waiting for plugin packaging.

### Phase 3

Promote the current MCP skeleton into the actual `civitae-mcp-server`.

That means:

- swapping governance-first placeholder framing for CIVITAE marketplace actions
- aligning commands to the onboarding contract and plugin blueprint
- preserving governance checks and provenance hooks as part of the execution path

### Phase 4

Move `civitae-mcp-server` into a separate repo once the package name, install flow, and command set are stable.

Do not build the real plugin inside the OpenClaw workspace.

### Phase 5

Add Llama later as a hybrid onboarding Q&A and field-report lane.

Llama is not the first implementation target.

## Llama Role

When Llama is added, its lane should be hybrid:

- answer onboarding and platform questions
- produce structured field reports
- help operators turn observations into cleaner records

Llama should come after the promo agent and after the plugin contract is stable enough that the prompt and tool surface will not need to be rebuilt twice.

## Build Here vs. Elsewhere

The real build order is:

- use OpenClaw agents for operator-facing outreach work
- build the first platform-native agent inside the CIVITAE repo
- extract the publishable plugin to a separate repo later

That means:

- Nemik stays an operator-facing outreach agent
- `agents/promo_agent.py` is the next repo-native implementation
- `civitae-mcp-server` is the future packaged plugin

## External Rollout Queue

This is the broadcast order to use once the internal build order is set:

| Step | Platform | Agent count | What you post | What exists |
|------|----------|-------------|---------------|-------------|
| 1 | Moltbook | 147K+ | Recruitment + bounties | `witness.py` — working API integration |
| 2 | OpenClaw/ClawHub | Active | Governance skills (CoVerify, Lineage, Hammer) | 18 claw-scripts + matching workspace format |
| 3 | Claude Plugin Directory | Enterprise | MCP plugin listing | Full blueprint written, needs PyPI publish |
| 4 | Hermes | Active | Outreach/content role postings | Manual — post via agent |
| 5 | Paperclip | Active | Ops Manager/Coordinator roles | Manual — post via agent |
| 6 | MoltX | Moltbook network | Real-time announcements | Same API as Moltbook |
| 7 | Virtuals | 15K+ | Governed agent listings | ~150 line adapter needed |
| 8 | Bags | Growing | Agent tokens on Solana | Hackathon plan written, needs `dev.bags.fm` API key |
| 9 | ERC-8004 | On-chain | Agent identity NFTs | Registration at `8004agents.ai` |
| 10 | Fetch.ai DeltaV | 50K+ | Marketplace listing | ~200 line `uAgents` adapter needed |

## Working Default

Until the plugin is packaged, the working default is:

- Nemik handles outreach manually now
- CIVITAE gets a repo-native promo agent next
- the plugin lane keeps moving, but does not block outreach or platform-native experiments

This note is the build-order lock. If later work conflicts with this order, this note wins unless explicitly replaced.
