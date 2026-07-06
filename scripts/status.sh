#!/bin/bash
# status.sh — session status viewer (portable).
#
# Prints the roster table (intended state) THEN the last N (default 15) ACTIVITY.log
# lines (actual activity). Shows both layers plainly. FLAGS NOTHING, compares nothing,
# computes no drift. Run it, read it, decide for yourself.
#
# PORTABLE: configurable via env vars (same as the hook):
#   TRACKER_DOCS_DIR=Devins_Plans   — the docs directory (relative to repo root)
#   TRACKER_STATE_DIR=<docs>/state  — where ACTIVITY.log + ROSTER.md live
#
# Usage: bash scripts/status.sh [N]    (N = number of activity lines, default 15)

set +e

# ─── Config (env vars with defaults — portable across projects) ─────────────
docs_dir="${TRACKER_DOCS_DIR:-Devins_Plans}"

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
state_dir="${TRACKER_STATE_DIR:-$repo_root/$docs_dir/state}"
roster="$state_dir/ROSTER.md"
activity="$state_dir/ACTIVITY.log"
n="${1:-15}"

# ─── Header ──────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "  Session Status — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "═══════════════════════════════════════════════════════════════════════════════"
echo ""

# ─── Layer B: Roster (intended state) ────────────────────────────────────────
echo "─── ROSTER (intended state) ───────────────────────────────────────────────────"
echo ""
if [ -f "$roster" ]; then
  # Print the roster table (the markdown table between "## Roster" and the next "---" or "## ").
  # Simplest: print the whole file body after the frontmatter, skip the prose.
  awk '
    /^---$/ && in_fm { in_fm=0; next }
    /^---$/ { in_fm=1; next }
    in_fm { next }
    /^## Roster/ { show=1; next }
    /^---$/ { show=0 }
    /^## / { show=0 }
    show { print }
  ' "$roster"
else
  echo "  (no roster yet — create $docs_dir/state/ROSTER.md)"
fi
echo ""

# ─── Layer A: Activity log (actual, ground truth) ────────────────────────────
echo "─── ACTIVITY (last $n lines, ground truth) ────────────────────────────────────"
echo ""
if [ -f "$activity" ] && [ -s "$activity" ]; then
  tail -n "$n" "$activity" 2>/dev/null | while IFS= read -r line; do
    [ -n "$line" ] && printf "  %s\n" "$line"
  done
  total=$(wc -l < "$activity" 2>/dev/null | tr -d ' ')
  echo ""
  echo "  ($total total lines in ACTIVITY.log)"
else
  echo "  (no activity yet — ACTIVITY.log is created on the first $docs_dir/*.md edit)"
fi
echo ""

# ─── Footer ──────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════════════════════"
echo "  This is a TRACKER, not governance. Flags nothing. Reads the gap by hand."
echo "═══════════════════════════════════════════════════════════════════════════════"
