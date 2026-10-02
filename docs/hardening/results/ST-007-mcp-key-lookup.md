# ST-007 Result — MCP API-Key Lookup Disk Reload

**Status before fix:** CONFIRMED / NARROW  
**Area:** MCP performance / identity lookup

## Claim

Authenticated MCP tools perform unnecessary registry disk I/O on every API-key lookup.

## Evidence

`MCPBridge.build_fastmcp()` defines `_agent_from_key(api_key)` which:

1. calls `runtime.reload_registry()`
2. hashes the key
3. linearly scans `runtime.registry` for an active matching record

`reload_registry()` acquires a file lock and reparses `data/provision.json`.

The production deployment is intentionally single-worker, so same-process key rotations/status changes already update the in-memory registry before persisting.

## Scope

The confirmed cost is the **disk reload**. The O(n) in-memory scan is not yet shown to be a bottleneck and should not be replaced by a cache until measured at realistic registry sizes.

A TTL cache would also introduce invalidation complexity for rotation/suspension, so the review's cache proposal is not accepted without evidence.

## Stress test

Call an authenticated MCP tool that has no independent registry refresh (for example `agent.inbox`) while instrumenting `runtime.reload_registry`.

Pre-fix expectation: one disk reload per call.

Post-fix requirement: zero reloads from `_agent_from_key`; key rotation and status changes remain immediately visible because the authoritative process updates memory synchronously.

## Decision

**CONFIRMED narrowly. Remove the per-auth disk reload; retain simple in-memory scan.**

## Closure

**Final status:** FIXED

**Implementation/evidence:** authenticated MCP key resolution no longer reloads the registry from disk on every lookup; the current single-worker deployment uses the authoritative in-memory registry and retains the simple scan.

**Regression coverage:** `tests/test_mcp_bridge.py::test_mcp_api_key_lookup_does_not_reload_registry`.

**Merge verification:** implementation is present on PR #50; full-suite CI and final branch-vs-main audit remain mandatory merge gates.
