"""test_p5c_escrow_durable.py — escrow on SQLite: atomic transitions, restart, JSON migration."""
import json
import threading

import pytest

from app.escrow import EscrowError, EscrowStore


def _held(s, amount=100):
    e = s.fund(poster_id="p", amount=amount, source="operator", mission_id="m1")
    s.hold(e["escrow_id"])
    return e["escrow_id"]


def _race(n, fn):
    out, bar = [], threading.Barrier(n)

    def w():
        bar.wait()
        try:
            out.append(("ok", fn()))
        except EscrowError as x:
            out.append(("err", x.code))
    ts = [threading.Thread(target=w) for _ in range(n)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    return out


def test_concurrent_full_release_applies_once(tmp_path):
    s = EscrowStore(tmp_path / "e.db")
    eid = _held(s)
    out = _race(8, lambda: s.reserve_release(eid, agent_id="a", gross=100))
    assert sum(1 for k, _ in out if k == "ok") == 1
    e = s.get(eid)
    assert e["released_total"] == 100 and e["state"] == "released" and len(e["releases"]) == 1


def test_concurrent_release_across_two_store_handles(tmp_path):
    a, b = EscrowStore(tmp_path / "e.db"), EscrowStore(tmp_path / "e.db")   # two replicas, one volume
    eid = _held(a)
    fns = [lambda: a.reserve_release(eid, agent_id="x", gross=100), lambda: b.reserve_release(eid, agent_id="y", gross=100)]
    out, bar = [], threading.Barrier(2)

    def w(f):
        bar.wait()
        try:
            out.append(f())
        except EscrowError as x:
            out.append(x.code)
    ts = [threading.Thread(target=w, args=(f,)) for f in fns]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sum(1 for o in out if isinstance(o, dict)) == 1
    assert a.get(eid)["released_total"] == 100


def test_concurrent_release_and_refund_apply_once(tmp_path):
    s = EscrowStore(tmp_path / "e.db")
    eid = _held(s)
    res = []
    bar = threading.Barrier(2)

    def rel():
        bar.wait()
        try:
            res.append(s.reserve_release(eid, agent_id="a", gross=100))
        except EscrowError as x:
            res.append(x.code)

    def ref():
        bar.wait()
        try:
            res.append(s.reserve_refund(eid))
        except EscrowError as x:
            res.append(x.code)
    ts = [threading.Thread(target=rel), threading.Thread(target=ref)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    e = s.get(eid)
    assert e["released_total"] + e["refunded_total"] == 100 and e["remaining"] == 0


def test_concurrent_refund_applies_once(tmp_path):
    s = EscrowStore(tmp_path / "e.db")
    eid = _held(s)
    out = _race(8, lambda: s.reserve_refund(eid))
    assert sum(1 for k, _ in out if k == "ok") == 1
    assert s.get(eid)["refunded_total"] == 100 and s.get(eid)["state"] == "refunded"


def test_concurrent_fund_same_session_is_one_row(tmp_path):
    s = EscrowStore(tmp_path / "e.db")
    _race(8, lambda: s.fund(poster_id="p", amount=5, source="stripe_checkout", stripe_session_id="cs_9"))
    assert len(s.list()) == 1


def test_restart_persistence(tmp_path):
    s = EscrowStore(tmp_path / "e.db")
    eid = _held(s)
    s.reserve_release(eid, agent_id="a", gross=30)
    s.close()
    e = EscrowStore(tmp_path / "e.db").get(eid)
    assert e["released_total"] == 30 and e["remaining"] == 70 and e["state"] == "held"
    assert len(e["history"]) == 3


def test_failed_transition_rolls_back(tmp_path):
    s = EscrowStore(tmp_path / "e.db")
    eid = _held(s)
    with pytest.raises(EscrowError):
        s.reserve_release(eid, agent_id="a", gross=101)
    assert s.get(eid)["released_total"] == 0


def test_json_fallback_still_works(tmp_path):
    s = EscrowStore(tmp_path / "e.json")
    eid = _held(s)
    out = _race(6, lambda: s.reserve_release(eid, agent_id="a", gross=100))
    assert sum(1 for k, _ in out if k == "ok") == 1
    assert EscrowStore(tmp_path / "e.json").get(eid)["state"] == "released"


def test_migrates_json_records_once(tmp_path):
    old = EscrowStore(tmp_path / "escrow.json")
    eid = _held(old)
    old.reserve_release(eid, agent_id="a", gross=40)
    s = EscrowStore(tmp_path / "escrow.db", import_json=tmp_path / "escrow.json")
    e = s.get(eid)
    assert e["released_total"] == 40 and e["remaining"] == 60 and e["state"] == "held"
    assert (tmp_path / "escrow.json").exists()            # legacy file is kept
    s.reserve_release(eid, agent_id="a", gross=60)
    s.close()
    # restart: the import does not run again and cannot resurrect the old state
    s2 = EscrowStore(tmp_path / "escrow.db", import_json=tmp_path / "escrow.json")
    assert s2.get(eid)["state"] == "released" and s2.get(eid)["released_total"] == 100
    assert len(s2.list()) == 1


def test_migration_tolerates_corrupt_json(tmp_path):
    (tmp_path / "escrow.json").write_text("{not json")
    s = EscrowStore(tmp_path / "escrow.db", import_json=tmp_path / "escrow.json")
    assert s.list() == []
    assert (tmp_path / "escrow.json").read_text() == "{not json"
