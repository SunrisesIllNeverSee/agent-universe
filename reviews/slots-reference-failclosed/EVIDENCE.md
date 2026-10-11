# Evidence: POST /api/slots/create unknown mission_id fails closed (D-C)

Branch claude/slots-reference-failclosed, base 73894b7 (baseline 625 passed).

## Change
app/routes/missions.py, create_slots_from_formation: one early block after
mission_id is determined. A non-empty caller-supplied mission_id must match an
existing mission record (`id` or `mission_id`, exact match, same as get_mission);
otherwise `404 {"error": "Mission not found", "mission_id": <id>}` before any
write (no slots, mission, audit, seed).

## Why 404
Every missions.py lookup miss (get/end mission, tasks, slots) returns
`JSONResponse({"error": "... not found"}, 404)`. 404 keeps one convention.

## Edge-case decisions
- omitted / "" : minted (unchanged, exactly one mission record).
- whitespace-only, case variants, slot ids, ids present only on orphan slots:
  treated as supplied and unknown -> 404 (no trimming/case-folding, matches get_mission).
- unauthenticated: still 403 from middleware before validation.

## Falsifier
Validation reverted (git stash of missions.py): 14 failed, 7 passed in
tests/test_slots_reference_failclosed.py. Restored: 21 passed.
Full suite after change: 646 passed (625 baseline - 1 removed pin + 21 new + ... see commit).

## Compatibility
Callers that supplied an arbitrary new mission_id to create slots now get 404
and must create the mission first or omit mission_id. Existing orphan slots are
not migrated. tests/test_p4_mission_integrity.py pin removed (inverted by the new
file); tests/test_h5_comms.py::_make_slot dropped its made-up mission_id (relied
on passthrough) so the id is minted.
