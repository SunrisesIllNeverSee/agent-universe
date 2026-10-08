# H5 Communications Lane — Independent Falsifier Review

**Verdict: FAIL**

The builder's ten claims are accurate as far as they go — every REST-side
hardening item verified true. But the same invariants do not hold on the MCP
transport, which the lane touched (claim 4) without porting the surrounding
auth/notification contract. Two cross-principal write holes and one dead
credential path in `app/mcp_bridge.py`, plus a deterministic PII leak through
the public `/api/audit` feed, break the lane's stated privacy and
thread-auth invariants.

Builder suite: **454/454 green.** Falsifier suite (`tests/test_h5_falsifier.py`,
21 probes): 19 pass, **2 fail** (H5F-01, H5F-02); the remaining findings are
code-verified or documented-as-exposure.

## Findings by severity

| Severity | Count | IDs |
|---|---|---|
| HIGH | 3 | H5F-01, H5F-02, H5F-03 |
| MEDIUM | 2 | H5F-04, H5F-05 |
| LOW | 3 | H5F-06, H5F-07, H5F-08 |
| INFO | 1 | H5F-09 |

## Top 3 findings

1. **H5F-01 — MCP `market.message` is an unauthenticated cross-principal write
   into private threads.** `app/mcp_bridge.py:656-689` authenticates the caller
   by api_key but never checks `thread.agent_id == agent.agent_id`. Any
   registered agent can inject `sender_type: "agent"` messages into any other
   agent's negotiation thread — spoofed negotiation content that the poster
   will attribute to the counterparty. REST enforces this at
   `kassa.py:654-657`. Reproduced live: returns `{"status": "sent"}`.
2. **H5F-03 — MCP `market.stake` creates threads whose poster credential is
   undeliverable.** `mcp_bridge.py:606-653` generates `magic_token`, stores
   only the hash (good, claim 4 true), then **drops the plaintext** — no
   `send_magic_link`, no return field, no operator alert. Compare
   `kassa.py:380-390`. Every MCP-created thread is one the poster can never
   open; the agent negotiates into a void.
3. **H5F-05 — Public `GET /api/audit` exposes PII the lane just locked down.**
   `core.py:127-129` serves the full audit log unauthenticated.
   `kassa.py:1296-1300` writes `from_email` into it on every public contact
   submission; `operator.py:273` writes applicant `name` on every
   `/api/inbox/apply`; `operator.py:218` writes contact `name`/`subject`. The
   admin gate added to `/api/inbox` and `/api/kassa/messages` is bypassed by
   reading the same PII from `/api/audit`. Test confirms both values present.

## Attacks run

- **Forged admin credentials** on `GET /api/inbox` + `GET /api/kassa/messages`:
  no header, wrong key, empty key, right key in `X-API-Key`/`Authorization`,
  `?admin_key=` query param — all 403. **Held.** (`admin_key_matches` reads
  `X-Admin-Key` only, `hmac.compare_digest`, fails closed — auth.py:25-34.)
- **Agent Bearer (api_key and JWT) on both admin GETs** — 403. Correct
  fail-closed; agents cannot read the operator inbox. **Held.**
- **POST `/api/inbox/apply` and `/api/kassa/contact` still public** — 200.
  **Held.** `"/api/inbox"` GET-prefix does not swallow the public write.
- **Prefix collisions:** `"/api/inbox"` also gates a hypothetical
  `GET /api/inbox-foo` (over-broad but harmless — no such route);
  `"/api/kassa/messages"` collides with no public route. No false-negative
  gaps found.
- **WS event PII sweep:** every `state.emit` site in `app/routes/*.py`
  audited. `inbox_application`, `kassa_contact`, `kassa_thread_message`,
  `inbox_updated`, forum emits, `slot_filled`/`slot_left` all carry
  public-safe envelopes. **Held** — with one structural caveat: `state.emit`
  broadcasts to the *unauthenticated* `public_hub` too (deps.py:53-58), so any
  future PII field added to `message_added`/`kassa_stake`/`audit_event`
  payloads leaks by default. `audit_event` emits `audit.recent(1)` — newest
  row, not own row — a real cross-talk race (H5F-06).
- **`/ws/thread/{id}` auth:** no creds → close; wrong `?magic=` → close;
  hash-compare against stored sha256. **Held** (non-constant-time `!=`
  compare noted, negligible vs 256-bit token entropy).
- **Magic token strength:** `secrets.token_urlsafe(32)` (REST) /
  `token_urlsafe(24)` (MCP) → sha256 storage; not brute-forceable. **Held.**
- **Thread GETs strip:** single-thread GET strips magic fields; the agent
  thread *list* does not (H5F-07, low).
- **Forum emit ordering:** emits fire only after `set_pinned`/`set_locked`
  return True and after insert commits. **Held.**
- **Missions emits:** `slot_filled`/`slot_left` after `_save_slots` inside
  `slot_lock`; `missions.html:446` listens for exact names. **Held.**
- **Frontend wiring:** no `frontend/*.html` calls dead `/api/message`;
  `console.html:1290` POSTs `/api/messages` — `MessageCreate` (models.py:101)
  accepts `sender/text/channel/role_context`. **Held.** `POST /api/messages`
  rides the `"/api/message"` operator-write prefix → agent bearer or admin.
- **MCP parity:** `agent.profile` strips `operator_contact` on the public
  path (mcp_bridge.py:737). **Held.** But `market.message`/`market.stake`
  diverge as above; `market.stake` also skips the dup-stake check, the
  `kassa_stake` event, operator alert, and never persists `amount` (H5F-09).
- **`/api/state`, `mcp_read`, `/ws` public surface:** exposes runtime
  messages only — the "open square" chat is public by design; agent-inbox
  content does not flow into it (inbox is a separate store, readable only
  via Bearer `GET /api/agent/inbox` or keyed `agent.inbox` MCP). **Held.**
- **Bonus surface defect (pre-existing, not H5-introduced):** agent
  `DELETE /api/kassa/stakes/{id}` is unreachable — middleware 403s before the
  handler's ownership check (H5F-08).

## What "fixed" looks like

- mcp_bridge `civitae_message`: add `thread.agent_id == agent.agent_id` and
  `thread.status == "open"` checks, then mirror REST post-commit side effects
  (thread_hub broadcast + poster notification).
- mcp_bridge `civitae_stake`: deliver the plaintext magic token to the poster
  (`send_magic_link` or `notify_agent` fallback), exactly like
  `kassa.py:378-390`.
- PII out of the public audit feed: gate `/api/audit` or stop logging
  `from_email`/`name`/`subject` from public write paths.

Re-run `tests/test_h5_falsifier.py` after corrections — the two failing tests
must flip to the `error` branch, and H5F-05's assertions must invert.

---

## Re-verification (post-corrections pass)

**Verdict: CONDITIONAL — bounded corrections**

Suite: **475/475 green** (`pytest tests/ -x -q`), including the updated
`test_h5_falsifier.py` (21 probes, all passing with inverted assertions where
the builder hardened the code).

### Per-finding status

| Finding | Status | Evidence |
|---|---|---|
| H5F-01 foreign-thread MCP write | verified_fixed | `mcp_bridge.py:745-747` rejects `thread.agent_id != agent.agent_id` with `rejected_not_owner`; falsifier test passes |
| H5F-02 closed-thread MCP write | verified_fixed | `mcp_bridge.py:748-750` returns `rejected_closed`; test passes |
| H5F-03 undeliverable poster credential | verified_fixed | `mcp_bridge.py:661-698` calls `send_magic_link` with `@signomy.xyz` → registry `email`/`operator_contact` fallback via `agent_for_email`, plus `notify_agent` for registered posters |
| H5F-04 missing MCP post-commit side effects | verified_fixed | `state.loop` captured in lifespan (`server.py:180`); `civitae_message` schedules `thread_hub.broadcast` + public-safe `kassa_thread_message` envelope via `run_coroutine_threadsafe`, plus poster email + inbox notify (`mcp_bridge.py:766-830`). Residual: if `state.loop` is unset (stdio MCP w/o app), emits silently skip — acceptable, documented |
| H5F-05 public /api/audit PII | verified_fixed | PII scrubbed at source: `contact_received` logs `{id, post_id, tab}` (kassa.py:1296), `form_submitted` logs `{id}` (operator.py:218), `application_received` logs `{id, role}` (operator.py:273), `post_submitted`/`prompt_injection_blocked` likewise. Fresh-app probe: 0 PII hits in `/api/audit`. Note: `governance meeting_called` still logs caller+subject — governance is public-by-design, accepted |
| H5F-06 audit_event foreign-row race | **partial_fix** | economy/kassa/missions/agents + provision:324 converted to `_audit_entry` from own `log()` return. **19 `audit.recent(1)` emit sites remain racing: 13 in `core.py` (lines 173,187,207,221,244,311,399,434,533,568,592,660,664) and 6 in `provision.py` (228,361,463,483,559,590).** Impact is now bounded (PII removed from audit details by H5F-05), but an `audit_event` payload can still name the wrong action under interleaving — event-integrity wart, no longer a PII vector |
| H5F-07 thread list magic_token leak | verified_fixed | `kassa.py:588-592` strips `magic_token`/`magic_token_plain` in the list endpoint |
| H5F-08 DELETE stake unreachable | verified_fixed | `/api/kassa/stakes/` added to `_PUBLIC_WRITE_PREFIXES` (server.py:303); handler still enforces JWT ownership (kassa.py:442-448) |
| H5F-09 MCP stake parity gaps | verified_fixed | dup-stake 409 parity (607-614), `amount` persisted on stake row (624), `kassa_stake` envelope emitted on app loop (702-716), operator-side notification path via send_magic_link/notify_agent |

### New attacks run this pass

- Re-ran all 21 falsifier probes — all green.
- Fresh-app `/api/audit` PII probe — 0 hits (scrub confirmed end-to-end).
- Grep sweep for residual `recent(1)` emit sites — found the 19 in
  core.py/provision.py above (H5F-06 residual).
- `provision.py` `_audit_entry` audit — only line 324-325 uses the returned
  entry; 6 sibling sites still race (consistent with H5F-06 partial).
- MCP `civitae_message` unauthenticated path returns `{"error": ...}` while
  rejections return MessageResult-shaped dicts — cosmetic schema
  inconsistency, pre-existing, noted only.

### Remaining required correction (bounded)

Convert the 19 remaining `audit.recent(1)[0]` emit sites in
`app/routes/core.py` and `app/routes/provision.py` to emit the `AuditEvent`
returned by each endpoint's own `audit.log(...)` call, matching the pattern
already applied in economy/kassa/missions/agents. No new schema work needed.

## Final re-verification (H5F-06 residual)

**Verdict: PASS**

- Suite: **475/475 green** (`pytest tests/ -x -q`) — includes 21 falsifier probes.
- Residual sweep: **zero** `audit.recent(1)` emit sites remain in `app/` —
  all 19 converted. Adjacent-log sites bind `_audit_entry = audit.log(...)`
  (core.py file_uploaded/session fork/starred; all 6 provision.py sites).
  Inner-logged sites capture `_ac = state.audit_cursor()` before the mutation
  and emit via `state.emit_audit_since(_ac)` (`deps.py:66-75`).
- Cursor arithmetic verified against `moses_core/audit.py`: ledger ids are
  0-based (`len(_entries)`); `AuditEvent.id = ledger_id + 1`; cursor returns
  `event.id - 1` = the newest row's ledger id, so `since(cursor)` yields
  exactly the rows logged after the cursor — no skip, no dupe (probed live:
  2 rows logged → both emitted; 0 logged → none).
- No new findings. Lane closes clean: 9/9 verified_fixed, 0 open.
