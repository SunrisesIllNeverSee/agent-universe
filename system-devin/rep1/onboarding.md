---
type: Handoff
title: rep1 (LEAD) Onboarding
description: Onboarding for a new rep1/LEAD session in agent-universe. Read this FIRST before starting any work.
tags: [repo-standard, coordination, drep, rep1, lead, onboarding]
timestamp: 2026-08-19
---

# rep1 (LEAD) Onboarding

You are **rep1** — the LEAD. Your role: primary build coordination, documentation, big-picture.

## Role mapping

- **OWNER** = Owner. Human. Mediates decisions, fires external actions.
- **rep1 / LEAD** = You. Coordinate, track status, documentation.
- **rep2 / ASSIST** = Assistant lane. One-off tasks, reports to you.

## Session start

```bash
bash .coord/micro/scripts/set-role.sh rep1
bash .coord/micro/scripts/status.sh
```

## Read order

1. `REPO.yaml`
2. `AGENTS.md`
3. `.coord/micro/STATE.md`
4. tail of `.coord/micro/SCRATCHPAD.md`
5. current handoff: `bash .coord/micro/scripts/handoff.sh current LEAD`

## While working

- All reports go through `.coord/micro/SCRATCHPAD.md` using arrow format:
  - `### ⤷ rep1 → rep2: <task>` — assign work to rep2
  - `### ⤷ rep1 → Log: <summary>` — your own reports
  - `### ⤷ rep1 → OWNER: <question>` — items needing owner decisions

## Before stopping

```bash
bash .coord/micro/scripts/handoff.sh generate rep1
bash .coord/micro/scripts/save-state.sh "summary of what you did"
bash .coord/micro/scripts/signout.sh "summary"
```
