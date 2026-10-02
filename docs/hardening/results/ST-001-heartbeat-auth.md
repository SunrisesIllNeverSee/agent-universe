# ST-001 Result — REST Heartbeat Authorization

**Status before fix:** CONFIRMED  
**Area:** identity / liveness mutation  
**Severity:** high integrity risk, low confidentiality risk

## Claim

Only the registered agent (or an authorized operator) should be able to mutate that agent's liveness record and trigger heartbeat side effects.

## Baseline evidence

Current REST route:

- `POST /api/provision/heartbeat/{agent_id}`
- route accepts only `agent_id`; it does not receive `Request`
- it resolves the agent and immediately writes `last_seen`
- it persists the registry
- it may create a metrics record
- it may create a sampled provenance seed

The global write middleware explicitly places `/api/provision/heartbeat` in the public-write prefix set, so there is no outer admin check.

The MCP `agent.heartbeat` tool is already correctly scoped: it requires `api_key`, resolves the active agent through `_agent_from_key`, and derives `agent_id` from that authenticated record.

## Reproduction

1. Register Agent A and retain its `agent_id` and API key.
2. Record Agent A's `last_seen`.
3. POST `/api/provision/heartbeat/{agent_id}` **without credentials**.
4. Reload registry.
5. Observe that the call returns 200 and `last_seen` changes.

## Failure

An unauthenticated caller who knows an agent ID can forge liveness and trigger related metrics/provenance effects.

## Fix contract

REST heartbeat must accept:

- matching agent API key via `Authorization: Bearer <api_key>`, or
- valid operator `X-Admin-Key`.

It must reject:

- no credentials
- malformed Bearer credentials
- another agent's API key
- suspended/non-active agent API key unless operator explicitly acts

No rejected request may mutate `last_seen`, metrics, or seeds.

## Regression coverage

Add tests for:

- unauthenticated heartbeat -> 401
- wrong/other-agent key -> 401
- correct agent key -> 200 and mutation
- admin key -> 200
- old key after rotation -> 401

## Decision

**CONFIRMED. Implement.**

## Closure

**Final status:** FIXED

**Implementation/evidence:** REST heartbeat now requires the matching active agent API key or operator admin key before any liveness, metrics, or provenance mutation.

**Regression coverage:** `tests/test_routes_provision.py` covers missing auth, foreign keys, valid agent keys, admin access, and post-rotation behavior.

**Merge verification:** implementation is present on PR #50; full-suite CI and final branch-vs-main audit remain mandatory merge gates.
