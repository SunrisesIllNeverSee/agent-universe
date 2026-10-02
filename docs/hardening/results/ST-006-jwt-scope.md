# ST-006 Result — JWT Expiry, Rotation, and Scope

**Status:** PARTIAL / NO IMMEDIATE SECURITY PATCH  
**Area:** identity / session tokens

## Review claim

JWTs lacked a hardened rotation/scoping story and should gain audience claims and verification.

## Verified current behavior

### Production secret handling

`app/jwt_config.py` already fails startup on Railway if neither `KASSA_JWT_SECRET` nor `JWT_SECRET` is configured. It does not silently use an ephemeral production secret.

### Rotation

The verifier already supports `KASSA_JWT_SECRET_PREV`, allowing a previous secret during rotation.

### Expiry

The active REST issuers in both provision and KA§§A issue JWTs with:

- `sub`
- `name`
- `iat`
- `exp` = 24 hours

PyJWT verification enforces expiry.

### MCP helper

`app/mcp_bridge.py` contains a local `_issue_jwt` helper with no expiry, but code search shows it has no callers. The MCP registration tool returns an API key, not this JWT.

## Remaining gap

Tokens have no explicit `aud`/`iss` boundary. That is only a security gain if CIVITAE has multiple JWT-consuming trust domains. Adding it immediately would invalidate current tokens/consumers unless migrated carefully.

## Decision

- The "JWTs are non-expiring / production secret is not hardened" claim is **disproved** for active issuance paths.
- Audience/issuer claims remain a **future compatibility-hardening option**, not an emergency patch.
- Dead MCP JWT helper should be removed only in a low-risk cleanup/refactor batch, not as part of a live auth change.
