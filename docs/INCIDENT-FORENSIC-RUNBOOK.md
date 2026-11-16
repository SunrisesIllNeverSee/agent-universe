# Signomy stress-run tracing and registration boundaries

This runbook governs ongoing forensic investigation and safe validation. It does
**not** identify an external operator and does **not** authorize live stress tests.

## Passive fingerprinting

Run `python scripts/incident_fingerprint.py <export.jsonl> [other-export.json] --json-out report.json --md-out report.md`
against **saved** Railway HTTP logs (`railway logs --http --json`) or the
structured `security_call` app records. The program makes no network calls.
It deduplicates matching source+request IDs, recognizes signup/mission/KA§§A/
forum/MPP/slot patterns, and groups calls by time (default ten-minute gaps).

The suite-equivalent ratios are **patterns**, not counts of distinct machines,
humans, processes or credentialed principals. To link a resource creation to an
authenticated request, use the request-ID, authenticated `principal_id`,
audit/resource IDs, and the relevant audit event. A 200 response from `/mcp`
does not establish a successful inner tool action.

For details of the initial implementation, see `docs/FORENSIC-CALL-LOGGING.md`.

## Voluntary test-run markers

The official `scripts/stress_test.py` assigns a new UUID run identifier
(`CIVITAE_STRESS_RUN_ID` may override with 8–64 safe ASCII characters).
Every HTTP request carries:

- `X-Signomy-Test-Run`: run identifier
- `X-Signomy-Test-Suite`: `civitae-stress-v1`

The script report includes its claimed run ID. The server's forensic log records
`client_test_run_id` and `client_test_suite` only when syntax-valid, plus a
truncated SHA-256 user-agent fingerprint. These are **untrusted caller claims**,
not authentication. Old copies of the script and independent testers need not
send them. No URL query, request body, credential or free-text UA is logged.

This suite defaults to localhost. A remote target still requires both
`CIVITAE_URL` and explicit `CIVITAE_STRESS_ALLOW_REMOTE=1`.
Never point an investigative test at production to prove instrumentation.

## Shared registration control

Three paths create durable agents: REST `/api/provision/signup`,
REST `/api/kassa/agent/register`, and MCP `agent.register`.
They now share a persisted rolling creation budget of five per 300 seconds.
REST/KASSA return HTTP 429; MCP returns a validated application `error`
with `retry_after_seconds` inside the RPC outcome. Per-origin limits also
apply when a trusted client origin can be observed.

A process-local lock prevents concurrent calls from overshooting the budget,
and each path reloads the persisted registry immediately before checking it.
The app is deliberately **one worker / one replica**. Do not scale processes
or replicas until these checks move to a transactional database or shared
atomic rate-limit store. The previous REST two/hour per-IP limiter remains.
These are enrollment throttles, not proof-of-personhood controls.

## Preview to production isolation

Vercel's `vercel.json` still contains production API rewrite targets for the
real production deployment. `middleware.js` intercepts `/api`, `/mcp`,
`/health`, `/docs`, and `/ws` requests in **nonproduction Vercel
environments** and returns no-store HTTP 503
`preview_backend_unavailable` rather than forwarding them.
A preview must never be treated as an isolated API test environment just
because its frontend URL is different.

This is a **fail-closed preview gate**, not a working staging backend.
If an isolated preview backend is needed, provision separate credentials and
a separate datastore, then review its routing explicitly before opening writes.
Validate preview API 503 and production API unchanged after deployment.

## Retention / custody

App stdout logs are structured JSON (Railway extracts fields to top level).
The optional on-volume file `/app/data/security_calls.jsonl` is rotating,
not an immutable audit archive. Preserve saved evidence with hashes. Do not
alter or delete prior STRESS registrations during attribution.
Existing WAF source blocks are defense in depth, not identity proof.

## Remaining attribution work

1. Match an actual runner-side report, task transcript, CI job, cron execution,
   or provider egress record to a saved Railway request ID/time.
2. Submit a provider trace packet using the saved source IPs and edge IDs;
   ask the provider to preserve egress records and identify whether execution
   was user-directed or scheduled. Never infer a Meta human or a Claude agent
   from an IP range, UA or supplied model string.
3. Audit any use of the incident-created keys from server-side authenticated
   request records. Credential actions require separate explicit review.
4. `audit-fixture` is a separate, tracked public MCP case; it is not linked
   to the REST stress workflow by authenticated identity or shared request ID.
