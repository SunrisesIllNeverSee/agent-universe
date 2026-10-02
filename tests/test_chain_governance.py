"""ST-020 regression tests for pre-execution chain governance."""
from types import SimpleNamespace

from app.chains import MultiChainRouter


def _runtime(posture: str):
    return SimpleNamespace(
        governance=SimpleNamespace(mode="CONSTITUTIONAL", posture=posture, role="operator")
    )


def test_chain_transfer_blocked_in_scout_before_execution():
    router = MultiChainRouter(_runtime("SCOUT"))

    result = router.transfer("offchain", "recipient", 100.0, "USD", agent_id="agent-1")

    assert result["status"] == "BLOCKED"
    assert "SCOUT" in result["reason"]


def test_chain_transfer_requires_confirmation_in_defense():
    router = MultiChainRouter(_runtime("DEFENSE"))

    held = router.transfer("offchain", "recipient", 100.0, "USD", agent_id="agent-1")
    assert held["status"] == "AWAITING_CONFIRMATION"

    confirmed = router.transfer(
        "offchain", "recipient", 100.0, "USD", agent_id="agent-1", confirm=True
    )
    assert confirmed["status"] == "PROCESSED"
