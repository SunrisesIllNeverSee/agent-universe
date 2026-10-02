# ST-013 Result — Health and MCP Readiness

**Status:** DISPROVED AS PROPOSED / CURRENT LIVENESS DESIGN PRESERVED  
**Area:** deployment health

## Review claim

The review suggested making `/health` build/list MCP tools on every request and return 503 if the tool list fails.

## Verified behavior

Current `GET /health` is intentionally cheap and returns liveness/version/uptime/timestamp.

FastMCP has already been built before the FastAPI application starts serving. If `build_fastmcp()` or creation of the streamable HTTP sub-app fails, app creation fails.

Therefore rebuilding MCP inside every health request would:

- duplicate work
- create avoidable allocations/session machinery
- couple liveness to an expensive internal operation
- still fail to detect the Vercel/Railway public-proxy class of error that caused the recent Glama issue

## Decision

**DISPROVED as proposed.**

- Keep `/health` cheap.
- Verify the public `/mcp` transport separately in release/rollback procedure ST-022.
- If a distinct readiness endpoint is ever needed, it should inspect already-created dependencies rather than rebuilding them.

## Closure

**Final status:** DISPROVED

**Implementation/evidence:** the proposed health redesign was not adopted. The current liveness endpoint remains intentionally cheap and does not construct or probe a new FastMCP instance on every request.

**Regression coverage:** existing health/readiness tests plus the startup and MCP contract suites protect the intended separation.

**Decision:** no production behavior change required.
