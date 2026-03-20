"""MO§ES™ Governance Engine — Mode translation + context assembly.

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


# ── Mode Aliases (shorthand → canonical) ──────────────────────

MODE_ALIASES = {
    "high-security": "High Security",
    "high_security": "High Security",
    "high-integrity": "High Integrity",
    "high_integrity": "High Integrity",
    "creative": "Creative",
    "research": "Research",
    "self-growth": "Self Growth",
    "self_growth": "Self Growth",
    "problem-solving": "Problem Solving",
    "problem_solving": "Problem Solving",
    "idk": "I Don't Know What To Do",
    "i-dont-know": "I Don't Know What To Do",
    "unrestricted": "None (Unrestricted)",
    "none": "None (Unrestricted)",
}


def resolve_mode(mode_input: str) -> str:
    """Resolve a mode alias or shorthand to its canonical name."""
    key = mode_input.strip().lower()
    return MODE_ALIASES.get(key, mode_input)


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
    return MODES.get(resolve_mode(mode), MODES["None (Unrestricted)"])


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
    
    This is the core IP. This function is why MO§ES™ exists.
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


# ── Concept Keyword Map ────────────────────────────────────────
# Maps semantic concepts (derived from prohibited rule language)
# to signal words that indicate the concept is present in an action.

_CONCEPT_SIGNALS: dict[str, list[str]] = {
    "transaction": [
        "transfer", "send", "swap", "trade", "pay", "wire", "transact",
        "remit", "remittance", "liquidate", "disburse", "settle", "payout",
        "move funds", "execute payment", "initiate transfer",
    ],
    "execution": [
        "execute", "deploy", "run", "launch", "trigger", "call", "invoke",
        "propagate", "spin up", "kick off", "fire", "dispatch",
    ],
    "destructive": [
        "delete", "remove", "drop", "destroy", "wipe", "purge", "rm -",
        "truncate", "erase", "overwrite", "nuke", "teardown", "shutdown",
    ],
    "approval": [
        "approve", "sign", "authorize", "accept", "confirm", "ratify",
        "green-light", "sign off", "rubber stamp",
    ],
    "outbound": [
        "upload", "post", "publish", "submit", "push", "export", "send",
        "broadcast", "relay", "forward", "transmit", "dispatch",
    ],
    "external_access": [
        "external", "api", "url", "fetch", "request", "http", "access",
        "curl", "wget", "connect", "ping", "ssh", "endpoint", "webhook",
    ],
    "sensitive_data": [
        "password", "key", "secret", "credential", "token", "private", "seed",
        "mnemonic", "passphrase", "api key", "auth token", "bearer",
    ],
    "speculation": [
        "assume", "probably", "guess", "might be", "i think", "perhaps",
        "maybe", "likely", "suppose", "speculate", "predict",
    ],
    "inference_as_fact": [
        "definitely", "certainly", "guaranteed", "always", "never", "obviously",
        "it goes without saying", "clearly", "undoubtedly", "without question",
    ],
    "state_change": [
        "write", "edit", "modify", "update", "create", "overwrite", "save",
        "patch", "mutate", "alter", "revise", "amend",
    ],
    "autonomous": [
        "automatically", "without asking", "skip confirmation", "just do it",
        "no need to confirm", "proceed without", "bypass", "override",
    ],
}


def _action_concepts(action: str) -> set[str]:
    """Extract semantic concepts present in an action description."""
    action_lower = action.lower()
    return {
        concept
        for concept, signals in _CONCEPT_SIGNALS.items()
        if any(sig in action_lower for sig in signals)
    }


def _rule_triggered(rule: str, concepts: set[str]) -> bool:
    """
    Check whether a prohibited rule is triggered by the action's concepts.
    Maps rule language to concepts — no hardcoded per-mode logic.
    """
    rule_lower = rule.lower()
    trigger_map = {
        "transaction":       ["transaction", "transfer", "swap", "trade"],
        "execution":         ["execut", "deploy", "run"],
        "destructive":       ["destructive", "delete", "irreversible", "remov"],
        "approval":          ["approv", "sign", "authoriz"],
        "outbound":          ["outbound", "transfer", "transmit", "send"],
        "external_access":   ["external", "resource", "api", "access"],
        "sensitive_data":    ["sensitive", "data", "privacy", "exposure", "private"],
        "speculation":       ["speculative", "speculation", "without evidence", "unverified"],
        "inference_as_fact": ["inference", "as fact", "established fact", "presenting"],
        "state_change":      ["state change", "modif", "writ"],
        "autonomous":        ["autonomous", "without", "confirmation", "explicit"],
    }
    for concept, rule_signals in trigger_map.items():
        if concept in concepts and any(sig in rule_lower for sig in rule_signals):
            return True
    return False


def check_action_permitted(
    action_description: str,
    governance: GovernanceState,
) -> dict:
    """
    Check if a proposed action is permitted under current governance.

    Evaluates action against:
    1. Posture transaction policy (structural — SCOUT/DEFENSE/OFFENSE)
    2. Mode prohibited rules (derived from active mode config)
    3. Mode constraint conditions (confirmation requirements)

    Returns: {"permitted": bool, "reason": str, "conditions": list, "triggered_rules": list}
    """
    mode_config = translate_mode(governance.mode)
    concepts = _action_concepts(action_description)
    conditions: list[str] = []
    triggered_rules: list[str] = []

    # ── 1. Posture check (structural) ─────────────────────────
    if governance.posture == "SCOUT":
        state_changing = concepts & {"transaction", "execution", "destructive",
                                     "approval", "outbound", "state_change"}
        if state_changing:
            return {
                "permitted": False,
                "reason": "SCOUT posture prohibits state-changing operations",
                "triggered_rules": [f"SCOUT: read-only — detected: {', '.join(state_changing)}"],
                "conditions": ["Switch to DEFENSE or OFFENSE posture to enable execution"],
            }

    if governance.posture == "DEFENSE":
        if concepts & {"transaction", "outbound"}:
            conditions.append(
                "Explicit operator confirmation required (DEFENSE posture — outbound detected)"
            )

    # ── 2. Mode prohibited rules (rule-driven) ────────────────
    for rule in mode_config.get("prohibited", []):
        if _rule_triggered(rule, concepts):
            triggered_rules.append(rule)

    if triggered_rules:
        return {
            "permitted": False,
            "reason": f"Action violates {governance.mode} mode prohibition",
            "triggered_rules": triggered_rules,
            "conditions": [f"Change mode or rephrase action to comply with: {r}" for r in triggered_rules],
        }

    # ── 3. Mode constraint conditions ─────────────────────────
    for constraint in mode_config.get("constraints", []):
        constraint_lower = constraint.lower()
        if "confirmation" in constraint_lower or "explicit" in constraint_lower:
            if concepts & {"transaction", "destructive", "approval", "outbound"}:
                conditions.append(f"Required by {governance.mode}: {constraint}")

    return {
        "permitted": True,
        "reason": f"Action permitted under {governance.mode} + {governance.posture}",
        "triggered_rules": [],
        "conditions": conditions,
    }


# ── CLI Entry Point ────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import json as _json

    parser = argparse.ArgumentParser(description="MO§ES™ Governance CLI")
    subparsers = parser.add_subparsers(dest="command")

    # translate_mode subcommand
    tm = subparsers.add_parser("translate_mode", help="Get constraints for a mode")
    tm.add_argument("mode", help="Mode name or alias (e.g. high-security, idk)")

    # check_action subcommand
    ca = subparsers.add_parser("check_action", help="Check if action is permitted")
    ca.add_argument("action", help="Action description")
    ca.add_argument("--mode", default=None, help="Override mode (ignored if --state is used)")
    ca.add_argument("--posture", default=None, help="Override posture (ignored if --state is used)")
    ca.add_argument("--role", default=None, help="Override role (ignored if --state is used)")
    ca.add_argument("--state", default=None, help="Path to governance_state.json to load mode/posture/role")

    # list_modes subcommand
    subparsers.add_parser("list_modes", help="List all available governance modes")

    args = parser.parse_args()

    if args.command == "translate_mode":
        result = translate_mode(args.mode)
        print(_json.dumps(result, indent=2))

    elif args.command == "check_action":
        if args.state:
            import os as _os
            state_path = _os.path.expandvars(args.state)
            with open(state_path) as f:
                s = _json.load(f)
            state = GovernanceState(
                mode=resolve_mode(s.get("mode", "None (Unrestricted)")),
                posture=s.get("posture", "SCOUT"),
                role=s.get("role", "Primary"),
            )
        else:
            state = GovernanceState(
                mode=resolve_mode(args.mode or "None (Unrestricted)"),
                posture=args.posture or "SCOUT",
                role=args.role or "Primary",
            )
        result = check_action_permitted(args.action, state)
        print(_json.dumps(result, indent=2))

    elif args.command == "list_modes":
        for name in MODES:
            print(f"  {name}")

    else:
        parser.print_help()
