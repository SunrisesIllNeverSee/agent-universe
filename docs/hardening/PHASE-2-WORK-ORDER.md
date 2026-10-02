# Phase 2 Hardening Work Order

**Base:** PR #50 / `hardening/verification-first-2026-10-01`  
**Branch:** `hardening/phase-2-remaining-2026-10-02`

This phase implements the remaining defensible hardening from the original external review after the first 24-item verification program.

## Scope

| ID | Hardening | Decision |
|---|---|---|
| P2-001 | Centralize duplicated in-memory rate limiting without changing deployment semantics | IMPLEMENT |
| P2-002 | Add JWT issuer/audience scoping with bounded legacy-token compatibility | IMPLEMENT |
| P2-003 | Add explicit readiness endpoint separate from liveness | IMPLEMENT |
| P2-004 | Add privacy-safe successful admin-auth telemetry | IMPLEMENT |
| P2-005 | Publish precise API-key/JWT/admin-key privilege and rotation guidance | IMPLEMENT |
| P2-006 | Remove dead JWT helper and stale multi-worker auth/MCP comments | IMPLEMENT |

## Explicit non-goals

These recommendations remain rejected because prior stress testing showed they are incorrect, unsafe, or unjustified:

- do not mount the FastMCP child at parent `/mcp`
- do not increase Railway workers while authoritative state remains current file/in-memory architecture
- do not persist rate-limit counters into JSON files or add Redis without a deployment need
- do not allow self-service API-key rotation using the same long-lived credential being rotated
- do not add blanket automatic retries to MCP writes
- do not add a broad `create_app` refactor
- do not pretend prompt-content fencing is a security boundary

## Acceptance criteria

### P2-001
- one shared rate-limit implementation
- current per-bucket semantics preserved
- stale eviction and boundary behavior still pass
- existing route call sites retain their current limits

### P2-002
- all newly issued REST session JWTs include `iss`, `aud`, `sub`, `iat`, `exp`
- tokens with incorrect issuer/audience are rejected
- currently valid legacy tokens without `iss`/`aud` remain usable only under a bounded compatibility rule
- previous-secret rotation continues to work

### P2-003
- `/health` remains cheap liveness
- `/api/ready` reports initialized critical dependencies
- readiness never rebuilds FastMCP or performs state-changing I/O
- not-ready returns HTTP 503

### P2-004
- successful operator auth emits privacy-safe telemetry
- no admin key, JWT, API key, magic link, or raw client IP appears in logs
- duplicate middleware/route-local success checks are throttled

### P2-005
- agent-facing documentation clearly states which credential is used where
- JWT and admin-key rotation procedures are distinct
- API-key compromise response points to operator-controlled rotation

### P2-006
- unused MCP JWT issuer removed
- stale comments implying multi-worker production corrected
- no runtime contract change

## Merge rule

Phase 2 does not merge until the complete test suite passes on its exact head and the Phase 2 diff is audited against this work order.
