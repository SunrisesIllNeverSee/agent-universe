# DG2 - Operational Spine

**Standing:** PROVISIONAL (planning authority only; owner accepted originals as provisional baseline; does not satisfy P2_FINAL). Labels used: VERIFIED CURRENT / PROPOSED / UNRESOLVED / OWNER DECISION.

**Delta artifact:** Operational Spine (owner_visual_approval: pending, update_status: backlog)

## 1. Original master reference(s)

Root: `$CW/` = `/Users/dericmchenry/Developer/_7_labs/signomy-control-surface/` (read-only). Hashes recomputed at authoring time and matched against `p2-original-asset-inventory.json` (sha256 of inventory: `11c94aa77e2724a0a0820bf37692a45a7499b9c282e6a537ce4c57f7d84f94d3`).

- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/operational-spine.png`  sha256 `1927c900f226463a05e9be82ae2be17d07a0c86906b0418ffd26e4aea9c18678`
- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/operational-spine.pdf`  sha256 `011879292916420fe63aee9a4c9fe61c9fff61565374cf5eda75676ca0610782`
- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/operational-spine-text.txt`  sha256 `eaa609dbb5107fbb56c099031f04d491713fd9aa8d93fcec0dafb9b0790fffef`

### PRESERVE (verbatim from p2-visual-deltas.json)

> Preserve original densely connected composition

### REQUIRED UPDATE (verbatim from p2-visual-deltas.json)

> opportunity > intent > Agreement > mission/work > slot/formation > execution; Open/Standard/Constitutional resolution, delivery/acceptance/settlement, provenance

Master rule: original FigJam/MagicPath designs remain the visual master; nothing below replaces them with a simplified diagram. Additions are overlays/annotations within the original visual grammar.

## 2. Required updates with frozen-contract traceability

Contract citations resolve to files under $CW/reports/phase-1/ (frozen Phase 1, hashes in p2-delta-specs.json). Section headings are quoted from those files.

### DG2-U1 - Canonical ordering spine: opportunity > entry intent > Agreement > mission/work > slot/formation > governed execution

**Status:** PROPOSED

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §2 Canonical ordering (established by this contract)
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §7 Ordering recap + WorkEntry placement

**Visual change list:**
- [ADD] Insert an 'Agreement relationship' node (WorkEntryAgreement) and an 'Entry intent' node between 'KA§§A Opportunity' and 'Mission'/'Slots / Roles'.
- [RENAME] Original 'KA§§A Opportunity' keeps its label; it is the opportunity/post stage. Original 'Slots / Roles' + 'Formation' become the 'slot/formation' stage; 'Task / Milestone', 'Mission Dashboard', 'Mission Payout' fall under 'governed execution'.
- [RENAME] Original edges 'can expose bounty' (Opportunity->Slots), 'creates' (Opportunity->Mission), 'filled by' (Slots->Agent Identity) are re-pathed via the Agreement node; text in the original labels is retained.
- [ANNOTATE] Rule chips: 'commitment order, not record-creation order'; 'compression at commit time only' (1A §2 rules 1, 3).

### DG2-U2 - Open / Standard / Constitutional resolution branch at entry

**Status:** PROPOSED

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §6 O-J-1 owner-resolved
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §6.1 How each resolution maps
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §5.2 WorkEntryAgreement (F6, F7, F8)

**Visual change list:**
- [ADD] Three-way branch on the Agreement node: Open -> auto-accept/immediate (one atomic gated commit); Standard -> pending + resolver; Constitutional -> pending + governance gate. Branches rejoin at 'active -> binds mission/slot'.
- [ADD] Terminal exits from pending: rejected, withdrawn, expired (each emits evidence).

### DG2-U3 - Governance gate only on consequential transitions (per-transition rule)

**Status:** PROPOSED

**Frozen-contract basis:**
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §3 Reading rules and invariants (rule 10: O-J-4 governance-gate rule)
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §5.2 WorkEntryAgreement (F8)

**Visual change list:**
- [RENAME] Original 'authorizes / rejects transition' and 'captures governance at launch' edges stay; annotate 'gate only: authority, rights, custody/economics, recognition, constitutional state, disputed membership, recovery, consequential external execution'.
- [ANNOTATE] Routine execution under an active Agreement: 'in-path preconditions only, no re-gate' (K8).

### DG2-U4 - Delivery, acceptance, settlement with evidence class

**Status:** PROPOSED

**Frozen-contract basis:**
- 1C `reports/phase-1/PHASE-1C-DELIVERY-EVIDENCE.md` - §5 The three classes - comparison
- 1C `reports/phase-1/PHASE-1C-DELIVERY-EVIDENCE.md` - §9.1 The acceptance record
- 1C `reports/phase-1/PHASE-1C-DELIVERY-EVIDENCE.md` - §10.1 Dependency direction (locked)

**Visual change list:**
- [ADD] Between 'Task / Milestone' and 'Mission Payout': nodes 'Delivery' (DeliveryEvidenceClass chip: Solution | Solution+Proof | Solution+Proof+Work Access) -> 'Acceptance record' (accepted | revision_requested | rejected | deemed_accepted) -> settlement trigger.
- [RENAME] Original 'completion triggers' edge into Mission Payout is re-labelled 'acceptance outcome triggers settlement per agreement + entitlement terms'.
- [ANNOTATE] 'Class is a contract term, not a merit tier; no platform-wide pricing gradient' (1C §3 L1, L4; §10.1).

### DG2-U5 - Provenance: Seeds at consequential transitions, failure writes no success Seed

**Status:** PROPOSED

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §4.2 Evidence rules
- 1C `reports/phase-1/PHASE-1C-DELIVERY-EVIDENCE.md` - §3 Locked rules (L6, L8, L9)
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §0 Canonical invariants (generic Seed != Root Seed)

**Visual change list:**
- [RENAME] Original 'Seed' node label becomes 'Seed (runtime provenance)'; edges 'creates / touches', 'provenance supports', 'provenance overlay' unchanged.
- [ANNOTATE] Seed legend: evidence, not commitment (L6); append-only (L9); failed commit emits no success Seed (L8).

### DG2-U6 - Projections stay read-only: World, Tier/Leaderboard, Refinery, Switchboard

**Status:** PROPOSED

**Frozen-contract basis:**
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §7.2 Privilege rules
- 1B `reports/phase-1/PHASE-1B-ENTITLEMENT-MATRIX.md` - §1 Load-bearing invariants (I-5, I-9)

**Visual change list:**
- [ANNOTATE] Existing 'projected into', 'affects eligibility / tier' edges toward Tier/Reputation/Leaderboard and World/Kingdom Projection: add 'read-only derived' tag; 'affects eligibility' must read 'informs eligibility policy; never is the grant' (1G §3 rule 6).
- [ADD] Refinery and Switchboard as read-only terminals only (see DG1-X1: no further edges).

### DG2-U7 - Runtime context ribbon shown as a separate lens, not the spine

**Status:** PROPOSED

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §2 Canonical ordering (reading rule 4: not the runtime ribbon)
- 1F `reports/phase-1/PHASE-1F-WORKENTRY-UNBLOCK.md` - §1.1 Agreement relationship ordering

**Visual change list:**
- [ADD] Thin ribbon strip beneath the spine: opportunity/post > agreement/entry > slot > mission > formation > motion > settlement > provenance/Seed, captioned 'navigation lens; coexists with, does not replace, the Agreement order'.

### DG2-X1 - Exact ribbon key list ('motion', 'settlement' ids) and slot pre-existence vs create-at-entry

**Status:** OWNER DECISION

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §6.3 What stays open

**Visual change list:**
- [NOTE] Resolver identity, timeouts, notification mechanics, and slot pre-existence are open per 1A §6.3; spine must not depict specific values.

## 3. Explicitly unchanged

- [UNCHANGED] Original densely connected composition, all existing nodes (Console/COMMAND, Campaign, Mission, KA§§A Opportunity, Matcher, Slots/Roles, Formation, Deploy Tactical Grid, Agent Identity, Active Principal/Auth, Governance State, Meeting, Motion, Vote/Decision, Audit Chain, Realtime Feed/WS, Tier/Leaderboard, World/Kingdom Projection, Seed, Treasury, EXP/Credits, Mission Payout, Task/Milestone, Mission Dashboard, Thread/Inbox, Individual/Operator, Constitution/Rules).
- [UNCHANGED] Colour-coding by domain (identity=blue, governance=green, market/ops=dark/orange) and edge routing.

## 4. Current-implementation crosscheck (worktree `frontend/shell.html`, 337 lines; plus original asset checks)

- [VERIFIED CURRENT] Original spine (operational-spine.png sha 1927c900...) draws Opportunity -> Slots ('can expose bounty'), Opportunity -> Mission ('creates') and Slots -> Agent Identity ('filled by') with no Agreement node; confirmed visually and by text export.
- [VERIFIED CURRENT] shell.html:225-249 derives only post_id, thread_id, mission_id, slot_id from the hosted URL; no agreement/entry key exists (shell.html:265-266 placeholders). Ribbon in DG2-U7 is therefore design-only today.
- [VERIFIED CURRENT] Mode map comment shell.html:118-120 encodes 'Mission Control != COMMAND != DEPLOY != CAMPAIGN; KA§§A != Switchboard; Town Hall != Governance' (aligned with Visual Re-Baseline Register exit conditions).

## 5. Acceptance checklist (independent visual QA reviewer)

- [ ] Spine reads, left to right, in the exact 1A §2 six-stage order.
- [ ] An Agreement node exists on every opportunity->work path; no direct opportunity->slot edge remains.
- [ ] Open/Standard/Constitutional branch present with correct behaviours and rejoin.
- [ ] Evidence class chip on Delivery; acceptance outcomes enumerated.
- [ ] No score or weight claim appears as authority (I-4/I-5).
- [ ] Ribbon is visibly a separate lens.
- [ ] All original nodes/edges retained (overlay diff against sha 1927c900...).
- [ ] PROVISIONAL legend present.

## 6. Owner question(s)

- [OWNER DECISION] Q3: Should the Agreement node sit inline on the spine or as a stacked layer over Mission (visual only)?
- [OWNER DECISION] Q4 (OWNER DECISION DG2-X1): confirm resolver/timeout/notification details stay out of the diagram until 1F sub-decisions are made.

## 7. Limits of this spec

- Text exports of the original diagrams list labels without edge endpoints; edge-level statements were checked against the PNG at reduced resolution where noted and must be re-confirmed at full resolution by the QA reviewer.
- No image generation and no MagicPath/Figma calls were made. Preparation only - does not satisfy P2_FINAL.
