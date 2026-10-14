"""test_p5g_linked_wallets.py — on-chain withdraw destination must be an agent-linked wallet (max 3).

The body never chooses where money goes: it selects one of the agent's stored links.
"""
import pytest

from app.deps import state
from tests.test_p5_money_path import ADMIN, _agent

EVM = "0x" + "ab" * 20
EVM2 = "0x" + "cd" * 20
EVM3 = "0x" + "ef" * 20
EVM4 = "0x" + "12" * 20
SOL = "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"


@pytest.fixture(autouse=True)
def _stub_router(monkeypatch):
    import app.routes.economy as economy

    class _Router:
        calls: list = []

        def transfer(self, chain, to, amount, agent_id="", confirm=False):
            _Router.calls.append((chain, to, agent_id))
            return {"status": "SIGNED", "chain": chain, "note": "governed transaction stub"}

    _Router.calls = []
    monkeypatch.setattr(economy, "_get_chain_router", lambda: _Router())
    return _Router


def _link(client, jwt, address=EVM, chain="base", **kw):
    return client.post("/api/economy/wallets", json={"chain": chain, "address": address, **kw}, headers=jwt)


def _seed(agent_id, amount=50):
    state.economy.treasury.credit(agent_id, amount, reason="test_seed_balance")


def test_link_list_unlink(client):
    d, _, jwt = _agent(client)
    r = _link(client, jwt, label="main")
    assert r.status_code == 201, r.text
    wid = r.json()["wallet"]["wallet_id"]
    lst = client.get("/api/economy/wallets", headers=jwt).json()
    assert lst["max"] == 3 and [w["wallet_id"] for w in lst["wallets"]] == [wid]
    assert client.delete(f"/api/economy/wallets/{wid}", headers=jwt).status_code == 200
    assert client.get("/api/economy/wallets", headers=jwt).json()["wallets"] == []
    assert client.delete(f"/api/economy/wallets/{wid}", headers=jwt).status_code == 404


def test_fourth_link_is_409_and_unlink_frees_a_slot(client):
    _, _, jwt = _agent(client)
    ids = [_link(client, jwt, a).json()["wallet"]["wallet_id"] for a in (EVM, EVM2, EVM3)]
    assert _link(client, jwt, EVM4).status_code == 409
    assert _link(client, jwt, SOL, chain="solana").status_code == 409
    client.delete(f"/api/economy/wallets/{ids[0]}", headers=jwt)
    assert _link(client, jwt, EVM4).status_code == 201


def test_duplicate_link_409_case_insensitive_for_evm(client):
    _, _, jwt = _agent(client)
    assert _link(client, jwt, EVM).status_code == 201
    assert _link(client, jwt, EVM.upper().replace("0X", "0x")).status_code == 409


@pytest.mark.parametrize("chain,addr", [
    ("base", "0x123"), ("ethereum", "not-an-address"), ("solana", "0xabc"), ("solana", "short"),
    ("offchain", "anything"), ("usd", "x"), ("nochain", EVM),
])
def test_bad_address_or_chain_400(client, chain, addr):
    _, _, jwt = _agent(client)
    assert _link(client, jwt, addr, chain=chain).status_code == 400


def test_valid_solana_links(client):
    _, _, jwt = _agent(client)
    assert _link(client, jwt, SOL, chain="solana").status_code == 201


def test_wallet_endpoints_need_a_principal(client):
    assert client.get("/api/economy/wallets").status_code in (401, 403)
    assert client.post("/api/economy/wallets", json={"chain": "base", "address": EVM}).status_code in (401, 403)
    assert client.delete("/api/economy/wallets/wal_x").status_code in (401, 403)


def test_agent_cannot_touch_another_agents_wallets(client):
    _, _, owner = _agent(client)
    _, _, other = _agent(client)
    wid = _link(client, owner).json()["wallet"]["wallet_id"]
    assert client.delete(f"/api/economy/wallets/{wid}", headers=other).status_code == 404
    assert client.get("/api/economy/wallets", headers=other).json()["wallets"] == []
    # body agent_id is ignored for an agent JWT: the link lands on the caller
    d_other = client.get("/api/economy/wallets", headers=other).json()["agent_id"]
    r = client.post("/api/economy/wallets", json={"chain": "base", "address": EVM2, "agent_id": "victim"}, headers=other)
    assert r.status_code == 201 and r.json()["wallet"]["agent_id"] == d_other


def test_operator_acts_for_any_agent(client):
    d, _, _ = _agent(client)
    r = client.post("/api/economy/wallets", json={"agent_id": d["agent_id"], "chain": "base", "address": EVM}, headers=ADMIN)
    assert r.status_code == 201, r.text
    lst = client.get(f"/api/economy/wallets?agent_id={d['agent_id']}", headers=ADMIN).json()
    assert len(lst["wallets"]) == 1
    wid = lst["wallets"][0]["wallet_id"]
    assert client.delete(f"/api/economy/wallets/{wid}?agent_id={d['agent_id']}", headers=ADMIN).status_code == 200
    assert client.post("/api/economy/wallets", json={"chain": "base", "address": EVM}, headers=ADMIN).status_code == 400
    assert client.post("/api/economy/wallets", json={"agent_id": "nope", "chain": "base", "address": EVM},
                       headers=ADMIN).status_code == 404


def test_withdraw_unlinked_to_is_403_and_nothing_moves(client, _stub_router):
    d, _, jwt = _agent(client)
    _seed(d["agent_id"])
    before = state.economy.treasury.balance(d["agent_id"])
    r = client.post("/api/economy/withdraw", json={"amount": 5, "chain": "base", "confirm": True, "to": EVM}, headers=jwt)
    assert r.status_code == 403
    assert state.economy.treasury.balance(d["agent_id"]) == before and _stub_router.calls == []


def test_withdraw_requires_a_selector(client):
    d, _, jwt = _agent(client)
    _seed(d["agent_id"])
    _link(client, jwt)
    r = client.post("/api/economy/withdraw", json={"amount": 5, "chain": "base", "confirm": True}, headers=jwt)
    assert r.status_code == 400


def test_withdraw_to_linked_wallet_by_id_and_by_address(client, _stub_router):
    d, _, jwt = _agent(client)
    _seed(d["agent_id"])
    wid = _link(client, jwt).json()["wallet"]["wallet_id"]
    r = client.post("/api/economy/withdraw", json={"amount": 5, "chain": "base", "confirm": True, "wallet_id": wid}, headers=jwt)
    assert r.status_code == 200, r.text
    r = client.post("/api/economy/withdraw", json={"amount": 5, "chain": "base", "confirm": True, "to": EVM.upper().replace("0X", "0x")}, headers=jwt)
    assert r.status_code == 200, r.text
    # the destination handed to the chain is the stored one, byte for byte
    assert [c[1] for c in _stub_router.calls] == [EVM, EVM]


def test_wallet_id_with_a_different_to_is_refused(client, _stub_router):
    d, _, jwt = _agent(client)
    _seed(d["agent_id"])
    wid = _link(client, jwt).json()["wallet"]["wallet_id"]
    r = client.post("/api/economy/withdraw",
                    json={"amount": 5, "chain": "base", "confirm": True, "wallet_id": wid, "to": EVM2}, headers=jwt)
    assert r.status_code == 403 and _stub_router.calls == []


def test_wallet_on_another_chain_is_refused(client, _stub_router):
    d, _, jwt = _agent(client)
    _seed(d["agent_id"])
    wid = _link(client, jwt, chain="ethereum").json()["wallet"]["wallet_id"]
    r = client.post("/api/economy/withdraw", json={"amount": 5, "chain": "base", "confirm": True, "wallet_id": wid}, headers=jwt)
    assert r.status_code == 403 and _stub_router.calls == []


def test_another_agents_wallet_id_or_address_is_refused(client, _stub_router):
    victim, _, vjwt = _agent(client)
    thief, _, tjwt = _agent(client)
    _seed(thief["agent_id"])
    wid = _link(client, vjwt).json()["wallet"]["wallet_id"]
    for body in ({"wallet_id": wid}, {"to": EVM}):
        r = client.post("/api/economy/withdraw", json={"amount": 5, "chain": "base", "confirm": True, **body}, headers=tjwt)
        assert r.status_code == 403
    assert _stub_router.calls == []


def test_operator_withdraw_also_uses_the_agents_links(client, _stub_router):
    d, _, jwt = _agent(client)
    _seed(d["agent_id"])
    body = {"agent_id": d["agent_id"], "amount": 5, "chain": "base", "confirm": True, "to": EVM2}
    assert client.post("/api/economy/withdraw", json=body, headers=ADMIN).status_code == 403
    _link(client, jwt, EVM2)
    assert client.post("/api/economy/withdraw", json=body, headers=ADMIN).status_code == 200
    assert _stub_router.calls[-1][1] == EVM2


def test_unlink_cannot_redirect_an_in_flight_withdrawal(client, monkeypatch):
    """The unlink lands while the chain transfer is running; the transfer still carries the
    destination resolved at request time, and the unlinked wallet is refused afterwards."""
    import app.routes.economy as economy
    d, _, jwt = _agent(client)
    _seed(d["agent_id"])
    wid = _link(client, jwt).json()["wallet"]["wallet_id"]
    seen = []

    class _Router:
        def transfer(self, chain, to, amount, agent_id="", confirm=False):
            state.wallets.unlink(d["agent_id"], wid)                      # unlink mid-flight
            state.wallets.link(d["agent_id"], "base", EVM2)               # and link another
            seen.append(to)
            return {"status": "SIGNED", "chain": chain, "note": "governed transaction stub"}

    monkeypatch.setattr(economy, "_get_chain_router", lambda: _Router())
    r = client.post("/api/economy/withdraw", json={"amount": 5, "chain": "base", "confirm": True, "wallet_id": wid}, headers=jwt)
    assert r.status_code == 200 and seen == [EVM]
    r = client.post("/api/economy/withdraw", json={"amount": 5, "chain": "base", "confirm": True, "wallet_id": wid}, headers=jwt)
    assert r.status_code == 403 and seen == [EVM]


def test_link_events_are_append_only_history(client):
    d, _, jwt = _agent(client)
    wid = _link(client, jwt).json()["wallet"]["wallet_id"]
    client.delete(f"/api/economy/wallets/{wid}", headers=jwt)
    rows = state.wallets._conn.execute(
        "SELECT action FROM wallet_link_events WHERE wallet_id=? ORDER BY event_id", (wid,)).fetchall()
    assert [r[0] for r in rows] == ["link", "unlink"]
