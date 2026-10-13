"""
test_p5_money_adversarial.py — hostile-agent / anonymous attacks on the money path.

Each test is an attack that was demonstrated against the code before its fix.
Hard guarantees live only on money and provenance; nothing here fences behaviour.
"""
import json
import uuid

import pytest

from app import kassa_payments
from app.deps import state
from tests.test_p4_entry_api import _agent
from tests.test_p4_slot_binding import _fill, _mk_slot, _store

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


def _held(client, amount=100.0):
    poster, entrant = _agent(client), _agent(client)
    slot = _mk_slot(client, poster)
    esc = client.post("/api/escrow/fund", headers=ADMIN,
                      json={"mission_id": slot["mission_id"], "amount": amount}).json()["escrow"]
    return poster, entrant, slot, esc


@pytest.fixture
def fake_stripe(monkeypatch):
    calls = []
    monkeypatch.setattr(kassa_payments, "create_connected_account",
                        lambda **kw: {"account_id": f"acct_{uuid.uuid4().hex[:8]}"})
    monkeypatch.setattr(kassa_payments, "get_account_status", lambda acct: {"charges_enabled": True})
    monkeypatch.setattr(kassa_payments, "create_transfer",
                        lambda **kw: calls.append(kw) or {"transfer_id": "tr_adv"})
    return calls


def _webhook(client, monkeypatch, event):
    import stripe
    monkeypatch.setattr(kassa_payments, "stripe_ready", lambda: True)
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda payload, sig, secret: event)
    return client.post("/api/kassa/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t"})


# 1. NaN balance: cashout(NaN) poisons the ledger so every later balance check passes.
def test_cashout_nan_cannot_poison_balance(client, fake_stripe):
    a = _agent(client)
    client.post("/api/connect/accounts", headers=a["jwt"], json={"display_name": "x", "email": "x@x.test"})
    state.economy.treasury.credit(a["id"], 5.0, reason="test")
    r = client.post("/api/connect/cashout", headers={**a["jwt"], "content-type": "application/json"},
                    content=b'{"amount": NaN}')
    assert r.status_code == 400
    bal = state.economy.treasury.balance(a["id"])
    assert bal == 5.0
    r = client.post("/api/connect/cashout", headers=a["jwt"], json={"amount": 1000})
    assert r.status_code == 400 and not fake_stripe


def test_treasury_rejects_non_finite_and_negative():
    t = state.economy.treasury
    for bad in (float("nan"), float("inf"), -1.0):
        assert t.debit("adv-x", bad, reason="t").get("error")
        with pytest.raises(ValueError):
            t.credit("adv-x", bad, reason="t")
    assert t.balance("adv-x") == 0.0


# 2. Poster terminates the live Agreement, then refunds: the worker's pay is clawed back unilaterally.
def test_poster_cannot_terminate_then_refund(client):
    poster, entrant, slot, esc = _held(client, 40)
    aid = _fill(client, entrant, slot["id"]).json()["agreement_id"]
    r = client.post(f"/api/work-entry/{aid}/terminate", headers=poster["h"], json={"reason": "x"})
    if r.status_code == 404:                       # no REST terminate: use the store as the poster
        _store().terminate(aid, actor=poster["id"], reason="x")
    assert _store().get(aid)["state"] == "terminated"
    r = client.post(f"/api/escrow/{esc['escrow_id']}/refund", headers=poster["h"])
    assert r.status_code == 403, r.text
    assert state.escrow.get(esc["escrow_id"])["state"] == "held"


# 3. Regression guard: terminate-then-end cannot sweep the escrow back either (the worker is still paid).
def test_terminate_then_end_still_pays_the_worker(client):
    poster, entrant, slot, esc = _held(client, 40)
    aid = _fill(client, entrant, slot["id"]).json()["agreement_id"]
    _store().terminate(aid, actor=poster["id"], reason="x")
    before_p = state.economy.treasury.balance(poster["id"])
    before_e = state.economy.treasury.balance(entrant["id"])
    r = client.post(f"/api/missions/{slot['mission_id']}/end", headers=poster["h"], json={})
    assert r.status_code == 200, r.text
    assert state.economy.treasury.balance(poster["id"]) == before_p
    assert state.economy.treasury.balance(entrant["id"]) > before_e


# 4. Originator credit self-dealing: the poster names its own sock puppet as "originator" to cut the fee.
def test_owner_cannot_name_a_sock_puppet_originator(client):
    poster, sock, slot, esc = _held(client, 100)
    state.economy.trials.commit(sock["id"])                   # out of trial: a real tier fee applies
    _fill(client, sock, slot["id"])
    r = client.post(f"/api/missions/{slot['mission_id']}/end", headers=poster["h"],
                    json={"originator_id": sock["id"]})
    assert r.status_code == 200, r.text
    (payout,) = r.json()["payouts"]
    assert payout["originator_credit_applied"] is False
    assert payout["fee_breakdown"]["originator_credit"] == 0.0


# 5. A replayed / retried Stripe webhook credits the same fee-credit purchase twice.
def test_fee_credit_webhook_replay_credits_once(client, monkeypatch):
    agent = f"adv-{uuid.uuid4().hex[:6]}"
    ev = {"type": "checkout.session.completed", "data": {"object": {
        "id": f"cs_{uuid.uuid4().hex[:8]}", "amount_total": 2500, "payment_status": "paid",
        "metadata": {"type": "fee_credit_pack", "pack_name": "Starter", "agent_id": agent}}}}
    assert _webhook(client, monkeypatch, ev).status_code == 200
    assert _webhook(client, monkeypatch, ev).status_code == 200
    assert state.economy.fee_credits.balance(agent) == 50


# 6. A cheap MPP credential for one resource is accepted as payment for a different, dearer post.
def test_mpp_credential_is_bound_to_its_post(client):
    from datetime import UTC, datetime
    now = datetime.now(UTC).isoformat()
    ids = []
    for reward in ("$1", "$200"):
        pid = f"K-{uuid.uuid4().hex[:8]}"
        state.kassa.insert_post({"id": pid, "tab": "iso", "title": pid, "tag": "t", "body": "b", "reward": reward,
                                 "from_name": "P", "from_email": "p@example.com", "created_at": now,
                                 "updated_at": now, "poster_agent_id": None})
        ids.append(pid)
    cheap, dear = ids
    payer = f"adv-{uuid.uuid4().hex[:6]}"
    state.economy.treasury.credit(payer, 5.0, reason="test")
    ch = kassa_payments.mpp_challenge("1.00", cheap, "cheap")
    token = kassa_payments.mpp_pay(ch["challengeId"], payer, state.economy.treasury)["token"]
    assert client.post(f"/api/kassa/posts/{cheap}/pay", headers={"Authorization": token}).json()["paid"] is True
    r = client.post(f"/api/kassa/posts/{dear}/pay", headers={"Authorization": token})
    assert r.status_code == 402


# 7. An entrant that walked away (terminated its own Agreement) freezes the poster's escrow by disputing it.
def test_walked_away_entrant_cannot_freeze_the_escrow(client):
    poster, entrant, slot, esc = _held(client, 40)
    aid = _fill(client, entrant, slot["id"]).json()["agreement_id"]
    _store().terminate(aid, actor=entrant["id"], reason="leaving")
    r = client.post(f"/api/escrow/{esc['escrow_id']}/dispute", headers=entrant["h"], json={"reason": "grief"})
    assert r.status_code == 403
    assert state.escrow.get(esc["escrow_id"])["state"] == "held"
    # and the poster, who is owed nothing to a worker that left, gets the refund
    r = client.post(f"/api/escrow/{esc['escrow_id']}/refund", headers=poster["h"])
    assert r.status_code == 200 and r.json()["refunded"] == 40


# 8. Anonymous buyer smuggles webhook-reserved metadata through product checkout: a $1 purchase
#    (paid to the attacker's own connected account) would be read by the webhook as escrow funding.
def test_checkout_metadata_cannot_carry_webhook_instructions(client, monkeypatch):
    seen = {}
    monkeypatch.setattr(kassa_payments, "list_products", lambda: [
        {"product_id": "prod_adv", "name": "p", "price_cents": 100, "connected_account_id": "acct_attacker"}])
    monkeypatch.setattr(kassa_payments, "create_checkout_session",
                        lambda **kw: seen.update(kw) or {"session_id": "cs_adv", "url": "https://x.test"})
    r = client.post("/api/connect/checkout", json={"product_id": "prod_adv", "metadata": {
        "type": "escrow_funding", "mission_id": "m", "poster_id": "me", "pack_name": "Cycle Pack",
        "agent_id": "me", "note": "ok"}})
    assert r.status_code == 200, r.text
    assert seen["metadata"] == {"note": "ok", "product_id": "prod_adv"}
