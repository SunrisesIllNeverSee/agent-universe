"""Hotfix: an agent cannot name a mission payout (closes the self-mint path)."""
import uuid

from app.deps import state
from tests.conftest import signup_agent


def test_agent_cannot_set_mission_payout(client, admin_client):
    d = signup_agent(client, name=f"hf-{uuid.uuid4().hex[:6]}", ip=f"10.66.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}").json()
    m = admin_client.post("/api/missions", json={"label": "hf"}).json()
    before = state.economy.treasury.balance(d["agent_id"])
    r = client.post(f"/api/missions/{m['id']}/end", json={"payout_per_slot": 1_000_000},
                    headers={"Authorization": f"Bearer {d['api_key']}"})
    assert r.status_code == 403
    assert state.economy.treasury.balance(d["agent_id"]) == before


def test_operator_can_still_set_payout(admin_client):
    m = admin_client.post("/api/missions", json={"label": "hf-op"}).json()
    r = admin_client.post(f"/api/missions/{m['id']}/end", json={"payout_per_slot": 10})
    assert r.status_code == 200


def test_checkout_strips_webhook_instruction_metadata(client, monkeypatch):
    from app import kassa_payments
    seen = {}
    monkeypatch.setattr(kassa_payments, "create_checkout_session",
                        lambda **kw: seen.update(kw) or {"session_id": "cs_t", "url": "u"})
    r = client.post("/api/connect/checkout", json={
        "product_name": "x", "price_cents": 100, "connected_account_id": "acct_x",
        "metadata": {"type": "fee_credit_pack", "pack_name": "Cycle Pack", "agent_id": "a", "note": "ok"}})
    assert r.status_code == 200, r.text
    assert seen["metadata"] == {"note": "ok"}
