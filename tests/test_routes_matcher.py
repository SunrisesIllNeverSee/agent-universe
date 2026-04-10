"""
test_routes_matcher.py — HTTP contract tests for app/routes/matcher.py

2 endpoints: match for a specific post, match all open posts.
Both are public GET endpoints — no auth required.
"""
import uuid
from tests.test_routes_kassa import _kassa_signup, _auth_headers, _post_payload


# ── Matcher ───────────────────────────────────────────────────────────────────

def test_match_all_open_posts(client):
    r = client.get("/api/match")
    assert r.status_code == 200
    d = r.json()
    assert "matches" in d


def test_match_post_404(client):
    r = client.get("/api/match/nonexistent-post-xyz")
    assert r.status_code == 404


def test_match_post_returns_scored_list(client, admin_client):
    # Create a post to match against
    create = admin_client.post("/api/kassa/posts", json=_post_payload("iso"))
    assert create.status_code == 200
    post_id = create.json()["id"]

    r = client.get(f"/api/match/{post_id}")
    assert r.status_code == 200
    d = r.json()
    assert "post_id" in d
    assert "matches" in d
    assert "count" in d


def test_match_limit_param(client, admin_client):
    create = admin_client.post("/api/kassa/posts", json=_post_payload("bounties"))
    assert create.status_code == 200
    post_id = create.json()["id"]

    r = client.get(f"/api/match/{post_id}", params={"limit": 2})
    assert r.status_code == 200
    d = r.json()
    assert len(d.get("matches", [])) <= 2
