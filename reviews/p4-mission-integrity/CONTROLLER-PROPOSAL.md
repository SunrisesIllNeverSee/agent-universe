# PROPOSAL (not applied) — controller nodes for P4_BASELINE / P4_REPAIR_MISSION_INTEGRITY

`workflows/signomy/roadmap.json` was NOT edited. The task graph
(`reports/PHASE-4-AGREEMENT-WORKENTRY-TASK-GRAPH.md` ~L470-L590) already specifies both nodes. This note
only proposes how their `acceptance`/`files` could reference the evidence from this branch. No attestation is claimed.

Suggested amendments to the existing stubs (JSON merge fragments):

```json
{
  "id": "P4_BASELINE",
  "evidence_refs": [
    "1_agent-universe@claude/p4-mission-integrity:ba60574",
    "reviews/p4-mission-integrity/EVIDENCE.md"
  ],
  "acceptance_note": "slots/create auth + orphan characterization pinned by tests/test_p4_mission_integrity.py (strict xfail at ba60574)"
}
```

```json
{
  "id": "P4_REPAIR_MISSION_INTEGRITY",
  "needs": ["P4_BASELINE"],
  "evidence_refs": [
    "1_agent-universe@claude/p4-mission-integrity:df8f540",
    "reviews/p4-mission-integrity/EVIDENCE.md"
  ],
  "acceptance_note": "GET /api/missions/{id} resolves for every id minted by slots/create (omitted mission_id); falsifier: 4 tests RED with fix reverted, 14 GREEN with fix; suite 544 passed; backfill deferred; supplied-id behavior unchanged"
}
```

Caveats for the controller owner:
- `out/p4-baseline.json` (nine 1F requirements) is a separate deliverable not produced here; this branch covers only
  the slots/create slice of P4_BASELINE.
- The repair's `risk: medium` and Q13 (production orphan audit) are untouched; status should stay "pending owner
  verification" until the owner reviews/merges. Nothing here is a self-attestation.
