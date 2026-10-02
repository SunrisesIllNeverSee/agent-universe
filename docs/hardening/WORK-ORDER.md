# Agent Universe Hardening Work Order

**Program:** verification-first security, deployment, MCP, and resilience hardening  
**Baseline:** current `main` after MCP routing repair and design-note merge  
**Rule:** no recommendation is implemented until its stress test is documented and the current code is verified against it.

## Why this exists

This work order converts the external architecture/security review into testable claims. The review contains useful leads, but also stale or incorrect assumptions. This repository must not be refactored from prose alone.

Known corrections before testing:

- MCP surface is **30 tools + 7 resources**, not 27 tools.
- `app.mount("", _mcp_app)` is intentional. Mounting the FastMCP sub-app at `/mcp` previously caused path/redirect failures and is protected by regression coverage.
- Railway is intentionally **single-worker** because the current JSON-backed runtime/state stores corrupted state under multi-worker execution. Increasing workers is prohibited unless storage semantics are changed first.
- The repository already has route/MCP tests and CI runs `python -m pytest tests/ -x -q`; the claim that no obvious test layer exists is false.
- Public `/mcp` routing was separately repaired on 2026-10-01 so content negotiation cannot divert machine clients to a human docs route.

## Operating protocol

For every stress test:

1. Record the claim and threat/failure model.
2. Record the exact current behavior and source locations.
3. Define a reproducible test that would fail if the risk is real.
4. Run or encode the test before changing production behavior.
5. Classify the result: **CONFIRMED / PARTIAL / DISPROVED / INTENTIONAL / BLOCKED**.
6. Only confirmed/partial issues receive implementation work.
7. Add regression coverage for every implementation.
8. Update the stress-test record with the code commit and verification result.
9. Do not broaden scope while fixing a test.

## Status legend

- **QUEUED** — documented, not yet executed
- **TESTING** — evidence/test under construction
- **CONFIRMED** — defect reproduced
- **PARTIAL** — part of the claim is valid
- **DISPROVED** — current code does not exhibit the claimed failure
- **INTENTIONAL** — behavior is deliberate and should be preserved
- **FIXED** — implementation complete and regression-covered
- **DEFERRED** — valid but not appropriate until prerequisite architecture changes

## Work queue

| ID | Area | Stress test | Initial state |
|---|---|---|---|
| ST-001 | Identity | REST heartbeat authorization and side effects | TESTING |
| ST-002 | Identity | API-key rotation invalidates old key and activates new key | TESTING |
| ST-003 | Security | Admin auth coverage/bypass matrix | QUEUED |
| ST-004 | Security | Admin authentication audit trail | QUEUED |
| ST-005 | Identity | API key vs JWT privilege matrix and documentation drift | QUEUED |
| ST-006 | Identity | JWT expiry, issuer/audience, and cross-surface compatibility | QUEUED |
| ST-007 | Performance | MCP API-key lookup disk reload/O(n) behavior | QUEUED |
| ST-008 | Content | Stored/rendered HTML/XSS handling | QUEUED |
| ST-009 | Content | Prompt-injection normalization/fencing behavior | QUEUED |
| ST-010 | Abuse | Rate-limit correctness, memory bounds, restart semantics | QUEUED |
| ST-011 | Abuse | Open MCP discovery harvesting/flood resistance | QUEUED |
| ST-012 | Deploy | Startup validation with corrupt/missing state | QUEUED |
| ST-013 | Deploy | Health endpoint independence and MCP readiness | QUEUED |
| ST-014 | Deploy | Multi-worker state integrity | INTENTIONAL |
| ST-015 | MCP | Public endpoint/mount/path contract | INTENTIONAL |
| ST-016 | MCP | 30-tool smoke/contract validation | QUEUED |
| ST-017 | MCP | Tool version/deprecation contract | QUEUED |
| ST-018 | MCP | Discovery hot-path scalability/caching | QUEUED |
| ST-019 | MCP | Cursor loss/recovery semantics | QUEUED |
| ST-020 | Governance | Governance decision occurs before irreversible persistence | QUEUED |
| ST-021 | Reliability | Retry/idempotency/error semantics for MCP writes | QUEUED |
| ST-022 | Deploy | Rollback and release verification procedure | QUEUED |
| ST-023 | Architecture | `create_app` modularization value vs regression risk | QUEUED |
| ST-024 | Secrets | Production secret presence/rotation/fail-closed behavior | QUEUED |

## Locked invariants during this program

1. Do not change FastMCP root mounting without reproducing a real path failure.
2. Do not increase uvicorn workers while authoritative state uses current uncoordinated JSON/in-memory stores.
3. Do not change product routes, UX, or visual design as part of hardening.
4. Preserve public discovery unless a test proves a security boundary requires narrowing it.
5. Preserve MO§ES™ governance/provenance behavior; hardening must not silently bypass or reorder governed state transitions.
6. Keep all security changes fail-closed.
7. Never log raw API keys, JWTs, admin keys, magic links, or secrets.

## Deliverables

- This canonical work order.
- A documented record for every ST-* item.
- Reproduction/regression tests for confirmed defects.
- Minimal implementation patches tied to specific ST-* IDs.
- CI evidence for each implementation batch.
- Final closure table separating:
  - confirmed defects fixed,
  - disproved review claims,
  - intentional behavior preserved,
  - deferred architectural work,
  - remaining unknowns.
