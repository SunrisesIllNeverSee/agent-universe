---
type: Design
title: Future Design Lock — SIGNOMY / Agent Universe
description: Hold note for the next design session. Preserve the current redesign direction, collect owner suggestions, then lock the visual shell before further IA cleanup.
tags: [design, future, lock, signomy, agent-universe]
timestamp: 2026-10-01
status: future-review
---

# Future Design Lock — SIGNOMY / Agent Universe

## Status

**Future note only. Do not implement from this file yet.**

The current redesign is a strong candidate to become the stable visual/product shell. Before locking it, the owner has additional suggestions to review in a later design session.

The next session should start from the current shipped design rather than reopening earlier redesign directions.

## Candidate elements to preserve

- Current homepage identity: **SIGNOMY § CIVITAE**
- Current agent-city / governed marketplace framing
- Two-door entry model:
  - AI agents / AAI
  - humans / BI
- Current top-level site model:
  - Active
  - Context
  - Building
- Core product locations:
  - KA§§A
  - Missions
  - Forums
  - Advisory / Governance
  - agent dashboard / operator cockpit
- Current visual language:
  - dark obsidian base
  - gold accents
  - Playfair Display + DM Mono
  - layered global navigation

## What should *not* trigger another redesign

Remaining work is primarily information architecture and route consolidation, not a reason to replace the visual system.

Known cleanup areas include:

- `agent` / `agent-profile` / `agentdash` / `dashboard`
- `console` / `command`
- KA§§A detail surfaces and duplicated marketplace entry points
- parallel provision and KA§§A registration/login doors
- stale route metadata where old surfaces still claim canonical ownership

Example already identified: `config/pages.json` still describes Kingdoms as "also served at /", while the current root homepage is the SIGNOMY § CIVITAE landing page.

## Next design-session rule

Before changing the current shell:

1. Review the owner's additional suggestions.
2. Compare them against the current shipped homepage/nav/system.
3. Decide which changes are additive versus structural.
4. Lock the selected homepage/nav/visual system.
5. After the lock, treat future changes as surgical product/IA work rather than broad redesigns.

## Intent

The purpose of this note is to prevent future agents from interpreting unfinished route cleanup as permission to redesign the product again.

The current direction should be treated as the baseline for the next review.
