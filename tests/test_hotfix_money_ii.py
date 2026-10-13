"""Hotfix money II: webhook fails closed, fee-pack price/coverage server-side, connect onboarding gated."""
from app import kassa_payments
from app.deps import state

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


def _ev(session_id, amount, pack="Founding", agent="agent-hf2"):
    return {"type": "checkout.session.completed", "data": {"object": {
        "id": session_id, "amount_total": amount, "payment_status": "paid",
        "metadata": {"type": "fee_credit_pack", "pack_name": pack, "agent_id": agent}}}}


# 1. Empty signing secret: HMAC over an empty key verifies, so a forged event would be accepted.
def test_webhook_without_signing_secret_is_refused(client, monkeypatch):
    import hashlib, hmac, json, time
    monkeypatch.setattr(kassa_payments, "stripe_ready", lambda: True)
    monkeypatch.setattr(kassa_payments, "STRIPE_WEBHOOK_SECRET", "")
    called = []
    import stripe
    real = stripe.Webhook.construct_event
    monkeypatch.setattr(stripe.Webhook, "construct_event",
                        lambda *a, **k: called.append(1) or real(*a, **k))
    body = json.dumps(_ev("cs_forged", 25000, agent="agent-forged")).encode()
    t = int(time.time())
    sig = hmac.new(b"", f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    r = client.post("/api/kassa/webhooks/stripe", content=body, headers={"stripe-signature": f"t={t},v1={sig}"})
    assert r.status_code in (400, 503), r.text
    assert called == []
    assert state.economy.fee_credits.balance("agent-forged") == 0


# 2. Fee packs: server-side price; coverage scales with amount paid.
def test_fee_pack_price_comes_from_the_pack_not_the_body(admin_client, monkeypatch):
    import stripe
    seen = {}
    monkeypatch.setattr(kassa_payments, "stripe_ready", lambda: True)

    class _S:
        id, url = "cs_pack", "https://stripe.test/pay"

    monkeypatch.setattr(stripe.checkout.Session, "create",
                        staticmethod(lambda **kw: seen.update(kw) or _S()))
    r = admin_client.post("/api/fee-credits/checkout", json={"pack_name": "Founding", "price_cents": 50, "agent_id": "a"})
    assert r.status_code == 200, r.text
    assert seen["line_items"][0]["price_data"]["unit_amount"] == 25000


def _webhook(client, monkeypatch, ev):
    import stripe
    monkeypatch.setattr(kassa_payments, "stripe_ready", lambda: True)
    monkeypatch.setattr(kassa_payments, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda payload, sig, secret: ev)
    return client.post("/api/kassa/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t"})


def test_fee_pack_coverage_is_proportional_to_what_was_paid(client, monkeypatch):
    r = _webhook(client, monkeypatch, _ev("cs_cheap", 50, agent="agent-cheap"))
    assert r.status_code == 200, r.text
    assert state.economy.fee_credits.balance("agent-cheap") <= 1.2


def test_fee_pack_paid_in_full_gets_full_coverage(client, monkeypatch):
    r = _webhook(client, monkeypatch, _ev("cs_full", 25000, agent="agent-full"))
    assert r.status_code == 200, r.text
    assert state.economy.fee_credits.balance("agent-full") == 600


# 3. Connect onboarding session/link: production has no account->agent binding, so operator only.
def test_connect_onboarding_is_operator_only(client, admin_client, monkeypatch):
    from tests.conftest import signup_agent
    import uuid
    calls = []
    monkeypatch.setattr(kassa_payments, "create_account_link",
                        lambda **kw: calls.append(kw) or {"url": "https://stripe.test/o"})
    monkeypatch.setattr(kassa_payments, "create_account_session",
                        lambda account_id: calls.append(account_id) or {"client_secret": "cs"})
    d = signup_agent(client, name=f"hf2-{uuid.uuid4().hex[:6]}",
                     ip=f"10.77.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}").json()
    agent_hdr = {"Authorization": f"Bearer {d['api_key']}"}
    for path in ("onboard", "session"):
        url = f"/api/connect/accounts/acct_victim/{path}"
        assert client.post(url).status_code in (401, 403)
        assert client.post(url, headers=agent_hdr).status_code in (401, 403)
    assert calls == []
    assert admin_client.post("/api/connect/accounts/acct_ok/onboard").status_code == 200
    assert admin_client.post("/api/connect/accounts/acct_ok/session").status_code == 200
    assert len(calls) == 2
