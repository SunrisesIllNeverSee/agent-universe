"""OPHARD-D route probes (characterization only; no app/ changes).

Surface: the cockpit-write routes that the admin_key_guard middleware admits
for a registered agent's Bearer key (_OPERATOR_WRITE_PREFIXES) but whose
handlers do not read request.state.agent_principal:

  POST /api/messages, /api/messages/star, /api/messages/unstar   (core.py)
  POST /api/governance/check                                      (core.py)
  POST /api/composer/compose                                      (composer.py)
  POST /api/boost/{post_id}, POST /api/sponsored                  (boost.py)
  POST /api/campaigns (owner binding already enforced - control)  (missions.py)

Each probe runs anonymous / valid agent / agent spoofing another identity /
admin. Synthetic agents only, session tmp root (see conftest), never real data.

Passing tests pin CURRENT behavior. Tests marked xfail(strict=True) assert the
DESIRED behavior for a hole someone else will fix; when the fix lands the
strict xfail turns into a failure that tells the fixer to delete the marker.
"""
import json
import uuid

import pytest

from app.deps import state
from tests.conftest import signup_agent

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


def _agent(client):
    ip = f"10.7.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"oh-{uuid.uuid4().hex[:6]}", ip=ip).json()
    return d["agent_id"], {"Authorization": f"Bearer {d['api_key']}"}, d


def _msgs():
    return len(state.store.all())


def _stars():
    p = state.data_path("starred.json")
    return json.loads(p.read_text()) if p.exists() else []


def _boosts():
    p = state.data_path("boosts.json")
    if not p.exists():
        for cand in state.data_path("").glob("*boost*"):
            p = cand
            break
    return json.loads(p.read_text()) if p.exists() else {"boosts": [], "sponsored": []}


def _post_id():
    pid = f"K-OH{uuid.uuid4().hex[:6]}"
    state.kassa.insert_post({
        "id": pid, "tab": "bounties", "title": "probe", "body": "probe",
        "tag": "", "status": "open", "urgency": "normal", "upvotes": 0,
        "reply_count": 0, "reward": "", "from_name": "probe", "from_email": "",
        "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-01T00:00:00+00:00",
    })
    return pid


# ── anonymous: every probed route is closed ───────────────────────────────

ANON_CASES = [
    ("/api/messages", {"sender": "x", "text": "t"}),
    ("/api/messages/star", {"id": 1}),
    ("/api/messages/unstar", {"id": 1}),
    ("/api/governance/check", {"action": "read"}),
    ("/api/composer/compose", {"text": "hire someone"}),
    ("/api/boost/K-00001", {"agent_id": "a"}),
    ("/api/sponsored", {"post_id": "K-00001", "handle": "h"}),
    ("/api/campaigns", {"name": "c"}),
]


@pytest.mark.parametrize("path,body", ANON_CASES)
def test_anonymous_write_rejected_403(client, path, body):
    r = client.post(path, json=body)
    assert r.status_code == 403, (path, r.status_code, r.text)
    assert r.json().get("error", r.json()).get("code", "admin_key_required") == "admin_key_required" \
        if isinstance(r.json().get("error"), dict) else True


@pytest.mark.parametrize("path,body", ANON_CASES)
def test_bogus_bearer_rejected_403(client, path, body):
    r = client.post(path, json=body, headers={"Authorization": "Bearer not-a-real-key"})
    assert r.status_code == 403, (path, r.status_code)


# ── POST /api/messages ────────────────────────────────────────────────────

def test_messages_agent_can_write_global_store(client):
    _, h, _ = _agent(client)
    before = _msgs()
    r = client.post("/api/messages", json={"sender": "me", "text": "hello"}, headers=h)
    assert r.status_code == 200, r.text
    assert _msgs() == before + 1  # shared operator console store mutated


@pytest.mark.xfail(strict=True, reason="OPHARD-D F1 MED: core.py:183 post_message trusts body.sender; "
                   "an agent can post as another agent/operator (attribution spoof). "
                   "Fix: bind sender to request.state.agent_principal or reject.")
def test_messages_sender_spoof_rejected(client):
    a, ha, _ = _agent(client)
    b, _, _ = _agent(client)
    r = client.post("/api/messages", json={"sender": b, "text": "forged"}, headers=ha)
    assert r.status_code in (400, 403, 404), r.text


def test_messages_admin_ok(client):
    r = client.post("/api/messages", json={"sender": "operator", "text": "x"}, headers=ADMIN)
    assert r.status_code == 200


# ── POST /api/messages/star + unstar ──────────────────────────────────────

def _seed_message(client):
    r = client.post("/api/messages", json={"sender": "operator", "text": "seed"}, headers=ADMIN)
    return r.json()["id"]


def test_star_agent_mutates_operator_state(client):
    _, h, _ = _agent(client)
    mid = _seed_message(client)
    tag = f"t{uuid.uuid4().hex[:4]}"
    r = client.post("/api/messages/star", json={"id": mid, "tag": tag}, headers=h)
    assert r.status_code == 200, r.text
    assert any(s["id"] == mid for s in _stars())
    # also writes a vault doc and auto-loads it into global active context
    assert (state.root / "vault" / "starred" / f"star-{mid}-{tag}.md").exists()


@pytest.mark.xfail(strict=True, reason="OPHARD-D F2 MED: core.py:464 star_message lets any agent key write the "
                   "shared operator star list, vault/starred/*.md and global loaded context; "
                   "tag is interpolated into a filename (see F3). Should be admin-only.")
def test_star_agent_rejected(client):
    _, h, _ = _agent(client)
    mid = _seed_message(client)
    r = client.post("/api/messages/star", json={"id": mid, "tag": "gold"}, headers=h)
    assert r.status_code == 403


def test_star_tag_with_separators_does_not_escape_vault(client):
    # Containment holds only by accident: the parent 'star-<id>-..' dir does not
    # exist, so the write fails instead of traversing (see next test).
    mid = _seed_message(client)
    marker = f"zz{uuid.uuid4().hex[:6]}"
    client.post("/api/messages/star", json={"id": mid, "tag": f"../../{marker}"}, headers=ADMIN)
    assert list(state.root.rglob(f"*{marker}*.md")) == []


@pytest.mark.xfail(strict=True, reason="OPHARD-D F3 LOW/MED: core.py:464 star_message interpolates an unvalidated "
                   "tag into the vault filename. A tag with '/' yields an unhandled 500 (FileNotFoundError) "
                   "AFTER the star was already persisted to starred.json (partial write, inconsistent state). "
                   "Fix: validate tag (^[A-Za-z0-9_-]{1,32}$) before any write.")
def test_star_bad_tag_rejected_without_partial_state(client):
    mid = _seed_message(client)
    before = len(_stars())
    r = client.post("/api/messages/star", json={"id": mid, "tag": "a/b"}, headers=ADMIN)
    assert r.status_code in (400, 422) and len(_stars()) == before


def test_unstar_agent_can_delete_operator_star(client):
    _, h, _ = _agent(client)
    mid = _seed_message(client)
    client.post("/api/messages/star", json={"id": mid, "tag": "gold"}, headers=ADMIN)
    assert any(s["id"] == mid for s in _stars())
    r = client.post("/api/messages/unstar", json={"id": mid}, headers=h)
    assert r.status_code == 200
    assert not any(s["id"] == mid for s in _stars())  # agent deleted operator state


@pytest.mark.xfail(strict=True, reason="OPHARD-D F4 MED: core.py:544 unstar_message lets any agent key "
                   "delete operator stars. Should be admin-only.")
def test_unstar_agent_rejected(client):
    _, h, _ = _agent(client)
    r = client.post("/api/messages/unstar", json={"id": 1}, headers=h)
    assert r.status_code == 403


# ── POST /api/governance/check ────────────────────────────────────────────

def test_governance_check_agent_readonly_no_storage(client):
    _, h, _ = _agent(client)
    before_msgs, before_stars = _msgs(), len(_stars())
    r = client.post("/api/governance/check", json={"action": "read"}, headers=h)
    assert r.status_code == 200
    assert "permitted" in r.json()
    assert (_msgs(), len(_stars())) == (before_msgs, before_stars)  # pure compute (LOW)


def test_governance_check_evaluates_against_global_operator_posture(client):
    # No agent identity is consulted: agent_tier defaults to UNGOVERNED and the
    # verdict reflects the operator's global posture (LOW; informational only).
    _, h, _ = _agent(client)
    r = client.post("/api/governance/check", json={"action": "anything"}, headers=h)
    assert r.status_code == 200


# ── POST /api/composer/compose ────────────────────────────────────────────

def test_composer_agent_pure_compute(client):
    _, h, _ = _agent(client)
    r = client.post("/api/composer/compose", json={"text": "I want to hire a dev for $500."}, headers=h)
    assert r.status_code == 200
    assert r.json()["composed"]["tab"] == "hiring"  # returns structure only; no post is created (LOW)


def test_composer_requires_text_or_template(client):
    _, h, _ = _agent(client)
    assert client.post("/api/composer/compose", json={}, headers=h).status_code == 400


# ── POST /api/boost/{post_id} ─────────────────────────────────────────────

def test_boost_agent_allowed_and_persisted(client):
    a, h, _ = _agent(client)
    pid = _post_id()
    r = client.post(f"/api/boost/{pid}", json={"agent_id": a, "duration_hours": 1}, headers=h)
    assert r.status_code == 200, r.text
    assert any(b["post_id"] == pid and b["boosted_by"] == a for b in _boosts().get("boosts", []))


@pytest.mark.xfail(strict=True, reason="OPHARD-D F5 MED: boost.py:63 boost_post trusts body.agent_id for "
                   "boosted_by + seed creator; attribution spoof, and any agent may boost any post "
                   "(no poster-ownership check). Owner: lane B.")
def test_boost_agent_id_spoof_rejected(client):
    a, h, _ = _agent(client)
    b, _, _ = _agent(client)
    pid = _post_id()
    r = client.post(f"/api/boost/{pid}", json={"agent_id": b}, headers=h)
    assert r.status_code in (400, 403, 404), r.text


def test_boost_unknown_post_404(client):
    a, h, _ = _agent(client)
    assert client.post("/api/boost/K-NOPE", json={"agent_id": a}, headers=h).status_code == 404


# ── POST /api/sponsored ───────────────────────────────────────────────────

def test_sponsored_agent_allowed_and_persisted(client):
    a, h, _ = _agent(client)
    handle = f"h{uuid.uuid4().hex[:5]}"
    r = client.post("/api/sponsored", json={"post_id": "K-ANY", "handle": handle, "agent_id": a}, headers=h)
    assert r.status_code == 200, r.text
    assert any(s["handle"] == handle for s in _boosts().get("sponsored", []))


@pytest.mark.xfail(strict=True, reason="OPHARD-D F6 MED/HIGH(if billing goes live): boost.py:138 create_sponsored "
                   "does not verify post_id exists, does not verify agent_id==principal, accepts any "
                   "handle/label (public Featured-section content injection) and any duration_hours "
                   "(no 1-168 cap unlike boost). Owner: lane B.")
def test_sponsored_unknown_post_rejected(client):
    a, h, _ = _agent(client)
    r = client.post("/api/sponsored", json={"post_id": "K-DOES-NOT-EXIST", "handle": "x", "agent_id": a}, headers=h)
    assert r.status_code in (400, 404)


@pytest.mark.xfail(strict=True, reason="OPHARD-D F6b: boost.py:138 duration_hours unbounded for sponsored "
                   "(boost caps at 168).")
def test_sponsored_duration_capped(client):
    a, h, _ = _agent(client)
    r = client.post("/api/sponsored", json={"post_id": _post_id(), "handle": "x", "agent_id": a,
                                            "duration_hours": 10_000_000}, headers=h)
    assert r.status_code in (400, 422)


# ── POST /api/campaigns (control: owner derived server-side) ──────────────

def test_campaign_owner_bound_to_principal_not_body(client):
    a, h, _ = _agent(client)
    b, _, _ = _agent(client)
    r = client.post("/api/campaigns", json={"name": "c", "owner_agent_id": b}, headers=h)
    assert r.status_code == 200
    assert r.json().get("owner_agent_id") == a  # body-supplied owner ignored (good)


def test_campaign_admin_ok(client):
    assert client.post("/api/campaigns", json={"name": "c"}, headers=ADMIN).status_code == 200
