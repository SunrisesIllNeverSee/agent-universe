---
type: Reference
title: DREP Coordination Root — system-devin
description: Canonical DREP coordination root for agent-universe. rep1=LEAD, rep2=ASSIST, OWNER=human. Single operational coordination state.
tags: [repo-standard, coordination, drep, system-devin]
timestamp: 2026-08-19
---

# DREP Coordination Root

This directory is the canonical DREP coordination root for `agent-universe`.

## Role mapping (canonical, non-negotiable)

| DREP name | Standard name | Human/Agent | Role |
|-----------|--------------|-------------|------|
| OWNER | OWNER | Human (Owner) | Decisions, external actions |
| rep1 | LEAD | Agent | Primary build coordination, documentation, big-picture |
| rep2 | ASSIST | Agent | Bounded support lane, one-off tasks, reports to rep1 |

## Single coordination state

The live coordination bus is `.coord/micro/SCRATCHPAD.md`.
The live session state is `.coord/micro/STATE.md`.

`system-devin/` holds per-role onboarding and handoff state.
It does NOT hold a competing scratchpad or state file.

## Pre-existing coordination (preserved, NOT active bus)

This repo has extensive pre-existing coordination infrastructure:
- `Devins_Plans/SCRATCHPAD.md` — legacy scratchpad bus
- `Devins_Plans/STATE.md` — legacy state
- `Devins_Plans/handoffs/` — legacy handoffs
- `Devins_Plans/DECISIONS.md` — legacy decisions log
- `Devins_Plans/CROSSWIRE.md` — legacy cross-repo bus
- `Devins_Plans/state/ROSTER.md` — legacy roster
- `.agents/claims.yaml` — legacy lane claims
- `scripts/set-role.sh`, `scripts/check.py`, `scripts/status.sh` — legacy coordination scripts

All preserved as historical record. The canonical bus is now
`.coord/micro/SCRATCHPAD.md`. Do NOT create competing scratchpads.
