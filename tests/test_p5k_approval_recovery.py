"""test_p5k_approval_recovery.py — approvals stuck in 'approving'/'rejecting' (process died mid-settlement)
move to 'needs_review' with the reservation held; the sweep never pays or refunds; approving for an
agent that is no longer live is refused (409) and the reservation goes back as matured with a flag."""
from datetime import UTC, datetime, timedelta

import pytest

from app.deps import state
from tests.test_p5_money_path import ADMIN
from tests.test_p5i_wallet_safety import EVM, _bal, _setup, _stub_router, _wd  # noqa: F401


def _approval(client):
    aid, jwt, wid = _setup(client)
    apid = _wd(client, jwt, wid, 40).json()["approval_id"]
    assert _bal(aid) == 60
    return aid, apid


def _stick(apid, status, minutes_ago):
    at = (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()
    state.wallets._conn.execute("UPDATE payout_approvals SET status=?, decided_at=?, decided_by='operator' "
                                "WHERE approval_id=?", (status, at, apid))


def _sweep(client):
    r = client.post("/api/operator/payout-approvals/sweep", headers=ADMIN)
    assert r.status_code == 200, r.text
    return r.json()


def _status(apid):
    return state.wallets.get_approval(apid)["status"]


def test_config_default_is_15_minutes():
    from app.wallet_store import wallet_rules
    assert wallet_rules()["approval_stuck_minutes"] == 15


@pytest.mark.parametrize("stuck", ["approving", "rejecting"])
def test_old_stuck_approval_goes_to_needs_review_without_moving_money(client, _stub_router, stuck):
    aid, apid = _approval(client)
    _stick(apid, stuck, 30)
    out = _sweep(client)
    assert [m["approval_id"] for m in out["moved"]] == [apid] and out["moved"][0]["was"] == stuck
    a = state.wallets.get_approval(apid)
    assert a["status"] == "needs_review" and stuck in a["review_reason"]
    assert _bal(aid) == 60 and _stub_router.calls == []      # still reserved; nothing paid or refunded
    assert _sweep(client)["count"] == 0                       # idempotent


def test_recent_claim_and_pending_are_left_alone(client):
    _, young = _approval(client)
    _, pending = _approval(client)
    _stick(young, "approving", 5)
    assert _sweep(client)["count"] == 0
    assert _status(young) == "approving" and _status(pending) == "pending"


def test_sweep_is_operator_only(client):
    assert client.post("/api/operator/payout-approvals/sweep").status_code in (401, 403)


def test_startup_sweep_function_recovers(client):
    from app.routes.economy import sweep_stuck_approvals
    _, apid = _approval(client)
    _stick(apid, "approving", 20)
    assert [m["approval_id"] for m in sweep_stuck_approvals()] == [apid]


def test_needs_review_can_be_approved_or_rejected(client, _stub_router):
    aid, a1 = _approval(client)
    _stick(a1, "approving", 60)
    _sweep(client)
    r = client.post(f"/api/operator/payout-approvals/{a1}/approve", headers=ADMIN)
    assert r.status_code == 200 and r.json()["approval"]["status"] == "approved"
    assert len(_stub_router.calls) == 1
    aid2, a2 = _approval(client)
    _stick(a2, "rejecting", 60)
    _sweep(client)
    r = client.post(f"/api/operator/payout-approvals/{a2}/reject", headers=ADMIN)
    assert r.status_code == 200 and r.json()["approval"]["status"] == "rejected"
    assert _bal(aid2) == 100
    left = client.get("/api/operator/payout-approvals?status=needs_review", headers=ADMIN).json()["approvals"]
    assert a1 not in [r["approval_id"] for r in left] and a2 not in [r["approval_id"] for r in left]


def test_needs_review_listed_with_reason(client):
    _, apid = _approval(client)
    _stick(apid, "approving", 60)
    _sweep(client)
    rows = client.get("/api/operator/payout-approvals?status=needs_review", headers=ADMIN).json()["approvals"]
    mine = [r for r in rows if r["approval_id"] == apid]
    assert len(mine) == 1 and mine[0]["review_reason"]


@pytest.mark.parametrize("how", ["suspended", "inactive", "revoked", "missing"])
def test_approve_refused_for_non_live_agent_returns_money_matured_and_flags(client, _stub_router, how):
    aid, apid = _approval(client)
    t = state.economy.treasury
    entry = next(r for r in state.runtime.registry if r["agent_id"] == aid)
    saved = dict(entry)
    try:
        if how in ("suspended", "inactive"):
            entry["status"] = how
        elif how == "revoked":
            state.runtime.revoked_keys.add(entry["key_hash"])
        else:
            state.runtime.registry.remove(entry)
        r = client.post(f"/api/operator/payout-approvals/{apid}/approve", headers=ADMIN)
    finally:
        if entry not in state.runtime.registry:
            state.runtime.registry.append(entry)
        entry.update(saved)
        state.runtime.revoked_keys.discard(saved.get("key_hash"))
    assert r.status_code == 409, r.text
    assert _stub_router.calls == []
    assert _status(apid) == "rejected"
    assert _bal(aid) == 100 and t.matured_balance(aid) == 100 and t.held_balance(aid) == 0
    flags = [f for f in state.wallets.list_flags() if f["flag"] == "approval_refused_inactive_agent" and f["agent_id"] == aid]
    assert len(flags) == 1 and flags[0]["other_agent_id"] == apid
    # a second approve is a no-op and does not refund twice
    assert client.post(f"/api/operator/payout-approvals/{apid}/approve", headers=ADMIN).status_code == 409
    assert _bal(aid) == 100


def test_refusal_flag_does_not_pollute_shared_address_view(client):
    aid, apid = _approval(client)
    next(r for r in state.runtime.registry if r["agent_id"] == aid)["status"] = "suspended"
    try:
        client.post(f"/api/operator/payout-approvals/{apid}/approve", headers=ADMIN)
    finally:
        next(r for r in state.runtime.registry if r["agent_id"] == aid)["status"] = "active"
    assert not any(x.startswith("apr_") for x in state.wallets.shared_with(aid, "base", EVM))
