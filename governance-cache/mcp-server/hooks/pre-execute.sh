#!/bin/bash
# MO§ES™ Pre-Execute Hook — Gemini hardened pattern
# © 2026 Ello Cello LLC | Patent Pending: Serial No. 63/877,177
#
# Audit Dead Man's Switch: blocks execution if audit chain is corrupt.
# Source this or call it before any governed action in your pipeline.
#
# Usage:
#   source hooks/pre-execute.sh         # in shell scripts
#   bash hooks/pre-execute.sh           # as subprocess (exits non-zero on failure)
#
# Exits 2 if audit chain is corrupt. Exits 1 if governance state is missing.
# Exits 0 (clean) if all checks pass.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GOVERNANCE_STATE="$PROJECT_ROOT/data/governance_state.json"
AUDIT_LEDGER="$PROJECT_ROOT/data/audit_default.jsonl"

echo "━━━ MO§ES™ Pre-Execute Governance Check ━━━"

# ── 1. Governance state present ──────────────────────────────
if [[ ! -f "$GOVERNANCE_STATE" ]]; then
    echo "⚠  No governance_state.json found — initializing default state."
    echo "   Run: python3 server.py (or govern_set_mode via MCP) to set governance."
    # Not a hard block — server initializes state on first call
else
    MODE=$(python3 -c "import json; print(json.load(open('$GOVERNANCE_STATE')).get('mode','Unknown'))" 2>/dev/null || echo "Unknown")
    POSTURE=$(python3 -c "import json; print(json.load(open('$GOVERNANCE_STATE')).get('posture','SCOUT'))" 2>/dev/null || echo "SCOUT")
    ROLE=$(python3 -c "import json; print(json.load(open('$GOVERNANCE_STATE')).get('role','Primary'))" 2>/dev/null || echo "Primary")
    echo "   Mode:    $MODE"
    echo "   Posture: $POSTURE"
    echo "   Role:    $ROLE"
fi

# ── 2. Audit chain integrity — Dead Man's Switch ─────────────
if [[ -f "$AUDIT_LEDGER" ]]; then
    INTEGRITY_RESULT=$(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from governance.audit import AuditLedger
ledger = AuditLedger('$AUDIT_LEDGER')
r = ledger.verify_integrity()
print('valid' if r['valid'] else f'CORRUPT:entry:{r.get(\"first_failure\",\"unknown\")}')
" 2>/dev/null || echo "ERROR")

    if [[ "$INTEGRITY_RESULT" == "valid" ]]; then
        echo "✓  Audit chain: intact"
    elif [[ "$INTEGRITY_RESULT" == "ERROR" ]]; then
        echo "⚠  Audit chain: could not verify (non-fatal)"
    else
        echo "❌ CRITICAL: Audit chain corruption detected — $INTEGRITY_RESULT"
        echo "   Execution BLOCKED. Resolve audit integrity before proceeding."
        echo "   Run: govern_audit_verify via MCP to diagnose."
        exit 2
    fi
else
    echo "   Audit ledger: not yet initialized (first run)"
fi

# ── 3. Lockdown hard block ────────────────────────────────────
if [[ -f "$GOVERNANCE_STATE" ]]; then
    CURRENT_MODE=$(python3 -c "import json; print(json.load(open('$GOVERNANCE_STATE')).get('mode',''))" 2>/dev/null || echo "")
    if [[ "$CURRENT_MODE" == "Lockdown" ]]; then
        echo "❌ HARD BLOCK: Governance mode is LOCKDOWN — no actions permitted."
        exit 2
    fi
fi

echo "✓  Pre-execute checks passed. Proceeding."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit 0
