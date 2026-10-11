# P4 mission integrity — evidence

Branch `claude/p4-mission-integrity` (base `feat/signomy-p3-shell` @ c5c9b6f).

| Step | SHA | Result |
|------|-----|--------|
| P4_BASELINE | ba60574 | 7 passed + 1 strict xfail (orphan proof) in tests/test_p4_mission_integrity.py |
| Repair | df8f540 | 14 passed; full suite 544 passed (baseline 530 + 14) |

## Defect
`POST /api/slots/create` with `mission_id` omitted minted `mission-<hex>`, persisted slots
carrying it, and never wrote a mission record, so `GET /api/missions/{id}` returned 404.
Sibling `/api/slots/bounty` was fixed forward in b06ae00.

## Fix (app/routes/missions.py, `create_slots_from_formation` only)
- Only when `mission_id` is omitted: mint an id not present in missions or slots (re-mint on collision),
  write a mission record (shape mirrors b06ae00: `origin="slots_create"`, `status="active"`,
  `governance_at_launch`, `slot_ids`), then save slots.
- Mission record is written BEFORE slots, so a crash between the two writes leaves an empty mission,
  never a slot pointing at nothing.
- `agents: []`, `objective: ""` — no owner/principal/Agreement semantics chosen.

## Unchanged (pinned by tests)
- Auth: middleware-only (`/api/slots/` operator write prefix): no creds / bad admin key / bogus bearer
  -> 403 with zero store mutation; admin key and registered-agent bearer -> 200.
- Audit: exactly one `deploy/slots_created` event per call; seed (`slot_created`) and response keys
  (`created, mission_id, slots, seed_doi`) unchanged.
- Caller-supplied `mission_id` passes through verbatim, no validation, no mission record
  (changing that would break existing callers; belongs to later binding-precondition nodes).

## Retry / idempotency semantics (documented, tested)
- Omitted id: NOT idempotent. Each call mints a new mission and new slots (same as pre-fix, minus the orphan).
  No duplicate or colliding ids: ids are checked against existing missions and slots and re-minted on collision
  (forced-collision test).
- Supplied id: unchanged — a retry appends another batch of slots under the same id; still no mission record.
  Dedupe would need an idempotency key, which is an owner/design decision (not made here).

## Falsifier (fix reverted via `git checkout` of missions.py, then re-applied)
- Reverted: 4 failed, 10 passed — `test_minted_mission_id_resolves_to_mission_record`,
  `test_slot_mission_linkage_both_ways`, `test_every_minted_id_resolves_across_repeated_calls`,
  `test_minted_id_avoids_existing_ids`. Auth/audit/passthrough pins stayed green.
- Restored: 14 passed.

## Isolation
Tests use the session `app` fixture rooted at a tmp dir (conftest `tmp_root`); real `data/` is never touched.

## Out of scope / not done
No backfill of historical orphans, no Agreement/WorkEntry records, no escrow, no migrations, no push.
Production orphan state remains unverified (Q13). Owner decisions needed: none for this repair.
Residual gaps: supplied unknown `mission_id` still produces orphan slots (deferred by design);
no cross-process file lock on the JSON stores (pre-existing; same as bounty).
