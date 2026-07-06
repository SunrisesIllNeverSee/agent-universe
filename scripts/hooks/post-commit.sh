#!/bin/bash
# post-commit.sh — appends every commit to the SCRATCHPAD commit log.
#
# This is the COMMITTED, travels-with-the-repo version of the old
# .git/hooks/post-commit. The original broke two ways (2026-06-17):
#   1. It pointed at $REPO_ROOT/_merge/LOG.md — but that file moved to
#      Devins_Plans/_merge/LOG.md, so it silently no-op'd (file not found → exit 0).
#   2. It lived in .git/hooks/ which NEVER travels (clone/push drop it), so it only
#      existed in one session's local setup → "tied to the environment, not the repo".
#
# Fix: this script lives IN the repo (scripts/hooks/), is installed into .git/hooks
# by scripts/install-hooks.sh, and targets the canonical bus (SCRATCHPAD.md). Any
# session/clone runs `bash scripts/install-hooks.sh` once and the log self-feeds.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
LOG_FILE="$REPO_ROOT/Devins_Plans/SCRATCHPAD.md"
MARKER='<!-- POST-COMMIT HOOK APPENDS BELOW THIS LINE -->'

# No-op cleanly if the bus or its marker is absent (don't ever fail a commit).
[ -f "$LOG_FILE" ] || exit 0
grep -q "$MARKER" "$LOG_FILE" || exit 0

HASH=$(git rev-parse --short HEAD)
TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M UTC')
SUBJECT=$(git log -1 --pretty=format:'%s' | tr -d '\\')
AUTHOR=$(git log -1 --pretty=format:'%an')
ENTRY="[HOOK] $TIMESTAMP · $HASH · $AUTHOR · $SUBJECT"

# Insert directly after the marker line (newest entries appear at the top of the log).
sed -i.bak "/$MARKER/a\\
$ENTRY" "$LOG_FILE"
rm -f "$LOG_FILE.bak"
