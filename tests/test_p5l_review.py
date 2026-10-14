"""test_p5l_review.py -- adversarial-review fixes on the p5k Stripe approvals / recovery / operator UI.

* a needs_review approval that was stuck mid-refund can never pay, and refunds at most once
* re-approving a Stripe approval stuck mid-transfer replays the same idempotency key (no second transfer)
* an inactive agent's needs_review approval is not auto-refunded or paid by an 'approve' click
* the operator page carries no third-party scripts (it holds the admin key) and never innerHTMLs data
"""
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app import kassa_payments
from app.deps import state
from tests.test_p5_money_path import ADMIN
from tests.test_p5i_wallet_safety import _bal, _stub_router, _setup as _chain_setup, _wd  # noqa: F401
from tests.test_p5k_stripe_new_dest_cap import _bal as _sbal, _co, _setup as _stripe_setup, stripe  # noqa: F401

PAGE = Path(__file__).resolve().parents[1] / "frontend" / "admin-payouts.html"


def _stick(apid, status, minutes_ago=30):
    at = (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()
    state.wallets._conn.execute("UPDATE payout_approvals SET status=?, decided_at=?, decided_by='operator' "
                                "WHERE approval_id=?", (status, at, apid))


def _sweep(client):
    assert client.post("/api/operator/payout-approvals/sweep", headers=ADMIN).status_code == 200


def _chain_approval(client):
    aid, jwt, wid = _chain_setup(client)
    r = _wd(client, jwt, wid, 40)
    assert r.status_code in (200, 202) and "approval_id" in r.json(), r.text
    apid = r.json()["approval_id"]
    return aid, apid


def _approve(client, apid):
    return client.post(f"/api/operator/payout-approvals/{apid}/approve", headers=ADMIN)


def _reject(client, apid):
    return client.post(f"/api/operator/payout-approvals/{apid}/reject", headers=ADMIN)


# ── refund at most once ──────────────────────────────────────────────────────

def test_reject_after_refund_already_landed_does_not_double_credit(client, _stub_router):
    aid, apid = _chain_approval(client)
    a = state.wallets.get_approval(apid)
    # process died after the refund credit but before settle: ledger already holds it
    state.economy.treasury.credit(aid, a["amount"], reason="withdrawal_reserve_refund", mission_id=f"rev-{a['reserve_txn']}")
    before = _bal(aid)
    _stick(apid, "rejecting")
    _sweep(client)
    assert state.wallets.get_approval(apid)["status"] == "needs_review"
    assert _reject(client, apid).status_code == 200
    assert _bal(aid) == before                      # no second refund
    assert state.wallets.get_approval(apid)["status"] == "rejected"


def test_normal_reject_still_refunds_once(client, _stub_router):
    aid, apid = _chain_approval(client)
    before = _bal(aid)
    assert _reject(client, apid).status_code == 200
    assert _bal(aid) == before + 40
    assert _reject(client, apid).status_code == 409
    assert _bal(aid) == before + 40


def test_needs_review_from_rejecting_cannot_be_approved(client, _stub_router):
    aid, apid = _chain_approval(client)
    _stick(apid, "rejecting")
    _sweep(client)
    r = _approve(client, apid)
    assert r.status_code == 409 and _stub_router.calls == []
    assert state.wallets.get_approval(apid)["status"] == "needs_review"


def test_needs_review_from_approving_can_still_be_approved(client, _stub_router):
    aid, apid = _chain_approval(client)
    _stick(apid, "approving")
    _sweep(client)
    assert state.wallets.get_approval(apid)["review_from"] == "approving"
    assert _approve(client, apid).status_code == 200 and len(_stub_router.calls) == 1


# ── inactive agent + needs_review ────────────────────────────────────────────

def test_inactive_agent_needs_review_is_not_auto_refunded_or_paid(client, _stub_router):
    aid, apid = _chain_approval(client)
    _stick(apid, "approving")
    _sweep(client)
    entry = next(r for r in state.runtime.registry if r["agent_id"] == aid)
    entry["status"] = "suspended"
    before = _bal(aid)
    try:
        r = _approve(client, apid)
    finally:
        entry["status"] = "active"
    assert r.status_code == 409 and _stub_router.calls == []
    assert state.wallets.get_approval(apid)["status"] == "needs_review"   # untouched; operator decides
    assert _bal(aid) == before                                            # no automatic refund while a transfer may be out


# ── Stripe idempotency ───────────────────────────────────────────────────────

def test_stripe_reapprove_after_stuck_replays_same_idempotency_key(client, stripe):
    aid, jwt, acct = _stripe_setup(client)
    apr = _co(client, jwt, 60).json()["approval_id"]
    assert _approve(client, apr).status_code == 200
    first = stripe[0]["idempotency_key"]
    # process died after Stripe accepted the transfer but before we recorded it
    state.wallets._conn.execute("UPDATE payout_approvals SET status='approving', decided_at=? WHERE approval_id=?",
                                ((datetime.now(UTC) - timedelta(minutes=30)).isoformat(), apr))
    _sweep(client)
    assert _approve(client, apr).status_code == 200
    assert stripe[1]["idempotency_key"] == first and apr in first
    assert stripe[1]["connected_account_id"] == acct


def test_stripe_key_advances_only_after_definitive_refusal(client, stripe, monkeypatch):
    aid, jwt, _ = _stripe_setup(client)
    apr = _co(client, jwt, 60).json()["approval_id"]
    keys = []

    def fail(kind):
        def f(**kw):
            keys.append(kw["idempotency_key"])
            return {"error": "nope", "type": kind}
        return f
    monkeypatch.setattr(kassa_payments, "create_transfer", fail("InvalidRequestError"))
    assert _approve(client, apr).status_code == 502
    assert _approve(client, apr).status_code == 502
    assert keys[0] != keys[1]                       # definitive refusal: retry is not replayed
    monkeypatch.setattr(kassa_payments, "create_transfer", fail("APIConnectionError"))
    assert _approve(client, apr).status_code == 502
    assert _approve(client, apr).status_code == 502
    assert keys[2] == keys[3]                       # ambiguous failure: same key, the transfer may have gone out
    assert state.wallets.get_approval(apr)["status"] == "pending" and _sbal(aid) == 140


def test_create_transfer_passes_idempotency_key_to_stripe(monkeypatch):
    seen = {}

    class T:
        id, amount, destination = "tr_1", 100, "acct_x"

    class Fake:
        class Transfer:
            @staticmethod
            def create(**kw):
                seen.update(kw)
                return T()
        class error:  # noqa: N801
            class StripeError(Exception):
                pass
    monkeypatch.setattr(kassa_payments, "_stripe_ready", True)
    monkeypatch.setattr(kassa_payments, "_stripe_module", Fake)
    out = kassa_payments.create_transfer(amount_cents=100, connected_account_id="acct_x", idempotency_key="k1")
    assert out["transfer_id"] == "tr_1" and seen["idempotency_key"] == "k1"
    seen.clear()
    kassa_payments.create_transfer(amount_cents=100, connected_account_id="acct_x")
    assert "idempotency_key" not in seen


# ── operator page ────────────────────────────────────────────────────────────

def test_operator_page_has_no_third_party_scripts():
    src = PAGE.read_text()
    for host in ("googletagmanager", "posthog", "google-analytics"):
        assert host not in src
    # only first-party scripts remain
    for m in re.findall(r'<script[^>]+src="([^"]+)"', src):
        assert m.startswith("/"), m


def test_operator_page_never_innerhtmls_data():
    src = PAGE.read_text()
    for m in re.finditer(r"innerHTML\s*=\s*([^;]+);", src):
        rhs = m.group(1).strip()
        assert re.fullmatch(r"'[^'+]*'", rhs) or re.fullmatch(r'"[^"+]*"', rhs), rhs   # literal only, no concatenation
    assert "document.write" not in src and "outerHTML" not in src and "insertAdjacentHTML" not in src
