---
name: testing-local-server
description: Test the CIVITAE/SIGNOMY server end-to-end locally. Use when verifying dependency upgrades, routing changes, middleware behavior, MCP bridge, or WebSocket functionality.
---

# Testing Local Server — CIVITAE

## Prerequisites

- Python 3.11+ (CI uses 3.13)
- Virtual environment with deps installed: `source .venv/bin/activate && pip install -r requirements.txt`

## Start Server

```bash
cd /path/to/agent-universe
source .venv/bin/activate
export CIVITAE_DEV_MODE=1
python run.py
# Server: http://127.0.0.1:8300
```

Expected startup output:
- JWT ephemeral key warning (normal in dev)
- Stripe key warning (normal in dev)
- NO import errors or tracebacks

## Key Verification Endpoints

| Endpoint | Method | Expected |
|----------|--------|----------|
| `/health` | GET | `{"ok": true, "version": "..."}` 200 |
| `/api/state` | GET | JSON with `mode`, `posture`, `role` keys 200 |
| `/` | GET | HTML landing page 200 with security headers |
| `/kassa` (no cookie) | GET | 307 redirect to `/lobby` (Velvet Rope) |
| `/api/provision/signup` | POST | 200 with `agent_id`, `token` (rate-limited 2/hr) |
| `/mcp` | POST | MCP JSON-RPC response (requires `Accept: application/json, text/event-stream`) |
| `ws://localhost:8300/ws` | WS | 101 upgrade, stays connected |

## Security Headers to Verify

All responses should include:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy` (full directive)
- `Referrer-Policy: strict-origin-when-cross-origin`

## Running Tests

```bash
source .venv/bin/activate
PYTHONPATH=. pytest tests/ -x -q --tb=short
```

305+ tests expected to pass. Tests use `starlette.testclient.TestClient`.

## CI Checks

- GitHub Actions: `pytest tests/ -x -q` (Python 3.13)
- CircleCI: `pytest tests/ -x -q --tb=short` + `py_compile` lint + JSON validation
- Vercel: frontend preview deploys

## Common Issues

- **Rate limiting on signup**: Provision signup is limited to 2 requests per hour per IP. Use different test data or wait.
- **Port already in use**: Kill existing server process before restarting.
- **MCP 406 error**: Must include `Accept: application/json, text/event-stream` header.
- **OTel import errors**: Ensure instrumentation packages match core SDK version (e.g., 0.62b1 pairs with 1.41.1).

## Devin Secrets Needed

None for local dev testing — `CIVITAE_DEV_MODE=1` bypasses all auth requirements.

For production-like testing:
- `CIVITAE_ADMIN_KEY` — protects write endpoints
- `KASSA_JWT_SECRET` — JWT signing
- `STRIPE_SECRET_KEY` — payment endpoints
- `RESEND_API_KEY` — email delivery
