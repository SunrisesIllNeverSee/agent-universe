# ST-018 Result — MCP Discovery Hot-Path Scalability

**Status:** PARTIAL / ONE MEASURED STRUCTURAL HOT PATH  
**Area:** MCP read scalability

## Baseline findings

### KA§§A browse

`market.browse` historically called `KassaStore.load_posts()`, which executed a SQLite `SELECT ... ORDER BY ...` with no `LIMIT`, fetched every matching row into Python, optionally scanned every title/body for search, and only then sliced the requested result count.

That means the public result cap did not bound database work.

### Agent leaderboard

`agent.leaderboard` scans the in-memory registry and calculates tier data for each agent before slicing. The result is now hard-capped at 100 under ST-011. The registry scan remains O(n), but it is in-memory and no evidence yet justifies a cache with invalidation complexity.

### Forums

`ForumsStore.list_threads()` already clamps limit to 100 and pushes `LIMIT/OFFSET` into SQLite.

## Decision

**PARTIAL.**

- Push KA§§A search and result limit into SQLite for the MCP path.
- Keep the public result cap from ST-011.
- Do not add a generic 5-minute cache to leaderboard/browse until measurement demonstrates it is needed.
- Preserve immediate visibility of registry/status changes over speculative cache speed.

## Closure

**Final status:** PARTIAL

**Implementation/evidence:** the measured KA§§A discovery hot path now pushes search and limit into SQLite. Generic time-based caches were intentionally not added without measurement.

**Regression coverage:** MCP browse contract tests exercise bounded result behavior; store behavior remains covered by the KA§§A test suite.

**Remaining work:** benchmark larger registries/posts before adding any further cache or indexing layer.
