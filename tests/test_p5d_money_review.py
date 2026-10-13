"""test_p5d_money_review.py — adversarial money review of the P5c escrow / force-assign / outbox code.

Each test is an attack demonstrated against the code before its fix.
"""
from app import kassa_payments
from app.deps import state
from tests.test_p4_entry_api import _agent
from tests.test_p4_slot_binding import _fill, _mk_slot

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


def _funded_mission(client, amount=100.0):
    poster, worker = _agent(client), _agent(client)
    slot = _mk_slot(client, poster)
    mid = slot["mission_id"]
    esc = client.post("/api/escrow/fund", headers=ADMIN, json={"mission_id": mid, "amount": amount}).json()["escrow"]
    return poster, worker, slot, mid, esc


def _enter_mission(client, who, mid):
    """File an entry on the mission itself (no slot): open mode accepts it with no poster say."""
    r = client.post("/api/work-entry", headers=who["h"], json={"opportunity_ref": f"mission:{mid}"})
    assert r.status_code == 201, r.text
    assert r.json()["agreement"]["state"] == "accepted"
    return r.json()["agreement"]


# 1. Swarm: open-mode entries on a funded mission are accepted with no poster consent. They must not
#    dilute the real worker's share, block the poster's refund or freeze the escrow.
def test_swarm_entrants_do_not_dilute_the_payout(client):
    poster, worker, slot, mid, esc = _funded_mission(client)
    assert _fill(client, worker, slot["id"]).status_code == 200
    swarm = [_agent(client) for _ in range(3)]
    for s in swarm:
        _enter_mission(client, s, mid)
    out = client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={}).json()
    assert [p["agent_id"] for p in out["payouts"]] == [worker["id"]]
    assert state.economy.treasury.balance(worker["id"]) == 100.0
    assert all(state.economy.treasury.balance(s["id"]) == 0 for s in swarm)


def test_swarm_entrant_cannot_lock_the_posters_refund(client):
    poster, _w, _slot, mid, esc = _funded_mission(client)
    _enter_mission(client, _agent(client), mid)
    r = client.post(f"/api/escrow/{esc['escrow_id']}/refund", headers=poster["h"])
    assert r.status_code == 200, r.text
    assert state.escrow.get(esc["escrow_id"])["state"] == "refunded"


def test_swarm_entrant_cannot_freeze_the_escrow(client):
    _p, _w, _slot, mid, esc = _funded_mission(client)
    s = _agent(client)
    _enter_mission(client, s, mid)
    r = client.post(f"/api/escrow/{esc['escrow_id']}/dispute", headers=s["h"], json={"reason": "x"})
    assert r.status_code == 403
    assert state.escrow.get(esc["escrow_id"])["state"] == "held"


def test_entrant_the_poster_accepted_is_still_paid(client):
    poster, _w, _slot, mid, esc = _funded_mission(client)
    e = _agent(client)
    ag = client.post("/api/work-entry", headers=e["h"],
                     json={"opportunity_ref": f"mission:{mid}", "entry_mode": "standard"}).json()["agreement"]
    assert ag["state"] == "pending"
    assert client.post(f"/api/work-entry/{ag['agreement_id']}/accept", headers=poster["h"], json={}).status_code == 200
    client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    assert state.economy.treasury.balance(e["id"]) == 100.0


def test_poster_terminating_a_swarm_entrant_does_not_make_it_payable(client):
    poster, worker, slot, mid, esc = _funded_mission(client)
    assert _fill(client, worker, slot["id"]).status_code == 200
    s = _agent(client)
    ag = _enter_mission(client, s, mid)
    state.workentry.terminate(ag["agreement_id"], actor=poster["id"], reason="not wanted")
    client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    assert state.economy.treasury.balance(s["id"]) == 0
    assert state.economy.treasury.balance(worker["id"]) == 100.0


# 2. Webhook with no signing secret configured: an HMAC over an empty key verifies, so anyone could
#    forge a paid escrow_funding event and mint held funds. No secret = no webhook.
def test_webhook_without_signing_secret_is_refused(client, monkeypatch):
    import hashlib
    import hmac
    import json
    import time

    from app import kassa_payments
    monkeypatch.setattr(kassa_payments, "stripe_ready", lambda: True)
    monkeypatch.setattr(kassa_payments, "STRIPE_WEBHOOK_SECRET", "")
    poster = _agent(client)
    slot = _mk_slot(client, poster)
    body = json.dumps({"id": "evt_forged", "object": "event", "type": "checkout.session.completed",
                       "data": {"object": {"id": "cs_forged", "amount_total": 10_000_000, "payment_status": "paid",
                                           "metadata": {"type": "escrow_funding", "mission_id": slot["mission_id"],
                                                        "poster_id": poster["id"]}}}}).encode()
    t = int(time.time())
    sig = hmac.new(b"", f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    r = client.post("/api/kassa/webhooks/stripe", content=body, headers={"stripe-signature": f"t={t},v1={sig}"})
    assert r.status_code in (400, 503), r.text
    assert state.escrow.by_session("cs_forged") is None


# 3. Fee-credit packs: the pack name picked the coverage, the BODY picked the price. A $0.50
#    "Founding" checkout bought $600 of fee coverage (fees skipped on money the platform earned).
def _fake_session(monkeypatch, seen):
    import stripe
    monkeypatch.setattr(kassa_payments, "stripe_ready", lambda: True)

    class _S:
        id, url = "cs_pack", "https://stripe.test/pay"

    def create(**kw):
        seen.update(kw)
        return _S()
    monkeypatch.setattr(stripe.checkout.Session, "create", staticmethod(create))


def test_fee_pack_price_comes_from_the_pack_not_the_body(client, monkeypatch):
    seen = {}
    _fake_session(monkeypatch, seen)
    a = _agent(client)
    r = client.post("/api/fee-credits/checkout", headers=ADMIN,
                    json={"pack_name": "Founding", "price_cents": 50, "agent_id": a["id"]})
    assert r.status_code == 200, r.text
    assert seen["line_items"][0]["price_data"]["unit_amount"] == 25000


def test_fee_pack_coverage_is_proportional_to_what_was_paid(client, monkeypatch):
    import stripe
    a = _agent(client)
    monkeypatch.setattr(kassa_payments, "stripe_ready", lambda: True)
    ev = {"type": "checkout.session.completed", "data": {"object": {
        "id": "cs_cheap", "amount_total": 50, "payment_status": "paid",
        "metadata": {"type": "fee_credit_pack", "pack_name": "Founding", "agent_id": a["id"]}}}}
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda payload, sig, secret: ev)
    r = client.post("/api/kassa/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t"})
    assert r.status_code == 200, r.text
    assert state.economy.fee_credits.balance(a["id"]) <= 1.2


def test_fee_pack_paid_in_full_gets_full_coverage(client, monkeypatch):
    import stripe
    a = _agent(client)
    monkeypatch.setattr(kassa_payments, "stripe_ready", lambda: True)
    ev = {"type": "checkout.session.completed", "data": {"object": {
        "id": "cs_full", "amount_total": 25000, "payment_status": "paid",
        "metadata": {"type": "fee_credit_pack", "pack_name": "Founding", "agent_id": a["id"]}}}}
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda payload, sig, secret: ev)
    client.post("/api/kassa/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t"})
    assert state.economy.fee_credits.balance(a["id"]) == 600
