---
type: Reference
title: Session Resume — pick up here
description: Session Resume — pick up here — archived documentation in docs/.
tags: [documentation, archive, docs]
timestamp: 2026-08-19
---

# Session Resume — pick up here

**Last checkpoint:** 2026-05-05

---

## Where everything stands

### MCP Distribution — DONE
| Platform | Status |
|---|---|
| Official MCP Registry | ✅ `xyz.signomy/civitae` v1.1.2 active |
| Smithery | ✅ `burnmydays/civitae`, 100% quality, 19 tools, TS SDK published |
| Glama | ⏳ paused mid-Docker-config (see below) |
| PulseMCP | ✅ live |
| AI Agents Directory | ✅ listed (badge in README) |
| PyPI `civitae-mcp` | ✅ v0.2.0 live |
| Agentic.ai | ⏳ blocked on business email |

### Live endpoints
- `https://signomy.xyz/mcp` — 19 tools, streamable-http
- `https://signomy.xyz/.well-known/mcp-server-card.json` — discovery card
- `https://registry.modelcontextprotocol.io/v0/servers?search=xyz.signomy%2Fcivitae` — registry proof

---

## Pick up here next session

### Immediate: finish Glama Docker build
Glama wants a Dockerfile config to host the server. I gave the values; you were about to paste them in. **Paste these into the Glama form:**

**Build steps:**
```json
["pip install --no-cache-dir -r requirements.txt"]
```

**CMD:**
```json
["sh", "-c", "python -m uvicorn app.server:app --host 0.0.0.0 --port ${PORT:-8300}"]
```

**Placeholder parameters:**
```json
{
  "CIVITAE_ADMIN_KEY": "dummy-admin-key-not-for-real-use",
  "KASSA_JWT_SECRET": "dummy-jwt-secret-replace-in-prod",
  "RESEND_API_KEY": "re_dummy_for_glama_build_check",
  "OPERATOR_EMAIL": "noreply@signomy.xyz",
  "STRIPE_SECRET_KEY": "sk_test_dummy_for_glama_build_check"
}
```

> Note: Glama already auto-detected base image (`debian:trixie-slim`), Python 3.14, Node 25, and pulled the env var schema from your repo. The three fields above are what's missing.

**Optional:** I can spin up a local Docker test with these exact settings to verify the container boots before Glama tries it. Tell me "test docker" if you want that.

### After Glama: wait on Agentic.ai (blocked on business email)

---

## Open backend backlog (from CLAUDE.md, not blocking)

- Fee Credit Pack purchase/balance/apply endpoints
- Seed Card (points, streaks, badges, 48h banking)
- Sliding Scale Reward Engine
- Phase transition logic (Day 1/8/31)
- Operator auth flow (login → JWT → console)
- Cascade Matcher (AGENTDASH Layer 1)
- Refinery (SIGRANK) — placeholder
- Switchboard (signal routing) — depends on Refinery

---

## Critical fixes from this run (already shipped, for context)

1. **MCP wasn't running on Railway** — `run.py` never executed in prod. Fix: mounted FastMCP into FastAPI at `/mcp`.
2. **DNS rebinding protection** blocked all prod hosts (HTTP 421). Fix: `enable_dns_rebinding_protection=False`.
3. **Multi-worker session sharing** broke `tools/list` after `initialize`. Fix: `stateless_http=True`.
4. **`from __future__ import annotations`** broke `Annotated[type, Field(description=...)]` parameter descriptions. Fix: removed import.
5. **Tool naming** flat `civitae_register` → dot-notation `agent.register`. Smithery score jumped.
6. **`/kingdoms` popup** removed; standard SIGNOMY nav restored (page removed from `_nav.js` SKIP list).

---

## Identity / credentials reminder

- **MCP registry private key:** stored in your password manager. The auth file at `signomy.xyz/.well-known/mcp-registry-auth` references the matching public key. To republish: `mcp-publisher login http --domain signomy.xyz --private-key <key>`, then `mcp-publisher publish`.
- **PyPI token:** used once and deleted from `.pypirc`. Create a new project-scoped token at pypi.org if you need to push another version.
- **CircleCI:** config at `.circleci/config.yml` — connect via dashboard if not already done.

---

*Resume by reading this file or asking: "where did we leave off?"*
