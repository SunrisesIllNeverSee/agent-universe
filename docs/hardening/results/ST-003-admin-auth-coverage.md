# ST-003 Result — Admin/Cockpit Auth Coverage and Suspended-Key Bypass

**Status before fix:** CONFIRMED  
**Area:** authorization middleware  
**Severity:** high authorization-integrity defect

## Claim

A credential belonging to a non-active agent must not authorize cockpit/operator write prefixes.

## Baseline evidence

The global middleware intentionally permits a registered agent API key on a bounded set of cockpit write prefixes such as:

- `/api/governance`
- `/api/missions`
- `/api/deploy`
- `/api/campaigns`
- `/api/slots/`
- `/api/mission-dash/`

This is an intentional product capability and is not being removed by this test.

However, `_agent_bearer_ok(request)` currently authorizes when **any** registry record has a matching `key_hash`. It does not verify that the record's `status` is `active`.

By contrast, route-local API-key and JWT resolvers for inbox, MCP, KA§§A, and forums explicitly reject non-active agents.

## Reproduction

1. Register Agent A and retain its API key.
2. POST a harmless cockpit mutation (`/api/deploy` with an empty/default update) using Agent A's Bearer API key.
3. Confirm active Agent A passes middleware.
4. Suspend Agent A through the admin endpoint.
5. Repeat the same cockpit request with the same API key.

Pre-fix expected result: the suspended agent still passes the global middleware because only the hash is checked.

## Failure

Suspension does not consistently revoke authorization. A suspended credential remains capable of invoking global cockpit write routes even though MCP, inbox, KA§§A, and forum authorization treat the same principal as inactive.

## Fix contract

`_agent_bearer_ok` must require:

- non-empty matching key hash
- agent status == `active`

The credential comparison should be constant-time where practical.

## Regression coverage

- active agent API key may access an intended cockpit write
- suspended agent's same API key receives 403
- wrong API key receives 403
- admin key remains unaffected

## Decision

**CONFIRMED. Implement narrowly in the global bearer resolver.**

## Closure

**Final status:** FIXED

**Implementation/evidence:** the global cockpit Bearer resolver now requires a matching key hash on an agent whose status is `active`; suspension therefore revokes this authorization path consistently.

**Regression coverage:** `tests/test_agent_readiness.py::test_cockpit_bearer_rejects_suspended_agent`.

**Merge verification:** implementation is present on PR #50; full-suite CI and final branch-vs-main audit remain mandatory merge gates.
