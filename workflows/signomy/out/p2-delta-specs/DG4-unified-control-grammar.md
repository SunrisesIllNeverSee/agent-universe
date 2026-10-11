# DG4 - Unified Control Grammar

**Standing:** PROVISIONAL (planning authority only; owner accepted originals as provisional baseline; does not satisfy P2_FINAL). Labels used: VERIFIED CURRENT / PROPOSED / UNRESOLVED / OWNER DECISION.

**Delta artifact:** Unified Control Grammar (owner_visual_approval: pending, update_status: backlog)

## 1. Original master reference(s)

Root: `$CW/` = `/Users/dericmchenry/Developer/_7_labs/signomy-control-surface/` (read-only). Hashes recomputed at authoring time and matched against `p2-original-asset-inventory.json` (sha256 of inventory: `11c94aa77e2724a0a0820bf37692a45a7499b9c282e6a537ce4c57f7d84f94d3`).

- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/unified-control-grammar.png`  sha256 `a0d398978dfbd972acbfbc85184c786059176b5e3d79f4a220836ebdef0fe528`
- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/unified-control-grammar.pdf`  sha256 `e73074d585587dfd94eabe271c9ffca8de6a3b65e9b1f2089743c4c5a71010a5`
- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/unified-control-grammar-text.txt`  sha256 `53f0a23a4876ab6798b059b6c227d85c9d14d6e51c12aa0ca5eeea6b3b13bb62`
- `source/SIGNOMY-CIVITAE-design-handoff/01-magicpath/unified-control-grammar/offline-preview.html`  sha256 `f770cf5bb3b7ec4a9db8010f5f65cf4b4afa178c8bcaf1a1468de552f67b5863`
- `source/SIGNOMY-CIVITAE-design-handoff/01-magicpath/shared-component-language/offline-preview.html`  sha256 `d28ac9d775b4bee91f5e6e1f134c4c99b41a422f6f336c8711caba038afa8c97`

### PRESERVE (verbatim from p2-visual-deltas.json)

> Reuse original grammar and update vocabulary

### REQUIRED UPDATE (verbatim from p2-visual-deltas.json)

> principal, Agreement, object context, economic/evidence effects, consequential preflight, read-only projections

Master rule: original FigJam/MagicPath designs remain the visual master; nothing below replaces them with a simplified diagram. Additions are overlays/annotations within the original visual grammar.

## 2. Required updates with frozen-contract traceability

Contract citations resolve to files under $CW/reports/phase-1/ (frozen Phase 1, hashes in p2-delta-specs.json). Section headings are quoted from those files.

### DG4-U1 - 'Resolve active principal' step names the principal class

**Status:** PROPOSED

**Frozen-contract basis:**
- 1B `reports/phase-1/PHASE-1B-ENTITLEMENT-MATRIX.md` - §2 Principal classes
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §3 Reading rules and invariants (rule 9: operator acts FOR a named principal)

**Visual change list:**
- [RENAME] Flow step 'Resolve active principal' keeps its label; sub-caption adds 'P1 human, P2 agent, P3 operator-FOR-named-principal, P4 admin (operational), P5 Entity (anchor, not actor), P6-P8 affiliated/enterprise/delegated'.
- [ADD] Principal badge in Object Identity Block (principal class + credential door; a credential is not a principal class).

### DG4-U2 - Agreement as object context in Context Breadcrumb and Object Identity Block

**Status:** PROPOSED

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §3 Common envelope - every Agreement instance
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §1.3 Agreement != neighbors

**Visual change list:**
- [RENAME] Breadcrumb 'Entity > Campaign > Mission > Object' retained; Agreement inserted as optional segment 'Agreement' before Mission when the object is Agreement-governed. 'Entity' segment is annotated as Entity (identity), not Entity Node.
- [ADD] Object Identity Block gains Agreement id/class/state fields (state from 1A §4.1 skeleton).

### DG4-U3 - Preflight economic and evidence effects (disclosure, treasury != escrow != stake)

**Status:** PROPOSED

**Frozen-contract basis:**
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §7 Consistency obligations (canonical preflight reads this table)
- 1B `reports/phase-1/PHASE-1B-ENTITLEMENT-MATRIX.md` - §1 Load-bearing invariants (I-7)
- 1C `reports/phase-1/PHASE-1C-DELIVERY-EVIDENCE.md` - §10.1 Dependency direction (locked)

**Visual change list:**
- [RENAME] Flow step 'Show consequence: state + economy + evidence' keeps label; Value Strip distinguishes treasury movement, escrow (mechanism pending), and stake (intent, no funds).
- [ADD] Evidence Trail component gains evidence-class chip and 'private / counterparty / public' visibility marker (1C §9.2).

### DG4-U4 - Consequential-action flow: governance gate only where O-J-4 categories fire

**Status:** PROPOSED

**Frozen-contract basis:**
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §3 Reading rules and invariants (rule 10)
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §7 Consistency obligations (preflight sequence)

**Visual change list:**
- [ANNOTATE] 'Governance / permission preflight' step: in-path preconditions always; discretionary gate only for the eight categories.
- [UNCHANGED] Flow sequence: invoke > resolve principal > preflight > show consequence > confirm > commit > emit live event > write Seed/audit > refresh projections (original nine steps).

### DG4-U5 - Read-only projection adapters: World, Rank/Refinery, Switchboard canvas adapters marked read-only

**Status:** PROPOSED

**Frozen-contract basis:**
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §7.2 Privilege rules
- 1B `reports/phase-1/PHASE-1B-ENTITLEMENT-MATRIX.md` - §1 Load-bearing invariants (I-9)

**Visual change list:**
- [ADD] Existing 'World Canvas Adapter' tagged read-only projection (no commit step). Add stub adapter cards 'Refinery' and 'Switchboard' (read-only; no Action Stack with destructive items).
- [UNCHANGED] Deploy, Market, Mission, Civic adapters and Persistent Application Grammar items 1-8.

### DG4-U6 - Action Stack inherits the authority-table row of the verb invoked

**Status:** PROPOSED

**Frozen-contract basis:**
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §7 Consistency obligations (O-IA-8 cockpit scopes)
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §3 Reading rules and invariants (rule 2: consent classes distinct)

**Visual change list:**
- [ANNOTATE] Action Stack caption: 'each action inherits its 1G verb row; consent class (UNILATERAL/BILATERAL/CONSTITUTIONAL/RULE-FIRED) shown in preflight'.

### DG4-X1 - Command Palette (item 7) and Live Event Stream (item 8): vocabulary for agreement/evidence events

**Status:** UNRESOLVED

**Frozen-contract basis:** NONE - marked UNRESOLVED; no semantics invented.

**Visual change list:**
- [NOTE] No frozen-contract text defines event names for the palette/stream; only the evidence/Seed requirements per transition exist (1A §4.2, F9 rows). Event vocabulary left unspecified.

## 3. Explicitly unchanged

- [UNCHANGED] Original grammar: 8-item Persistent Application Grammar, Shared Control Components (Governance Preflight, Action Stack, Evidence Trail, Value Strip, State Badge, Object Identity Block, Selection Model, Context Breadcrumb, Queues, Filter/Layer Controls), five canvas adapters, nine-step consequential-action flow.
- [UNCHANGED] MagicPath unified-control-grammar and shared-component-language component language (offline previews sha f770cf5b..., d28ac9d7...).

## 4. Current-implementation crosscheck (worktree `frontend/shell.html`, 337 lines; plus original asset checks)

- [VERIFIED CURRENT] shell.html implements grammar items 1 (rail, :83-90), 2 (sidebar, :91-95), 4 (canvas host, :96-99), 5 (Inspector, :100-106), 6 (HUD, :107-113). Items 3 (Context Tabs), 7 (Command Palette), 8 (Live Event Stream) are not present in shell.html.
- [VERIFIED CURRENT] Inspector (shell.html:253-278) shows route/surface/status/section/post/thread/mission/slot/agreement_id/workentry/seed rows; no STATE/AUTHORITY/GOVERNANCE/ECONOMY/PROVENANCE grouping from the preserved Inspector grammar.

## 5. Acceptance checklist (independent visual QA reviewer)

- [ ] Nine-step flow unchanged and in original order.
- [ ] Principal step names the 8 principal classes without conflating credential with principal.
- [ ] Breadcrumb shows Agreement as an optional segment and distinguishes Entity from Entity Node.
- [ ] Value Strip separates treasury / escrow / stake.
- [ ] World/Refinery/Switchboard adapters show no commit/write control.
- [ ] All original shared components and adapters retained.
- [ ] Vocabulary changes are additive; no original term removed.
- [ ] PROVISIONAL legend.

## 6. Owner question(s)

- [OWNER DECISION] Q7: Is DG4-X1 (event vocabulary for palette/stream) deferred to a later phase?

## 7. Limits of this spec

- Text exports of the original diagrams list labels without edge endpoints; edge-level statements were checked against the PNG at reduced resolution where noted and must be re-confirmed at full resolution by the QA reviewer.
- No image generation and no MagicPath/Figma calls were made. Preparation only - does not satisfy P2_FINAL.
