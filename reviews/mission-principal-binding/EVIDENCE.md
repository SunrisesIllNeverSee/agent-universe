# Mission principal binding (D-B) — private evidence. NOT FOR PUBLICATION.

Branch claude/mission-principal-binding (base 73894b7). Throwaway tmp-root fixtures only.

## Semantics (contract + code)
- 1G s5 rows `create`/`end`/`update` mission, `form` slots: authority = mission owner; operator acts FOR a named principal.
  Principal = active registry agent resolved from Bearer API key (`app.auth.active_agent_from_bearer`, same primitive as
  server.py `_agent_bearer_ok` and `require_agent_claim`; revoked digests and non-active agents are rejected).
- New field `owner_agent_id` (+ `created_by`: agent|operator), set server-side only. Body values ignored.
- Admin key: allowed, never fabricates an agent principal (owner_agent_id=None, created_by=operator).
- Legacy / operator-created (no owner): agents get 403; admin allowed. No migration/backfill.
- JWT: nothing new accepted. Bearer must match an agent `key_hash`; an agent JWT does not (test_jwt_does_not_authorize).
- Also bound: `/api/slots/bounty` (owner = claiming agent; admin => none) and minted missions in `/api/slots/create`.

## RED (guard + owner binding absent, baseline missions.py)
14 failed, 19 passed — other-agent end/update/slots succeed (200), ownerless records mutable by agents, no owner recorded.

## GREEN
tests/test_mission_principal_binding.py: 33 passed. Full suite: 658 passed (baseline 625 + 33).

## Falsifier (scratch, reverted, not committed): owner comparison neutered (`if False:`)
9 failed, 24 passed — other_agent x3, legacy_ownerless x3, operator_created x3 go RED; reverting => 33 passed.

## Compatibility
- 403 now: any agent key calling end/update/slots-create (existing id) on a mission it does not own, including ALL
  pre-existing missions (no owner) and operator-created missions. Operators (admin key) unaffected.
- Agents' own missions (created after this change) and own bounties keep working.
- Mutated test: tests/test_p3_shell_authority_fixtures.py canary now probes `withdraw` (mission_end is no longer
  middleware-only, so patching the middleware no longer breaches it — defence in depth).
## Not covered (out of lane)
Unknown mission_id on /api/slots/create (other specialist, D-C); tasks/campaigns/mission_dash/deploy mission mutations.
