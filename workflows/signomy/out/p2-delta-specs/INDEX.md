# P2 Delta Specs - Index

**Preparation only - does not satisfy P2_FINAL.**

Standing: PROVISIONAL. P2_FINAL still requires independent architecture-aligned visual QA and OWNER signoff. These specs make that review possible; they do not pass or attest anything. Original FigJam/MagicPath designs remain the visual master. Frozen Phase 1 contracts (1A-1G) are authority and are unmodified.

| Group | Artifact | Spec | Update items | Contract citations | PROPOSED | OWNER DECISION | UNRESOLVED |
|---|---|---|---|---|---|---|---|
| DG1 | System Interaction Map | [DG1-system-interaction-map.md](DG1-system-interaction-map.md) | 9 | 28 | 8 | 0 | 1 |
| DG2 | Operational Spine | [DG2-operational-spine.md](DG2-operational-spine.md) | 8 | 18 | 7 | 1 | 0 |
| DG3 | Mission Lifecycle | [DG3-mission-lifecycle.md](DG3-mission-lifecycle.md) | 7 | 18 | 6 | 1 | 0 |
| DG4 | Unified Control Grammar | [DG4-unified-control-grammar.md](DG4-unified-control-grammar.md) | 7 | 13 | 6 | 0 | 1 |
| DG5 | Shell States and Control Board | [DG5-shell-states-control-board.md](DG5-shell-states-control-board.md) | 8 | 14 | 6 | 1 | 1 |
| DG6 | High-fidelity MagicPath concepts | [DG6-magicpath-concepts.md](DG6-magicpath-concepts.md) | 10 | 22 | 7 | 3 | 0 |
| **Total** | | | **49** | **113** | **40** | **6** | **3** |

Unresolved count: **3** (items with no frozen-contract basis: no semantics invented). Owner-decision items: **6**.

## Unresolved items

- DG1-X1 - Exact content of Refinery and Switchboard beyond the read-only/derived boundary (inputs, outputs, activation)
- DG4-X1 - Command Palette (item 7) and Live Event Stream (item 8): vocabulary for agreement/evidence events
- DG5-X1 - Where Rank/Refinery and Switchboard live in the rail

## Owner decision items (items)

- DG2-X1 - Exact ribbon key list ('motion', 'settlement' ids) and slot pre-existence vs create-at-entry
- DG3-X1 - Escrow/funding precondition drawn on mission activation
- DG5-U7 - Rail mode set: original nine-mode vs shell's nine modes
- DG6-U6 - Rank / Refinery concept (read-only derived projection)
- DG6-U7 - Switchboard concept (read-only derived routing/suggestion)
- DG6-U8 - Enterprise / Entity concept (Entity, Entity Node, Enterprise domain, Recognition Office)

## Consolidated owner questions

- Q1: Is the Agreement Stack drawn as its own zone, or folded into MISSION / WORK (design choice; semantics unchanged)?
- Q2: Accept Refinery/Switchboard shown at boundary level only until Phase 6B/6C semantics are frozen (see UNRESOLVED DG1-X1)?
- Q3: Should the Agreement node sit inline on the spine or as a stacked layer over Mission (visual only)?
- Q4 (OWNER DECISION DG2-X1): confirm resolver/timeout/notification details stay out of the diagram until 1F sub-decisions are made.
- Q5: Depict escrow/funding precondition (DG3-X1) or omit until mechanism exists?
- Q6: Keep terminal exception nodes on the main canvas or on a collapsible overlay?
- Q7: Is DG4-X1 (event vocabulary for palette/stream) deferred to a later phase?
- Q8: Move Town Hall out of CIVITAS (COMMS only) or keep and annotate? And should /forums leave GOVERN in the shell (shell.html:128)?
- Q9 (DG5-U7): Which nine-mode rail is the visual master for P2_FINAL: the original (HOME/MISSIONS/.../WORLD) or the shell's (ORIENT/.../REFERENCE)?
- Q10: Accept that Rank/Refinery/Switchboard placement is UNRESOLVED (DG5-X1)?
- Q11: For the three concepts with no original master (Rank/Refinery, Switchboard, Enterprise/Entity): author offline later, wait for quota reset, or defer past P2_FINAL?
- Q12: Is boundary-level depiction of Refinery/Switchboard sufficient for P2_FINAL while Phase 6B/6C is unfrozen?

## Cross-cutting findings

1. No original master exists for Rank/Refinery, Switchboard, or Enterprise/Entity concepts (DG6): new design, not an update.
2. Shell rail (9 modes) differs from the original 9-mode rail (DG5-U7).
3. shell.html:128 puts /forums (Town Hall) under GOVERN, against 'Town Hall != Governance' (DG5-U5).
4. Refinery/Switchboard are specified in frozen contracts only at the read-only boundary; detailed semantics are UNRESOLVED (DG1-X1, DG5-X1).

## Files

- `p2-delta-specs.json` machine summary; `DG1`-`DG6` specs; this index.
