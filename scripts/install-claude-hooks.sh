#!/bin/bash
# install-claude-hooks.sh — wire Claude Code-specific hooks for full automation.
#
# Claude Code supports PreToolUse and UserPromptSubmit hooks, which enable:
#   - File lock conflict warnings before Write/Edit (pre-tool-use.mjs)
#   - Token burn-rate anomaly alerts on prompt submit (burn-rate-guard.mjs)
#
# Other providers (Devin, Codex, Copilot) don't have these hook points.
# They fall back to advisory-only mode (read files, follow convention).
#
# Usage: bash scripts/install-claude-hooks.sh
#
# This writes to .claude/settings.json (or merges with existing config).

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SETTINGS_DIR="$REPO_ROOT/.claude"
SETTINGS_FILE="$SETTINGS_DIR/settings.json"

mkdir -p "$SETTINGS_DIR"

# Read existing settings or start fresh
if [ -f "$SETTINGS_FILE" ]; then
  echo "  Existing .claude/settings.json found — merging hook config"
  EXISTING=$(cat "$SETTINGS_FILE")
else
  EXISTING='{}'
fi

# Build the hook config
HOOKS_CONFIG=$(cat <<'JSON'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "node \"$REPO_ROOT/scripts/hooks/pre-tool-use.mjs\""
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "node \"$REPO_ROOT/scripts/hooks/burn-rate-guard.mjs\""
          }
        ]
      }
    ]
  }
}
JSON
)

# Replace $REPO_ROOT with actual path
HOOKS_CONFIG="${HOOKS_CONFIG//\$REPO_ROOT/$REPO_ROOT}"

# Merge with existing using node
node -e "
const existing = $EXISTING;
const newConfig = $HOOKS_CONFIG;
existing.hooks = existing.hooks || {};
existing.hooks.PreToolUse = newConfig.hooks.PreToolUse;
existing.hooks.UserPromptSubmit = newConfig.hooks.UserPromptSubmit;
process.stdout.write(JSON.stringify(existing, null, 2));
" > "$SETTINGS_FILE.tmp" && mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"

echo "✓ Claude Code hooks installed:"
echo "  PreToolUse (Write|Edit) → file lock conflict warning"
echo "  UserPromptSubmit → burn-rate anomaly alert"
echo ""
echo "  To enable strict lock enforcement: set COORD_STRICT_LOCKS=1 in env"
echo "  To adjust burn thresholds: see scripts/hooks/burn-rate-guard.mjs header"
