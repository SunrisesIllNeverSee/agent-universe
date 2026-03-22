#!/bin/bash
# CIVITAE Stress Test — 8 agents, full route coverage
# Run this from any terminal: bash ~/Desktop/CIVITAE/stress-test.sh

CIVITAE_DIR="$HOME/Desktop/CIVITAE"
CLAWTEAM="$HOME/.local/bin/clawteam"
TEAM_NAME="civitae-run"
TEMPLATE="civitae-stress"

# Ensure claude and clawteam are findable inside tmux panes
export PATH="$HOME/.local/bin:$PATH"

# ── 1. Start CIVITAE server if not already up ────────────────────────────────
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8300/ | grep -q "200"; then
  echo "✓ CIVITAE already running on :8300"
else
  echo "→ Starting CIVITAE server..."
  cd "$CIVITAE_DIR"
  .venv/bin/python run.py > /tmp/civitae.log 2>&1 &
  sleep 4
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:8300/ | grep -q "200"; then
    echo "✓ CIVITAE up on :8300"
  else
    echo "✗ CIVITAE failed to start. Check /tmp/civitae.log"
    exit 1
  fi
fi

# ── 2. Kill any previous run of this team ────────────────────────────────────
rm -rf "$HOME/.clawteam/teams/$TEAM_NAME" 2>/dev/null
tmux kill-session -t "clawteam-$TEAM_NAME" 2>/dev/null
echo "→ Previous run cleared"

# ── 2b. Ensure tmux server is running ────────────────────────────────────────
if ! tmux list-sessions &>/dev/null; then
  tmux new-session -d -s _placeholder
  echo "→ tmux server started"
fi

# ── 3. Launch 8-agent team ───────────────────────────────────────────────────
echo "→ Launching team: $TEAM_NAME"
$CLAWTEAM launch "$TEMPLATE" \
  --team-name "$TEAM_NAME" \
  --goal "Ship-readiness stress test of CIVITAE at http://localhost:8300. Every route gets hit. Every failure gets named. TonyStark synthesizes the final report."

# ── 4. Attach to watch ───────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  8 agents running: TonyStark / Micro / Nebula"
echo "  K2SO / Erwin / Reiner / Hange / Kleya"
echo ""
echo "  Board:  $CLAWTEAM board show $TEAM_NAME"
echo "  Inbox:  $CLAWTEAM inbox list $TEAM_NAME TonyStark"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Attaching to tmux... (Ctrl+B D to detach)"
sleep 1
tmux attach -t "clawteam-$TEAM_NAME"
