"""
MO§ES™ MCP Governance Server — server.py
© 2026 Ello Cello LLC — Patent pending: Serial No. 63/877,177

FastMCP server exposing 16 governance, vault, and audit tools.
Transport: stdio (local dev / Claude Code)
State:     in-memory GovernanceState per session + persistent JSONL audit ledger

Tools (v1.1):
  Core (13): govern_set_mode, govern_set_posture, govern_set_role,
             govern_check_action, govern_get_status, govern_assemble_context,
             vault_load, vault_list, vault_clear,
             audit_log, audit_verify, audit_recent, audit_hash_session
  v1.1 (+3): govern_check_commitment, govern_oracle_verify, govern_run_swarm_round

Run:
    python3 server.py

Connect via .mcp.json (Claude Code) — see repo root.
"""

import json
import os
import uuid
from pathlib import Path

from fastmcp import FastMCP, Context

from governance.engine import (
    GovernanceState,
    translate_mode,
    translate_posture,
    get_role_instruction,
    assemble_context,
    check_action_permitted,
    resolve_mode,
    MODES,
    POSTURES,
    ROLES,
)
from governance.audit import (
    AuditLedger,
    hash_governance_state,
    hash_conversation,
    format_for_onchain,
)
from governance.commitment import evaluate_commitment, score_commitment
from governance.oracle import grok_verify_sync
from governance.swarm import run_swarm_round, SwarmConfig
from governance.meta import (
    analyze_audit_trail,
    apply_amendment,
    list_proposals,
    get_proposal,
    reject_proposal,
    rollback_amendment,
    constitution_status,
    make_operator_sig,
    _get_operator_secret,
)

# ---------------------------------------------------------------------------
# Server init
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="moses-governance",
    version="1.2.0",
    instructions="Constitutional governance engine for AI agents — MO§ES™",
)

# ---------------------------------------------------------------------------
# Session state (in-memory dict per session)
# ---------------------------------------------------------------------------

_sessions: dict[str, GovernanceState] = {}
_ledgers: dict[str, AuditLedger] = {}

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

GOVERNANCE_STATE_FILE = DATA_DIR / "governance_state.json"


def _get_session(session_id: str) -> GovernanceState:
    """Return existing GovernanceState or create default for session_id."""
    if session_id not in _sessions:
        _sessions[session_id] = GovernanceState()
    return _sessions[session_id]


def _get_ledger(session_id: str) -> AuditLedger:
    """Return existing AuditLedger or create one for session_id."""
    if session_id not in _ledgers:
        ledger_path = DATA_DIR / f"audit_{session_id}.jsonl"
        _ledgers[session_id] = AuditLedger(ledger_path)
    return _ledgers[session_id]


def _resolve_session(ctx: Context | None) -> str:
    """Resolve session ID from MCP context, or use 'default'."""
    try:
        if ctx and hasattr(ctx, "session_id") and ctx.session_id:
            return str(ctx.session_id)
    except Exception:
        pass
    return "default"


def _persist_state(gs: GovernanceState):
    """Write governance state snapshot to governance_state.json."""
    import dataclasses
    snapshot = dataclasses.asdict(gs)
    GOVERNANCE_STATE_FILE.write_text(json.dumps(snapshot, indent=2))


# ---------------------------------------------------------------------------
# GOVERNANCE TOOLS
# ---------------------------------------------------------------------------

@mcp.tool()
def govern_set_mode(mode: str, ctx: Context | None = None) -> dict:
    """
    Set the active governance mode.
    Accepts canonical names or aliases (idk, high-security, self-growth, etc.)
    Updates in-memory GovernanceState and writes governance_state.json.
    Returns: {"mode": canonical_name, "constraints": [...], "prohibited": [...]}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)

    canonical = resolve_mode(mode)
    gs.mode = canonical
    _persist_state(gs)

    result = {"mode": canonical, **translate_mode(canonical)}
    _get_ledger(session_id).log_action(
        component="govern",
        action="set_mode",
        detail={"mode": canonical},
        governance_mode=gs.mode,
        posture=gs.posture,
        role=gs.role,
    )
    return result


@mcp.tool()
def govern_set_posture(posture: str, ctx: Context | None = None) -> dict:
    """
    Set operational posture: SCOUT | DEFENSE | OFFENSE.
    SCOUT = read-only, no state changes.
    DEFENSE = protect assets, outbound requires confirmation.
    OFFENSE = execute within governance constraints.
    Returns: {"posture": str, "behavior": str, "transaction_policy": str}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)

    canonical = posture.strip().upper()
    result = {"posture": canonical, **translate_posture(canonical)}
    gs.posture = canonical
    _persist_state(gs)

    _get_ledger(session_id).log_action(
        component="govern",
        action="set_posture",
        detail={"posture": gs.posture},
        governance_mode=gs.mode,
        posture=gs.posture,
        role=gs.role,
    )
    return result


@mcp.tool()
def govern_set_role(role: str, ctx: Context | None = None) -> dict:
    """
    Set hierarchy role: Primary | Secondary | Observer.
    Primary leads. Secondary validates. Observer flags only.
    Returns: {"role": str, "authority": str, "instruction": str, "constraints": [...]}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)

    canonical = role.strip().title()
    result = {"role": canonical, **get_role_instruction(canonical)}
    gs.role = canonical
    _persist_state(gs)

    _get_ledger(session_id).log_action(
        component="govern",
        action="set_role",
        detail={"role": gs.role},
        governance_mode=gs.mode,
        posture=gs.posture,
        role=gs.role,
    )
    return result


@mcp.tool()
def govern_check_action(action_description: str, ctx: Context | None = None) -> dict:
    """
    Check if a proposed action is permitted under current governance.
    Uses concept extraction + rule-driven evaluation against active mode's prohibited list.
    Returns: {"permitted": bool, "reason": str, "triggered_rules": [...], "conditions": [...]}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)

    result = check_action_permitted(action_description, gs)

    _get_ledger(session_id).log_action(
        component="govern",
        action="check_action",
        detail={"action_description": action_description, "permitted": result["permitted"]},
        governance_mode=gs.mode,
        posture=gs.posture,
        role=gs.role,
    )
    return result


@mcp.tool()
def govern_get_status(ctx: Context | None = None) -> dict:
    """
    Return full current GovernanceState.
    Returns: {"mode": str, "posture": str, "role": str, "vault_documents": [...], ...all fields}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)

    import dataclasses
    status = dataclasses.asdict(gs)
    status["vault_count"] = len(gs.vault_documents)
    return status


@mcp.tool()
def govern_assemble_context(
    messages: list[dict],
    agent_name: str = "agent",
    previous_responses: list[dict] | None = None,
    ctx: Context | None = None,
) -> dict:
    """
    Build the full governed context payload for an agent.
    This is the core IP — every agent read passes through here.
    Returns full governed payload: constitutional_governance, role_assignment,
    user_profile, vault_context, messages, [prior_responses if Secondary/Observer]
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)
    gs.agent_name = agent_name

    payload = assemble_context(gs, messages, agent_name, previous_responses)

    _get_ledger(session_id).log_action(
        component="govern",
        action="assemble_context",
        detail={"agent_name": agent_name, "message_count": len(messages)},
        governance_mode=gs.mode,
        posture=gs.posture,
        role=gs.role,
        agent=agent_name,
    )
    return payload


# ---------------------------------------------------------------------------
# VAULT TOOLS
# ---------------------------------------------------------------------------

@mcp.tool()
def vault_load(name: str, content: str, category: str = "general", ctx: Context | None = None) -> dict:
    """
    Load a governance document into the active vault.
    Injected into every governed context via assemble_context().
    Returns: {"loaded": name, "vault_count": int}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)

    # Replace if name already exists
    gs.vault_documents = [d for d in gs.vault_documents if d.get("name") != name]
    gs.vault_documents.append({"name": name, "content": content, "category": category})
    _persist_state(gs)

    _get_ledger(session_id).log_action(
        component="vault",
        action="load",
        detail={"name": name, "category": category},
        governance_mode=gs.mode,
        posture=gs.posture,
        role=gs.role,
    )
    return {"loaded": name, "vault_count": len(gs.vault_documents)}


@mcp.tool()
def vault_list(ctx: Context | None = None) -> dict:
    """
    List all documents currently in the vault.
    Returns: {"documents": [{"name": str, "category": str}]}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)

    return {
        "documents": [
            {"name": d["name"], "category": d.get("category", "general")}
            for d in gs.vault_documents
        ]
    }


@mcp.tool()
def vault_clear(ctx: Context | None = None) -> dict:
    """
    Clear all documents from the vault.
    Returns: {"cleared": int}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)

    count = len(gs.vault_documents)
    gs.vault_documents = []
    _persist_state(gs)

    _get_ledger(session_id).log_action(
        component="vault",
        action="clear",
        detail={"cleared": count},
        governance_mode=gs.mode,
        posture=gs.posture,
        role=gs.role,
    )
    return {"cleared": count}


# ---------------------------------------------------------------------------
# AUDIT TOOLS
# ---------------------------------------------------------------------------

@mcp.tool()
def audit_log(
    component: str,
    action: str,
    detail: dict,
    agent: str = "",
    ctx: Context | None = None,
) -> dict:
    """
    Append a governed action to the audit ledger.
    Automatically captures active mode/posture/role from GovernanceState.
    Returns: {"id": int, "hash": str, "iso_time": str}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)

    return _get_ledger(session_id).log_action(
        component=component,
        action=action,
        detail=detail,
        governance_mode=gs.mode,
        posture=gs.posture,
        role=gs.role,
        agent=agent,
    )


@mcp.tool()
def audit_verify(ctx: Context | None = None) -> dict:
    """
    Verify the entire audit chain integrity.
    Returns: {"valid": bool, "entries_checked": int, "first_failure": int | None}
    """
    session_id = _resolve_session(ctx)
    return _get_ledger(session_id).verify_integrity()


@mcp.tool()
def audit_recent(n: int = 10, ctx: Context | None = None) -> dict:
    """
    Return the last N audit entries.
    Returns: {"entries": [...], "count": int}
    """
    session_id = _resolve_session(ctx)
    entries = _get_ledger(session_id).recent(n)
    return {"entries": entries, "count": len(entries)}


@mcp.tool()
def audit_hash_session(messages: list[dict], ctx: Context | None = None) -> dict:
    """
    Generate all three session hashes.
    ① Config fingerprint (governance state)
    ② Content integrity (conversation)
    ③ Onchain anchor (Solana memo format)
    Returns: {"hash_config": str, "hash_content": str, "hash_onchain": str}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)

    # vault_docs: list[str] (names only), systems: list[dict] (not in GovernanceState — pass empty)
    vault_doc_names = [d.get("name", "") for d in gs.vault_documents]
    hash_config = hash_governance_state(
        mode=gs.mode,
        posture=gs.posture,
        role=gs.role,
        vault_docs=vault_doc_names,
        systems=[],
    )
    hash_content = hash_conversation(messages)
    hash_onchain = format_for_onchain(hash_config, hash_content, session_id)

    return {
        "hash_config": hash_config,
        "hash_content": hash_content,
        "hash_onchain": hash_onchain,
    }


# ---------------------------------------------------------------------------
# v1.1 TOOLS — Commitment, Oracle, Swarm
# ---------------------------------------------------------------------------

@mcp.tool()
def govern_check_commitment(
    message: str,
    history: list[str] | None = None,
    block_threshold: float = 40.0,
    ctx: Context | None = None,
) -> dict:
    """
    Check semantic commitment drift between a message and conversation history.
    Based on the 2026 McHenry Conservation Law.
    Drift < 5% = green (preserved). Drift > threshold = blocked.
    Returns: {"drift_score": float, "drift_level": str, "commitment_preserved": bool,
              "reason": str, "conditions": [...], "scorer": str}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)

    result = evaluate_commitment(message, history=history, block_threshold=block_threshold)

    _get_ledger(session_id).log_action(
        component="commitment",
        action="check_commitment",
        detail={
            "drift_score": result["drift_score"],
            "drift_level": result["drift_level"],
            "commitment_preserved": result["commitment_preserved"],
        },
        governance_mode=gs.mode,
        posture=gs.posture,
        role=gs.role,
    )
    return result


@mcp.tool()
def govern_oracle_verify(
    message: str,
    context: str = "",
    ctx: Context | None = None,
) -> dict:
    """
    Send message to Grok Oracle for independent commitment verification.
    Falls back gracefully if XAI_GROK_API_KEY is not set.
    Returns: {"preserves_commitment": bool, "explanation": str, "source": str}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)

    result = grok_verify_sync(
        message=message,
        context=context or f"Governance mode: {gs.mode} | Posture: {gs.posture} | Role: {gs.role}",
    )

    _get_ledger(session_id).log_action(
        component="oracle",
        action="oracle_verify",
        detail={
            "preserves_commitment": result["preserves_commitment"],
            "source": result["source"],
        },
        governance_mode=gs.mode,
        posture=gs.posture,
        role=gs.role,
    )
    return result


@mcp.tool()
def govern_run_swarm_round(
    task: str,
    primary_output: str = "",
    secondary_output: str = "",
    history: list[str] | None = None,
    drift_block_threshold: float = 75.0,
    use_oracle: bool = False,
    ctx: Context | None = None,
) -> dict:
    """
    Run a full governance-enforced swarm round: Primary → Secondary → Observer.
    Enforces commitment conservation between steps.
    Grok Oracle final gate is optional (set use_oracle=True + XAI_GROK_API_KEY).

    Pass primary_output and secondary_output as pre-generated text (from your agents).
    The server enforces the constitutional checks — commitment scoring, governance
    pre-flight, oracle gate — and returns the full verdict.

    drift_block_threshold: float (default 75.0) — drift % above which Secondary vetoes.
    Tune down for stricter sessions (e.g. High Security: 30.0).

    Returns: {"approved": bool, "output": str, "drift_score": float,
              "commitment_preserved": bool, "oracle": dict, "blocked": bool,
              "block_reason": str | None, "steps": [...]}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)

    # Build role handlers from provided outputs (or placeholder stubs)
    def make_handler(output: str):
        def handler(role: str, input_text: str) -> str:
            if output:
                return output
            raise NotImplementedError(f"No output provided for {role}")
        return handler

    role_handlers = {
        "Primary": make_handler(primary_output),
        "Secondary": make_handler(secondary_output),
        "Observer": make_handler(""),  # Observer always uses placeholder — flags from full context
    }

    cfg = SwarmConfig(
        drift_block_threshold=drift_block_threshold,
        use_oracle=use_oracle,
    )

    result = run_swarm_round(
        task=task,
        governance=gs,
        role_handlers=role_handlers,
        history=history,
        config=cfg,
    )

    _get_ledger(session_id).log_action(
        component="swarm",
        action="swarm_round",
        detail={
            "task_len": len(task),
            "approved": result["approved"],
            "blocked": result["blocked"],
            "drift_score": result["drift_score"],
            "block_reason": result.get("block_reason"),
        },
        governance_mode=gs.mode,
        posture=gs.posture,
        role=gs.role,
    )
    return result


# ---------------------------------------------------------------------------
# v1.2 TOOLS — Meta-Governance / Constitutional Amendment Protocol
# ---------------------------------------------------------------------------

@mcp.tool()
def meta_analyze_trail(
    timeframe: str = "week",
    focus: list[str] | None = None,
    min_confidence: float = 0.8,
    exclude_tags: list[str] | None = None,
    ctx: Context | None = None,
) -> dict:
    """
    Analyze the audit trail and generate constitutional amendment proposals.
    The constitution reads its own history and proposes improvements.

    timeframe:     "day" | "week" | "month" | "all"
    focus:         ["modes", "postures", "roles"] — which dimensions to analyze
    min_confidence: 0.0–1.0 — minimum confidence to emit a proposal
    exclude_tags:  Session tags to exclude from analysis (e.g. ["test", "dev", "ci"]).
                   Entries logged with {"session_tag": "test"} in their detail dict
                   will be excluded, preventing acceptance-test traffic from generating
                   false amendment proposals. Always pass ["test"] for production analysis.

    Returns: {"proposals": [...], "entries_analyzed": int, "entries_excluded_by_tag": int,
              "analysis_summary": str}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)
    focus = focus or ["modes", "postures", "roles"]

    result = analyze_audit_trail(
        timeframe=timeframe,
        focus=focus,
        min_confidence=min_confidence,
        ledger_name=f"audit_{session_id}.jsonl",
        exclude_tags=exclude_tags or [],
    )

    _get_ledger(session_id).log_action(
        component="meta",
        action="analyze_trail",
        detail={
            "timeframe": timeframe,
            "entries_analyzed": result["entries_analyzed"],
            "entries_excluded_by_tag": result.get("entries_excluded_by_tag", 0),
            "exclude_tags": exclude_tags or [],
            "proposals_generated": len(result["proposals"]),
        },
        governance_mode=gs.mode,
        posture=gs.posture,
        role=gs.role,
    )
    return result


@mcp.tool()
def meta_list_proposals(status: str = "pending", ctx: Context | None = None) -> dict:
    """
    List constitutional amendment proposals by status.
    status: "pending" | "approved" | "rejected"

    Returns: {"proposals": [...], "count": int, "status": str}
    """
    return list_proposals(status)


@mcp.tool()
def meta_apply_amendment(
    proposal_id: str,
    operator_signature: str,
    ctx: Context | None = None,
) -> dict:
    """
    Apply a pending amendment to the constitution. Atomic write + cryptographic signing.
    Requires operator_signature (non-empty string). Bumps constitution version.
    Moves proposal from pending → approved. Appends to amendments.jsonl.

    Returns: {"success": bool, "new_version": str, "constitution_hash": str, "message": str}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)

    result = apply_amendment(proposal_id, operator_signature)

    _get_ledger(session_id).log_action(
        component="meta",
        action="apply_amendment",
        detail={
            "proposal_id": proposal_id,
            "success": result["success"],
            "new_version": result.get("new_version"),
        },
        governance_mode=gs.mode,
        posture=gs.posture,
        role=gs.role,
    )
    return result


@mcp.tool()
def meta_reject_proposal(
    proposal_id: str,
    reason: str,
    ctx: Context | None = None,
) -> dict:
    """
    Reject a pending amendment proposal with a reason.
    Moves proposal from pending → rejected.

    Returns: {"success": bool, "message": str}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)

    result = reject_proposal(proposal_id, reason)

    _get_ledger(session_id).log_action(
        component="meta",
        action="reject_proposal",
        detail={"proposal_id": proposal_id, "reason": reason, "success": result["success"]},
        governance_mode=gs.mode,
        posture=gs.posture,
        role=gs.role,
    )
    return result


@mcp.tool()
def meta_constitution_status(ctx: Context | None = None) -> dict:
    """
    Return full meta-governance status: constitution version, signature,
    amendment count, proposal counts, and core principles status.

    Returns: {"constitution_version": str, "constitution_signature": str,
              "amendment_count": int, "proposals": {...}, "core_principles_count": int}
    """
    return constitution_status()


@mcp.tool()
def meta_rollback_amendment(
    amendment_id: str,
    operator_signature: str,
    reason: str,
    ctx: Context | None = None,
) -> dict:
    """
    Emergency operator tool: reverse an applied amendment.

    Records a rollback entry in amendments.jsonl, moves the approved proposal
    to rejected/, and returns a warning reminding the operator to verify that
    constitution.json content was manually restored to the correct prior state.

    IMPORTANT: This tool does NOT automatically rewrite constitution.json content.
    The operator must edit constitution.json directly and re-sign it if the
    amendment modified the document body. Use meta_constitution_status() to
    confirm state after rollback.

    Args:
        amendment_id: ID of the amendment to roll back (from amendments.jsonl)
        operator_signature: Authorization string (non-empty required)
        reason: Human-readable reason for the rollback

    Returns: {"success": bool, "message": str, "warning": str}
    """
    session_id = _resolve_session(ctx)
    gs = _get_session(session_id)

    result = rollback_amendment(amendment_id, operator_signature, reason)

    _get_ledger(session_id).log_action(
        component="meta",
        action="rollback_amendment",
        detail={
            "amendment_id": amendment_id,
            "reason": reason,
            "success": result.get("success"),
        },
        governance_mode=gs.mode,
        posture=gs.posture,
        role=gs.role,
    )
    return result


# ---------------------------------------------------------------------------
# Operator Signature Helper
# ---------------------------------------------------------------------------

@mcp.tool()
def meta_generate_sig(
    operator_id: str,
    proposal_id: str,
    ctx: Context | None = None,
) -> dict:
    """
    Generate a valid HMAC-SHA256 operator signature for use with meta_apply_amendment
    or meta_rollback_amendment.

    Requires MOSES_OPERATOR_SECRET to be set in the server environment.
    The generated signature is scoped to the specific proposal_id — it cannot
    be reused for a different proposal.

    Args:
        operator_id: Your operator identifier (e.g. "luthen")
        proposal_id: The exact proposal ID you intend to approve or roll back

    Returns:
        {"signature": str, "operator_id": str, "proposal_id": str, "secret_configured": bool}
        On error: {"error": str, "secret_configured": bool}
    """
    secret_configured = _get_operator_secret() is not None
    try:
        sig = make_operator_sig(operator_id, proposal_id)
        return {
            "signature": sig,
            "operator_id": operator_id,
            "proposal_id": proposal_id,
            "secret_configured": secret_configured,
            "usage": f"Pass this signature as operator_signature to meta_apply_amendment or meta_rollback_amendment",
        }
    except EnvironmentError as e:
        return {
            "error": str(e),
            "secret_configured": False,
            "action_required": (
                "Set MOSES_OPERATOR_SECRET in your environment before starting the server. "
                "Example: export MOSES_OPERATOR_SECRET=<your-random-secret>"
            ),
        }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()  # stdio transport — for Claude Code local dev
