"""
test_p5_first_transaction.py — rehearsal of the first live transaction, locally.

One poster, one entrant, one paid mission, end to end through the real routes:
post (slot) → enter (Agreement active) → operator settles (payout + fee from
config + per-payout Seed) → Agreement completed with receipt → entrant links a
Stripe account → cash out to that account only. Stripe calls are faked; this
is the shape that goes to the owner for R_LIVE in Stripe test mode.
"""
import json
import uuid
from pathlib import Path

from app import kassa_payments
from app.deps import state
from tests.test_p4_entry_api import _agent
from tests.test_p4_slot_binding import _fill, _mk_slot, _store

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}
RATES = json.loads((Path(__file__).resolve().parents[1] / "config" / "economic_rates.json").read_text())


def test_first_transaction_end_to_end(client, monkeypatch):
    transfers = []
    monkeypatch.setattr(kassa_payments, "create_connected_account",
                        lambda **kw: {"account_id": f"acct_{uuid.uuid4().hex[:8]}"})
    monkeypatch.setattr(kassa_payments, "get_account_status", lambda acct: {"charges_enabled": True})
    monkeypatch.setattr(kassa_payments, "create_transfer",
                        lambda **kw: transfers.append(kw) or {"transfer_id": "tr_rehearsal"})

    poster, entrant = _agent(client), _agent(client)

    # 1. Poster posts work; entrant enters it (open mode) → Agreement active.
    slot = _mk_slot(client, poster)
    r = _fill(client, entrant, slot["id"])
    assert r.status_code == 200, r.text
    aid = r.json()["agreement_id"]
    assert _store().get(aid)["state"] == "active"

    # 2. The poster cannot name the payout; the operator settles.
    gross = 100.0
    r = client.post(f"/api/missions/{slot['mission_id']}/end", headers=poster["h"], json={"payout_per_slot": gross})
    assert r.status_code == 403
    before = state.economy.treasury.balance(entrant["id"])
    r = client.post(f"/api/missions/{slot['mission_id']}/end", headers=ADMIN, json={"payout_per_slot": gross})
    assert r.status_code == 200, r.text
    out = r.json()

    # 3. Payout: fee from config (trial → trial rate), one Seed, no silent errors.
    (payout,) = out["payouts"]
    expected_rate = RATES["trial"]["fee_rate"] if payout["trial"] else RATES["tiers"]["ungoverned"]["fee_rate"]
    net = payout["fee_breakdown"]["net_to_agent"]
    assert round(net, 4) == round(gross * (1 - expected_rate), 4)
    assert payout["seed"]["doi"]
    assert out["payout_errors"] == [] and out["provenance_errors"] == []
    assert round(state.economy.treasury.balance(entrant["id"]) - before, 4) == round(net, 4)

    # 4. Agreement completed, with a receipt that carries a Seed.
    assert out["agreements_completed"] == [aid]
    assert _store().get(aid)["state"] == "completed"
    assert _store().receipts(aid)[-1]["seed_doi"]

    # 5. Entrant links a Stripe account and cashes out — only to that account.
    acct = client.post("/api/connect/accounts", headers=entrant["jwt"],
                       json={"display_name": "Entrant", "email": "e@x.test"}).json()["account_id"]
    r = client.post("/api/connect/cashout", headers=entrant["jwt"], json={"amount": net})
    assert r.status_code == 200, r.text
    assert transfers[-1]["connected_account_id"] == acct
    assert round(state.economy.treasury.balance(entrant["id"]) - before, 4) == 0
