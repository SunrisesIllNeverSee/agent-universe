"""test_p5_escrow.py — escrow: held funds, bounded release, refund, dispute, Stripe funding, seller tier."""
import json
import uuid

import pytest

from app import kassa_payments
from app.deps import state
from app.escrow import EscrowError, EscrowStore
from tests.test_p4_entry_api import _agent
from tests.test_p4_slot_binding import _fill, _mk_slot, _store

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


def _funded(client, amount=100.0):
    poster, entrant = _agent(client), _agent(client)
    slot = _mk_slot(client, poster)
    r = client.post("/api/escrow/fund", headers=ADMIN, json={"mission_id": slot["mission_id"], "amount": amount})
    assert r.status_code == 200, r.text
    return poster, entrant, slot, r.json()["escrow"]


# ── store: the money bound ────────────────────────────────────────────────

def test_store_bounds_and_states(tmp_path):
    s = EscrowStore(tmp_path / "e.json")
    e = s.fund(poster_id="p", amount=50, source="operator", mission_id="m1")
    assert e["state"] == "funded"
    with pytest.raises(EscrowError):           # release only from held
        s.reserve_release(e["escrow_id"], agent_id="a", gross=10)
    s.hold(e["escrow_id"])
    s.reserve_release(e["escrow_id"], agent_id="a", gross=30)
    with pytest.raises(EscrowError) as x:      # cannot exceed held funds
        s.reserve_release(e["escrow_id"], agent_id="a", gross=20.01)
    assert x.value.code == "exceeds_held"
    r = s.reserve_refund(e["escrow_id"])
    assert r["amount"] == 20 and r["escrow"]["state"] == "released" and r["escrow"]["remaining"] == 0
    with pytest.raises(EscrowError):
        s.reserve_refund(e["escrow_id"])
    # persisted
    assert EscrowStore(tmp_path / "e.json").get(e["escrow_id"])["refunded_total"] == 20


def test_store_dispute_freezes_and_resolves(tmp_path):
    s = EscrowStore(tmp_path / "e.json")
    e = s.fund(poster_id="p", amount=10, source="operator", mission_id="m")
    s.hold(e["escrow_id"])
    s.dispute(e["escrow_id"], by="p", reason="no show")
    for fn in (lambda: s.reserve_release(e["escrow_id"], agent_id="a", gross=1),
               lambda: s.reserve_refund(e["escrow_id"])):
        with pytest.raises(EscrowError) as x:
            fn()
        assert x.value.code == "disputed"
    assert s.resolve_dispute(e["escrow_id"], by="op")["state"] == "held"


def test_store_fund_idempotent_on_session(tmp_path):
    s = EscrowStore(tmp_path / "e.json")
    a = s.fund(poster_id="p", amount=5, source="stripe_checkout", stripe_session_id="cs_1")
    b = s.fund(poster_id="p", amount=5, source="stripe_checkout", stripe_session_id="cs_1")
    assert b["duplicate"] and b["escrow_id"] == a["escrow_id"] and len(s.list()) == 1


# ── routes ────────────────────────────────────────────────────────────────

def test_fund_is_operator_only_and_links_agreement(client):
    poster, entrant, slot, esc = _funded(client)
    assert esc["state"] == "held"
    r = client.post("/api/escrow/fund", headers=poster["h"], json={"mission_id": slot["mission_id"], "amount": 5})
    assert r.status_code == 403
    r = client.post("/api/escrow/fund", headers=ADMIN, json={"mission_id": slot["mission_id"], "amount": 5})
    assert r.status_code == 409                                   # one live escrow per mission
    aid = _fill(client, entrant, slot["id"]).json()["agreement_id"]
    assert _store().get(aid)["objects"]["escrow_id"] == esc["escrow_id"]


def test_operator_release_bounded_and_fee_from_config(client):
    poster, entrant, slot, esc = _funded(client, 100)
    eid = esc["escrow_id"]
    r = client.post(f"/api/escrow/{eid}/release", headers=ADMIN, json={"agent_id": entrant["id"], "amount": 100.01})
    assert r.status_code == 400 and r.json()["code"] == "exceeds_held"
    before = state.economy.treasury.balance(entrant["id"])
    r = client.post(f"/api/escrow/{eid}/release", headers=ADMIN, json={"agent_id": entrant["id"], "amount": 60})
    assert r.status_code == 200, r.text
    net = r.json()["fee_breakdown"]["net_to_agent"]
    assert round(state.economy.treasury.balance(entrant["id"]) - before, 4) == round(net, 4)
    assert r.json()["seed"]["doi"] and r.json()["escrow_seed"]["doi"]
    assert r.json()["escrow"]["remaining"] == 40 and r.json()["escrow"]["state"] == "held"
    # not callable by an agent
    r = client.post(f"/api/escrow/{eid}/release", headers=entrant["h"], json={"agent_id": entrant["id"], "amount": 1})
    assert r.status_code == 403


def test_refund_returns_to_poster_and_blocks_further_release(client):
    poster, entrant, slot, esc = _funded(client, 40)
    before = state.economy.treasury.balance(poster["id"])
    r = client.post(f"/api/escrow/{esc['escrow_id']}/refund", headers=poster["h"])   # no active Agreement yet
    assert r.status_code == 200, r.text
    assert r.json()["refunded"] == 40 and r.json()["seed"]["doi"]
    assert round(state.economy.treasury.balance(poster["id"]) - before, 4) == 40
    assert r.json()["escrow"]["state"] == "refunded"
    r = client.post(f"/api/escrow/{esc['escrow_id']}/release", headers=ADMIN, json={"agent_id": entrant["id"], "amount": 1})
    assert r.status_code == 409


def test_poster_cannot_refund_under_active_agreement(client):
    poster, entrant, slot, esc = _funded(client, 40)
    _fill(client, entrant, slot["id"])
    r = client.post(f"/api/escrow/{esc['escrow_id']}/refund", headers=poster["h"])
    assert r.status_code == 403
    assert client.post(f"/api/escrow/{esc['escrow_id']}/refund", headers=ADMIN).status_code == 200


def test_dispute_freezes_mission_end_payout(client):
    poster, entrant, slot, esc = _funded(client, 50)
    _fill(client, entrant, slot["id"])
    r = client.post(f"/api/escrow/{esc['escrow_id']}/dispute", headers=entrant["h"], json={"reason": "scope"})
    assert r.status_code == 200 and r.json()["escrow"]["state"] == "disputed"
    before = state.economy.treasury.balance(entrant["id"])
    out = client.post(f"/api/missions/{slot['mission_id']}/end", headers=poster["h"], json={}).json()
    assert out["payouts"] == [] and out["payout_errors"][0]["code"] == "disputed"
    assert state.economy.treasury.balance(entrant["id"]) == before
    assert state.escrow.get(esc["escrow_id"])["remaining"] == 50          # nothing moved
    assert client.post(f"/api/escrow/{esc['escrow_id']}/resolve", headers=poster["h"], json={}).status_code == 403
    assert client.post(f"/api/escrow/{esc['escrow_id']}/resolve", headers=ADMIN, json={}).json()["escrow"]["state"] == "held"


def test_mission_end_with_no_filled_slot_refunds_poster(client):
    poster, entrant, slot, esc = _funded(client, 25)
    before = state.economy.treasury.balance(poster["id"])
    out = client.post(f"/api/missions/{slot['mission_id']}/end", headers=poster["h"], json={}).json()
    assert out["escrow"]["refunded"] == 25 and out["escrow"]["state"] == "refunded"
    assert round(state.economy.treasury.balance(poster["id"]) - before, 4) == 25


def test_operator_claim_over_held_funds_is_bounded(client):
    poster, entrant, slot, esc = _funded(client, 30)
    _fill(client, entrant, slot["id"])
    out = client.post(f"/api/missions/{slot['mission_id']}/end", headers=ADMIN, json={"payout_per_slot": 500}).json()
    assert out["payouts"] == [] and out["payout_errors"][0]["code"] == "exceeds_held"
    assert out["escrow"]["refunded"] == 30                                  # mission ended; held funds go home


def test_no_escrow_keeps_operator_payout(client):
    poster, entrant = _agent(client), _agent(client)
    slot = _mk_slot(client, poster)
    _fill(client, entrant, slot["id"])
    out = client.post(f"/api/missions/{slot['mission_id']}/end", headers=ADMIN, json={"payout_per_slot": 10}).json()
    assert len(out["payouts"]) == 1 and out["escrow"] is None


def test_every_transition_is_audited(client):
    poster, entrant, slot, esc = _funded(client, 20)
    client.post(f"/api/escrow/{esc['escrow_id']}/refund", headers=ADMIN)
    acts = [e.action for e in state.audit.recent(60) if (e.detail or {}).get("escrow_id") == esc["escrow_id"]]
    assert {"escrow_funded", "escrow_held", "escrow_refunded"} <= set(acts)


# ── Stripe test-mode funding path (webhook; Stripe faked) ─────────────────

def _webhook(client, monkeypatch, event):
    import stripe
    monkeypatch.setattr(kassa_payments, "stripe_ready", lambda: True)
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda payload, sig, secret: event)
    return client.post("/api/kassa/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t"})


def test_webhook_funds_escrow_once(client, monkeypatch):
    poster = _agent(client)
    slot = _mk_slot(client, poster)
    sid = f"cs_{uuid.uuid4().hex[:8]}"
    ev = {"type": "checkout.session.completed", "data": {"object": {
        "id": sid, "amount_total": 7500, "payment_status": "paid",
        "metadata": {"type": "escrow_funding", "mission_id": slot["mission_id"], "poster_id": poster["id"]}}}}
    r = _webhook(client, monkeypatch, ev)
    assert r.status_code == 200, r.text
    eid = r.json()["escrow_id"]
    rec = state.escrow.get(eid)
    assert rec["amount"] == 75.0 and rec["state"] == "held" and rec["source"] == "stripe_checkout"
    assert rec["poster_id"] == poster["id"]
    _webhook(client, monkeypatch, ev)                          # Stripe retry: no second escrow
    assert len(state.escrow.list(mission_id=slot["mission_id"])) == 1


def test_webhook_signature_still_required(client, monkeypatch):
    import stripe
    monkeypatch.setattr(kassa_payments, "stripe_ready", lambda: True)
    def boom(*a, **k):
        raise ValueError("bad sig")
    monkeypatch.setattr(stripe.Webhook, "construct_event", boom)
    r = client.post("/api/kassa/webhooks/stripe", content=b"{}", headers={"stripe-signature": "x"})
    assert r.status_code == 400


def test_unpaid_session_does_not_fund(client, monkeypatch):
    poster = _agent(client)
    slot = _mk_slot(client, poster)
    ev = {"type": "checkout.session.completed", "data": {"object": {
        "id": "cs_unpaid_1", "amount_total": 1000, "payment_status": "unpaid",
        "metadata": {"type": "escrow_funding", "mission_id": slot["mission_id"], "poster_id": poster["id"]}}}}
    _webhook(client, monkeypatch, ev)
    assert state.escrow.list(mission_id=slot["mission_id"]) == []


# ── seller tier on the Stripe binding ─────────────────────────────────────

def test_seller_tier_inputs_stored_and_fee_read_from_config(client, monkeypatch):
    from app.routes import connect
    monkeypatch.setattr(kassa_payments, "create_connected_account",
                        lambda **kw: {"account_id": f"acct_{uuid.uuid4().hex[:8]}"})
    a = _agent(client)
    acct = client.post("/api/connect/accounts", headers=a["jwt"],
                       json={"display_name": "S", "email": "s@x.test"}).json()["account_id"]
    rec = next(r for r in state.runtime.registry if r["agent_id"] == a["id"])
    assert "governance_active" in rec["stripe_tier_inputs"]
    from app.economy import TIERS
    assert connect._seller_fee_percent(acct) == int(round(TIERS["ungoverned"]["fee_rate"] * 100))
    # a seller with governed-tier inputs gets the governed tier's configured rate
    rec["stripe_tier_inputs"] = {"governance_active": True}
    assert connect._seller_fee_percent(acct) == int(round(TIERS["governed"]["fee_rate"] * 100))
    assert connect._seller_fee_percent("acct_unbound") == kassa_payments.DEFAULT_APP_FEE_PERCENT


# ── Stripe rehearsal script guards ────────────────────────────────────────

def test_rehearsal_script_refuses_live_key_and_remote_host():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "p5_rehearsal", Path(__file__).resolve().parents[1] / "scripts" / "p5_stripe_rehearsal.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for bad in (None, "", "sk_live_abc", "rk_test_abc", "pk_test_abc"):
        with pytest.raises(SystemExit):
            mod.require_test_key(bad)
    assert mod.require_test_key("sk_test_abc") == "sk_test_abc"
    with pytest.raises(SystemExit):
        mod.require_local("https://agent-universe-production.up.railway.app")
    assert mod.require_local("http://127.0.0.1:8300/") == "http://127.0.0.1:8300"
    # the signature the script produces is what stripe's own verifier accepts
    import stripe
    body = b'{"id":"evt_1","object":"event","type":"x","data":{"object":{}}}'
    stripe.Webhook.construct_event(body, mod.sign_webhook(body, "whsec_t"), "whsec_t")


def test_escrow_release_queues_no_standalone_anchor(client, tmp_path):
    """Integration: Q5: a release is anchored only via its completed Agreement, never on its own."""
    from app import anchor_outbox as ao
    ob = ao.AnchorOutbox(tmp_path / "anchor.db")
    ao.configure(ob)
    try:
        poster, entrant, slot, esc = _funded(client, 100)
        eid = esc["escrow_id"]
        for amt in (30, 20):
            r = client.post(f"/api/escrow/{eid}/release", headers=ADMIN, json={"agent_id": entrant["id"], "amount": amt})
            assert r.status_code == 200, r.text
        kinds = [j["kind"] for j in ob.jobs()]
        assert kinds == []
    finally:
        ao.configure(None)
