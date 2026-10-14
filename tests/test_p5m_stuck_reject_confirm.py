"""test_p5m_stuck_reject_confirm.py -- rejecting an approval stuck in 'approving' (a transfer may already
have gone out) needs the operator's confirmation that they checked Stripe / the chain; a Stripe transfer
that can be found blocks the reject outright."""
from pathlib import Path

import pytest

from app import kassa_payments
from app.deps import state
from tests.test_p5_money_path import ADMIN
from tests.test_p5l_review import _stick, _sweep, _chain_approval, _bal, _stub_router  # noqa: F401
from tests.test_p5k_stripe_new_dest_cap import _bal as _sbal, _co, _setup as _stripe_setup, stripe  # noqa: F401

PAGE = Path(__file__).resolve().parents[1] / "frontend" / "admin-payouts.html"


def _rej(client, apid, body=None):
    return client.post(f"/api/operator/payout-approvals/{apid}/reject", headers=ADMIN, **({"json": body} if body is not None else {}))


@pytest.fixture
def lookup(monkeypatch):
    box = {"r": {"found": False}, "calls": []}

    def f(approval_id, account):
        box["calls"].append((approval_id, account))
        return box["r"]
    monkeypatch.setattr(kassa_payments, "find_transfer_by_approval", f)
    return box


def _stripe_stuck(client):
    aid, jwt, _ = _stripe_setup(client)
    apid = _co(client, jwt, 60).json()["approval_id"]
    _stick(apid, "approving")
    _sweep(client)
    assert state.wallets.get_approval(apid)["status"] == "needs_review"
    return aid, apid


def test_stripe_reject_without_confirmation_is_409_with_key(client, stripe, lookup):
    aid, apid = _stripe_stuck(client)
    for body in (None, {}, {"checked_stripe": False}, {"checked_stripe": "true"}, {"checked_chain": True}):
        r = _rej(client, apid, body)
        assert r.status_code == 409, r.text
        assert apid in r.json()["error"] and "Stripe dashboard" in r.json()["error"]
        assert r.json()["idempotency_key"] == f"p5l-approval-{apid}-0"
    assert state.wallets.get_approval(apid)["status"] == "needs_review" and _sbal(aid) == 140


def test_stripe_reject_with_confirmation_refunds_and_records(client, stripe, lookup):
    aid, apid = _stripe_stuck(client)
    r = _rej(client, apid, {"checked_stripe": True})
    assert r.status_code == 200, r.text
    a = state.wallets.get_approval(apid)
    assert a["status"] == "rejected" and _sbal(aid) == 200
    assert a["reject_confirmed_by"] == "operator" and a["reject_confirmed_at"] and a["reject_confirmed_what"] == "checked_stripe"


def test_stripe_reject_refused_outright_when_transfer_exists(client, stripe, lookup):
    aid, apid = _stripe_stuck(client)
    lookup["r"] = {"found": True, "transfer_id": "tr_real"}
    r = _rej(client, apid, {"checked_stripe": True})
    assert r.status_code == 409 and "tr_real" in r.json()["error"]
    assert state.wallets.get_approval(apid)["status"] == "needs_review" and _sbal(aid) == 140
    assert lookup["calls"] and lookup["calls"][0][0] == apid


def test_stripe_lookup_error_falls_back_to_confirmation(client, stripe, lookup):
    aid, apid = _stripe_stuck(client)
    lookup["r"] = {"error": "stripe down"}
    assert _rej(client, apid).status_code == 409
    assert _rej(client, apid, {"checked_stripe": True}).status_code == 200


def test_chain_stuck_in_approving_needs_checked_chain(client, _stub_router):
    aid, apid = _chain_approval(client)
    _stick(apid, "approving")
    _sweep(client)
    before = _bal(aid)
    r = _rej(client, apid, {"checked_stripe": True})
    assert r.status_code == 409 and apid in r.json()["error"] and r.json()["requires"] == "checked_chain"
    assert _bal(aid) == before
    assert _rej(client, apid, {"checked_chain": True}).status_code == 200
    a = state.wallets.get_approval(apid)
    assert a["status"] == "rejected" and a["reject_confirmed_what"] == "checked_chain" and a["reject_confirmed_by"] == "operator"
    assert _bal(aid) == before + 40


def test_normal_pending_and_stuck_rejecting_reject_need_no_confirmation(client, stripe, lookup, _stub_router):
    aid, jwt, _ = _stripe_setup(client)
    apid = _co(client, jwt, 60).json()["approval_id"]
    assert _rej(client, apid).status_code == 200 and lookup["calls"] == []
    assert state.wallets.get_approval(apid)["reject_confirmed_by"] == ""
    _, capid = _chain_approval(client)
    _stick(capid, "rejecting")
    _sweep(client)
    assert _rej(client, capid).status_code == 200


def test_ui_has_confirmation_checkbox_for_stuck_paying_reject():
    html = PAGE.read_text(encoding="utf-8")
    assert "review_from === 'approving'" in html and "confirm-checked" in html
    assert "I checked ' + what + ' and no transfer went out" in html
    assert "checked_stripe" in html and "checked_chain" in html and "yes.disabled = true" in html
