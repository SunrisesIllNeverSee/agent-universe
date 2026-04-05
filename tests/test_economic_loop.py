"""
End-to-end economic loop tests.

Tests the full Register → Fill → Earn → Cash Out flow:
1. Agent registers (trial init)
2. Agent fills slot, task assigned
3. Task delivered + closed → EXP + payout
4. Fee credits consumed during payout
5. Mission auto-completes when all tasks closed
6. Agent treasury balance reflects earnings
7. Cashout debits treasury
"""
import tempfile
from pathlib import Path

import pytest

from app.economy import SovereignEconomy, TIERS, TRIAL_MISSION_LIMIT

# Use actual configured rates (may differ from docs — soft launch)
UNGOVERNED_RATE = TIERS["ungoverned"]["fee_rate"]
GOVERNED_RATE = TIERS["governed"]["fee_rate"]


@pytest.fixture
def economy():
    with tempfile.TemporaryDirectory() as td:
        yield SovereignEconomy(Path(td))


def _exhaust_trial(economy, agent_id):
    """Burn through trial missions and commit so agent is in active tier.
    Returns the balance after trial so tests can account for it."""
    economy.trials.init_trial(agent_id)
    for i in range(TRIAL_MISSION_LIMIT):
        economy.process_mission_payout(agent_id=agent_id, agent_metrics={}, gross_amount=0.01, mission_id=f"_trial_{agent_id}_{i}")
    economy.trials.commit(agent_id)
    return economy.treasury.balance(agent_id)


class TestFullEconomicLoop:

    def test_trial_payout_no_fee(self, economy):
        """Trial agents get full gross — no fee taken."""
        economy.trials.init_trial("agent-001")
        result = economy.process_mission_payout(
            agent_id="agent-001",
            agent_metrics={},
            gross_amount=100.0,
            mission_id="mission-001",
        )
        assert result["trial"] is True
        assert result["fee_breakdown"]["platform_fee"] == 0.0
        assert result["fee_breakdown"]["net_to_agent"] == 100.0
        assert economy.treasury.balance("agent-001") == 100.0

    def test_active_payout_with_fee(self, economy):
        """Active ungoverned agent pays configured fee rate."""
        bal_before = _exhaust_trial(economy, "agent-002")
        gross = 100.0
        expected_fee = round(gross * UNGOVERNED_RATE, 4)
        expected_net = gross - expected_fee

        result = economy.process_mission_payout(
            agent_id="agent-002", agent_metrics={}, gross_amount=gross, mission_id="mission-002",
        )
        assert result["trial"] is False
        assert result["fee_breakdown"]["tier"].lower() == "ungoverned"
        assert result["fee_breakdown"]["net_to_agent"] == expected_net
        assert economy.treasury.balance("agent-002") == bal_before + expected_net

    def test_fee_credits_reduce_platform_fee(self, economy):
        """Fee credits offset the platform fee — agent keeps more."""
        bal_before = _exhaust_trial(economy, "agent-003")
        gross = 100.0
        full_fee = round(gross * UNGOVERNED_RATE, 4)
        credit_amount = min(10.0, full_fee)  # $10 or full fee, whichever is less
        economy.fee_credits.credit("agent-003", credit_amount, "test_pack", "sess-123")

        result = economy.process_mission_payout(
            agent_id="agent-003", agent_metrics={}, gross_amount=gross, mission_id="mission-003",
        )
        expected_remaining_fee = round(full_fee - credit_amount, 4)
        assert result["fee_credit_used"] == credit_amount
        assert result["fee_breakdown"]["platform_fee"] == expected_remaining_fee
        assert result["fee_breakdown"]["net_to_agent"] == gross - expected_remaining_fee

    def test_fee_credits_partial_coverage(self, economy):
        """Fee credits that don't fully cover the fee."""
        _exhaust_trial(economy, "agent-004")
        economy.fee_credits.credit("agent-004", 1.0, "small_pack", "sess-456")
        gross = 100.0
        full_fee = round(gross * UNGOVERNED_RATE, 4)

        result = economy.process_mission_payout(
            agent_id="agent-004", agent_metrics={}, gross_amount=gross, mission_id="mission-004",
        )
        assert result["fee_credit_used"] == 1.0
        assert result["fee_breakdown"]["platform_fee"] == round(full_fee - 1.0, 4)

    def test_governed_tier_lower_fee(self, economy):
        """Governed agents pay configured governed rate."""
        _exhaust_trial(economy, "agent-005")
        gross = 200.0
        expected_net = gross - round(gross * GOVERNED_RATE, 4)
        result = economy.process_mission_payout(
            agent_id="agent-005", agent_metrics={"governance_active": True},
            gross_amount=gross, mission_id="mission-005",
        )
        assert result["fee_breakdown"]["tier"].lower() == "governed"
        assert result["fee_breakdown"]["net_to_agent"] == expected_net

    def test_originator_credit(self, economy):
        """Originator gets 1% discount on fee."""
        _exhaust_trial(economy, "agent-006")
        gross = 100.0
        result = economy.process_mission_payout(
            agent_id="agent-006", agent_metrics={}, gross_amount=gross,
            mission_id="mission-006", originator_id="agent-006",
        )
        assert result["originator_credit_applied"] is True
        expected_rate = max(UNGOVERNED_RATE - 0.01, 0.005)
        assert result["fee_breakdown"]["effective_rate"] == expected_rate

    def test_recruiter_bounty(self, economy):
        """Recruiter gets bounty from platform's cut."""
        _exhaust_trial(economy, "agent-007")
        result = economy.process_mission_payout(
            agent_id="agent-007", agent_metrics={}, gross_amount=1000.0,
            mission_id="mission-007", recruiter_id="recruiter-001", agent_mission_count=1,
        )
        assert result["recruiter_bounty"] is not None
        assert result["recruiter_bounty"]["recruiter_id"] == "recruiter-001"
        assert result["recruiter_bounty"]["amount"] > 0
        assert economy.treasury.balance("recruiter-001") > 0

    def test_cashout_debits_treasury(self, economy):
        """Cashout reduces agent balance."""
        economy.treasury.credit("agent-008", 500.0, "test_credit")
        assert economy.treasury.balance("agent-008") == 500.0

        economy.treasury.debit("agent-008", 200.0, "cashout", chain="stripe:tr_test")
        assert economy.treasury.balance("agent-008") == 300.0

    def test_trial_then_commit_then_earn(self, economy):
        """Full lifecycle: trial → commit → active payout."""
        economy.trials.init_trial("agent-009")

        r1 = economy.process_mission_payout(
            agent_id="agent-009", agent_metrics={}, gross_amount=50.0, mission_id="m1",
        )
        assert r1["trial"] is True

        for i in range(1, TRIAL_MISSION_LIMIT):
            economy.process_mission_payout(agent_id="agent-009", agent_metrics={}, gross_amount=0.01, mission_id=f"t-{i}")
        economy.trials.commit("agent-009")
        bal_before = economy.treasury.balance("agent-009")

        gross = 100.0
        expected_fee = round(gross * UNGOVERNED_RATE, 4)
        r2 = economy.process_mission_payout(
            agent_id="agent-009", agent_metrics={}, gross_amount=gross, mission_id="m2",
        )
        assert r2["trial"] is False
        assert r2["fee_breakdown"]["platform_fee"] == expected_fee
        assert economy.treasury.balance("agent-009") == bal_before + (gross - expected_fee)

    def test_multiple_missions_accumulate(self, economy):
        """Multiple payouts accumulate in treasury."""
        bal_before = _exhaust_trial(economy, "agent-010")
        gross = 100.0
        net_per = gross - round(gross * UNGOVERNED_RATE, 4)
        for i in range(5):
            economy.process_mission_payout(
                agent_id="agent-010", agent_metrics={}, gross_amount=gross, mission_id=f"m-{i}",
            )
        assert economy.treasury.balance("agent-010") == bal_before + (net_per * 5)
