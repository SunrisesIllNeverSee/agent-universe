# SIGNOMY — Integrated Executable Roadmap

**Status at packaging (2026-10-09):** Phase 0 PASS; Phase 1 FROZEN; T0 mostly complete (formal adversarial gate remains open); Phase 2 in progress with original visual assets retained as provisional baseline; Phase 3 **preparation only**; H5 safe subset locally reviewed PASS; H1/H3 MCP vote defect locally reported fixed; full H0–H7, Phase 4–8, production release **not** passed.

This is an **actual `roadmap.json` graph of 18 tasks** for Portable Roadmap Engine v0.1; it is not a static markdown substitute. Local tasks inspect authoritative source repos, create hash-verified outputs, and enter the controller's evidence/receipt mechanism. Explicit owner gates protect Phase 3 implementation and all later stages. The workflow never modifies the runtime/design repositories, contacts Figma/MagicPath, launches Devin, migrates state, or deploys.

## Install/use on the Mac with the two existing repositories

Unzip the archive somewhere stable. From its `roadmap-engine-portable-v0` root:

```bash
python3 -m roadmap_engine --project workflows/signomy validate
python3 -m roadmap_engine --project workflows/signomy refresh
python3 -m roadmap_engine --project workflows/signomy run
python3 -m roadmap_engine --project workflows/signomy status
python3 -m roadmap_engine --project workflows/signomy blockers
python3 -m roadmap_engine --project workflows/signomy verify
```

**Review the commands before `run`.** The six automatic tasks run only `python3 steps/signomy.py produce/check` in the workflow directory, reading source artifacts and writing to `out/`. They may fail closed if a referenced source is moved or changed. The rest are manual approval/verification gates.

Sources auto-discovered on this user's Mac by defaults in `settings.json`:
- `~/Developer/_5_Signomy/1_agent-universe` — working runtime, containing `635a794` H1/H3 vote correction and `2102508` H5.
- `~/Developer/_7_labs/signomy-control-surface` — frozen architecture and original 44-MB design research package.

Override without editing accepted task contracts:

```bash
SIGNOMY_RUNTIME_REPO=/other/checkout \
SIGNOMY_DESIGN_ARCHIVE=/other/archive \
python3 -m roadmap_engine --project workflows/signomy refresh
```

## What the controller now controls

| Stage | What it produces or holds | Automatic? |
|---|---|---|
| T0 | Read-only Phase 1 contract SHA256 snapshot; runtime pointer + corrected crosswalk ancestor checks | Yes, evidence inspection only |
| H5 | Receipt of committed H5 report/review; safe subset closure vs deliberately held comms work | Yes, evidence inspection only |
| H1/H3 | Receipt of `govern.vote` correction and open REST closed-meeting parity issue | Yes, evidence inspection only |
| T0 verification | Red/green mutation demonstration, independent skill adoption and T0 owner gate | **Manual, held** |
| P2 | Native FigJam + five original diagrams + 12 offline MagicPath preview inventory | Yes, no external quotas |
| P2 | Copy/hash the six-item **visual delta register** without losing original visual quality | Yes |
| P2 | Owner adoption of original visuals as *provisional* baseline | **Manual, held** |
| P3 | Generate bounded host-first shell prep spec (9-mode rail/sidebar/canvas/Inspector/HUD and context rules) | Yes, planning only |
| P2 full exit | Architecture-aligned redraw + independent visual review | **Manual, held** |
| P3 implementation | Explicit owner approval allows **bounded host-first shell** on the provisional-design exception, after T0 review; does not require final P2 approval for a planning/prototype slice | **Manual, held** |
| P4 | Agreement/WorkEntry authoritative implementation and receipts; **requires final P2 review** | **Manual, held** |
| P5–P8, release | Full hardening, derived systems, IA, acceptance, controlled release | **Manual, held** |

The temporary **Phase 3 fast path** is intentional: owner-approved, host-first shell integration can proceed against existing high-fidelity assets **without pretending the Phase 2 redesign is complete**. Phase 4 still requires final architecture-aligned visuals and full Phase 3 verification. No `run` task performs Phase 3 implementation itself.

## Status changes vs outside observations

The source-refresh feature is new to the engine:

```bash
python3 -m roadmap_engine --project workflows/signomy refresh
```

It executes `observer.argv` (configured in `roadmap.json`), reads commits/contracts/assets, writes `tracking/OBSERVED_STATUS.json` and `.md`, and regenerates `ROADMAP_STATUS.md`. It **does not alter `.roadmap/state.json` or mark tasks PASS**. The controller progresses only when an automatic task/check/receipt is accepted or a manual gate is attested. Thus new Git commits will be visible after `refresh`, but don't automatically declare a phase complete. You can invoke `refresh` from an explicit scheduled job or repo hook after reviewing the command; none is silently installed. There is no background daemon/live watcher in v0.1.

To accept an owner gate *after its prerequisites pass*, create a durable evidence/authorization file yourself, then:

```bash
python3 -m roadmap_engine --project workflows/signomy attest P2_PROVISIONAL --evidence /absolute/path/to/owner-review.md
```

`attest` records a local operator assertion with an artifact hash, not cryptographic proof of identity. **Do not use a generic placeholder evidence file as permission**. The owner is the only party who can authorize production implementation/release. `P3_AUTHORIZE` is distinct from `R_LIVE`.

## Map and authority

- Canonical roadmap: `design_archive/reports/IMPLEMENTATION-SLICE-PLAN.md` (Phase 0–8, unmodified).
- Frozen contracts: `reports/phase-1/PHASE-1A` through `1G`; closeout on 2026-10-07.
- Runtime implementation facts: `runtime_repo/docs/contracts/FROZEN-CONTRACT-IMPLEMENTATION-CROSSWALK.md` as corrected by `3d099dc`.
- Past observations and their confidence: `inputs/established_status_2026-10-09.json` (not automatic gates).
- Provisional design deltas: `inputs/visual_delta_register.json`. Full Stage-2 visual upgrade still needs authoring and owner QA.
- Phase-3 bounded shell spec: `inputs/shell_brief.json`. Existing pages should be hosted, not rewritten.
- Detailed local outputs: `out/` and `.roadmap/` after `run`, with cryptographic digests (not signed).

**Do not collapse:** Agreement≠Commitment; Entity≠Entity Node≠Ecosystem; Root Seed≠Secondary Seed; Town Hall≠formal governance; KA§§A discovery≠Switchboard; Mission Control≠COMMAND≠DEPLOY≠CAMPAIGN; Seeds≠Refinery≠Switchboard; authority core≠read-only projection. No formal commitment-weight measurement.

## Gate semantics and remaining questions

The tracker does **not** re-open O-IA-3 (two doors/unified principal) or the frozen ten Agreement classes. Genuine Phase-4 owner sub-decisions—WorkEntry resolver identity/timeout/notification, stake precursor vs coexistence, and intake unification—remain held rather than guessed. The reported H5 475/475 and MCP vote 478/478 test results are evidence references, not test runs in this ZIP. T0's deliberate adversarial red/green gate has not been demonstrated by the package and must remain open.

## No automatic modification of prior official roadmap

This workflow is packaged separately rather than overwriting `reports/next-agent-package/Roadmap.csv` in the frozen architecture archive. That CSV contains stale T0/P2/P5 statuses, and must not serve as execution truth after this transition. The generated controller `ROADMAP_STATUS.md`, external observations, and historical-source snapshots are the intended reconciliation outputs. A future controlled update to the canonical CSV may be planned, not silently committed.
