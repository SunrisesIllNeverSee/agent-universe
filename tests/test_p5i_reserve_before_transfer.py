"""test_p5i_reserve_before_transfer.py — withdraw reserves (debits) BEFORE the chain transfer.

Concurrent withdrawals can never transfer more than the matured balance; a transfer that does not
really happen gives the reservation back (matured stays matured). /api/chains/transfer is operator-only.
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.deps import state
from tests.test_p5_money_path import ADMIN, _agent

EVM = "0x" + "ab" * 20


class _Router:
    status = "SIGNED"
    note = "submitted tx 0xabc"
    delay = 0.0
    boom = False
    calls: list = []
    seen_balance: list = []

    def transfer(self, chain, to, amount, agent_id="", confirm=False, **kw):
        _Router.calls.append((chain, to, amount))
        _Router.seen_balance.append(state.economy.treasury.balance(agent_id))
        if _Router.delay:
            time.sleep(_Router.delay)
        if _Router.boom:
            raise RuntimeError("rpc down")
        return {"status": _Router.status, "chain": chain, "note": _Router.note}


@pytest.fixture(autouse=True)
def _router(monkeypatch):
    import app.routes.economy as economy
    _Router.status, _Router.note, _Router.delay, _Router.boom = "SIGNED", "submitted tx 0xabc", 0.0, False
    _Router.calls, _Router.seen_balance = [], []
    monkeypatch.setattr(economy, "_get_chain_router", lambda: _Router())
    return _Router


def _setup(client, amount=50):
    d, _, jwt = _agent(client)
    aid = d["agent_id"]
    r = client.post("/api/economy/wallets", json={"chain": "base", "address": EVM}, headers=jwt)
    assert r.status_code == 201, r.text
    state.economy.treasury.credit(aid, amount, reason="test_seed_balance")
    return aid, jwt, r.json()["wallet"]["wallet_id"]


def _wd(client, jwt, wid, amount):
    return client.post("/api/economy/withdraw",
                       json={"amount": amount, "chain": "base", "confirm": True, "wallet_id": wid}, headers=jwt)


def test_debit_happens_before_the_transfer(client):
    aid, jwt, wid = _setup(client, 50)
    assert _wd(client, jwt, wid, 10).status_code == 200
    assert _Router.seen_balance == [40]          # already reserved when the adapter was called
    assert state.economy.treasury.balance(aid) == 40


@pytest.mark.parametrize("status,note", [
    ("ERROR", ""), ("FAILED", ""), ("BLOCKED", ""), ("AWAITING_CONFIRMATION", ""),
    ("SIGNED", "governed transaction stub"),
])
def test_failed_or_stub_transfer_refunds_the_reservation_as_matured(client, status, note):
    aid, jwt, wid = _setup(client, 50)
    t = state.economy.treasury
    t.hold(aid, 20, reason="test", days=7)       # 30 matured, 20 held
    _Router.status, _Router.note = status, note
    assert _wd(client, jwt, wid, 30).status_code == 200
    assert t.balance(aid) == 50
    assert t.matured_balance(aid) == 30 and t.held_balance(aid) == 20
    reasons = [x["reason"] for x in t._txns(aid)]
    assert "withdrawal" in reasons and "withdrawal_reversal" in reasons
    # and it is spendable again right away
    _Router.status, _Router.note = "SIGNED", "submitted"
    assert _wd(client, jwt, wid, 30).json()["withdrawal"]["type"] == "debit"
    assert t.balance(aid) == 20


def test_adapter_exception_refunds(client):
    aid, jwt, wid = _setup(client, 50)
    _Router.boom = True
    try:
        r = _wd(client, jwt, wid, 10)
        assert r.status_code == 500
    except RuntimeError:
        pass
    t = state.economy.treasury
    assert t.balance(aid) == 50 and t.matured_balance(aid) == 50


def test_successful_transfer_keeps_the_debit(client):
    aid, jwt, wid = _setup(client, 50)
    r = _wd(client, jwt, wid, 10).json()
    assert r["withdrawal"]["type"] == "debit" and state.economy.treasury.balance(aid) == 40


def test_held_money_is_never_reserved_or_transferred(client):
    aid, jwt, wid = _setup(client, 50)
    state.economy.treasury.hold(aid, 45, reason="test", days=7)
    r = _wd(client, jwt, wid, 10).json()
    assert "error" in r and _Router.calls == []


def test_concurrent_withdraws_never_transfer_more_than_matured(client):
    aid, jwt, wid = _setup(client, 20)           # 20 matured, 8 attempts of 5
    _Router.delay = 0.05
    start = threading.Barrier(8)

    def go(_):
        start.wait()
        return _wd(client, jwt, wid, 5).json()

    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(go, range(8)))
    ok = [r for r in results if r.get("withdrawal")]
    assert len(ok) == 4 and len(_Router.calls) == 4
    assert sum(c[2] for c in _Router.calls) <= 20
    assert state.economy.treasury.balance(aid) == 0
    assert all("error" in r for r in results if not r.get("withdrawal"))


def test_concurrent_withdraws_overlimit_transfer_total_capped(client):
    aid, jwt, wid = _setup(client, 12)
    _Router.delay = 0.05
    start = threading.Barrier(4)

    def go(_):
        start.wait()
        return _wd(client, jwt, wid, 5).json()

    with ThreadPoolExecutor(4) as ex:
        list(ex.map(go, range(4)))
    assert sum(c[2] for c in _Router.calls) == 10
    assert state.economy.treasury.balance(aid) == 2


def test_chains_transfer_is_operator_only(client):
    body = {"chain": "base", "to": EVM, "amount": 1, "confirm": True}
    assert client.post("/api/chains/transfer", json=body).status_code == 403
    _, _, jwt = _agent(client)
    assert client.post("/api/chains/transfer", json=body, headers=jwt).status_code == 403
    assert client.post("/api/chains/transfer", json=body, headers={"X-Admin-Key": "wrong"}).status_code == 403
    assert _Router.calls == []
    assert client.post("/api/chains/transfer", json=body, headers=ADMIN).status_code == 200
    assert len(_Router.calls) == 1
