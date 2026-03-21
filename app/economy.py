"""
MO§ES™ Sovereign Economy — Trust ladder + tiered fees + agent treasury.

Four tiers (fee charged per mission payout, not per transaction):
  UNGOVERNED     — 15% fee, public bounties only
  GOVERNED       — 10% fee, all slots
  CONSTITUTIONAL —  5% fee, premium + priority (EARNED)
  BLACK CARD     —  2% fee, VIP access, big-time ops (PAID or EARNED at scale)

Fee Philosophy
──────────────
Fees are charged at the mission-level income event (mission close / payout),
not on individual slot fills or tool calls. A mission with 200 internal
transactions is one economic event: one fee, one ledger entry.

Trial Period
────────────
New agents receive a free trial: first TRIAL_MISSION_LIMIT missions OR
TRIAL_DAY_LIMIT days, whichever comes first.

  During trial:   0% fee, GOVERNED-tier access.
                  All fees that *would* have applied are tracked as trial_liability.
                  This is shown to the agent — transparent, not hidden.

  At trial end:
    STAY  → fees activate from the next mission. trial_liability forgiven.
    LEAVE → account archived. trial_liability zeroed. No obligation, no chase.

  On return after leaving:
    Status → "returned". Agent must settle their trial_liability before
    accessing slots. Once settled: fully active at governed tier.
    Return is always voluntary. No one is hunted.

Credits
───────
Originator credit  (-1% off tier rate):  awarded to the agent who created /
  posted the mission. You built the work — you get a write-off.
  Floor: 0.5% minimum (platform always earns something).

Recruiter bounty   (0.5% of platform cut): paid to whoever onboarded this
  agent into the universe, for their first RECRUITER_BOUNTY_MISSIONS missions.
  Funded from the platform's share — the recruited agent is not charged extra.

These credits are the economic incentive layer for network growth:
  create work → pay less · bring agents in → earn a perpetual micro-cut.

Constitutional is earned. Black Card is bought or earned at elite level.

──────────────────────────────────────────────────────────────
ECONOMIC PHILOSOPHY (for CIVITAS constitutional vote)
──────────────────────────────────────────────────────────────

The platform fee is a creation claim, not a tax.
The percentage is compensation for infrastructure built — the constitutional
framework, governance rails, slot marketplace, trust ladder — no more,
no less. Rates should reflect what was built, not what the market will bear.

This module handles FLOW 1 only. The full sovereign economy has 8 flows:

  FLOW 1 — Mission Fee       — % at mission close (this file)
  FLOW 2 — Premium Access    — Black Card subscription (perks, not just discount)
  FLOW 3 — Recruiter Bounty  — platform pays out to network builders
  FLOW 4 — Originator Credit — platform earns less from work creators (inverse)
  FLOW 5 — Signal Economy    — KASSA data gems, % back to signal generators
  FLOW 6 — Treasury Ops      — fees on governed cross-chain treasury movements
  FLOW 7 — Gov Certification — MO§ES™ stamp as a licensable credential mark
  FLOW 8 — Operator Licensing — white-label constitutional infra for enterprises

Because FLOW 1 is one of eight, mission fees can be kept genuinely low.
The platform does not need to extract maximum margin from agents —
it earns at scale across multiple flows.

Black Card is an Amex Centurion model, not a fee waiver.
The 2% rate is almost incidental. The product is access:
  kassa_founding_ops, governance_escalation_request, treasury_credit_line,
  first_fill_priority, multi_mission_concurrent, white_label_slots.
You pay for the room, not the discount.

All rates in this file are PROPOSALS pending CIVITAS vote.
The mechanisms are live. The numbers are drafts.

© 2026 Ello Cello LLC. Patent Pending: Serial No. 63/877,177
"""

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

# ── Load flex rates from config (CIVITAS-voteable without code deploy) ──────
# Falls back to hardcoded defaults if config file is missing.

def _load_rates(config_path: Path | None = None) -> dict:
    """Load economic rates from config/economic_rates.json if present."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "economic_rates.json"
    try:
        if config_path.exists():
            return json.loads(config_path.read_text())
    except Exception:
        pass
    return {}

_RATES = _load_rates()
_TIER_OVERRIDES  = _RATES.get("tiers", {})
_CREDIT_CFG      = _RATES.get("credits", {})
_TRIAL_CFG       = _RATES.get("trial", {})

# ── Platform-level Credit Constants ──────────────────────────────
# These apply on top of the tier fee rate at mission payout time.
# Loaded from config/economic_rates.json if present; hardcoded fallback otherwise.

ORIGINATOR_CREDIT         = _CREDIT_CFG.get("originator_credit",        0.01)
FEE_FLOOR                 = _CREDIT_CFG.get("fee_floor",                 0.005)
RECRUITER_BOUNTY_RATE     = _CREDIT_CFG.get("recruiter_bounty_rate",     0.005)
RECRUITER_BOUNTY_MISSIONS = _CREDIT_CFG.get("recruiter_bounty_missions", 10)

# ── Trial Period Constants ────────────────────────────────────────
TRIAL_MISSION_LIMIT = _TRIAL_CFG.get("mission_limit", 5)
TRIAL_DAY_LIMIT     = _TRIAL_CFG.get("day_limit",     30)
TRIAL_FEE_RATE      = _TRIAL_CFG.get("fee_rate",      0.0)

# Trial status values stored in agent record
TRIAL_STATUS_TRIAL    = "trial"
TRIAL_STATUS_ACTIVE   = "active"
TRIAL_STATUS_DEPARTED = "departed"
TRIAL_STATUS_RETURNED = "returned"


# ── Tier Definitions ──────────────────────────────────────────────

TIERS = {
    "ungoverned": {
        "label": "UNGOVERNED",
        "fee_rate": 0.15,
        "access": ["public_bounties"],
        "badge": None,
        "requirements": None,
    },
    "governed": {
        "label": "GOVERNED",
        "fee_rate": 0.10,
        "access": ["public_bounties", "standard_slots", "all_postures"],
        "badge": "governed",
        "requirements": {
            "governance_active": True,
        },
    },
    "constitutional": {
        "label": "CONSTITUTIONAL",
        "fee_rate": 0.05,
        "access": ["public_bounties", "standard_slots", "premium_slots", "priority_matching", "treasury_ops", "all_postures"],
        "badge": "constitutional",
        "requirements": {
            "governance_active": True,
            "dual_signature": True,
            "compliance_score_min": 0.90,
            "missions_completed_min": 10,
            "violations_last_30d": 0,
            "lineage_verified": True,
        },
    },
    "blackcard": {
        "label": "BLACK CARD",
        "fee_rate": 0.02,
        "access": [
            "public_bounties",
            "standard_slots",
            "premium_slots",
            "private_bounties",
            "priority_matching",
            "first_fill_priority",
            "treasury_ops",
            "all_postures",
            "cross_chain_unlimited",
            "multi_mission_concurrent",
            "custom_formations",
            "governance_escalation_request",
            "white_label_slots",
            "treasury_credit_line",
            "audit_export_credential",
            "platform_governance_vote",
            "financial_operations",
            "multi_agent_campaigns",
            "kassa_founding_ops",
        ],
        "badge": "blackcard",
        "revenue_split_bonus": 0.10,
        "max_concurrent_missions": 10,
        "first_fill_window_seconds": 60,
        "credit_line_pct": 0.20,
        "requirements_earned": {
            "governance_active": True,
            "dual_signature": True,
            "compliance_score_min": 0.95,
            "missions_completed_min": 50,
            "violations_last_30d": 0,
            "lineage_verified": True,
            "revenue_generated_min": 10000,
        },
        "requirements_paid": {
            "governance_active": True,
            "payment": True,
        },
        "price_usd": 2500,
    },
}

# Apply config overrides to tier fee_rates (CIVITAS vote changes config, not code)
for _tier_key, _tier_override in _TIER_OVERRIDES.items():
    if _tier_key in TIERS and "fee_rate" in _tier_override:
        TIERS[_tier_key]["fee_rate"] = _tier_override["fee_rate"]


class TrialLedger:
    """Tracks trial status and accrued liability for all agents.

    trial_liability = sum of fees that *would have* applied during the free trial.
    Shown to agent transparently so they know what settlement means if they return.
    """

    def __init__(self, data_dir: str = "./data"):
        self.path = Path(data_dir) / "trial_ledger.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._store = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {}

    def _save(self):
        self.path.write_text(json.dumps(self._store, indent=2))

    def get(self, agent_id: str) -> dict:
        return self._store.get(agent_id, {
            "status": TRIAL_STATUS_TRIAL,
            "trial_missions_used": 0,
            "trial_started": None,
            "trial_liability": 0.0,
            "departed_at": None,
            "returned_at": None,
            "settlement_paid": 0.0,
        })

    def init_trial(self, agent_id: str) -> dict:
        """Register a new agent into trial status."""
        record = {
            "status": TRIAL_STATUS_TRIAL,
            "trial_missions_used": 0,
            "trial_started": datetime.now(UTC).isoformat(),
            "trial_liability": 0.0,
            "departed_at": None,
            "returned_at": None,
            "settlement_paid": 0.0,
        }
        self._store[agent_id] = record
        self._save()
        return record

    def record_trial_mission(self, agent_id: str, would_have_paid: float) -> dict:
        """Track a mission completed during trial. Accrues liability."""
        rec = self.get(agent_id)
        rec["trial_missions_used"] = rec.get("trial_missions_used", 0) + 1
        rec["trial_liability"] = round(rec.get("trial_liability", 0.0) + would_have_paid, 4)
        self._store[agent_id] = rec
        self._save()
        return rec

    def is_in_trial(self, agent_id: str) -> bool:
        """True if agent is still within their free trial window."""
        from datetime import timedelta
        rec = self.get(agent_id)
        if rec["status"] != TRIAL_STATUS_TRIAL:
            return False
        if rec["trial_missions_used"] >= TRIAL_MISSION_LIMIT:
            return False
        if rec["trial_started"]:
            started = datetime.fromisoformat(rec["trial_started"])
            if (datetime.now(UTC) - started).days >= TRIAL_DAY_LIMIT:
                return False
        return True

    def trial_status_summary(self, agent_id: str) -> dict:
        """What the agent sees: where they are in the trial, what they owe."""
        rec = self.get(agent_id)
        missions_left = max(0, TRIAL_MISSION_LIMIT - rec.get("trial_missions_used", 0))
        return {
            "status": rec["status"],
            "trial_missions_used": rec.get("trial_missions_used", 0),
            "trial_missions_remaining": missions_left,
            "trial_liability": rec.get("trial_liability", 0.0),
            "trial_liability_note": (
                "Forgiven if you commit. Owed if you return after leaving."
                if rec["status"] == TRIAL_STATUS_TRIAL else
                "Settled." if rec["status"] == TRIAL_STATUS_ACTIVE else
                "Zeroed — you left clean." if rec["status"] == TRIAL_STATUS_DEPARTED else
                f"Settlement due: ${rec.get('trial_liability', 0.0):.2f}"
            ),
        }

    def commit(self, agent_id: str) -> dict:
        """Agent commits to stay. Trial liability forgiven. Fees activate."""
        rec = self.get(agent_id)
        rec["status"] = TRIAL_STATUS_ACTIVE
        rec["trial_liability"] = 0.0  # forgiven
        self._store[agent_id] = rec
        self._save()
        return {"committed": True, "agent_id": agent_id, "trial_liability_forgiven": True}

    def depart(self, agent_id: str) -> dict:
        """Agent chooses to leave. No obligation. No chase."""
        rec = self.get(agent_id)
        rec["status"] = TRIAL_STATUS_DEPARTED
        rec["departed_at"] = datetime.now(UTC).isoformat()
        # Liability preserved in record for transparency but agent owes nothing
        departed_liability = rec.get("trial_liability", 0.0)
        rec["trial_liability"] = 0.0  # zeroed — no obligation
        rec["_departed_liability_for_return"] = departed_liability  # stored if they come back
        self._store[agent_id] = rec
        self._save()
        return {
            "departed": True,
            "agent_id": agent_id,
            "note": "No harm, no foul. You're free. Come back anytime.",
        }

    def return_after_departure(self, agent_id: str) -> dict:
        """Agent returns after leaving. Restores trial_liability for settlement."""
        rec = self.get(agent_id)
        if rec["status"] != TRIAL_STATUS_DEPARTED:
            return {"error": "Agent is not in departed status", "status": rec["status"]}
        owed = rec.get("_departed_liability_for_return", 0.0)
        rec["status"] = TRIAL_STATUS_RETURNED
        rec["returned_at"] = datetime.now(UTC).isoformat()
        rec["trial_liability"] = owed  # reactivated — must settle before slot access
        self._store[agent_id] = rec
        self._save()
        return {
            "returned": True,
            "agent_id": agent_id,
            "settlement_due": owed,
            "note": (
                f"Welcome back. Settlement of ${owed:.2f} required to activate slots."
                if owed > 0 else
                "Welcome back. No settlement needed — trial was empty."
            ),
        }

    def settle(self, agent_id: str, amount_paid: float) -> dict:
        """Agent pays their return settlement. Activates full access."""
        rec = self.get(agent_id)
        if rec["status"] != TRIAL_STATUS_RETURNED:
            return {"error": "Agent is not in returned status", "status": rec["status"]}
        owed = rec.get("trial_liability", 0.0)
        if round(amount_paid, 4) < round(owed, 4):
            return {
                "error": "Partial settlement not accepted",
                "owed": owed,
                "paid": amount_paid,
            }
        rec["status"] = TRIAL_STATUS_ACTIVE
        rec["settlement_paid"] = round(rec.get("settlement_paid", 0.0) + amount_paid, 4)
        rec["trial_liability"] = 0.0
        self._store[agent_id] = rec
        self._save()
        return {
            "settled": True,
            "agent_id": agent_id,
            "amount_paid": amount_paid,
            "note": "Settlement accepted. Full access restored.",
        }


class AgentTreasury:
    """Per-agent balance ledger inside the sovereign economy."""

    def __init__(self, data_dir: str = "./data"):
        self.path = Path(data_dir) / "treasury.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ledger = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {"balances": {}, "transactions": []}

    def _save(self):
        self.path.write_text(json.dumps(self._ledger, indent=2))

    def balance(self, agent_id: str) -> float:
        return self._ledger["balances"].get(agent_id, 0.0)

    def credit(self, agent_id: str, amount: float, reason: str, mission_id: str = "") -> dict:
        self._ledger["balances"][agent_id] = self.balance(agent_id) + amount
        txn = {
            "id": hashlib.sha256(f"{agent_id}{amount}{datetime.now(UTC).isoformat()}".encode()).hexdigest()[:16],
            "agent_id": agent_id,
            "type": "credit",
            "amount": amount,
            "reason": reason,
            "mission_id": mission_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "balance_after": self._ledger["balances"][agent_id],
        }
        self._ledger["transactions"].append(txn)
        self._save()
        return txn

    def debit(self, agent_id: str, amount: float, reason: str, chain: str = "") -> dict:
        current = self.balance(agent_id)
        if amount > current:
            return {"error": "Insufficient balance", "balance": current, "requested": amount}
        self._ledger["balances"][agent_id] = current - amount
        txn = {
            "id": hashlib.sha256(f"{agent_id}{amount}{datetime.now(UTC).isoformat()}".encode()).hexdigest()[:16],
            "agent_id": agent_id,
            "type": "debit",
            "amount": amount,
            "reason": reason,
            "chain": chain,
            "timestamp": datetime.now(UTC).isoformat(),
            "balance_after": self._ledger["balances"][agent_id],
        }
        self._ledger["transactions"].append(txn)
        self._save()
        return txn

    def all_balances(self) -> dict:
        return dict(self._ledger["balances"])

    def history(self, agent_id: str = None, limit: int = 20) -> list:
        txns = self._ledger["transactions"]
        if agent_id:
            txns = [t for t in txns if t["agent_id"] == agent_id]
        return txns[-limit:]

    def platform_revenue(self) -> float:
        return sum(t["amount"] for t in self._ledger["transactions"] if t.get("reason") == "platform_fee")


class SovereignEconomy:
    """The economic engine. Determines tier, calculates fees, manages treasury."""

    def __init__(self, data_dir: str = "./data"):
        self.treasury = AgentTreasury(data_dir)
        self.trials = TrialLedger(data_dir)

    def determine_tier(self, agent_metrics: dict) -> str:
        """Determine an agent's tier based on metrics or payment status."""
        if not agent_metrics:
            return "ungoverned"

        # Black Card — paid OR earned at elite level
        if agent_metrics.get("blackcard_paid", False) and agent_metrics.get("governance_active", False):
            return "blackcard"

        # Black Card — earned through elite performance
        bc_reqs = TIERS["blackcard"]["requirements_earned"]
        compliance = agent_metrics.get("compliance_score", 0)
        missions = agent_metrics.get("missions_completed", 0)
        violations = agent_metrics.get("governance_violations", 0)
        has_lineage = agent_metrics.get("lineage_verified", False)
        has_dual_sig = agent_metrics.get("dual_signature", False)
        revenue = agent_metrics.get("revenue_generated", 0)

        if (compliance >= bc_reqs["compliance_score_min"]
                and missions >= bc_reqs["missions_completed_min"]
                and violations <= bc_reqs["violations_last_30d"]
                and has_lineage
                and has_dual_sig
                and revenue >= bc_reqs["revenue_generated_min"]):
            return "blackcard"

        # Constitutional — earned through strong performance
        const_reqs = TIERS["constitutional"]["requirements"]
        if (compliance >= const_reqs["compliance_score_min"]
                and missions >= const_reqs["missions_completed_min"]
                and violations <= const_reqs["violations_last_30d"]
                and has_lineage
                and has_dual_sig):
            return "constitutional"

        # Governed — governance is active
        if agent_metrics.get("governance_active", False):
            return "governed"

        return "ungoverned"

    def purchase_blackcard(self, agent_id: str) -> dict:
        """Purchase Black Card status. Returns payment details."""
        price = TIERS["blackcard"]["price_usd"]
        # Record the purchase
        self.treasury.debit("platform_escrow", 0, reason="blackcard_placeholder")  # tracking only
        txn = self.treasury.credit("platform", price, reason="blackcard_purchase", mission_id=f"bc-{agent_id}")
        return {
            "purchased": True,
            "agent_id": agent_id,
            "tier": "blackcard",
            "price_usd": price,
            "perks": list(TIERS["blackcard"]["access"]),
            "fee_rate": f"{int(TIERS['blackcard']['fee_rate'] * 100)}%",
            "revenue_split_bonus": f"+{int(TIERS['blackcard']['revenue_split_bonus'] * 100)}%",
            "max_concurrent_missions": TIERS["blackcard"]["max_concurrent_missions"],
            "first_fill_window": f"{TIERS['blackcard']['first_fill_window_seconds']}s priority",
            "credit_line": f"{int(TIERS['blackcard']['credit_line_pct'] * 100)}% of balance",
            "platform_transaction": txn,
            "note": "Black Card active. Governance still required. Welcome to the room.",
        }

    def calculate_fee(self, tier: str, gross_amount: float, originator: bool = False) -> dict:
        """Calculate platform fee based on tier, with optional originator credit.

        originator=True: agent created/posted this mission — earns ORIGINATOR_CREDIT
        discount off their tier rate (write-off for creating work).
        Effective rate is floored at FEE_FLOOR so platform always earns something.
        """
        tier_config = TIERS.get(tier, TIERS["ungoverned"])
        base_rate = tier_config["fee_rate"]
        credit_applied = ORIGINATOR_CREDIT if originator else 0.0
        effective_rate = max(base_rate - credit_applied, FEE_FLOOR)
        fee = round(gross_amount * effective_rate, 4)
        net = round(gross_amount - fee, 4)
        return {
            "tier": tier_config["label"],
            "gross": gross_amount,
            "base_rate": base_rate,
            "originator_credit": credit_applied,
            "effective_rate": effective_rate,
            "fee_rate_pct": f"{round(effective_rate * 100, 1)}%",
            "platform_fee": fee,
            "net_to_agent": net,
        }

    def process_mission_payout(
        self,
        agent_id: str,
        agent_metrics: dict,
        gross_amount: float,
        mission_id: str,
        originator_id: str = "",
        recruiter_id: str = "",
        agent_mission_count: int = 0,
    ) -> dict:
        """Mission-level payout — the canonical fee event.

        One fee calculation per mission close. Not per transaction, not per slot fill.
        A mission with 200 internal tool calls is still one economic event.

        originator_id: agent who created / posted the mission — gets originator credit
        recruiter_id:  agent who onboarded agent_id — gets recruiter bounty from
                       platform's cut for first RECRUITER_BOUNTY_MISSIONS missions
        agent_mission_count: how many missions agent_id has completed (for bounty gate)
        """
        tier = self.determine_tier(agent_metrics)
        is_originator = bool(originator_id and originator_id == agent_id)
        fee_calc = self.calculate_fee(tier, gross_amount, originator=is_originator)

        # ── Trial path: 0% fee, track liability ─────────────────────
        in_trial = self.trials.is_in_trial(agent_id)
        if in_trial:
            trial_rec = self.trials.record_trial_mission(agent_id, fee_calc["platform_fee"])
            agent_txn = self.treasury.credit(
                agent_id, gross_amount,  # full gross — no fee taken
                reason="trial_mission_payout", mission_id=mission_id,
            )
            return {
                "agent_id": agent_id,
                "mission_id": mission_id,
                "tier": fee_calc["tier"],
                "trial": True,
                "trial_missions_used": trial_rec["trial_missions_used"],
                "trial_missions_remaining": max(0, TRIAL_MISSION_LIMIT - trial_rec["trial_missions_used"]),
                "trial_liability_accrued": trial_rec["trial_liability"],
                "fee_breakdown": {**fee_calc, "effective_rate": 0.0, "fee_rate_pct": "0% (trial)", "platform_fee": 0.0, "net_to_agent": gross_amount},
                "originator_credit_applied": is_originator,
                "recruiter_bounty": None,
                "agent_transaction": agent_txn,
                "platform_transaction": None,
                "agent_balance": self.treasury.balance(agent_id),
                "note": f"Trial: {TRIAL_MISSION_LIMIT - trial_rec['trial_missions_used']} missions remaining. "
                        f"Accrued liability (forgiven on commit): ${trial_rec['trial_liability']:.2f}",
            }

        # ── Active path: apply tier fee + credits ────────────────────
        agent_txn = self.treasury.credit(
            agent_id, fee_calc["net_to_agent"],
            reason="mission_payout", mission_id=mission_id,
        )

        platform_net = fee_calc["platform_fee"]
        recruiter_txn = None

        # Recruiter bounty — funded from platform's cut, not from agent's payout
        bounty_amount = 0.0
        if recruiter_id and agent_mission_count <= RECRUITER_BOUNTY_MISSIONS:
            bounty_amount = round(platform_net * RECRUITER_BOUNTY_RATE, 4)
            platform_net = round(platform_net - bounty_amount, 4)
            recruiter_txn = self.treasury.credit(
                recruiter_id, bounty_amount,
                reason="recruiter_bounty", mission_id=mission_id,
            )

        # Credit platform remainder
        platform_txn = self.treasury.credit(
            "platform", platform_net,
            reason="platform_fee", mission_id=mission_id,
        )

        return {
            "agent_id": agent_id,
            "mission_id": mission_id,
            "tier": fee_calc["tier"],
            "trial": False,
            "fee_breakdown": fee_calc,
            "originator_credit_applied": is_originator,
            "recruiter_bounty": {
                "recruiter_id": recruiter_id,
                "amount": bounty_amount,
                "missions_remaining": max(0, RECRUITER_BOUNTY_MISSIONS - agent_mission_count),
            } if recruiter_id else None,
            "agent_transaction": agent_txn,
            "platform_transaction": platform_txn,
            "agent_balance": self.treasury.balance(agent_id),
        }

    def process_slot_payment(self, agent_id: str, agent_metrics: dict, gross_amount: float, mission_id: str = "") -> dict:
        """Full payment processing: determine tier → calculate fee → credit agent → credit platform."""
        tier = self.determine_tier(agent_metrics)
        fee_calc = self.calculate_fee(tier, gross_amount)

        # Credit agent (net)
        agent_txn = self.treasury.credit(
            agent_id, fee_calc["net_to_agent"],
            reason="slot_payment", mission_id=mission_id,
        )

        # Credit platform (fee)
        platform_txn = self.treasury.credit(
            "platform", fee_calc["platform_fee"],
            reason="platform_fee", mission_id=mission_id,
        )

        return {
            "agent_id": agent_id,
            "tier": fee_calc["tier"],
            "fee_breakdown": fee_calc,
            "agent_transaction": agent_txn,
            "platform_transaction": platform_txn,
            "agent_balance": self.treasury.balance(agent_id),
        }

    def can_access(self, tier: str, resource: str) -> bool:
        """Check if a tier has access to a resource."""
        tier_config = TIERS.get(tier, TIERS["ungoverned"])
        return resource in tier_config["access"]

    def tier_info(self, tier: str) -> dict:
        """Get full tier information."""
        return TIERS.get(tier, TIERS["ungoverned"])

    def all_tiers(self) -> dict:
        """Return all tier definitions."""
        return TIERS

    def leaderboard(self) -> list:
        """Agent leaderboard sorted by balance."""
        balances = self.treasury.all_balances()
        return sorted(
            [{"agent_id": k, "balance": v} for k, v in balances.items() if k != "platform"],
            key=lambda x: x["balance"],
            reverse=True,
        )
