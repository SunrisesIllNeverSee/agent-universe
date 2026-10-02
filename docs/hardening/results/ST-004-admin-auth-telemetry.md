# ST-004 Result — Admin Authentication Observability

**Status before fix:** PARTIAL / OBSERVABILITY GAP  
**Area:** operator authentication

## Review claim

Failed admin-key attempts were silent and should be audit-logged.

## Verified behavior

Admin authorization exists at two layers:

1. the global FastAPI middleware for non-public writes and sensitive operator GETs
2. route-local admin guards on selected paths that sit under otherwise public prefixes

The checks fail closed, but rejected credentials are not consistently observable.

## Important logging constraint

Appending every attacker-controlled failed authentication attempt to the immutable provenance/audit spine would create an abuse primitive: an unauthenticated client could grow authoritative audit storage and associated I/O at will.

Authentication failures are security telemetry, not constitutional business actions.

## Fix contract

- emit privacy-safe security logs for rejected admin authentication
- never log the provided key
- use a hashed client fingerprint rather than raw IP
- throttle repeated identical rejection logs
- keep successful business/operator actions in their existing domain audit trail rather than duplicating every successful header check
- use one shared constant-time admin-key comparison helper for middleware and route-local guards

## Decision

**PARTIAL. Implement security telemetry, not unbounded provenance writes.**
