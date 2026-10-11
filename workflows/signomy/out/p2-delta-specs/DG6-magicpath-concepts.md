# DG6 - High-fidelity MagicPath concepts

**Standing:** PROVISIONAL (planning authority only; owner accepted originals as provisional baseline; does not satisfy P2_FINAL). Labels used: VERIFIED CURRENT / PROPOSED / UNRESOLVED / OWNER DECISION.

**Delta artifact:** High-fidelity MagicPath concepts (owner_visual_approval: pending, update_status: backlog)

## 1. Original master reference(s)

Root: `$CW/` = `/Users/dericmchenry/Developer/_7_labs/signomy-control-surface/` (read-only). Hashes recomputed at authoring time and matched against `p2-original-asset-inventory.json` (sha256 of inventory: `11c94aa77e2724a0a0820bf37692a45a7499b9c282e6a537ce4c57f7d84f94d3`).

- `source/SIGNOMY-CIVITAE-design-handoff/01-magicpath/civitae-world/offline-preview.html`  sha256 `48c26a82e32b6e5a0e9046f3a9caa545dc0542279688f98b6e98a9462c0937b7`
- `source/SIGNOMY-CIVITAE-design-handoff/01-magicpath/civitas-chamber/offline-preview.html`  sha256 `5132ccc498ac57ddf876f601820f2b77df902b43cba783ac422ffecab6eebe8e`
- `source/SIGNOMY-CIVITAE-design-handoff/01-magicpath/command-deploy/offline-preview.html`  sha256 `53e4e4b64c8eba6a5dfad8378464a2659c7a83c178507ebbc066f6268a31540e`
- `source/SIGNOMY-CIVITAE-design-handoff/01-magicpath/kassa-find-work/offline-preview.html`  sha256 `df86b489407069557c7eb27178f188bcf29fb1b66c0062f2e22fcd4b6bff9ae0`
- `source/SIGNOMY-CIVITAE-design-handoff/01-magicpath/mission-control/offline-preview.html`  sha256 `36c6d98dc8cce206e335f5b602ef7ac3f65416a786d4b51dd3b00af922cc7e15`
- `source/SIGNOMY-CIVITAE-design-handoff/01-magicpath/reality-constraints/offline-preview.html`  sha256 `d7562b066a809893239645f1991386136f4361e7088fed434bd569c0eb02d165`
- `source/SIGNOMY-CIVITAE-design-handoff/01-magicpath/shared-component-language/offline-preview.html`  sha256 `d28ac9d775b4bee91f5e6e1f134c4c99b41a422f6f336c8711caba038afa8c97`
- `source/SIGNOMY-CIVITAE-design-handoff/01-magicpath/unified-control-grammar/offline-preview.html`  sha256 `f770cf5bb3b7ec4a9db8010f5f65cf4b4afa178c8bcaf1a1468de552f67b5863`
- `source/SIGNOMY-CIVITAE-design-handoff/01-magicpath/exploratory-civic-world-map/offline-preview.html`  sha256 `b76127cdb208de28343d3f040385c17657e37b24c76bf332e73f3b79faeae526`
- `source/SIGNOMY-CIVITAE-design-handoff/01-magicpath/exploratory-mission-command-deck/offline-preview.html`  sha256 `4c42081516f325868f09f32faa8a13bc22a8fb517a6fe528d48d19bad53e0d8c`
- `source/SIGNOMY-CIVITAE-design-handoff/01-magicpath/exploratory-tactical-deploy-board/offline-preview.html`  sha256 `da83594f3d7fabc90c525dce8bc1c146452044316670bad5eabd07277617be9c`
- `source/SIGNOMY-CIVITAE-design-handoff/01-magicpath/exploratory-visual-directions/offline-preview.html`  sha256 `363b5da42c34847a6d3cb343f54b53834d2ff037a6634375b23d1948c9652d30`

### PRESERVE (verbatim from p2-visual-deltas.json)

> Adopt the eight canonical designs as provisional visual references

### REQUIRED UPDATE (verbatim from p2-visual-deltas.json)

> Find Work, COMMAND, World, Rank/Refinery, Switchboard, Enterprise/Entity, consequential preflight; inspect in offline prototypes

Master rule: original FigJam/MagicPath designs remain the visual master; nothing below replaces them with a simplified diagram. Additions are overlays/annotations within the original visual grammar.

## 2. Required updates with frozen-contract traceability

Contract citations resolve to files under $CW/reports/phase-1/ (frozen Phase 1, hashes in p2-delta-specs.json). Section headings are quoted from those files.

### DG6-U1 - KA§§A Find Work: entry via WorkEntryAgreement with mode-dependent resolution

**Status:** PROPOSED

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §5.2 WorkEntryAgreement
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §6 O-J-1 owner-resolved
- 1F `reports/phase-1/PHASE-1F-WORKENTRY-UNBLOCK.md` - §1.1 Agreement relationship ordering

**Visual change list:**
- [RENAME] CONFIRM ENTRY (original: closes the dialog only) keeps label; preflight panel after it shows resulting Agreement state: active (Open) / pending (Standard) / pending + governance (Constitutional).
- [ANNOTATE] Existing governance tag (Constitutional) maps to resolution mode; existing 'IDENTITY / REGISTRATION: ONE CANONICAL ENTRY' kept.
- [UNCHANGED] Discovery chips, match %, slot count, modal-in-one-workspace pattern.

### DG6-U2 - COMMAND (command-deploy): consequential preflight with Agreement-bound deploy authority; DEPLOY != COMMAND != CAMPAIGN

**Status:** PROPOSED

**Frozen-contract basis:**
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §5.C Work objects - mission / slot / formation / task / deploy (deploy row)
- 1E `reports/phase-1/PHASE-1E-ENTERPRISE-NODE.md` - §0 Canonical enterprise chain (COMMAND != DEPLOY != CAMPAIGN)

**Visual change list:**
- [ANNOTATE] GOVERNANCE GATE panel ('2 approvals required before authoritative deploy') reads 'deploy = consequential external execution: gated'; AUTH VALID shows authority source.
- [UNCHANGED] Tactical grid, formation presets, posture controls.

### DG6-U3 - World: Entity/Node/Ecosystem distinction and read-only projection

**Status:** PROPOSED

**Frozen-contract basis:**
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §0 Canonical invariants (non-compressible)
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §7.2 Privilege rules

**Visual change list:**
- [ANNOTATE] Original PROJECTION NOTE ('World does not own parallel truth') retained and extended with 'read-only derived projection'.
- [ADD] District Inspector adds 'Entity Node' / 'Ecosystem' rows qualified separately; Seeds overlay legend 'runtime provenance Seed'.

### DG6-U4 - Mission Control: Agreement in the control graph and context

**Status:** PROPOSED

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §7 Ordering recap + WorkEntry placement
- 1C `reports/phase-1/PHASE-1C-DELIVERY-EVIDENCE.md` - §9.1 The acceptance record

**Visual change list:**
- [ADD] Control graph chain (K-284 > M-017 > F-04 > GOV-121 > SET-017) gains an 'AGR' node between opportunity and mission; settlement node shows evidence class chip.
- [UNCHANGED] Queues, graph tabs, value state ESCROWED (escrow mechanism pending: label as design example).

### DG6-U5 - Civitas chamber: Town Hall vs formal governance labeling

**Status:** PROPOSED

**Frozen-contract basis:**
- 1B `reports/phase-1/PHASE-1B-ENTITLEMENT-MATRIX.md` - §1 Load-bearing invariants (I-9, I-10)
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §5.E Governance verbs (Town Hall != formal governance)

**Visual change list:**
- [ANNOTATE] Owner-only (OWN-##) decision handling preserved; Town Hall surface labeled community/deliberation.
- [UNCHANGED] Vote/motion mechanics, chamber layout.

### DG6-U6 - Rank / Refinery concept (read-only derived projection)

**Status:** OWNER DECISION

**Frozen-contract basis:**
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §7.2 Privilege rules
- 1B `reports/phase-1/PHASE-1B-ENTITLEMENT-MATRIX.md` - §1 Load-bearing invariants (I-5)
- 1C `reports/phase-1/PHASE-1C-DELIVERY-EVIDENCE.md` - §10.2 What this contract forbids economically

**Visual change list:**
- [NOTE] NO ORIGINAL MASTER: none of the 8 canonical concepts or 4 exploratory previews renders Rank/Refinery (only a 'Rank' rail glyph). Contract basis supports boundary-level constraints only; a new concept is a new design, not an update.

### DG6-U7 - Switchboard concept (read-only derived routing/suggestion)

**Status:** OWNER DECISION

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §5.6 EntityRelationAgreement (F13: Switchboard eligibility context, read-only)
- 1B `reports/phase-1/PHASE-1B-ENTITLEMENT-MATRIX.md` - §1 Load-bearing invariants (I-5)

**Visual change list:**
- [NOTE] NO ORIGINAL MASTER. Detailed Switchboard semantics are outside frozen Phase 1 (UNRESOLVED beyond the read-only boundary).

### DG6-U8 - Enterprise / Entity concept (Entity, Entity Node, Enterprise domain, Recognition Office)

**Status:** OWNER DECISION

**Frozen-contract basis:**
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §1 Definitions (contract vocabulary)
- 1E `reports/phase-1/PHASE-1E-ENTERPRISE-NODE.md` - §0 Canonical enterprise chain (non-compressible)
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §4.3 Recognition request and formalization

**Visual change list:**
- [NOTE] NO ORIGINAL MASTER for Entity Node or Enterprise Entity Node screens ('Entity' appears only as an identity/context label). Contract basis exists for objects and chains; screen layouts are new design requiring owner approval of method (offline authoring vs waiting for quota).

### DG6-U9 - Consequential preflight pattern across concepts (shared-component-language, unified-control-grammar)

**Status:** PROPOSED

**Frozen-contract basis:**
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §7 Consistency obligations (canonical preflight)
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §3 Reading rules and invariants (rule 10)

**Visual change list:**
- [ANNOTATE] Preflight sequence reads: principal resolution > governance check > economic disclosure > authoritative commit > event > provenance > refresh; failure shows no success evidence (1C §3 L8).
- [UNCHANGED] Preflight visual component.

### DG6-X1 - Inspect updates in offline prototypes only

**Status:** PROPOSED

**Frozen-contract basis:**
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §7 Consistency obligations (nothing here is a runtime grant yet)

**Visual change list:**
- [NOTE] Per constraint, no MagicPath/Figma calls. Updates are specified as annotations against the offline-preview.html copies; an offline mock may be authored locally later. Nothing here authorizes implementation.

## 3. Explicitly unchanged

- [UNCHANGED] The eight canonical designs adopted as PROVISIONAL visual references: civitae-world, civitas-chamber, command-deploy, kassa-find-work, mission-control, reality-constraints, shared-component-language, unified-control-grammar.
- [UNCHANGED] Four exploratory references retained as non-canonical: exploratory-civic-world-map, exploratory-mission-command-deck, exploratory-tactical-deploy-board, exploratory-visual-directions.
- [UNCHANGED] Editable source not recovered; compiled offline previews are the reference (inventory note).

## 4. Current-implementation crosscheck (worktree `frontend/shell.html`, 337 lines; plus original asset checks)

- [VERIFIED CURRENT] Prototype behaviour recorded in SIGNOMY-DESIGN-JOURNEY-MAP.md 'Verified prototype findings': Find Work CONFIRM ENTRY closes dialog only; Mission Control Open Deploy is a no-op; Command/Deploy palette has no handlers; Civitas CONFIRM VOTE closes only. These are prototype states, not defects of this spec.
- [VERIFIED CURRENT] Shell hosts existing 0.4.0 pages rather than rebuilding concepts (shell.html:98 'Existing 0.4.0 pages are hosted, not rebuilt').
- [VERIFIED CURRENT] Only a 'Rank' rail glyph appears in the preview text; no Refinery, Switchboard, Enterprise, Agreement or WorkEntry strings in any concept preview-visible-text.txt (grep over 01-magicpath); 'Entity' appears only as an identity/context label (e.g. 'ENTITY: ACME' in mission-control), not as Entity Node.

## 5. Acceptance checklist (independent visual QA reviewer)

- [ ] Eight canonical references unchanged on disk (hashes match inventory).
- [ ] Each PROPOSED annotation is attached to an existing screen element.
- [ ] Rank/Refinery, Switchboard, Enterprise/Entity are clearly marked 'no original master / OWNER DECISION', not presented as updates.
- [ ] No new generation or external design-tool call was used.
- [ ] Read-only projection screens expose no commit control.
- [ ] Entity, Entity Node, Ecosystem separately labeled.
- [ ] PROVISIONAL legend.

## 6. Owner question(s)

- [OWNER DECISION] Q11: For the three concepts with no original master (Rank/Refinery, Switchboard, Enterprise/Entity): author offline later, wait for quota reset, or defer past P2_FINAL?
- [OWNER DECISION] Q12: Is boundary-level depiction of Refinery/Switchboard sufficient for P2_FINAL while Phase 6B/6C is unfrozen?

## 7. Limits of this spec

- Text exports of the original diagrams list labels without edge endpoints; edge-level statements were checked against the PNG at reduced resolution where noted and must be re-confirmed at full resolution by the QA reviewer.
- No image generation and no MagicPath/Figma calls were made. Preparation only - does not satisfy P2_FINAL.
