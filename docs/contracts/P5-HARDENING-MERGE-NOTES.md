# P5 hardening merge notes (2026-10-13)

Candidate branch `claude/p5-hardening-merge`, built on `08c3a9b` (claude/p5-money-path). Local only; nothing pushed or deployed.

## Lineage inspection
| Branch | Relation to 08c3a9b | Action |
|---|---|---|
| claude/operational-hardening-2026-10-11 (6249720) | Already an ancestor (via P3/P4 lineage) | None |
| claude/exp-durability (6478ada) | One commit over 6249720: durable EXP | Included through r2 (same change, bcff178) |
| claude/security-hotfix-candidate-ii (54e5ae0) | 15 commits over 292d3ba | Ancestor of r2, included through r2 |
| claude/release-candidate-r2-2026-10-12 (bcff178) | 19 commits over 292d3ba; superset of hotfix-ii + EXP | Merged (`--no-ff`) |

So one merge brought in everything: owner-bound mission/task/campaign mutations, uniform 404 oracle, operator-only /api/governance and /api/deploy, /ws and cockpit principal binding, scoped boost/sponsored, 256-bit agent keys, honest Refinery ("Not yet measured"), frontend repairs, durable EXP.

## Conflicts (single file: app/routes/missions.py, 9 hunks)
All hunks had the same shape: r2 predates Phase 4/5, so the r2 side lacked code that the base added. Resolution in every hunk was to keep the base (HEAD) side while the r2 hardening that merged cleanly around it stays.

1. `MAX_SLOT_PAYOUT` and `_payout_seed` (P5 s2/s3): kept. Needed for operator-only, bounded payout and loud provenance.
2. `_resolve_refs` (P4 entry_mode/post_id/agreement_id validation): kept.
3. `create_mission`: kept the `_resolve_refs` call and the `entry_mode/post_id/agreement_id` fields beside r2's `_owner_fields`.
4. `end_mission`: r2 set `status=completed` before the payout block; the base sets it after the operator-only/bounded payout checks. Kept the base order so a rejected payout cannot leave a mission half-ended. Owner gate (`_mission_gate`) from r2 retained.
5. `create_slots_from_formation`: kept the base's commented principal resolution plus `existing = None` (r2's gate call that follows is unchanged) and the P4 `_resolve_refs` call and the three ref fields on the minted mission record.
6. Bounty mission creation: kept `_resolve_refs` and the three ref fields beside `_owner_fields`.

Money-path check: nothing that moves money comes from the request body (r2 does not touch connect/economy routes); mission-end payout stays operator-only; Stripe account binding untouched. No test dropped from either side.

## Tests
Unit: 1223 passed, 3 skipped (base 1217/3). Full with browser: 1254 passed (base 1248).

## Owner questions
None blocking. Informational: r2's strict owner-binding makes foreign-mission calls return 404 rather than 403 (existing r2 decision).
