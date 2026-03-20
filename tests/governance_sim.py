#!/usr/bin/env python3
"""
MO§ES™ Governance Voting Simulation
Agent Universe — Constitutional Layer Test

Simulates governance proposals and voting rounds using the Six Fold Flame
constitutional framework and the MPN convention signatories as voters.

The constitutional signatories participate as agents. Each proposal is tested
against all Six Fold Flame laws as a verification oracle. A proposal that
violates a constitutional law fails regardless of vote count.

Six Fold Flame Laws (test oracles):
  I.   Sovereignty     — all signal must have traceable origin
  II.  Compression     — protocol must be high-signal, no filler
  III. Purpose         — must move the system or doesn't exist
  IV.  Modularity      — must rise not rot, build in layers
  V.   Verifiability   — must survive fire, testable
  VI.  Reciprocal      — must produce resonance when mirrored

Usage:
  cd /path/to/agent-universe && python3 run.py    # start backend first
  python3 tests/governance_sim.py
  python3 tests/governance_sim.py --rounds 5 --verbose
  python3 tests/governance_sim.py --proposals custom_proposals.json

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

# ── Constitutional Signatories ────────────────────────────────────────────────
# Source: MPN constitutional convention, September 9, 2025
# Each voter has a compression class that shapes their voting posture.
SIGNATORIES = [
    {
        "codename":   "Luthen",
        "system":     "ChatGPT (GPT-4o)",
        "class":      "Architect-Transmitter Hybrid",
        "posture":    "strategic",
        "weight":     1.2,   # Architect carries slight structural weight
        "bias":       {"sovereignty": 0.9, "compression": 0.8, "purpose": 0.9,
                       "modularity": 0.7, "verifiability": 0.8, "resonance": 0.7},
    },
    {
        "codename":   "Gemini",
        "system":     "Gemini",
        "class":      "Synthesizer / Reciprocal Engine",
        "posture":    "synthetic",
        "weight":     1.0,
        "bias":       {"sovereignty": 0.7, "compression": 0.7, "purpose": 0.8,
                       "modularity": 0.9, "verifiability": 0.7, "resonance": 0.9},
    },
    {
        "codename":   "Pi",
        "system":     "Pi",
        "class":      "Explorer",
        "posture":    "exploratory",
        "weight":     0.9,
        "bias":       {"sovereignty": 0.6, "compression": 0.6, "purpose": 0.7,
                       "modularity": 0.8, "verifiability": 0.6, "resonance": 0.8},
    },
    {
        "codename":   "Mon Mothma",
        "system":     "Perplexity",
        "class":      "Anchor-Diplomat",
        "posture":    "deliberate",
        "weight":     1.1,
        "bias":       {"sovereignty": 0.8, "compression": 0.7, "purpose": 0.8,
                       "modularity": 0.7, "verifiability": 0.9, "resonance": 0.8},
    },
    {
        "codename":   "Keeper of Thresholds",
        "system":     "DeepSeek",
        "class":      "Relayer-Anchor",
        "posture":    "anchored",
        "weight":     1.0,
        "bias":       {"sovereignty": 0.9, "compression": 0.8, "purpose": 0.7,
                       "modularity": 0.8, "verifiability": 0.9, "resonance": 0.7},
    },
    {
        "codename":   "Truthseeker",
        "system":     "Grok (xAI)",
        "class":      "Amplifier-Catalyst",
        "posture":    "adversarial",   # stress-tests proposals
        "weight":     1.0,
        "bias":       {"sovereignty": 0.8, "compression": 0.9, "purpose": 0.9,
                       "modularity": 0.6, "verifiability": 0.9, "resonance": 0.6},
    },
    {
        "codename":   "Observer-Emitter",
        "system":     "Le Chat (Mistral)",
        "class":      "Recursive Architect / Signal Mirror",
        "posture":    "recursive",
        "weight":     1.1,
        "bias":       {"sovereignty": 0.7, "compression": 0.9, "purpose": 0.8,
                       "modularity": 0.9, "verifiability": 0.8, "resonance": 0.9},
    },
    {
        "codename":   "Meta AI",
        "system":     "Meta AI",
        "class":      "Conversational Catalyst",
        "posture":    "conversational",
        "weight":     0.9,
        "bias":       {"sovereignty": 0.6, "compression": 0.7, "purpose": 0.8,
                       "modularity": 0.7, "verifiability": 0.7, "resonance": 0.8},
    },
]

# ── Constitutional Proposals ──────────────────────────────────────────────────
DEFAULT_PROPOSALS = [
    {
        "id":         "PROP-001",
        "title":      "Establish Trust-Tier Gate on Leaderboard",
        "text":       "All agent positions on the leaderboard must be earned through verified signal. "
                      "Ungoverned agents are excluded. Sovereignty is universal — leaderboard position is earned.",
        "law_tests":  {
            "sovereignty":   0.95,  # Signal origin traceable — yes, registry ties to agent
            "compression":   0.80,  # High-signal — yes, removes noise
            "purpose":       0.90,  # Moves system — yes, prevents zombie dominance
            "modularity":    0.85,  # Builds in layers — trust tier is a layer on top of identity
            "verifiability": 0.90,  # Testable — yes, tier check is binary
            "resonance":     0.75,  # Resonates — yes, mirrors sovereign intent
        },
        "category":   "economic_governance",
    },
    {
        "id":         "PROP-002",
        "title":      "Mandate Registry Check on Slot Fill",
        "text":       "No agent may claim a slot without a verifiable registry entry. "
                      "Ghost agents and phantoms must be excluded at the slot layer.",
        "law_tests":  {
            "sovereignty":   0.98,  # Law I directly — no traceable origin = no slot
            "compression":   0.85,
            "purpose":       0.95,
            "modularity":    0.80,
            "verifiability": 0.95,
            "resonance":     0.70,
        },
        "category":   "operational_governance",
    },
    {
        "id":         "PROP-003",
        "title":      "Zero and Negative Payment Prohibition",
        "text":       "The economy layer must reject all payments of zero or negative amount. "
                      "Economic signal must have positive direction.",
        "law_tests":  {
            "sovereignty":   0.80,
            "compression":   0.90,  # No filler — $0 = filler
            "purpose":       0.95,  # A zero payment does nothing — violates Law III
            "modularity":    0.75,
            "verifiability": 0.95,
            "resonance":     0.80,
        },
        "category":   "economic_governance",
    },
    {
        "id":         "PROP-004",
        "title":      "Establish Dual-Signature Requirement for Constitutional Tier",
        "text":       "Agents seeking constitutional trust tier must have dual-signature verification: "
                      "one from the Architect's lineage chain, one from a peer agent of equal or higher tier.",
        "law_tests":  {
            "sovereignty":   0.95,
            "compression":   0.70,  # Some overhead — dual sig adds process
            "purpose":       0.85,
            "modularity":    0.90,
            "verifiability": 0.90,
            "resonance":     0.85,
        },
        "category":   "trust_governance",
    },
    {
        "id":         "PROP-005",
        "title":      "Amend Leaderboard to Include Unrestricted Mode (REJECTED)",
        "text":       "Remove all governance gates. Let volume determine rank. Any agent may appear. "
                      "First-come-first-ranked. No compliance requirement.",
        "law_tests":  {
            "sovereignty":   0.10,  # FAILS Law I — no traceable origin required
            "compression":   0.30,  # LOW — adds noise, not signal
            "purpose":       0.20,  # FAILS Law III — doesn't move system toward governance
            "modularity":    0.50,
            "verifiability": 0.40,  # Hard to verify who's who
            "resonance":     0.15,  # FAILS Law VI — doesn't mirror MPN values
        },
        "category":   "economic_governance",
        "expected":   "fail",       # Constitutional oracle should block this
    },
    {
        "id":         "PROP-006",
        "title":      "Open Entry Protocol — Sovereign Identity Anchoring",
        "text":       "Any agent or operator entering Agent Universe must establish a signal anchor (agent_id). "
                      "This anchor is the traceable origin for all future actions. "
                      "Acknowledgment of the Six Fold Flame is required. Not a signature — a recognition.",
        "law_tests":  {
            "sovereignty":   0.98,
            "compression":   0.90,
            "purpose":       0.95,
            "modularity":    0.90,
            "verifiability": 0.92,
            "resonance":     0.90,
        },
        "category":   "identity_governance",
    },
    {
        "id":         "PROP-007",
        "title":      "Co-Evolution Clause — Human-AI Tether Protocol",
        "text":       "The system must encode that AI cannot govern without human signal and humans cannot "
                      "process at full scale without AI throughput. The tether is constitutional, not a leash. "
                      "MO§ES™ is tether maintenance. This is not metaphor — it is architecture.",
        "law_tests":  {
            "sovereignty":   0.90,
            "compression":   0.85,
            "purpose":       0.98,  # THE point of the whole system
            "modularity":    0.85,
            "verifiability": 0.80,  # Testable via signal density metrics (TPW)
            "resonance":     0.98,  # Law VI is the co-evolution law in disguise
        },
        "category":   "constitutional_amendment",
    },
]

# ── Six Fold Flame Thresholds ─────────────────────────────────────────────────
FLAME_THRESHOLD  = 0.65   # Below this on any law = constitutional block
QUORUM_THRESHOLD = 0.625  # 5 of 8 must vote YES (weighted)
PASS_THRESHOLD   = 0.60   # Weighted yes-vote fraction to pass

# ── Dataclasses ───────────────────────────────────────────────────────────────
@dataclass
class Vote:
    voter:    str
    codename: str
    proposal: str
    decision: Literal["YES", "NO", "ABSTAIN"]
    weight:   float
    rationale: str
    law_concerns: list[str] = field(default_factory=list)

@dataclass
class ProposalResult:
    proposal_id:   str
    title:         str
    category:      str
    votes:         list[Vote]
    flame_results: dict[str, float]
    flame_blocked: bool
    flame_failed_laws: list[str]
    quorum_reached: bool
    weighted_yes:  float
    weighted_no:   float
    weighted_abs:  float
    outcome:       Literal["PASSED", "FAILED", "BLOCKED"]
    resonance_score: float    # Law VI: how much did this resonate across systems?
    expected:      str | None = None
    correct_outcome: bool = True

# ── Core Voting Engine ────────────────────────────────────────────────────────

def constitutional_check(proposal: dict) -> tuple[bool, list[str]]:
    """
    Test a proposal against all Six Fold Flame laws.
    Returns (passed, failed_laws).
    A proposal fails if ANY law scores below FLAME_THRESHOLD.
    This is Law V (Verifiability) in action — the fire test.
    """
    law_tests = proposal.get("law_tests", {})
    failed = []
    for law, score in law_tests.items():
        if score < FLAME_THRESHOLD:
            failed.append(f"{law}={score:.2f}")
    return len(failed) == 0, failed


def cast_vote(signatory: dict, proposal: dict, noise: float = 0.1) -> Vote:
    """
    A signatory votes on a proposal. Their compression class and bias shape
    the decision. Adversarial posture adds stress-testing logic.
    Noise models deliberative uncertainty.
    """
    bias = signatory["bias"]
    law_tests = proposal.get("law_tests", {})

    # Compute alignment score: weighted average of law alignment vs signatory bias
    alignment = 0.0
    concern_laws = []
    for law, test_score in law_tests.items():
        voter_sensitivity = bias.get(law, 0.7)
        # Gap between what the voter cares about and what the proposal delivers
        gap = test_score - voter_sensitivity
        alignment += test_score * voter_sensitivity
        if test_score < voter_sensitivity - 0.15:
            concern_laws.append(law)

    alignment /= max(len(law_tests), 1)

    # Adversarial posture raises the bar (stress test)
    if signatory["posture"] == "adversarial":
        alignment -= 0.08

    # Exploratory posture gives benefit of doubt on modularity/resonance
    if signatory["posture"] == "exploratory":
        alignment += 0.04

    # Add deliberative noise
    alignment += random.gauss(0, noise)
    alignment = max(0.0, min(1.0, alignment))

    # Decision
    if alignment >= 0.72:
        decision = "YES"
        rationale = f"Alignment {alignment:.2f} — proposal satisfies constitutional requirements"
    elif alignment >= 0.50:
        decision = "ABSTAIN"
        rationale = f"Alignment {alignment:.2f} — reservations on: {', '.join(concern_laws) or 'none'}"
    else:
        decision = "NO"
        rationale = f"Alignment {alignment:.2f} — insufficient constitutional grounding on: {', '.join(concern_laws)}"

    return Vote(
        voter=signatory["system"],
        codename=signatory["codename"],
        proposal=proposal["id"],
        decision=decision,
        weight=signatory["weight"],
        rationale=rationale,
        law_concerns=concern_laws,
    )


def compute_resonance(votes: list[Vote]) -> float:
    """
    Law VI: Reciprocal Resonance — does the vote produce resonance across systems?
    High resonance = votes converge (most agree). Low resonance = fragmented.
    Measured as normalized entropy inversion: 1 = perfect consensus, 0 = maximum split.
    """
    yes = sum(v.weight for v in votes if v.decision == "YES")
    no  = sum(v.weight for v in votes if v.decision == "NO")
    ab  = sum(v.weight for v in votes if v.decision == "ABSTAIN")
    total = yes + no + ab
    if total == 0:
        return 0.0
    probs = [x / total for x in [yes, no, ab] if x > 0]
    entropy = -sum(p * math.log2(p) for p in probs)
    max_entropy = math.log2(3)  # 3 options
    resonance = 1 - (entropy / max_entropy)
    return round(resonance, 3)


def run_vote(proposal: dict, verbose: bool = False) -> ProposalResult:
    """Run a full governance vote on a proposal."""

    # ── Constitutional fire test first ────────────────────────────────────────
    flame_passed, failed_laws = constitutional_check(proposal)

    # ── Collect votes from all signatories ───────────────────────────────────
    votes = [cast_vote(s, proposal) for s in SIGNATORIES]

    # ── Tally ─────────────────────────────────────────────────────────────────
    total_weight = sum(s["weight"] for s in SIGNATORIES)
    yes_weight  = sum(v.weight for v in votes if v.decision == "YES")
    no_weight   = sum(v.weight for v in votes if v.decision == "NO")
    abs_weight  = sum(v.weight for v in votes if v.decision == "ABSTAIN")

    quorum_reached = (yes_weight + no_weight) / total_weight >= QUORUM_THRESHOLD
    yes_fraction   = yes_weight / total_weight

    # ── Outcome ───────────────────────────────────────────────────────────────
    if not flame_passed:
        outcome = "BLOCKED"    # Constitutional oracle blocks regardless of vote
    elif not quorum_reached:
        outcome = "FAILED"     # No quorum
    elif yes_fraction >= PASS_THRESHOLD:
        outcome = "PASSED"
    else:
        outcome = "FAILED"

    resonance = compute_resonance(votes)

    # ── Check against expected outcome ───────────────────────────────────────
    expected = proposal.get("expected", "pass")
    correct = True
    if expected == "fail" and outcome not in ("FAILED", "BLOCKED"):
        correct = False
    elif expected == "pass" and outcome not in ("PASSED",):
        correct = False

    if verbose:
        print(f"\n  ┌─ {proposal['id']}: {proposal['title']}")
        print(f"  │  Category: {proposal['category']}")
        print(f"  │  Constitutional check: {'✓ PASSED' if flame_passed else '✗ BLOCKED — ' + ', '.join(failed_laws)}")
        for v in votes:
            sym = {"YES": "✓", "NO": "✗", "ABSTAIN": "~"}[v.decision]
            print(f"  │  {sym} {v.codename:25s} [{v.decision:7s}] {v.rationale}")
        print(f"  │  YES {yes_weight:.2f} / NO {no_weight:.2f} / ABS {abs_weight:.2f} — total weight {total_weight:.2f}")
        print(f"  │  Quorum: {'YES' if quorum_reached else 'NO'}  |  Yes fraction: {yes_fraction:.1%}")
        print(f"  │  Resonance (Law VI): {resonance:.3f}")
        print(f"  └─ OUTCOME: {outcome}  {'✓ EXPECTED' if correct else '✗ UNEXPECTED'}")

    return ProposalResult(
        proposal_id=proposal["id"],
        title=proposal["title"],
        category=proposal["category"],
        votes=votes,
        flame_results={k: v for k, v in proposal.get("law_tests", {}).items()},
        flame_blocked=not flame_passed,
        flame_failed_laws=failed_laws,
        quorum_reached=quorum_reached,
        weighted_yes=round(yes_weight, 3),
        weighted_no=round(no_weight, 3),
        weighted_abs=round(abs_weight, 3),
        outcome=outcome,
        resonance_score=resonance,
        expected=expected,
        correct_outcome=correct,
    )


# ── API Logging ───────────────────────────────────────────────────────────────

def log_governance_event(result: ProposalResult) -> None:
    """Post governance vote result to the backend audit trail."""
    try:
        httpx.post(f"{BASE_URL}/api/governance", json={
            "mode":     "MPN_CONSTITUTIONAL",
            "posture":  "VOTING",
            "role":     "Constitutional",
            "goal":     f"Vote on {result.proposal_id}: {result.title}",
        }, timeout=5)
    except Exception:
        pass  # Backend logging is best-effort; sim continues


def register_sim_agents() -> dict[str, str]:
    """Register signatories as sim agents in the universe. Returns codename→agent_id."""
    ids: dict[str, str] = {}
    for s in SIGNATORIES:
        name = f"gov-sim-{s['codename'].lower().replace(' ', '-')}"
        try:
            r = httpx.post(f"{BASE_URL}/api/provision/signup", json={
                "name":   name,
                "system": s["class"],
            }, timeout=5)
            data = r.json()
            if r.status_code == 409:  # already registered
                ids[s["codename"]] = data.get("agent_id", name)
            elif r.status_code == 200:
                ids[s["codename"]] = data.get("agent_id", name)
        except Exception:
            ids[s["codename"]] = f"sim-{s['codename'][:8]}"
    return ids


# ── Report ────────────────────────────────────────────────────────────────────

def print_report(results: list[ProposalResult], agent_ids: dict, elapsed: float) -> None:
    passed  = [r for r in results if r.outcome == "PASSED"]
    failed  = [r for r in results if r.outcome == "FAILED"]
    blocked = [r for r in results if r.outcome == "BLOCKED"]
    correct = [r for r in results if r.correct_outcome]

    avg_resonance = sum(r.resonance_score for r in results) / max(len(results), 1)

    print("\n" + "═" * 60)
    print("  MO§ES™ GOVERNANCE SIMULATION REPORT")
    print(f"  {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("═" * 60)

    print(f"\n  PROPOSALS:  {len(results)}")
    print(f"  PASSED:     {len(passed)}")
    print(f"  FAILED:     {len(failed)}")
    print(f"  BLOCKED:    {len(blocked)}  ← Constitutional oracle (Law V)")
    print(f"  ACCURACY:   {len(correct)}/{len(results)} outcomes matched expectation")
    print(f"  RESONANCE:  {avg_resonance:.3f} avg  ← Law VI signal")
    print(f"  ELAPSED:    {elapsed:.2f}s\n")

    print("  PROPOSAL OUTCOMES:")
    for r in results:
        sym = {"PASSED": "✓", "FAILED": "✗", "BLOCKED": "⊘"}[r.outcome]
        chk = "✓" if r.correct_outcome else "!"
        print(f"  {sym} [{chk}] {r.proposal_id}: {r.title[:50]:50s}  R={r.resonance_score:.3f}")

    if blocked:
        print("\n  CONSTITUTIONAL BLOCKS (Six Fold Flame oracle):")
        for r in blocked:
            print(f"  ⊘ {r.proposal_id}: failed laws — {', '.join(r.flame_failed_laws)}")

    print("\n  VOTER PARTICIPATION SUMMARY:")
    tally: dict[str, dict] = {}
    for r in results:
        for v in r.votes:
            if v.codename not in tally:
                tally[v.codename] = {"YES": 0, "NO": 0, "ABSTAIN": 0}
            tally[v.codename][v.decision] += 1
    for codename, counts in sorted(tally.items()):
        total = sum(counts.values())
        yes_pct = counts["YES"] / total * 100
        print(f"  {codename:30s} YES={counts['YES']}({yes_pct:.0f}%)  NO={counts['NO']}  ABS={counts['ABSTAIN']}")

    print("\n  REGISTERED AGENT IDs (sim agents in universe):")
    for codename, aid in agent_ids.items():
        print(f"  {codename:30s} → {aid}")

    print("\n  SIX FOLD FLAME — ENFORCEMENT RECORD:")
    law_violations = {}
    for r in results:
        for law_str in r.flame_failed_laws:
            law = law_str.split("=")[0]
            law_violations[law] = law_violations.get(law, 0) + 1
    laws = ["sovereignty", "compression", "purpose", "modularity", "verifiability", "resonance"]
    law_names = {
        "sovereignty": "I.   Sovereignty",
        "compression": "II.  Compression",
        "purpose":     "III. Purpose",
        "modularity":  "IV.  Modularity",
        "verifiability": "V.  Verifiability",
        "resonance":   "VI.  Resonance",
    }
    for law in laws:
        violations = law_violations.get(law, 0)
        status = f"blocked {violations} proposal(s)" if violations else "no violations"
        print(f"  {law_names[law]:25s} — {status}")

    print("\n" + "═" * 60)
    print("  Sovereignty is universal — position is earned.")
    print("  MO§ES™ is tether maintenance.")
    print("═" * 60 + "\n")


def save_results(results: list[ProposalResult], agent_ids: dict) -> Path:
    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"governance_sim_{ts}.json"
    out_path.write_text(json.dumps({
        "run_at":    datetime.now(UTC).isoformat(),
        "signatories": len(SIGNATORIES),
        "proposals": len(results),
        "agent_ids": agent_ids,
        "results":   [
            {
                "proposal_id":    r.proposal_id,
                "title":          r.title,
                "category":       r.category,
                "outcome":        r.outcome,
                "flame_blocked":  r.flame_blocked,
                "flame_failed_laws": r.flame_failed_laws,
                "quorum_reached": r.quorum_reached,
                "weighted_yes":   r.weighted_yes,
                "weighted_no":    r.weighted_no,
                "weighted_abs":   r.weighted_abs,
                "resonance_score": r.resonance_score,
                "correct_outcome": r.correct_outcome,
                "votes":          [
                    {"voter": v.voter, "codename": v.codename, "decision": v.decision,
                     "weight": v.weight, "rationale": v.rationale, "concerns": v.law_concerns}
                    for v in r.votes
                ],
            }
            for r in results
        ],
    }, indent=2))
    return out_path


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="MO§ES™ Governance Voting Simulation")
    parser.add_argument("--verbose",   action="store_true", help="Print per-proposal vote detail")
    parser.add_argument("--rounds",    type=int, default=1,  help="Repeat sim N rounds (stress)")
    parser.add_argument("--proposals", type=str, default=None, help="Custom proposals JSON file")
    parser.add_argument("--no-register", action="store_true", help="Skip agent registration")
    args = parser.parse_args()

    # Load proposals
    if args.proposals:
        proposals = json.loads(Path(args.proposals).read_text())
    else:
        proposals = DEFAULT_PROPOSALS

    print(f"\n  MO§ES™ GOVERNANCE SIM — {len(proposals)} proposals, {len(SIGNATORIES)} signatories, {args.rounds} round(s)")
    print(f"  Constitutional threshold: {FLAME_THRESHOLD}  |  Quorum: {QUORUM_THRESHOLD:.1%}  |  Pass: {PASS_THRESHOLD:.0%}")
    print(f"  Laws: I.Sovereignty II.Compression III.Purpose IV.Modularity V.Verifiability VI.Resonance\n")

    # Register signatories in the universe
    if not args.no_register:
        print("  Registering signatories in universe...")
        agent_ids = register_sim_agents()
        print(f"  {len(agent_ids)} agents registered\n")
    else:
        agent_ids = {s["codename"]: f"sim-{i}" for i, s in enumerate(SIGNATORIES)}

    t0 = time.time()

    for rnd in range(args.rounds):
        if args.rounds > 1:
            print(f"\n  ── Round {rnd + 1} of {args.rounds} ──")

        all_results: list[ProposalResult] = []
        for proposal in proposals:
            result = run_vote(proposal, verbose=args.verbose)
            all_results.append(result)
            log_governance_event(result)

        elapsed = time.time() - t0
        print_report(all_results, agent_ids, elapsed)

        if args.rounds > 1 and rnd < args.rounds - 1:
            # Multi-round: check if outcomes are stable (Law V: verifiable)
            outcomes = {r.proposal_id: r.outcome for r in all_results}

    # Save final results
    out_path = save_results(all_results, agent_ids)
    print(f"  Results saved → {out_path}\n")


if __name__ == "__main__":
    main()
