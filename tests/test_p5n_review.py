"""test_p5n_review.py -- adversarial review of the p5m changes (stuck-reject confirmation, admin pages,
MCP queued cashouts).

* a reject that could refund money that already went out needs the operator's confirmation on EVERY path
  that leaves an approval in doubt: needs_review rows with no/unknown review_from (fail closed), and
  'pending' rows whose last attempt ended ambiguously (exception / non-definitive Stripe error)
* the inactive-agent approve path never auto-refunds such an approval
* only the operator key can send the confirmation; the confirmation is recorded
* admin/operator pages are served under a first-party-only CSP
"""
import pytest

import app.routes.economy as economy_routes
from app import kassa_payments
from app.deps import state
from tests.test_p5_money_path import ADMIN
from tests.test_p5l_review import _stick, _sweep, _chain_approval, _bal, _approve, _stub_router  # noqa: F401
from tests.test_p5k_stripe_new_dest_cap import _bal as _sbal, _co, _setup as _stripe_setup, stripe  # noqa: F401


def _rej(client, apid, body=None, headers=ADMIN):
    return client.post(f"/api/operator/payout-approvals/{apid}/reject", headers=headers, **({"json": body} if body is not None else {}))


@pytest.fixture(autouse=True)
def _no_stripe_lookup(monkeypatch):
    monkeypatch.setattr(kassa_payments, "find_transfer_by_approval", lambda a, acct: {"found": False})


# ── fail closed on needs_review without a known review_from ──────────────────

def test_needs_review_with_blank_review_from_still_needs_confirmation(client, _stub_router):
    aid, apid = _chain_approval(client)
    _stick(apid, "approving")
    _sweep(client)
    state.wallets._conn.execute("UPDATE payout_approvals SET review_from='' WHERE approval_id=?", (apid,))
    before = _bal(aid)
    r = _rej(client, apid)
    assert r.status_code == 409 and r.json()["requires"] == "checked_chain" and _bal(aid) == before
    assert _rej(client, apid, {"checked_chain": True}).status_code == 200 and _bal(aid) == before + 40


# ── ambiguous failures leave the approval 'pending' but in doubt ─────────────

def test_chain_exception_on_approve_requires_confirmation_to_reject(client, monkeypatch, _stub_router):
    aid, apid = _chain_approval(client)

    class Boom:
        def transfer(self, *a, **k):
            raise RuntimeError("rpc timeout after broadcast?")
    monkeypatch.setattr(economy_routes, "_get_chain_router", lambda: Boom())
    assert _approve(client, apid).status_code == 502
    a = state.wallets.get_approval(apid)
    assert a["status"] == "pending" and a["review_from"] == "approving"
    before = _bal(aid)
    r = _rej(client, apid)
    assert r.status_code == 409 and r.json()["requires"] == "checked_chain" and _bal(aid) == before
    assert _rej(client, apid, {"checked_chain": True}).status_code == 200 and _bal(aid) == before + 40


def test_stripe_nondefinitive_error_requires_confirmation_definitive_does_not(client, stripe, monkeypatch):
    aid, jwt, _ = _stripe_setup(client)
    apid = _co(client, jwt, 60).json()["approval_id"]
    monkeypatch.setattr(kassa_payments, "create_transfer", lambda **kw: {"error": "timeout", "type": "APIConnectionError"})
    assert _approve(client, apid).status_code == 502
    assert state.wallets.get_approval(apid)["review_from"] == "approving"
    assert _rej(client, apid).status_code == 409 and _sbal(aid) == 140
    # a later definitive refusal proves nothing went out: the mark is cleared and reject is plain again
    monkeypatch.setattr(kassa_payments, "create_transfer", lambda **kw: {"error": "bad", "type": "InvalidRequestError"})
    assert _approve(client, apid).status_code == 502
    assert state.wallets.get_approval(apid)["review_from"] == ""
    assert _rej(client, apid).status_code == 200 and _sbal(aid) == 200


def test_stripe_ambiguous_pending_reject_blocked_when_transfer_exists(client, stripe, monkeypatch):
    aid, jwt, _ = _stripe_setup(client)
    apid = _co(client, jwt, 60).json()["approval_id"]
    monkeypatch.setattr(kassa_payments, "create_transfer", lambda **kw: {"error": "timeout", "type": "APIConnectionError"})
    assert _approve(client, apid).status_code == 502
    monkeypatch.setattr(kassa_payments, "find_transfer_by_approval", lambda a, acct: {"found": True, "transfer_id": "tr_out"})
    r = _rej(client, apid, {"checked_stripe": True})
    assert r.status_code == 409 and "tr_out" in r.json()["error"] and _sbal(aid) == 140


def test_inactive_agent_does_not_auto_refund_ambiguous_pending(client, monkeypatch, _stub_router):
    aid, apid = _chain_approval(client)

    class Boom:
        def transfer(self, *a, **k):
            raise RuntimeError("boom")
    monkeypatch.setattr(economy_routes, "_get_chain_router", lambda: Boom())
    assert _approve(client, apid).status_code == 502
    entry = next(r for r in state.runtime.registry if r["agent_id"] == aid)
    entry["status"] = "suspended"
    before = _bal(aid)
    try:
        r = _approve(client, apid)
    finally:
        entry["status"] = "active"
    assert r.status_code == 409 and state.wallets.get_approval(apid)["status"] == "pending" and _bal(aid) == before


def test_plain_pending_inactive_agent_still_auto_refunds(client, _stub_router):
    aid, apid = _chain_approval(client)
    entry = next(r for r in state.runtime.registry if r["agent_id"] == aid)
    entry["status"] = "suspended"
    before = _bal(aid)
    try:
        assert _approve(client, apid).status_code == 409
    finally:
        entry["status"] = "active"
    assert state.wallets.get_approval(apid)["status"] == "rejected" and _bal(aid) == before + 40


# ── only the operator can confirm ────────────────────────────────────────────

def test_non_operator_cannot_confirm_reject(client, _stub_router):
    aid, apid = _chain_approval(client)
    _stick(apid, "approving")
    _sweep(client)
    before = _bal(aid)
    for headers in ({}, {"X-Admin-Key": "wrong"}):
        r = _rej(client, apid, {"checked_chain": True, "checked_stripe": True}, headers=headers)
        assert r.status_code == 403
    a = state.wallets.get_approval(apid)
    assert a["status"] == "needs_review" and a["reject_confirmed_by"] == "" and _bal(aid) == before


# ── admin pages: strict CSP ──────────────────────────────────────────────────

@pytest.mark.parametrize("path", ["/admin", "/admin/payouts", "/operator/x", "/assets/admin.html"])
def test_admin_pages_served_with_first_party_only_csp(client, path):
    # the test root has no frontend files: give it stand-ins so the real routes answer 200
    for name in ("admin.html", "admin-payouts.html"):
        (state.frontend_dir / name).write_text("<html></html>")
    r = client.get(path)
    csp = r.headers["content-security-policy"]
    for bad in ("googletagmanager", "google-analytics", "fonts.googleapis", "fonts.gstatic", "stripe.com", "https:", "wss:"):
        assert bad not in csp, (path, bad, csp)
    assert "default-src 'none'" in csp and "frame-ancestors 'none'" in csp and "connect-src 'self'" in csp
    assert r.headers["referrer-policy"] == "no-referrer" and r.headers["cache-control"] == "no-store"
    assert r.headers["x-frame-options"] == "DENY"


def test_public_pages_keep_their_csp(client):
    (state.frontend_dir / "index.html").write_text("<html></html>")
    for path in ("/", "/administrators", "/api/operator/stats", "/assets/index.html"):
        assert "js.stripe.com" in client.get(path).headers["content-security-policy"], path
