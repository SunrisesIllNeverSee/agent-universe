"""test_p5j_review.py — adversarial review fixes on top of the P5i wallet safety work."""
from app.deps import state
from tests.test_p5_money_path import ADMIN, _agent
from tests.test_p5i_wallet_safety import EVM, EVM2, _age, _bal, _stub_router  # noqa: F401  (autouse fixture)


def _link(client, jwt, chain, address):
    return client.post("/api/economy/wallets", json={"chain": chain, "address": address}, headers=jwt)


def _wd(client, jwt, wid, chain, amount):
    return client.post("/api/economy/withdraw", json={"amount": amount, "chain": chain, "confirm": True,
                                                       "wallet_id": wid}, headers=jwt)


def test_same_evm_address_on_two_chains_shares_one_cap_and_window(client, _stub_router):
    """ethereum and base are one address space: linking the same 0x address on both must not
    give a second $25 cap (or a fresh 24h window)."""
    d, _, jwt = _agent(client)
    aid = d["agent_id"]
    state.economy.treasury.credit(aid, 200, reason="test_seed_balance")
    w1 = _link(client, jwt, "ethereum", EVM).json()["wallet"]["wallet_id"]
    _age(12.1)
    w2 = _link(client, jwt, "base", EVM).json()["wallet"]["wallet_id"]
    assert _wd(client, jwt, w1, "ethereum", 25).status_code == 200
    r = _wd(client, jwt, w2, "base", 25)
    assert r.status_code == 202 and r.json()["status"] == "pending_approval"
    assert len(_stub_router.calls) == 1
    # window is counted from the first link of the address on any EVM chain
    _age(12.0)
    assert _wd(client, jwt, w2, "base", 5).status_code == 200


def test_same_evm_address_other_agent_other_chain_is_flagged(client):
    _, _, a = _agent(client)
    _, _, b = _agent(client)
    import uuid
    addr = "0x" + uuid.uuid4().hex + uuid.uuid4().hex[:8]
    assert _link(client, a, "ethereum", addr).status_code == 201
    assert _link(client, b, "base", addr).status_code == 201
    assert any(f["flag"] == "shared_address" for f in state.wallets.list_flags()
               if f["addr_key"] == addr.lower())


def test_duplicate_link_is_409_even_inside_the_interval(client):
    _, _, jwt = _agent(client)
    assert _link(client, jwt, "base", EVM).status_code == 201
    assert _link(client, jwt, "base", EVM).status_code == 409
    assert _link(client, jwt, "base", EVM2).status_code == 429


def test_failed_reject_refund_does_not_strand_the_approval(client, _stub_router, monkeypatch):
    d, _, jwt = _agent(client)
    aid = d["agent_id"]
    state.economy.treasury.credit(aid, 100, reason="test_seed_balance")
    wid = _link(client, jwt, "base", EVM).json()["wallet"]["wallet_id"]
    apid = _wd(client, jwt, wid, "base", 40).json()["approval_id"]
    assert _bal(aid) == 60

    real = state.economy.treasury.credit
    monkeypatch.setattr(state.economy.treasury, "credit",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db down")))
    assert client.post(f"/api/operator/payout-approvals/{apid}/reject", headers=ADMIN).status_code == 500
    monkeypatch.setattr(state.economy.treasury, "credit", real)
    assert state.wallets.get_approval(apid)["status"] == "pending"
    assert _bal(aid) == 60
    r = client.post(f"/api/operator/payout-approvals/{apid}/reject", headers=ADMIN)
    assert r.status_code == 200 and _bal(aid) == 100


def test_refund_keeps_matured_money_matured_and_held_money_held(client, _stub_router):
    d, _, jwt = _agent(client)
    aid = d["agent_id"]
    t = state.economy.treasury
    t.credit(aid, 100, reason="test_seed_balance")
    t.hold(aid, 60, reason="test_hold", ref="x")
    wid = _link(client, jwt, "base", EVM).json()["wallet"]["wallet_id"]
    assert t.matured_balance(aid) == 40 and t.held_balance(aid) == 60
    r = _wd(client, jwt, wid, "base", 40)
    assert r.status_code == 202
    assert t.matured_balance(aid) == 0 and t.held_balance(aid) == 60
    apid = r.json()["approval_id"]
    client.post(f"/api/operator/payout-approvals/{apid}/reject", headers=ADMIN)
    assert t.matured_balance(aid) == 40 and t.held_balance(aid) == 60


def test_chains_transfer_rejects_agent_jwt_and_anonymous(client):
    _, _, jwt = _agent(client)
    body = {"chain": "base", "to": EVM, "amount": 1, "agent_id": "x", "confirm": True}
    assert client.post("/api/chains/transfer", json=body).status_code == 403
    assert client.post("/api/chains/transfer", json=body, headers=jwt).status_code == 403
    assert client.post("/api/chains/transfer", json=body, headers={"X-Admin-Key": "wrong"}).status_code == 403
