#!/bin/bash
# stamp-last-touched.sh — the "library card" hook + activity log append.
#
# PostToolUse(Write|Edit|exec) hook: when a tracked *.md doc is touched:
#   1. Stamp `last_touched: <UTC>` into its YAML frontmatter (library card).
#   2. Append one line to <state_dir>/ACTIVITY.log (tracker, ground truth):
#        "<UTC> · <role> · edited <path>"
#      Role from $TRACKER_ROLE (or $SIGRANK_ROLE for backward compat; unset → "UNKNOWN (in <dir>)").
#
# PORTABLE: configurable via env vars (defaults shown):
#   TRACKER_DOCS_DIR=Devins_Plans   — the docs directory to watch (relative to repo root)
#   TRACKER_STATE_DIR=<docs>/state  — where ACTIVITY.log lives (default: <docs>/state)
#   TRACKER_ROLE / SIGRANK_ROLE     — session role (LEAD/TERM/DEVIN/etc.; unset → UNKNOWN)
#
# Drop into any project: set TRACKER_DOCS_DIR=docs (or whatever your docs dir is called)
# and the hook watches that directory instead. No code changes needed.
#
# (Owner convention 2026-06-28; tracker spec 2026-06-28; see DECISIONS.md.)
#
# Reads the hook payload on stdin. Handles two tool types:
#   - Write|Edit: extracts file_path from tool_input.file_path
#   - exec:       extracts <docs_dir>/*.md paths from tool_input.command
#                 (catches `cat >> <docs_dir>/SCRATCHPAD.md` style appends)
#
# Only touches:
#   - files under <docs_dir>/ ending in .md
#   - that already open with a `---` frontmatter block (for the stamp; the
#     activity log records ANY <docs_dir>/*.md edit regardless of frontmatter)
# Never fails the tool: all errors swallowed, always exits 0.

set +e

payload="$(cat)"

# ─── Config (env vars with defaults — portable across projects) ─────────────
docs_dir="${TRACKER_DOCS_DIR:-Devins_Plans}"

# ─── Resolve repo root (for relative paths + state dir) ─────────────────────
repo_root="${DEVIN_PROJECT_DIR:-$CLAUDE_PROJECT_DIR}"
[ -n "$repo_root" ] || repo_root="$(cd "$(dirname "$0")/../.." && pwd)"

state_dir="${TRACKER_STATE_DIR:-$repo_root/$docs_dir/state}"
activity_log="$state_dir/ACTIVITY.log"

# ─── Extract target file path(s) from the payload ───────────────────────────
# Try Write|Edit first (file_path field), then exec (command field).
tool_name="$(printf '%s' "$payload" | jq -r '.tool_name // empty' 2>/dev/null)"

files=""

if [ "$tool_name" = "exec" ] || [ "$tool_name" = "Bash" ] || [ "$tool_name" = "PowerShell" ]; then
  # Exec/Shell tool: extract any <docs_dir>/*.md paths from the command string.
  cmd="$(printf '%s' "$payload" | jq -r '.tool_input.command // empty' 2>/dev/null)"
  if [ -n "$cmd" ]; then
    # Extract <docs_dir>/*.md paths from the command (relative or absolute).
    # The docs_dir name is interpolated into the regex so it's portable.
    files="$(printf '%s' "$cmd" | grep -oE "([^[:space:]\"']*/)?${docs_dir}/[A-Za-z0-9_./-]+\.md" 2>/dev/null | sort -u)"
  fi
else
  # Write|Edit tool: extract the file_path directly.
  f="$(printf '%s' "$payload" | jq -r '.tool_input.file_path // .tool_response.filePath // empty' 2>/dev/null)"
  [ -n "$f" ] && files="$f"
fi

# No files to stamp → exit quietly.
[ -n "$files" ] || exit 0

now="$(date -u '+%Y-%m-%d %H:%M UTC')"

# ─── Role resolution (for the activity log) ─────────────────────────────────
# Priority: (1) $TRACKER_ROLE / $SIGRANK_ROLE if the env actually reaches this
# hook process (rare — see below), (2) a per-session role FILE keyed off the
# session_id in the hook payload, (3) UNKNOWN.
#
# WHY THE FILE (root-cause fix 2026-06-30): this hook runs as a subprocess
# Claude Code spawns; it inherits Claude Code's env, NOT the env of any single
# Bash tool call. So `export SIGRANK_ROLE=LEAD` run inside a Bash tool only sets
# the var in that throwaway subshell — it NEVER reaches this hook, which is why
# ACTIVITY.log logged 492/492 UNKNOWN despite everyone "logging in". The durable
# fix: a session writes its role to state/.role-<session_id> (via
# `scripts/set-role.sh <ROLE>`), and we read it here keyed on the session_id the
# hook payload carries on stdin. The role then lives in a file the hook CAN read,
# scoped to the session. Env vars still win if they happen to be set.
role="${TRACKER_ROLE:-${SIGRANK_ROLE:-}}"
if [ -z "$role" ]; then
  session_id="$(printf '%s' "$payload" | jq -r '.session_id // empty' 2>/dev/null)"
  if [ -n "$session_id" ] && [ -f "$state_dir/.role-$session_id" ]; then
    role="$(head -1 "$state_dir/.role-$session_id" 2>/dev/null | tr -d '[:space:]')"
  fi
fi
# Fallback: if payload session_id didn't match a role file (e.g. Devin CLI
# sends a different session_id format than Claude Code), try .session-current
# which was written by set-role.sh via session-start.sh.
if [ -z "$role" ] && [ -f "$state_dir/.session-current" ]; then
  fallback_sid="$(head -1 "$state_dir/.session-current" 2>/dev/null | tr -d '[:space:]')"
  if [ -n "$fallback_sid" ] && [ -f "$state_dir/.role-$fallback_sid" ]; then
    role="$(head -1 "$state_dir/.role-$fallback_sid" 2>/dev/null | tr -d '[:space:]')"
  fi
fi
if [ -z "$role" ]; then
  role="UNKNOWN (in $(basename "$(pwd)"))"
fi

# ─── Stamp each target file + append activity log ───────────────────────────
while IFS= read -r f; do
  [ -n "$f" ] || continue

  # Guard: must be a real <docs_dir> markdown file.
  case "$f" in
    */${docs_dir}/*.md) ;;
    ${docs_dir}/*.md) ;;
    *) continue ;;
  esac
  [ -f "$f" ] || continue

  # ── Activity log append (ground truth — records ANY <docs_dir>/*.md edit) ──
  # Make the path relative to repo root for readability.
  rel="$f"
  case "$f" in
    "$repo_root"/*) rel="${f#"$repo_root"/}" ;;
  esac
  # Ensure state dir exists (best effort — swallowed on failure).
  mkdir -p "$state_dir" 2>/dev/null
  printf '%s · %s · edited %s\n' "$now" "$role" "$rel" >> "$activity_log" 2>/dev/null

  # ── Library card stamp (requires frontmatter) ──────────────────────────────
  # Must have a frontmatter block (line 1 == '---').
  [ "$(head -1 "$f")" = "---" ] || continue

  # Find the closing '---' of the frontmatter (first one after line 1).
  close="$(awk 'NR>1 && /^---[[:space:]]*$/ {print NR; exit}' "$f")"
  [ -n "$close" ] || continue

  if grep -qE '^last_touched:' "$f"; then
    # Update the existing line in place (only within frontmatter — it's a unique key).
    perl -i -pe "s/^last_touched:.*/last_touched: $now/ if \$. <= $close" "$f" 2>/dev/null
  else
    # Insert a last_touched line just before the closing '---'.
    awk -v n="$close" -v stamp="last_touched: $now" 'NR==n{print stamp} {print}' "$f" > "$f.tmp" 2>/dev/null && mv "$f.tmp" "$f"
  fi
done <<< "$files"

exit 0
