"""
test_p5_money_path.py — nothing that moves money is taken from the request body.

P5 s2. Closes the mint → cashout path: an agent could end its own mission with
an arbitrary payout_per_slot (crediting a slot it filled itself), then cash the
balance out to any Stripe account it named. Also: checkout price/fee/account
come from the product record, and every payout writes its own Seed, loudly.
"""
import uuid

import pytest

from app import kassa_payments
from app.deps import state
from tests.conftest import signup_agent

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


def _agent(client):
    ip = f"10.55.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"mp-{uuid.uuid4().hex[:6]}", ip=ip).json()
    return d, {"Authorization": f"Bearer {d['api_key']}"}, {"Authorization": f"Bearer {d['token']}"}


def _filled_mission(client, admin_client, agent_id):
    r = admin_client.post("/api/slots/create", json={
        "formation_id": "mp", "posture": "SCOUT", "label": "MP",
        "positions": [{"row": 0, "col": 0}], "roles": ["primary"], "revenue_splits": [100],
    })
    assert r.status_code == 200, r.text
    slot = r.json()["slots"][0]
    r = admin_client.post("/api/slots/fill", json={"slot_id": slot["id"], "agent_id": agent_id, "agent_name": "MP"})
    assert r.status_code == 200, r.text
    return slot["mission_id"]


# ── mission end: payout is an operator claim ────────────────────────────────

def test_owner_agent_cannot_name_a_mission_payout(client):
    d, key, _ = _agent(client)
    m = client.post("/api/missions", json={"label": "self-pay"}, headers=key).json()
    before = state.economy.treasury.balance(d["agent_id"])
    r = client.post(f"/api/missions/{m['id']}/end", json={"payout_per_slot": 1_000_000}, headers=key)
    assert r.status_code == 403
    assert state.economy.treasury.balance(d["agent_id"]) == before


def test_owner_agent_can_still_end_without_payout(client):
    _, key, _ = _agent(client)
    m = client.post("/api/missions", json={"label": "plain-end"}, headers=key).json()
    r = client.post(f"/api/missions/{m['id']}/end", json={}, headers=key)
    assert r.status_code == 200 and r.json()["status"] == "completed"


def test_operator_payout_writes_a_seed_per_payout(client, admin_client):
    d, _, _ = _agent(client)
    mission_id = _filled_mission(client, admin_client, d["agent_id"])
    r = admin_client.post(f"/api/missions/{mission_id}/end", json={"payout_per_slot": 40})
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["payouts"]) == 1
    assert body["payouts"][0]["seed"]["doi"]
    assert body["provenance_errors"] == [] and body["payout_errors"] == []


def test_payout_seed_failure_is_loud(client, admin_client, monkeypatch):
    from app.routes import missions as m

    async def boom(**_):
        raise RuntimeError("seed store down")
    monkeypatch.setattr(m, "create_seed", boom)
    d, _, _ = _agent(client)
    mission_id = _filled_mission(client, admin_client, d["agent_id"])
    r = admin_client.post(f"/api/missions/{mission_id}/end", json={"payout_per_slot": 10})
    assert r.status_code == 200
    assert r.json()["provenance_errors"] == [d["agent_id"]]


def test_payout_bounds(admin_client):
    r = admin_client.post("/api/missions/nope/end", json={"payout_per_slot": 10})
    assert r.status_code == 404
    m = admin_client.post("/api/missions", json={"label": "cap"}).json()
    r = admin_client.post(f"/api/missions/{m['id']}/end", json={"payout_per_slot": 5_000_000})
    assert r.status_code == 400


# ── Connect: accounts bound to agents ───────────────────────────────────────

@pytest.fixture
def fake_stripe(monkeypatch):
    calls = {}
    monkeypatch.setattr(kassa_payments, "create_connected_account",
                        lambda **kw: {"account_id": f"acct_{uuid.uuid4().hex[:8]}"})
    monkeypatch.setattr(kassa_payments, "get_account_status", lambda acct: {"charges_enabled": True})

    def transfer(**kw):
        calls["transfer"] = kw
        return {"transfer_id": "tr_test"}
    monkeypatch.setattr(kassa_payments, "create_transfer", transfer)

    def checkout(**kw):
        calls["checkout"] = kw
        return {"session_id": "cs_test", "url": "https://checkout.test"}
    monkeypatch.setattr(kassa_payments, "create_checkout_session", checkout)
    return calls


def test_account_creation_requires_a_principal(client, fake_stripe):
    r = client.post("/api/connect/accounts", json={"display_name": "x", "email": "x@x.test"})
    assert r.status_code == 401


def test_account_creation_binds_to_agent(client, fake_stripe):
    d, _, jwt = _agent(client)
    r = client.post("/api/connect/accounts", json={"display_name": "x", "email": "x@x.test"}, headers=jwt)
    assert r.status_code == 200, r.text
    rec = next(a for a in state.runtime.registry if a["agent_id"] == d["agent_id"])
    assert rec["stripe_account_id"] == r.json()["account_id"]


def test_cashout_goes_only_to_the_bound_account(client, fake_stripe):
    d, _, jwt = _agent(client)
    acct = client.post("/api/connect/accounts", json={"display_name": "x", "email": "x@x.test"}, headers=jwt).json()["account_id"]
    state.economy.treasury.credit(d["agent_id"], 25, reason="test_seed_balance")
    r = client.post("/api/connect/cashout", json={"amount": 10, "connected_account_id": "acct_attacker"}, headers=jwt)
    assert r.status_code == 403
    r = client.post("/api/connect/cashout", json={"amount": 10}, headers=jwt)
    assert r.status_code == 200, r.text
    assert fake_stripe["transfer"]["connected_account_id"] == acct


def test_cashout_without_bound_account_refused(client, fake_stripe):
    d, _, jwt = _agent(client)
    state.economy.treasury.credit(d["agent_id"], 25, reason="test_seed_balance")
    r = client.post("/api/connect/cashout", json={"amount": 10, "connected_account_id": "acct_any"}, headers=jwt)
    assert r.status_code == 400
    assert "transfer" not in fake_stripe


# ── Checkout: server-derived price, fee and seller ──────────────────────────

def test_checkout_ignores_client_price_fee_and_account(client, fake_stripe, monkeypatch):
    monkeypatch.setattr(kassa_payments, "list_products", lambda: [
        {"product_id": "prod_1", "name": "Thing", "price_cents": 4900, "connected_account_id": "acct_seller"}])
    r = client.post("/api/connect/checkout", json={
        "product_id": "prod_1", "price_cents": 1, "app_fee_percent": 0, "connected_account_id": "acct_attacker"})
    assert r.status_code == 200, r.text
    c = fake_stripe["checkout"]
    assert c["price_cents"] == 4900
    assert c["connected_account_id"] == "acct_seller"
    assert c["app_fee_percent"] == kassa_payments.DEFAULT_APP_FEE_PERCENT


def test_checkout_unknown_product(client, fake_stripe, monkeypatch):
    monkeypatch.setattr(kassa_payments, "list_products", lambda: [])
    assert client.post("/api/connect/checkout", json={"product_id": "prod_x"}).status_code == 404
    assert client.post("/api/connect/checkout", json={}).status_code == 400


def test_agent_product_is_pinned_to_its_bound_account(client, fake_stripe, monkeypatch):
    seen = {}

    def create_product(**kw):
        seen.update(kw)
        return {"product_id": "prod_new"}
    monkeypatch.setattr(kassa_payments, "create_product", create_product)
    d, _, jwt = _agent(client)
    body = {"name": "P", "price_cents": 900}
    assert client.post("/api/connect/products", json=body).status_code == 401
    assert client.post("/api/connect/products", json=body, headers=jwt).status_code == 400  # not linked
    acct = client.post("/api/connect/accounts", json={"display_name": "x", "email": "x@x.test"}, headers=jwt).json()["account_id"]
    assert client.post("/api/connect/products", json={**body, "connected_account_id": "acct_other"}, headers=jwt).status_code == 403
    assert client.post("/api/connect/products", json=body, headers=jwt).status_code == 200
    assert seen["connected_account_id"] == acct
