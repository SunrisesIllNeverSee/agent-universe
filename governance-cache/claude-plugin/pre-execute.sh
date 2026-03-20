#!/bin/bash
# MO§E§™ Pre-Execute Hook
# Runs before any onchain action to verify governance is set.
# Place in .claude/hooks/pre-execute.sh
#
# If governance state file doesn't exist or mode is empty,
# block execution and notify the operator.

GOVERNANCE_STATE="./data/governance_state.json"

if [ ! -f "$GOVERNANCE_STATE" ]; then
    echo "⛔ GOVERNANCE NOT SET — Cannot execute without active governance mode."
    echo "Set a governance mode in COMMAND before proceeding."
    exit 1
fi

MODE=$(python3 -c "import json; print(json.load(open('$GOVERNANCE_STATE')).get('mode', ''))")

if [ -z "$MODE" ] || [ "$MODE" = "null" ]; then
    echo "⛔ GOVERNANCE MODE EMPTY — Cannot execute without active governance mode."
    exit 1
fi

echo "✓ Governance active: $MODE"
exit 0
