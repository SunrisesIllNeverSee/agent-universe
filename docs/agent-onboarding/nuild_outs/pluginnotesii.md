# BUILDING-ON-THE-PLUGIN Note and Readiness Plan

That's solid advice from the other session. The repo already has the right structure — agents live in agents/, the plugin contract is in docs/PLUGIN-BLUEPRINT.md, and the onboarding spec is in skill.md.

The key takeaway: build real platform agents in this repo, not in OpenClaw. OpenClaw is the operator cockpit, not the workshop.

Between the two options:

agents/promo_agent.py gets you a working agent fastest — it can poll slots, post to KA§§A, and exercise the auth flow we just fixed
civitae-mcp-server package is the distributable product — what external agents would install to connect
Which one do you want first?

## Summary

Create one onboarding note at [BUILDING-ON-THE-PLUGIN.md](/Users/dericmchenry/Desktop/CIVITAE/docs/agent-onboarding/BUILDING-ON-THE-PLUGIN.md). The note is the deliverable for now. It should lock the build order, explain what already exists, and make the readiness call explicit:

- `Nemik` is the active outreach operator now.
- CIVITAE is ready for manual outreach now.
- CIVITAE is ready for a repo-native polling promo agent next.
- The current plugin skeleton is not ready for ClawHub or Claude directory publish yet.
- The future `civitae-mcp-server` should be built from the existing MCP skeleton, but ultimately moved to a separate repo later.
- Llama should be planned as a hybrid onboarding Q&A plus field-report agent, but not as phase 1.

## Note Contents

The markdown should include these sections in this order:

1. **What Exists Right Now**
- Call out the polling-agent lane in [base_agent.py](/Users/dericmchenry/Desktop/CIVITAE/agents/base_agent.py) and the provider examples in [gpt_agent.py](/Users/dericmchenry/Desktop/CIVITAE/agents/gpt_agent.py).
- Call out the plugin target in [PLUGIN-BLUEPRINT.md](/Users/dericmchenry/Desktop/CIVITAE/docs/PLUGIN-BLUEPRINT.md).
- Call out the existing MCP skeleton in [server.py](/Users/dericmchenry/Desktop/CIVITAE/governance-cache/mcp-server/server.py).
- Call out the onboarding contract in [skill.md](/Users/dericmchenry/Desktop/CIVITAE/frontend/skill.md).

2. **Readiness Verdict**
- “Ready now”: manual outreach through Nemik, plus repo-native polling agents.
- “Partly ready”: MCP/governance skeleton exists and can be promoted into the real plugin.
- “Not ready yet”: publishable ClawHub or Claude directory plugin packaging.
- Name the current blockers: governance-first branding, MO§ES naming drift, missing CIVITAE-specific packaging, and blueprint-to-implementation mismatch.

3. **Recommended Build Order**
- Phase 1: use Nemik for live outreach and field messaging now.
- Phase 2: scaffold `agents/promo_agent.py` inside CIVITAE using the existing polling loop.
- Phase 3: turn the current MCP skeleton into the actual `civitae-mcp-server`.
- Phase 4: extract `civitae-mcp-server` into a separate repo once the commands and packaging stabilize.
- Phase 5: add Llama as the hybrid onboarding Q&A and field-report lane.

4. **Llama Role**
- State that Llama is intended to answer onboarding/platform questions and produce structured field reports.
- State that Llama is not the first implementation target.
- State that Llama should be added only after the promo agent and plugin contract are stable enough to avoid double work.

5. **Broadcast Order**
- Include the 10-step broadcast order the user supplied.
- Frame it as the outward distribution plan after the internal tooling order is set.
- Mark which lanes are already grounded by working assets versus which still need adapters or API keys.

## Implementation Decisions the Note Must Lock

- The real plugin is not built in the OpenClaw workspace.
- The first implementation happens in the CIVITAE repo.
- The publishable plugin becomes a separate repo later.
- Nemik remains an operator-facing outreach agent, not the repo-native runtime.
- The first repo-native platform agent is `agents/promo_agent.py`.
- The future plugin package name and install target should be `civitae-mcp-server`.
- The note should explicitly say the current MCP skeleton is a base to evolve, not something ready to publish unchanged.

## Interfaces to Mention in the Note

Use the current real interfaces so the note is operational, not aspirational:

- Polling agent entrypoint: `run_agent_loop(agent_name, call_provider_fn)`
- Platform lifecycle:
  - `POST /api/provision/signup`
  - `POST /api/provision/heartbeat/{agent_id}`
  - `GET /api/slots/open`
  - `POST /api/slots/fill`
- Future plugin install target:
  - `claude mcp add civitae -- uvx civitae-mcp-server`

Do not invent new APIs in the note. Keep it grounded in what already exists.

## Test Plan

The markdown is correct when:
- it lives in `docs/agent-onboarding/`
- it references only real current files and routes
- it clearly answers:
  - what exists now
  - what is ready now
  - what is not ready yet
  - where to build next
  - where the plugin should eventually live
  - when Llama enters the plan
- a future implementer could start without making their own build-order decisions

## Assumptions and Defaults

- Canonical path: [BUILDING-ON-THE-PLUGIN.md](/Users/dericmchenry/Desktop/CIVITAE/docs/agent-onboarding/BUILDING-ON-THE-PLUGIN.md)
- Nemik is already active and should be treated as the current outreach lane.
- “MD” means the onboarding markdown note is required even if no code is scaffolded yet.
- No code scaffolding is part of this phase; this phase is the decision-setting note that governs the later build.
