---
type: Crosswalk
title: Frozen Contract → Runtime Implementation Crosswalk
date: 2026-10-08
repo: _5_Signomy/1_agent-universe
runtime_head: 2102508 (+49a572c docs, +ad4abbb coord)
frozen_source: ~/Developer/_7_labs/signomy-control-surface/reports/phase-1/
status: reconciliation — definitive
---

# FROZEN CONTRACT → RUNTIME IMPLEMENTATION CROSSWALK

**Program state:** Working SIGNOMY → Phase 1 architecture **FROZEN**
(2026-10-07) → Phase 2 visual redesign underway (separate lane) → H5 safe
subset hardened (commit `2102508`, falsifier PASS) → remaining runtime
upgrades + verification.

**Purpose:** distinguish *defined-and-frozen* from *implemented* so
remaining work is measured correctly. Every contract in `reports/phase-1/`
carries `status: PHASE-1 FROZEN (2026-10-07)`. Stale `PRE-FREEZE` wording
survives only in supporting docs (`PHASE-1-HARDENING-CROSSWALK.md`,
`PHASE-1-RECONCILIATION.md`, `OWNER-DECISION-READINESS.md`, interior text in
1E/1G) — flagged for the frozen-package owner; this matrix supersedes them
for runtime planning.

## Legend

| Contract frozen | Runtime object/route exists | Gap classified | Test/verification status |
|---|---|---|---|
| ● frozen | ● exists · ◐ partial/analog only · ○ absent | GAP class from contract: NONE / RUNTIME GAP / IMPLEMENTATION LATER / OWNER DECISION | ● tested · ◐ adjacent coverage · ○ untested |

## 1A — Agreement Stack (FROZEN)

`PHASE-1A-AGREEMENT-STACK.md` — canonical ordering §2, common envelope §3,
semantics §4, 11-class registry §5, O-J-1 landed §6.

| Contract element | Runtime | Gap | Verified |
|---|---|---|---|
| Agreement ordering (opportunity→entry→Agreement→mission→slot→execution) | ○ — no Agreement objects anywhere (`grep agreement app/ → 0`) | RUNTIME GAP — ordering exists only as convention (post→stake/thread; inbox/apply→review) | ◐ — H5 tests cover the intake edges, not the ordering |
| Common envelope + state skeleton (`draft/proposed→active→terminal`) | ○ | RUNTIME GAP — greenfield | ○ |
| `PlatformParticipationAgreement` (§5.1) | ◐ — credential issuance + registration Seed (`provision.py`, `kassa.py` agent register) | relationship object absent; credentials exist | ● — signup/login/rotate/suspend/decommission tested (`test_routes_provision.py`, `test_routes_kassa.py`) |
| `WorkEntryAgreement` (§5.2 — the seam object, F1–F15) | ○ — closest: `inbox.jsonl` `app-*` records + `slots/fill` immediate path | RUNTIME GAP — no post→mission/slot linkage carrier; `inbox/{id}/review` flips status without binding (non-conformant per §5.2 F15) | ○ — review-without-resolution defect untested against contract shape |
| `MissionWorkAgreement` (§5.3) | ◐ — `mission-*` records + slot economics inline | agreement absent; bounty-minted mission IDs orphan (RUNTIME GAP — repair item §9.10) | ◐ — mission create/end paths tested |
| `FormationAgreement` (§5.4) | ◐ — `formation_id`/`role`/`revenue_split_pct` fields on slots | membership object absent | ◐ |
| `ContributionAgreement` (§5.5) | ○ — "Propose" writes a `contact_messages` row (label only) | RUNTIME GAP | ○ |
| Entity/Enterprise/ContributionBacked/Reciprocal classes (§5.6–§5.10) | ○ | absent — gated on 1D/1E objects | ○ |
| Evidence/idempotency/projection rules (§4.2–§4.4) | ◐ — audit + Seed writes exist; `try/except: pass` lets provenance fail silently (H3); PII projection hardened by H5 | loud-failure rule violated at commit sites | ◐ — H5 hardened the projection half |

## 1B — Entitlement Matrix (FROZEN)

`PHASE-1B-ENTITLEMENT-MATRIX.md` — P1–P8 principals, D1–D18 dimensions,
5-axis independence invariant.

| Contract element | Runtime | Gap | Verified |
|---|---|---|---|
| Principal classes P1–P8 | ◐ — agents (P2) + admin key (P4) + kassa poster (magic) exist | P5–P8 (Entity/Node-affiliated/Enterprise) have no objects | ● — P2/P4 auth heavily tested |
| D7 identity + dual credential doors | ◐ — provision `api_key` (work-execution) + KA§§A JWT (market-participation) coexist; semantics RESOLVED by contract | door unification = OWNER DECISION O-IA-3 (expressible, not picked) | ● — `test_jwt_config.py`, `test_auth_hardening.py`, H5 thread-auth probes |
| Key revocation deny-list (in-path before acceptance) | ○ — rotate/suspend/decommission exist; no dedicated deny-list | RUNTIME GAP (H1) | ○ |
| D9 custody / D10 treasury | ◐ — JSON ledger (`economy.py`) executes | custodial-claims model committed + disclosed by contract; ledger has no custody object | ◐ — `test_economy.py` covers ledger ops |
| D11 escrow authority | ○ — `$0 "platform_escrow"` tracking debit + docstring metaphor only | RUNTIME GAP — mechanism committed-to-build (owner G4); does not block entry | ○ |
| D12 payout / D13 fees / D14 limits | ◐ — payout paths execute; 2 of 3 payout call sites lack Seeds (H3+H4) | provenance + limits semantics incomplete | ◐ — `test_economic_loop.py` partial |
| D15/D16 licensing / capacity | ○ — vocabulary strings only (Black Card perk text, docstring flows 6–8) | absent | ○ |

## 1C — Delivery Evidence (FROZEN)

`PHASE-1C-DELIVERY-EVIDENCE.md` — three evidence classes,
`delivery_evidence_class` agreement field, acceptance record.

| Contract element | Runtime | Gap | Verified |
|---|---|---|---|
| `DeliveryEvidenceClass` enum + field on agreements | ○ | absent — depends on 1A objects | ○ |
| Proof/verification/access-grant Seeds + `parent_doi` chains | ○ — `parent_doi` field exists on SeedRecord, populated 0/2,324 | RUNTIME GAP — lineage carrier dead; every Seed is own-lineage | ○ |
| Acceptance record (de facto = task `close`) | ◐ — `POST /api/tasks/{id}/close` pays out | no review/revision/deemed-acceptance machinery | ◐ — task close tested |
| No-forced-disclosure / class privacy projections | ◐ — public post projection strips private fields (H5-strengthened) | acceptance privacy model unbuilt | ◐ |

## 1D — Entity Node (FROZEN)

`PHASE-1D-ENTITY-NODE.md` — genesis/recognition, Root Seed, lineage,
recursive Nodes, four projection states.

| Contract element | Runtime | Gap | Verified |
|---|---|---|---|
| Entity / EntityNode / relation edge / ecosystem projection objects | ○ — zero hits in `app/` | absent — greenfield; every object is new contract object | ○ |
| Root Seed semantics (explicit genesis artifact, not `parent_doi:None` implication) | ◐ — Seed schema present; no `is_root`, no `node_*` source_types | RUNTIME GAP | ○ |
| Candidate detection (derived, never authoritative) | ○ | absent | ○ |
| Recovery (K9: consume + re-emit with restored lineage) | ○ | absent; blocked by dead `parent_doi` | ○ |

## 1E — Enterprise Node (FROZEN)

`PHASE-1E-ENTERPRISE-NODE.md` — buy-in, delegated domain, subordinate
Nodes, three-class data split, parent override.

| Contract element | Runtime | Gap | Verified |
|---|---|---|---|
| Commercial agreement / buy-in | ○ | absent — no agreement objects | ○ |
| Delegated governance domain (four-sided bound) | ○ — no domain profile/scope/delegation objects | absent | ○ |
| Subordinate Nodes + domain edge | ○ | absent — gated on 1D | ○ |
| Enterprise economics/licensing | ○ — docstring vocabulary only | absent | ○ |

## 1F — WorkEntry unblock (FROZEN scaffold)

`PHASE-1F-WORKENTRY-UNBLOCK.md` — 21-row requirement classification:
RESOLVED BY CONTRACT **7** · OWNER-ANSWERED **2** · OWNER DECISION
REQUIRED **5** · RUNTIME GAP **5** · IMPLEMENTATION LATER **3**.

Runtime gaps named there — status at HEAD `2102508`:

| 1F runtime gap | Status today |
|---|---|
| #14 unauthenticated PII inbox GETs | **CLOSED by H5** (`2102508`) — admin-gated, tested |
| #13 review-without-resolution (`operator.py:310-334` status-flip never binds) | **OPEN** — contract position resolved (non-conformant); defect persists, held until WorkEntry wiring exists to bind TO |
| #12 bounty/orphan mission IDs | **OPEN** — repair mandated before binding relies on `slot.mission_id` |
| #20 escrow mechanism | **OPEN** — GAP by contract; blocks mission-side funding semantics, not entry |
| #21 silent provenance failure + dead `parent_doi` | **OPEN** — H3 lane |

## 1G — Authority Table (FROZEN)

`PHASE-1G-AUTHORITY-TABLE.md` — per-verb actor-class × credential × gate ×
custody × evidence cells; owner resolutions landed for O-J-1, O-J-4, O-IA-3,
O-IA-4, O-IA-5, O-6/O-7, G4–G7, G9, G10.

| Contract element | Runtime | Gap | Verified |
|---|---|---|---|
| Consequential-verb table semantics | ◐ — runtime enforces equivalents ad-hoc (`require_admin`, `require_agent_claim`, middleware prefix sets) | no per-verb table consult; cells not loadable | ● — current ad-hoc guards tested (incl. H5) |
| Credential revoke deny-list | ○ | RUNTIME GAP (H1) | ○ |
| O-J-4 per-transition gating rule | ○ — no in-path K8 gate evaluation layer | IMPLEMENTATION LATER | ○ |

## Summary — how much upgrade work remains

**Contracts frozen: 7/7.** **Runtime objects implementing contract
classes: ~0.** The runtime today is the 0.4.0 working system *plus* H5 comms
hardening — the Agreement/Entity/Enterprise/evidence object layer is
entirely unbuilt (greenfield, not rework).

| Bucket | Count (approx, by contract rows) |
|---|---|
| Contract elements fully absent from runtime | ~20 objects/classes (all of 1A §5 registry except credential-adjacent PPA, all of 1C/1D/1E) |
| Partial analogs needing hardening to contract | ~10 (credentials, slots/missions economics, ledger, inbox intake, task close) |
| Closed by H5 lane | 5 named defects + 9 falsifier findings |
| Named runtime gaps still open | H1 revoke deny-list · H2 orphan missions + WorkEntry carrier · H3 `parent_doi`/atomic Seeds/per-payout Seeds · H4 escrow mechanism · MCP `govern.vote` write divergence · thread-close route |
| Owner decisions still fileable | O-IA-3 (credential door), O-IA-5 residual cells, 1F rows #15/#16/#17 (resolver identity, stake-as-precursor, inbox unify) |

**Bottom line:** architecture-complete, implementation ~a working 0.4.0
base plus one hardening lane. The 70–80% intuition describes *contract*
completeness, not runtime completeness — the runtime upgrade work (Phase 5
program: H1–H4 implementations + verification) is the bulk of what remains.
