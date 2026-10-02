# ST-024 Result — Production Secrets, Fail-Closed Behavior, and Rotation

**Status:** PARTIAL / CORE SECRET BEHAVIOR ALREADY SOUND  
**Area:** deployment secrets

## JWT secret

Production behavior is already hardened:

- Railway requires `KASSA_JWT_SECRET` or `JWT_SECRET`
- missing persistent production secret raises during app creation
- `KASSA_JWT_SECRET_PREV` supports a controlled overlap window during JWT-secret rotation
- tokens expire after 24 hours on active issuance paths

## Admin key

`CIVITAE_ADMIN_KEY` is different by design.

When absent in Railway production:

- the app may remain available for public/read/self-service surfaces
- non-public operator writes are fail-closed
- sensitive operator GETs are fail-closed

This is a useful **read-only/degraded operator mode**, not necessarily a reason to take the whole public service offline.

Changing the Railway admin-key environment value and redeploying immediately invalidates the previous key. There is no overlap/previous-key window.

## Gap

Admin-key comparisons are duplicated across middleware and route modules, mostly with direct string equality. The behavior is logically correct but difficult to audit consistently.

## Fix contract

- centralize admin-key comparison in a small behavior-only helper
- use `hmac.compare_digest`
- preserve all existing route authorization boundaries
- do not log raw secret values
- document JWT and admin-key rotation separately because their overlap semantics differ

## Decision

**PARTIAL.** Preserve the current production failure modes; consolidate comparison/logging behavior without rearchitecting authentication.
