# Phase 2 Final Audit

**Phase 2 branch:** `hardening/phase-2-remaining-2026-10-02`
**Stacked base:** `hardening/verification-first-2026-10-01` (PR #50)

## Production-file mapping

| File | Authority | Change |
|---|---|---|
| `app/rate_limit.py` | P2-001 | Shared process-local limiter with stale-entry eviction |
| `app/routes/core.py` | P2-001, P2-003 | Shared limiter wrapper and `/api/ready` |
| `app/routes/operator.py` | P2-001 | Shared limiter wrapper |
| `app/routes/provision.py` | P2-001, P2-002 | Shared limiter and scoped session-token issuance |
| `app/routes/kassa.py` | P2-001, P2-002 | Shared limiter and scoped session-token issuance |
| `app/jwt_config.py` | P2-002 | Issuer/audience validation, previous-key rotation, bounded legacy migration |
| `app/deps.py` | P2-003 | Explicit MCP readiness state |
| `app/server.py` | P2-003, P2-004 | MCP-ready transition and operator-auth success telemetry |
| `app/auth.py` | P2-004 | Privacy-safe throttled operator-auth success telemetry |
| `app/mcp_bridge.py` | P2-006 | Dead token helper removed and stale multi-worker comment corrected |
| `frontend/skill.md` | P2-005 | Explicit credential boundary |

## Documentation

- `docs/hardening/PHASE-2-WORK-ORDER.md`
- `docs/hardening/CREDENTIAL-AND-ROTATION-GUIDE.md`
- `docs/JWT-ROTATION-RUNBOOK.md`

## Tests

- `tests/test_rate_limit_contract.py`
- `tests/test_jwt_config.py`
- `tests/test_routes_core.py`
- `tests/test_auth_hardening.py`

## Preserved invariants

- FastMCP parent root mount is unchanged.
- Railway remains single-worker.
- Rate limits remain process-local.
- Agent key rotation remains operator-controlled.
- `/health` remains cheap liveness; readiness is separate.
- No automatic replay of ambiguous MCP writes.
- No broad application-factory refactor.

## Verification evidence

CI run #407 on code head `a922e42d28af34dc8efe2a533ca3e83410f2d0cc`:

**419 passed, 1 dependency deprecation warning, 0 failures.**

## Audit result

**No Phase 2 production change falls outside P2-001 through P2-006.**

The external-review hardening supported by current-repo evidence is now implemented across PR #50 and this Phase 2 stack. Recommendations disproved or shown unsafe by stress testing remain intentionally excluded.
