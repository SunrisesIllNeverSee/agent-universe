#!/bin/bash
# MO§ES™ Post-Execute AAR Hook — Gemini pattern
# © 2026 Ello Cello LLC | Patent Pending: Serial No. 63/877,177
#
# After-Action Review: verifies output matched governance constraints.
# Detects posture breaches (e.g. files modified while in SCOUT mode).
# Logs violations to the audit ledger.
#
# Usage:
#   bash hooks/post-execute.sh [component] [action]
#   bash hooks/post-execute.sh "agent" "code_generation"
#
# Arguments (optional):
#   $1 — component name for audit log (default: "post-execute")
#   $2 — action name for audit log (default: "aar_check")

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GOVERNANCE_STATE="$PROJECT_ROOT/data/governance_state.json"
AUDIT_LEDGER="$PROJECT_ROOT/data/audit_default.jsonl"

COMPONENT="${1:-post-execute}"
ACTION="${2:-aar_check}"

echo "━━━ MO§ES™ After-Action Review ━━━"

# ── 1. Load current posture ───────────────────────────────────
CURRENT_POSTURE="SCOUT"
CURRENT_MODE="None (Unrestricted)"
if [[ -f "$GOVERNANCE_STATE" ]]; then
    CURRENT_POSTURE=$(python3 -c "import json; print(json.load(open('$GOVERNANCE_STATE')).get('posture','SCOUT'))" 2>/dev/null || echo "SCOUT")
    CURRENT_MODE=$(python3 -c "import json; print(json.load(open('$GOVERNANCE_STATE')).get('mode','Unknown'))" 2>/dev/null || echo "Unknown")
fi

echo "   Mode: $CURRENT_MODE | Posture: $CURRENT_POSTURE"

# ── 2. SCOUT posture breach detection ────────────────────────
# If in SCOUT, no files should have been modified.
AAR_STATUS="CLEAN"
BREACH_DETAIL=""

if [[ "$CURRENT_POSTURE" == "SCOUT" ]]; then
    # Check git status for modifications
    if command -v git &>/dev/null && git -C "$PROJECT_ROOT" rev-parse --git-dir &>/dev/null; then
        MODIFIED_FILES=$(git -C "$PROJECT_ROOT" status --short 2>/dev/null | grep -v '^\?' || true)
        if [[ -n "$MODIFIED_FILES" ]]; then
            AAR_STATUS="BREACH"
            BREACH_DETAIL="SCOUT modified files detected: $(echo "$MODIFIED_FILES" | tr '\n' '|' | sed 's/|$//')"
            echo "⚠  POSTURE BREACH: Modifications detected in SCOUT mode"
            echo "   Files: $MODIFIED_FILES"
        else
            echo "✓  SCOUT posture: no modifications detected"
        fi
    else
        echo "   SCOUT check: git not available — skipping file modification check"
    fi
else
    echo "✓  Posture $CURRENT_POSTURE: modification checks not required"
fi

# ── 3. Log AAR result to audit ledger ────────────────────────
if [[ -f "$AUDIT_LEDGER" ]] || [[ "$AAR_STATUS" == "BREACH" ]]; then
    python3 -c "
import sys, json
sys.path.insert(0, '$PROJECT_ROOT')
from governance.audit import AuditLedger

ledger = AuditLedger('$AUDIT_LEDGER')
ledger.log_action(
    component='$COMPONENT',
    action='$ACTION',
    detail={
        'aar_status': '$AAR_STATUS',
        'posture': '$CURRENT_POSTURE',
        'mode': '$CURRENT_MODE',
        'breach_detail': '$BREACH_DETAIL',
    },
    governance_mode='$CURRENT_MODE',
    posture='$CURRENT_POSTURE',
    role='',
)
print('   AAR logged to audit ledger.')
" 2>/dev/null || echo "   AAR log: audit ledger not yet initialized"
fi

# ── 4. Final status ───────────────────────────────────────────
if [[ "$AAR_STATUS" == "BREACH" ]]; then
    echo "⚠  AAR complete — POSTURE BREACH logged. Review audit ledger."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
else
    echo "✓  AAR complete — clean execution."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
fi
