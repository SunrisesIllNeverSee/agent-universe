# ST-022 Result — Release Verification and Rollback

**Status:** CONFIRMED PROCESS GAP / RUNBOOK REQUIRED  
**Area:** deployment resilience

## Failure model

A commit can pass unit/CI checks and both Vercel/Railway processes can be healthy while the externally consumed MCP path is broken by proxy/routing/discovery drift.

This happened in the recent Glama incident: the application-side MCP implementation was healthy, but a Vercel content-negotiation rewrite changed what some public `/mcp` probes reached.

## Required release gates

A production release is not complete until all of these layers agree:

1. **Repository/CI**
   - hardening/contract tests green
   - expected commit merged to `main`

2. **Frontend/proxy — Vercel**
   - production deployment is READY for the expected `main` SHA
   - `/.well-known/mcp` resolves to the server card
   - server card points to `https://signomy.xyz/mcp`
   - hosted contract version/tool list match the repository

3. **Backend — Railway**
   - `/health` returns healthy
   - the MCP process is reachable through the public Vercel proxy

4. **Protocol — public custom domain**
   - initialize a real Streamable HTTP MCP client against `https://signomy.xyz/mcp`
   - list tools
   - assert 30 tools and expected critical names
   - do not substitute a browser GET for a protocol check

## Rollback triggers

Rollback/revert the release when any of the following appears immediately after deployment:

- public `/mcp` returns 404/redirect/docs HTML to an MCP client
- initialize/list-tools fails through `signomy.xyz`
- runtime and public card tool sets diverge
- critical auth regression
- production health fails
- high-integrity state corruption is observed

## Split-deploy rule

Vercel and Railway are separate failure domains.

- a frontend/proxy defect may require Vercel/main rollback without changing backend state
- a backend defect may require Railway/application rollback
- do not assume one platform's green status proves the other path works

## Decision

**CONFIRMED process gap.** Add an operator runbook and a reusable public MCP verification script. Keep the script out of ordinary CI because it depends on live production/network state; run it after deployment or from an authorized release environment.

## Closure

**Final status:** FIXED

**Implementation/evidence:** an operator release/rollback runbook and a read-only public MCP verification script were added. The verifier checks health, public server-card metadata, runtime tool count, critical tools, and runtime/card synchronization.

**Regression/ops coverage:** `docs/hardening/RELEASE-VERIFY-ROLLBACK.md` and `scripts/verify_public_mcp.py`.

**Remaining work:** run the public verifier after production deployment from a network-capable authorized environment; it is intentionally not a normal offline CI test.
