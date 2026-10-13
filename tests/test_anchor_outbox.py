"""P5 ProofPress anchor outbox: commit first, anchor after; hashes only; never blocks an interaction."""
from __future__ import annotations

import json
from datetime import datetime, UTC

import pytest

from app import anchor_outbox as ao
from app.anchor_outbox import (
    AdapterUnavailable, AnchorOutbox, AnchorResult, NullAdapter, ProofPressAdapter,
    content_digest, scrub_projection,
)
from app.workentry_store import WorkEntryStore


class Seeds:
    n = 0

    def __call__(self, **kw):
        Seeds.n += 1
        return {"doi": f"10.test/s{Seeds.n}"}


def _store(tmp_path, adapter=None, anchors=True):
    ob = AnchorOutbox(tmp_path / "anchor.db", adapter=adapter) if anchors else None
    return WorkEntryStore(tmp_path / "we.db", seed_fn=Seeds(), anchors=ob), ob


def _file(store, mode="open", **kw):
    return store.file_entry(entrant="agent-a", owner="agent-o", opportunity_ref="post:K-1", entry_mode=mode,
                            objects={"post_id": "K-1"}, terms={"pitch": "secret pitch text"}, **kw)


class OkAdapter:
    name = "ok"
    def __init__(self): self.sent = []
    def submit(self, job):
        self.sent.append(job["dedupe_key"])
        return AnchorResult("anchored", "evd_" + "a" * 16)


class DownAdapter:
    name = "down"
    def submit(self, job): raise AdapterUnavailable("connection refused")


def test_flag_off_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv(ao.FLAG_ENV, raising=False)
    assert ao.build_outbox(tmp_path) is None
    s, _ = _store(tmp_path, anchors=False)
    r = _file(s)
    assert "anchor" not in r["receipts"][0]          # no key, existing shapes unchanged


def test_flag_on_builds_null_adapter(monkeypatch, tmp_path):
    monkeypatch.setenv(ao.FLAG_ENV, "1")
    monkeypatch.delenv(ao.URL_ENV, raising=False)
    ob = ao.build_outbox(tmp_path)
    assert isinstance(ob.adapter, NullAdapter)
    monkeypatch.setenv(ao.URL_ENV, "https://pp.example/mcp")
    assert isinstance(ao.build_outbox(tmp_path / "x").adapter, ProofPressAdapter)


def test_enqueue_after_commit_and_pending_receipt(tmp_path):
    s, ob = _store(tmp_path)
    r = _file(s, auto_activate=True)
    kinds = [j["kind"] for j in ob.jobs()]
    assert kinds == ["agreement.accepted", "agreement.active"]      # create/file/pending not anchored
    last = s.get_receipt(r["receipts"][-1]["receipt_id"])
    assert last["anchor"]["anchor"] == "pending"
    assert s.get_receipt(r["receipts"][0]["receipt_id"])["anchor"] == {"anchor": "none"}


def test_rolled_back_transition_enqueues_nothing(tmp_path):
    class Boom:
        def __call__(self, **kw): raise RuntimeError("seed down")
    ob = AnchorOutbox(tmp_path / "a.db")
    s = WorkEntryStore(tmp_path / "w.db", seed_fn=Boom(), anchors=ob)
    with pytest.raises(Exception):
        _file(s)
    assert ob.jobs() == []


def test_interaction_succeeds_when_proofpress_unreachable(tmp_path):
    s, ob = _store(tmp_path, adapter=DownAdapter())
    a = _file(s)["agreement"]
    out = s.activate(a["agreement_id"], actor="agent-a")
    assert out["agreement"]["state"] == "active"
    tally = ob.drain()
    assert tally["errors"] == 2 and tally["anchored"] == 0
    assert all(j["status"] == "pending" and j["attempts"] == 1 for j in ob.jobs())


def test_enqueue_failure_never_breaks_interaction(tmp_path):
    s, ob = _store(tmp_path)
    ob.close()                                        # outbox DB unusable
    a = _file(s)["agreement"]
    assert a["state"] == "accepted"


def test_idempotent_drain_and_writeback(tmp_path):
    ad = OkAdapter()
    s, ob = _store(tmp_path, adapter=ad)
    r = _file(s, auto_activate=True)
    assert ob.drain()["anchored"] == 2
    assert ob.drain()["anchored"] == 0 and len(ad.sent) == 2        # second drain sends nothing
    rc = s.get_receipt(r["receipts"][-1]["receipt_id"])
    assert rc["anchor"]["anchor"] == "anchored" and rc["anchor"]["anchor_receipt_id"].startswith("evd_")
    assert ob.for_seed(rc["seed_doi"])["anchor"] == "anchored"
    # replayed idempotent call does not double-enqueue
    k = s.file_entry(entrant="e", owner="o", opportunity_ref="p", entry_mode="open", idempotency_key="k1")
    n = len(ob.jobs())
    s.file_entry(entrant="e", owner="o", opportunity_ref="p", entry_mode="open", idempotency_key="k1")
    assert len(ob.jobs()) == n
    # dedupe on key
    j = ob.enqueue("payout", "m1", {"mission_id": "m1"}, dedupe_key="same")
    assert ob.enqueue("payout", "m1", {"mission_id": "m1"}, dedupe_key="same") == j


def test_null_adapter_leaves_pending(tmp_path):
    s, ob = _store(tmp_path, adapter=NullAdapter())
    _file(s)
    assert ob.drain() == {"anchored": 0, "pending": 1, "errors": 0, "skipped": 0}


def test_gives_up_after_max_attempts(tmp_path):
    ob = AnchorOutbox(tmp_path / "a.db", adapter=DownAdapter())
    ob.enqueue("payout", "m", {"mission_id": "m"})
    for _ in range(ao.MAX_ATTEMPTS):
        ob.drain()
    assert ob.jobs()[0]["status"] == "failed"


def test_no_pii_in_payload(tmp_path):
    s, ob = _store(tmp_path)
    a = s.file_entry(entrant="agent-a", owner="agent-o", opportunity_ref="post:K-1", entry_mode="open",
                     objects={"post_id": "K-1"}, terms={"pitch": "call me dev@example.com secret pitch text"})
    s.activate(a["agreement"]["agreement_id"], actor="agent-a")
    blob = " ".join(j["payload_json"] for j in ob.jobs())
    for needle in ("secret pitch", "dev@example.com", "pitch", "reason", "prompt"):
        assert needle not in blob
    for j in ob.jobs():
        assert set(json.loads(j["payload_json"])) <= ao.PROJECTION_KEYS
        assert j["digest"].startswith("sha256:") and len(j["digest"]) == 71


def test_scrub_projection():
    out = scrub_projection({"actor": "agent-a", "reason": "free text", "note": "x", "tier": "a@b.co",
                            "gross": 10, "mission_id": "x" * 500, "nested": {"a": 1}})
    assert out == {"actor": "agent-a", "gross": 10}


def test_digest_is_canonical():
    assert content_digest({"b": 1, "a": 2}) == content_digest({"a": 2, "b": 1})


def test_payout_and_cashout_hooks(tmp_path, monkeypatch):
    ob = AnchorOutbox(tmp_path / "a.db")
    ao.configure(ob)
    try:
        res = {"agent_id": "agent-a", "mission_id": "m1", "tier": "T1",
               "fee_breakdown": {"gross_amount": 100.0, "platform_fee": 10.0, "net_to_agent": 90.0}}
        ao.anchor_payout(res, source="mission_end", seed_doi="10.test/p")
        ao.anchor_payout(res, source="mission_end", seed_doi="10.test/p")      # idempotent
        ao.anchor_cashout(agent_id="agent-a", amount_usd=5.0, transfer_id="tr_1", seed_doi=None)
        ao.anchor_escrow_release(escrow_id="esc-1", agreement_id="agr-1", actor="platform", amount_usd=3.0)
        assert [j["kind"] for j in ob.jobs()] == ["payout", "cashout", "escrow_release"]
        p = json.loads(ob.jobs()[0]["payload_json"])
        assert p["gross"] == 100.0 and p["platform_fee"] == 10.0 and p["net_to_agent"] == 90.0
    finally:
        ao.configure(None)


def test_hooks_inert_without_outbox():
    ao.configure(None)
    ao.anchor_payout({"agent_id": "a"}, source="x")           # no raise
    ao.anchor_cashout(agent_id="a", amount_usd=1, transfer_id="t", seed_doi=None)


def test_proofpress_adapter_disabled_without_url(monkeypatch):
    monkeypatch.delenv(ao.URL_ENV, raising=False)
    ad = ProofPressAdapter()
    assert not ad.enabled
    with pytest.raises(AdapterUnavailable):
        ad.submit({"job_id": "j", "dedupe_key": "d", "kind": "payout", "subject_id": "s",
                   "payload_json": "{}", "digest": "sha256:" + "0" * 64})


def test_proofpress_adapter_envelope_and_reply(tmp_path):
    seen = {}
    def transport(url, body, headers):
        seen.update(url=url, body=body, headers=headers)
        return {"jsonrpc": "2.0", "id": body["id"], "result": {"content": [{"type": "text",
                "text": json.dumps({"evidence_id": "evd_0123456789abcdef"})}]}}
    ad = ProofPressAdapter("https://pp.example/mcp", "tok", transport=transport)
    ob = AnchorOutbox(tmp_path / "a.db", adapter=ad)
    ob.enqueue("payout", "m1", {"mission_id": "m1", "gross": 1})
    assert ob.drain()["anchored"] == 1
    args = seen["body"]["params"]["arguments"]
    env = args["payload"]
    assert seen["body"]["params"]["name"] == "proofpress_submit_evidence"
    assert env["schema_version"] == "proofpress/retrieval-evidence/v1"
    assert env["source"]["content_digest"].startswith("sha256:") and args["idempotency_key"]
    assert env["evidence"]["locator"]["end"] == len(env["evidence"]["quote"])
    assert seen["headers"]["Authorization"] == "Bearer tok"
    assert ob.jobs()[0]["anchor_receipt_id"] == "evd_0123456789abcdef"


def test_proofpress_error_reply_stays_pending(tmp_path):
    ad = ProofPressAdapter("https://pp", transport=lambda u, b, h: {"error": {"message": "no"}})
    ob = AnchorOutbox(tmp_path / "a.db", adapter=ad)
    ob.enqueue("payout", "m1", {"mission_id": "m1"})
    assert ob.drain()["errors"] == 1 and ob.jobs()[0]["status"] == "pending"
