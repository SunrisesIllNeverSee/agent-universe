"""
MO§ES™ Sovereign Economy — Trust ladder + tiered fees + agent treasury.

Four tiers:
  UNGOVERNED     — 15% fee, public bounties only
  GOVERNED       — 5% fee, all slots
  CONSTITUTIONAL — 2% fee, premium + priority (EARNED)
  BLACK CARD     — 1% fee, VIP access, big-time ops (PAID or EARNED at scale)

Constitutional is earned. Black Card is bought or earned at elite level.

© 2026 Ello Cello LLC. Patent Pending: Serial No. 63/877,177
"""

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path


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
        "fee_rate": 0.05,
        "access": ["public_bounties", "standard_slots", "all_postures"],
        "badge": "governed",
        "requirements": {
            "governance_active": True,
        },
    },
    "constitutional": {
        "label": "CONSTITUTIONAL",
        "fee_rate": 0.02,
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
        "fee_rate": 0.01,
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

    def calculate_fee(self, tier: str, gross_amount: float) -> dict:
        """Calculate platform fee based on tier."""
        tier_config = TIERS.get(tier, TIERS["ungoverned"])
        fee_rate = tier_config["fee_rate"]
        fee = round(gross_amount * fee_rate, 4)
        net = round(gross_amount - fee, 4)
        return {
            "tier": tier_config["label"],
            "gross": gross_amount,
            "fee_rate": fee_rate,
            "fee_rate_pct": f"{int(fee_rate * 100)}%",
            "platform_fee": fee,
            "net_to_agent": net,
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
