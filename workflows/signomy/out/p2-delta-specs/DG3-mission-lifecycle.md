# DG3 - Mission Lifecycle

**Standing:** PROVISIONAL (planning authority only; owner accepted originals as provisional baseline; does not satisfy P2_FINAL). Labels used: VERIFIED CURRENT / PROPOSED / UNRESOLVED / OWNER DECISION.

**Delta artifact:** Mission Lifecycle (owner_visual_approval: pending, update_status: backlog)

## 1. Original master reference(s)

Root: `$CW/` = `/Users/dericmchenry/Developer/_7_labs/signomy-control-surface/` (read-only). Hashes recomputed at authoring time and matched against `p2-original-asset-inventory.json` (sha256 of inventory: `11c94aa77e2724a0a0820bf37692a45a7499b9c282e6a537ce4c57f7d84f94d3`).

- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/mission-lifecycle.png`  sha256 `c612a5445a8a6e89480bfdfe94a8f961f41bd4a8819335226b797a3027fad12c`
- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/mission-lifecycle.pdf`  sha256 `001ca7e21097b41ca429f3ebad228e5e1cf164975598790c7ef18f2af5d8d545`
- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/mission-lifecycle-text.txt`  sha256 `5ad7336d02e4401502a9516222217b4494a31c9fc98e4d6f10fc99959e4709db`

### PRESERVE (verbatim from p2-visual-deltas.json)

> Maintain established state and feedback complexity

### REQUIRED UPDATE (verbatim from p2-visual-deltas.json)

> hybrid WorkEntry, DeliveryEvidenceClass, authoritative receipt/Seed, formation and governed transition gates

Master rule: original FigJam/MagicPath designs remain the visual master; nothing below replaces them with a simplified diagram. Additions are overlays/annotations within the original visual grammar.

## 2. Required updates with frozen-contract traceability

Contract citations resolve to files under $CW/reports/phase-1/ (frozen Phase 1, hashes in p2-delta-specs.json). Section headings are quoted from those files.

### DG3-U1 - Hybrid WorkEntry states before MissionDraft/FormationOpen

**Status:** PROPOSED

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §5.2 WorkEntryAgreement (F6 state model, F7 transitions)
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §6.1 How each resolution maps
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §4.1 State-model skeleton

**Visual change list:**
- [ADD] Sub-lifecycle entry: intent -> pending -> accepted -> active (binds mission/slot) -> completed; exits rejected, withdrawn, expired, terminated.
- [RENAME] Original state 'Matching' ('agents fill slots') is annotated 'entry via WorkEntryAgreement; Open = pending crossed atomically'; state label retained.
- [ADD] Edge 'Matching -> [WorkEntryAgreement active] -> FormationReady' replaces implicit direct fill.
- [UNCHANGED] Original states Opportunity, MissionDraft, CampaignLinked, FormationOpen, FormationReady, VoteOpen, DeployReady, Blocked, GovernanceCheck, MeetingRequired, InProgress, ProgressUpdate, Review, Complete, Settlement, ReputationUpdate, Seeded, Audited, WorldProjection, Comms, MotionOpen.

### DG3-U2 - Formation and MissionWork Agreement gates on existing transitions

**Status:** PROPOSED

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §5.3 MissionWorkAgreement
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §5.4 FormationAgreement
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §5.C Work objects - mission / slot / formation / task / deploy

**Visual change list:**
- [ANNOTATE] Transition 'create mission -> activate mission': tagged 'MissionWorkAgreement draft -> active'.
- [ANNOTATE] Transitions into FormationReady and 'formation configured': tagged 'FormationAgreement membership'.
- [ANNOTATE] 'deploy / state-changing action' -> GovernanceCheck: tagged 'consequential external execution: gated (O-J-4)'; routine task start/assign: no re-gate (1G §5.C).

### DG3-U3 - Governed-transition gates drawn per-transition, not per-phase

**Status:** PROPOSED

**Frozen-contract basis:**
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §3 Reading rules and invariants (rule 10)
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §5.2 WorkEntryAgreement (F8)

**Visual change list:**
- [ANNOTATE] GovernanceCheck decision outputs (permitted / approval required / rejected) retained; add legend: gate categories fire only for authority, rights, custody/economics, recognition, constitutional state, disputed membership, recovery, consequential external execution.
- [UNCHANGED] Principal / Rules / Decision sub-flow shape.

### DG3-U4 - DeliveryEvidenceClass on Review / deliverable-ready

**Status:** PROPOSED

**Frozen-contract basis:**
- 1C `reports/phase-1/PHASE-1C-DELIVERY-EVIDENCE.md` - §5 The three classes - comparison
- 1C `reports/phase-1/PHASE-1C-DELIVERY-EVIDENCE.md` - §9.1 The acceptance record
- 1C `reports/phase-1/PHASE-1C-DELIVERY-EVIDENCE.md` - §3 Locked rules (L1, L4)

**Visual change list:**
- [ADD] On 'deliverable ready' -> Review: class chip (Solution | Solution+Proof | Solution+Proof+Work Access) and 'class fixed by agreement before/at engagement'.
- [RENAME] Review outcomes: original 'accepted / closed' and 'changes requested' map to accepted / revision_requested; add rejected (grounds required) and deemed_accepted (rule-fired).
- [ANNOTATE] 'Verification != acceptance; proof != access' (1C §4).

### DG3-U5 - Authoritative receipt and Seed after Settlement; failure writes no Seed

**Status:** PROPOSED

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §4.2 Evidence rules
- 1C `reports/phase-1/PHASE-1C-DELIVERY-EVIDENCE.md` - §3 Locked rules (L8, L9)
- 1C `reports/phase-1/PHASE-1C-DELIVERY-EVIDENCE.md` - §10.1 Dependency direction (locked)

**Visual change list:**
- [ADD] Between Settlement and Seeded: 'Committed receipt' node (carries agreement_id/delivery id) per 1A §5.2 F9 / 1C §9.1.
- [ANNOTATE] 'create provenance seed' edge: runtime provenance Seed; not Root Seed (1D §0).
- [ADD] 'Failed commit -> no success Seed' side-note on every commit edge.
- [ANNOTATE] Settlement: 'acceptance outcome is the settlement trigger; class creates no premium'.

### DG3-U6 - Entry/terminal exception states: rejected, expired, withdrawn, disputed

**Status:** PROPOSED

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §5.2 WorkEntryAgreement (F11, F12, F15)
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §5.D Delivery & acceptance (dispute row)

**Visual change list:**
- [ADD] Terminal nodes beside Blocked: Rejected, Withdrawn, Expired (entry); Disputed (freezes disputed leg only) hung off Review/Settlement.

### DG3-X1 - Escrow/funding precondition drawn on mission activation

**Status:** OWNER DECISION

**Frozen-contract basis:**
- 1E `reports/phase-1/PHASE-1E-ENTERPRISE-NODE.md` - §10.1 Honest status: committed-to-build
- 1B `reports/phase-1/PHASE-1B-ENTITLEMENT-MATRIX.md` - §1 Load-bearing invariants (I-6, I-7)

**Visual change list:**
- [NOTE] Escrow is committed-to-build, mechanism absent at runtime; diagram may show 'funding precondition (mechanism pending)' only. Owner to confirm whether to depict it.

## 3. Explicitly unchanged

- [UNCHANGED] Original state-machine layout, feedback loops (Blocked -> revise, Review -> changes requested, MeetingRequired loop) and state vocabulary.
- [UNCHANGED] Left/Right affordance notes ('Left: My agents / affiliations...', tabs).

## 4. Current-implementation crosscheck (worktree `frontend/shell.html`, 337 lines; plus original asset checks)

- [VERIFIED CURRENT] Original lifecycle (mission-lifecycle.png sha c612a544...) has no entry-agreement states and no evidence-class element; 'Matching - agents fill slots' goes straight to FormationReady.
- [VERIFIED CURRENT] shell.html:253-278 Inspector shows 'agreement_id' / 'workentry' as 'PHASE-4 - not implemented' (class 'future' purple italics, shell.html:275) and 'seed evidence' from ctx.seed_doi, which no code sets (only post_id/thread_id/mission_id/slot_id are set, shell.html:236-243). No lifecycle state is rendered by the shell.

## 5. Acceptance checklist (independent visual QA reviewer)

- [ ] WorkEntry sub-lifecycle present with all five main states and four exits.
- [ ] Open mode shows pending as crossed atomically, not elided.
- [ ] Class chip present; three outcomes plus rejected/deemed enumerated.
- [ ] Committed receipt precedes Seeded; no success Seed on failure.
- [ ] Gates are annotated per transition; no per-phase gate.
- [ ] All original states retained and unrenamed.
- [ ] Disputed leg freezes only the disputed leg.
- [ ] PROVISIONAL legend.

## 6. Owner question(s)

- [OWNER DECISION] Q5: Depict escrow/funding precondition (DG3-X1) or omit until mechanism exists?
- [OWNER DECISION] Q6: Keep terminal exception nodes on the main canvas or on a collapsible overlay?

## 7. Limits of this spec

- Text exports of the original diagrams list labels without edge endpoints; edge-level statements were checked against the PNG at reduced resolution where noted and must be re-confirmed at full resolution by the QA reviewer.
- No image generation and no MagicPath/Figma calls were made. Preparation only - does not satisfy P2_FINAL.
