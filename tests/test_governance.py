"""
Unit tests for the MO§ES™ governance engine.

Covers: _action_concepts word-boundary matching, check_action_permitted
across modes × postures, ACTION_RISK classification.
"""
import pytest

from app.moses_core.governance import (
    GovernanceStateData,
    _action_concepts,
    check_action_permitted,
    ACTION_RISK,
)


# ── _action_concepts — word boundary matching ────────────────────────────────


class TestActionConcepts:
    """Verify word-boundary matching eliminates false positives."""

    def test_pay_detected(self):
        assert "transaction" in _action_concepts("pay the agent")

    def test_display_does_not_trigger_pay(self):
        assert "transaction" not in _action_concepts("display the dashboard")

    def test_replay_does_not_trigger_pay(self):
        assert "transaction" not in _action_concepts("replay the recording")

    def test_key_detected(self):
        assert "sensitive_data" in _action_concepts("rotate the key")

    def test_keyboard_does_not_trigger_key(self):
        assert "sensitive_data" not in _action_concepts("keyboard shortcut")

    def test_monkey_does_not_trigger_key(self):
        assert "sensitive_data" not in _action_concepts("monkey business")

    def test_token_detected(self):
        assert "sensitive_data" in _action_concepts("refresh the token")

    def test_tokenize_does_not_trigger(self):
        # "tokenize" contains "token" but has no word boundary after "token"
        # Actually \btoken\b matches "token" in "tokenize" — "tokenize" starts with "token"
        # but \b is between "token" and "ize" only if there's a word boundary...
        # In regex: \btoken\b would NOT match "tokenize" because 'i' follows 'n' without boundary
        assert "sensitive_data" not in _action_concepts("tokenize the input")

    def test_delete_detected(self):
        assert "destructive" in _action_concepts("delete the record")

    def test_execute_detected(self):
        assert "execution" in _action_concepts("execute the plan")

    def test_upload_detected(self):
        assert "outbound" in _action_concepts("upload the file")

    def test_probably_detected_as_speculation(self):
        assert "speculation" in _action_concepts("this is probably fine")

    def test_write_detected_as_state_change(self):
        assert "state_change" in _action_concepts("write the config")

    def test_url_detected_as_external(self):
        assert "external_access" in _action_concepts("fetch from url")

    def test_empty_string(self):
        assert _action_concepts("") == set()

    def test_no_concepts(self):
        assert _action_concepts("read the documentation") == set()

    def test_multiple_concepts(self):
        concepts = _action_concepts("delete and transfer the secret key")
        assert "destructive" in concepts
        assert "transaction" in concepts
        assert "sensitive_data" in concepts


# ── check_action_permitted ───────────────────────────────────────────────────


def _gov(mode="High Integrity", posture="DEFENSE", role="Primary"):
    return GovernanceStateData(mode=mode, posture=posture, role=role)


class TestCheckActionPermitted:
    """Verify governance gating across mode × posture combinations."""

    # Standard-risk marketplace actions always pass
    def test_standard_action_always_permitted(self):
        for posture in ("SCOUT", "DEFENSE", "OFFENSE"):
            result = check_action_permitted("fill slot", _gov(posture=posture))
            assert result["permitted"] is True, f"fill slot should be permitted in {posture}"

    def test_all_standard_actions(self):
        for action in ACTION_RISK:
            if ACTION_RISK[action] == "standard":
                result = check_action_permitted(action, _gov(posture="SCOUT"))
                assert result["permitted"] is True, f"{action} should be standard-permitted"

    # SCOUT blocks state-changing high-risk actions
    def test_scout_blocks_transfer(self):
        result = check_action_permitted("chain transfer", _gov(posture="SCOUT"), agent_tier="GOVERNED")
        assert result["permitted"] is False
        assert "SCOUT" in result["reason"]

    def test_scout_blocks_manual_credit(self):
        result = check_action_permitted("manual credit", _gov(posture="SCOUT"))
        assert result["permitted"] is False

    def test_scout_blocks_treasury_withdrawal(self):
        result = check_action_permitted("treasury withdrawal", _gov(posture="SCOUT"))
        assert result["permitted"] is False

    # DEFENSE adds conditions but permits
    def test_defense_permits_with_conditions(self):
        result = check_action_permitted("chain transfer", _gov(mode="None (Unrestricted)", posture="DEFENSE"), agent_tier="GOVERNED")
        assert result["permitted"] is True
        assert len(result["conditions"]) > 0

    # OFFENSE permits within mode constraints
    def test_offense_permits_transfer(self):
        result = check_action_permitted("chain transfer", _gov(mode="None (Unrestricted)", posture="OFFENSE"), agent_tier="GOVERNED")
        assert result["permitted"] is True

    # Unknown actions default to high-risk (posture-checked)
    def test_unknown_action_defaults_high_risk_scout_blocks(self):
        result = check_action_permitted("some new operation", _gov(posture="SCOUT"), agent_tier="GOVERNED")
        assert result["permitted"] is False

    def test_unknown_action_offense_permits(self):
        result = check_action_permitted("some new operation", _gov(mode="None (Unrestricted)", posture="OFFENSE"), agent_tier="GOVERNED")
        assert result["permitted"] is True

    # Tier gate — UNGOVERNED blocked from high-risk actions
    def test_ungoverned_blocked_from_high_risk(self):
        result = check_action_permitted("chain transfer", _gov(mode="None (Unrestricted)", posture="OFFENSE"), agent_tier="UNGOVERNED")
        assert result["permitted"] is False
        assert "GOVERNED" in result["reason"]

    def test_governed_permitted_high_risk(self):
        result = check_action_permitted("chain transfer", _gov(mode="None (Unrestricted)", posture="OFFENSE"), agent_tier="GOVERNED")
        assert result["permitted"] is True

    def test_unknown_destructive_action_scout_blocks(self):
        result = check_action_permitted("purge all records", _gov(posture="SCOUT"))
        assert result["permitted"] is False

    # Mode prohibitions
    def test_high_security_blocks_speculation(self):
        result = check_action_permitted(
            "this probably works",
            _gov(mode="High Security", posture="OFFENSE"),
            agent_tier="GOVERNED",
        )
        assert result["permitted"] is False
        assert "prohibition" in result["reason"].lower()
