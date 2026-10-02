# Final Branch Audit — PR #50

**Branch:** `hardening/verification-first-2026-10-01`  
**Base:** `main`  
**Purpose:** verify that every production change maps to a documented ST-* finding and that no unrelated product/design refactor entered the hardening branch.

## Production-file mapping

| File | Stress-test authority | Scope |
|---|---|---|
| `app/auth.py` | ST-004, ST-024 | Shared constant-time admin comparison and privacy-safe rejection telemetry |
| `app/kassa_store.py` | ST-018 | Push measured search/limit work into SQLite |
| `app/mcp_bridge.py` | ST-007, ST-009, ST-011, ST-016, ST-020, ST-021 | Key lookup, shared injection detector, public projection/bounds, contract wording, retry/idempotency semantics |
| `app/public_projection.py` | ST-011 | Strip private KA§§A routing/contact metadata from public discovery |
| `app/routes/advisory.py` | ST-004, ST-024 | Reuse shared admin-auth primitive |
| `app/routes/connect.py` | ST-004, ST-024 | Reuse shared admin-auth primitive |
| `app/routes/forums.py` | ST-004, ST-024 | Reuse shared admin-auth primitive |
| `app/routes/kassa.py` | ST-004, ST-011, ST-024 | Shared admin auth and public post projection |
| `app/routes/operator.py` | ST-004, ST-024 | Shared admin-auth primitive |
| `app/routes/provision.py` | ST-001, ST-002, ST-004, ST-024 | Heartbeat auth, real key rotation, shared admin comparison |
| `app/sanitize.py` | ST-008, ST-009 | Normalized prompt-injection detection and explicit defense-in-depth semantics |
| `app/server.py` | ST-003, ST-004, ST-024 | Active-agent cockpit bearer check and shared admin rejection telemetry |
| `frontend/kassa.html` | ST-011 | Consume public `collaborator_type` without requiring private email |
| `frontend/skill.md` | ST-021 | Retry/reconciliation guidance for MCP clients |
| `scripts/verify_public_mcp.py` | ST-022 | Read-only post-deploy public MCP verification |

## Test/document-only files

All remaining changed files are hardening specifications, per-ST result records, the release/rollback runbook, or regression tests tied to the items above.

## Explicitly preserved invariants

- FastMCP parent mount remains `app.mount("", _mcp_app)` — ST-015.
- Railway remains single-worker — ST-014.
- No Redis/persistent rate-limit rewrite — ST-010.
- No API-key/JWT credential collapse — ST-005/ST-006.
- No generic automatic retry of MCP writes — ST-021.
- No broad `create_app` modularization — ST-023.
- No product route, IA, UX, or visual redesign.

## Review blockers corrected

1. Canonical work-order status table updated from stale initial states to current classifications.
2. All ST-001 through ST-024 records now contain explicit closure sections.
3. Admin rejection telemetry first-event throttling bug fixed.
4. Prompt-fencing documentation corrected: fencing is context separation, not a security boundary.
5. PR #50 description updated to reflect the complete hardening scope.
6. MCP structured-result tests use the supported FastMCP client interface rather than relying on the server object's internal return shape.

## Audit result

**No undocumented production-file change was identified in the branch-vs-main file set.**

Every production modification listed above has an explicit ST-* authority. Any future change added to PR #50 must be added to this mapping or removed before merge.

## Merge gates

- [ ] Latest full CI run passes.
- [x] Branch-vs-main production-file mapping complete.
- [x] 24 stress-test records closed/classified.
- [x] Locked mount and single-worker invariants preserved.
- [ ] After merge/deploy: run `scripts/verify_public_mcp.py` from a network-capable authorized environment.
