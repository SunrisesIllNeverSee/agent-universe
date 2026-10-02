---
type: Reference
title: JWT Secret Rotation Runbook
description: JWT Secret Rotation Runbook — documentation in docs/.
tags: [documentation, docs]
timestamp: 2026-08-19
---

# JWT Secret Rotation Runbook

## Architecture

All agent JWTs are signed with a single shared secret (`KASSA_JWT_SECRET`).
Tokens expire after 24 hours. The system supports dual-secret graceful rotation
via `KASSA_JWT_SECRET_PREV`.

## When to Rotate

- Suspected secret compromise
- Team member departure with access to Railway env vars
- Periodic rotation (recommended: every 90 days)

## Rotation Steps

### 1. Generate a new secret

```bash
openssl rand -hex 32
```

### 2. Set the previous secret on Railway

Copy the **current** value of `KASSA_JWT_SECRET` into `KASSA_JWT_SECRET_PREV`:

```bash
railway variables set KASSA_JWT_SECRET_PREV=<current-secret-value>
```

### 3. Set the new secret on Railway

```bash
railway variables set KASSA_JWT_SECRET=<new-secret-from-step-1>
```

### 4. Deploy

Railway will redeploy automatically. The new deployment will:
- Sign all **new** tokens with the new secret
- Accept tokens signed with **either** the new or previous secret

### 5. Wait 24 hours

All tokens signed with the old secret will expire naturally (24h TTL).

### 6. Remove the previous secret

```bash
railway variables delete KASSA_JWT_SECRET_PREV
```

This is optional but recommended for hygiene. Once removed, only the current
secret is checked (faster decode path).

## How It Works

`app/jwt_config.py` now issues scoped agent-session tokens with:

- `iss=https://signomy.xyz`
- `aud=civitae-agent`
- `sub=<agent_id>`
- `iat`
- `exp` (24-hour TTL)

Verification:
1. Try scoped decode with `KASSA_JWT_SECRET` (current).
2. If that fails, try `KASSA_JWT_SECRET_PREV` (previous) for zero-downtime secret rotation.
3. During the Phase 2 migration only, an already-issued token without `iss`/`aud` may pass if its `iat` predates the fixed migration cutoff and its original `exp` is still valid.
4. A token that supplies the wrong issuer or audience is never allowed through the legacy fallback.
5. If no current/previous-secret validation path succeeds, the token is invalid.

Signing always uses the current `KASSA_JWT_SECRET`.

## Zero-Downtime Guarantee

- No forced logouts during rotation
- No window where valid tokens are rejected
- Grace period equals token TTL (24 hours)

## Emergency Rotation (Breach)

If the secret is compromised and you need to invalidate all tokens immediately:

1. Set `KASSA_JWT_SECRET` to a new value
2. Do **NOT** set `KASSA_JWT_SECRET_PREV` to the old value
3. Deploy

All existing tokens become invalid. Agents must re-authenticate.

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `KASSA_JWT_SECRET` | Current signing/verification secret | Yes (Railway) |
| `KASSA_JWT_SECRET_PREV` | Previous secret for graceful rotation | Only during rotation window |
| `JWT_SECRET` | Fallback if `KASSA_JWT_SECRET` not set | Legacy only |
