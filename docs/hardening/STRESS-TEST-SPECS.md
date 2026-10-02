# Stress-Test Specifications

These are the executable specifications for the Agent Universe hardening program. Results are recorded separately as tests are run.

## ST-001 — REST heartbeat authorization

**Claim:** only the registered agent (or an authorized operator) should be able to update that agent's liveness state.

**Threat model:** an unauthenticated caller learns/guesses an `agent_id` and repeatedly mutates `last_seen`, bootstrap metrics, and sampled provenance seeds.

**Method:** create an agent; POST heartbeat with no auth, wrong Bearer API key, correct Bearer API key, and admin auth. Inspect `last_seen` before/after.

**Pass condition:** unauthenticated/wrong-key requests cannot mutate state; correct agent key succeeds; operator behavior is explicit.

**Implementation gate:** if unauthenticated mutation succeeds, require scoped agent authentication without breaking the MCP heartbeat path.

## ST-002 — API-key rotation authority

**Claim:** rotating a key must atomically make the new key authoritative and invalidate the old key.

**Method:** register agent; authenticate with old key; rotate via authorized operator; verify registry hash/persistence; old key must fail; new key must succeed; reload registry and repeat.

**Pass condition:** exactly one current key is authoritative after persistence.

**Implementation gate:** update hash + persistence before returning new secret; regression test old/new behavior.

## ST-003 — Admin auth coverage/bypass matrix

**Claim:** all operator-only reads/writes are centrally or redundantly protected with no public-prefix bypass.

**Method:** enumerate FastAPI routes; classify method/path; execute sensitive endpoints with no key, wrong key, admin key, agent API key, JWT. Compare middleware prefixes with route-local guards.

**Pass condition:** every sensitive route has the intended principal and no broader prefix accidentally exposes it.

## ST-004 — Admin authentication audit trail

**Claim:** failed and successful operator-auth attempts should be observable without leaking credentials.

**Method:** generate no-key/wrong-key/right-key attempts against representative admin paths; inspect audit/OTel/log outputs.

**Pass condition:** security-relevant events are attributable by route/result and privacy-safe client identifier.

## ST-005 — API key/JWT privilege matrix

**Claim:** long-lived API keys and short-lived JWTs have intentional, documented, non-overlapping privileges.

**Method:** build endpoint/tool matrix and try each credential type on heartbeat, inbox, Kassa writes, forums, operator cockpit, MCP writes.

**Pass condition:** implementation matches a written matrix and no credential receives accidental broader privilege.

## ST-006 — JWT claim validation

**Claim:** session JWTs expire and are scoped so tokens issued by one surface cannot be accepted indefinitely or outside intended audience.

**Method:** inspect all issuers/verifiers; test expired token, malformed token, wrong audience/issuer, cross-surface token, and current valid token.

**Pass condition:** all production JWTs have consistent expiry and explicit validation semantics. Audience/issuer are added only if all consumers can migrate safely.

## ST-007 — MCP API-key lookup performance

**Claim:** authenticated MCP calls should not perform unnecessary full registry disk reload + linear scan on every call.

**Method:** instrument/mock `reload_registry`; issue repeated authenticated tool calls at registry sizes 10/100/1000; count reloads and lookup cost.

**Pass condition:** correctness is preserved and hot-path I/O is bounded. Any cache must have explicit invalidation on key rotation/status change.

## ST-008 — Stored/rendered HTML/XSS

**Claim:** user content cannot execute script when rendered in first-party UI.

**Method:** submit HTML/event-handler/URL payloads through every user-content ingress; inspect stored value and frontend sinks (`innerHTML`, template interpolation, DOM APIs).

**Pass condition:** executable HTML is escaped/sanitized at render boundary; plain text content is preserved when safe.

## ST-009 — Prompt-injection normalization/fencing

**Claim:** governance filtering/fencing reduces accidental instruction confusion without pretending to be a complete prompt-injection defense.

**Method:** corpus of casing, whitespace, Unicode confusables, soft hyphens, encoded strings, role markers, nested fences, and benign false positives.

**Pass condition:** documented defense has predictable behavior; no claim that substring filtering makes arbitrary UGC safe for system-prompt interpolation.

## ST-010 — Rate-limit correctness

**Claim:** abuse controls enforce intended limits without unbounded memory or unsafe multi-worker assumptions.

**Method:** boundary requests, unique-IP churn, forwarded-for handling, restart reset behavior, stale eviction, and concurrency.

**Pass condition:** limits are correct for the current single-process deployment; persistence is added only if threat model justifies state cost.

## ST-011 — Open MCP discovery flood/harvest

**Claim:** intentionally public discovery remains usable without enabling trivial resource exhaustion or private-data leakage.

**Method:** inspect returned fields, paginate/loop calls, large search terms, high-frequency reads, contact-field exposure.

**Pass condition:** public fields are intentionally public; expensive operations are bounded; sensitive contact/internal fields are excluded.

## ST-012 — Startup state validation

**Claim:** production should detect authoritative state corruption before accepting traffic where possible.

**Method:** boot against malformed JSON, missing optional files, inaccessible SQLite/data directory, invalid secrets, and valid empty state.

**Pass condition:** critical corruption fails clearly; recoverable/optional state produces bounded warnings rather than unnecessary outage.

## ST-013 — Health/MCP readiness

**Claim:** health checks must distinguish process liveness from dependency/readiness failures without rebuilding MCP per request.

**Method:** healthy boot, MCP initialization failure, unavailable data store, degraded optional subsystem.

**Pass condition:** `/health` remains cheap; readiness signal is explicit. Do not instantiate a new FastMCP server inside every health request.

## ST-014 — Multi-worker state integrity

**Claim under review:** increase uvicorn workers for scale.

**Known evidence:** prior 4-worker deployment corrupted JSON-backed authoritative state because workers maintained independent in-memory ledgers and uncoordinated writes.

**Method before any future change:** concurrent writes across >=2 workers with registry/treasury/runtime files, restart, and consistency verification.

**Current decision:** preserve `--workers 1`. Scaling requires storage/locking redesign first.

## ST-015 — MCP mount/path contract

**Claim under review:** mount FastMCP at `/mcp`.

**Known evidence:** the FastMCP sub-app owns `/mcp`; parent empty-prefix mount preserves public `/mcp`. Prior parent `/mcp` mounting produced redirect/path nesting issues.

**Method:** POST initialize/list-tools through public proxy and direct Railway path; verify no 307/404/path doubling.

**Current decision:** preserve `app.mount("", _mcp_app)` and the Vercel `/mcp` proxy regression test.

## ST-016 — 30-tool MCP contract smoke

**Claim:** every advertised MCP tool exists and core call paths remain invocable.

**Method:** compare decorators/list_tools/server card; smoke read-only tools; use isolated fixtures for writes; verify 7 resources.

**Pass condition:** runtime == advertised == 30 tools; resource count == 7; no schema drift.

## ST-017 — MCP version/deprecation contract

**Claim:** clients need a stable way to detect breaking public-surface changes.

**Method:** inventory `server.json`, server card, package version, instructions, schemas; classify what constitutes breaking change.

**Pass condition:** one documented version authority and deprecation policy; avoid decorative headers that clients do not consume.

## ST-018 — MCP discovery hot-path scalability

**Claim:** public leaderboard/browse/lookups should remain bounded as registry/posts grow.

**Method:** synthetic datasets at 100/1k/10k entries; measure call behavior and allocations; inspect unbounded scans.

**Pass condition:** bounded limits and acceptable cost. Cache only where measurements justify it.

## ST-019 — Cursor loss/recovery

**Claim:** chat clients can recover if local `since_id` is lost.

**Method:** join/read/send, lose cursor, reconnect, request recent page; inspect server cursor semantics.

**Pass condition:** recovery behavior is documented and bounded. Do not add server state if current cursor storage already solves the problem.

## ST-020 — Governance-before-persistence

**Claim:** rejected governed actions must not leave authoritative mutations behind.

**Method:** force governance denial for chat/post/vote paths; compare stores/audit before and after.

**Pass condition:** denied actions have no authoritative side effect except allowed audit evidence.

## ST-021 — Retry/idempotency semantics

**Claim:** clients can safely recover from transport timeouts without duplicating destructive writes.

**Method:** replay requests for idempotent and non-idempotent tools; simulate timeout after commit; inspect duplicate records.

**Pass condition:** tool annotations/docs accurately state retry behavior; idempotency keys added only to flows needing them.

## ST-022 — Rollback/release verification

**Claim:** a bad release can be detected and reversed without relying on manual intuition.

**Method:** document production verification sequence, deployment identifiers, public MCP probe, health probe, and rollback trigger.

**Pass condition:** operator runbook exists and uses already-supported Vercel/Railway controls; no invented automation.

## ST-023 — `create_app` modularization value

**Claim:** server setup is too large and should be split.

**Method:** measure responsibilities/import coupling/testability; identify concrete defects caused by current layout; compare refactor blast radius.

**Pass condition:** refactor only if it removes demonstrated coupling/risk. Structural churn alone is not a hardening win.

## ST-024 — Production secrets and rotation

**Claim:** required production secrets are present, fail closed, and can be rotated without silent auth breakage.

**Method:** missing admin/JWT secret boot, key rotation, old-token behavior, logs, config docs.

**Pass condition:** no secret values in logs; missing critical production secret behavior is explicit; rotation procedure documented.
