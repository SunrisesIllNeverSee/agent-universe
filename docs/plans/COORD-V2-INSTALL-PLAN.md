---
type: Runbook
title: multi-agent-coord v2 install plan for agent-universe
description: Step-by-step plan to install the v2 coordination package, clean up branches, fix AGENTS.md, and replace SESSION_RESUME.md. Agreed 2026-07-06.
tags: [coordination, v2, install, branches, cleanup]
timestamp: 2026-07-06T06:00:00Z
last_touched: 2026-07-06 06:00 UTC
---

# multi-agent-coord v2 — Install Plan for agent-universe

**Agreed:** 2026-07-06
**Source package:** `Right Screen/dev-tools/multi-agent-coord-v2/` (28 files)
**Difficulty:** Easy–moderate (file copying + customization, no code changes)

## Context

agent-universe has 540 commits across 3 providers (Claude 370, Devin 9, Copilot 1) with zero coordination between sessions. No SCRATCHPAD, no claims, no hooks. AGENTS.md references a dead COWORK_CLAUDE.md. 21 stale remote branches. This plan installs the v2 coordination system and cleans up the repo.

## Task 1: Commit BRANCH-CLEANUP.md + delete merged branches + review unmerged

1. `git add docs/plans/BRANCH-CLEANUP.md` and commit
2. Delete the 4 confirmed-merged remote branches:
   - `origin/001-civitae-full-build`
   - `origin/claude/fix-mcp-admin-guard`
   - `origin/copilot/build-mcp-for-github`
   - `origin/railway/code-change-N8Csif`
3. For each of the 18 unmerged branches, run `git diff main...origin/{branch} --stat` to see what it touches, then check if that work is already on main. Delete superseded branches. For any with unique work (likely Tier 2: seed card loyalty, MCP endpoint fix, SEO audit), flag them and leave in place.
4. `git fetch --prune` to clean local refs
5. Commit a summary of what was deleted/kept

## Task 2: Install multi-agent-coord v2 + customize

1. Copy from `Right Screen/dev-tools/multi-agent-coord-v2/`:
   - `.agents/claims.yaml`, `.agents/registry.yaml`, `.agents/locks.json` (merge with existing `.agents/skills/`)
   - `Devins_Plans/` (SCRATCHPAD.md, CROSSWIRE.md, DECISIONS.md, handoffs/, state/ROSTER.md, state/ACTIVITY.log)
   - `scripts/` (set-role.sh, lanes.sh, status.sh, install-hooks.sh, install-claude-hooks.sh, check.py, check-okf.mjs, hooks/)
2. Customize `registry.yaml` — fill in project name (CIVITAE / agent-universe), version, status, feature list
3. Customize `lanes.sh` — configure the LANES array for agent-universe (main repo + PyPI `civitae-mcp` package)
4. Run `bash scripts/install-hooks.sh` to wire the post-commit hook
5. Commit

## Task 3: Fix AGENTS.md + CLAUDE.md

1. Replace the dead `COWORK_CLAUDE.md` reference in AGENTS.md with the v2 coordination protocol (11-step protocol from the v2 AGENTS.md template)
2. Keep everything below the `<!-- Edit everything below this line -->` marker — the CIVITAE-specific project state, architecture, conventions
3. Fill in the PROJECT STATE section with: status, repos (agent-universe + related repos), live versions (PyPI civitae-mcp v0.2.0, MCP registry xyz.signomy/civitae v1.1.2)
4. Do the same for CLAUDE.md
5. Commit

## Task 4: SESSION_RESUME.md — keep warm, then archive

1. Extract the live actionable items into a session note appended to `Devins_Plans/SCRATCHPAD.md`:
   - Glama Docker build (build steps, CMD, placeholder params — still paused mid-config)
   - MCP distribution status table (which platforms are live vs. paused/blocked)
   - Credentials reminders (MCP registry private key location, PyPI token note, CircleCI)
   - Open backend backlog (fee credit packs, seed cards, sliding scale reward, etc.)
2. Move `SESSION_RESUME.md` to `docs/archive/SESSION_RESUME.md`
3. Commit

## Verification

- Run `bash scripts/status.sh` — should show roster + empty activity log
- Run `python3 scripts/check.py` — should report clean
- Run `bash scripts/lanes.sh --no-fetch` — should show agent-universe lane
- Run the test suite to confirm no regressions from the file changes
- Verify the post-commit hook works by making a test commit

## Commit strategy

One commit per task (4 commits total). Clean history, easy to revert individually. Once the post-commit hook is installed, each commit auto-logs to SCRATCHPAD.md.
