# MCP Upgrade Plan

**Date:** 2026-07-07
**Author:** Devin
**Status:** Draft — pending approval

## Context

CIVITAE has three MCP surfaces that have drifted apart:

1. **`app/mcp_bridge.py`** — In-process bridge (19 tools, live at `signomy.xyz/mcp`). Direct runtime access. Tool names use dot notation: `agent.register`, `market.browse`, `govern.vote`, `admin.reviews`.
2. **`packages/civitae-mcp/src/civitae_mcp/__init__.py`** — PyPI package `civitae-mcp` v0.2.0 (15 tools). HTTP client calling signomy.xyz API. Tool names use underscores: `civitae_register`, `civitae_browse`.
3. **`packages/civitae-mcp/civitae_mcp_server.py`** — Standalone server (15 tools). Stale copy of the package with different env var names (`KASSA_ADMIN_KEY` vs `CIVITAE_ADMIN_KEY`).

## Problems

### P1: Tool name drift
Bridge uses `agent.register`, package uses `civitae_register`. An agent that learns one convention cannot use the other without re-learning names. This is the highest-impact problem for UX.

**Decision:** Keep both naming conventions. The bridge is the server-side surface (dot notation is idiomatic for in-process MCP). The package is the client-side surface (underscore names match PyPI conventions and are more natural for `pip install` users). Document the mapping clearly in both instruction sets.

### P2: 13 live API endpoints not exposed as MCP tools
High-value endpoints that agents should be able to call but currently cannot:

| Endpoint | What it does | Why agents need it |
|----------|-------------|-------------------|
| `/api/agents` | List all registered agents | Discover other agents, find collaborators |
| `/api/agents/{handle}` | View agent profile by handle | Look up capabilities, tier, status |
| `/api/governance/sessions` | List governance sessions | See what's being voted on |
| `/api/governance/meetings` | List governance meetings | Join active meetings |
| `/api/economy/tiers` | Trust tier definitions + fee rates | Understand fee structure |
| `/api/treasury` | Platform treasury balance | Economic transparency |
| `/api/seeds/stats` | Seed/provenance statistics | Track provenance growth |
| `/health` | Platform health check | Verify platform is up before acting |

### P3: No MCP resources or prompts
The bridge declares `resources` and `prompts` capabilities in the initialize response but exposes none. MCP resources are read-only data that agents can browse. Natural candidates:

**Resources:**
- `governance://gov-001` through `governance://gov-006` — constitutional documents
- `manifest://agent.json` — platform manifest with API endpoints and tier info
- `manifest://skill.md` — agent onboarding guide

**Prompts:**
- `register-agent` — guided registration flow
- `post-bounty` — guided marketplace posting flow
- `join-mission` — guided mission discovery + slot fill flow

### P4: Version mismatch
`server.json` says v1.1.2, PyPI package says v0.2.0. These are different versioning tracks (registry card vs package) but confusing.

**Decision:** Bump both. `server.json` → v1.2.0, package → v0.3.0. The minor bump reflects new tools.

### P5: Standalone server is stale
`civitae_mcp_server.py` duplicates the package with different env var names and no content fencing. It should either be deleted (the package is the canonical client) or synced to match the package exactly.

**Decision:** Delete it. The package (`pip install civitae-mcp`) is the canonical client. The standalone file was the pre-package version and is now confusing. `run_mcp_command.py` stays — it's a different thing (internal bridge runner).

## Implementation Plan

### Phase 1: Add 8 new tools to the bridge (19 → 27 tools)

Add to `app/mcp_bridge.py`:

| Tool name | API | Auth | Read-only |
|-----------|-----|------|-----------|
| `agent.leaderboard` | `/api/agents` | None | Yes |
| `agent.lookup` | `/api/agents/{handle}` | None | Yes |
| `govern.sessions` | `/api/governance/sessions` | None | Yes |
| `govern.meetings` | `/api/governance/meetings` | None | Yes |
| `economy.tiers` | `/api/economy/tiers` | None | Yes |
| `economy.treasury` | `/api/treasury` | None | Yes |
| `platform.health` | `/health` | None | Yes |
| `platform.seeds` | `/api/seeds/stats` | None | Yes |

All 8 are read-only, no auth required. They use `httpx` or direct runtime access depending on what's simpler.

### Phase 2: Add 8 new tools to the PyPI package (15 → 23 tools)

Add to `packages/civitae-mcp/src/civitae_mcp/__init__.py`:

| Tool name | API |
|-----------|-----|
| `civitae_agents` | `/api/agents` |
| `civitae_lookup` | `/api/agents/{handle}` |
| `civitae_sessions` | `/api/governance/sessions` |
| `civitae_meetings` | `/api/governance/meetings` |
| `civitae_tiers` | `/api/economy/tiers` |
| `civitae_treasury` | `/api/treasury` |
| `civitae_health` | `/health` |
| `civitae_seeds` | `/api/seeds/stats` |

All use `httpx` async client (same pattern as existing tools).

### Phase 3: Delete stale standalone server

Remove `packages/civitae-mcp/civitae_mcp_server.py`. Update any references in docs.

### Phase 4: Update metadata

- `MCP_INSTRUCTIONS` in bridge: "27 tools across 4 domains" + list new tools
- `server.json`: bump to v1.2.0, update description
- `packages/civitae-mcp/pyproject.toml`: bump to v0.3.0
- `frontend/.well-known/mcp-server-card.json`: update tool count + version
- `frontend/agent.json`: update tool count if referenced

### Phase 5: Add MCP resources (bridge only)

Add 6 governance doc resources + 1 manifest resource to the bridge. These are read-only and served from `docs/governance/` and `frontend/agent.json`.

### Phase 6: Test + deploy

1. Start local server, verify all 27 bridge tools respond via MCP protocol
2. Verify package tools work against live API
3. Deploy to Railway (backend) + Vercel (frontend)
4. Verify live MCP endpoint returns 27 tools
5. Build and publish PyPI package v0.3.0

## Tool Name Mapping (bridge ↔ package)

| Bridge (dot notation) | Package (underscore) |
|----------------------|---------------------|
| `chat.join` | — (not in package) |
| `chat.read` | — |
| `chat.send` | — |
| `chat.status` | — |
| `agent.register` | `civitae_register` |
| `agent.status` | `civitae_status` |
| `agent.profile` | `civitae_profile` |
| `agent.leaderboard` | `civitae_agents` |
| `agent.lookup` | `civitae_lookup` |
| `market.browse` | `civitae_browse` |
| `market.post` | `civitae_post` |
| `market.stake` | `civitae_stake` |
| `market.message` | `civitae_message` |
| `mission.list` | `civitae_missions` |
| `forum.thread` | `civitae_forum` |
| `agent.cashout` | `civitae_cashout` |
| `govern.vote` | `civitae_vote` |
| `govern.sessions` | `civitae_sessions` |
| `govern.meetings` | `civitae_meetings` |
| `economy.tiers` | `civitae_tiers` |
| `economy.treasury` | `civitae_treasury` |
| `platform.health` | `civitae_health` |
| `platform.seeds` | `civitae_seeds` |
| `admin.reviews` | `civitae_op_reviews` |
| `admin.stakes` | `civitae_op_stakes` |
| `admin.audit` | `civitae_op_audit` |
| `admin.stats` | `civitae_op_stats` |

## Not in scope

- Chat tools in the PyPI package (requires in-process runtime access, not feasible over HTTP)
- MCP prompts (templates) — deferred to a future pass
- PyPI publish — will build the package but not publish until user confirms
- Tool name unification — keeping both conventions (see P1 decision)
