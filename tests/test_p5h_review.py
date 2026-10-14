"""test_p5h_review.py -- findings from the adversarial review of p5g-integration.

1. Withdraw to a linked ethereum/base wallet debited the treasury for a transfer that never happened:
   the adapters are stubs, but only the Solana adapter's note said "stub", so the route's stub check
   missed the other two. The new linked-wallet flow made that path the normal one.
2. release_to credited the payout and created the chargeback hold in two separate treasury
   transactions. Now that the treasury is shared between processes, another process could cash out
   card-funded money in the gap. Credit + hold are now one atomic transaction (and roll back together).
3. An unreadable treasury.json was skipped silently, so the database started empty without a trace.
4. Missing property tests: link limit under concurrency, the G2-D window end to end through the real
   posts column (an entrant-supplied value never wins).
"""
import logging
import threading
import uuid

import pytest

from app.deps import state
from app.economy import AgentTreasury
from tests.test_p5_money_path import _agent

EVM = "0x" + "ab" * 20


# ── 1. stub detection on the real router ────────────────────────────────────

@pytest.mark.parametrize("chain", ["base", "ethereum", "solana"])
def test_real_router_stub_adapters_never_debit(client, monkeypatch, chain):
    import app.routes.economy as economy
    from app.chains import GovernanceGate, MultiChainRouter
    monkeypatch.setattr(GovernanceGate, "check",
                        lambda self, action, agent_id="": {"permitted": True, "governance": {}})
    router = MultiChainRouter(state.runtime)
    monkeypatch.setattr(economy, "_get_chain_router", lambda: router)
    d, _, jwt = _agent(client)
    aid = d["agent_id"]
    addr = EVM if chain != "solana" else "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"
    state.economy.treasury.credit(aid, 50, reason="test_seed_balance")
    wid = state.wallets.link(aid, chain, addr)["wallet_id"]
    r = client.post("/api/economy/withdraw", json={"amount": 5, "chain": chain, "confirm": True, "wallet_id": wid},
                    headers=jwt)
    assert r.status_code == 200, r.text
    assert r.json()["chain_transfer"]["status"] == "PENDING_ADAPTER", r.text
    assert state.economy.treasury.balance(aid) == 50      # nothing left the ledger for a stub transfer


# ── 2. credit + hold are one transaction ────────────────────────────────────

def _fund_escrow(poster, amount=100.0):
    e = state.escrow.fund(poster_id=poster, amount=amount, source="stripe_checkout",
                          mission_id=f"m-{uuid.uuid4().hex[:6]}")
    return state.escrow.hold(e["escrow_id"])


def test_release_credit_is_never_visible_without_its_hold(client, monkeypatch):
    """A second connection (stand-in for another process) reads the treasury at the moment the hold
    is about to be written: the credited payout must not be visible yet."""
    import asyncio

    from app.routes.escrow import release_to
    d, _, _ = _agent(client)
    aid = d["agent_id"]
    poster, _, _ = _agent(client)
    esc = _fund_escrow(poster["agent_id"])
    other = AgentTreasury(state.economy.treasury.path.parent)
    seen = {}
    real_hold = state.economy.treasury.hold

    def spying_hold(*a, **kw):
        seen["balance"] = other.balance(aid)
        seen["matured"] = other.matured_balance(aid)
        return real_hold(*a, **kw)

    monkeypatch.setattr(state.economy.treasury, "hold", spying_hold)
    before = other.balance(aid)
    res = asyncio.run(release_to(esc["escrow_id"], aid, 10.0, source="test"))
    assert res["hold"]["agent_id"] == aid
    assert seen["balance"] == before                       # not visible before the hold existed
    assert other.balance(aid) > before                     # visible after the transaction commits
    assert other.matured_balance(aid) == 0.0               # and born held
    other.close()


def test_hold_failure_rolls_back_the_whole_payout(client, monkeypatch):
    import asyncio

    from app.routes.escrow import release_to
    d, _, _ = _agent(client)
    aid = d["agent_id"]
    poster, _, _ = _agent(client)
    esc = _fund_escrow(poster["agent_id"])
    bal0, plat0 = state.economy.treasury.balance(aid), state.economy.treasury.balance("platform")

    def boom(*a, **kw):
        raise RuntimeError("hold failed")

    monkeypatch.setattr(state.economy.treasury, "hold", boom)
    with pytest.raises(RuntimeError):
        asyncio.run(release_to(esc["escrow_id"], aid, 10.0, source="test"))
    assert state.economy.treasury.balance(aid) == bal0            # agent credit rolled back
    assert state.economy.treasury.balance("platform") == plat0    # and the platform's fee credit
    e = state.escrow.get(esc["escrow_id"])                         # escrow release reverted
    assert e["released_total"] == 0.0 and e["history"][-1]["transition"] == "release_reverted"


def test_atomic_groups_operations_and_rolls_back_together(tmp_path):
    t = AgentTreasury(tmp_path)
    with t.atomic():
        t.credit("a", 10.0, reason="s")
        t.hold("a", 10.0, reason="card", days=7)
    assert t.balance("a") == 10.0 and t.matured_balance("a") == 0.0
    with pytest.raises(RuntimeError):
        with t.atomic():
            t.credit("a", 5.0, reason="s")
            raise RuntimeError("x")
    assert t.balance("a") == 10.0


# ── 3. unreadable legacy json is loud ───────────────────────────────────────

def test_unreadable_treasury_json_is_logged_and_left(tmp_path, caplog):
    src = tmp_path / "treasury.json"
    src.write_text("{not json")
    with caplog.at_level(logging.ERROR, logger="app.economy"):
        t = AgentTreasury(tmp_path)
    assert "TREASURY IMPORT SKIPPED" in caplog.text
    assert src.read_text() == "{not json"
    assert t.all_balances() == {}


# ── 4. property tests that were missing ─────────────────────────────────────

def test_link_limit_holds_under_concurrent_links(tmp_path):
    """Separate connections (as separate processes would have) race to link: exactly three win."""
    from app.wallet_store import MAX_LINKED_WALLETS, WalletError, WalletStore
    db = tmp_path / "w.db"
    stores = [WalletStore(db) for _ in range(8)]
    wins, losses, barrier = [], [], threading.Barrier(8)

    def go(i):
        barrier.wait()
        try:
            stores[i].link("agent-1", "base", "0x" + f"{i + 1:02x}" * 20)
            wins.append(i)
        except WalletError as e:
            losses.append(e.status)

    ts = [threading.Thread(target=go, args=(i,)) for i in range(8)]
    for th in ts:
        th.start()
    for th in ts:
        th.join(60)
    assert len(wins) == MAX_LINKED_WALLETS and losses == [409] * 5
    assert len(stores[0].list("agent-1")) == MAX_LINKED_WALLETS
    for s in stores:
        s.close()


def test_g2d_window_comes_only_from_the_post_through_the_real_column(client, admin_client):
    from tests.test_p4_entry_api import _agent as _wagent, _file
    from tests.test_routes_kassa import _post_payload
    declared = admin_client.post("/api/kassa/posts", json={**_post_payload("bounties"), "answer_window_hours": 6}).json()["id"]
    plain = admin_client.post("/api/kassa/posts", json=_post_payload("bounties")).json()["id"]
    ent = _wagent(client)
    a = _file(client, ent, f"post:{declared}", terms={"answer_window_hours": 168}).json()["agreement"]
    assert a["terms"]["answer_window_hours"] == 12.0           # poster's 6 h, clamped to the 12 h floor; not 168
    ent2 = _wagent(client)
    b = _file(client, ent2, f"post:{plain}", terms={"answer_window_hours": 1}).json()["agreement"]
    assert "answer_window_hours" not in b["terms"]             # no poster value: the entrant's is dropped
