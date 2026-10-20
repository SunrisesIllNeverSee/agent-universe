"""Hotfix 2026-10-20: public metrics writes are closed; public GET drops money fields.

POST /api/metrics/agent and /api/metrics/mission used to be open to anyone and fed the
leaderboard order and the tier filter (self-reported counts). They are now operator-only
(X-Admin-Key). GET /api/metrics stays public but no longer returns revenue, costs, roi or
the financial block.
"""
import uuid

from app.metrics_io import load_metrics

AGENT_BODY = {"agent_id": "hotfix-victim", "name": "V", "event": "mission_complete"}
MISSION_BODY = {"mission_id": "hotfix-m", "label": "x", "event": "ended"}
MONEY_KEYS = {"revenue", "costs", "roi"}


def _agent(client):
    from tests.conftest import signup_agent
    ip = f"10.7.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"mw-{uuid.uuid4().hex[:6]}", ip=ip).json()
    lg = client.post("/api/provision/login", json={"agent_id": d["agent_id"], "api_key": d["api_key"]},
                     headers={"x-forwarded-for": ip})
    return {"id": d["agent_id"],
            "key": {"Authorization": "Bearer " + d["api_key"]},
            "jwt": {"Authorization": "Bearer " + lg.json()["token"]}}


def test_anonymous_agent_metric_post_is_refused_and_writes_nothing(client):
    before = load_metrics()
    r = client.post("/api/metrics/agent", json=AGENT_BODY)
    assert r.status_code == 403
    assert "hotfix-victim" not in load_metrics()["agents"]
    assert load_metrics()["agents"].keys() == before["agents"].keys()


def test_anonymous_empty_body_post_does_not_create_unknown_entry(client):
    """The T27 case: an empty body defaulted agent_id to 'unknown' and created an entry."""
    had = "unknown" in load_metrics()["agents"]
    r = client.post("/api/metrics/agent", json={})
    assert r.status_code == 403
    assert ("unknown" in load_metrics()["agents"]) == had


def test_anonymous_mission_metric_post_is_refused(client):
    r = client.post("/api/metrics/mission", json=MISSION_BODY)
    assert r.status_code == 403
    assert "hotfix-m" not in load_metrics()["missions"]


def test_any_path_under_metrics_post_is_refused(client):
    for path in ("/api/metrics/agent", "/api/metrics/mission", "/api/metrics/whatever", "/api/metrics/"):
        assert client.post(path, json={}).status_code == 403, path


def test_registered_agent_cannot_write_metrics_with_key_or_jwt(client):
    a = _agent(client)
    body = {"agent_id": a["id"], "event": "mission_complete"}
    for hdr in (a["key"], a["jwt"]):
        assert client.post("/api/metrics/agent", json=body, headers=hdr).status_code == 403
        assert client.post("/api/metrics/mission", json=MISSION_BODY, headers=hdr).status_code == 403
    assert load_metrics()["agents"].get(a["id"], {}).get("missions_completed", 0) == 0


def test_wrong_admin_key_is_refused(client):
    r = client.post("/api/metrics/agent", json=AGENT_BODY, headers={"X-Admin-Key": "nope"})
    assert r.status_code == 403
    assert "hotfix-victim" not in load_metrics()["agents"]


def test_operator_can_still_write_metrics(admin_client):
    aid = f"op-{uuid.uuid4().hex[:6]}"
    r = admin_client.post("/api/metrics/agent", json={"agent_id": aid, "name": "Op", "event": "mission_complete"})
    assert r.status_code == 200 and r.json()["logged"] is True
    assert load_metrics()["agents"][aid]["missions_completed"] == 1
    mid = f"om-{uuid.uuid4().hex[:6]}"
    r = admin_client.post("/api/metrics/mission", json={"mission_id": mid, "label": "x", "event": "message"})
    assert r.status_code == 200 and mid in load_metrics()["missions"]


def test_public_get_has_no_money_fields(client, admin_client):
    aid = f"mf-{uuid.uuid4().hex[:6]}"
    admin_client.post("/api/metrics/agent", json={"agent_id": aid, "name": "M", "event": "revenue",
                                                  "amount": 123.45, "description": "secret-desc"})
    admin_client.post("/api/metrics/agent", json={"agent_id": aid, "event": "cost", "amount": 7})
    r = client.get("/api/metrics")
    assert r.status_code == 200
    d = r.json()
    assert "financial" not in d
    assert not (MONEY_KEYS & set(d["totals"]))
    row = next(x for x in d["scoreboard"] if x["agent_id"] == aid)
    assert not (MONEY_KEYS & set(row))
    assert "123.45" not in r.text and "secret-desc" not in r.text
    # the public scoreboard still carries the non-money columns
    assert {"agent_id", "name", "missions", "success_rate", "compliance_score", "messages", "last_active"} <= set(row)
    assert {"agents", "missions"} <= set(d["totals"])


def test_heartbeat_still_registers_agent_on_scoreboard(client):
    a = _agent(client)
    hb = client.post(f"/api/provision/heartbeat/{a['id']}", headers=a["key"])
    assert hb.status_code == 200, hb.text
    ids = {x["agent_id"] for x in client.get("/api/metrics").json()["scoreboard"]}
    assert a["id"] in ids
