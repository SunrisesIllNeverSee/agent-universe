# P5 integration notes

Branch `claude/p5-integration`, base `08c3a9b`. Merge commits, no rebase. Order: escrow, hardening-merge,
civitas-surface, provenance, proofpress-anchor. (The task named the branches `claude/claude/p5-*`; the real
local names are `claude/p5-*`.)

## Conflicts
- escrow, hardening-merge, civitas-surface, provenance: merged clean.
- proofpress-anchor: import-line conflicts only, in `app/routes/economy.py` and `app/routes/missions.py`.
  Resolved by keeping both sides: `from app.seeds import create_seed, create_seed_loud` plus
  `from app.anchor_outbox import anchor_payout`. Other overlapping edits (connect.py, economy.py, missions.py,
  server.py) auto-merged.

## Integration fix
- The anchor branch's `anchor_escrow_release` hook had no call site because escrow did not exist there.
  It is now called from `release_to` in `app/routes/escrow.py` after the release is committed. The hook takes an
  optional `release_id` so partial releases of one escrow get distinct dedupe keys (previously one key per
  escrow, which would have collapsed them). Test: `test_escrow_release_queues_one_anchor_per_release`.

## Not changed
No rates, no money-path test weakened, nothing pushed or deployed. R_LIVE and P5_HARDENING_VERIFIED remain
owner-held. Open items of each track are unchanged (see track reports).
