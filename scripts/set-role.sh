#!/bin/bash
# set-role.sh — claim this session's tracker role (LEAD / DEVIN / DEVIN1 / GTM / …).
#
# THE fix for the "ACTIVITY.log logs UNKNOWN forever" bug. Run ONCE per session:
#
#   bash scripts/set-role.sh LEAD
#
# Why not `export SIGRANK_ROLE=LEAD`? Because that export lives only in the
# Bash-tool subshell and never reaches the PostToolUse stamp hook (a separate
# subprocess) — which is exactly why every prior log line said UNKNOWN. This
# helper instead writes a per-session role FILE that the hook CAN read, keyed on
# the session_id the SessionStart hook recorded at state/.session-current.
#
# Result: every subsequent Devins_Plans/*.md edit logs with your real role.

set -euo pipefail

role="${1:-}"
if [ -z "$role" ]; then
  echo "usage: bash scripts/set-role.sh <ROLE>   e.g. LEAD | DEVIN | DEVIN1 | GTM" >&2
  exit 1
fi

docs_dir="${TRACKER_DOCS_DIR:-Devins_Plans}"
repo_root="$(git rev-parse --show-toplevel 2>/dev/null)"
[ -n "$repo_root" ] || repo_root="$(cd "$(dirname "$0")/.." && pwd)"
state_dir="${TRACKER_STATE_DIR:-$repo_root/$docs_dir/state}"
marker="$state_dir/.session-current"

if [ ! -f "$marker" ]; then
  echo "✗ no $marker — the SessionStart hook hasn't run yet." >&2
  echo "  Open /hooks once (or restart the session) so session-start.sh fires, then re-run." >&2
  exit 1
fi

session_id="$(head -1 "$marker" | tr -d '[:space:]')"
[ -n "$session_id" ] || { echo "✗ empty session id in $marker" >&2; exit 1; }

printf '%s\n' "$role" > "$state_dir/.role-$session_id"
echo "✓ role for this session = $role  (state/.role-$session_id)"
echo "  Every Devins_Plans/*.md edit from now logs as '$role' in ACTIVITY.log."
