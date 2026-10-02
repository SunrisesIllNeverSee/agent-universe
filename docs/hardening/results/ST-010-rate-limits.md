# ST-010 Result — Rate-Limit Correctness, Memory, and Restart Semantics

**Status:** PARTIAL / CURRENT MODEL ACCEPTABLE WITH KNOWN LIMITS  
**Area:** abuse controls

## Review claim

The external review asserted that the in-memory limiter leaks stale IP entries, is unsafe under multiple workers, and should be moved to Redis or persisted to disk.

## Verified current behavior

Four route modules currently carry near-identical in-memory per-IP limiters. Each check:

1. derives a client key from `X-Forwarded-For` or `request.client.host`
2. rebuilds the bucket and removes **all stale entries**, not just the current IP
3. removes timestamps outside the window for the current IP
4. rejects once the configured hit count is reached

Therefore the specific claim that stale idle IPs are never evicted is **disproved**: any subsequent check on that bucket performs global stale-entry eviction.

## Real limitations

- limits reset on process restart/deploy
- implementation is duplicated across modules
- memory is proportional to unique client identifiers seen within the active window
- correctness depends on the deployment proxy providing trustworthy `X-Forwarded-For`
- the limiter is process-local and therefore would multiply limits under multi-worker deployment

## Deployment context

Production is intentionally single-worker. ST-014 forbids increasing workers until authoritative state is redesigned, so a multi-worker rate-limit backend is not an immediate requirement.

Persisting rate-limit hits into the current JSON/file state would add write amplification and contention to a system deliberately kept single-worker after prior state corruption. That is not justified by the present evidence.

## Decision

**PARTIAL.**

- Keep the in-memory limiter for the current single-worker deployment.
- Do not add Redis or disk persistence merely to satisfy the review.
- Treat restart reset and proxy trust as documented limitations.
- Centralization may be considered under ST-023 if it reduces duplicated security logic without changing behavior.
- Add boundary/eviction tests before any future limiter rewrite.

## Closure

**Final status:** PARTIAL

**Implementation/evidence:** the current in-memory limiter is intentionally retained for the single-worker deployment. Redis/disk persistence was not added. Boundary, stale-eviction, and forwarded-client behavior are now regression-tested.

**Regression coverage:** `tests/test_rate_limit_contract.py`.

**Remaining work:** restart reset and trusted-proxy assumptions remain documented limitations; redesign only when deployment/storage architecture changes.
