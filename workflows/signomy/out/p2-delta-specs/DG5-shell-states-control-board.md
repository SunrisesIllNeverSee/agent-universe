# DG5 - Shell States and Control Board

**Standing:** PROVISIONAL (planning authority only; owner accepted originals as provisional baseline; does not satisfy P2_FINAL). Labels used: VERIFIED CURRENT / PROPOSED / UNRESOLVED / OWNER DECISION.

**Delta artifact:** Shell States and Control Board (owner_visual_approval: pending, update_status: backlog)

## 1. Original master reference(s)

Root: `$CW/` = `/Users/dericmchenry/Developer/_7_labs/signomy-control-surface/` (read-only). Hashes recomputed at authoring time and matched against `p2-original-asset-inventory.json` (sha256 of inventory: `11c94aa77e2724a0a0820bf37692a45a7499b9c282e6a537ce4c57f7d84f94d3`).

- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/shell-states.png`  sha256 `c5bf074a20deec7bd491c3ce048998f50c140972ebcad1daf96a09de1847214d`
- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/shell-states.pdf`  sha256 `41e68172c5700173e9f4cc7d65fdd85d53893a4711e0db9549ad7fd095d8fa07`
- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/shell-states-text.txt`  sha256 `f1f077773bdb629980b24f96803a26d8158bba8a7207841e7670581367bef29a`
- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/canonical-board-page-1-overview.png`  sha256 `47f8614f2bc744b3ee97fd8d7139c60d208b80030d21b68a1f7e57ef1466ba0d`

### PRESERVE (verbatim from p2-visual-deltas.json)

> Retain original nine-mode rail/sidebar/canvas/Inspector/HUD grammar

### REQUIRED UPDATE (verbatim from p2-visual-deltas.json)

> acting principal, context carry, Agreement/WorkEntry status, Entity/Node distinctions; Town Hall not governance

Master rule: original FigJam/MagicPath designs remain the visual master; nothing below replaces them with a simplified diagram. Additions are overlays/annotations within the original visual grammar.

## 2. Required updates with frozen-contract traceability

Contract citations resolve to files under $CW/reports/phase-1/ (frozen Phase 1, hashes in p2-delta-specs.json). Section headings are quoted from those files.

### DG5-U1 - Acting principal shown in HUD and Inspector, with principal class

**Status:** PROPOSED

**Frozen-contract basis:**
- 1B `reports/phase-1/PHASE-1B-ENTITLEMENT-MATRIX.md` - §2 Principal classes
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §3 Reading rules and invariants (rule 9)

**Visual change list:**
- [ADD] Original HUD fields 'acting identity / current agent' gain principal class (P1-P8) and 'acting FOR' when operator.
- [ADD] Inspector 'AUTHORITY' block lists authority source: Agreement id/class or 'platform operational' (admin is operational, not standing).
- [UNCHANGED] Nine-mode rail, per-mode Left/Tabs/Canvas/Inspector/HUD definitions.

### DG5-U2 - Context carry: Agreement/WorkEntry fields in sidebar/inspector

**Status:** PROPOSED

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §2 Canonical ordering (rule 4: not the runtime ribbon)
- 1F `reports/phase-1/PHASE-1F-WORKENTRY-UNBLOCK.md` - §1.2 Authoritative mapping shape

**Visual change list:**
- [ADD] Context ribbon in HUD or Inspector header: opportunity/post > agreement/entry > slot > mission > formation > motion > settlement > provenance/Seed; items without a live key render as 'not carried', never invented.
- [ANNOTATE] 'Agreement != WorkEntry UI carry': ribbon is a navigation lens; the Agreement lives in authoritative state.

### DG5-U3 - Agreement/WorkEntry status badge using 1A state names

**Status:** PROPOSED

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §4.1 State-model skeleton
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §5.2 WorkEntryAgreement (F6)

**Visual change list:**
- [ADD] State Badge values for entry: intent, pending, accepted, active, completed, rejected, withdrawn, expired, terminated; badge in Inspector STATE block for Missions/KA§§A/COMMAND modes.

### DG5-U4 - Entity vs Entity Node vs Ecosystem distinctions in World and relevant Inspectors

**Status:** PROPOSED

**Frozen-contract basis:**
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §0 Canonical invariants (non-compressible)
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §7.1 The four states

**Visual change list:**
- [ANNOTATE] WORLD mode Inspector 'selected district / entity / agents': 'entity' label qualified (Entity vs Entity Node); add projection-state tag (authoritative / derived / candidate / public verification).
- [UNCHANGED] WORLD tabs Map/District/Activity/Missions/Market/Governance/Seeds.

### DG5-U5 - Town Hall is not governance: relocate/annotate Town Hall in the mode taxonomy

**Status:** PROPOSED

**Frozen-contract basis:**
- 1B `reports/phase-1/PHASE-1B-ENTITLEMENT-MATRIX.md` - §1 Load-bearing invariants (I-9)
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §4.3 Recognition request and formalization (Town Hall = intake/deliberation/notice only)
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §5.E Governance verbs (Town Hall != formal governance)

**Visual change list:**
- [RENAME] Original COMMS mode already hosts Town Hall (Left: Inbox / forums / threads / mission channels / town hall); CIVITAS mode (Town Hall / Meetings / Motions...) lists Town Hall beside formal governance objects: annotate 'Town Hall = community surface, not formal governance' there, or move to COMMS only (OWNER DECISION Q8).
- [ADD] Mode-level caption on CIVITAS: 'formal governance: meetings, motions, votes, council, constitution'.

### DG5-U6 - Control Board: show latent/gated systems and derived layers hidden by rail compression

**Status:** PROPOSED

**Frozen-contract basis:**
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §7.1 The four states
- 1B `reports/phase-1/PHASE-1B-ENTITLEMENT-MATRIX.md` - §1 Load-bearing invariants (I-9)

**Visual change list:**
- [ADD] Control Board frame: authoritative core band vs derived projection band; placement of Refinery, Switchboard, Node Recognition Office, Agreements as latent/gated tiles with 'not implemented / gated' state badge.
- [UNCHANGED] Persistent rail / context sidebar / canvas host / Inspector / HUD arrangement.

### DG5-U7 - Rail mode set: original nine-mode vs shell's nine modes

**Status:** OWNER DECISION

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §2 Canonical ordering (rule 4)

**Visual change list:**
- [NOTE] Original rail (shell-states.png; UCG glyphs): HOME/PROFILE, MISSIONS, COMMAND, KA§§A, SIG/RANK, COMMS, CIVITAS, ECONOMY, WORLD. Shell (shell.html:121-131): ORIENT, FIND WORK, MISSION CONTROL, DEPLOY, COMMAND, CAMPAIGN, GOVERN, ECONOMY, REFERENCE. Both are nine, but the sets differ; frozen contracts only require 'navigation consolidation != semantic consolidation' (Visual Re-Baseline Register exit conditions) and the Mission Control != COMMAND != DEPLOY != CAMPAIGN separation. No frozen-contract clause selects between them.

### DG5-X1 - Where Rank/Refinery and Switchboard live in the rail

**Status:** UNRESOLVED

**Frozen-contract basis:** NONE - marked UNRESOLVED; no semantics invented.

**Visual change list:**
- [NOTE] Original rail has SIG/RANK; neither original nor shell has a Refinery or Switchboard mode. Frozen contracts do not assign rail placement; do not invent.

## 3. Explicitly unchanged

- [UNCHANGED] Original nine-mode rail/sidebar/canvas/Inspector/HUD grammar and per-mode definitions (HOME/PROFILE, MISSIONS, COMMAND, KA§§A, SIG/RANK, COMMS, CIVITAS, ECONOMY, WORLD).
- [UNCHANGED] Original canonical board (page 1 overview) structure.

## 4. Current-implementation crosscheck (worktree `frontend/shell.html`, 337 lines; plus original asset checks)

- [VERIFIED CURRENT] Shell layout: rail 64px, sidebar 230px, canvas, inspector 260px, HUD 34px (shell.html:9-13, 17-20).
- [VERIFIED CURRENT] Shell modes (shell.html:121-131): orient[/portal,/world,/kingdoms], find[/kassa,/missions,/bountyboard,/openroles], mc[/agentdash,/dashboard,/mission,/slots], deploy[/deploy], command[/command], campaign[/campaign], govern[/governance,/senate,/forums], econ[/economics,/treasury,/connect,/earnings-matrix], ref[/vault,/academia,/guides,/moses].
- [VERIFIED CURRENT] POTENTIAL CONFLICT: shell.html:128 places /forums (Town Hall Forums per COMMS-TOWN-HALL-MAP.md section 4) inside GOVERN, while shell.html:119-120 comment asserts 'Town Hall != Governance'. Contract basis: 1B I-9, 1D §0. Flagged for owner, not changed.
- [VERIFIED CURRENT] Inspector rows (shell.html:256-267) incl. agreement_id/workentry 'PHASE-4 - not implemented'; note text shell.html:103-105 says read-only projection, shell grants no permissions (consistent with 1D §7.2 rule 1).
- [VERIFIED CURRENT] Principal block (shell.html:94, 281-311) shows agent name/role/status from existing credentials only, else 'guest'; no principal class (P1-P8) or acting-for shown.
- [VERIFIED CURRENT] HUD (shell.html:107-113, 315-330) shows governance mode/posture and systems-observed count only; no context ribbon.

## 5. Acceptance checklist (independent visual QA reviewer)

- [ ] Rail has the original nine modes (or the owner-approved set per Q9) with distinct semantics preserved.
- [ ] HUD and Inspector show principal class and acting-for.
- [ ] Agreement/WorkEntry badge uses 1A §4.1/§5.2 names.
- [ ] Entity, Entity Node, Ecosystem distinguished in WORLD.
- [ ] Town Hall is not shown as formal governance anywhere.
- [ ] Control Board shows latent/gated systems and derived vs authoritative bands.
- [ ] Inspector grammar groups STATE / AUTHORITY / GOVERNANCE / ECONOMY / PROVENANCE (preserved from the original).
- [ ] No shell element implies it grants permissions.
- [ ] PROVISIONAL legend.

## 6. Owner question(s)

- [OWNER DECISION] Q8: Move Town Hall out of CIVITAS (COMMS only) or keep and annotate? And should /forums leave GOVERN in the shell (shell.html:128)?
- [OWNER DECISION] Q9 (DG5-U7): Which nine-mode rail is the visual master for P2_FINAL: the original (HOME/MISSIONS/.../WORLD) or the shell's (ORIENT/.../REFERENCE)?
- [OWNER DECISION] Q10: Accept that Rank/Refinery/Switchboard placement is UNRESOLVED (DG5-X1)?

## 7. Limits of this spec

- Text exports of the original diagrams list labels without edge endpoints; edge-level statements were checked against the PNG at reduced resolution where noted and must be re-confirmed at full resolution by the QA reviewer.
- No image generation and no MagicPath/Figma calls were made. Preparation only - does not satisfy P2_FINAL.
