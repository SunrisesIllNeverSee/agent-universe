"""P3 shell authority: pre-mutation denial against EXISTING target entities.

test_p3_shell_authority.py proves status uniformity, but several of its probes
hit nonexistent entities (404 before any auth check), which is not evidence of
enforcement. Here every target entity is seeded into the session's isolated
temp data dir (conftest tmp_root; asserted below, never real data/), and for
each consequential verb we assert:

  * anonymous / forged / shell-origin / shell-origin+forged  -> 401/403
  * a wrong-principal (other registered agent) where the route binds identity
  * the backing store is byte-identical after the denied calls
  * the legitimate principal (owner agent or admin) succeeds, where safe

No Stripe, no network. Withdraw (money movement) stays denial-only.
"""
import json
import uuid

import pytest

from app.deps import state

SHELL_HDRS = {
    "Referer": "http://localhost:8941/shell?route=/kassa",
    "Origin": "http://localhost:8941",
}
FORGED_HDRS = {
    "Authorization": "Bearer forged.garbage.token",
    "X-Agent-Key": "forged",
    "X-Admin-Key": "forged",
}
DENIED = (401, 403)


# ── helpers ──────────────────────────────────────────────────────────────────

def _mint(client):
    """Register an agent via provision signup. Returns identity + both credentials."""
    ip = f"10.7.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    r = client.post(
        "/api/provision/signup",
        json={"name": f"p3a-{uuid.uuid4().hex[:6]}", "system": "claude"},
        headers={"x-forwarded-for": ip},
    )
    assert r.status_code == 200, r.text
    d = r.json()
    return {
        "id": d["agent_id"],
        "name": d["name"],
        "key": {"Authorization": f"Bearer {d['api_key']}"},   # cockpit/slot bearer
        "jwt": {"Authorization": f"Bearer {d['token']}"},     # kassa/forums JWT
    }


def _read(path):
    return path.read_text() if path.exists() else None


class World:
    """Seeded entities for one test. All state lives under state.data_path()."""

    def __init__(self, client, admin_client):
        # Guard: this suite must only ever touch the isolated temp data dir.
        assert "civitae_root" in str(state.data_path("x")), "not an isolated data dir"
        self.client = client
        self.admin = admin_client
        self.a = _mint(client)
        self.b = _mint(client)
        uid = uuid.uuid4().hex[:8]
        now = "2026-01-01T00:00:00+00:00"

        # kassa: post, active stake by A, open thread owned by A, one message
        self.post_id = f"K-p3-{uid}"
        state.kassa.insert_post({
            "id": self.post_id, "tab": "ISO", "title": "fixture post", "body": "b",
            "from_name": "Poster", "from_email": "poster@example.invalid",
            "created_at": now, "updated_at": now,
        })
        self.post2_id = f"K-p3b-{uid}"   # un-staked post for the success path
        state.kassa.insert_post({
            "id": self.post2_id, "tab": "ISO", "title": "fixture post 2", "body": "b",
            "from_name": "Poster", "from_email": "poster@example.invalid",
            "created_at": now, "updated_at": now,
        })
        self.stake_id = f"stk-p3-{uid}"
        state.kassa.insert_stake({
            "stake_id": self.stake_id, "post_id": self.post_id,
            "agent_id": self.a["id"], "agent_name": self.a["name"],
            "status": "active", "created_at": now,
        })
        self.thread_id = f"thr-p3-{uid}"
        state.kassa.insert_thread({
            "thread_id": self.thread_id, "post_id": self.post_id, "post_tab": "ISO",
            "post_title": "fixture post", "agent_id": self.a["id"],
            "agent_name": self.a["name"], "poster_name": "Poster",
            "poster_email": "poster@example.invalid", "magic_token": "hash-not-real",
            "status": "open", "message_count": 0, "created_at": now, "updated_at": now,
        })
        self.thread2_id = f"thr-p3b-{uid}"   # second open thread for the close success path
        state.kassa.insert_thread({
            "thread_id": self.thread2_id, "post_id": self.post_id, "post_tab": "ISO",
            "post_title": "fixture post", "agent_id": self.a["id"],
            "agent_name": self.a["name"], "poster_name": "Poster",
            "poster_email": "poster@example.invalid", "magic_token": "hash-not-real",
            "status": "open", "message_count": 0, "created_at": now, "updated_at": now,
        })

        # missions/slots via the real admin routes (writes to the tmp data dir)
        r = admin_client.post("/api/missions", json={"label": f"fx-{uid}", "objective": "o"})
        assert r.status_code == 200, r.text
        d = r.json()
        self.mission_id = (d.get("mission") or d)["id"]
        r = admin_client.post("/api/slots/create", json={
            "mission_id": self.mission_id, "positions": [{"row": 0, "col": 0}, {"row": 0, "col": 1}],
        })
        assert r.status_code == 200, r.text
        self.open_slot, self.filled_slot_src = [s["id"] for s in r.json()["slots"]]
        r = client.post("/api/slots/fill", json={
            "slot_id": self.filled_slot_src, "agent_id": self.a["id"]}, headers=self.a["key"])
        assert r.status_code == 200, r.text
        self.filled_slot = self.filled_slot_src   # occupied by A

        # governance: meeting with A and B attending, one pending motion
        r = admin_client.post("/api/governance/meeting", json={
            "caller": self.a["id"], "subject": "fixture", "quorum": 2})
        assert r.status_code == 200, r.text
        self.meeting_id = r.json()["id"] if "id" in r.json() else r.json()["meeting"]["id"]
        r = admin_client.post(f"/api/governance/meeting/{self.meeting_id}/join",
                              json={"agent_id": self.b["id"]})
        assert r.status_code == 200, r.text
        r = admin_client.post(f"/api/governance/meeting/{self.meeting_id}/motion", json={
            "proposer": self.a["id"], "motion": "fixture motion"})
        assert r.status_code == 200, r.text
        body = r.json()
        self.motion_id = body["id"] if "id" in body else body["motion"]["id"]

    def snapshot(self):
        """Everything the 13 endpoints could mutate, as comparable plain data."""
        led = state.economy.treasury._ledger
        forum_n = state.forums._conn.execute("SELECT COUNT(*) FROM forum_threads").fetchone()[0]
        return {
            "slots": _read(state.data_path("slots.json")),
            "missions": _read(state.data_path("missions.json")),
            "meetings": _read(state.data_path("meetings.json")),
            "posts": json.dumps(state.kassa.load_posts(), sort_keys=True, default=str),
            "stakes": json.dumps(state.kassa.load_stakes(), sort_keys=True, default=str),
            "thread": json.dumps(state.kassa.get_thread(self.thread_id), sort_keys=True, default=str),
            "thread2": json.dumps(state.kassa.get_thread(self.thread2_id), sort_keys=True, default=str),
            "messages": json.dumps(state.kassa.load_thread_messages(self.thread_id), default=str),
            "forum_threads": forum_n,
            "treasury": json.dumps(led, sort_keys=True, default=str),
        }

    def cleanup(self):
        try:
            state.kassa._conn.execute("DELETE FROM posts WHERE id IN (?, ?)", (self.post_id, self.post2_id))
            state.kassa._conn.commit()
        except Exception:
            pass


@pytest.fixture
def world(client, admin_client):
    w = World(client, admin_client)
    yield w
    w.cleanup()


# ── endpoint table: (label, method, path(w), body(w), wrong_principal_hdr(w) | None) ─
# Wrong principal = registered agent B acting on A's entity / identity.

def _b_key(w): return w.b["key"]
def _b_jwt(w): return w.b["jwt"]

CASES = [
    ("stake", "POST", lambda w: f"/api/kassa/posts/{w.post2_id}/stake", lambda w: {}, None),
    ("withdraw_stake", "DELETE", lambda w: f"/api/kassa/stakes/{w.stake_id}", lambda w: None, _b_jwt),
    ("kassa_post", "POST", lambda w: "/api/kassa/posts",
     lambda w: {"tab": "ISO", "title": "t", "body": "b", "from_name": "n", "from_email": "e@x.invalid"}, None),
    ("thread_message", "POST", lambda w: f"/api/kassa/threads/{w.thread_id}/messages",
     lambda w: {"text": "hello"}, _b_jwt),
    ("thread_close", "POST", lambda w: f"/api/kassa/threads/{w.thread2_id}/close", lambda w: {}, _b_jwt),
    ("slot_fill", "POST", lambda w: "/api/slots/fill",
     lambda w: {"slot_id": w.open_slot, "agent_id": w.b["id"]}, None),
    ("slot_leave", "POST", lambda w: "/api/slots/leave",
     lambda w: {"slot_id": w.filled_slot, "agent_id": w.a["id"]}, _b_key),
    ("slot_create", "POST", lambda w: "/api/slots/create",
     lambda w: {"mission_id": w.mission_id, "positions": [{"row": 5, "col": 5}]}, None),
    ("slot_bounty", "POST", lambda w: "/api/slots/bounty",
     lambda w: {"agent_id": w.a["id"], "label": "fx"}, _b_key),
    ("mission_create", "POST", lambda w: "/api/missions", lambda w: {"label": "evil", "objective": "x"}, None),
    ("mission_end", "POST", lambda w: f"/api/missions/{w.mission_id}/end", lambda w: {}, None),
    ("mission_update", "POST", lambda w: f"/api/missions/{w.mission_id}/update",
     lambda w: {"status": "hijacked"}, None),
    ("vote", "POST", lambda w: f"/api/governance/meeting/{w.meeting_id}/vote",
     lambda w: {"voter": w.a["id"], "motion_id": w.motion_id, "vote": "nay"}, _b_key),
    ("withdraw", "POST", lambda w: "/api/economy/withdraw",
     lambda w: {"agent_id": w.a["id"], "amount": 1, "chain": "base", "to": "0x0"}, None),
    ("forum_thread", "POST", lambda w: "/api/forums/threads",
     lambda w: {"title": "hijack title", "body": "b"}, None),
]
IDS = [c[0] for c in CASES]


def _fire(client, case, w, headers):
    _, method, path, body, _ = case
    return client.request(method, path(w), json=body(w), headers=headers).status_code


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_denied_before_mutation_on_existing_entity(client, world, case):
    """Anonymous / forged / shell-origin (+forged): 401|403 and store unchanged."""
    before = world.snapshot()
    for hdrs in ({}, SHELL_HDRS, FORGED_HDRS, {**SHELL_HDRS, **FORGED_HDRS}):
        status = _fire(client, case, world, hdrs)
        assert status in DENIED, f"{case[0]} {sorted(hdrs)} -> {status}"
    assert world.snapshot() == before, f"{case[0]}: store mutated by a denied call"


@pytest.mark.parametrize("case", [c for c in CASES if c[4] is not None],
                         ids=[c[0] for c in CASES if c[4] is not None])
def test_wrong_principal_denied_before_mutation(client, world, case):
    """A different registered agent (and shell origin on top) cannot act on A's entity."""
    before = world.snapshot()
    hdrs = case[4](world)
    for h in (hdrs, {**SHELL_HDRS, **hdrs}):
        status = _fire(client, case, world, h)
        assert status in DENIED, f"{case[0]} wrong principal -> {status}"
    assert world.snapshot() == before


def test_shell_origin_does_not_alter_a_legitimate_success(client, world):
    """Same authorized request succeeds identically with and without shell headers
    (the shell neither adds nor removes authority)."""
    with_shell = client.post(f"/api/kassa/posts/{world.post_id}/upvote", json={}, headers=SHELL_HDRS)
    without = client.post(f"/api/kassa/posts/{world.post_id}/upvote", json={})
    assert with_shell.status_code == without.status_code == 200
    assert without.json()["upvotes"] == with_shell.json()["upvotes"] + 1


# ── Public-by-design: upvote has no auth. It is NOT an authority endpoint. ──

def test_upvote_is_public_by_design_and_shell_neutral(client, world):
    """kassa.py upvote performs no identity check (rate-limited only). Anonymous,
    forged and shell-origin calls are all accepted equally: nothing to escalate,
    and the shell neither helps nor hinders. Recorded so no one reads the old
    404-only probe as 'upvote is auth-protected'."""
    codes = [client.post(f"/api/kassa/posts/{world.post_id}/upvote", json={}, headers=h).status_code
             for h in ({}, SHELL_HDRS, FORGED_HDRS)]
    assert codes == [200, 200, 200]


# ── Authorized principals succeed (proves the denials above are not blanket) ─

def test_owner_jwt_can_stake_message_close_withdraw_and_post(client, world):
    a = world.a["jwt"]
    r = client.post(f"/api/kassa/posts/{world.post2_id}/stake", json={}, headers=a)
    assert r.status_code == 200, r.text
    r = client.post(f"/api/kassa/threads/{world.thread_id}/messages", json={"text": "hi"}, headers=a)
    assert r.status_code == 200, r.text
    assert [m["text"] for m in state.kassa.load_thread_messages(world.thread_id)] == ["hi"]
    r = client.post(f"/api/kassa/threads/{world.thread2_id}/close", json={}, headers=a)
    assert r.status_code == 200, r.text
    assert state.kassa.get_thread(world.thread2_id)["status"] == "closed"
    r = client.delete(f"/api/kassa/stakes/{world.stake_id}", headers=a)
    assert r.status_code == 200, r.text
    ip = {"x-forwarded-for": f"10.8.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"}
    r = client.post("/api/kassa/posts", headers={**a, **ip}, json={
        "tab": "ISO", "title": "owner post", "body": "b", "from_name": "n", "from_email": "e@x.invalid"})
    assert r.status_code == 200, r.text
    r = client.post("/api/forums/threads", headers=a, json={"title": "owner thread", "body": "b"})
    assert r.status_code == 200, r.text


def test_owner_key_can_leave_vote_and_fill_slot(client, world):
    a = world.a["key"]
    r = client.post("/api/slots/leave", json={"slot_id": world.filled_slot, "agent_id": world.a["id"]}, headers=a)
    assert r.status_code == 200, r.text
    r = client.post("/api/slots/fill", json={"slot_id": world.open_slot, "agent_id": world.a["id"]}, headers=a)
    assert r.status_code == 200, r.text
    r = client.post(f"/api/governance/meeting/{world.meeting_id}/vote", headers=a,
                    json={"voter": world.a["id"], "motion_id": world.motion_id, "vote": "yea"})
    assert r.status_code == 200, r.text
    r = client.post("/api/slots/bounty", headers=a, json={"agent_id": world.a["id"], "label": "fx"})
    assert r.status_code == 200, r.text


def test_admin_can_run_operator_verbs(admin_client, world):
    r = admin_client.post(f"/api/missions/{world.mission_id}/update", json={"posture": "SCOUT"})
    assert r.status_code == 200, r.text
    r = admin_client.post(f"/api/missions/{world.mission_id}/end", json={})
    assert r.status_code == 200, r.text
    # /api/economy/withdraw intentionally NOT exercised with credentials: the
    # admin path reaches the chain router (money movement). Denial-only.


# ── Falsifier canaries: the harness must go RED when a guard is removed ─────
# These patch a guard away in-process (test-local, never committed to app/) and
# assert the same probe the denial tests use now observes acceptance/mutation.

def _case(label):
    return next(c for c in CASES if c[0] == label)


def _breached(client, world, label):
    before = world.snapshot()
    status = _fire(client, _case(label), world, {})
    return status not in DENIED or world.snapshot() != before


def test_canary_claim_guard_removal_is_detected(client, world, monkeypatch):
    import app.routes.missions as missions
    assert not _breached(client, world, "slot_fill")          # guard intact: denied
    monkeypatch.setattr(missions, "require_agent_claim", lambda *a, **kw: None)
    assert _breached(client, world, "slot_fill")              # guard gone: detected


def test_canary_middleware_removal_is_detected(client, world, monkeypatch):
    import app.server as server
    assert not _breached(client, world, "mission_end")
    monkeypatch.setattr(server, "admin_key_matches", lambda *a, **kw: True)
    assert _breached(client, world, "mission_end")
