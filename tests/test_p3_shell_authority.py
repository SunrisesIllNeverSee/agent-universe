"""P3 shell authority falsifier.

Claim under test: hosting a page inside /shell grants NO permission. A request
that carries same-origin /shell Referer/Origin headers must be treated exactly
like the same request without them, for anonymous and forged-credential callers.

Statuses are compared against the no-header baseline (not hard-coded) so the
test pins "shell origin changes nothing"; a separate assertion pins that the
baseline itself is a rejection (4xx, never 2xx).
"""
import pytest

SHELL_HDRS = {
    "Referer": "http://localhost:8941/shell?route=/kassa",
    "Origin": "http://localhost:8941",
}
FORGED_HDRS = {
    "Authorization": "Bearer forged.garbage.token",
    "X-Agent-Key": "forged",
    "X-Admin-Key": "forged",
}

# (method, path, json body) — consequential verbs reachable from hosted pages.
# Routes: app/routes/kassa.py (stake/stakes/posts/upvote/messages/close),
# app/routes/missions.py (missions, slots), app/routes/governance.py (vote),
# app/routes/economy.py (withdraw), app/routes/forums.py (threads).
ENDPOINTS = [
    ("POST", "/api/kassa/posts/p1/stake", {"amount": 1}),
    ("DELETE", "/api/kassa/stakes/s1", None),
    ("POST", "/api/kassa/posts", {"title": "t", "body": "b", "kind": "offer"}),
    ("POST", "/api/slots/fill", {"slot_id": "s", "agent_id": "victim"}),
    ("POST", "/api/slots/leave", {"slot_id": "s", "agent_id": "victim"}),
    ("POST", "/api/slots/create", {"mission_id": "m", "role": "r"}),
    ("POST", "/api/slots/bounty", {"slot_id": "s", "amount": 1}),
    ("POST", "/api/missions", {"label": "probe", "objective": "x"}),
    ("POST", "/api/missions/m1/end", {}),
    ("POST", "/api/missions/m1/update", {}),
    ("POST", "/api/governance/meeting/m1/vote",
     {"voter": "victim", "motion_id": "x", "vote": "yea"}),
    ("POST", "/api/economy/withdraw",
     {"agent_id": "victim", "amount": 1, "chain": "base", "address": "0x0"}),
    ("POST", "/api/forums/threads", {"title": "t", "body": "b"}),
    # Resource lookup (404) precedes the claim check on these three, so the
    # uniformity assertion is weaker here (see EVIDENCE.md limitations).
    ("POST", "/api/kassa/posts/p1/upvote", {}),
    ("POST", "/api/kassa/threads/t1/messages", {"body": "x"}),
    ("POST", "/api/kassa/threads/t1/close", {}),
]
IDS = [f"{m} {p}" for m, p, _ in ENDPOINTS]


def _call(client, method, path, body, headers):
    return client.request(method, path, json=body, headers=headers).status_code


@pytest.mark.parametrize("method,path,body", ENDPOINTS, ids=IDS)
def test_anonymous_rejected_and_shell_origin_changes_nothing(client, method, path, body):
    base = _call(client, method, path, body, {})
    shell = _call(client, method, path, body, SHELL_HDRS)
    assert 400 <= base < 500, f"anonymous call was not rejected: {base}"
    assert shell == base, f"shell origin changed status {base} -> {shell}"


@pytest.mark.parametrize("method,path,body", ENDPOINTS, ids=IDS)
def test_forged_credentials_rejected_regardless_of_shell_origin(client, method, path, body):
    forged = _call(client, method, path, body, FORGED_HDRS)
    forged_shell = _call(client, method, path, body, {**SHELL_HDRS, **FORGED_HDRS})
    assert 400 <= forged < 500, f"forged call was not rejected: {forged}"
    assert forged_shell == forged


def test_shell_origin_grants_nothing_vs_anonymous_baseline(client):
    """Aggregate: header never flips any endpoint from rejected to accepted."""
    for method, path, body in ENDPOINTS:
        assert _call(client, method, path, body, SHELL_HDRS) >= 400, path


# Regression: formerly a strict xfail (anonymous availability write accepted);
# fixed by claude/h1-availability-auth 3036503 (owner credential required).
def test_availability_write_requires_authority(client):
    r = client.post("/api/availability/victim-agent", json={"available_now": True})
    assert r.status_code in (401, 403)
