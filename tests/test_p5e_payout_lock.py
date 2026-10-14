"""test_p5e_payout_lock.py — the payout guard holds across processes, not just threads."""
import multiprocessing as mp
import sqlite3

import pytest

from app.escrow import EscrowError, EscrowStore


def _worker(path, eid, who, barrier, q):
    s = EscrowStore(path)           # own connection and own process lock: a separate replica
    barrier.wait()
    try:
        s.reserve_release(eid, agent_id=who, gross=100)
        q.put(("ok", who))
    except EscrowError as x:
        q.put(("err", x.code))
    finally:
        s.close()


def _held(path, amount=100):
    s = EscrowStore(path)
    e = s.fund(poster_id="p", amount=amount, source="operator", mission_id="m1")
    s.hold(e["escrow_id"])
    s.close()
    return e["escrow_id"]


@pytest.mark.parametrize("n", [2, 4])
def test_processes_racing_one_escrow_pay_once(tmp_path, n):
    path = tmp_path / "e.db"
    eid = _held(path)
    ctx = mp.get_context("spawn")
    barrier, q = ctx.Barrier(n), ctx.Queue()
    ps = [ctx.Process(target=_worker, args=(path, eid, f"a{i}", barrier, q)) for i in range(n)]
    [p.start() for p in ps]
    out = [q.get(timeout=60) for _ in ps]
    [p.join(timeout=60) for p in ps]
    assert sum(1 for k, _ in out if k == "ok") == 1, out
    assert all(c == "bad_state" for k, c in out if k == "err"), out
    s = EscrowStore(path)
    e = s.get(eid)
    assert e["released_total"] == 100 and e["state"] == "released" and len(e["releases"]) == 1


def test_stale_write_is_refused_by_the_database(tmp_path):
    """A writer whose read went stale (modified by another connection) updates 0 rows and raises."""
    path = tmp_path / "e.db"
    eid = _held(path)
    s = EscrowStore(path)
    with pytest.raises(EscrowError) as ei:
        with s._txn():
            e = s._get(eid)
            raw = sqlite3.connect(str(path), isolation_level=None)   # bypasses the store entirely
            raw.execute("PRAGMA busy_timeout=0")
            try:
                raw.execute("UPDATE escrows SET doc=doc||' ' WHERE escrow_id=?", (eid,))
            except sqlite3.OperationalError:
                # BEGIN IMMEDIATE already blocks outside writers; simulate the lost-lock case instead
                s._seen[eid] = e and "stale"
            finally:
                raw.close()
            e["released_total"] = 100
            s._put(e)
    assert ei.value.code == "conflict"
    assert s.get(eid)["released_total"] == 0
