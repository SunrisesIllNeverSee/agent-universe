"""test_p5c_escrow_rules.py — owner rulings Q1-Q3 (P5 long push) and their attack angles.

Q1 poster ends own funded mission = acceptance: even split across the mission's entrants.
Q2 leftover escrow refunds to the poster (audited + Seeded).
Q3 card-funded money is held N days (config settlement.chargeback_hold_days) before cashout.
"""
import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app import economy as economy_mod
from app import kassa_payments
from app.deps import state
from tests.test_p4_entry_api import _agent
from tests.test_p4_slot_binding import _fill, _mk_slot, _store

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}
JSON = {"content-type": "application/json"}


def _mission(client, poster, n):
    """A mission with ``n`` open slots (one Agreement each once filled)."""
    first = _mk_slot(client, poster)
    slots = [first]
    for _ in range(n - 1):
        slots.append(_mk_slot(client, poster, mission_id=first["mission_id"]))
    return first["mission_id"], slots


def _crew(client, n, amount, *, stripe=False, monkeypatch=None):
    poster = _agent(client)
    mission_id, slots = _mission(client, poster, n)
    if stripe:
        esc = _stripe_fund(client, monkeypatch, poster, mission_id, amount)
    else:
        esc = client.post("/api/escrow/fund", headers=ADMIN,
                          json={"mission_id": mission_id, "amount": amount}).json()["escrow"]
    entrants = []
    for s in slots:
        e = _agent(client)
        state.economy.trials.commit(e["id"])           # out of trial: the tier fee applies
        assert _fill(client, e, s["id"]).status_code == 200
        entrants.append(e)
    return poster, entrants, mission_id, esc


def _stripe_fund(client, monkeypatch, poster, mission_id, amount):
    import stripe
    monkeypatch.setattr(kassa_payments, "stripe_ready", lambda: True)
    ev = {"type": "checkout.session.completed", "data": {"object": {
        "id": f"cs_{uuid.uuid4().hex[:8]}", "amount_total": int(amount * 100), "payment_status": "paid",
        "metadata": {"type": "escrow_funding", "mission_id": mission_id, "poster_id": poster["id"]}}}}
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda payload, sig, secret: ev)
    r = client.post("/api/kassa/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t"})
    assert r.status_code == 200, r.text
    return state.escrow.get(r.json()["escrow_id"])


@pytest.fixture
def fake_stripe(monkeypatch):
    calls = []
    monkeypatch.setattr(kassa_payments, "create_connected_account",
                        lambda **kw: {"account_id": f"acct_{uuid.uuid4().hex[:8]}"})
    monkeypatch.setattr(kassa_payments, "get_account_status", lambda acct: {"charges_enabled": True})
    monkeypatch.setattr(kassa_payments, "create_transfer",
                        lambda **kw: calls.append(kw) or {"transfer_id": f"tr_{len(calls)}"})
    return calls


def _bind(client, who):
    r = client.post("/api/connect/accounts", headers=who["jwt"], json={"display_name": "x", "email": "x@x.test"})
    assert r.status_code == 200, r.text


def _cashout(client, who, amount):
    return client.post("/api/connect/cashout", headers=who["jwt"], json={"amount": amount})


def _mature(agent_id):
    """Pretend the hold window passed."""
    led = state.economy.treasury._ledger
    for h in led.get("holds", []):
        if h["agent_id"] == agent_id:
            h["matures_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    state.economy.treasury._save()


# ── Q1: poster ends own funded mission = acceptance ────────────────────────

def test_q1_poster_end_splits_evenly_across_entrants_with_fees_and_seeds(client):
    poster, entrants, mid, esc = _crew(client, 3, 90.0)
    r = client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    assert r.status_code == 200, r.text
    out = r.json()
    assert len(out["payouts"]) == 3 and out["payout_errors"] == []
    for p in out["payouts"]:
        assert p["fee_breakdown"]["gross"] == 30.0
        assert p["fee_breakdown"]["platform_fee"] == 1.5            # 5% from config
        assert p["seed"]["doi"]                                     # one Seed per payout
    for e in entrants:
        assert state.economy.treasury.balance(e["id"]) == 28.5
    assert state.escrow.get(esc["escrow_id"])["remaining"] == 0
    assert all(a["state"] == "completed" for a in _store().list_by_object("mission_id", mid))


def test_q1_trial_entrant_pays_no_fee(client):
    poster = _agent(client)
    mid, (slot,) = _mission(client, poster, 1)
    client.post("/api/escrow/fund", headers=ADMIN, json={"mission_id": mid, "amount": 20})
    e = _agent(client)                                              # fresh: in trial
    _fill(client, e, slot["id"])
    client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    assert state.economy.treasury.balance(e["id"]) == 20.0


def test_q1_poster_still_cannot_name_a_payout(client):
    poster, entrants, mid, esc = _crew(client, 1, 50.0)
    r = client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={"payout_per_slot": 49})
    assert r.status_code == 403
    assert state.escrow.get(esc["escrow_id"])["remaining"] == 50


def test_q1_entrant_who_walked_away_is_not_paid(client):
    poster, entrants, mid, esc = _crew(client, 2, 40.0)
    aid = _store().list_by_object("mission_id", mid)
    gone = next(a for a in aid if any(p["id"] == entrants[0]["id"] and p["role"] == "entrant" for p in a["principals"]))
    _store().terminate(gone["agreement_id"], actor=entrants[0]["id"], reason="leaving")
    client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    assert state.economy.treasury.balance(entrants[0]["id"]) == 0
    assert state.economy.treasury.balance(entrants[1]["id"]) == 38.0   # whole 40 to the one left, less 5%


def test_q1_rounding_remainder_stays_then_refunds_to_poster(client):
    poster, entrants, mid, esc = _crew(client, 3, 10.0)
    before = state.economy.treasury.balance(poster["id"])
    out = client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={}).json()
    assert [p["fee_breakdown"]["gross"] for p in out["payouts"]] == [3.3333] * 3
    assert out["escrow"]["refunded"] == 0.0001
    assert round(state.economy.treasury.balance(poster["id"]) - before, 4) == 0.0001


# ── Q2: leftover refunds to the poster, audited + Seeded ───────────────────

def test_q2_cancel_with_no_entrants_refunds_audited_and_seeded(client):
    poster = _agent(client)
    mid, _ = _mission(client, poster, 1)
    esc = client.post("/api/escrow/fund", headers=ADMIN, json={"mission_id": mid, "amount": 25}).json()["escrow"]
    before = state.economy.treasury.balance(poster["id"])
    out = client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={}).json()
    assert out["escrow"]["refunded"] == 25 and out["escrow"]["state"] == "refunded"
    assert round(state.economy.treasury.balance(poster["id"]) - before, 4) == 25
    assert state.escrow.get(esc["escrow_id"])["history"][-1]["transition"] == "refunded"
    assert out["escrow"]["state"] == "refunded"


# ── attack angles ──────────────────────────────────────────────────────────

def test_attack_poster_ends_twice_pays_once(client):
    poster, entrants, mid, esc = _crew(client, 2, 60.0)
    client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    bal = [state.economy.treasury.balance(e["id"]) for e in entrants]
    pb = state.economy.treasury.balance(poster["id"])
    r = client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    assert r.status_code in (200, 404, 409)
    assert [state.economy.treasury.balance(e["id"]) for e in entrants] == bal
    assert state.economy.treasury.balance(poster["id"]) == pb
    assert state.escrow.get(esc["escrow_id"])["released_total"] == 60.0


def test_attack_poster_ends_then_refunds_gets_nothing_back(client):
    poster, entrants, mid, esc = _crew(client, 1, 50.0)
    client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    pb = state.economy.treasury.balance(poster["id"])
    r = client.post(f"/api/escrow/{esc['escrow_id']}/refund", headers=poster["h"])
    assert r.status_code in (403, 409)
    assert state.economy.treasury.balance(poster["id"]) == pb


def test_attack_ended_poster_cannot_release_to_a_sock_puppet(client):
    poster, entrants, mid, esc = _crew(client, 1, 50.0)
    r = client.post(f"/api/escrow/{esc['escrow_id']}/release", headers=poster["h"],
                    json={"agent_id": poster["id"], "amount": 50})
    assert r.status_code == 403


# ── Q3: card-funded money is held before cashout ───────────────────────────

def test_q3_config_key_present_and_read():
    cfg = json.loads((economy_mod.Path(economy_mod.__file__).parent.parent / "config" / "economic_rates.json").read_text())
    assert cfg["settlement"]["chargeback_hold_days"] == economy_mod.CHARGEBACK_HOLD_DAYS == 7


def test_q3_card_funded_payout_is_held_and_cashout_is_capped(client, monkeypatch, fake_stripe):
    poster, entrants, mid, esc = _crew(client, 1, 100.0, stripe=True, monkeypatch=monkeypatch)
    e = entrants[0]
    _bind(client, e)
    client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    assert state.economy.treasury.balance(e["id"]) == 95.0
    r = _cashout(client, e, 10)
    assert r.status_code == 400 and not fake_stripe
    body = r.json()
    assert body["held"] == 95.0 and body["matured"] == 0 and body["held_until"]
    until = datetime.fromisoformat(body["held_until"])
    assert timedelta(days=6, hours=23) < until - datetime.now(UTC) <= timedelta(days=7, seconds=5)
    assert state.economy.treasury.balance(e["id"]) == 95.0           # nothing reserved


def test_q3_cashout_works_after_hold_matures_and_reports_held(client, monkeypatch, fake_stripe):
    poster, entrants, mid, esc = _crew(client, 1, 100.0, stripe=True, monkeypatch=monkeypatch)
    e = entrants[0]
    _bind(client, e)
    client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    _mature(e["id"])
    r = _cashout(client, e, 95)
    assert r.status_code == 200, r.text
    assert r.json()["held"] == 0 and fake_stripe[0]["amount_cents"] == 9500


def test_q3_operator_funded_and_existing_balances_are_not_held(client, fake_stripe):
    poster, entrants, mid, esc = _crew(client, 1, 100.0)
    e = entrants[0]
    _bind(client, e)
    state.economy.treasury.credit(e["id"], 5.0, reason="legacy")
    client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    r = _cashout(client, e, 100)                                    # 95 payout + 5 prior
    assert r.status_code == 200, r.text
    assert r.json()["held"] == 0


def test_q3_only_the_card_part_is_held_when_mixed(client, monkeypatch, fake_stripe):
    poster, entrants, mid, esc = _crew(client, 1, 100.0, stripe=True, monkeypatch=monkeypatch)
    e = entrants[0]
    _bind(client, e)
    state.economy.treasury.credit(e["id"], 5.0, reason="legacy")
    client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    assert _cashout(client, e, 5.01).status_code == 400
    assert _cashout(client, e, 5).status_code == 200


def test_q3_refund_of_card_money_to_poster_is_held_too(client, monkeypatch, fake_stripe):
    poster = _agent(client)
    mid, _ = _mission(client, poster, 1)
    _stripe_fund(client, monkeypatch, poster, mid, 30.0)
    _bind(client, poster)
    client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    assert state.economy.treasury.balance(poster["id"]) == 30.0
    r = _cashout(client, poster, 30)
    assert r.status_code == 400 and r.json()["held"] == 30.0


def test_attack_cashout_before_hold_matures(client, monkeypatch, fake_stripe):
    poster, entrants, mid, esc = _crew(client, 1, 40.0, stripe=True, monkeypatch=monkeypatch)
    e = entrants[0]
    _bind(client, e)
    client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    for amt in (38, 0.01):
        assert _cashout(client, e, amt).status_code == 400
    assert not fake_stripe


def test_attack_many_small_cashouts_cannot_bypass_the_hold(client, monkeypatch, fake_stripe):
    poster, entrants, mid, esc = _crew(client, 1, 40.0, stripe=True, monkeypatch=monkeypatch)
    e = entrants[0]
    _bind(client, e)
    state.economy.treasury.credit(e["id"], 3.0, reason="legacy")    # 3 is cashable, the 38 is held
    client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    ok = sum(1 for _ in range(30) if _cashout(client, e, 1).status_code == 200)
    assert ok == 3
    assert sum(c["amount_cents"] for c in fake_stripe) == 300
    assert state.economy.treasury.balance(e["id"]) == 38.0


def test_attack_withdraw_route_cannot_bypass_the_hold(client, monkeypatch):
    poster, entrants, mid, esc = _crew(client, 1, 40.0, stripe=True, monkeypatch=monkeypatch)
    e = entrants[0]
    client.post(f"/api/missions/{mid}/end", headers=poster["h"], json={})
    r = client.post("/api/economy/withdraw", json={"agent_id": e["id"], "amount": 10, "chain": "base", "to": "0x" + "1" * 40})
    assert state.economy.treasury.balance(e["id"]) == 38.0
    assert r.status_code != 200 or "error" in r.json() or r.json().get("withdrawal") in (None, {"status": "pending", "agent_id": e["id"], "amount": 10})


def test_q3_hold_survives_reload(client, monkeypatch, tmp_path):
    t = economy_mod.AgentTreasury(tmp_path)
    t.credit("a", 10, reason="x")
    t.hold("a", 10, days=7, reason="card", ref="esc-1")
    t2 = economy_mod.AgentTreasury(tmp_path)
    assert t2.held_balance("a") == 10 and t2.matured_balance("a") == 0
