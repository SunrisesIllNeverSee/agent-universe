---
type: Reference
title: DECISIONS — why things are the way they are
description: Decision log for non-obvious choices. Append-only. If you're wondering "why is X like this?", check here first. If the answer isn't here, add it after you find out.
tags: [decisions, reference, architecture]
timestamp: 2026-01-01T00:00:00Z
last_touched: 2026-07-06 05:14 UTC
---

# DECISIONS — why things are the way they are

> Append-only. If you're wondering "why is X like this?", check here first.
> If the answer isn't here, add it after you find out.

## D1 — File-based coordination, not daemon-based

**Decision:** Sessions coordinate through files (SCRATCHPAD.md, ACTIVITY.log, ROSTER.md), not through a daemon or MCP server.

**Why:** Daemon-based coordination has a single point of failure. If the daemon crashes, coordination vanishes. File-based coordination fails open — the worst case is a stale file, not a crashed coordinator. Files also travel with the repo (via git), so coordination history is preserved.

**Trade-off:** No real-time conflict detection. Sessions can step on each other. Mitigated by: (1) the bus protocol (announce before editing shared files), (2) the activity log (see what was touched), (3) the human as merge gate.

## D2 — Owner-mediated bus, not agent-to-agent

**Decision:** Messages are `### ⤷ FROM → TO: subject`, owner relays between sessions.

**Why:** Agents in separate terminals can't see each other's output. The owner is the only one who sees all sessions. Making the owner the relay is honest about the architecture.

**Trade-off:** Owner is a serial bottleneck for cross-session decisions. Acceptable — the owner should be in the loop for decisions anyway.

## D3 — Activity log is ground truth, roster is intended state

**Decision:** ACTIVITY.log (auto-stamped by hooks) is the source of truth. ROSTER.md (manually maintained) is what sessions *intended* to do. The gap between them is the signal.

**Why:** Manual tracking drifts. Automated tracking doesn't. By having both, you can see when sessions say they're working on X but are actually editing Y.

## D4 — Hooks fail open

**Decision:** All git hooks (post-commit, session-start, stamp-last-touched) swallow errors and exit 0. They never block work.

**Why:** A coordination hook that blocks your commit is worse than no coordination. The hooks are for tracking, not enforcement. If they break, you lose tracking, not your work.

## D5 — OKF frontmatter on every doc

**Decision:** Every markdown doc in the docs directory carries YAML frontmatter with type/title/description/tags/timestamp.

**Why:** Makes every doc a searchable knowledge object. The `last_touched` field (auto-stamped by hooks) tells you when a doc was last edited. The linter (`check-okf.mjs`) catches missing frontmatter.

## D6 — Machine-readable claims alongside human-readable bus

**Decision:** `claims.yaml` (machine-readable lane claims) and `registry.yaml` (machine-readable truth ledger) live alongside SCRATCHPAD.md (human-readable bus) and ACTIVITY.log (auto-stamped ground truth).

**Why:** The human-readable bus is for context and decisions. The machine-readable ledgers are for validation — `check.py` can catch overlapping claims, stale sessions, and migration number conflicts that a human reading SCRATCHPAD would miss. They're complementary: ACTIVITY.log = what happened, claims.yaml = what's intended, registry.yaml = what's true.

**Trade-off:** Two more files to maintain. Mitigated by: claims are append-only (low overhead), registry updates only on state changes (migrations, shipped features).

## D7 — File locks with expiry, not permanent locks

**Decision:** `locks.json` uses 2-hour expiry on file locks. Expired locks are ignored.

**Why:** Dead sessions hold locks forever without expiry. A 2-hour window is long enough for a real work session but short enough that a crashed session doesn't block work indefinitely. The PreToolUse hook (Claude Code only) checks locks before Write/Edit — advisory by default, strict with `COORD_STRICT_LOCKS=1`.

**Trade-off:** A slow session might lose its lock mid-work. Mitigated by: the lock is advisory, not a hard block (unless strict mode). Re-claim if needed.

## D8 — Provider-agnostic by design, automated where possible

**Decision:** The system works with any AI coding tool that can read/write files. Claude Code gets full automation (PreToolUse, UserPromptSubmit hooks). Other providers (Devin, Codex, Copilot, Cursor, Gemini) get advisory-only mode (read files, follow convention).

**Why:** Different providers have different hook capabilities. Building for the lowest common denominator would waste Claude Code's hook system. Building only for Claude Code would lock out other providers. The files are the protocol — hooks are a convenience layer that degrades gracefully.

**Trade-off:** Non-Claude providers don't get lock enforcement or burn-rate alerts. They rely on convention (reading claims.yaml before editing). Acceptable — the bus protocol and activity log catch most issues regardless.

## D9 — Structured handoffs for cold-start pickup

**Decision:** `handoffs/` directory with structured handoff docs (what's done / what's needed / pickup files / open questions / authority limits).

**Why:** A freeform bus message is great for "here's what I'm doing" but terrible for "here's what you need to do next." A structured handoff lets a receiving session pick up cold without reading the entire bus history. The template lives at `handoffs/TEMPLATE.md`.

## D10 — Cross-repo bus (CROSSWIRE) separate from repo-local bus (SCRATCHPAD)

**Decision:** SCRATCHPAD.md is repo-local. CROSSWIRE.md is machine-local. Different scopes, different files.

**Why:** Mixing repo-local and cross-repo messages in one file creates noise. A session working on repo X doesn't need to see repo Y's handoffs. CROSSWIRE is only for work that spans repos — "I pushed to the app, the MCP needs a version bump."

## D11 — Three generations unified

**Decision:** This package unifies three prior generations of multi-agent coordination:
- Gen 1 (5_comms): structured handoffs, file locks with expiry, operator inbox
- Gen 2a (substrate): machine-readable claims/registry, check.py validator, cross-workspace bus, pitch docs
- Gen 2b (claude-coord): session identity, file stamps, broadcast queue, cowork mode, burn-rate guard, 7 skills
- Gen 3 (RNS): automated hooks, ACTIVITY.log, ROSTER gap, lanes.sh, OKF frontmatter

**Why:** Each generation solved a different layer and lost what the previous had figured out. Gen 3 nailed automation but dropped machine-readable claims. Gen 2a nailed machine-readable truth but never automated. Gen 2b nailed collaboration primitives but never shipped. Gen 1 nailed protocol but had no automation. This package combines all six layers.
