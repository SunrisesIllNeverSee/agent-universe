"""
test_p5_fee_semblance.py — config/economic_rates.json is the single source of truth for fees.

Phase 5 slice 1: no rate changes. Every surface that states a fee must read it
from config (via app.economy) instead of a hard-coded number.
"""
import json
import uuid
from pathlib import Path

from app import economy, kassa_payments
from tests.conftest import signup_agent

ROOT = Path(__file__).resolve().parents[1]
RATES = json.loads((ROOT / "config" / "economic_rates.json").read_text())


def test_live_tier_rates_come_from_config():
    for tier, cfg in RATES["tiers"].items():
        assert economy.TIERS[tier]["fee_rate"] == cfg["fee_rate"]


def test_trial_constants_come_from_config():
    assert economy.TRIAL_MISSION_LIMIT == RATES["trial"]["mission_limit"]
    assert economy.TRIAL_DAY_LIMIT == RATES["trial"]["day_limit"]
    assert economy.TRIAL_FEE_RATE == RATES["trial"]["fee_rate"]


def test_fee_split_declared_and_sums_to_one():
    split = RATES["fee_split"]
    legs = [v for k, v in split.items() if not k.startswith("_")]
    assert abs(sum(legs) - 1.0) < 1e-9
    assert split["contribution_royalties"] == 0.30


def test_target_rates_are_not_live():
    target = {k: v for k, v in RATES["target_tier_rates"].items() if not k.startswith("_")}
    assert target == {"ungoverned": 0.15, "governed": 0.10, "constitutional": 0.05, "blackcard": 0.02}


def test_stripe_default_app_fee_matches_config():
    expected = int(round(RATES["tiers"]["ungoverned"]["fee_rate"] * 100))
    assert kassa_payments.DEFAULT_APP_FEE_PERCENT == expected


def test_signup_response_states_config_rates(client):
    r = signup_agent(client, name=f"FeeBot-{uuid.uuid4().hex[:6]}", ip=f"10.9.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}")
    assert r.status_code == 200
    data = r.json()
    assert data["fee_rate"] == RATES["tiers"]["ungoverned"]["fee_rate"]
    assert data["trial"]["missions_remaining"] == RATES["trial"]["mission_limit"]
    assert data["trial"]["days_remaining"] == RATES["trial"]["day_limit"]
    assert "CIVITAS" in data["trial"]["note"]


def test_no_hardcoded_fee_fallbacks_left():
    for rel in ("app/mcp_bridge.py", "app/routes/agents.py", "app/routes/provision.py"):
        src = (ROOT / rel).read_text()
        assert '"fee_rate", 0.15)' not in src, rel
        assert '"fee_rate": 0.05,' not in src, rel
    assert "Governed (5%)" not in (ROOT / "app/mcp_bridge.py").read_text()
