---
type: Roster
title: Session Roster — intended tracks + live status
description: Manual roster of active sessions. Set-info (semi-static: role · session · surface) + live status (track · purpose · updated_at UTC). Agents update their OWN row when focus changes. The activity log is ground truth regardless.
tags: [tracker, roster, coordination, sessions]
timestamp: 2026-01-01T00:00:00Z
last_touched: 2026-07-06 05:14 UTC
---

# Session Roster

> **Intended state** (this file) vs **actual activity** (`ACTIVITY.log`). The gap is the signal —
> read after the fact, reconcile by hand. Run `bash scripts/status.sh` to see both side by side.
>
> **Convention:** agents update their OWN row when track/purpose changes. Nothing stops a violation —
> the activity log would show it.

## Roster

| Role | Session | Repo / Surface | Track | Purpose | Updated (UTC) |
|------|---------|---------------|-------|---------|---------------|
| LEAD | session-1 | main repo | set your track | set your purpose | 2026-01-01 00:00 UTC |
| DEVIN | session-2 | (add sessions as they arrive) | — | — | — |

<!--
Add rows as new sessions arrive. Strike retired sessions with ~~strikethrough~~.
The activity log (ACTIVITY.log) is ground truth — this file is intended state.
-->
