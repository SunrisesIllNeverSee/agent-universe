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


# 4. Onboarding session / link for ANY connected account, anonymously. Account ids are public (the
#    storefront lists them), and an onboarding session lets its holder edit the account's details,
#    including where payouts go. Only the bound agent (or the operator) may open one.
def _linked(client, monkeypatch):
    import uuid
    acct = f"acct_{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(kassa_payments, "create_connected_account", lambda **kw: {"account_id": acct})
    owner = _agent(client)
    r = client.post("/api/connect/accounts", headers=owner["jwt"], json={"display_name": "x", "email": "x@x.test"})
    assert r.status_code == 200, r.text
    return owner, acct


def test_onboarding_link_and_session_need_the_bound_agent(client, monkeypatch):
    owner, acct = _linked(client, monkeypatch)
    calls = []
    monkeypatch.setattr(kassa_payments, "create_account_link",
                        lambda **kw: calls.append(kw) or {"url": "https://stripe.test/onboard"})
    monkeypatch.setattr(kassa_payments, "create_account_session",
                        lambda account_id: calls.append(account_id) or {"client_secret": "cs_secret"})
    stranger = _agent(client)
    for path in ("onboard", "session"):
        url = f"/api/connect/accounts/{acct}/{path}"
        assert client.post(url).status_code in (401, 403)
        assert client.post(url, headers=stranger["jwt"]).status_code == 403
    assert calls == []
    assert client.post(f"/api/connect/accounts/{acct}/onboard", headers=owner["jwt"]).status_code == 200
    assert client.post(f"/api/connect/accounts/{acct}/session", headers=owner["jwt"]).status_code == 200
    assert client.post(f"/api/connect/accounts/{acct}/onboard", headers=ADMIN).status_code == 200
    assert len(calls) == 3


def test_unbound_account_onboarding_is_operator_only(client, monkeypatch):
    monkeypatch.setattr(kassa_payments, "create_account_link", lambda **kw: {"url": "https://stripe.test/o"})
    a = _agent(client)
    assert client.post("/api/connect/accounts/acct_unbound/onboard", headers=a["jwt"]).status_code == 403
    assert client.post("/api/connect/accounts/acct_unbound/onboard", headers=ADMIN).status_code == 200


# 5. The anchor drain held the outbox lock across the network call, so a slow ProofPress stalled every
#    enqueue (called from the completing request) for up to attempts x timeout. 'Never blocks anything.'
def test_slow_proofpress_does_not_block_enqueue(tmp_path):
    import threading
    import time

    from app.anchor_outbox import AnchorOutbox, AnchorResult

    gate, entered = threading.Event(), threading.Event()

    class Slow:
        name = "slow"

        def submit(self, job):
            entered.set()
            gate.wait(10)
            return AnchorResult("pending")

    ob = AnchorOutbox(tmp_path / "a.db", adapter=Slow())
    ob.enqueue("agreement.completed", "agr-1", {"agreement_id": "agr-1"})
    t = threading.Thread(target=ob.drain)
    t.start()
    assert entered.wait(5)
    started = time.monotonic()
    done = []
    threading.Thread(target=lambda: done.append(ob.enqueue("agreement.completed", "agr-2", {"agreement_id": "agr-2"}))).start()
    time.sleep(0.5)
    gate.set()
    t.join(5)
    assert done and time.monotonic() - started < 2


# 6. Two checkouts opened before either was paid both fund the same mission. Only one escrow is
#    settled at mission end; the other stayed held forever and, with the Agreement completed, the
#    poster could no longer refund it (only the operator could).
def test_second_escrow_on_the_same_mission_is_refunded_at_end(client):
    poster, worker, slot, mid, esc = _funded_mission(client, 100.0)
    assert _fill(client, worker, slot["id"]).status_code == 200
    second = state.escrow.fund(poster_id=poster["id"], amount=40.0, source="operator", mission_id=mid)
    state.escrow.hold(second["escrow_id"], mission_id=mid)
    client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    assert state.escrow.get(esc["escrow_id"])["remaining"] == 0
    assert state.escrow.get(second["escrow_id"])["state"] == "refunded"
    assert state.economy.treasury.balance(poster["id"]) == 40.0
