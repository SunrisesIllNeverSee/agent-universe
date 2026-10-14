"""P5g G2 option D -- poster-declared answer_window_hours: storage, validated/clamped input on post
creation, and the frontend form field. Nudge timing only; nothing expires, nothing moves money."""
import sqlite3
from pathlib import Path

import pytest

from app import workentry_store as ws
from app.kassa_store import KassaStore
from tests.test_routes_kassa import _auth_headers, _kassa_signup, _post_payload

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("raw,want", [
    (None, None), ("", None), (1, 12.0), (12, 12.0), (48, 48.0), ("72", 72.0),
    (168, 168.0), (500, 168.0), (36.5, 36.5)])
def test_clamp(raw, want):
    assert ws.clamp_answer_window(raw) == want


@pytest.mark.parametrize("bad", [0, -5, True, "abc", float("nan"), float("inf"), [1], {}])
def test_clamp_rejects(bad):
    with pytest.raises(ValueError):
        ws.clamp_answer_window(bad)


def test_migration_adds_column_to_legacy_db(tmp_path):
    db = tmp_path / "legacy.db"
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE posts (id TEXT PRIMARY KEY, _v INTEGER DEFAULT 1, tab TEXT NOT NULL, "
              "title TEXT NOT NULL, tag TEXT NOT NULL DEFAULT '', body TEXT NOT NULL DEFAULT '', "
              "status TEXT NOT NULL DEFAULT 'open', urgency TEXT NOT NULL DEFAULT 'normal', "
              "upvotes INTEGER NOT NULL DEFAULT 0, reply_count INTEGER NOT NULL DEFAULT 0, reward TEXT, "
              "from_name TEXT NOT NULL DEFAULT '', from_email TEXT NOT NULL DEFAULT '', "
              "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
    c.commit(); c.close()
    for _ in range(2):  # idempotent
        s = KassaStore(db)
        cols = [r[1] for r in s._conn.execute("PRAGMA table_info(posts)")]
        assert "answer_window_hours" in cols
        s.close()


def _create(client, token, **extra):
    return client.post("/api/kassa/posts", json={**_post_payload("bounties"), **extra},
                       headers=_auth_headers(token))


def test_agent_post_stores_clamped_window_in_review(client):
    _, _, token = _kassa_signup(client)
    r = _create(client, token, answer_window_hours=1000)
    assert r.status_code == 200
    from app.deps import state
    rev = state.kassa.get_review(f"rev-{r.json()['id']}")
    assert rev["post"]["answer_window_hours"] == 168.0


def test_default_is_none(client):
    _, _, token = _kassa_signup(client)
    r = _create(client, token)
    assert r.status_code == 200
    from app.deps import state
    assert state.kassa.get_review(f"rev-{r.json()['id']}")["post"]["answer_window_hours"] is None


@pytest.mark.parametrize("bad", [0, -1, "soon", True])
def test_invalid_is_400(admin_client, bad):
    r = admin_client.post("/api/kassa/posts", json={**_post_payload("bounties"), "answer_window_hours": bad})
    assert r.status_code == 400


def test_admin_post_roundtrips_through_get_and_feeds_the_entry_terms(admin_client):
    r = admin_client.post("/api/kassa/posts", json={**_post_payload("bounties"), "answer_window_hours": 6})
    assert r.status_code == 200
    got = admin_client.get(f"/api/kassa/posts/{r.json()['id']}").json()
    assert got["answer_window_hours"] == 12.0
    from app.deps import state
    assert state.kassa.get_post(r.json()["id"])["answer_window_hours"] == 12.0


def test_frontend_form_has_optional_input_and_sends_it():
    html = (REPO / "frontend" / "kassa.html").read_text()
    assert 'id="modal-answer-window"' in html
    i = html.index('id="modal-answer-window"')
    tag = html[html.rfind("<input", 0, i):html.index(">", i)]
    assert 'min="12"' in tag and 'max="168"' in tag and "required" not in tag
    assert "payload.answer_window_hours" in html
