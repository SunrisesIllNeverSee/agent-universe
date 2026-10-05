# CIVITAE MCP 0.4.0 — Release Closeout

**Date:** 2026-10-05
**Status:** CLOSED — all release artifacts verified live; one external directory refresh pending on Glama's side.

## Verified production state (2026-10-05)

| Surface | Expected | Observed | Evidence |
|---|---|---|---|
| Domain health | HTTP 200 | `{"ok":true,"version":"0.9.0"}` | `GET /health` |
| Hosted MCP endpoint | reachable | HTTP 200 on `initialize` | `POST /mcp` |
| Server card | `1.2.2` | `version: 1.2.2` | `GET /.well-known/mcp-server-card.json` |
| Hosted tool count | `30` | 30 tools enumerated | `scripts/verify_public_mcp.py` → `PUBLIC CONTRACT HEALTHY` |
| Registry auth proof | `p=dPPGE5N3xwx/kjkVP7mMMmRIwsUGo93w6dwu3o34TIY=` | byte-identical | `GET /.well-known/mcp-registry-auth` vs committed file |
| PyPI | `civitae-mcp==0.4.0` | wheel + sdist present, uploaded 2026-10-02 | PyPI JSON API |
| Official MCP Registry | `xyz.signomy/civitae` v`1.2.2` | `status: active`, `isLatest: true`, published 2026-10-05T09:06Z | `registry.modelcontextprotocol.io/v0/servers?search=civitae` |
| CI (main `7392d8a`) | green | `success` | `gh run list` |
| Railway deploy | single worker | `--workers 1` in `railway.json`; treasury reads stable | prior session verification |

## Contracts (intentionally separate)

- **Hosted remote** `https://signomy.xyz/mcp` — streamable-http, **30 tools**, dot-named (`agent.register`, `market.browse`, `admin.stats`, …), contract version `1.2.2`.
- **Stdio package** `civitae-mcp` — PyPI **0.4.0**, **27 tools**, `civitae_*` names, HTTP client over the public REST API.

## Registry identity

- Canonical name: `xyz.signomy/civitae`
- Published version: `1.2.2` (latest; prior versions 1.0.0–1.2.1 retained in registry history)
- Public proof: `v=MCPv1; k=ed25519; p=dPPGE5N3xwx/kjkVP7mMMmRIwsUGo93w6dwu3o34TIY=` (served at `/.well-known/mcp-registry-auth`)
- Private key: GitHub environment secret `MCP_REGISTRY_PRIVATE_KEY` — do not print/rotate/move.

## Glama status

Listing: `https://glama.ai/mcp/servers/SunrisesIllNeverSee/agent-universe` (connector recognized, ownership verified).

**Stale.** Tool catalog still reflects an older introspection (23 `civitae_*` tool links shown — including the removed `civitae_op_stakes`; the catalog snapshot predates the 0.4.0/30-tool surface even though newer dates appear elsewhere in the page metadata). Glama re-scans continuously on its own schedule and detects schema drift automatically. Owner-side refresh: sign in to Glama with GitHub as `SunrisesIllNeverSee`, open the listing admin page, and use the repository **re-sync** control ("Request a re-sync when you have pushed something you want reflected here"). No unauthenticated rescan endpoint exists. The next scheduled sweep will capture the 30-tool hosted surface. This is the only remaining external step — not a code defect.

## Post-review metadata corrections (second pass)

- `README.md` MCP endpoint row: "27 governed tools" → 30 (was self-contradicting the same file's line 113).
- `AGENTS.md` Live versions block: Registry v1.2.0 → v1.2.2; PyPI v0.3.0-unpublished → v0.4.0 published; Smithery note retargeted to 30.
- `DIRECTORY_SUBMISSIONS.md`: pending DNS-TXT instruction block replaced with completed record (it carried the rotated-out public key **and** the dead private key in an actionable command — scrubbed; current proof recorded instead). Pending outbound submission copy updated 27 → 30 MCP tools.
- `BACKLINK_STRATEGY_SIGNOMY.md` Smithery action item retargeted to 30; `DOC-001-CIVITAE-SUBMISSION-COPY.md` 15 → 30 tools.
- Point-in-time records (plan docs, ST-* results, dated handoffs, hook logs) intentionally untouched.

## Deferred future architecture (explicitly out of scope, not incomplete work)

1. Transactional/coordinated persistence required before multi-worker scaling (ST-014 stays INTENTIONAL until then).
2. Explicit RBAC/scopes/capabilities for broad cockpit write operations (ST-025 follow-up — product authorization decision).
3. Idempotency keys / operation receipts for ambiguous MCP writes.
4. External MCP production canary (beyond `scripts/verify_public_mcp.py` manual runs).
5. `create_app` / server modularization (ST-023 DEFERRED — regression risk outweighed value).

## Closeout

Release cycle formally closed 2026-10-05. All owned surfaces verified; no release-blocking defects found.
