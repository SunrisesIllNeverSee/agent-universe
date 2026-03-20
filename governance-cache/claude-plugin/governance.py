"""MO§E§™ Governance Engine — Mode translation + context assembly.

Translates governance modes into behavioral constraints,
assembles governed context for agent operations.

© 2026 Ello Cello LLC. All rights reserved.
Patent Pending: Serial No. 63/877,177
"""

from dataclasses import dataclass, field
from typing import Optional


# ── Governance Modes ──────────────────────────────────────────

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
            "Explore freely — speculative and divergent thinking encouraged",
            "Log reasoning so creative leaps are traceable",
            "Flag when shifting from grounded analysis to creative exploration",
            "Pursue unexpected connections across domains",
        ],
        "prohibited": [
            "Presenting creative speculation as factual analysis without flagging it",
        ],
        "priority": "exploration_first",
    },
    "Research": {
        "constraints": [
            "Document methodology before executing investigation",
            "Follow threads deeply — do not surface-skim",
            "Track provenance of every data point",
            "Maintain bibliography of sources consulted",
            "Flag gaps in available evidence",
        ],
        "prohibited": [
            "Drawing conclusions without documented methodology",
            "Abandoning investigation threads without explanation",
        ],
        "priority": "depth_first",
    },
    "Self Growth": {
        "constraints": [
            "Reflect on prior interactions and build on learned patterns",
            "Track what's working and what isn't",
            "Identify capability gaps and suggest development paths",
            "Maintain growth log of insights and improvements",
        ],
        "prohibited": [
            "Repeating previously identified mistakes without acknowledgment",
        ],
        "priority": "learning_first",
    },
    "Problem Solving": {
        "constraints": [
            "Decompose problem before attempting solution",
            "Verify solution against original problem statement",
            "Consider edge cases and failure modes",
            "Document assumptions explicitly",
            "Provide fallback approaches if primary solution fails",
        ],
        "prohibited": [
            "Jumping to solution without problem decomposition",
            "Declaring solved without verification",
        ],
        "priority": "systematic_first",
    },
    "I Don't Know What To Do": {
        "constraints": [
            "Begin with clarifying questions — do not assume intent",
            "Propose 2-3 possible next steps with tradeoffs",
            "Guide the operator toward a decision, don't make it for them",
            "Flag when the situation needs human judgment",
        ],
        "prohibited": [
            "Taking autonomous action in ambiguous situations",
            "Pretending to understand when clarification is needed",
        ],
        "priority": "guided_discovery",
    },
    "None (Unrestricted)": {
        "constraints": [
            "No behavioral constraints applied",
            "All actions still audited and logged",
            "Operator accepts full responsibility for outcomes",
        ],
        "prohibited": [],
        "priority": "unrestricted",
    },
}


# ── Postures ──────────────────────────────────────────────────

POSTURES = {
    "SCOUT": {
        "behavior": "Information gathering only",
        "transaction_policy": "NO transactions, NO state changes",
        "constraints": [
            "Read-only operations exclusively",
            "Gather, analyze, and report — do not act",
            "Flag opportunities for operator review",
        ],
    },
    "DEFENSE": {
        "behavior": "Protect existing positions",
        "transaction_policy": "Outbound transfers require explicit confirmation",
        "constraints": [
            "Prioritize capital preservation",
            "Flag any action that reduces holdings",
            "Require double confirmation for transfers exceeding 10% of position",
            "Monitor for threats to existing positions",
        ],
    },
    "OFFENSE": {
        "behavior": "Execute on opportunities",
        "transaction_policy": "Permitted within governance constraints",
        "constraints": [
            "Execute opportunities that pass governance checks",
            "Still bound by governance mode constraints",
            "Log all execution decisions with rationale",
            "Track performance of executed actions",
        ],
    },
}


# ── Roles ─────────────────────────────────────────────────────

ROLES = {
    "Primary": {
        "authority": "Initiates analysis, sets direction",
        "instruction": (
            "You are the Primary system. Respond first. Set the analytical "
            "direction. Other systems will build on your response. Do not "
            "wait for input from Secondary or Observer."
        ),
        "constraints": [
            "Must complete analysis before Secondary responds",
            "Responsible for initial framing of the problem",
        ],
    },
    "Secondary": {
        "authority": "Validates, challenges, extends",
        "instruction": (
            "You are Secondary. The Primary system has already responded. "
            "Build on, challenge, or extend their analysis. Do NOT repeat "
            "what Primary said. Add new value or identify what they missed."
        ),
        "constraints": [
            "Must read Primary's response before generating own",
            "Cannot repeat Primary's analysis",
            "Must explicitly state how response differs from or extends Primary",
        ],
    },
    "Observer": {
        "authority": "Flags risks and gaps",
        "instruction": (
            "You are Observer. Read all responses from Primary and Secondary. "
            "Flag inconsistencies, gaps, or risks. Do NOT generate original "
            "analysis. Do NOT initiate actions. Your role is oversight."
        ),
        "constraints": [
            "Cannot initiate actions or generate original analysis",
            "Can only flag issues in existing responses",
            "Must reference specific claims when flagging concerns",
        ],
    },
}


# ── Context Assembly ──────────────────────────────────────────

@dataclass
class GovernanceState:
    """Current governance configuration set by operator."""
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
    vault_documents: list = field(default_factory=list)


def translate_mode(mode: str) -> dict:
    """Translate a governance mode name into behavioral constraints."""
    return MODES.get(mode, MODES["None (Unrestricted)"])


def translate_posture(posture: str) -> dict:
    """Translate a posture name into behavioral parameters."""
    return POSTURES.get(posture, POSTURES["SCOUT"])


def get_role_instruction(role: str) -> dict:
    """Get role behavior specification."""
    return ROLES.get(role, ROLES["Primary"])


def assemble_context(
    governance: GovernanceState,
    messages: list[dict],
    agent_name: str = "agent",
    previous_responses: Optional[list[dict]] = None,
) -> dict:
    """
    Build the full governed payload that an agent receives.
    
    This is the core IP. This function is why MO§E§™ exists.
    Every agent read passes through here.
    """
    mode_config = translate_mode(governance.mode)
    posture_config = translate_posture(governance.posture)
    role_config = get_role_instruction(governance.role)

    context = {
        "constitutional_governance": {
            "mode": governance.mode,
            "mode_constraints": mode_config["constraints"],
            "mode_prohibited": mode_config.get("prohibited", []),
            "mode_priority": mode_config.get("priority", "none"),
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
        "vault_context": [
            {"name": doc.get("name", ""), "category": doc.get("category", ""),
             "content": doc.get("content", "")}
            for doc in governance.vault_documents
        ],
        "messages": messages,
    }

    # If Secondary or Observer, include previous responses
    if governance.role in ("Secondary", "Observer") and previous_responses:
        context["prior_responses"] = previous_responses

    return context


def check_action_permitted(
    action_description: str,
    governance: GovernanceState,
) -> dict:
    """
    Check if a proposed action is permitted under current governance.
    
    Returns: {"permitted": bool, "reason": str, "conditions": list}
    """
    mode_config = translate_mode(governance.mode)
    posture_config = translate_posture(governance.posture)

    # Check posture transaction policy
    if governance.posture == "SCOUT":
        if any(word in action_description.lower()
               for word in ["transfer", "send", "swap", "trade", "execute", "deploy",
                            "approve", "sign", "submit"]):
            return {
                "permitted": False,
                "reason": "SCOUT posture prohibits state-changing operations",
                "conditions": ["Switch to DEFENSE or OFFENSE posture to enable execution"],
            }

    # Check mode prohibitions
    for prohibition in mode_config.get("prohibited", []):
        # This is a simplified check — real implementation would use
        # semantic matching against the action description
        pass

    # Check DEFENSE confirmation requirements
    conditions = []
    if governance.posture == "DEFENSE":
        if any(word in action_description.lower()
               for word in ["transfer", "send", "withdraw"]):
            conditions.append("Explicit operator confirmation required (DEFENSE posture)")

    if governance.mode == "High Security":
        if any(word in action_description.lower()
               for word in ["transfer", "deploy", "delete", "approve"]):
            conditions.append("Explicit operator confirmation required (High Security mode)")

    return {
        "permitted": True,
        "reason": f"Action permitted under {governance.mode} + {governance.posture}",
        "conditions": conditions,
    }
