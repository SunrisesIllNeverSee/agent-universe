---
type: Baseline Report
title: H5 Communications Hardening — Baseline Verification
date: 2026-10-07
lane: H5 Privacy/Comms
repo: _5_Signomy/1_agent-universe
head: 0f32b1f7f4d146ae16fb7973ef34dc75462ed0b3
branch: main
status: baseline-verified
---

# H5 COMMS BASELINE — 2026-10-07

**Repo:** `/Users/dericmchenry/Developer/_5_Signomy/1_agent-universe`
**HEAD:** `0f32b1f` on `main`, clean working tree at lane start.
**Frozen architecture source:** `/Users/dericmchenry/Developer/_7_labs/signomy-control-surface/` (read-only; not modified).

## Reverified hypotheses

| Hypothesis | Verdict | Evidence |
|---|---|---|
| Agent inbox authenticated, principal-bound, platform-written, pull-only | CONFIRMED | `app/routes/inbox.py:20-62`, `app/inbox.py:23-49` (no `state.emit`) |
| `state.emit()` fans to public hub — unsafe for private content | CONFIRMED | `app/deps.py:53-58` — `emit()` broadcasts to `hub` (unauthenticated `/ws`, "public square" per `core.py:632-637`) AND `public_hub` (`/ws/public`, rejects all commands) |
| `GET /api/inbox`, `GET /api/inbox/{id}` unauthenticated | CONFIRMED | `app/routes/operator.py:278-307` — no auth in handlers; `/api/inbox` absent from `_ADMIN_GET_PREFIXES` (`server.py:310`); test asserts public (`tests/test_routes_operator.py:61-64`) |
| `GET /api/kassa/messages` unauthenticated, returns names/emails/bodies | CONFIRMED | `app/routes/kassa.py:1300-1302` — no auth anywhere on the path |
| MCP `market.stake` stores plaintext magic token; REST stores hash | CONFIRMED | `app/mcp_bridge.py:627` plaintext vs `app/routes/kassa.py:568` `_hash_key()`; verify always hashes presented token (`kassa.py:602,625,659`) → MCP-minted threads fail poster `?magic=` auth |
| Mission comms = channel slug, no per-mission ACL | CONFIRMED | `missions.py:54,269`; no `/api/missions/{id}/messages` route; held — not invented in this lane |
| Forums produce no realtime events | CONFIRMED | zero `state.emit` in `app/routes/forums.py`; page is fetch/poll (`forums.html`) |
| Console POSTs `/api/message` (nonexistent); canonical is `/api/messages` | CONFIRMED | `frontend/console.html:1290`; route is `core.py:181` (`MessageCreate` requires `sender`+`text`) |
| `missions.html` listens for `slot_filled`/`slot_left`; backend emits only `audit_event` | CONFIRMED | `frontend/missions.html:446` vs `missions.py:879,949` |
| `operator_contact` stripped from public posts but returned by `agent.profile` | CONFIRMED | `public_projection.py:9` strips; `mcp_bridge.py:731` public handle-path returns all fields except key_hash/key_prefix/signup_ip. Field doc: "not shown publicly" (`mcp_bridge.py:288`) → **defect**, not intentional |

## Additional defects found during baseline (same privacy class)

| Defect | Evidence |
|---|---|
| `kassa_contact` emits the **full entry** (from_name, from_email, message body) to the public websocket hubs | `kassa.py:1292` — PII broadcast to any unauthenticated `/ws` or `/ws/public` client |
| `inbox_application` emits the **full application** (name, handle, message) publicly | `operator.py:274` |
| `kassa_thread_message` emits the **full private negotiation message** (text + sender) on the global hubs | `kassa.py:685-689` — the scoped `state.thread_hub` broadcast exists and stays; the global emit is the leak |
| MCP `agent.profile` self-view also returns `key_prefix` | `mcp_bridge.py:738` — excludes only `key_hash` |

## Mechanism chosen

`_ADMIN_GET_PREFIXES` (middleware, fail-closed) extended with `/api/inbox` and
`/api/kassa/messages`; handlers additionally gain `require_admin()` in-handler
for defense in depth, matching the `operator.py` convention. No new auth scheme
introduced — the operator review workflow already uses `X-Admin-Key`.
No frontend callers of these GETs exist (grep: only `helpwanted.html` posts to
`/api/inbox/apply`), so no UI compatibility shim is needed.
