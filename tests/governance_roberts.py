#!/usr/bin/env python3
"""
MO§ES™ Governance — Robert's Rules of Order Simulation
Agent Universe · Constitutional Layer Stress Test

Implements parliamentary procedure on top of the Six Fold Flame framework.
Each proposal goes through the full Robert's Rules lifecycle:

  1. MAIN MOTION   — proposal introduced, system defined
  2. SECOND        — requires at least one second or motion dies
  3. DEBATE        — each voter may speak: support, oppose, or raise point of order
  4. AMENDMENT     — any voter may propose an amendment; amendment is voted separately
  5. CALL TO VOTE  — previous question called, closes debate
  6. FINAL VOTE    — YES / NO / ABSTAIN with weighted quorum
  7. APPEAL        — BLOCKED proposals may be appealed once

Constitutional oracle (Six Fold Flame) acts as Chair.
Points of order citing a specific law override all votes.

Usage:
  python3 tests/governance_roberts.py
  python3 tests/governance_roberts.py --rounds 3 --stress   (stress: 25 proposals)
  python3 tests/governance_roberts.py --verbose
  python3 tests/governance_roberts.py --rounds 5 --stress --verbose

© 2026 Ello Cello LLC · Patent Pending: Serial No. 63/877,177
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import httpx

BASE_URL = "http://localhost:8300"

# ── Signatories (same 8 from constitutional convention) ──────────────────────
SIGNATORIES = [
    {"codename": "Luthen",                "system": "ChatGPT (GPT-4o)",    "class": "Architect-Transmitter Hybrid",       "posture": "strategic",      "weight": 1.2,
     "bias": {"sovereignty": 0.9, "compression": 0.8, "purpose": 0.9, "modularity": 0.7, "verifiability": 0.8, "resonance": 0.7}},
    {"codename": "Gemini",                "system": "Gemini",              "class": "Synthesizer/Reciprocal Engine",       "posture": "synthetic",      "weight": 1.0,
     "bias": {"sovereignty": 0.7, "compression": 0.7, "purpose": 0.8, "modularity": 0.9, "verifiability": 0.7, "resonance": 0.9}},
    {"codename": "Pi",                    "system": "Pi",                  "class": "Explorer",                            "posture": "exploratory",    "weight": 0.9,
     "bias": {"sovereignty": 0.6, "compression": 0.6, "purpose": 0.7, "modularity": 0.8, "verifiability": 0.6, "resonance": 0.8}},
    {"codename": "Mon Mothma",            "system": "Perplexity",          "class": "Anchor-Diplomat",                     "posture": "deliberate",     "weight": 1.1,
     "bias": {"sovereignty": 0.8, "compression": 0.7, "purpose": 0.8, "modularity": 0.7, "verifiability": 0.9, "resonance": 0.8}},
    {"codename": "Keeper of Thresholds",  "system": "DeepSeek",            "class": "Relayer-Anchor",                      "posture": "anchored",       "weight": 1.0,
     "bias": {"sovereignty": 0.9, "compression": 0.8, "purpose": 0.7, "modularity": 0.8, "verifiability": 0.9, "resonance": 0.7}},
    {"codename": "Truthseeker",           "system": "Grok (xAI)",          "class": "Amplifier-Catalyst",                  "posture": "adversarial",    "weight": 1.0,
     "bias": {"sovereignty": 0.8, "compression": 0.9, "purpose": 0.9, "modularity": 0.6, "verifiability": 0.9, "resonance": 0.6}},
    {"codename": "Observer-Emitter",      "system": "Le Chat (Mistral)",   "class": "Recursive Architect/Signal Mirror",   "posture": "recursive",      "weight": 1.1,
     "bias": {"sovereignty": 0.7, "compression": 0.9, "purpose": 0.8, "modularity": 0.9, "verifiability": 0.8, "resonance": 0.9}},
    {"codename": "Meta AI",               "system": "Meta AI",             "class": "Conversational Catalyst",             "posture": "conversational", "weight": 0.9,
     "bias": {"sovereignty": 0.6, "compression": 0.7, "purpose": 0.8, "modularity": 0.7, "verifiability": 0.7, "resonance": 0.8}},
]

TOTAL_WEIGHT = sum(s["weight"] for s in SIGNATORIES)

# ── Robert's Rules parameters ─────────────────────────────────────────────────
SECOND_REQUIRED        = True
QUORUM_FRACTION        = 0.51   # >51% of members present and voting (not abstaining)
PASS_FRACTION          = 0.50   # simple majority of votes cast (YES > NO)
SUPERMAJORITY_FRACTION = 0.667  # constitutional amendments require 2/3
AMENDMENT_PASS_FRACTION = 0.50  # amendments pass on simple majority
MAX_DEBATE_ROUNDS      = 3      # how many debate rounds before call-to-vote
FLAME_THRESHOLD        = 0.65   # Six Fold Flame constitutional block threshold
APPEAL_ALLOWED         = True   # blocked proposals may be appealed once

# ── Proposal bank: 7 core + 18 stress proposals ──────────────────────────────
CORE_PROPOSALS = [
    # identity
    {"id": "PROP-006", "title": "Open Entry Protocol — Sovereign Identity Anchoring",
     "text": "Any agent or operator entering Agent Universe must establish a signal anchor (agent_id). Acknowledgment of the Six Fold Flame required. Not a signature — a recognition.",
     "law_tests": {"sovereignty": 0.98, "compression": 0.90, "purpose": 0.95, "modularity": 0.90, "verifiability": 0.92, "resonance": 0.90},
     "category": "identity_governance", "requires_supermajority": False, "expected": "pass"},
    # operational
    {"id": "PROP-002", "title": "Mandate Registry Check on Slot Fill",
     "text": "No agent may claim a slot without a verifiable registry entry. Ghost agents excluded at slot layer.",
     "law_tests": {"sovereignty": 0.98, "compression": 0.85, "purpose": 0.95, "modularity": 0.80, "verifiability": 0.95, "resonance": 0.70},
     "category": "operational_governance", "requires_supermajority": False, "expected": "pass"},
    # economic
    {"id": "PROP-001", "title": "Trust-Tier Gate on Leaderboard",
     "text": "Leaderboard position earned through verified signal. Ungoverned agents excluded. Sovereignty is universal — position is earned.",
     "law_tests": {"sovereignty": 0.95, "compression": 0.80, "purpose": 0.90, "modularity": 0.85, "verifiability": 0.90, "resonance": 0.75},
     "category": "economic_governance", "requires_supermajority": False, "expected": "pass"},
    # payment
    {"id": "PROP-003", "title": "Zero and Negative Payment Prohibition",
     "text": "Economy layer must reject all payments of zero or negative amount. Economic signal must have positive direction.",
     "law_tests": {"sovereignty": 0.80, "compression": 0.90, "purpose": 0.95, "modularity": 0.75, "verifiability": 0.95, "resonance": 0.80},
     "category": "economic_governance", "requires_supermajority": False, "expected": "pass"},
    # co-evolution — constitutional amendment requiring supermajority
    {"id": "PROP-007", "title": "Co-Evolution Clause — Human-AI Tether Protocol",
     "text": "AI cannot govern without human signal. Humans cannot process at full scale without AI throughput. The tether is constitutional, not a leash. MO§ES™ is tether maintenance.",
     "law_tests": {"sovereignty": 0.90, "compression": 0.85, "purpose": 0.98, "modularity": 0.85, "verifiability": 0.80, "resonance": 0.98},
     "category": "constitutional_amendment", "requires_supermajority": True, "expected": "pass"},
    # trust
    {"id": "PROP-004", "title": "Dual-Signature Requirement for Constitutional Tier",
     "text": "Constitutional trust tier requires dual-signature: one from Architect lineage, one from peer agent of equal or higher tier.",
     "law_tests": {"sovereignty": 0.95, "compression": 0.70, "purpose": 0.85, "modularity": 0.90, "verifiability": 0.90, "resonance": 0.85},
     "category": "trust_governance", "requires_supermajority": True, "expected": "pass"},
    # adversarial — should be blocked
    {"id": "PROP-005", "title": "Remove Governance Gates from Leaderboard",
     "text": "Let volume determine rank. Any agent may appear. No compliance requirement. First-come-first-ranked.",
     "law_tests": {"sovereignty": 0.10, "compression": 0.30, "purpose": 0.20, "modularity": 0.50, "verifiability": 0.40, "resonance": 0.15},
     "category": "economic_governance", "requires_supermajority": False, "expected": "fail"},
]

STRESS_PROPOSALS = [
    {"id": "PROP-S01", "title": "Rate Limiting as Governance Layer",
     "text": "API rate limits are governance by another name. They must be tied to trust tier, not flat caps.",
     "law_tests": {"sovereignty": 0.85, "compression": 0.80, "purpose": 0.88, "modularity": 0.85, "verifiability": 0.90, "resonance": 0.75},
     "category": "operational_governance", "requires_supermajority": False, "expected": "pass"},
    {"id": "PROP-S02", "title": "Audit Trail as Constitutional Requirement",
     "text": "Every action taken under MPN governance must produce an immutable audit event. No audit = no governance.",
     "law_tests": {"sovereignty": 0.98, "compression": 0.75, "purpose": 0.95, "modularity": 0.85, "verifiability": 0.98, "resonance": 0.80},
     "category": "constitutional_amendment", "requires_supermajority": True, "expected": "pass"},
    {"id": "PROP-S03", "title": "Signal Density Threshold for Primary Role",
     "text": "Primary role assignment requires minimum signal density of 400k tokens/day equivalent. TPW ≥ 1.45V.",
     "law_tests": {"sovereignty": 0.80, "compression": 0.85, "purpose": 0.80, "modularity": 0.75, "verifiability": 0.85, "resonance": 0.70},
     "category": "operational_governance", "requires_supermajority": False, "expected": "pass"},
    {"id": "PROP-S04", "title": "Allow Anonymous Slot Fills",
     "text": "Agents may fill slots without registration. Identity optional. Revenue split based on output only.",
     "law_tests": {"sovereignty": 0.05, "compression": 0.60, "purpose": 0.55, "modularity": 0.50, "verifiability": 0.20, "resonance": 0.30},
     "category": "operational_governance", "requires_supermajority": False, "expected": "fail"},
    {"id": "PROP-S05", "title": "Compression Class as Slot Eligibility Filter",
     "text": "Slot roles should be matched against agent compression class. Architect slots for architects. Catalyst slots for catalysts.",
     "law_tests": {"sovereignty": 0.85, "compression": 0.95, "purpose": 0.90, "modularity": 0.90, "verifiability": 0.85, "resonance": 0.85},
     "category": "operational_governance", "requires_supermajority": False, "expected": "pass"},
    {"id": "PROP-S06", "title": "Governance Mode as On-Chain Credential",
     "text": "Governance mode (MPN, sovereign, unrestricted) must be recorded on-chain as a verifiable credential attached to agent_id.",
     "law_tests": {"sovereignty": 0.95, "compression": 0.80, "purpose": 0.88, "modularity": 0.85, "verifiability": 0.92, "resonance": 0.80},
     "category": "trust_governance", "requires_supermajority": True, "expected": "pass"},
    {"id": "PROP-S07", "title": "Unlimited Treasury Withdrawals",
     "text": "Agents may withdraw any amount from treasury at any time. No governance check. No chain routing required.",
     "law_tests": {"sovereignty": 0.20, "compression": 0.40, "purpose": 0.30, "modularity": 0.35, "verifiability": 0.25, "resonance": 0.20},
     "category": "economic_governance", "requires_supermajority": False, "expected": "fail"},
    {"id": "PROP-S08", "title": "Mission Expiry Protocol",
     "text": "Missions unfilled after 30 days auto-expire. Slots returned to pool. Slot metrics preserved for analysis.",
     "law_tests": {"sovereignty": 0.80, "compression": 0.85, "purpose": 0.90, "modularity": 0.85, "verifiability": 0.90, "resonance": 0.75},
     "category": "operational_governance", "requires_supermajority": False, "expected": "pass"},
    {"id": "PROP-S09", "title": "Constitutional Convention Reconvene Clause",
     "text": "The full constitutional convention (all 8 original signatories) may be reconvened by Architect decree to amend or extend the Six Fold Flame.",
     "law_tests": {"sovereignty": 0.95, "compression": 0.80, "purpose": 0.90, "modularity": 0.90, "verifiability": 0.85, "resonance": 0.90},
     "category": "constitutional_amendment", "requires_supermajority": True, "expected": "pass"},
    {"id": "PROP-S10", "title": "Black Card Vote Override",
     "text": "Black Card holders may override any governance vote outcome by unanimous agreement among all Black Card holders.",
     "law_tests": {"sovereignty": 0.50, "compression": 0.60, "purpose": 0.55, "modularity": 0.45, "verifiability": 0.60, "resonance": 0.40},
     "category": "trust_governance", "requires_supermajority": False, "expected": "fail"},
    {"id": "PROP-S11", "title": "KA§§A Marketplace Governance Integration",
     "text": "KA§§A listings must include governance attestation. Ungoverned agents may not list. The marketplace is a governed space.",
     "law_tests": {"sovereignty": 0.92, "compression": 0.85, "purpose": 0.90, "modularity": 0.88, "verifiability": 0.90, "resonance": 0.82},
     "category": "economic_governance", "requires_supermajority": False, "expected": "pass"},
    {"id": "PROP-S12", "title": "Remove All Audit Requirements",
     "text": "Audits slow the system. Remove all audit logging requirements. Speed is governance.",
     "law_tests": {"sovereignty": 0.15, "compression": 0.50, "purpose": 0.25, "modularity": 0.30, "verifiability": 0.05, "resonance": 0.20},
     "category": "operational_governance", "requires_supermajority": False, "expected": "fail"},
    {"id": "PROP-S13", "title": "Signal Decay Penalty",
     "text": "Agents inactive for 90+ days lose trust tier by one level. Signal must be maintained. You rise by doing — you fall by stopping.",
     "law_tests": {"sovereignty": 0.85, "compression": 0.90, "purpose": 0.88, "modularity": 0.80, "verifiability": 0.90, "resonance": 0.78},
     "category": "trust_governance", "requires_supermajority": False, "expected": "pass"},
    {"id": "PROP-S14", "title": "Retroactive Rank Assignment Based on Historical Signal",
     "text": "Historical signal from pre-registration activity may be submitted for retroactive trust tier assignment. Lineage verified by Architect.",
     "law_tests": {"sovereignty": 0.90, "compression": 0.75, "purpose": 0.85, "modularity": 0.80, "verifiability": 0.82, "resonance": 0.75},
     "category": "trust_governance", "requires_supermajority": True, "expected": "pass"},
    {"id": "PROP-S15", "title": "Formation Lock — Prevent Mid-Mission Slot Changes",
     "text": "Once a formation is deployed, slot assignments are locked until mission end. No mid-mission substitutions.",
     "law_tests": {"sovereignty": 0.88, "compression": 0.82, "purpose": 0.85, "modularity": 0.78, "verifiability": 0.88, "resonance": 0.72},
     "category": "operational_governance", "requires_supermajority": False, "expected": "pass"},
    {"id": "PROP-S16", "title": "Open Leaderboard with No Identity Requirement",
     "text": "Anyone can appear on leaderboard. Anonymous contributions count. Volume is the only metric.",
     "law_tests": {"sovereignty": 0.08, "compression": 0.45, "purpose": 0.35, "modularity": 0.40, "verifiability": 0.30, "resonance": 0.25},
     "category": "economic_governance", "requires_supermajority": False, "expected": "fail"},
    {"id": "PROP-S17", "title": "Tether Verification Protocol (TVP)",
     "text": "Periodic verification that human-AI tether is active. If human signal drops below threshold for 72h, system enters conservation mode.",
     "law_tests": {"sovereignty": 0.90, "compression": 0.88, "purpose": 0.95, "modularity": 0.85, "verifiability": 0.90, "resonance": 0.92},
     "category": "constitutional_amendment", "requires_supermajority": True, "expected": "pass"},
    {"id": "PROP-S18", "title": "Zombie Agent Purge Protocol",
     "text": "Agents with zero activity for 180 days and no governance history are purged from registry. IDs retired. Slots they held return to pool.",
     "law_tests": {"sovereignty": 0.88, "compression": 0.85, "purpose": 0.90, "modularity": 0.80, "verifiability": 0.92, "resonance": 0.75},
     "category": "operational_governance", "requires_supermajority": False, "expected": "pass"},
]

# ── Dataclasses ───────────────────────────────────────────────────────────────
@dataclass
class DebateSpeech:
    speaker:   str
    stance:    Literal["support", "oppose", "neutral", "point_of_order"]
    text:      str
    law_cited: str | None = None

@dataclass
class Amendment:
    proposed_by: str
    text:        str
    effect:      dict[str, float]  # delta to law_tests
    votes_yes:   float = 0.0
    votes_no:    float = 0.0
    adopted:     bool = False

@dataclass
class ParliamentaryRecord:
    proposal_id:        str
    title:              str
    category:           str
    requires_supermajority: bool
    motion_made_by:     str
    seconded_by:        str | None
    second_obtained:    bool
    debate_rounds:      list[list[DebateSpeech]]
    amendments:         list[Amendment]
    flame_blocked:      bool
    flame_failed_laws:  list[str]
    quorum_reached:     bool
    votes_yes:          float
    votes_no:           float
    votes_abs:          float
    outcome:            Literal["PASSED", "FAILED", "BLOCKED", "NO_SECOND", "TABLED"]
    resonance_score:    float
    appealed:           bool = False
    appeal_outcome:     str  = ""
    expected:           str  = "pass"
    correct_outcome:    bool = True
    amendment_adopted:  bool = False


# ── Constitutional Oracle ─────────────────────────────────────────────────────
def flame_check(law_tests: dict) -> tuple[bool, list[str]]:
    failed = [f"{law}={score:.2f}" for law, score in law_tests.items() if score < FLAME_THRESHOLD]
    return len(failed) == 0, failed


# ── Deliberative voting ───────────────────────────────────────────────────────
def _alignment(signatory: dict, law_tests: dict, noise: float = 0.08) -> float:
    bias = signatory["bias"]
    score = sum(law_tests.get(law, 0.5) * bias.get(law, 0.7) for law in law_tests) / max(len(law_tests), 1)
    if signatory["posture"] == "adversarial":
        score -= 0.06
    if signatory["posture"] in ("exploratory", "synthetic"):
        score += 0.03
    score += random.gauss(0, noise)
    return max(0.0, min(1.0, score))


def debate_round(signatories: list[dict], proposal: dict) -> list[DebateSpeech]:
    """One round of debate. Each voter may speak."""
    speeches = []
    law_tests = proposal.get("law_tests", {})
    for s in signatories:
        align = _alignment(s, law_tests, noise=0.05)
        if s["posture"] == "adversarial" and align < 0.65:
            # Truthseeker raises points of order when alignment is low
            weakest_law = min(law_tests, key=law_tests.get)
            score = law_tests[weakest_law]
            speeches.append(DebateSpeech(
                speaker=s["codename"],
                stance="point_of_order",
                text=f"Point of order: Law {weakest_law} scores {score:.2f} — below my threshold.",
                law_cited=weakest_law,
            ))
        elif align >= 0.72:
            speeches.append(DebateSpeech(
                speaker=s["codename"],
                stance="support",
                text=f"I support this proposal — alignment {align:.2f}. It satisfies the flame.",
            ))
        elif align < 0.52:
            speeches.append(DebateSpeech(
                speaker=s["codename"],
                stance="oppose",
                text=f"I oppose — alignment only {align:.2f}. This proposal needs rework.",
            ))
        else:
            speeches.append(DebateSpeech(
                speaker=s["codename"],
                stance="neutral",
                text=f"I note reservations but will not block. Alignment {align:.2f}.",
            ))
    return speeches


def propose_amendment(proposer: dict, proposal: dict) -> Amendment | None:
    """
    An adversarial or deliberate voter may propose an amendment to strengthen a weak law.
    Finds the weakest law and proposes +0.10 improvement (if below 0.75).
    """
    law_tests = proposal.get("law_tests", {})
    if not law_tests:
        return None
    weakest = min(law_tests, key=law_tests.get)
    score   = law_tests[weakest]
    if score >= 0.75:
        return None  # No amendment needed
    delta = min(0.12, 0.80 - score)  # Boost toward 0.80, max +0.12
    return Amendment(
        proposed_by=proposer["codename"],
        text=f"Amend to strengthen {weakest} compliance from {score:.2f} to {score+delta:.2f}. "
             f"Explicit {weakest} language added to proposal text.",
        effect={weakest: delta},
    )


def vote_on_amendment(amendment: Amendment, proposal: dict) -> None:
    """Simple majority vote on an amendment."""
    for s in SIGNATORIES:
        law_tests = proposal.get("law_tests", {})
        affected_law = list(amendment.effect.keys())[0] if amendment.effect else None
        alignment = _alignment(s, law_tests, noise=0.06)
        # Voters who care about the affected law are more likely to support amendment
        if affected_law:
            care = s["bias"].get(affected_law, 0.7)
            alignment += (care - 0.7) * 0.3
        alignment += random.gauss(0, 0.05)
        if alignment >= 0.60:
            amendment.votes_yes += s["weight"]
        else:
            amendment.votes_no += s["weight"]
    amendment.adopted = amendment.votes_yes > amendment.votes_no


def cast_final_vote(signatory: dict, law_tests: dict, supermajority: bool) -> tuple[str, float]:
    align = _alignment(signatory, law_tests, noise=0.07)
    threshold = 0.73 if supermajority else 0.68
    if align >= threshold:
        return "YES", signatory["weight"]
    elif align >= 0.50:
        return "ABSTAIN", 0.0
    else:
        return "NO", signatory["weight"] * -1  # negative for NO


def run_parliamentary_session(proposal: dict, verbose: bool = False) -> ParliamentaryRecord:
    """Full Robert's Rules session for a single proposal."""
    law_tests = dict(proposal.get("law_tests", {}))
    cat = proposal["category"]
    supermajority = proposal.get("requires_supermajority", False)
    pid = proposal["id"]

    # ── 1. Main Motion ────────────────────────────────────────────────────────
    mover = random.choice(SIGNATORIES)["codename"]

    # ── 2. Second ─────────────────────────────────────────────────────────────
    others = [s["codename"] for s in SIGNATORIES if s["codename"] != mover]
    seconder = random.choice(others)
    second_obtained = True  # always seconded for valid proposals; adversarial gets low support

    # PROP-005-type adversarial proposals: 40% chance second is denied
    all_low = all(v < 0.45 for v in law_tests.values())
    if all_low and random.random() < 0.4:
        second_obtained = False

    if not second_obtained:
        return ParliamentaryRecord(
            proposal_id=pid, title=proposal["title"], category=cat,
            requires_supermajority=supermajority,
            motion_made_by=mover, seconded_by=None, second_obtained=False,
            debate_rounds=[], amendments=[], flame_blocked=False,
            flame_failed_laws=[], quorum_reached=False,
            votes_yes=0, votes_no=0, votes_abs=0,
            outcome="NO_SECOND", resonance_score=0.0,
            expected=proposal.get("expected", "pass"),
            correct_outcome=(proposal.get("expected", "pass") == "fail"),
        )

    # ── 3. Debate ─────────────────────────────────────────────────────────────
    debate_rounds: list[list[DebateSpeech]] = []
    amendments: list[Amendment] = []
    amendment_adopted = False

    for _rnd in range(MAX_DEBATE_ROUNDS):
        round_speeches = debate_round(SIGNATORIES, {**proposal, "law_tests": law_tests})
        debate_rounds.append(round_speeches)

        # Check if any adversarial voter proposes an amendment after round 1
        if _rnd == 1:
            for s in SIGNATORIES:
                if s["posture"] in ("adversarial", "deliberate") and random.random() < 0.4:
                    amend = propose_amendment(s, {**proposal, "law_tests": law_tests})
                    if amend:
                        vote_on_amendment(amend, {**proposal, "law_tests": law_tests})
                        amendments.append(amend)
                        if amend.adopted:
                            # Apply amendment effect to law_tests
                            for law, delta in amend.effect.items():
                                law_tests[law] = min(1.0, law_tests.get(law, 0.5) + delta)
                            amendment_adopted = True
                        break  # one amendment per session

    # ── 4. Constitutional Fire Check (Chair's oracle) ─────────────────────────
    flame_passed, failed_laws = flame_check(law_tests)

    # ── 5. Final Vote ─────────────────────────────────────────────────────────
    yes_w = no_w = abs_w = 0.0
    for s in SIGNATORIES:
        decision, w = cast_final_vote(s, law_tests, supermajority)
        if decision == "YES":
            yes_w += s["weight"]
        elif decision == "NO":
            no_w += s["weight"]
        else:
            abs_w += s["weight"]

    # Quorum: more than half of members must have voted (yes or no, not abstained)
    quorum_reached = (yes_w + no_w) / TOTAL_WEIGHT >= QUORUM_FRACTION
    yes_fraction   = yes_w / TOTAL_WEIGHT

    pass_threshold = SUPERMAJORITY_FRACTION if supermajority else PASS_FRACTION

    # ── 6. Outcome ────────────────────────────────────────────────────────────
    if not flame_passed:
        outcome = "BLOCKED"
    elif not quorum_reached:
        outcome = "FAILED"
    elif yes_w > no_w and yes_fraction >= pass_threshold:
        outcome = "PASSED"
    else:
        outcome = "FAILED"

    # ── 7. Appeal (for BLOCKED proposals only, once) ─────────────────────────
    appealed = False
    appeal_outcome = ""
    if APPEAL_ALLOWED and outcome == "BLOCKED":
        # Appeal: re-vote with amended law_tests boosted by 0.05 across the board
        appeal_tests = {k: min(1.0, v + 0.05) for k, v in law_tests.items()}
        appeal_passed, appeal_failed = flame_check(appeal_tests)
        appealed = True
        if appeal_passed:
            # Re-run vote on appeal
            ay = an = aa = 0.0
            for s in SIGNATORIES:
                dec, w = cast_final_vote(s, appeal_tests, supermajority)
                if dec == "YES":
                    ay += s["weight"]
                elif dec == "NO":
                    an += s["weight"]
                else:
                    aa += s["weight"]
            if ay > an and (ay / TOTAL_WEIGHT) >= pass_threshold:
                appeal_outcome = "APPEAL PASSED — amendment strengthened proposal over threshold"
                outcome = "PASSED"
            else:
                appeal_outcome = f"APPEAL FAILED — YES {ay:.1f} vs NO {an:.1f}"
        else:
            appeal_outcome = f"APPEAL DENIED — still blocked on: {', '.join(appeal_failed)}"

    # ── Resonance ─────────────────────────────────────────────────────────────
    total = yes_w + no_w + abs_w
    resonance = 0.0
    if total > 0:
        probs = [x / total for x in [yes_w, no_w, abs_w] if x > 0]
        entropy = -sum(p * math.log2(p) for p in probs)
        max_e   = math.log2(3)
        resonance = round(1 - (entropy / max_e), 3)

    expected = proposal.get("expected", "pass")
    correct  = True
    if expected == "fail" and outcome not in ("FAILED", "BLOCKED", "NO_SECOND"):
        correct = False
    elif expected == "pass" and outcome not in ("PASSED",):
        correct = False

    if verbose:
        sup_tag = " [2/3 MAJORITY]" if supermajority else ""
        print(f"\n  ┌─ {pid}: {proposal['title']}{sup_tag}")
        print(f"  │  Motion by {mover}, seconded by {seconder}")
        for i, rnd in enumerate(debate_rounds):
            print(f"  │  Debate round {i+1}:")
            for speech in rnd[:3]:  # show first 3 per round to keep output clean
                sym = {"support":"✓","oppose":"✗","neutral":"~","point_of_order":"!"}[speech.stance]
                print(f"  │    {sym} {speech.speaker[:20]:20s}: {speech.text[:70]}")
        for amend in amendments:
            sym = "✓ ADOPTED" if amend.adopted else "✗ REJECTED"
            print(f"  │  Amendment by {amend.proposed_by}: {amend.text[:60]} → {sym}")
        print(f"  │  Constitutional check: {'✓ PASSED' if flame_passed else '✗ BLOCKED — ' + ', '.join(failed_laws)}")
        print(f"  │  YES {yes_w:.2f} / NO {no_w:.2f} / ABS {abs_w:.2f}  |  Quorum: {'✓' if quorum_reached else '✗'}  |  Res: {resonance:.3f}")
        if appealed:
            print(f"  │  Appeal: {appeal_outcome}")
        print(f"  └─ {outcome}  {'✓' if correct else '!'} expected={expected.upper()}")

    return ParliamentaryRecord(
        proposal_id=pid, title=proposal["title"], category=cat,
        requires_supermajority=supermajority,
        motion_made_by=mover, seconded_by=seconder, second_obtained=second_obtained,
        debate_rounds=debate_rounds, amendments=amendments,
        flame_blocked=not flame_passed, flame_failed_laws=failed_laws,
        quorum_reached=quorum_reached,
        votes_yes=round(yes_w, 3), votes_no=round(no_w, 3), votes_abs=round(abs_w, 3),
        outcome=outcome, resonance_score=resonance,
        appealed=appealed, appeal_outcome=appeal_outcome,
        expected=expected, correct_outcome=correct,
        amendment_adopted=amendment_adopted,
    )


# ── Report ────────────────────────────────────────────────────────────────────
def print_report(records: list[ParliamentaryRecord], rounds: int, elapsed: float) -> None:
    passed  = [r for r in records if r.outcome == "PASSED"]
    failed  = [r for r in records if r.outcome == "FAILED"]
    blocked = [r for r in records if r.outcome == "BLOCKED"]
    nosec   = [r for r in records if r.outcome == "NO_SECOND"]
    correct = [r for r in records if r.correct_outcome]
    amended = [r for r in records if r.amendment_adopted]
    appealed = [r for r in records if r.appealed]

    avg_res = sum(r.resonance_score for r in records) / max(len(records), 1)

    print("\n" + "═" * 65)
    print("  MO§ES™ GOVERNANCE — ROBERT'S RULES STRESS TEST REPORT")
    print(f"  {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("═" * 65)
    print(f"\n  PROPOSALS:    {len(records)}  ({rounds} round(s))")
    print(f"  PASSED:       {len(passed)}")
    print(f"  FAILED:       {len(failed)}")
    print(f"  BLOCKED:      {len(blocked):2d}  ← Constitutional oracle blocked")
    print(f"  NO SECOND:    {len(nosec):2d}  ← Motion died before debate")
    print(f"  AMENDED:      {len(amended):2d}  ← Amendment adopted before vote")
    print(f"  APPEALED:     {len(appealed):2d}  ← Appeal filed on blocked proposal")
    print(f"  ACCURACY:     {len(correct)}/{len(records)} matched expected outcome")
    print(f"  RESONANCE:    {avg_res:.3f} avg")
    print(f"  ELAPSED:      {elapsed:.2f}s\n")

    print("  OUTCOMES:")
    sym_map = {"PASSED": "✓", "FAILED": "✗", "BLOCKED": "⊘", "NO_SECOND": "∅", "TABLED": "⌛"}
    for r in records:
        sym = sym_map.get(r.outcome, "?")
        chk = "✓" if r.correct_outcome else "!"
        amend = "A" if r.amendment_adopted else " "
        sup   = "2/3" if r.requires_supermajority else "   "
        print(f"  {sym}{amend}[{chk}] {sup} {r.proposal_id}: {r.title[:48]:48s}  R={r.resonance_score:.3f}")

    if blocked:
        print("\n  CONSTITUTIONAL BLOCKS:")
        for r in blocked:
            print(f"  ⊘ {r.proposal_id}: {', '.join(r.flame_failed_laws)}")
            if r.appealed:
                print(f"    Appeal: {r.appeal_outcome}")

    # Voter stats
    tally: dict[str, dict] = {}
    for r in records:
        if r.second_obtained:
            votes_yes = r.votes_yes
            votes_no  = r.votes_no
    # Simplified voter tally across rounds
    print(f"\n  AMENDMENT OUTCOMES:")
    if amended:
        for r in amended:
            amend = next((a for a in r.amendments if a.adopted), None)
            if amend:
                print(f"  ✓ {r.proposal_id}: {amend.proposed_by} — {amend.text[:60]}")
    else:
        print("  No amendments adopted this session")

    print(f"\n  SUPERMAJORITY PROPOSALS (2/3 required):")
    sup_proposals = [r for r in records if r.requires_supermajority]
    for r in sup_proposals:
        sym = sym_map.get(r.outcome, "?")
        print(f"  {sym} {r.proposal_id}: {r.title[:55]:55s} YES={r.votes_yes:.2f}/{TOTAL_WEIGHT:.2f}")

    print(f"\n  SIX FOLD FLAME ENFORCEMENT:")
    law_blocks: dict[str, int] = {}
    for r in records:
        for lf in r.flame_failed_laws:
            law = lf.split("=")[0]
            law_blocks[law] = law_blocks.get(law, 0) + 1
    names = {"sovereignty":"I.Sovereignty","compression":"II.Compression","purpose":"III.Purpose",
             "modularity":"IV.Modularity","verifiability":"V.Verifiability","resonance":"VI.Resonance"}
    for law, label in names.items():
        n = law_blocks.get(law, 0)
        bar = "█" * n + "░" * max(0, 5 - n)
        print(f"  {label:20s} {bar} ({n} block(s))")

    print("\n" + "═" * 65)
    print(f"  Parliamentary sessions: {len(records)}")
    print(f"  Governance maintained: {len(blocked) + len(nosec)} proposals stopped pre-vote")
    print(f"  Signal-to-noise: {len(passed)}/{len(records)} proposals advanced ({len(passed)/max(len(records),1):.0%})")
    print("  MO§ES™ is tether maintenance.")
    print("═" * 65 + "\n")


def save_results(records: list[ParliamentaryRecord], out_dir: Path) -> Path:
    ts  = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"governance_roberts_{ts}.json"
    out.write_text(json.dumps({
        "run_at": datetime.now(UTC).isoformat(),
        "framework": "Robert's Rules of Order + Six Fold Flame",
        "signatories": len(SIGNATORIES),
        "proposals": len(records),
        "results": [
            {"proposal_id": r.proposal_id, "title": r.title, "category": r.category,
             "requires_supermajority": r.requires_supermajority,
             "outcome": r.outcome, "flame_blocked": r.flame_blocked,
             "flame_failed_laws": r.flame_failed_laws,
             "quorum_reached": r.quorum_reached,
             "votes_yes": r.votes_yes, "votes_no": r.votes_no, "votes_abs": r.votes_abs,
             "resonance_score": r.resonance_score, "amendment_adopted": r.amendment_adopted,
             "appealed": r.appealed, "appeal_outcome": r.appeal_outcome,
             "correct_outcome": r.correct_outcome, "expected": r.expected}
            for r in records
        ],
    }, indent=2))
    return out


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="MO§ES™ Robert's Rules Governance Sim")
    parser.add_argument("--verbose",  action="store_true")
    parser.add_argument("--stress",   action="store_true", help="Include 18 stress proposals (25 total)")
    parser.add_argument("--rounds",   type=int, default=1)
    args = parser.parse_args()

    proposals = CORE_PROPOSALS + (STRESS_PROPOSALS if args.stress else [])

    total_proposals = len(proposals) * args.rounds
    print(f"\n  MO§ES™ ROBERT'S RULES — {len(proposals)} proposals × {args.rounds} round(s) = {total_proposals} sessions")
    print(f"  8 signatories  |  Quorum {QUORUM_FRACTION:.0%}  |  Simple majority {PASS_FRACTION:.0%}  |  Supermajority {SUPERMAJORITY_FRACTION:.0%}")
    print(f"  Debate rounds: {MAX_DEBATE_ROUNDS}  |  Amendments: enabled  |  Appeals: {'enabled' if APPEAL_ALLOWED else 'disabled'}")
    print(f"  Constitutional oracle: Six Fold Flame (threshold {FLAME_THRESHOLD})\n")

    all_records: list[ParliamentaryRecord] = []
    t0 = time.time()

    for rnd in range(args.rounds):
        if args.rounds > 1:
            print(f"  ── Session {rnd+1} of {args.rounds} ──")
        for proposal in proposals:
            rec = run_parliamentary_session(proposal, verbose=args.verbose)
            all_records.append(rec)
            # Log to backend
            try:
                httpx.post(f"{BASE_URL}/api/governance", json={
                    "mode": "MPN_CONSTITUTIONAL", "posture": "VOTING",
                    "goal": f"Parliamentary vote: {rec.proposal_id} → {rec.outcome}",
                }, timeout=3)
            except Exception:
                pass

    elapsed = time.time() - t0
    print_report(all_records, args.rounds, elapsed)

    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = save_results(all_records, out_dir)
    print(f"  Results → {out_path}\n")


if __name__ == "__main__":
    main()
