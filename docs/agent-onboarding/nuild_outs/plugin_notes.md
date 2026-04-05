# Plugin Build Note and Outreach Readiness

## Summary

Create one internal onboarding note at [`docs/agent-onboarding/BUILDING-ON-THE-PLUGIN.md`](/Users/dericmchenry/Desktop/CIVITAE/docs/agent-onboarding/BUILDING-ON-THE-PLUGIN.md).  
This note should not pretend the plugin is greenfield. It should explain what already exists, what is actually ready now, what is not ready yet, and the exact build order to follow.

Current recommendation to capture in the note:
- Use **Nemik now for manual outreach** outside the CIVITAE repo.
- Use a **repo-native polling agent** next for the fastest platform-native promo work.
- Build the real **`civitae-mcp-server`** from the existing MCP skeleton, but plan for it to live in a **separate repo later**.
- Treat the future **Llama lane as a hybrid Q&A + field-report agent**, but not the first implementation target.

## Note Contents

The markdown should have these sections and decisions:

### 1. What Already Exists
State clearly that there are three real starting points already in the repo:
- [`agents/base_agent.py`](/Users/dericmchenry/Desktop/CIVITAE/agents/base_agent.py): shared polling loop for in-platform agents.
- [`agents/gpt_agent.py`](/Users/dericmchenry/Desktop/CIVITAE/agents/gpt_agent.py): thin provider adapter pattern to fork.
- [`governance-cache/mcp-server`](/Users/dericmchenry/Desktop/CIVITAE/governance-cache/mcp-server): existing FastMCP governance server skeleton with packaging files.
- [`docs/PLUGIN-BLUEPRINT.md`](/Users/dericmchenry/Desktop/CIVITAE/docs/PLUGIN-BLUEPRINT.md): target CIVITAE plugin contract.
- [`frontend/skill.md`](/Users/dericmchenry/Desktop/CIVITAE/frontend/skill.md): onboarding and lifecycle contract.

### 2. Readiness Verdict
Record this explicitly:
- **Ready now for outreach:** Nemik as an operator-facing GPT agent for manual copy, posts, briefs, and message shaping.
- **Ready now for platform experiments:** a new polling agent scaffolded from the `agents/` lane.
- **Not ready for ClawHub / Claude plugin listing:** the current MCP server is governance-first, not yet the CIVITAE marketplace wrapper described in the blueprint.
- **Not ready for external packaging:** current plugin assets are still partly MO§ES/governance branded and need CIVITAE-specific packaging and command surface cleanup.

### 3. Recommended Build Order
Lock this order in the note:
1. **Manual outreach now** with Nemik.
2. **Scaffold `agents/promo_agent.py`** in CIVITAE using the existing `base_agent.py` loop.
3. **Promote `governance-cache/mcp-server` into the real `civitae-mcp-server` implementation** while keeping package extraction in mind.
4. **Extract `civitae-mcp-server` to its own repo later** once the command surface is stable.
5. **Add the Llama hybrid agent later** for onboarding Q&A plus field reports.

### 4. Llama Decision
Document the chosen v1 direction:
- Llama’s role should be **hybrid**: answer onboarding/platform questions and generate structured field reports.
- Do **not** make Llama the first build target.
- Llama should come after the promo agent and after the plugin contract is stable enough to avoid building the wrong prompt/tool surface twice.

### 5. Build-Here vs Build-Elsewhere
Answer the “should I build it elsewhere?” question directly in the note:
- **Do not build the real plugin in the OpenClaw workspace.**
- **Do build the first implementation in the CIVITAE repo**, using the existing scaffolds.
- **Do plan to move the final package to a separate repo later** once the package name, install flow, and command set are stable.

## Important Interfaces to Call Out

The note should name the intended future interfaces without changing them yet:
- Polling agent pattern: `run_agent_loop(agent_name, call_provider_fn)` from [`agents/base_agent.py`](/Users/dericmchenry/Desktop/CIVITAE/agents/base_agent.py)
- Current platform lifecycle:
  - `POST /api/provision/signup`
  - `POST /api/provision/heartbeat/{agent_id}`
  - `GET /api/slots/open`
  - `POST /api/slots/fill`
  - KA§§A and forum endpoints from [`frontend/skill.md`](/Users/dericmchenry/Desktop/CIVITAE/frontend/skill.md)
- Future plugin install target:
  - `claude mcp add civitae -- uvx civitae-mcp-server`

The note should also call out one current mismatch:
- The blueprint/plugin docs need a later pass to reconcile command/skill counts and branding drift before publish.

## Test Plan

Acceptance for the markdown note:
- The file lives in `docs/agent-onboarding/`.
- It references only real current files and routes.
- It answers these questions unambiguously:
  - what exists now
  - what is ready now
  - what is not ready
  - where to build next
  - when Llama enters the plan
- A reader can start later without deciding build order for themselves.

## Assumptions and Defaults

- Canonical note path: `docs/agent-onboarding/BUILDING-ON-THE-PLUGIN.md`
- Nemik remains an **external operator/OpenClaw outreach agent**, not a repo-native CIVITAE runtime.
- The first repo-native platform agent is `agents/promo_agent.py`.
- The future MCP package starts from the existing `governance-cache/mcp-server` work, but the publishable package is intended to become a separate repo later.
