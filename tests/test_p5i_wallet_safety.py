"""test_p5i_wallet_safety.py — one new wallet link per 12h; $25 cap for 24h on a new wallet,
over-cap withdrawals reserve the money and wait for operator approval; shared addresses are flagged."""
from datetime import UTC, datetime, timedelta

import pytest

from app.deps import state
from tests.test_p5_money_path import ADMIN, _agent

EVM = "0x" + "ab" * 20
EVM2 = "0x" + "cd" * 20
EVM3 = "0x" + "ef" * 20


@pytest.fixture(autouse=True)
def _stub_router(monkeypatch):
    import app.routes.economy as economy

    class _Router:
        calls: list = []

        def transfer(self, chain, to, amount, agent_id="", confirm=False):
            _Router.calls.append((chain, to, amount, agent_id))
            return {"status": "SIGNED", "chain": chain, "note": "governed transaction"}

    _Router.calls = []
    monkeypatch.setattr(economy, "_get_chain_router", lambda: _Router())
    return _Router


def _link(client, jwt, address=EVM, **kw):
    return client.post("/api/economy/wallets", json={"chain": "base", "address": address, **kw}, headers=jwt)


def _age(hours):
    """Make every link event / wallet look ``hours`` older."""
    c = state.wallets._conn
    shift = lambda iso: (datetime.fromisoformat(iso) - timedelta(hours=hours)).isoformat()  # noqa: E731
    for t, col, key in (("wallet_link_events", "at", "event_id"), ("linked_wallets", "created_at", "wallet_id")):
        for k, v in c.execute(f"SELECT {key}, {col} FROM {t}").fetchall():
            c.execute(f"UPDATE {t} SET {col}=? WHERE {key}=?", (shift(v), k))


def _setup(client, balance=100, address=EVM):
    d, _, jwt = _agent(client)
    state.economy.treasury.credit(d["agent_id"], balance, reason="test_seed_balance")
    wid = _link(client, jwt, address).json()["wallet"]["wallet_id"]
    return d["agent_id"], jwt, wid


def _wd(client, jwt, wid, amount):
    return client.post("/api/economy/withdraw", json={"amount": amount, "chain": "base", "confirm": True,
                                                       "wallet_id": wid}, headers=jwt)


def _bal(aid):
    return state.economy.treasury.balance(aid)


# ── 12h link interval ───────────────────────────────────────────────────────

def test_second_link_inside_12h_is_429_with_allowed_time(client):
    _, _, jwt = _agent(client)
    assert _link(client, jwt, EVM).status_code == 201
    r = _link(client, jwt, EVM2)
    assert r.status_code == 429
    allowed = datetime.fromisoformat(r.json()["allowed_at"])
    assert timedelta(hours=11, minutes=50) < allowed - datetime.now(UTC) <= timedelta(hours=12)
    assert int(r.headers["Retry-After"]) > 0
    _age(12.1)
    assert _link(client, jwt, EVM2).status_code == 201


def test_unlink_relink_does_not_reset_the_clock(client):
    _, _, jwt = _agent(client)
    wid = _link(client, jwt, EVM).json()["wallet"]["wallet_id"]
    assert client.delete(f"/api/economy/wallets/{wid}", headers=jwt).status_code == 200
    assert _link(client, jwt, EVM).status_code == 429
    assert _link(client, jwt, EVM2).status_code == 429


def test_operator_bypasses_link_interval(client):
    d, _, _ = _agent(client)
    for a in (EVM, EVM2, EVM3):
        r = client.post("/api/economy/wallets", json={"agent_id": d["agent_id"], "chain": "base", "address": a}, headers=ADMIN)
        assert r.status_code == 201, r.text


# ── new-wallet cap ──────────────────────────────────────────────────────────

def test_cap_boundary_exactly_25_pays_then_one_cent_more_goes_pending(client, _stub_router):
    aid, jwt, wid = _setup(client)
    assert _wd(client, jwt, wid, 25).status_code == 200
    assert len(_stub_router.calls) == 1
    r = _wd(client, jwt, wid, 0.01)
    assert r.status_code == 202 and r.json()["status"] == "pending_approval"
    assert len(_stub_router.calls) == 1


def test_cap_is_cumulative(client, _stub_router):
    aid, jwt, wid = _setup(client)
    assert _wd(client, jwt, wid, 15).status_code == 200
    assert _wd(client, jwt, wid, 10).status_code == 200
    assert _wd(client, jwt, wid, 1).status_code == 202


def test_over_cap_reserves_balance_and_creates_approval(client, _stub_router):
    aid, jwt, wid = _setup(client)
    r = _wd(client, jwt, wid, 40)
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "pending_approval" and body["approval_id"].startswith("apr_")
    assert _bal(aid) == 60 and _stub_router.calls == []   # reserved, not spendable, not paid
    rows = client.get("/api/operator/payout-approvals", headers=ADMIN).json()["approvals"]
    mine = [a for a in rows if a["approval_id"] == body["approval_id"]]
    assert mine and mine[0]["status"] == "pending" and mine[0]["address"] == EVM and mine[0]["amount"] == 40
    # the reserved money cannot be spent a second time
    state.economy.treasury.debit(aid, 60, reason="test_drain")
    r2 = _wd(client, jwt, wid, 40)
    assert r2.status_code == 200 and "error" in r2.json()   # nothing left to reserve twice


def test_approve_pays_once_to_snapshotted_destination(client, _stub_router):
    aid, jwt, wid = _setup(client)
    apid = _wd(client, jwt, wid, 40).json()["approval_id"]
    client.delete(f"/api/economy/wallets/{wid}", headers=jwt)   # unlink after the request: destination is snapshotted
    r = client.post(f"/api/operator/payout-approvals/{apid}/approve", headers=ADMIN)
    assert r.status_code == 200, r.text
    assert r.json()["approval"]["status"] == "approved"
    assert _stub_router.calls == [("base", EVM, 40, aid)]
    again = client.post(f"/api/operator/payout-approvals/{apid}/approve", headers=ADMIN)
    assert again.status_code == 409 and again.json()["noop"] is True
    assert len(_stub_router.calls) == 1 and _bal(aid) == 60
    assert client.post(f"/api/operator/payout-approvals/{apid}/reject", headers=ADMIN).status_code == 409
    assert _bal(aid) == 60


def test_reject_refunds_once(client, _stub_router):
    aid, jwt, wid = _setup(client)
    apid = _wd(client, jwt, wid, 40).json()["approval_id"]
    assert _bal(aid) == 60
    r = client.post(f"/api/operator/payout-approvals/{apid}/reject", headers=ADMIN)
    assert r.status_code == 200 and r.json()["approval"]["status"] == "rejected"
    assert _bal(aid) == 100
    assert client.post(f"/api/operator/payout-approvals/{apid}/reject", headers=ADMIN).status_code == 409
    assert client.post(f"/api/operator/payout-approvals/{apid}/approve", headers=ADMIN).status_code == 409
    assert _bal(aid) == 100 and _stub_router.calls == []
    # a rejected approval frees its cap usage
    assert _wd(client, jwt, wid, 25).status_code == 200


def test_approval_endpoints_are_operator_only(client):
    aid, jwt, wid = _setup(client)
    apid = _wd(client, jwt, wid, 40).json()["approval_id"]
    for method, path in (("get", "/api/operator/payout-approvals"), ("get", "/api/operator/wallet-flags"),
                         ("post", f"/api/operator/payout-approvals/{apid}/approve"),
                         ("post", f"/api/operator/payout-approvals/{apid}/reject")):
        assert getattr(client, method)(path, headers=jwt).status_code in (401, 403)
        assert getattr(client, method)(path).status_code in (401, 403)
    assert _bal(aid) == 60


def test_approval_stays_pending_when_chain_refuses(client, monkeypatch):
    import app.routes.economy as economy

    class _Blocked:
        def transfer(self, *a, **k):
            return {"status": "BLOCKED"}
    aid, jwt, wid = _setup(client)
    apid = _wd(client, jwt, wid, 40).json()["approval_id"]
    monkeypatch.setattr(economy, "_get_chain_router", lambda: _Blocked())
    assert client.post(f"/api/operator/payout-approvals/{apid}/approve", headers=ADMIN).status_code == 409
    assert state.wallets.get_approval(apid)["status"] == "pending" and _bal(aid) == 60


def test_after_24h_no_cap(client, _stub_router):
    aid, jwt, wid = _setup(client)
    _age(24.1)
    r = _wd(client, jwt, wid, 60)
    assert r.status_code == 200, r.text
    assert _stub_router.calls[-1][2] == 60


def test_relinking_the_same_address_does_not_restart_the_cap_window(client, _stub_router):
    aid, jwt, wid = _setup(client)
    _age(24.1)
    client.delete(f"/api/economy/wallets/{wid}", headers=jwt)
    wid2 = _link(client, jwt, EVM).json()["wallet"]["wallet_id"]
    assert _wd(client, jwt, wid2, 60).status_code == 200


# ── shared address flag ─────────────────────────────────────────────────────

def test_same_address_two_agents_allowed_and_flagged(client):
    import uuid
    addr = "0x" + uuid.uuid4().hex + uuid.uuid4().hex[:8]
    da, _, a = _agent(client)
    db, _, b = _agent(client)
    assert _link(client, a, addr).status_code == 201
    assert _link(client, b, "0x" + addr[2:].upper()).status_code == 201
    flags = client.get("/api/operator/wallet-flags", headers=ADMIN).json()["wallet_flags"]
    hit = [f for f in flags if f["addr_key"] == addr.lower() and f["flag"] == "shared_address"]
    assert len(hit) == 1
    assert {hit[0]["agent_id"], hit[0]["other_agent_id"]} == {da["agent_id"], db["agent_id"]}
    assert any(f["addr_key"] == addr.lower() for f in
               client.get("/api/operator/payout-approvals", headers=ADMIN).json()["wallet_flags"])
