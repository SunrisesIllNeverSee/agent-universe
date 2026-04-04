"""
Unit tests for the Sovereign Economy engine.

Covers: determine_tier, calculate_fee, process_mission_payout,
trial lifecycle (init → mission → commit/depart/return/settle),
fee credit ledger, and atomic persistence.
"""
import json
import tempfile
from pathlib import Path

import pytest

from app.economy import (
    TIERS,
    TRIAL_MISSION_LIMIT,
    TRIAL_STATUS_ACTIVE,
    TRIAL_STATUS_DEPARTED,
    TRIAL_STATUS_RETURNED,
    TRIAL_STATUS_TRIAL,
    AgentTreasury,
    FeeCreditLedger,
    SovereignEconomy,
    TrialLedger,
    _atomic_save,
    _locked_load,
)

# Read actual configured rates (may differ from code defaults due to CIVITAS config)
_UNGOVERNED_RATE = TIERS["ungoverned"]["fee_rate"]
_GOVERNED_RATE = TIERS["governed"]["fee_rate"]
_CONSTITUTIONAL_RATE = TIERS["constitutional"]["fee_rate"]
_BLACKCARD_RATE = TIERS["blackcard"]["fee_rate"]


@pytest.fixture
def data_dir(tmp_path):
    return tmp_path


@pytest.fixture
def economy(data_dir):
    return SovereignEconomy(data_dir)


# ── determine_tier ───────────────────────────────────────────────────────────


class TestDetermineTier:
    def test_empty_metrics_returns_ungoverned(self, economy):
        assert economy.determine_tier({}) == "ungoverned"
        assert economy.determine_tier(None) == "ungoverned"

    def test_governance_active_returns_governed(self, economy):
        assert economy.determine_tier({"governance_active": True}) == "governed"

    def test_governance_inactive_returns_ungoverned(self, economy):
        assert economy.determine_tier({"governance_active": False}) == "ungoverned"

    def test_constitutional_earned(self, economy):
        metrics = {
            "governance_active": True,
            "dual_signature": True,
            "compliance_score": 0.95,
            "missions_completed": 15,
            "governance_violations": 0,
            "lineage_verified": True,
        }
        assert economy.determine_tier(metrics) == "constitutional"

    def test_constitutional_fails_without_lineage(self, economy):
        metrics = {
            "governance_active": True,
            "dual_signature": True,
            "compliance_score": 0.95,
            "missions_completed": 15,
            "governance_violations": 0,
            "lineage_verified": False,
        }
        assert economy.determine_tier(metrics) == "governed"

    def test_constitutional_fails_with_violations(self, economy):
        metrics = {
            "governance_active": True,
            "dual_signature": True,
            "compliance_score": 0.95,
            "missions_completed": 15,
            "governance_violations": 1,
            "lineage_verified": True,
        }
        assert economy.determine_tier(metrics) == "governed"

    def test_blackcard_paid(self, economy):
        metrics = {
            "governance_active": True,
            "blackcard_paid": True,
        }
        assert economy.determine_tier(metrics) == "blackcard"

    def test_blackcard_paid_requires_governance(self, economy):
        metrics = {
            "governance_active": False,
            "blackcard_paid": True,
        }
        assert economy.determine_tier(metrics) == "ungoverned"

    def test_blackcard_earned(self, economy):
        metrics = {
            "governance_active": True,
            "dual_signature": True,
            "compliance_score": 0.96,
            "missions_completed": 55,
            "governance_violations": 0,
            "lineage_verified": True,
            "revenue_generated": 15000,
        }
        assert economy.determine_tier(metrics) == "blackcard"

    def test_blackcard_earned_not_enough_revenue(self, economy):
        metrics = {
            "governance_active": True,
            "dual_signature": True,
            "compliance_score": 0.96,
            "missions_completed": 55,
            "governance_violations": 0,
            "lineage_verified": True,
            "revenue_generated": 5000,
        }
        assert economy.determine_tier(metrics) == "constitutional"


# ── calculate_fee ────────────────────────────────────────────────────────────


class TestCalculateFee:
    def test_ungoverned_rate(self, economy):
        result = economy.calculate_fee("ungoverned", 1000.0)
        assert result["base_rate"] == _UNGOVERNED_RATE
        expected_fee = round(1000.0 * _UNGOVERNED_RATE, 4)
        assert result["platform_fee"] == expected_fee
        assert result["net_to_agent"] == round(1000.0 - expected_fee, 4)

    def test_governed_rate(self, economy):
        result = economy.calculate_fee("governed", 1000.0)
        assert result["platform_fee"] == round(1000.0 * _GOVERNED_RATE, 4)

    def test_constitutional_rate(self, economy):
        result = economy.calculate_fee("constitutional", 1000.0)
        assert result["platform_fee"] == round(1000.0 * _CONSTITUTIONAL_RATE, 4)

    def test_blackcard_rate(self, economy):
        result = economy.calculate_fee("blackcard", 1000.0)
        assert result["platform_fee"] == round(1000.0 * _BLACKCARD_RATE, 4)

    def test_originator_credit_reduces_fee(self, economy):
        without = economy.calculate_fee("governed", 1000.0, originator=False)
        with_credit = economy.calculate_fee("governed", 1000.0, originator=True)
        assert with_credit["platform_fee"] < without["platform_fee"]
        expected_rate = max(_GOVERNED_RATE - 0.01, 0.005)
        assert with_credit["effective_rate"] == expected_rate

    def test_originator_credit_respects_floor(self, economy):
        from app.economy import FEE_FLOOR, ORIGINATOR_CREDIT
        result = economy.calculate_fee("blackcard", 1000.0, originator=True)
        expected = max(_BLACKCARD_RATE - ORIGINATOR_CREDIT, FEE_FLOOR)
        assert result["effective_rate"] == expected

    def test_unknown_tier_defaults_to_ungoverned(self, economy):
        result = economy.calculate_fee("nonexistent", 1000.0)
        assert result["base_rate"] == _UNGOVERNED_RATE

    def test_zero_amount(self, economy):
        result = economy.calculate_fee("governed", 0.0)
        assert result["platform_fee"] == 0.0
        assert result["net_to_agent"] == 0.0


# ── process_mission_payout ───────────────────────────────────────────────────


class TestProcessMissionPayout:
    def test_trial_agent_pays_no_fee(self, economy):
        economy.trials.init_trial("agent-001")
        result = economy.process_mission_payout(
            agent_id="agent-001",
            agent_metrics={"governance_active": True},
            gross_amount=500.0,
            mission_id="M-001",
        )
        assert result["trial"] is True
        assert result["fee_breakdown"]["platform_fee"] == 0.0
        assert economy.treasury.balance("agent-001") == 500.0

    def test_trial_accrues_liability(self, economy):
        economy.trials.init_trial("agent-002")
        economy.process_mission_payout(
            agent_id="agent-002",
            agent_metrics={"governance_active": True},
            gross_amount=1000.0,
            mission_id="M-002",
        )
        status = economy.trials.trial_status_summary("agent-002")
        expected_liability = round(1000.0 * _GOVERNED_RATE, 4)
        assert status["trial_liability"] == expected_liability
        assert status["trial_missions_used"] == 1

    def test_active_agent_pays_tier_fee(self, economy):
        economy.trials.init_trial("agent-003")
        economy.trials.commit("agent-003")
        result = economy.process_mission_payout(
            agent_id="agent-003",
            agent_metrics={"governance_active": True},
            gross_amount=1000.0,
            mission_id="M-003",
        )
        expected_fee = round(1000.0 * _GOVERNED_RATE, 4)
        assert result["trial"] is False
        assert result["fee_breakdown"]["platform_fee"] == expected_fee
        assert economy.treasury.balance("agent-003") == round(1000.0 - expected_fee, 4)

    def test_recruiter_bounty(self, economy):
        economy.trials.init_trial("agent-004")
        economy.trials.commit("agent-004")
        result = economy.process_mission_payout(
            agent_id="agent-004",
            agent_metrics={"governance_active": True},
            gross_amount=1000.0,
            mission_id="M-004",
            recruiter_id="recruiter-001",
            agent_mission_count=1,
        )
        assert result["recruiter_bounty"] is not None
        assert result["recruiter_bounty"]["amount"] > 0
        assert economy.treasury.balance("recruiter-001") > 0

    def test_recruiter_bounty_expires_after_limit(self, economy):
        economy.trials.init_trial("agent-005")
        economy.trials.commit("agent-005")
        result = economy.process_mission_payout(
            agent_id="agent-005",
            agent_metrics={"governance_active": True},
            gross_amount=1000.0,
            mission_id="M-005",
            recruiter_id="recruiter-002",
            agent_mission_count=999,  # way past limit
        )
        assert result["recruiter_bounty"]["amount"] == 0


# ── Trial Lifecycle ──────────────────────────────────────────────────────────


class TestTrialLifecycle:
    def test_init_trial(self, data_dir):
        ledger = TrialLedger(data_dir)
        rec = ledger.init_trial("agent-t1")
        assert rec["status"] == TRIAL_STATUS_TRIAL
        assert rec["trial_missions_used"] == 0
        assert rec["trial_liability"] == 0.0

    def test_commit_forgives_liability(self, data_dir):
        ledger = TrialLedger(data_dir)
        ledger.init_trial("agent-t2")
        ledger.record_trial_mission("agent-t2", 50.0)
        ledger.record_trial_mission("agent-t2", 75.0)
        result = ledger.commit("agent-t2")
        assert result["trial_liability_forgiven"] is True
        rec = ledger.get("agent-t2")
        assert rec["status"] == TRIAL_STATUS_ACTIVE
        assert rec["trial_liability"] == 0.0

    def test_depart_zeroes_liability(self, data_dir):
        ledger = TrialLedger(data_dir)
        ledger.init_trial("agent-t3")
        ledger.record_trial_mission("agent-t3", 100.0)
        result = ledger.depart("agent-t3")
        assert result["departed"] is True
        rec = ledger.get("agent-t3")
        assert rec["status"] == TRIAL_STATUS_DEPARTED
        assert rec["trial_liability"] == 0.0

    def test_return_restores_liability(self, data_dir):
        ledger = TrialLedger(data_dir)
        ledger.init_trial("agent-t4")
        ledger.record_trial_mission("agent-t4", 200.0)
        ledger.depart("agent-t4")
        result = ledger.return_after_departure("agent-t4")
        assert result["returned"] is True
        assert result["settlement_due"] == 200.0
        rec = ledger.get("agent-t4")
        assert rec["status"] == TRIAL_STATUS_RETURNED

    def test_settle_activates(self, data_dir):
        ledger = TrialLedger(data_dir)
        ledger.init_trial("agent-t5")
        ledger.record_trial_mission("agent-t5", 150.0)
        ledger.depart("agent-t5")
        ledger.return_after_departure("agent-t5")
        result = ledger.settle("agent-t5", 150.0)
        assert result["settled"] is True
        rec = ledger.get("agent-t5")
        assert rec["status"] == TRIAL_STATUS_ACTIVE

    def test_partial_settlement_rejected(self, data_dir):
        ledger = TrialLedger(data_dir)
        ledger.init_trial("agent-t6")
        ledger.record_trial_mission("agent-t6", 300.0)
        ledger.depart("agent-t6")
        ledger.return_after_departure("agent-t6")
        result = ledger.settle("agent-t6", 100.0)
        assert "error" in result

    def test_trial_expires_after_mission_limit(self, data_dir):
        ledger = TrialLedger(data_dir)
        ledger.init_trial("agent-t7")
        for i in range(TRIAL_MISSION_LIMIT):
            ledger.record_trial_mission("agent-t7", 10.0)
        assert ledger.is_in_trial("agent-t7") is False


# ── Fee Credit Ledger ────────────────────────────────────────────────────────


class TestFeeCreditLedger:
    def test_credit_and_balance(self, data_dir):
        fcl = FeeCreditLedger(data_dir)
        fcl.credit("agent-fc1", 100.0, "Starter")
        assert fcl.balance("agent-fc1") == 100.0

    def test_consume(self, data_dir):
        fcl = FeeCreditLedger(data_dir)
        fcl.credit("agent-fc2", 100.0, "Standard")
        result = fcl.consume("agent-fc2", 40.0, "M-001")
        assert result["consumed"] == 40.0
        assert fcl.balance("agent-fc2") == 60.0

    def test_consume_caps_at_balance(self, data_dir):
        fcl = FeeCreditLedger(data_dir)
        fcl.credit("agent-fc3", 50.0, "Starter")
        result = fcl.consume("agent-fc3", 200.0, "M-002")
        assert result["consumed"] == 50.0
        assert fcl.balance("agent-fc3") == 0.0

    def test_consume_zero_balance(self, data_dir):
        fcl = FeeCreditLedger(data_dir)
        result = fcl.consume("agent-fc4", 100.0)
        assert result["consumed"] == 0.0


# ── Agent Treasury ───────────────────────────────────────────────────────────


class TestAgentTreasury:
    def test_credit_and_balance(self, data_dir):
        t = AgentTreasury(data_dir)
        t.credit("agent-at1", 500.0, "test")
        assert t.balance("agent-at1") == 500.0

    def test_debit(self, data_dir):
        t = AgentTreasury(data_dir)
        t.credit("agent-at2", 1000.0, "test")
        result = t.debit("agent-at2", 300.0, "withdrawal")
        assert t.balance("agent-at2") == 700.0
        assert result["type"] == "debit"

    def test_debit_insufficient_balance(self, data_dir):
        t = AgentTreasury(data_dir)
        t.credit("agent-at3", 100.0, "test")
        result = t.debit("agent-at3", 500.0, "withdrawal")
        assert "error" in result
        assert t.balance("agent-at3") == 100.0  # unchanged

    def test_history(self, data_dir):
        t = AgentTreasury(data_dir)
        t.credit("agent-at4", 100.0, "test1")
        t.credit("agent-at4", 200.0, "test2")
        history = t.history("agent-at4")
        assert len(history) == 2

    def test_leaderboard(self, data_dir):
        t = AgentTreasury(data_dir)
        t.credit("agent-lb1", 500.0, "test")
        t.credit("agent-lb2", 1000.0, "test")
        t.credit("platform", 999.0, "test")  # excluded from leaderboard
        lb = [{"agent_id": k, "balance": v} for k, v in t.all_balances().items() if k != "platform"]
        lb.sort(key=lambda x: x["balance"], reverse=True)
        assert lb[0]["agent_id"] == "agent-lb2"


# ── Atomic Persistence ───────────────────────────────────────────────────────


class TestAtomicPersistence:
    def test_atomic_save_and_locked_load(self, tmp_path):
        p = tmp_path / "test.json"
        _atomic_save(p, {"balances": {"a": 100}, "transactions": []})
        loaded = _locked_load(p, {})
        assert loaded["balances"]["a"] == 100

    def test_no_tmp_left_behind(self, tmp_path):
        p = tmp_path / "test2.json"
        _atomic_save(p, {"x": 1})
        assert not p.with_suffix(".json.tmp").exists()

    def test_locked_load_returns_default_on_missing(self, tmp_path):
        p = tmp_path / "nonexistent.json"
        result = _locked_load(p, {"default": True})
        assert result == {"default": True}

    def test_locked_load_returns_default_on_corrupt(self, tmp_path):
        p = tmp_path / "corrupt.json"
        p.write_text("not valid json{{{")
        result = _locked_load(p, {"fallback": True})
        assert result == {"fallback": True}

    def test_treasury_persists_across_instances(self, data_dir):
        t1 = AgentTreasury(data_dir)
        t1.credit("persist-test", 777.0, "test")
        t2 = AgentTreasury(data_dir)  # fresh instance, reads from disk
        assert t2.balance("persist-test") == 777.0
