"""P5g: AgentTreasury on SQLite. Every balance read-modify-write is one BEGIN IMMEDIATE
transaction that re-reads the database, so separate processes cannot double-spend."""
from __future__ import annotations

import json
import multiprocessing as mp
from datetime import UTC, datetime, timedelta

import pytest

from app.economy import AgentTreasury


def _debit_worker(data_dir: str, agent: str, amount: float, n: int, start, out) -> None:
    t = AgentTreasury(data_dir)   # its own connection: no shared in-memory state
    start.wait(30)
    spent = 0.0
    for _ in range(n):
        r = t.debit(agent, amount, reason="race", matured_only=True)
        if "error" not in r:
            spent += amount
    out.put(spent)


def test_multiprocess_debits_never_exceed_matured_balance(tmp_path):
    seed = AgentTreasury(tmp_path)
    seed.credit("a1", 100.0, reason="seed")
    seed.hold("a1", 40.0, reason="card", days=7)        # 60 matured, 40 held
    seed.close()
    ctx = mp.get_context("spawn")
    start, out = ctx.Event(), ctx.Queue()
    procs = [ctx.Process(target=_debit_worker, args=(str(tmp_path), "a1", 1.0, 40, start, out)) for _ in range(4)]
    for p in procs:
        p.start()
    start.set()
    totals = [out.get(timeout=120) for _ in procs]
    for p in procs:
        p.join(60)
        assert p.exitcode == 0
    assert sum(totals) == 60.0          # 160 attempts, exactly the matured 60 succeeded
    t = AgentTreasury(tmp_path)
    assert t.balance("a1") == 40.0
    assert t.matured_balance("a1") == 0.0
    debits = [x for x in t.history("a1", limit=500) if x["type"] == "debit"]
    assert round(sum(x["amount"] for x in debits), 4) == 60.0


def test_second_instance_sees_writes_without_reload(tmp_path):
    a, b = AgentTreasury(tmp_path), AgentTreasury(tmp_path)
    a.credit("x", 10.0, reason="t")
    assert b.balance("x") == 10.0
    assert b.debit("x", 10.0, reason="t")["type"] == "debit"
    assert a.balance("x") == 0.0
    assert "error" in a.debit("x", 1.0, reason="t")


def test_json_import_is_lossless_and_leaves_file(tmp_path):
    now = datetime.now(UTC)
    hold = {"hold_id": "hold-abc", "agent_id": "a1", "amount": 5.5, "reason": "r", "ref": "e1",
            "created_at": now.isoformat(), "charged_at": None, "hold_basis": "payout_time",
            "matures_at": (now + timedelta(days=3)).isoformat()}
    txns = [{"id": f"id{i}", "agent_id": "a1" if i % 2 else "a2", "type": "credit", "amount": 1.25 * i,
             "reason": "platform_fee" if i == 3 else "x", "mission_id": "", "timestamp": now.isoformat(),
             "balance_after": 0.1 * i} for i in range(1, 6)]
    ledger = {"balances": {"a1": 12.3456789, "a2": 0.1 + 0.2}, "transactions": txns, "holds": [hold]}
    src = tmp_path / "treasury.json"
    src.write_text(json.dumps(ledger))
    before = src.read_bytes()
    t = AgentTreasury(tmp_path)
    assert t._ledger == ledger                     # balances, transactions (order) and holds identical
    assert src.read_bytes() == before              # json untouched
    assert t.held_balance("a1") == 5.5
    assert t.platform_revenue() == txns[2]["amount"]
    t.credit("a1", 1.0, reason="after")
    t.close()
    t2 = AgentTreasury(tmp_path)                   # re-open: no second import, new data kept
    assert t2.balance("a1") == 12.3456789 + 1.0
    assert len(t2._ledger["transactions"]) == 6
    assert len(t2._ledger["holds"]) == 1


def test_matured_only_debit_and_hold_release(tmp_path):
    t = AgentTreasury(tmp_path)
    t.credit("a", 50.0, reason="s")
    h = t.hold("a", 30.0, reason="card", days=7)
    r = t.debit("a", 25.0, reason="cashout", matured_only=True)
    assert r["error"] == "Insufficient matured balance" and r["matured"] == 20.0
    assert t.balance("a") == 50.0
    assert t.debit("a", 20.0, reason="cashout", matured_only=True)["balance_after"] == 30.0
    t.release_hold(h["hold_id"])
    assert t.matured_balance("a") == 30.0
    assert t.held_until("a") is None


def test_invalid_amounts_unchanged(tmp_path):
    t = AgentTreasury(tmp_path)
    with pytest.raises(ValueError):
        t.credit("a", float("nan"), reason="x")
    with pytest.raises(ValueError):
        t.hold("a", -1, reason="x")
    assert t.debit("a", float("nan"), reason="x")["error"] == "Invalid amount"
    assert t.debit("a", 1.0, reason="x")["error"] == "Insufficient balance"


def test_failed_transaction_rolls_back(tmp_path):
    t = AgentTreasury(tmp_path)
    t.credit("a", 5.0, reason="s")
    with pytest.raises(RuntimeError):
        with t._txn():
            t._set_bal("a", 999.0)
            raise RuntimeError("boom")
    assert t.balance("a") == 5.0


def test_json_fallback_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("TREASURY_STORE", "json")
    t = AgentTreasury(tmp_path)
    t.credit("a", 7.0, reason="s")
    t.hold("a", 3.0, reason="c", days=1)
    assert (tmp_path / "treasury.json").exists() and not (tmp_path / "treasury.db").exists()
    assert t.matured_balance("a") == 4.0
    assert "error" in t.debit("a", 5.0, reason="c", matured_only=True)
    t2 = AgentTreasury(tmp_path)
    assert t2.balance("a") == 7.0
