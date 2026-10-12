"""Decision 11: Refinery cards must not fabricate 0.00 scores.

/api/metrics publishes no `aggregates` (Phase 6 is gated), so the four score
cards render "Not yet measured"; Active Agents stays a live count.
"""
from pathlib import Path

PAGE = Path(__file__).resolve().parents[1] / "frontend" / "refinery.html"


def test_metrics_endpoint_publishes_no_aggregates(client):
    r = client.get("/api/metrics")
    assert r.status_code == 200
    assert "aggregates" not in r.json()


def test_score_cards_do_not_default_to_zero():
    src = PAGE.read_text()
    assert "|| 0, 1)" not in src
    assert "Not yet measured" in src
    for field in ("avg_compliance_score", "avg_performance_score",
                  "avg_governance_adherence", "avg_output_quality"):
        assert f"setScore(" in src and field in src


def test_active_agents_still_live():
    src = PAGE.read_text()
    assert "setMetric('m-agents', 'mb-agents', active, 50)" in src

