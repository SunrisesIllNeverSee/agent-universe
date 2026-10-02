# ST-002 Result — API-Key Rotation Authority

**Status before fix:** CONFIRMED  
**Area:** identity / credential rotation  
**Severity:** critical credential-integrity defect

## Claim

A successful API-key rotation must make the returned new key authoritative, invalidate the old key, and survive registry reload.

## Baseline evidence

Current `POST /api/provision/key`:

1. finds the agent
2. generates `new_key`
3. updates only `agent["key_prefix"]`
4. logs `key_rotated`
5. returns the new secret

It does **not** update `agent["key_hash"]` and does **not** call `runtime.persist_registry()`.

Therefore the returned replacement key is not authoritative while the previous key hash remains valid.

The route is currently protected by the global admin middleware because `/api/provision/key` is not a public-write prefix.

## Reproduction

1. Register Agent A and save old API key.
2. Verify old key can log in.
3. As admin, POST `/api/provision/key` for Agent A.
4. Receive returned replacement key.
5. Attempt login with replacement key -> expected pre-fix failure.
6. Attempt login with old key -> expected pre-fix success.
7. Reload registry and repeat.

## Failure

The API reports a successful key rotation without changing credential authority. This creates a false security event and prevents actual revocation of a compromised key.

## Fix contract

Rotation must:

- generate the new key
- set `key_prefix`
- set `key_hash = sha256(new_key)`
- persist the registry before returning the new secret
- keep raw secret out of audit logs
- immediately invalidate the old key for REST and MCP authentication

## Regression coverage

Add tests for:

- non-admin rotation rejected
- admin rotation succeeds
- new key works
- old key fails
- registry reload preserves the new authority
- audit contains prefix only, never raw key

## Decision

**CONFIRMED. Implement immediately.**
