#!/bin/bash
# MO§E§™ Post-Execute Hook
# Runs after any action to log to audit trail.
# Place in .claude/hooks/post-execute.sh

GOVERNANCE_STATE="./data/governance_state.json"
AUDIT_LEDGER="./data/audit_ledger.jsonl"

if [ -f "$GOVERNANCE_STATE" ]; then
    MODE=$(python3 -c "import json; print(json.load(open('$GOVERNANCE_STATE')).get('mode', 'unknown'))")
    POSTURE=$(python3 -c "import json; print(json.load(open('$GOVERNANCE_STATE')).get('posture', 'unknown'))")
    echo "✓ Action completed under governance: $MODE / $POSTURE"
    echo "✓ Audit entry appended"
else
    echo "⚠ Action completed without governance state file"
fi
