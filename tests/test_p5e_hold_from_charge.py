"""test_p5e_hold_from_charge.py — the chargeback hold counts from the card charge, not from payout."""
import logging
import uuid
from datetime import UTC, datetime, timedelta

from app import economy as economy_mod
from app import kassa_payments
from app.deps import state
from tests.test_p5c_escrow_rules import _crew, _stripe_fund
from tests.test_p4_entry_api import _agent
from tests.test_p5c_escrow_rules import _mission

DAYS = economy_mod.CHARGEBACK_HOLD_DAYS


def _t(tmp_path):
    t = economy_mod.AgentTreasury(tmp_path)
    t.credit("a", 10, reason="x")
    return t


def _dt(s):
    return datetime.fromisoformat(s)


def test_hold_counts_from_charge_time(tmp_path):
    charged = datetime.now(UTC) - timedelta(days=3)
    h = _t(tmp_path).hold("a", 10, reason="card", ref="e", charged_at=charged.isoformat())
    assert _dt(h["matures_at"]) == charged + timedelta(days=DAYS)
    assert h["hold_basis"] == "charge_time" and h["charged_at"] == charged.isoformat()


def test_old_charge_is_already_matured(tmp_path):
    t = _t(tmp_path)
    t.hold("a", 10, reason="card", charged_at=(datetime.now(UTC) - timedelta(days=DAYS + 1)).isoformat())
    assert t.held_balance("a") == 0 and t.matured_balance("a") == 10 and t.held_until("a") is None


def test_fallback_to_payout_time_is_loud(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        h = _t(tmp_path).hold("a", 10, reason="card", ref="esc-x")
    assert h["hold_basis"] == "payout_time" and h["charged_at"] is None
    assert any("HOLD FALLBACK" in r.message and "esc-x" in r.message for r in caplog.records)
    assert abs(_dt(h["matures_at"]) - (datetime.now(UTC) + timedelta(days=DAYS))) < timedelta(seconds=5)


def test_garbage_charge_time_falls_back_loudly(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        h = _t(tmp_path).hold("a", 10, reason="card", charged_at="not-a-date")
    assert h["hold_basis"] == "payout_time"
    assert any("HOLD FALLBACK" in r.message for r in caplog.records)


def test_future_charge_time_cannot_extend_hold(tmp_path):
    h = _t(tmp_path).hold("a", 10, reason="card", charged_at=(datetime.now(UTC) + timedelta(days=30)).isoformat())
    assert _dt(h["matures_at"]) <= datetime.now(UTC) + timedelta(days=DAYS)


def test_naive_charge_time_treated_as_utc(tmp_path):
    charged = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=2)
    h = _t(tmp_path).hold("a", 10, reason="card", charged_at=charged.isoformat())
    assert _dt(h["matures_at"]) == charged.replace(tzinfo=UTC) + timedelta(days=DAYS)


def _fund_with_event_time(client, monkeypatch, poster, mission_id, amount, created):
    import stripe
    monkeypatch.setattr(kassa_payments, "stripe_ready", lambda: True)
    ev = {"type": "checkout.session.completed", "created": created, "data": {"object": {
        "id": f"cs_{uuid.uuid4().hex[:8]}", "amount_total": int(amount * 100), "payment_status": "paid",
        # a body-supplied time must be ignored
        "metadata": {"type": "escrow_funding", "mission_id": mission_id, "poster_id": poster["id"],
                     "charged_at": "2000-01-01T00:00:00+00:00"}}}}
    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda payload, sig, secret: ev)
    r = client.post("/api/kassa/webhooks/stripe", content=b"{}", headers={"stripe-signature": "t"})
    assert r.status_code == 200, r.text
    return state.escrow.get(r.json()["escrow_id"])


def test_webhook_records_charge_time_and_payout_hold_uses_it(client, monkeypatch):
    created = int((datetime.now(UTC) - timedelta(days=5)).timestamp())
    poster = _agent(client)
    mid, _slots = _mission(client, poster, 1)
    esc = _fund_with_event_time(client, monkeypatch, poster, mid, 40.0, created)
    assert _dt(esc["charged_at"]) == datetime.fromtimestamp(created, UTC)
    entrant = _agent(client)
    import asyncio
    from app.routes.escrow import release_to
    state.economy.trials.commit(entrant["id"])
    res = asyncio.run(release_to(esc["escrow_id"], entrant["id"], 10.0, source="test"))
    hold = res["hold"]
    assert hold["hold_basis"] == "charge_time"
    assert _dt(hold["matures_at"]) == datetime.fromtimestamp(created, UTC) + timedelta(days=DAYS)


def test_webhook_without_event_time_records_none_and_hold_falls_back(client, monkeypatch, caplog):
    poster = _agent(client)
    mid, _slots = _mission(client, poster, 1)
    esc = _stripe_fund(client, monkeypatch, poster, mid, 20.0)   # event carries no "created"
    assert esc["charged_at"] is None
    entrant = _agent(client)
    import asyncio
    from app.routes.escrow import release_to
    with caplog.at_level(logging.WARNING):
        res = asyncio.run(release_to(esc["escrow_id"], entrant["id"], 5.0, source="test"))
    assert res["hold"]["hold_basis"] == "payout_time"
    assert any("HOLD FALLBACK" in r.message for r in caplog.records)


def test_operator_funding_has_no_charge_time_and_no_hold(client):
    from tests.test_p5c_escrow_rules import ADMIN
    poster = _agent(client)
    mid, _ = _mission(client, poster, 1)
    esc = client.post("/api/escrow/fund", headers=ADMIN, json={"mission_id": mid, "amount": 10}).json()["escrow"]
    assert esc["charged_at"] is None


def test_refund_hold_uses_charge_time(client, monkeypatch):
    import asyncio
    from app.routes.escrow import refund_to_poster
    created = int((datetime.now(UTC) - timedelta(days=6)).timestamp())
    poster = _agent(client)
    mid, _ = _mission(client, poster, 1)
    esc = _fund_with_event_time(client, monkeypatch, poster, mid, 25.0, created)
    asyncio.run(refund_to_poster(esc["escrow_id"], reason="t"))
    h = [x for x in state.economy.treasury._ledger["holds"] if x["ref"] == esc["escrow_id"]][-1]
    assert h["hold_basis"] == "charge_time"
    assert _dt(h["matures_at"]) == datetime.fromtimestamp(created, UTC) + timedelta(days=DAYS)
