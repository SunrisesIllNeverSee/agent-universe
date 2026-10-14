"""test_p5k_stripe_recovery.py — stripe-kind approvals go through the stuck-approval sweep and the
inactive-agent refusal, and the operator screen / docs cover them."""
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.deps import state
from tests.test_p5_money_path import ADMIN
from tests.test_p5k_stripe_new_dest_cap import _bal, _co, _setup, stripe  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent


def _stick(apid, status):
    at = (datetime.now(UTC) - timedelta(minutes=45)).isoformat()
    state.wallets._conn.execute("UPDATE payout_approvals SET status=?, decided_at=? WHERE approval_id=?", (status, at, apid))


def test_stuck_stripe_approval_swept_then_operator_can_approve(client, stripe):
    aid, jwt, acct = _setup(client)
    apid = _co(client, jwt, 60).json()["approval_id"]
    _stick(apid, "approving")
    out = client.post("/api/operator/payout-approvals/sweep", headers=ADMIN).json()
    assert [m["approval_id"] for m in out["moved"]] == [apid]
    a = state.wallets.get_approval(apid)
    assert a["status"] == "needs_review" and a["kind"] == "stripe" and a["review_reason"]
    assert stripe == [] and _bal(aid) == 140
    listed = client.get("/api/operator/payout-approvals?status=needs_review", headers=ADMIN).json()["approvals"]
    assert any(x["approval_id"] == apid and x["kind"] == "stripe" for x in listed)
    r = client.post(f"/api/operator/payout-approvals/{apid}/approve", headers=ADMIN)
    assert r.status_code == 200 and len(stripe) == 1 and stripe[0]["connected_account_id"] == acct


def test_stripe_approval_refused_for_suspended_agent_refunds_matured(client, stripe):
    aid, jwt, _ = _setup(client)
    apid = _co(client, jwt, 60).json()["approval_id"]
    entry = next(r for r in state.runtime.registry if r["agent_id"] == aid)
    entry["status"] = "suspended"
    try:
        r = client.post(f"/api/operator/payout-approvals/{apid}/approve", headers=ADMIN)
    finally:
        entry["status"] = "active"
    assert r.status_code == 409, r.text
    assert stripe == [] and state.wallets.get_approval(apid)["status"] == "rejected"
    assert _bal(aid) == 200 and state.economy.treasury.matured_balance(aid) == 200


def test_ui_and_docs_cover_stripe_and_needs_review():
    html = (ROOT / "frontend" / "admin-payouts.html").read_text(encoding="utf-8")
    assert "stripe cashout" in html and "needs_review" in html and "review_reason" in html
    for f in ("skill.md", "openapi.json", "openapi.yaml"):
        t = (ROOT / "frontend" / f).read_text(encoding="utf-8")
        assert "needs_review" in t and "wallets.approval_stuck_minutes" in t and "Stripe cashout" in t, f
