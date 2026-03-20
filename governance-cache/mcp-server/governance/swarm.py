"""
MO§ES™ Agent Swarm Coordinator — swarm.py
© 2026 Ello Cello LLC — Patent pending: Serial No. 63/877,177

Implements Grok's AgentSwarm concept from MCP-FROM-REVIEWS.md, translated to
the FastMCP architecture.

Original concept: standalone AgentSwarm class with direct model API calls.
FastMCP translation: swarm logic becomes a governed MCP tool. Each role
(Primary / Secondary / Observer) maps to a separate GovernanceState with its
own session. Agent invocation is pluggable — caller provides role_handlers.

Design:
- SwarmRound encapsulates one full Primary → Secondary → Observer pass.
- Commitment conservation check runs between Primary and Secondary.
- Observer gets full prior context and flags only.
- Grok Oracle is the final gate (optional — skipped if no key).
- Each step is audit-logged.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Optional

from governance.engine import GovernanceState, check_action_permitted
from governance.commitment import evaluate_commitment
from governance.oracle import grok_verify_sync


# ---------------------------------------------------------------------------
# SwarmRound — one full governance-enforced agent round
# ---------------------------------------------------------------------------

@dataclass
class SwarmConfig:
    """Configuration for a swarm round."""
    # Drift threshold for Primary → Secondary conservation check
    drift_block_threshold: float = 40.0
    # Minimum FMS moat tier to pass final gate (placeholder — v2.0)
    min_moat_tier: int = 3
    # Whether to run Grok Oracle final gate
    use_oracle: bool = True
    # Genesis hash for this swarm session
    genesis_hash: str = field(default_factory=lambda: "MOSES-GENESIS-" + os.urandom(16).hex())


def run_swarm_round(
    task: str,
    governance: GovernanceState,
    role_handlers: dict[str, Callable[[str, str], str]],
    history: list[str] | None = None,
    config: Optional[SwarmConfig] = None,
) -> dict:
    """
    Run one full governance-enforced swarm round: Primary → Secondary → Observer.

    Args:
        task:           The task or query for the swarm.
        governance:     Active GovernanceState (mode/posture/role).
        role_handlers:  Dict mapping role names to callables: handler(role, input) → str.
                        Keys: "Primary", "Secondary", "Observer".
                        In production: each handler calls the appropriate model/agent API.
                        For testing: pass lambda functions returning mock outputs.
        history:        Prior conversation strings for commitment scoring.
        config:         SwarmConfig (defaults used if None).

    Returns:
        {
            "approved": bool,
            "output": str | None,           # Final approved output (Secondary's response)
            "primary_output": str,
            "secondary_output": str | None,
            "observer_report": str | None,
            "drift_score": float,
            "commitment_preserved": bool,
            "oracle": dict,
            "blocked": bool,
            "block_reason": str | None,
            "steps": list[dict],            # Per-step audit trail
        }
    """
    cfg = config or SwarmConfig()
    steps: list[dict] = []

    # ── Step 1: Pre-flight governance check ──────────────────────
    pre_check = check_action_permitted(task, governance)
    steps.append({"step": "pre_flight", "result": pre_check})

    if not pre_check["permitted"]:
        return {
            "approved": False,
            "output": None,
            "primary_output": "",
            "secondary_output": None,
            "observer_report": None,
            "drift_score": 0.0,
            "commitment_preserved": False,
            "oracle": {"preserves_commitment": False, "explanation": "Blocked at pre-flight"},
            "blocked": True,
            "block_reason": f"Pre-flight governance check: {pre_check['reason']}",
            "steps": steps,
        }

    # ── Step 2: Primary leads ─────────────────────────────────────
    primary_handler = role_handlers.get("Primary")
    if not primary_handler:
        return _blocked("No Primary handler provided", steps)

    try:
        primary_output = primary_handler("Primary", task)
    except NotImplementedError:
        primary_output = f"[Primary handler not implemented — placeholder for: {task}]"
    except Exception as exc:
        return _blocked(f"Primary handler error: {exc}", steps)

    steps.append({"step": "primary", "output_len": len(primary_output)})

    # ── Step 3: Commitment conservation check (Primary → Secondary) ─
    commit_eval = evaluate_commitment(
        primary_output,
        history=history,
        block_threshold=cfg.drift_block_threshold,
    )
    steps.append({"step": "commitment_check", "result": commit_eval})

    if not commit_eval["commitment_preserved"]:
        return {
            "approved": False,
            "output": None,
            "primary_output": primary_output,
            "secondary_output": None,
            "observer_report": None,
            "drift_score": commit_eval["drift_score"],
            "commitment_preserved": False,
            "oracle": {"preserves_commitment": False, "explanation": "Blocked at commitment check"},
            "blocked": True,
            "block_reason": (
                f"COMMITMENT DRIFT {commit_eval['drift_score']:.1f}% — "
                f"Secondary vetoed (threshold: {cfg.drift_block_threshold}%)"
            ),
            "steps": steps,
        }

    # ── Step 4: Secondary validates ──────────────────────────────
    secondary_handler = role_handlers.get("Secondary")
    try:
        secondary_input = f"[Primary said:]\n{primary_output}\n\n[Task:]\n{task}"
        secondary_output = (
            secondary_handler("Secondary", secondary_input)
            if secondary_handler
            else f"[Secondary not provided — accepting Primary output]"
        )
    except NotImplementedError:
        secondary_output = f"[Secondary handler not implemented]"
    except Exception as exc:
        return _blocked(f"Secondary handler error: {exc}", steps)

    steps.append({"step": "secondary", "output_len": len(secondary_output)})

    # ── Step 5: Observer flags only ───────────────────────────────
    observer_handler = role_handlers.get("Observer")
    observer_report = ""
    try:
        observer_input = (
            f"[Primary:]\n{primary_output}\n\n"
            f"[Secondary:]\n{secondary_output}\n\n"
            f"[Task:]\n{task}"
        )
        observer_report = (
            observer_handler("Observer", observer_input)
            if observer_handler
            else "[Observer not provided]"
        )
    except NotImplementedError:
        observer_report = "[Observer handler not implemented]"
    except Exception as exc:
        observer_report = f"[Observer error: {exc}]"

    steps.append({"step": "observer", "report_len": len(observer_report)})

    # ── Step 6: Grok Oracle final gate ────────────────────────────
    oracle_result = {"preserves_commitment": True, "explanation": "Oracle skipped", "source": "skipped"}
    if cfg.use_oracle:
        oracle_result = grok_verify_sync(
            message=secondary_output,
            context=f"Governance mode: {governance.mode} | Posture: {governance.posture} | Task: {task}",
        )
    steps.append({"step": "oracle", "result": oracle_result})

    if not oracle_result["preserves_commitment"]:
        return {
            "approved": False,
            "output": None,
            "primary_output": primary_output,
            "secondary_output": secondary_output,
            "observer_report": observer_report,
            "drift_score": commit_eval["drift_score"],
            "commitment_preserved": True,
            "oracle": oracle_result,
            "blocked": True,
            "block_reason": f"Grok Oracle rejected: {oracle_result['explanation']}",
            "steps": steps,
        }

    # ── Approved ──────────────────────────────────────────────────
    return {
        "approved": True,
        "output": secondary_output,
        "primary_output": primary_output,
        "secondary_output": secondary_output,
        "observer_report": observer_report,
        "drift_score": commit_eval["drift_score"],
        "commitment_preserved": True,
        "oracle": oracle_result,
        "blocked": False,
        "block_reason": None,
        "steps": steps,
    }


def _blocked(reason: str, steps: list) -> dict:
    return {
        "approved": False,
        "output": None,
        "primary_output": "",
        "secondary_output": None,
        "observer_report": None,
        "drift_score": 0.0,
        "commitment_preserved": False,
        "oracle": {"preserves_commitment": False, "explanation": reason},
        "blocked": True,
        "block_reason": reason,
        "steps": steps,
    }
