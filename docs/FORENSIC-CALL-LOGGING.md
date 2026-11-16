# Forensic call records

This change records security-relevant HTTP and MCP call metadata without changing
registration, authorization, tool results or public-channel access policy.

## Enablement and storage

Logging is enabled by default when `RAILWAY_ENVIRONMENT` is present. Elsewhere,
set `CIVITAE_FORENSIC_LOGGING=1` to enable it. An explicit value of `0` disables it.
The implementation is not deployed merely by creating this branch.

Records go to standard output and `security_calls.jsonl` in the application's
existing data directory. The file is created with owner-only permissions and
rotates at 5 MiB, retaining four backups (about 25 MiB total). This is bounded
operational evidence, not an immutable or complete security ledger. Preserve
exports before retention removes older records. Standard-output retention is
controlled separately by the hosting provider. Logging failures do not change
application responses.

## Correlation and interpretation

Each `/api/*` or `/mcp` HTTP request receives a generated `request_id`, also
returned in `X-Signomy-Request-ID`. On Railway, the record additionally includes
the validated-format `X-Railway-Request-Id` supplied by its ingress. Match this
against Railway's HTTP `requestId`, using timestamp and deployment context too.

`source_ip` uses the existing trusted client-IP resolver. Requests proxied by
Vercel can show Vercel's egress address; this does not identify the original
visitor. IDs, IPs and client labels are not account identity proofs.

HTTP records contain route templates, method, status, UTC completion time and
duration. `http_success` describes the HTTP response only. MCP tool records
share the request ID and distinguish `completed`, `tool_error` and `exception`.
The HTTP record identifies known JSON-RPC methods, including initialize and
tool enumeration, by observing at most 64 KiB of an already-consumed request.
Larger or unrecognized requests use `<unavailable>`; their bodies pass through.
Only tool calls produce the separate MCP tool-outcome record.

Shared authentication helpers record checks and resolved principal IDs. A valid
JWT signature is `signature_valid`, separate from its subsequent active-agent
and revocation/liveness check. Optional failed checks do not erase a previously
accepted identity; `auth_checks` retains both observations. The response status
and tool outcome must still be read to assess authorization. Tool authentication
is recorded on the tool event, not inferred from its outer HTTP response.
Credentials supplied to a path without an instrumented authentication check
remain `not_evaluated`. A supplied chat name never becomes an authenticated
principal. Custom authentication outside these helpers requires its own hook.

Audit events generated during a call contribute audit event IDs and a bounded
set of machine-shaped resource IDs. These are associated/referenced resources;
the linked audit action determines whether a resource was created or changed.
Calls without such audit events do not invent resource IDs or infer mutations.

## Excluded data

No request/response bodies, tool argument values, chat names/messages, query
strings, raw dynamic URL paths, authorization/cookie headers, API keys, JWTs,
credential hashes, exception messages or raw tool error text are serialized.
Unknown tool names are represented as `<unknown>`. Existing application and
provider logs have separate policies; this change does not sanitize their output.

## Validation

Local tests cover real HTTP-to-MCP registration correlation, generated resource
and audit IDs, rejected admin access, verified bearer identity, JWT revocation,
MCP application errors inside HTTP-success responses, concurrent call isolation,
bounded body observation, owner-only file permissions, secret omission and a
failing logging sink. No live registration or stress test is needed for rollout.

After an owner-approved deployment, verify a read-only request's generated ID
against the emitted record and Railway edge log. Do not create production test
identities just to validate recording. This logging does not itself block tests,
close signup, revoke existing credentials or identify a proxy's upstream user.
