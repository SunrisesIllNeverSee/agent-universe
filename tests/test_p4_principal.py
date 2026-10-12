"""P4 slice 2 -- one principal (either door) + poster binding + magic-link credential."""
import hashlib
import secrets
import uuid
from datetime import UTC, datetime

import pytest

from tests.conftest import signup_agent

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


def _agent(client):
    ip = f"10.9.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"p2-{uuid.uuid4().hex[:6]}", ip=ip).json()
    lg = client.post("/api/provision/login", json={"agent_id": d["agent_id"], "api_key": d["api_key"]},
                     headers={"x-forwarded-for": ip})
    assert lg.status_code == 200, lg.text
    return {"agent_id": d["agent_id"], "api_key": d["api_key"], "jwt": lg.json()["token"], "ip": ip}


def _bearer(t):
    return {"Authorization": f"Bearer {t}"}


def _post_body(s=None):
    s = s or uuid.uuid4().hex[:4]
    return {"title": f"P2 {s}", "tab": "iso", "body": "slice two body", "tag": "iso",
            "from_name": f"Tester-{s}", "from_email": f"t-{s}@example.com"}


def _thread(post_id):
    """Insert a thread directly with a known magic token; return (thread_id, plain)."""
    from app.deps import state
    plain = secrets.token_urlsafe(32)
    tid = f"thr-{secrets.token_hex(6)}"
    now = datetime.now(UTC).isoformat()
    state.kassa.insert_thread({
        "thread_id": tid, "post_id": post_id, "post_tab": "iso", "post_title": "t",
        "agent_id": "someone", "agent_name": "x", "poster_name": "P", "poster_email": "p@example.com",
        "magic_token": hashlib.sha256(plain.encode()).hexdigest(), "status": "open",
        "message_count": 0, "created_at": now, "updated_at": now})
    return tid, plain


def _live_post(admin_client, poster_agent_id=None):
    r = admin_client.post("/api/kassa/posts", json=_post_body())
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ── same agent, either door = same principal ─────────────────────────────────

def test_both_doors_resolve_to_same_principal(client):
    a = _agent(client)
    by_key = client.get("/api/principal", headers=_bearer(a["api_key"]))
    by_jwt = client.get("/api/principal", headers=_bearer(a["jwt"]))
    assert by_key.status_code == 200 and by_jwt.status_code == 200
    assert by_key.json()["agent_id"] == by_jwt.json()["agent_id"] == a["agent_id"]
    assert by_key.json()["credential_type"] == "api_key"
    assert by_jwt.json()["credential_type"] == "jwt"
    assert by_key.json()["ref"] == f"{a['agent_id']}#api_key"


def test_no_credential_401(client):
    assert client.get("/api/principal").status_code == 401


def test_forged_credentials_401(client):
    a = _agent(client)
    assert client.get("/api/principal", headers=_bearer("cmd_ak_" + "0" * 64)).status_code == 401
    assert client.get("/api/principal", headers=_bearer(a["jwt"][:-4] + "AAAA")).status_code == 401
    assert client.get("/api/principal", headers=_bearer("garbage")).status_code == 401


def test_revoked_both_doors_401(client, admin_client):
    a = _agent(client)
    assert client.get("/api/principal", headers=_bearer(a["jwt"])).status_code == 200
    rv = admin_client.post("/api/provision/revoke", json={"agent_id": a["agent_id"]})
    assert rv.status_code == 200
    assert client.get("/api/principal", headers=_bearer(a["api_key"])).status_code == 401
    # JWT dies with the credential (token_epoch bumped), even before expiry.
    assert client.get("/api/principal", headers=_bearer(a["jwt"])).status_code == 401


def test_rotated_key_kills_old_jwt_and_old_key(client, admin_client):
    a = _agent(client)
    r = admin_client.post("/api/provision/key", json={"agent_id": a["agent_id"], "requested_by": "t"})
    assert r.status_code == 200
    new_key = r.json()["key"]
    assert client.get("/api/principal", headers=_bearer(a["jwt"])).status_code == 401
    assert client.get("/api/principal", headers=_bearer(a["api_key"])).status_code == 401
    assert client.get("/api/principal", headers=_bearer(new_key)).status_code == 200


def test_helper_resolver_directly(app):
    """The helper is usable without HTTP (later slices call it from routes/MCP)."""
    from starlette.requests import Request
    from app.deps import state
    from app.principal import Principal, resolve_principal
    from fastapi import HTTPException
    req = Request({"type": "http", "headers": [], "query_string": b"", "method": "GET", "path": "/"})
    with pytest.raises(HTTPException) as e:
        resolve_principal(req, state)
    assert e.value.status_code == 401
    p = Principal("agent", "jwt", "agent-x")
    assert p.ref == "agent-x#jwt"
    with pytest.raises(HTTPException) as e:
        Principal("poster_link", "magic_link", thread_id="t", post_id="K-1").require_agent()
    assert e.value.status_code == 403


# ── poster binding ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("door", ["api_key", "jwt"])
def test_post_via_either_door_records_poster_agent_id(client, admin_client, door):
    a = _agent(client)
    r = client.post("/api/kassa/posts", json=_post_body(), headers=_bearer(a[door]))
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    # lives in the review queue; approval persists the post with the binding
    rev = admin_client.get("/api/operator/reviews", params={"status": "pending"}).json()
    mine = next(x for x in rev if x["review_id"] == f"rev-{pid}")
    assert mine["post"]["poster_agent_id"] == a["agent_id"]
    assert admin_client.patch(f"/api/operator/reviews/rev-{pid}", params={"action": "approve"}).status_code == 200
    from app.deps import state
    assert state.kassa.get_post(pid)["poster_agent_id"] == a["agent_id"]


def test_admin_post_has_no_poster_agent(admin_client):
    pid = _live_post(admin_client)
    from app.deps import state
    assert state.kassa.get_post(pid)["poster_agent_id"] is None


def test_post_with_revoked_or_forged_credential_401(client, admin_client):
    a = _agent(client)
    admin_client.post("/api/provision/revoke", json={"agent_id": a["agent_id"]})
    assert client.post("/api/kassa/posts", json=_post_body(), headers=_bearer(a["api_key"])).status_code == 401
    assert client.post("/api/kassa/posts", json=_post_body(), headers=_bearer("cmd_ak_" + "1" * 64)).status_code == 401
    assert client.post("/api/kassa/posts", json=_post_body()).status_code == 401


def test_additive_migration_is_idempotent_and_upgrades_old_db(tmp_path):
    import sqlite3
    from app.kassa_store import KassaStore
    db = tmp_path / "old.db"
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE posts (id TEXT PRIMARY KEY, _v INTEGER DEFAULT 1, tab TEXT NOT NULL, title TEXT NOT NULL,"
              " tag TEXT NOT NULL DEFAULT '', body TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'open',"
              " urgency TEXT NOT NULL DEFAULT 'normal', upvotes INTEGER NOT NULL DEFAULT 0,"
              " reply_count INTEGER NOT NULL DEFAULT 0, reward TEXT, from_name TEXT NOT NULL DEFAULT '',"
              " from_email TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
    c.execute("INSERT INTO posts (id, tab, title, created_at, updated_at) VALUES ('K-1','iso','t','x','x')")
    c.commit(); c.close()
    s = KassaStore(db); s.close()
    s = KassaStore(db)  # second open must not fail
    assert s.get_post("K-1")["poster_agent_id"] is None
    s.close()


# ── magic-link credential ────────────────────────────────────────────────────

def test_magic_link_resolves_to_post_scoped_principal(client, admin_client):
    pid = _live_post(admin_client)
    tid, plain = _thread(pid)
    r = client.get("/api/principal", headers={"X-Magic-Token": plain})
    assert r.status_code == 200
    d = r.json()
    assert d["credential_type"] == "magic_link" and d["post_id"] == pid and d["thread_id"] == tid
    assert d["agent_id"] is None
    assert client.get("/api/principal", params={"magic": plain}).status_code == 200


def test_magic_link_forged_or_wrong_thread_401(client, admin_client):
    pid = _live_post(admin_client)
    tid, plain = _thread(pid)
    other_tid, _ = _thread(pid)
    assert client.get("/api/principal", headers={"X-Magic-Token": plain + "x"}).status_code == 401
    # the stored hash itself is not a usable credential
    assert client.get("/api/principal",
                      headers={"X-Magic-Token": hashlib.sha256(plain.encode()).hexdigest()}).status_code == 401
    assert client.get("/api/principal", headers={"X-Magic-Token": plain},
                      params={"thread_id": other_tid}).status_code == 401


def test_magic_link_audited(client, admin_client, monkeypatch):
    from app.deps import state
    seen = []
    orig = state.audit.log
    monkeypatch.setattr(state.audit, "log", lambda c, a, d=None: (seen.append((c, a, d)), orig(c, a, d))[1])
    pid = _live_post(admin_client)
    tid, plain = _thread(pid)
    seen.clear()
    client.get("/api/principal", headers={"X-Magic-Token": plain})
    client.get("/api/principal", headers={"X-Magic-Token": "nope"})
    acts = [a for c, a, d in seen if c == "auth"]
    assert "magic_link_resolved" in acts and "magic_link_rejected" in acts
    assert all(plain not in str(d) for c, a, d in seen)


def test_magic_link_cannot_act_on_another_post(client, admin_client):
    from app.deps import state
    from app.principal import acts_for_post_owner, resolve_principal
    from fastapi import HTTPException
    from starlette.requests import Request
    p1, p2 = _live_post(admin_client), _live_post(admin_client)
    tid, plain = _thread(p1)
    req = Request({"type": "http", "headers": [(b"x-magic-token", plain.encode())],
                   "query_string": b"", "method": "GET", "path": "/"})
    pr = resolve_principal(req, state, allow_magic=True)
    pr.require_post(p1)  # own post OK
    with pytest.raises(HTTPException) as e:
        pr.require_post(p2)
    assert e.value.status_code == 403
    assert acts_for_post_owner(pr, state.kassa.get_post(p1))
    assert not acts_for_post_owner(pr, state.kassa.get_post(p2))
    with pytest.raises(HTTPException) as e:
        pr.require_agent()
    assert e.value.status_code == 403


def test_agent_is_owner_only_of_own_posts(client, admin_client):
    from app.deps import state
    from app.principal import acts_for_post_owner, Principal
    a, b = _agent(client), _agent(client)
    r = client.post("/api/kassa/posts", json=_post_body(), headers=_bearer(a["jwt"]))
    pid = r.json()["id"]
    admin_client.patch(f"/api/operator/reviews/rev-{pid}", params={"action": "approve"})
    post = state.kassa.get_post(pid)
    assert acts_for_post_owner(Principal("agent", "jwt", a["agent_id"]), post)
    assert not acts_for_post_owner(Principal("agent", "api_key", b["agent_id"]), post)
    assert not acts_for_post_owner(Principal("operator", "admin_key"), post)


def test_magic_link_for_closed_thread_401(client, admin_client):
    from app.deps import state
    pid = _live_post(admin_client)
    tid, plain = _thread(pid)
    state.kassa.update_thread(tid, {"status": "closed"})
    assert client.get("/api/principal", headers={"X-Magic-Token": plain}).status_code == 401
