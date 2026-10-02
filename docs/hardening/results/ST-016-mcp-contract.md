# ST-016 Result — 30-Tool MCP Contract Smoke

**Status:** PARTIAL BEFORE HARDENING / CONTRACT TESTS ADDED  
**Area:** MCP public contract

## Claim

The runtime tool surface, public server card, and resources must remain synchronized.

## Baseline

Current runtime exposes **30 tools** and **7 resources**.

The public server card currently advertises the same 30 tools. This was manually repaired on 2026-10-01 after several public discovery surfaces still described the older 27-tool contract.

Existing tests asserted the runtime count and presence of several lifecycle tools, but did not mechanically compare the complete runtime tool-name set against the server card or assert the resource count.

## Stress test

On every CI run:

1. build FastMCP
2. list runtime tools
3. parse `frontend/.well-known/mcp-server-card.json`
4. assert exact tool-name set equality
5. list runtime resources and assert count == 7
6. assert the public endpoint/transport remain `https://signomy.xyz/mcp` + `streamable-http`

## Pass condition

No missing or extra advertised tools and exactly seven resources.

## Decision

Add contract synchronization to CI. This is preferred over relying on manual metadata review after tool changes.
