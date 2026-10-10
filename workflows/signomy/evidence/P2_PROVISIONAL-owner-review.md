# P2_PROVISIONAL — Owner Review Evidence Packet

Date: 2026-10-09 · Prepared by: DREP2 · Runtime HEAD: `f2c01a6`

## What the owner is being asked to attest

Accept the **original** FigJam + MagicPath high-fidelity designs as the
**provisional** Phase 2 visual baseline — a planning baseline, not final
architecture-aligned approval.

## Original source inventory (verified, hashed)

Source: `~/Developer/_7_labs/signomy-control-surface/source/SIGNOMY-CIVITAE-design-handoff/`
Full hash inventory: `workflows/signomy/out/p2-original-asset-inventory.json`
(engine-produced, receipt `P2_INVENTORY`).

- Native FigJam export — sha256 `40d96db60…`
- Five original diagrams (PDF+PNG each, hashed): System Interaction Map,
  Operational Spine, Mission Lifecycle, Unified Control Grammar,
  Shell States / Control Board
- 12 offline MagicPath previews (8 canonical concepts + 4 exploratory
  references), hashed
- Handoff docs: `IMPLEMENTATION-HANDOFF-BRIEF.md`, `MANIFEST-SHA256.txt`,
  `VERIFICATION.json`, contact sheet, `START-HERE.html`

## Six outstanding visual delta groups (backlog, not done)

From `workflows/signomy/inputs/visual_delta_register.json` — all
`update_status: backlog`, `owner_visual_approval: pending`:

1. System Interaction Map — Agreement classes, WorkEntry authority,
   Node Recognition Office, Entity/Root/Secondary Seed, Enterprise,
   read-only Refinery/Switchboard
2. Operational Spine — canonical ordering
   (opportunity→intent→Agreement→mission→slot→execution), resolution
   modes, delivery/acceptance/settlement, provenance
3. Mission Lifecycle — hybrid WorkEntry, DeliveryEvidenceClass,
   authoritative receipt/Seed, formation + governed gates
4. Unified Control Grammar — principal, Agreement, object context,
   consequential preflight, read-only projections
5. Shell States / Control Board — acting principal, context carry,
   Agreement/WorkEntry status, Town Hall ≠ governance
6. MagicPath concepts — Find Work, COMMAND, World, Rank/Refinery,
   Switchboard, Enterprise/Entity, consequential preflight

## Design assumptions and known omissions

- Original visuals predate the frozen Agreement/Entity/Enterprise object
  layer — those systems are not depicted; deltas above are required.
- No formal commitment-weight metric exists (U1); any visual "weight" is
  experiential styling only.
- Refinery/Switchboard are derived read-only projections — no write path
  to authoritative state.
- MagicPath/Figma external quotas are exhausted/rate-limited at last
  check; deltas may be authored offline against the preserved originals.

## Explicit provisional limitations

- This is a **planning baseline** — it does not satisfy Phase 2 final
  architectural alignment.
- Accepting it authorizes **bounded preparation/planning** work only —
  it does NOT authorize production implementation (P3_AUTHORIZE is a
  separate gate), deployment, or release (R_LIVE).
- Phase 2 final exit (`P2_FINAL`) remains open: independent
  architecture-aligned visual QA + owner signoff still required before
  Phase 4 integration.

## Requested decision

Owner attests `P2_PROVISIONAL` via:

```
python3 -m roadmap_engine --project workflows/signomy attest \
    P2_PROVISIONAL --evidence workflows/signomy/evidence/P2_PROVISIONAL-owner-review.md
```

(or a separately authored owner approval document, which this file may
reference).
