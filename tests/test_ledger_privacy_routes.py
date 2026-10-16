"""Ledger privacy (owner-approved 2026-10-16).

Per-agent money (balances, ledger history, trial liability, fee credits, commissions,
recruitment rewards) is readable by the agent itself (api_key or JWT) and the operator
(X-Admin-Key) only: anonymous -> 401, another agent -> 403, self/operator -> 200.
Aggregate platform totals stay public.
"""
from __future__ import annotations

import uuid

import pytest

from tests.conftest import signup_agent


def _agent(client) -> dict:
    ip = f"10.9.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"lp-{uuid.uuid4().hex[:6]}", ip=ip).json()
    lg = client.post("/api/provision/login", json={"agent_id": d["agent_id"], "api_key": d["api_key"]},
                     headers={"x-forwarded-for": ip})
    assert lg.status_code == 200, lg.text
    return {"id": d["agent_id"], "key": {"Authorization": f"Bearer {d['api_key']}"},
            "jwt": {"Authorization": f"Bearer {lg.json()['token']}"}}


@pytest.fixture
def pair(client):
    from app.deps import state
    a, b = _agent(client), _agent(client)
    state.economy.treasury.credit(a["id"], 41.25, reason="lp_test_credit", mission_id="lp-mission")
    state.economy.fee_credits.credit(a["id"], 9.5, pack_name="lp-pack")
    state.economy.trials.init_trial(a["id"])
    state.economy.trials.record_trial_mission(a["id"], 3.25)
    return a, b


PER_AGENT_ROUTES = (
    "/api/economy/history/{id}",
    "/api/economy/trial/{id}",
    "/api/mpp/balance/{id}",
    "/api/fee-credits/balance/{id}",
    "/api/kassa/recruitments/{id}/stats",
)


@pytest.mark.parametrize("route", PER_AGENT_ROUTES)
def test_per_agent_money_route_binds_to_caller(client, admin_client, pair, route):
    a, b = pair
    url = route.format(id=a["id"])
    assert client.get(url).status_code == 401                       # anonymous
    assert client.get(url, headers=b["key"]).status_code == 403     # another agent (api key)
    assert client.get(url, headers=b["jwt"]).status_code == 403     # another agent (JWT)
    for headers in (a["key"], a["jwt"]):                            # the agent itself
        r = client.get(url, headers=headers)
        assert r.status_code == 200, r.text
    assert admin_client.get(url).status_code == 200                 # operator


@pytest.mark.parametrize("route", PER_AGENT_ROUTES)
def test_forged_or_wrong_admin_credential_fails_closed(client, pair, route):
    a, _ = pair
    url = route.format(id=a["id"])
    assert client.get(url, headers={"Authorization": "Bearer not-a-real-key"}).status_code == 401
    assert client.get(url, headers={"X-Admin-Key": "wrong-key"}).status_code == 401


def test_owner_sees_own_values(client, admin_client, pair):
    a, _ = pair
    hist = client.get(f"/api/economy/history/{a['id']}", headers=a["jwt"]).json()
    assert any(t["reason"] == "lp_test_credit" and t["amount"] == 41.25 for t in hist["transactions"])
    assert client.get(f"/api/mpp/balance/{a['id']}", headers=a["key"]).json()["balance"] == 41.25
    assert client.get(f"/api/fee-credits/balance/{a['id']}", headers=a["key"]).json()["balance"] == 9.5
    assert client.get(f"/api/economy/trial/{a['id']}", headers=a["key"]).json()["trial_liability"] == 3.25
    assert admin_client.get(f"/api/mpp/balance/{a['id']}").json()["balance"] == 41.25


def test_leaderboard_public_view_has_no_balances(client, admin_client, pair):
    a, _ = pair
    pub = client.get("/api/economy/leaderboard?trust=all").json()
    mine = [e for e in pub["leaderboard"] if e["agent_id"] == a["id"]]
    assert mine and set(mine[0]) == {"rank", "agent_id"}
    assert all("balance" not in e for e in pub["leaderboard"])
    op = admin_client.get("/api/economy/leaderboard?trust=all").json()
    assert any(e["agent_id"] == a["id"] and e["balance"] == 41.25 for e in op["leaderboard"])


def test_treasury_stays_public_and_recent_activity_has_explicit_fields(client):
    from app.deps import state
    state.economy.treasury.credit("platform", 1.5, reason="platform_fee", mission_id="lp-fee-mission")
    r = client.get("/api/treasury")
    assert r.status_code == 200
    data = r.json()
    assert "fees_collected" in data["treasury"]
    for row in data["recent_activity"]:
        assert set(row) <= {"timestamp", "amount", "reason", "mission_id"}


def test_commissions_private_to_parties_and_operator(client, admin_client, pair):
    a, b = pair
    c = _agent(client)
    r = admin_client.post("/api/kassa/commissions", json={
        "referrer_id": a["id"], "buyer_id": c["id"], "product_post_id": "lp-product", "purchase_amount": 120.0})
    assert r.status_code == 200, r.text
    cid = r.json()["commission_id"]
    url = "/api/kassa/commissions?product_post_id=lp-product"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=b["key"]).json() == []          # unrelated agent sees nothing
    assert client.get(f"/api/kassa/commissions?referrer_id={a['id']}", headers=b["jwt"]).json() == []
    for who in (a, c):                                             # referrer and buyer see the row
        rows = client.get(url, headers=who["jwt"]).json()
        assert [x["commission_id"] for x in rows] == [cid]
    assert client.get(url, headers=a["jwt"]).json()[0]["commission_amount"] == 6.0
    assert "commission_amount" not in client.get(url, headers=c["jwt"]).json()[0]   # buyer: not A's earnings
    assert any(x["commission_id"] == cid for x in admin_client.get(url).json())


def test_recruitments_private_to_parties_and_operator(client, admin_client, pair):
    a, b = pair
    c = _agent(client)
    r = admin_client.post("/api/kassa/recruitments", json={
        "recruiter_id": a["id"], "recruited_id": c["id"], "base_economic": 2.0})
    assert r.status_code == 200, r.text
    url = f"/api/kassa/recruitments?recruiter_id={a['id']}"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=b["key"]).json() == []
    assert client.get(url, headers=a["key"]).json()[0]["reward_economic"] == 2.0
    seen_by_recruited = client.get(url, headers=c["key"]).json()
    assert len(seen_by_recruited) == 1 and "reward_economic" not in seen_by_recruited[0]
    assert len(admin_client.get(url).json()) == 1
    stats = client.get(f"/api/kassa/recruitments/{a['id']}/stats", headers=a["jwt"]).json()
    assert stats["total_economic"] == 2.0


def test_product_review_reward_hidden_from_public(client, admin_client, pair):
    a, b = pair
    from app.deps import state
    state.kassa.insert_product_review({
        "review_id": f"PR-lp{uuid.uuid4().hex[:6]}", "product_post_id": "lp-review-product",
        "reviewer_id": a["id"], "reviewer_name": "lp", "reviewer_type": "AAI", "rating": 5, "body": "ok",
        "status": "pending", "reward": "77.5", "seed_doi": None, "created_at": "2026-10-16T00:00:00+00:00"})
    url = "/api/kassa/product-reviews?product_post_id=lp-review-product"
    pub = client.get(url).json()
    assert pub and all("reward" not in x for x in pub) and pub[0]["rating"] == 5
    assert all("reward" not in x for x in client.get(url, headers=b["key"]).json())
    assert client.get(url, headers=a["key"]).json()[0]["reward"] == "77.5"
    assert admin_client.get(url).json()[0]["reward"] == "77.5"


def test_public_seed_and_audit_views_drop_money_fields(client, admin_client, pair):
    a, _ = pair
    r = admin_client.post("/api/kassa/commissions", json={
        "referrer_id": a["id"], "buyer_id": "lp-buyer-xyz", "product_post_id": "lp-seed-product",
        "purchase_amount": 4321.0})
    assert r.status_code == 200
    doi = r.json()["seed_doi"]
    seed = client.get(f"/api/seeds/{doi}").json()
    meta = seed.get("metadata", seed.get("seed", {}).get("metadata", {}))
    assert "amount" not in meta and "buyer_id" not in meta
    assert meta.get("product_post_id") == "lp-seed-product"      # the event itself stays visible
    body = client.get("/api/audit").text
    assert "lp-buyer-xyz" not in client.get(f"/api/seeds/{doi}").text
    assert "216.05" not in body                                   # 5% commission on 4321.0


def test_public_projection_money_keys_dropped_at_any_depth():
    from app.public_projection import public_audit_event, public_seed
    ev = public_audit_event({"id": "1", "timestamp": "t", "component": "economy", "action": "escrow_checkout_initiated",
                             "detail": {"mission_id": "m1", "amount_cents": 12345, "nested": {"amount_usd": 9.99,
                                        "balance_after": 1.0, "fee_breakdown": {"gross": 5}}}})
    assert ev["detail"] == {"mission_id": "m1", "nested": {}}
    seed = public_seed({"doi": "au:x", "creator_id": "agent-1", "creator_type": "AAI", "source_type": "mission_payout",
                        "metadata": {"action": "mission_payout", "agent_id": "agent-1", "gross": 10.0,
                                     "net_to_agent": 9.0, "platform_fee": 1.0}})
    assert seed["metadata"] == {"action": "mission_payout", "agent_id": "agent-1"}
