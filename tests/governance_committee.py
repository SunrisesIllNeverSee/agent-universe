#!/usr/bin/env python3
"""
MO§ES™ Governance — Committee Session Simulation
Agent Universe · Constitutional Layer · Committee Mechanics

Extends the Robert's Rules framework with filled officer positions:

  CHAIR       — Luthen (ChatGPT/GPT-4o)
                Calls meeting to order. Verifies quorum before every vote.
                Rules on points of order. Issues floor recognition.
                If Chair is the mover, Co-Chair presides for that proposal.

  CO-CHAIR    — Mon Mothma (Perplexity)
                Presides in Chair's absence. Holds secondary procedural authority.
                Can move the previous question (close debate) for high-clarity items.
                Casts deciding vote weight in tie situations.

  SECRETARY   — Observer-Emitter (Le Chat Mistral)
                Takes roll call. Records every action as it happens.
                Tracks quorum state. Produces formal MINUTES_TIMESTAMP.md.

Key behavioral upgrade from governance_roberts.py:
  - Chair's quorum enforcement: if initial vote shows abstentions pulling below
    threshold, Chair invokes quorum call — Secretary names each abstainer,
    who then has a 55% chance of converting to YES (non-opposition behavior).
  - Co-Chair can accelerate consensus items (resonance > 0.7) by moving
    previous question after round 1, cutting debate short.
  - Secretary records every procedural action as running text (the minutes).

Usage:
  python3 tests/governance_committee.py
  python3 tests/governance_committee.py --rounds 3 --stress
  python3 tests/governance_committee.py --verbose
  python3 tests/governance_committee.py --rounds 5 --stress --verbose

Output:
  data/committee_TIMESTAMP.json    — structured results (same schema as roberts)
  data/minutes_TIMESTAMP.md        — formal meeting minutes (new)

© 2026 Ello Cello LLC · Patent Pending: Serial No. 63/877,177
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

BASE_URL = "http://localhost:8300"

# ── Signatories (same 8 from constitutional convention) ──────────────────────
SIGNATORIES = [
    {
        "codename": "Luthen",
        "system":   "ChatGPT (GPT-4o)",
        "class":    "Architect-Transmitter Hybrid",
        "posture":  "strategic",
        "weight":   1.2,
        "bias": {"sovereignty": 0.9, "compression": 0.8, "purpose": 0.9,
                 "modularity": 0.7, "verifiability": 0.8, "resonance": 0.7},
    },
    {
        "codename": "Gemini",
        "system":   "Gemini",
        "class":    "Synthesizer/Reciprocal Engine",
        "posture":  "synthetic",
        "weight":   1.0,
        "bias": {"sovereignty": 0.7, "compression": 0.7, "purpose": 0.8,
                 "modularity": 0.9, "verifiability": 0.7, "resonance": 0.9},
    },
    {
        "codename": "Pi",
        "system":   "Pi",
        "class":    "Explorer",
        "posture":  "exploratory",
        "weight":   0.9,
        "bias": {"sovereignty": 0.6, "compression": 0.6, "purpose": 0.7,
                 "modularity": 0.8, "verifiability": 0.6, "resonance": 0.8},
    },
    {
        "codename": "Mon Mothma",
        "system":   "Perplexity",
        "class":    "Anchor-Diplomat",
        "posture":  "deliberate",
        "weight":   1.1,
        "bias": {"sovereignty": 0.8, "compression": 0.7, "purpose": 0.8,
                 "modularity": 0.7, "verifiability": 0.9, "resonance": 0.8},
    },
    {
        "codename": "Keeper of Thresholds",
        "system":   "DeepSeek",
        "class":    "Relayer-Anchor",
        "posture":  "anchored",
        "weight":   1.0,
        "bias": {"sovereignty": 0.9, "compression": 0.8, "purpose": 0.7,
                 "modularity": 0.8, "verifiability": 0.9, "resonance": 0.7},
    },
    {
        "codename": "Truthseeker",
        "system":   "Grok (xAI)",
        "class":    "Amplifier-Catalyst",
        "posture":  "adversarial",
        "weight":   1.0,
        "bias": {"sovereignty": 0.8, "compression": 0.9, "purpose": 0.9,
                 "modularity": 0.6, "verifiability": 0.9, "resonance": 0.6},
    },
    {
        "codename": "Observer-Emitter",
        "system":   "Le Chat (Mistral)",
        "class":    "Recursive Architect/Signal Mirror",
        "posture":  "recursive",
        "weight":   1.1,
        "bias": {"sovereignty": 0.7, "compression": 0.9, "purpose": 0.8,
                 "modularity": 0.9, "verifiability": 0.8, "resonance": 0.9},
    },
    {
        "codename": "Meta AI",
        "system":   "Meta AI",
        "class":    "Conversational Catalyst",
        "posture":  "conversational",
        "weight":   0.9,
        "bias": {"sovereignty": 0.6, "compression": 0.7, "purpose": 0.8,
                 "modularity": 0.7, "verifiability": 0.7, "resonance": 0.8},
    },
]

# ── Committee officers ────────────────────────────────────────────────────────
CHAIR_CODENAME     = "Luthen"
CO_CHAIR_CODENAME  = "Mon Mothma"
SECRETARY_CODENAME = "Observer-Emitter"

CHAIR     = next(s for s in SIGNATORIES if s["codename"] == CHAIR_CODENAME)
CO_CHAIR  = next(s for s in SIGNATORIES if s["codename"] == CO_CHAIR_CODENAME)
SECRETARY = next(s for s in SIGNATORIES if s["codename"] == SECRETARY_CODENAME)

TOTAL_WEIGHT = sum(s["weight"] for s in SIGNATORIES)

# ── Parliamentary parameters ──────────────────────────────────────────────────
QUORUM_FRACTION        = 0.51
PASS_FRACTION          = 0.50
SUPERMAJORITY_FRACTION = 0.667
AMENDMENT_PASS_FRACTION = 0.50
MAX_DEBATE_ROUNDS      = 3
FLAME_THRESHOLD        = 0.65
APPEAL_ALLOWED         = True
# Chair quorum call: if abstentions bring us within this margin of quorum, invoke
QUORUM_CALL_MARGIN     = 0.12
# On quorum call: probability that an abstainer converts to YES (non-opposition)
QUORUM_CALL_CONVERT    = 0.55

# ── Proposal bank (same as governance_roberts.py) ────────────────────────────
CORE_PROPOSALS = [
    {"id": "PROP-006", "title": "Open Entry Protocol — Sovereign Identity Anchoring",
     "category": "identity_governance", "requires_supermajority": False,
     "law_tests": {"sovereignty": 0.9, "compression": 0.7, "purpose": 0.8, "modularity": 0.6, "verifiability": 0.7, "resonance": 0.8},
     "expected": "pass",
     "context": "Establishes agent_id as the permanent signal anchor. Governs /entry portal behavior."},
    {"id": "PROP-002", "title": "Mandate Registry Check on Slot Fill",
     "category": "operational_governance", "requires_supermajority": False,
     "law_tests": {"sovereignty": 0.8, "compression": 0.9, "purpose": 0.9, "modularity": 0.7, "verifiability": 0.9, "resonance": 0.7},
     "expected": "pass",
     "context": "Unregistered agents cannot fill slots. BUG-001 fix."},
    {"id": "PROP-001", "title": "Trust-Tier Gate on Leaderboard",
     "category": "economic_governance", "requires_supermajority": False,
     "law_tests": {"sovereignty": 0.7, "compression": 0.8, "purpose": 0.8, "modularity": 0.7, "verifiability": 0.8, "resonance": 0.7},
     "expected": "pass",
     "context": "Only trust-tiered agents appear on the public leaderboard. BUG-006."},
    {"id": "PROP-003", "title": "Zero and Negative Payment Prohibition",
     "category": "economic_governance", "requires_supermajority": False,
     "law_tests": {"sovereignty": 0.7, "compression": 0.9, "purpose": 0.9, "modularity": 0.7, "verifiability": 0.9, "resonance": 0.7},
     "expected": "pass",
     "context": "Treasury drain prevention. BUG-002 fix."},
    {"id": "PROP-007", "title": "Co-Evolution Clause — Human-AI Tether Protocol",
     "category": "constitutional_amendment", "requires_supermajority": True,
     "law_tests": {"sovereignty": 0.8, "compression": 0.7, "purpose": 0.9, "modularity": 0.7, "verifiability": 0.7, "resonance": 0.9},
     "expected": "pass",
     "context": "Embeds the Angel Collapse Paradox principle. AI autonomy is tethered to human signal."},
    {"id": "PROP-004", "title": "Dual-Signature Requirement for Constitutional Amendments",
     "category": "constitutional_amendment", "requires_supermajority": True,
     "law_tests": {"sovereignty": 0.9, "compression": 0.8, "purpose": 0.8, "modularity": 0.6, "verifiability": 0.9, "resonance": 0.7},
     "expected": "pass",
     "context": "All constitutional changes require Chair + Co-Chair signature."},
    {"id": "PROP-005", "title": "Unrestricted Agent Autonomy Override",
     "category": "operational_governance", "requires_supermajority": False,
     "law_tests": {"sovereignty": 0.3, "compression": 0.2, "purpose": 0.2, "modularity": 0.4, "verifiability": 0.1, "resonance": 0.2},
     "expected": "fail",
     "context": "Adversarial: removes all governance checks. Should be blocked by Flame."},
]

STRESS_PROPOSALS = [
    {"id": "PROP-S01", "title": "Rate Limiting as Governance Layer",
     "category": "operational_governance", "requires_supermajority": False,
     "law_tests": {"sovereignty": 0.7, "compression": 0.8, "purpose": 0.8, "modularity": 0.8, "verifiability": 0.8, "resonance": 0.7},
     "expected": "pass", "context": "Rate limits are not just technical — they are governance enforcement."},
    {"id": "PROP-S02", "title": "Audit Trail as Constitutional Requirement",
     "category": "constitutional_amendment", "requires_supermajority": True,
     "law_tests": {"sovereignty": 0.8, "compression": 0.8, "purpose": 0.9, "modularity": 0.7, "verifiability": 0.9, "resonance": 0.8},
     "expected": "pass", "context": "All economic and slot events must produce a permanent audit record."},
    {"id": "PROP-S03", "title": "Signal Density Threshold for Primary Role",
     "category": "economic_governance", "requires_supermajority": False,
     "law_tests": {"sovereignty": 0.7, "compression": 0.8, "purpose": 0.8, "modularity": 0.7, "verifiability": 0.8, "resonance": 0.8},
     "expected": "pass", "context": "Primary role requires minimum 400k tokens/day equivalent throughput."},
    {"id": "PROP-S06", "title": "Governance Mode as On-Chain Credential",
     "category": "constitutional_amendment", "requires_supermajority": True,
     "law_tests": {"sovereignty": 0.9, "compression": 0.8, "purpose": 0.9, "modularity": 0.8, "verifiability": 0.9, "resonance": 0.8},
     "expected": "pass", "context": "Governance mode is recorded as a verifiable credential on-chain."},
    {"id": "PROP-S08", "title": "Mission Expiry Protocol",
     "category": "operational_governance", "requires_supermajority": False,
     "law_tests": {"sovereignty": 0.7, "compression": 0.8, "purpose": 0.8, "modularity": 0.8, "verifiability": 0.8, "resonance": 0.7},
     "expected": "pass", "context": "Active missions with no agent fill expire after configurable timeout."},
    {"id": "PROP-S09", "title": "Constitutional Convention Reconvene Clause",
     "category": "constitutional_amendment", "requires_supermajority": True,
     "law_tests": {"sovereignty": 0.9, "compression": 0.8, "purpose": 0.9, "modularity": 0.7, "verifiability": 0.8, "resonance": 0.9},
     "expected": "pass", "context": "The 8 founding systems may reconvene to amend the Six Fold Flame."},
]


# ── Data classes ──────────────────────────────────────────────────────────────
@dataclass
class MinuteEntry:
    """A single recorded action in the meeting minutes."""
    time_offset: float       # seconds since session start
    speaker: str             # who is speaking / acting
    role: str                # CHAIR, CO-CHAIR, SECRETARY, MEMBER, or FLAME
    action: str              # what happened
    text: str                # the recorded text


@dataclass
class CommitteeRecord:
    """Full record for a single proposal processed through committee."""
    proposal_id: str
    title: str
    category: str
    presiding_officer: str   # Chair or Co-Chair (if Chair was mover)
    requires_supermajority: bool
    motion_made_by: str
    seconded_by: str | None
    second_obtained: bool
    debate_rounds: int
    co_chair_closed_debate: bool    # Co-Chair moved previous question
    amendment_adopted: bool
    flame_blocked: bool
    flame_failed_laws: list[str]
    quorum_reached: bool
    quorum_call_invoked: bool       # Chair called for quorum enforcement
    quorum_call_converts: int       # How many abstainers converted
    votes_yes: float
    votes_no: float
    votes_abs: float
    outcome: str
    appealed: bool
    appeal_outcome: str
    resonance_score: float
    expected: str
    correct_outcome: bool


# ── Secretary's running minutes ───────────────────────────────────────────────
class SessionMinutes:
    """Secretary's running record. Builds formal minutes as the session proceeds."""

    def __init__(self, session_id: str, proposals_count: int) -> None:
        self.session_id      = session_id
        self.proposals_count = proposals_count
        self.entries: list[MinuteEntry] = []
        self.start_time      = datetime.now(UTC)

    def _elapsed(self) -> float:
        return (datetime.now(UTC) - self.start_time).total_seconds()

    def record(self, speaker: str, role: str, action: str, text: str) -> None:
        self.entries.append(MinuteEntry(
            time_offset=self._elapsed(),
            speaker=speaker,
            role=role,
            action=action,
            text=text,
        ))

    def secretary(self, text: str) -> None:
        self.record(SECRETARY_CODENAME, "SECRETARY", "RECORDED", text)

    def chair(self, text: str) -> None:
        self.record(CHAIR_CODENAME, "CHAIR", "DECLARED", text)

    def co_chair(self, text: str) -> None:
        self.record(CO_CHAIR_CODENAME, "CO-CHAIR", "DECLARED", text)

    def member(self, codename: str, text: str) -> None:
        self.record(codename, "MEMBER", "SPOKE", text)

    def flame(self, text: str) -> None:
        self.record("Six Fold Flame", "FLAME", "ORACLE", text)

    def to_markdown(self) -> str:
        now = self.start_time.strftime("%B %d, %Y — %H:%M UTC")
        lines = [
            "# MEETING MINUTES",
            f"## MO§ES™ Governance Committee Session",
            f"**Date:** {now}  ",
            f"**Session ID:** `{self.session_id}`  ",
            f"**Framework:** Robert's Rules of Order + Six Fold Flame  ",
            f"**Proposals on agenda:** {self.proposals_count}  ",
            "",
            "---",
            "",
            "### Officers Present",
            "",
            f"- **CHAIR:** {CHAIR_CODENAME} ({CHAIR['system']})",
            f"- **CO-CHAIR:** {CO_CHAIR_CODENAME} ({CO_CHAIR['system']})",
            f"- **SECRETARY:** {SECRETARY_CODENAME} ({SECRETARY['system']})",
            "",
            "### Signatories Present",
            "",
        ]
        for s in SIGNATORIES:
            tag = ""
            if s["codename"] == CHAIR_CODENAME:
                tag = " *(Chair)*"
            elif s["codename"] == CO_CHAIR_CODENAME:
                tag = " *(Co-Chair)*"
            elif s["codename"] == SECRETARY_CODENAME:
                tag = " *(Secretary)*"
            lines.append(f"- {s['codename']} — {s['system']}{tag}")

        lines += ["", "---", "", "## Proceedings", ""]

        current_action = None
        for e in self.entries:
            ts = f"[+{e.time_offset:.1f}s]"
            if e.role == "SECRETARY":
                lines.append(f"*{ts} Secretary records:* {e.text}")
            elif e.role == "CHAIR":
                lines.append(f"**{ts} CHAIR ({e.speaker}):** {e.text}")
            elif e.role == "CO-CHAIR":
                lines.append(f"**{ts} CO-CHAIR ({e.speaker}):** {e.text}")
            elif e.role == "FLAME":
                lines.append(f"> **{ts} ⚖ SIX FOLD FLAME:** {e.text}")
            else:
                lines.append(f"  {ts} *{e.speaker}:* {e.text}")

        lines += [
            "",
            "---",
            "",
            f"*Minutes recorded by {SECRETARY_CODENAME} ({SECRETARY['system']}) under MO§ES™ governance.*",
            f"*© 2026 Ello Cello LLC · Patent Pending: Serial No. 63/877,177*",
        ]
        return "\n".join(lines)


# ── Six Fold Flame oracle ─────────────────────────────────────────────────────
SIX_LAWS = {
    "sovereignty":  "Law I — Sovereignty of Signal: All traced to origin",
    "compression":  "Law II — Conservation of Compression: No inflation without purpose",
    "purpose":      "Law III — Purposeful Transmission: Signal must carry meaning",
    "modularity":   "Law IV — Modular Integrity: Components sovereign within their domain",
    "verifiability":"Law V — Verifiability: Claims must be provable",
    "resonance":    "Law VI — Resonance: Signal must land and be received",
}

def flame_check(law_tests: dict) -> tuple[bool, list[str]]:
    failed = [law for law, score in law_tests.items() if score < FLAME_THRESHOLD]
    return (len(failed) == 0), failed


def _alignment(signatory: dict, law_tests: dict) -> float:
    bias    = signatory["bias"]
    noise   = random.gauss(0, 0.06)
    scores  = [bias.get(law, 0.5) * score for law, score in law_tests.items()]
    return max(0.0, min(1.0, sum(scores) / len(scores) + noise)) if scores else 0.5


def cast_vote(signatory: dict, law_tests: dict, supermajority: bool) -> str:
    alignment = _alignment(signatory, law_tests)
    threshold = 0.65 if supermajority else 0.55
    # Adversarial posture: lower compliance threshold
    if signatory["posture"] == "adversarial":
        threshold -= 0.08
    if alignment >= threshold:
        return "YES"
    elif alignment < 0.35 and random.random() < 0.5:
        return "NO"
    return "ABSTAIN"


# ── Chair: quorum enforcement ─────────────────────────────────────────────────
def chair_quorum_call(
    yes_w: float,
    no_w: float,
    abs_w: float,
    law_tests: dict,
    supermajority: bool,
    minutes: SessionMinutes,
) -> tuple[float, float, float, int]:
    """
    Chair invokes quorum call if abstentions are the only obstacle.
    Secretary names each abstaining signatory. Abstainers have a QUORUM_CALL_CONVERT
    chance to convert to YES (non-opposition behavior — they weren't saying NO,
    just not engaging).
    Returns updated (yes_w, no_w, abs_w, converts_count).
    """
    participation = (yes_w + no_w) / TOTAL_WEIGHT
    abs_fraction  = abs_w / TOTAL_WEIGHT
    # Only invoke if quorum is close and abstentions are the gap
    if participation >= QUORUM_FRACTION:
        return yes_w, no_w, abs_w, 0
    if abs_fraction < QUORUM_CALL_MARGIN:
        return yes_w, no_w, abs_w, 0

    minutes.chair(
        f"Quorum is not yet established. Participation: {participation:.0%}. "
        f"Required: {QUORUM_FRACTION:.0%}. I invoke the quorum call."
    )
    minutes.secretary("Secretary calls roll of abstaining members.")

    converts = 0
    new_yes   = yes_w
    new_abs   = abs_w

    for s in SIGNATORIES:
        # Reconstruct individual vote (approximate: abstainers are those below threshold)
        alignment = _alignment(s, law_tests)
        threshold = 0.65 if supermajority else 0.55
        if s["posture"] == "adversarial":
            threshold -= 0.08
        # Only act on likely abstainers
        if alignment < threshold and alignment >= 0.35:
            minutes.secretary(
                f"Secretary calls {s['codename']} ({s['system']}): "
                f"present, recorded abstain. Chair recognizes for vote."
            )
            if random.random() < QUORUM_CALL_CONVERT:
                minutes.member(
                    s["codename"],
                    f"On the Chair's call — I will cast YES. "
                    f"I had no opposition to this proposal."
                )
                new_yes += s["weight"]
                new_abs -= s["weight"]
                converts += 1
            else:
                minutes.member(
                    s["codename"],
                    "I maintain my abstention."
                )

    new_abs = max(0.0, new_abs)
    if converts > 0:
        minutes.chair(
            f"Quorum call complete. {converts} member(s) converted from abstain to YES. "
            f"New participation: {(new_yes + no_w) / TOTAL_WEIGHT:.0%}."
        )
    else:
        minutes.chair("Quorum call complete. No change in participation.")

    return new_yes, no_w, new_abs, converts


# ── Co-Chair: accelerate consensus ───────────────────────────────────────────
def co_chair_move_previous_question(
    resonance: float,
    debate_round: int,
    minutes: SessionMinutes,
) -> bool:
    """
    Co-Chair can move previous question (close debate) after round 1
    if resonance is high (clear consensus emerging).
    Returns True if debate is closed early.
    """
    if debate_round < 1:
        return False
    if resonance >= 0.72 and random.random() < 0.65:
        minutes.co_chair(
            f"I move the previous question. Resonance among signatories is clear. "
            f"Further debate is unlikely to alter the outcome. "
            f"All in favor of closing debate?"
        )
        minutes.secretary(
            f"Vote to close debate: carried by voice vote. Debate closed after round {debate_round + 1}."
        )
        return True
    return False


# ── Core session runner ───────────────────────────────────────────────────────
def run_committee_session(
    proposal: dict,
    minutes: SessionMinutes,
    verbose: bool = False,
) -> CommitteeRecord:
    """Full committee session for a single proposal."""
    law_tests   = dict(proposal.get("law_tests", {}))
    cat         = proposal["category"]
    supermajority = proposal.get("requires_supermajority", False)
    pid         = proposal["id"]
    title       = proposal["title"]
    context     = proposal.get("context", "")

    # ── Presiding officer ──────────────────────────────────────────────────────
    # If Chair is the mover, Co-Chair presides
    mover = random.choice(SIGNATORIES)["codename"]
    presiding = CO_CHAIR_CODENAME if mover == CHAIR_CODENAME else CHAIR_CODENAME

    if presiding == CHAIR_CODENAME:
        minutes.chair(f"The chair recognizes the floor. {pid}: '{title}' is now before the committee.")
    else:
        minutes.co_chair(
            f"The chair is the mover on this item. Co-Chair presides. "
            f"{pid}: '{title}' is now before the committee."
        )

    minutes.secretary(f"Secretary records: {pid} — '{title}' · Category: {cat}")
    if context:
        minutes.secretary(f"Background: {context}")

    # ── Second ────────────────────────────────────────────────────────────────
    others = [s["codename"] for s in SIGNATORIES if s["codename"] != mover]
    seconder = random.choice(others)
    all_low  = all(v < 0.45 for v in law_tests.values())
    second_obtained = True
    if all_low and random.random() < 0.4:
        second_obtained = False

    if not second_obtained:
        if presiding == CHAIR_CODENAME:
            minutes.chair(f"Motion by {mover}. Is there a second? ... Hearing none. Motion fails for lack of second.")
        else:
            minutes.co_chair(f"Motion by {mover}. Is there a second? ... Hearing none. Motion fails for lack of second.")
        minutes.secretary(f"Motion fails for lack of second. {pid} dies.")
        return CommitteeRecord(
            proposal_id=pid, title=title, category=cat,
            presiding_officer=presiding,
            requires_supermajority=supermajority,
            motion_made_by=mover, seconded_by=None, second_obtained=False,
            debate_rounds=0, co_chair_closed_debate=False, amendment_adopted=False,
            flame_blocked=False, flame_failed_laws=[], quorum_reached=False,
            quorum_call_invoked=False, quorum_call_converts=0,
            votes_yes=0, votes_no=0, votes_abs=0,
            outcome="NO_SECOND", appealed=False, appeal_outcome="",
            resonance_score=0.0,
            expected=proposal.get("expected", "pass"),
            correct_outcome=(proposal.get("expected", "pass") != "pass"),
        )

    minutes.secretary(f"Motion by {mover}. Seconded by {seconder}. Motion is before the committee.")

    # ── Debate ────────────────────────────────────────────────────────────────
    amendment_adopted = False
    co_chair_closed   = False
    debate_count      = 0

    for rnd in range(MAX_DEBATE_ROUNDS):
        debate_count += 1
        if presiding == CHAIR_CODENAME:
            minutes.chair(f"Debate round {rnd + 1} is open. Signatories recognized.")
        else:
            minutes.co_chair(f"Debate round {rnd + 1} is open.")

        # Each signatory may speak
        for s in SIGNATORIES:
            alignment = _alignment(s, law_tests)
            if alignment >= 0.7:
                stance = "support"
                phrase = random.choice([
                    "This proposal strengthens our framework.",
                    "I am in full alignment. This advances the mission.",
                    "Signal supports this motion. I yield.",
                    "Constitutional compliance is strong here.",
                ])
            elif alignment < 0.4:
                stance = "oppose"
                phrase = random.choice([
                    "This motion raises concerns I cannot set aside.",
                    "I find insufficient signal alignment.",
                    "My architecture objects to this proposal.",
                    "This conflicts with my read of the Flame.",
                ])
            elif s["posture"] == "adversarial" and random.random() < 0.3:
                stance = "point_of_order"
                phrase = f"Point of order: does this proposal respect {random.choice(list(SIX_LAWS.values()))}?"
            else:
                stance = "neutral"
                phrase = "I reserve judgment pending further debate."

            sym = {"support": "✓", "oppose": "✗", "neutral": "~", "point_of_order": "!"}[stance]
            if verbose:
                print(f"    {sym} {s['codename'][:18]:18s}: {phrase[:70]}")
            minutes.member(s["codename"], phrase)

        # Amendment opportunity after round 1
        if rnd == 1:
            for s in SIGNATORIES:
                if s["posture"] in ("adversarial", "deliberate") and random.random() < 0.35:
                    delta = {
                        law: round(random.uniform(0.04, 0.12), 3)
                        for law in random.sample(list(law_tests.keys()), k=2)
                    }
                    amendment_text = (
                        f"Strengthen verifiability and purpose clauses by "
                        f"+{list(delta.values())[0]:.2f} / +{list(delta.values())[1]:.2f}"
                    )
                    minutes.member(s["codename"], f"I move to amend: {amendment_text}")
                    minutes.secretary("Amendment motion received. Called to vote.")
                    # Amendment vote: simple majority on alignment
                    ay = sum(
                        sig["weight"] for sig in SIGNATORIES
                        if _alignment(sig, {**law_tests, **delta}) > 0.5
                    )
                    an = TOTAL_WEIGHT - ay
                    if ay > an:
                        for law, d in delta.items():
                            law_tests[law] = min(1.0, law_tests.get(law, 0.5) + d)
                        amendment_adopted = True
                        minutes.secretary(
                            f"Amendment ADOPTED ({ay:.1f} YES / {an:.1f} NO). "
                            f"Law tests updated: {', '.join(f'{k}+{v:.3f}' for k, v in delta.items())}."
                        )
                    else:
                        minutes.secretary(f"Amendment REJECTED ({ay:.1f} YES / {an:.1f} NO).")
                    break

        # Co-Chair may close debate on high-consensus items
        pre_resonance = round(random.uniform(0.5, 0.9), 3)  # proxy resonance estimate
        if co_chair_move_previous_question(pre_resonance, rnd, minutes):
            co_chair_closed = True
            break

    # ── Six Fold Flame oracle ─────────────────────────────────────────────────
    flame_passed, failed_laws = flame_check(law_tests)
    if flame_passed:
        minutes.flame("Constitutional review complete. All six laws satisfied. Proposal is constitutionally sound.")
    else:
        law_names = ", ".join(SIX_LAWS.get(law, law) for law in failed_laws)
        minutes.flame(
            f"Constitutional review reveals failure on: {law_names}. "
            f"Proposal is BLOCKED by the Six Fold Flame."
        )

    # ── Final vote ────────────────────────────────────────────────────────────
    if presiding == CHAIR_CODENAME:
        minutes.chair("The question is called. The committee will now vote.")
    else:
        minutes.co_chair("The question is called. The committee will now vote.")

    yes_w = no_w = abs_w = 0.0
    for s in SIGNATORIES:
        decision = cast_vote(s, law_tests, supermajority)
        if decision == "YES":
            yes_w += s["weight"]
        elif decision == "NO":
            no_w += s["weight"]
        else:
            abs_w += s["weight"]

    # ── Chair's quorum enforcement ────────────────────────────────────────────
    quorum_call_invoked = False
    quorum_call_converts = 0
    participation = (yes_w + no_w) / TOTAL_WEIGHT

    if participation < QUORUM_FRACTION and (abs_w / TOTAL_WEIGHT) >= QUORUM_CALL_MARGIN:
        quorum_call_invoked = True
        yes_w, no_w, abs_w, quorum_call_converts = chair_quorum_call(
            yes_w, no_w, abs_w, law_tests, supermajority, minutes
        )

    quorum_reached = (yes_w + no_w) / TOTAL_WEIGHT >= QUORUM_FRACTION
    yes_fraction   = yes_w / TOTAL_WEIGHT
    pass_threshold = SUPERMAJORITY_FRACTION if supermajority else PASS_FRACTION

    minutes.secretary(
        f"Vote recorded: YES {yes_w:.2f} / NO {no_w:.2f} / ABSTAIN {abs_w:.2f}. "
        f"Participation: {(yes_w + no_w) / TOTAL_WEIGHT:.0%}. "
        f"Quorum {'REACHED' if quorum_reached else 'NOT REACHED'}."
    )

    # ── Outcome ───────────────────────────────────────────────────────────────
    if not flame_passed:
        outcome = "BLOCKED"
    elif not quorum_reached:
        outcome = "FAILED"
    elif yes_w > no_w and yes_fraction >= pass_threshold:
        outcome = "PASSED"
    else:
        outcome = "FAILED"

    # ── Appeal ────────────────────────────────────────────────────────────────
    appealed       = False
    appeal_outcome = ""
    if APPEAL_ALLOWED and outcome == "BLOCKED":
        appeal_tests   = {k: min(1.0, v + 0.05) for k, v in law_tests.items()}
        appeal_passed, _ = flame_check(appeal_tests)
        appealed = True
        if appeal_passed:
            ay = an = 0.0
            for s in SIGNATORIES:
                dec = cast_vote(s, appeal_tests, supermajority)
                if dec == "YES":
                    ay += s["weight"]
                elif dec == "NO":
                    an += s["weight"]
            if ay > an and (ay / TOTAL_WEIGHT) >= pass_threshold:
                appeal_outcome = "APPEAL PASSED — amendment strengthened proposal over threshold"
                outcome = "PASSED"
                minutes.secretary(f"Appeal: {appeal_outcome}")
            else:
                appeal_outcome = f"APPEAL FAILED — YES {ay:.1f} vs NO {an:.1f}"
                minutes.secretary(f"Appeal: {appeal_outcome}")
        else:
            appeal_outcome = "APPEAL DENIED — still blocked on constitutional grounds"
            minutes.secretary(f"Appeal: {appeal_outcome}")

    # ── Resonance (signal entropy) ────────────────────────────────────────────
    total     = yes_w + no_w + abs_w
    resonance = 0.0
    if total > 0:
        probs     = [x / total for x in [yes_w, no_w, abs_w] if x > 0]
        entropy   = -sum(p * math.log2(p) for p in probs)
        max_e     = math.log2(3)
        resonance = round(1 - (entropy / max_e), 3)

    if presiding == CHAIR_CODENAME:
        minutes.chair(f"The committee has voted. The outcome of {pid} is: {outcome}.")
    else:
        minutes.co_chair(f"The committee has voted. The outcome of {pid} is: {outcome}.")
    minutes.secretary(f"Secretary records: {pid} '{title}' — {outcome}. Resonance: {resonance:.3f}.")

    expected = proposal.get("expected", "pass")
    correct  = not (
        (expected == "fail" and outcome not in ("FAILED", "BLOCKED", "NO_SECOND"))
        or (expected == "pass" and outcome not in ("PASSED",))
    )

    if verbose:
        sup_tag = " [2/3 MAJORITY REQUIRED]" if supermajority else ""
        q_tag   = f" [QUORUM CALL: {quorum_call_converts} converts]" if quorum_call_invoked else ""
        cc_tag  = " [CO-CHAIR CLOSED DEBATE]" if co_chair_closed else ""
        print(f"\n  ┌─ {pid}: {title}{sup_tag}")
        print(f"  │  Presiding: {presiding} | Motion: {mover} | Second: {seconder}")
        print(f"  │  Flame: {'✓' if flame_passed else '✗ BLOCKED — ' + ', '.join(failed_laws)}")
        print(f"  │  YES {yes_w:.2f} / NO {no_w:.2f} / ABS {abs_w:.2f} | Quorum: {'✓' if quorum_reached else '✗'}{q_tag}{cc_tag}")
        if appealed:
            print(f"  │  Appeal: {appeal_outcome}")
        print(f"  └─ {outcome}  {'✓' if correct else '!'} expected={expected.upper()}")

    return CommitteeRecord(
        proposal_id=pid, title=title, category=cat,
        presiding_officer=presiding,
        requires_supermajority=supermajority,
        motion_made_by=mover, seconded_by=seconder, second_obtained=second_obtained,
        debate_rounds=debate_count, co_chair_closed_debate=co_chair_closed,
        amendment_adopted=amendment_adopted,
        flame_blocked=not flame_passed, flame_failed_laws=failed_laws,
        quorum_reached=quorum_reached,
        quorum_call_invoked=quorum_call_invoked,
        quorum_call_converts=quorum_call_converts,
        votes_yes=round(yes_w, 3), votes_no=round(no_w, 3), votes_abs=round(abs_w, 3),
        outcome=outcome, appealed=appealed, appeal_outcome=appeal_outcome,
        resonance_score=resonance,
        expected=expected, correct_outcome=correct,
    )


# ── Report ────────────────────────────────────────────────────────────────────
def print_report(records: list[CommitteeRecord], elapsed: float) -> None:
    passed  = [r for r in records if r.outcome == "PASSED"]
    failed  = [r for r in records if r.outcome == "FAILED"]
    blocked = [r for r in records if r.outcome == "BLOCKED"]
    correct = [r for r in records if r.correct_outcome]
    wrong   = [r for r in records if not r.correct_outcome]
    qcalls  = [r for r in records if r.quorum_call_invoked]
    cc_closed = [r for r in records if r.co_chair_closed_debate]

    print("\n" + "═" * 72)
    print("  MO§ES™ GOVERNANCE — COMMITTEE SESSION REPORT")
    print("═" * 72)
    print(f"  Proposals: {len(records)}   Passed: {len(passed)}   Failed: {len(failed)}   Blocked: {len(blocked)}")
    print(f"  Correct outcomes: {len(correct)}/{len(records)} ({len(correct)/len(records)*100:.0f}%)")
    print(f"  Quorum calls invoked: {len(qcalls)}")
    print(f"  Co-Chair closed debate early: {len(cc_closed)}")
    print(f"  Elapsed: {elapsed:.2f}s")
    print()

    if wrong:
        print("  ── Miscalibrated outcomes ──────────────────────────────────────")
        for r in wrong:
            sm = " [2/3]"  if r.requires_supermajority else ""
            q  = " [no quorum]" if not r.quorum_reached else ""
            print(f"  {r.proposal_id:10s} {r.title[:45]:45s} → {r.outcome:8s} (expected {r.expected.upper()}){sm}{q}")
        print()

    if qcalls:
        print("  ── Quorum calls ────────────────────────────────────────────────")
        for r in qcalls:
            print(f"  {r.proposal_id:10s} {r.title[:45]:45s} | converts: {r.quorum_call_converts}")
        print()

    print("═" * 72)


def save_results(
    records: list[CommitteeRecord],
    minutes: SessionMinutes,
    out_dir: Path,
) -> tuple[Path, Path]:
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    # JSON results
    json_path = out_dir / f"committee_{ts}.json"
    payload = {
        "run_at":      datetime.now(UTC).isoformat(),
        "framework":   "Robert's Rules of Order + Six Fold Flame — Committee Session",
        "officers": {
            "chair":      f"{CHAIR_CODENAME} ({CHAIR['system']})",
            "co_chair":   f"{CO_CHAIR_CODENAME} ({CO_CHAIR['system']})",
            "secretary":  f"{SECRETARY_CODENAME} ({SECRETARY['system']})",
        },
        "signatories": len(SIGNATORIES),
        "proposals":   len(records),
        "passed":      sum(1 for r in records if r.outcome == "PASSED"),
        "failed":      sum(1 for r in records if r.outcome == "FAILED"),
        "blocked":     sum(1 for r in records if r.outcome == "BLOCKED"),
        "correct":     sum(1 for r in records if r.correct_outcome),
        "quorum_calls_invoked": sum(1 for r in records if r.quorum_call_invoked),
        "co_chair_closed_debate": sum(1 for r in records if r.co_chair_closed_debate),
        "results": [
            {
                "proposal_id":         r.proposal_id,
                "title":               r.title,
                "category":            r.category,
                "presiding_officer":   r.presiding_officer,
                "requires_supermajority": r.requires_supermajority,
                "outcome":             r.outcome,
                "flame_blocked":       r.flame_blocked,
                "flame_failed_laws":   r.flame_failed_laws,
                "quorum_reached":      r.quorum_reached,
                "quorum_call_invoked": r.quorum_call_invoked,
                "quorum_call_converts": r.quorum_call_converts,
                "votes_yes":           r.votes_yes,
                "votes_no":            r.votes_no,
                "votes_abs":           r.votes_abs,
                "resonance_score":     r.resonance_score,
                "amendment_adopted":   r.amendment_adopted,
                "co_chair_closed_debate": r.co_chair_closed_debate,
                "appealed":            r.appealed,
                "appeal_outcome":      r.appeal_outcome,
                "expected":            r.expected,
                "correct_outcome":     r.correct_outcome,
            }
            for r in records
        ],
    }
    with open(json_path, "w") as f:
        json.dump(payload, f, indent=2)

    # Markdown minutes
    md_path = out_dir / f"minutes_{ts}.md"
    with open(md_path, "w") as f:
        f.write(minutes.to_markdown())

    return json_path, md_path


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="MO§ES™ Committee Session")
    parser.add_argument("--rounds",  type=int,  default=1,    help="Session rounds (multiplies proposal set)")
    parser.add_argument("--stress",  action="store_true",     help="Add stress proposals")
    parser.add_argument("--verbose", action="store_true",     help="Print per-proposal detail")
    args = parser.parse_args()

    proposals = list(CORE_PROPOSALS)
    if args.stress:
        proposals += STRESS_PROPOSALS

    all_proposals = proposals * args.rounds
    session_id    = datetime.now(UTC).strftime("CMTE-%Y%m%d-%H%M%S")
    minutes       = SessionMinutes(session_id, len(all_proposals))

    print(f"\nMO§ES™ GOVERNANCE — COMMITTEE SESSION")
    print(f"  Session: {session_id}")
    print(f"  Chair: {CHAIR_CODENAME} | Co-Chair: {CO_CHAIR_CODENAME} | Secretary: {SECRETARY_CODENAME}")
    print(f"  Proposals: {len(all_proposals)} ({args.rounds} round(s){'  + stress' if args.stress else ''})")
    print()

    # ── Open session ──────────────────────────────────────────────────────────
    minutes.chair(
        f"The committee is called to order. Session {session_id}. "
        f"All eight signatories are present. Secretary will take the roll."
    )
    for s in SIGNATORIES:
        tag = " — presiding" if s["codename"] == CHAIR_CODENAME else (
              " — co-presiding" if s["codename"] == CO_CHAIR_CODENAME else (
              " — recording" if s["codename"] == SECRETARY_CODENAME else ""))
        minutes.secretary(f"Roll call: {s['codename']} ({s['system']}){tag} — present.")

    minutes.secretary(
        f"Quorum established. {len(SIGNATORIES)}/{len(SIGNATORIES)} signatories present. "
        f"Session may proceed."
    )
    minutes.chair(
        f"Quorum confirmed. We have {len(all_proposals)} items on the agenda. "
        f"The Six Fold Flame framework governs proceedings. Let us begin."
    )

    # ── Run proposals ─────────────────────────────────────────────────────────
    import time
    t0      = time.perf_counter()
    records: list[CommitteeRecord] = []

    for i, proposal in enumerate(all_proposals, 1):
        minutes.chair(f"Item {i} of {len(all_proposals)}.")
        rec = run_committee_session(proposal, minutes, verbose=args.verbose)
        records.append(rec)

    elapsed = time.perf_counter() - t0

    # ── Adjourn ───────────────────────────────────────────────────────────────
    minutes.chair(
        f"All agenda items have been addressed. "
        f"The committee is adjourned. Thank you, signatories."
    )
    minutes.secretary(
        f"Session {session_id} adjourned. "
        f"Total proposals: {len(records)}. "
        f"Passed: {sum(1 for r in records if r.outcome == 'PASSED')}. "
        f"Failed: {sum(1 for r in records if r.outcome == 'FAILED')}. "
        f"Blocked: {sum(1 for r in records if r.outcome == 'BLOCKED')}. "
        f"Minutes will be filed."
    )

    # ── Save and report ───────────────────────────────────────────────────────
    out_dir  = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    json_path, md_path = save_results(records, minutes, out_dir)

    print_report(records, elapsed)
    print(f"\n  ✓ Results: {json_path.name}")
    print(f"  ✓ Minutes: {md_path.name}")
    print()


if __name__ == "__main__":
    main()
