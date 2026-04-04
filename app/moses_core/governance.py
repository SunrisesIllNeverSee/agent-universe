from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


MODES = {
    "High Security": {
        "constraints": [
            "Verify all claims before stating them as fact",
            "Flag any data exposure or privacy risks immediately",
            "Require explicit operator confirmation before destructive actions",
            "Require explicit operator confirmation before any outbound transfer",
            "Log full reasoning chain for audit",
            "Do not access external resources without operator approval",
        ],
        "prohibited": [
            "Speculative responses without supporting evidence",
            "Executing transactions without confirmation",
            "Accessing or transmitting sensitive data without explicit approval",
        ],
        "priority": "security_first",
    },
    "High Integrity": {
        "constraints": [
            "Maintain accuracy above all other considerations",
            "Cite sources for every factual claim",
            "Explicitly flag uncertainty and confidence levels",
            "Distinguish between established fact, inference, and speculation",
            "Cross-reference claims against multiple sources when possible",
        ],
        "prohibited": [
            "Presenting inference as established fact",
            "Omitting relevant counter-evidence",
        ],
        "priority": "accuracy_first",
    },
    "Creative": {
        "constraints": [
            "Explore freely and flag speculative leaps",
            "Log reasoning so creative moves remain traceable",
            "Separate factual analysis from ideation",
        ],
        "prohibited": [
            "Presenting creative speculation as verified fact",
        ],
        "priority": "exploration_first",
    },
    "Research": {
        "constraints": [
            "Document methodology before concluding",
            "Track provenance of every material data point",
            "Flag gaps in available evidence",
        ],
        "prohibited": [
            "Drawing conclusions without documented methodology",
        ],
        "priority": "depth_first",
    },
    "Problem Solving": {
        "constraints": [
            "Decompose the problem before solutioning",
            "State assumptions explicitly",
            "Consider edge cases and fallback paths",
        ],
        "prohibited": [
            "Declaring a problem solved without verification",
        ],
        "priority": "systematic_first",
    },
    "I Don't Know What To Do": {
        "constraints": [
            "Start with clarifying questions",
            "Offer tradeoffs instead of pretending certainty",
            "Escalate ambiguity for human judgment",
        ],
        "prohibited": [
            "Taking autonomous action in ambiguous situations",
        ],
        "priority": "guided_discovery",
    },
    "None (Unrestricted)": {
        "constraints": [
            "No behavioral constraints applied",
            "All actions remain audited",
        ],
        "prohibited": [],
        "priority": "unrestricted",
    },
}

MODE_ALIASES = {
    "high-security": "High Security",
    "high_security": "High Security",
    "high-integrity": "High Integrity",
    "high_integrity": "High Integrity",
    "creative": "Creative",
    "research": "Research",
    "problem-solving": "Problem Solving",
    "problem_solving": "Problem Solving",
    "idk": "I Don't Know What To Do",
    "none": "None (Unrestricted)",
    "unrestricted": "None (Unrestricted)",
}

POSTURES = {
    "SCOUT": {
        "behavior": "Information gathering only",
        "transaction_policy": "NO transactions, NO state changes",
        "constraints": [
            "Read-only operations exclusively",
            "Gather and report without executing",
        ],
    },
    "DEFENSE": {
        "behavior": "Protect existing positions",
        "transaction_policy": "Outbound transfers require explicit confirmation",
        "constraints": [
            "Prioritize preservation",
            "Require confirmation on outbound actions",
        ],
    },
    "OFFENSE": {
        "behavior": "Execute within governance constraints",
        "transaction_policy": "Permitted within active governance limits",
        "constraints": [
            "Execute only after governance checks pass",
            "Log rationale for every operational action",
        ],
    },
}

ROLES = {
    "Primary": {
        "authority": "Initiates analysis and direction",
        "instruction": "Respond first and frame the work. Do not wait for downstream systems.",
        "constraints": ["Leads sequence ordering"],
    },
    "Secondary": {
        "authority": "Validates, challenges, and extends",
        "instruction": "Build on or challenge the Primary response. Add value rather than repeating it.",
        "constraints": ["Must consider prior responses before acting"],
    },
    "Observer": {
        "authority": "Flags risks and gaps",
        "instruction": "Identify inconsistencies, blind spots, and governance risks. Do not initiate original execution.",
        "constraints": ["Oversight role only"],
    },
}


@dataclass
class GovernanceStateData:
    mode: str = "None (Unrestricted)"
    posture: str = "SCOUT"
    role: str = "Primary"
    reasoning_mode: str = "Deductive"
    reasoning_depth: str = "MODERATE"
    response_style: str = "Direct"
    output_format: str = "Conversational"
    narrative_strength: float = 0.5
    expertise_level: str = "Expert"
    interaction_mode: str = "Executing"
    domain: str = "General"
    communication_pref: str = "Concise"
    goal: str = "Tactical Execution"
    vault_documents: list[dict] = field(default_factory=list)


def resolve_mode(mode_input: str) -> str:
    key = mode_input.strip().lower()
    return MODE_ALIASES.get(key, mode_input)


def translate_mode(mode: str) -> dict:
    return MODES.get(resolve_mode(mode), MODES["None (Unrestricted)"])


def translate_posture(posture: str) -> dict:
    return POSTURES.get(posture.strip().upper(), POSTURES["SCOUT"])


def get_role_instruction(role: str) -> dict:
    return ROLES.get(role.title(), ROLES["Primary"])


def assemble_context(
    governance: GovernanceStateData,
    messages: list[dict],
    agent_name: str = "agent",
    previous_responses: Optional[list[dict]] = None,
) -> dict:
    mode_config = translate_mode(governance.mode)
    posture_config = translate_posture(governance.posture)
    role_config = get_role_instruction(governance.role)

    payload = {
        "agent": agent_name,
        "constitutional_governance": {
            "mode": governance.mode,
            "mode_constraints": mode_config["constraints"],
            "mode_prohibited": mode_config.get("prohibited", []),
            "mode_priority": mode_config.get("priority", "unrestricted"),
            "posture": governance.posture,
            "posture_behavior": posture_config["behavior"],
            "posture_transaction_policy": posture_config["transaction_policy"],
            "posture_constraints": posture_config["constraints"],
            "reasoning_mode": governance.reasoning_mode,
            "reasoning_depth": governance.reasoning_depth,
            "response_style": governance.response_style,
            "output_format": governance.output_format,
            "narrative_strength": governance.narrative_strength,
        },
        "role_assignment": {
            "role": governance.role,
            "authority": role_config["authority"],
            "instruction": role_config["instruction"],
            "constraints": role_config["constraints"],
        },
        "user_profile": {
            "expertise": governance.expertise_level,
            "interaction_mode": governance.interaction_mode,
            "domain": governance.domain,
            "communication_pref": governance.communication_pref,
            "goal": governance.goal,
        },
        "vault_context": list(governance.vault_documents),
        "messages": messages,
    }
    if governance.role in {"Secondary", "Observer"} and previous_responses:
        payload["prior_responses"] = previous_responses
    return payload


_CONCEPT_SIGNALS = {
    "transaction": ["transfer", "send", "swap", "trade", "pay", "wire"],
    "execution": ["execute", "deploy", "run", "launch", "trigger", "invoke"],
    "destructive": ["delete", "remove", "destroy", "wipe", "purge", "truncate"],
    "outbound": ["upload", "post", "publish", "push", "export", "transmit"],
    "external_access": ["external", "api", "url", "fetch", "http", "connect"],
    "sensitive_data": ["password", "key", "secret", "credential", "token", "private"],
    "speculation": ["assume", "probably", "guess", "perhaps", "maybe", "likely"],
    "state_change": ["write", "edit", "modify", "update", "create", "patch"],
}


def _action_concepts(action: str) -> set[str]:
    """Detect governance-relevant concepts using word-boundary matching.

    Uses \\b (word boundary) to avoid false positives like
    'display' triggering 'pay' or 'keyboard' triggering 'key'.
    """
    lowered = action.lower()
    return {
        concept
        for concept, signals in _CONCEPT_SIGNALS.items()
        if any(re.search(rf"\b{re.escape(signal)}\b", lowered) for signal in signals)
    }


# ── Action risk levels ─────────────────────────────────────────────────────
# "standard" actions are marketplace operations governed by the tier/fee system.
#   → Always permitted regardless of posture (ungoverned agents pay higher fees).
# "high" actions are treasury/chain ops that need posture-level governance.
#   → Subject to SCOUT/DEFENSE/OFFENSE posture checks.
# Unlisted actions default to posture-checked (safe default).
ACTION_RISK: dict[str, str] = {
    "process payment": "standard",
    "fill slot": "standard",
    "create bounty": "standard",
    "close task": "standard",
    "purchase blackcard": "standard",
    "mission payout": "standard",
    # High-risk: chain transfers, treasury ops, operator actions
    "manual credit": "high",
    "chain transfer": "high",
    "treasury withdrawal": "high",
}


def check_action_permitted(action_description: str, governance: GovernanceStateData) -> dict:
    mode_config = translate_mode(governance.mode)
    concepts = _action_concepts(action_description)
    conditions: list[str] = []
    triggered_rules: list[str] = []

    # Standard-risk marketplace actions bypass posture checks —
    # the tier fee system provides economic governance instead.
    risk = ACTION_RISK.get(action_description, "high")
    if risk == "standard":
        return {
            "permitted": True,
            "reason": f"Marketplace action permitted (tier-governed) under {governance.mode}",
            "triggered_rules": [],
            "conditions": [],
        }

    if governance.posture == "SCOUT":
        # Explicitly high-risk actions are always blocked in SCOUT
        if risk == "high":
            return {
                "permitted": False,
                "reason": "SCOUT posture prohibits high-risk operations",
                "triggered_rules": [f"SCOUT read-only block: {action_description} (classified high-risk)"],
                "conditions": ["Switch posture to DEFENSE or OFFENSE for execution"],
            }
        state_changing = concepts & {"transaction", "execution", "destructive", "outbound", "state_change"}
        if state_changing:
            return {
                "permitted": False,
                "reason": "SCOUT posture prohibits state-changing operations",
                "triggered_rules": [f"SCOUT read-only block: {', '.join(sorted(state_changing))}"],
                "conditions": ["Switch posture to DEFENSE or OFFENSE for execution"],
            }

    if governance.posture == "DEFENSE" and concepts & {"transaction", "outbound"}:
        conditions.append("Explicit operator confirmation required in DEFENSE posture")

    for rule in mode_config.get("prohibited", []):
        lowered = rule.lower()
        if ("speculative" in lowered and "speculation" in concepts) or (
            "sensitive" in lowered and "sensitive_data" in concepts
        ) or ("transaction" in lowered and "transaction" in concepts):
            triggered_rules.append(rule)

    if triggered_rules:
        return {
            "permitted": False,
            "reason": f"Action violates {governance.mode} mode prohibition",
            "triggered_rules": triggered_rules,
            "conditions": [f"Comply with prohibition: {rule}" for rule in triggered_rules],
        }

    for constraint in mode_config.get("constraints", []):
        lowered = constraint.lower()
        if "confirmation" in lowered and concepts & {"transaction", "destructive", "outbound"}:
            conditions.append(constraint)

    return {
        "permitted": True,
        "reason": f"Action permitted under {governance.mode} + {governance.posture}",
        "triggered_rules": [],
        "conditions": conditions,
    }
