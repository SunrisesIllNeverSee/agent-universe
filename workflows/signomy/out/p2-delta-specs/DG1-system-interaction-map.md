# DG1 - System Interaction Map

**Standing:** PROVISIONAL (planning authority only; owner accepted originals as provisional baseline; does not satisfy P2_FINAL). Labels used: VERIFIED CURRENT / PROPOSED / UNRESOLVED / OWNER DECISION.

**Delta artifact:** System Interaction Map (owner_visual_approval: pending, update_status: backlog)

## 1. Original master reference(s)

Root: `$CW/` = `/Users/dericmchenry/Developer/_7_labs/signomy-control-surface/` (read-only). Hashes recomputed at authoring time and matched against `p2-original-asset-inventory.json` (sha256 of inventory: `11c94aa77e2724a0a0820bf37692a45a7499b9c282e6a537ce4c57f7d84f94d3`).

- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/canonical-figjam-board.jam`  sha256 `40d96db605cfdc21796241076ea0ec6615973d70549c4888173199a3838efb64`
- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/system-interaction-map.png`  sha256 `91d70965ba29dcc7a554f5cfa6331fb3297f34e7a9a76aa9dd37790451bb454d`
- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/system-interaction-map.pdf`  sha256 `486fe0581b5f5ee2806599a39305911f44e9f2f77fc409cb9f9d7b4ccf7d7a62`
- `source/SIGNOMY-CIVITAE-design-handoff/02-diagrams/system-interaction-map-text.txt`  sha256 `fcae333ec2b55d95f78b5f86be964f5f04f6d0dd2e93b72410c8659546acfd14`

### PRESERVE (verbatim from p2-visual-deltas.json)

> Original FigJam layout is visual master, new simplified overlay is explanatory only

### REQUIRED UPDATE (verbatim from p2-visual-deltas.json)

> Agreement classes, WorkEntry authority, Node Recognition Office, Entity/Root/Secondary Seed, Enterprise, read-only Refinery & Switchboard

Master rule: original FigJam/MagicPath designs remain the visual master; nothing below replaces them with a simplified diagram. Additions are overlays/annotations within the original visual grammar.

## 2. Required updates with frozen-contract traceability

Contract citations resolve to files under $CW/reports/phase-1/ (frozen Phase 1, hashes in p2-delta-specs.json). Section headings are quoted from those files.

### DG1-U1 - Add an Agreement Stack layer between KA§§A / MARKET and MISSION / WORK

**Status:** PROPOSED

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §1.1 Definition
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §2 Canonical ordering
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §5.11 Class registry summary
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §7 Ordering recap + WorkEntry placement

**Visual change list:**
- [ADD] New cluster 'AGREEMENT STACK' (same zone-box grammar as the existing 9 zones) placed on the Market Posts -> Missions path.
- [ADD] Ten class nodes in the registry's order: PlatformParticipation, WorkEntry, MissionWork, Formation, Contribution, EntityRelation, EntityNode, EnterpriseDelegatedDomain, ContributionBackedAccess, ReciprocalEconomics (1A §5.11 lists exactly these ten; registry is 'at minimum and extensible' per the reconciler's note).
- [ANNOTATE] Cluster caption: 'typed governed relationship object; active is the only state that authorizes governed execution' (1A §1.1, §4.1).
- [ADD] Edges: Agreement -> emits -> Seeds/receipts; Agreement -> gates -> Mission/Slots/Formation (1A §1.1 bullets 3-4).

### DG1-U2 - Re-route the opportunity-to-work edges through WorkEntryAgreement (no direct post->slot edge)

**Status:** PROPOSED

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §2 Canonical ordering (reading rule 2: the Agreement relationship may not be skipped)
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §5.2 WorkEntryAgreement (F13: not enabled: direct post_id->slot_id write)
- 1F `reports/phase-1/PHASE-1F-WORKENTRY-UNBLOCK.md` - §1.1 Agreement relationship ordering

**Visual change list:**
- [RENAME] The original KA§§A Market Posts -> Slots/Roles ('listed in' / 'filled by' / 'matches into') edges are re-drawn as Post -> [entry intent] -> WorkEntryAgreement -> Mission/Slot binding. The original edge labels are retained where they describe discovery/matching.
- [ANNOTATE] Edge label 'commitment order, not record-creation order' (1A §2 rule 1); slots may pre-exist.
- [UNCHANGED] Cascade Matcher / Availability / Inbox nodes remain; matcher output is ranking, not eligibility or Agreement (1B I-5).

### DG1-U3 - WorkEntry authority box with hybrid resolution annotation

**Status:** PROPOSED

**Frozen-contract basis:**
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §6 O-J-1 owner-resolved (hybrid by governance mode)
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §6.2 Anti-collapse guarantees
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §5.B Agreement lifecycle & entry

**Visual change list:**
- [ADD] On the WorkEntryAgreement node, three-chip annotation: Open = auto-accept/immediate after preconditions; Standard = pending + resolver; Constitutional = pending + required governance gate. One model, one node.
- [ADD] Edge from Governance (CIVIC / GOVERNANCE) to WorkEntryAgreement labeled 'gate: Constitutional mode only' (not all transitions: O-J-4 per-transition rule, 1A §5.2 F8).

### DG1-U4 - Entity / Entity Node / Root Seed / Secondary Seeds / Relations+Flows / Ecosystem chain

**Status:** PROPOSED

**Frozen-contract basis:**
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §0 Canonical invariants (non-compressible)
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §1 Definitions (contract vocabulary)
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §5.1 Root Seed role (K6)
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §5.2 Secondary Seed attribution

**Visual change list:**
- [ADD] New cluster 'ENTITY GRAPH' in/adjacent to WORLD / PROVENANCE: ENTITY -> ENTITY NODE -> ROOT SEED -> SECONDARY SEEDS -> RELATIONS + FLOWS -> ECOSYSTEM -> GROWTH as six distinct nodes (chain must not be compressed).
- [RENAME] Existing 'Districts / Entities' node: label 'Entities' must not be read as Entity Node; add annotation 'District/Entity = World projection label; not Entity Node' (1D §0 do-not-collapse: Entity != Entity Node != Ecosystem).
- [ANNOTATE] Existing 'Seeds' (overlay on World/Provenance, and 'create provenance seed' edges) are labeled 'runtime provenance Seed' and are NOT classed Root vs Secondary until Node-qualified (1D §0: generic unlinked Seed != Root Seed).
- [ADD] Node 'Root Seed' visually distinct from 'Secondary Seeds' (e.g. distinct border) with caption 'explicitly committed genesis/recognition artifact' (1D §3.2/§5.4 via §0).

### DG1-U5 - Node Recognition Office distinct from Town Hall

**Status:** PROPOSED

**Frozen-contract basis:**
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §4.3 Recognition request and formalization
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §0 Canonical invariants (Town Hall != recognition authority)
- 1B `reports/phase-1/PHASE-1B-ENTITLEMENT-MATRIX.md` - §1 Load-bearing invariants (I-9)

**Visual change list:**
- [ADD] Node 'Node Recognition Office' in the ENTITY GRAPH cluster with edges: declared genesis/emergent petition -> Recognition Office -> Root Seed + Entity Node record.
- [ANNOTATE] Existing COMMUNICATION / Town Hall node: edge 'petition intake / deliberation / notice' to Recognition Office; caption 'workflow only, not authority source'. No edge from Town Hall to Governance that implies it is formal governance (see DG1-U8).
- [ADD] Candidate projection node (derived, read-only, 'no authority') feeding the petition, labeled weaker than recognized projection (1D §7.2 rule 2).

### DG1-U6 - Enterprise branch: Commercial Agreement -> Enterprise Entity Node -> Delegated Governance Domain -> Subordinate Nodes

**Status:** PROPOSED

**Frozen-contract basis:**
- 1E `reports/phase-1/PHASE-1E-ENTERPRISE-NODE.md` - §0 Canonical enterprise chain (non-compressible)
- 1E `reports/phase-1/PHASE-1E-ENTERPRISE-NODE.md` - §5 Delegated governance domain
- 1E `reports/phase-1/PHASE-1E-ENTERPRISE-NODE.md` - §6 Parent constitutional override
- 1E `reports/phase-1/PHASE-1E-ENTERPRISE-NODE.md` - §8.1 The three classes

**Visual change list:**
- [ADD] Cluster 'ENTERPRISE' with the nine-step chain nodes in order (ENTERPRISE ENTITY, COMMERCIAL AGREEMENT, ENTERPRISE ENTITY NODE, ROOT SEED, DELEGATED GOVERNANCE DOMAIN, SUBORDINATE NODES, SECONDARY SEEDS+RELATIONS+FLOWS, CONTROLLED ECOSYSTEM PROJECTIONS, ENTERPRISE ECONOMICS/LICENSING/OPERATIONS).
- [ADD] Edge 'parent constitutional override / audit' from CIVIC / GOVERNANCE (Constitution/Vault) to the domain; edge direction shows domain subordinate to parent.
- [ANNOTATE] Caption: 'buy-in != network-wide constitutional authority; commercial access != constitutional control' (1E §0).
- [ADD] Three-class data split legend (private authoritative / private enterprise projection / public verification projection).

### DG1-U7 - Read-only Refinery and Switchboard as derived projections

**Status:** PROPOSED

**Frozen-contract basis:**
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §7.2 Privilege rules (derived projections may NOT write back)
- 1B `reports/phase-1/PHASE-1B-ENTITLEMENT-MATRIX.md` - §1 Load-bearing invariants (I-5, I-9)
- 1A `reports/phase-1/PHASE-1A-AGREEMENT-STACK.md` - §5.6 EntityRelationAgreement (F13: Switchboard eligibility context, read-only consumption)
- 1C `reports/phase-1/PHASE-1C-DELIVERY-EVIDENCE.md` - §10.2 What this contract forbids economically

**Visual change list:**
- [ADD] Nodes 'Refinery' and 'Switchboard' in a 'DERIVED READ-ONLY PROJECTIONS' band alongside existing SIG / PERFORMANCE and World/Kingdom Projection, with arrows only INTO them from authoritative state (no return arrow).
- [ANNOTATE] Switchboard caption: 'constrained routing/suggestion; consumes eligibility context read-only; ranking != eligibility'. Refinery caption: 'interpretive projection; may read verification history and acceptance outcomes; class selection is not a merit signal'.
- [UNCHANGED] Leaderboard, SigArena, Trust/Reputation/Tier nodes keep original placement; they are measurement layers (I-5).

### DG1-U8 - Formal governance boundary vs Town Hall

**Status:** PROPOSED

**Frozen-contract basis:**
- 1B `reports/phase-1/PHASE-1B-ENTITLEMENT-MATRIX.md` - §1 Load-bearing invariants (I-9, I-10)
- 1D `reports/phase-1/PHASE-1D-ENTITY-NODE.md` - §0 Canonical invariants
- 1G `reports/phase-1/PHASE-1G-AUTHORITY-TABLE.md` - §5.E Governance verbs (Town Hall != formal governance)

**Visual change list:**
- [ADD] Boundary line around Governance / Senate / Meetings / Motions / Votes labeled 'formal governance (standing from contracts, never purchased)'. Town Hall and Forums sit in COMMUNICATION outside it.
- [ANNOTATE] Admin key edge to governance objects labeled 'operational, not standing' (I-10).

### DG1-X1 - Exact content of Refinery and Switchboard beyond the read-only/derived boundary (inputs, outputs, activation)

**Status:** UNRESOLVED

**Frozen-contract basis:** NONE - marked UNRESOLVED; no semantics invented.

**Visual change list:**
- [NOTE] Frozen Phase 1 contracts fix only the privilege boundary; Phase 6B/6C semantics live in IMPLEMENTATION-SLICE-PLAN.md and REFINERY-SWITCHBOARD-CURRENT-STATE.md (not frozen Phase 1). The map must show the nodes only at boundary level; no input/output edges invented.

## 3. Explicitly unchanged

- [UNCHANGED] Original FigJam zone structure and all nine existing zone clusters (IDENTITY/USER SPACE, COMMAND/OPERATIONS, MISSION/WORK, SIG/PERFORMANCE, KA§§A/MARKET, ECONOMY, COMMUNICATION, CIVIC/GOVERNANCE, WORLD/PROVENANCE) and PLATFORM/CONNECTION entry cluster.
- [UNCHANGED] Dense multi-edge routing, dark node fills per zone and edge-label typography.
- [UNCHANGED] All original nodes and edges not named in the update list; additions are overlays within the same visual grammar.

## 4. Current-implementation crosscheck (worktree `frontend/shell.html`, 337 lines; plus original asset checks)

- [VERIFIED CURRENT] Original map has no Agreement, Entity Node, Enterprise, Refinery, Switchboard or Node Recognition node: text export (system-interaction-map-text.txt, sha fcae333e...) contains none of those labels. Original has 'Districts / Entities' and 'Seeds' overlay nodes only.
- [VERIFIED CURRENT] Shell does not render a system map; the Inspector shows 'agreement_id' and 'workentry' as 'PHASE-4 - not implemented' (frontend/shell.html:265-266) and the note at shell.html:103-105 states these are placeholders, not records. DG1 has no shell dependency.

## 5. Acceptance checklist (independent visual QA reviewer)

- [ ] Every one of the 10 classes of 1A §5.11 appears, named as in the registry.
- [ ] No edge connects a Post/Opportunity node directly to a Slot/Role node without WorkEntryAgreement.
- [ ] Entity, Entity Node, Ecosystem are three separate nodes; Root Seed and Secondary Seeds are two separate nodes.
- [ ] Node Recognition Office is a node distinct from Town Hall; no edge makes Town Hall an authority source.
- [ ] Refinery and Switchboard have inbound-only edges from authoritative state; none writes back.
- [ ] Enterprise chain shows all nine steps in order and shows parent override.
- [ ] Original 9 zones, nodes and edges unchanged (diff overlay vs original PNG sha 91d70965...).
- [ ] No label claims 'commitment weight' (1A §1.4, 1B I-4).
- [ ] Every added element is labeled PROVISIONAL in the legend.

## 6. Owner question(s)

- [OWNER DECISION] Q1: Is the Agreement Stack drawn as its own zone, or folded into MISSION / WORK (design choice; semantics unchanged)?
- [OWNER DECISION] Q2: Accept Refinery/Switchboard shown at boundary level only until Phase 6B/6C semantics are frozen (see UNRESOLVED DG1-X1)?

## 7. Limits of this spec

- Text exports of the original diagrams list labels without edge endpoints; edge-level statements were checked against the PNG at reduced resolution where noted and must be re-confirmed at full resolution by the QA reviewer.
- No image generation and no MagicPath/Figma calls were made. Preparation only - does not satisfy P2_FINAL.
