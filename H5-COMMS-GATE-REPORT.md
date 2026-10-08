---
type: Gate Report
title: H5 Communications Hardening — Gate Report
date: 2026-10-08
lane: H5 Privacy/Comms
repo: _5_Signomy/1_agent-universe
baseline_head: 0f32b1f7f4d146ae16fb7973ef34dc75462ed0b3
verdict: PASS (independent falsifier signed off; 9/9 findings verified_fixed)
---

# H5 COMMS GATE REPORT

**Lane:** bounded runtime hardening — existing comm surfaces only; no
redesign, no Phase-1 reopen, no semantic changes.

| Item | Status | Evidence | Remaining issue |
|---|---|---|---|
| A1 `GET /api/inbox` + `{id}` public PII | VERIFIED | `_ADMIN_GET_PREFIXES` + handler `require_admin` (`server.py:310`, `operator.py:283-303`); tests `test_h5_comms.py::test_a1_*` | none |
| A2 `GET /api/kassa/messages` public PII | VERIFIED | same two-layer guard (`kassa.py:1315-1320`); `test_a2_*` | none |
| A3 `operator_contact` classification | VERIFIED | **defect** — field doc says "not shown publicly"; now stripped from public `agent.profile` handle-path (`mcp_bridge.py:737`); `test_a3_*` | none |
| B1 console `/api/message` dead route | VERIFIED | `console.html:1290` → `/api/messages` with `MessageCreate`-conforming body; `test_b1_*` | none |
| B2 `slot_filled`/`slot_left` events | VERIFIED | emitted post-commit only (`missions.py:882-887, 960-965`); `test_b2_*` (success=1 event, failure=0, authoritative ids) | none |
| C REST/MCP magic-token parity | VERIFIED | MCP stores `_hash_key(magic_token)` (`mcp_bridge.py:630`); cross-thread/wrong/malformed tokens rejected; `test_c_*` | none |
| D Town Hall realtime | VERIFIED | `forum_thread_created`/`forum_reply_created`/`forum_thread_pinned`/`forum_thread_locked`, post-commit, payload ⊆ public GET envelope (`forums.py`); `forums.html` refreshes via `/ws/public`; `test_d_*` | none |
| E Communications contract | VERIFIED | `docs/contracts/COMMUNICATIONS-HARDENING-CONTRACT.md` — full surface matrix + holds | none |
| Public-submit flows unbroken | VERIFIED | `POST /api/inbox/apply`, `/api/kassa/contact` still public; 475/475 suite green | none |

## Hardened now (beyond the named scope — same privacy class, found in baseline)

- **Event-payload PII leaks**: `kassa_contact`, `inbox_application`,
  `kassa_thread_message` were broadcasting full PII/private bodies to the
  unauthenticated `/ws` + `/ws/public` hubs → now public-safe envelopes.
- **Cross-principal credential leak**: REST stake response returned the
  poster's `magic_link` to the staking agent → removed (kassa.py:424).
- **Post-commit crash**: `post_thread_message` referenced undefined `agent`
  → 500 after the message commit had already succeeded (kassa.py:725).
- **MCP `market.message`** had no thread-ownership or liveness check
  (cross-principal write into any thread) — now `rejected_not_owner` /
  `rejected_closed`.
- **MCP `market.stake`** created undeliverable threads (token never sent)
  → `send_magic_link` + `notify_agent` parity with REST; dup-stake check +
  `amount` persisted + `kassa_stake` emit added.
- **Public `/api/audit` PII**: contact/applicant PII was logged into the
  audit chain → scrubbed at source (5 sites).
- **`audit_event` foreign-row race**: all 38 emit sites now bind the entry
  this endpoint logged (`_audit_entry` binding or `emit_audit_since` cursor).
- **`GET /api/kassa/threads`** leaked stored `magic_token` hash → stripped.
- **`DELETE /api/kassa/stakes/{id}`** unreachable by agents (middleware 403)
  → added to public-write prefixes; handler still enforces JWT ownership.

## Intentionally held for post-design / WorkEntry integration

- Agent-inbox realtime push — no authenticated/scoped transport exists;
  inbox stays pull-only. Pushing through `state.emit` would leak private
  records publicly.
- Mission-channel ACL — channel is a naming convention; real ACL depends on
  Agreement/WorkEntry/formation authority. Not invented here.
- Forum → Motion promotion — not wired, per frozen architecture.
- Thread close endpoint — `status:"closed"` enforced on read; no route sets
  it. Held.
- MCP `govern.vote` audit-only divergence — H1/H3 lane, out of scope.

## Adversarial findings

Independent falsifier (fresh agent, own probes in `tests/test_h5_falsifier.py`):
first pass **FAIL** — 9 findings (3 HIGH, 2 MEDIUM, 3 LOW, 1 INFO), ledger at
`reviews/H5-Comms-Findings.csv`, review at
`reviews/H5-Comms-Independent-Review.md`. Bounded corrections applied to all 9;
final re-verification **PASS** — 9/9 verified_fixed, 0 open.

## Regression result

`pytest tests/ -x -q` → **475/475 green** (454 pre-existing/builder suite +
21 falsifier probes). Registration, agent inbox, KA§§A stake/thread/message,
forum create/read/reply/moderation, application submission, contact
submission, and websocket base behavior all covered. No live-deployment claim
— local verification only.

## Recommended next runtime lane

H1/H3 — MCP `govern.vote` records votes in audit without mutating motion/vote
state (REST/MCP divergence on the governance surface), plus the held
thread-close endpoint and mission-channel ACL once formation authority lands.
