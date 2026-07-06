#!/bin/bash
# session-start.sh — SessionStart hook: record THIS session's id so set-role.sh
# can map a human-chosen role (LEAD/TERM/DEVIN/…) to the session_id that the
# PostToolUse stamp hook reads from its own payload.
#
# WHY THIS EXISTS (root-cause fix 2026-06-30): the activity log logged 492/492
# UNKNOWN because the documented `export SIGRANK_ROLE=LEAD` runs in a throwaway
# Bash-tool subshell that the stamp hook (a separate subprocess) never inherits.
# The durable fix is a per-session role FILE keyed on session_id. A Bash tool
# call can't read its own session_id, but THIS hook gets it on stdin — so we
# stash it at state/.session-current for set-role.sh to consume.
#
# Writes: <state_dir>/.session-current  (single line: the current session_id)
# Never fails the session: all errors swallowed, always exits 0.

set +e
payload="$(cat)"

docs_dir="${TRACKER_DOCS_DIR:-Devins_Plans}"
repo_root="${DEVIN_PROJECT_DIR:-$CLAUDE_PROJECT_DIR}"
[ -n "$repo_root" ] || repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
state_dir="${TRACKER_STATE_DIR:-$repo_root/$docs_dir/state}"

session_id="$(printf '%s' "$payload" | jq -r '.session_id // empty' 2>/dev/null)"
[ -n "$session_id" ] || exit 0
mkdir -p "$state_dir" 2>/dev/null
printf '%s\n' "$session_id" > "$state_dir/.session-current" 2>/dev/null

exit 0
