"""Operational hardening — cockpit message attribution and operator stars.

Agent Bearer keys reach /api/message* through the middleware. They may post a
message only as themselves (agent_id or registered name) and never in the
operator role; starring/unstarring writes the operator vault and loaded context
and is admin-key only. Star tags are validated before any write. Every denial
leaves the message store, starred.json, vault/starred, audit.jsonl and
seeds.jsonl untouched. Session tmp root only (see conftest).
"""
import json
import uuid

import pytest

from app.deps import state
from tests.conftest import signup_agent

ADMIN = {"X-Admin-Key": "test-admin-key-12345"}


def _agent(client):
    ip = f"10.9.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    d = signup_agent(client, name=f"om-{uuid.uuid4().hex[:6]}", ip=ip).json()
    return d, {"Authorization": f"Bearer {d['api_key']}"}


def _text(rel):
    p = state.root / rel
    return p.read_text() if p.exists() else ""


def _snap():
    vault = state.root / "vault" / "starred"
    docs = sorted(x.name for x in vault.iterdir()) if vault.exists() else []
    return (
        len(state.store.all()),
        _text("data/starred.json") or _text("starred.json"),
        tuple(docs),
        tuple(state.runtime.vault.manifest.get("starred", [])),
        len(_text("data/audit.jsonl").splitlines()),
        len(_text("data/seeds.jsonl").splitlines()),
    )


def _admin_msg(client):
    r = client.post("/api/messages", json={"sender": "operator", "text": "hello"}, headers=ADMIN)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_agent_posts_as_self_by_id_and_role_forced_to_agent(client):
    d, h = _agent(client)
    r = client.post("/api/messages", json={"sender": d["agent_id"], "text": "hi", "role_context": "operator"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["sender"] == d["agent_id"]
    stored = next(m for m in state.store.all() if m.id == r.json()["id"])
    assert stored.role_context == "agent"


@pytest.mark.parametrize("sender", ["operator", "SYSTEM", "someone-else"])
def test_agent_cannot_post_as_other_sender(client, sender):
    _, h = _agent(client)
    s = _snap()
    r = client.post("/api/messages", json={"sender": sender, "text": "spoof"}, headers=h)
    assert r.status_code == 403
    assert _snap() == s


def test_agent_cannot_post_as_another_agent(client):
    victim, _ = _agent(client)
    _, h = _agent(client)
    s = _snap()
    for sender in (victim["agent_id"], victim.get("name") or victim["agent_id"]):
        assert client.post("/api/messages", json={"sender": sender, "text": "x"}, headers=h).status_code == 403
    assert _snap() == s


def test_admin_may_post_as_operator(client):
    assert _admin_msg(client)


def test_anonymous_and_garbage_admin_denied(client):
    _, h = _agent(client)
    s = _snap()
    assert client.post("/api/messages", json={"sender": "operator", "text": "x"}).status_code in (401, 403)
    assert client.post("/api/messages", json={"sender": "operator", "text": "x"},
                       headers={**h, "X-Admin-Key": "garbage"}).status_code == 403
    assert _snap() == s


@pytest.mark.parametrize("path,body", [("/api/messages/star", {"tag": "gold"}), ("/api/messages/unstar", {})])
def test_agent_cannot_star_or_unstar(client, path, body):
    mid = _admin_msg(client)
    assert client.post("/api/messages/star", json={"id": mid}, headers=ADMIN).status_code == 200
    _, h = _agent(client)
    s = _snap()
    r = client.post(path, json={"id": mid, **body}, headers=h)
    assert r.status_code == 403
    assert _snap() == s


@pytest.mark.parametrize("tag", ["../x", "a/b", "", "x" * 33, "gold tag"])
def test_bad_star_tag_rejected_before_any_write(client, tag):
    mid = _admin_msg(client)
    s = _snap()
    r = client.post("/api/messages/star", json={"id": mid, "tag": tag}, headers=ADMIN)
    assert r.status_code == 400
    assert _snap() == s


def test_admin_star_and_unstar_work(client):
    mid = _admin_msg(client)
    r = client.post("/api/messages/star", json={"id": mid, "tag": "gold"}, headers=ADMIN)
    assert r.status_code == 200 and r.json()["starred"] is True
    r = client.post("/api/messages/unstar", json={"id": mid}, headers=ADMIN)
    assert r.status_code == 200
    assert all(x.get("id") != mid for x in client.get("/api/messages/starred").json()["starred"])


# ── /ws writes (WebSockets bypass the HTTP admin_key_guard) ──────────────────

def _ws_send(client, payload, headers=None):
    with client.websocket_connect("/ws", headers=headers or {}) as ws:
        ws.receive_json()  # state snapshot
        ws.send_json(payload)
        ws.send_json({"action": "ping"})
        replies = []
        while True:
            m = ws.receive_json()
            replies.append(m)
            if m.get("type") == "pong":
                return replies


def _presence():
    return json.dumps(state.runtime.presence, sort_keys=True, default=str)


@pytest.mark.parametrize("sender", ["operator", "victim-agent"])
def test_ws_chat_send_anonymous_rejected(client, sender):
    s = _snap()
    replies = _ws_send(client, {"action": "chat_send", "payload": {"sender": sender, "text": "x"}})
    assert any(r.get("type") == "error" for r in replies)
    assert _snap() == s


def test_ws_chat_send_agent_as_other_rejected_as_self_ok(client):
    victim, _ = _agent(client)
    d, h = _agent(client)
    s = _snap()
    _ws_send(client, {"action": "chat_send", "payload": {"sender": victim["agent_id"], "text": "x"}}, h)
    assert _snap() == s
    _ws_send(client, {"action": "chat_send", "payload": {"sender": d["agent_id"], "text": "me", "role_context": "operator"}}, h)
    mine = [m for m in state.store.all() if m.sender == d["agent_id"]]
    assert mine and mine[-1].role_context == "agent"


def test_ws_agent_join_spoof_rejected_admin_ok(client):
    victim, _ = _agent(client)
    _, h = _agent(client)
    p, s = _presence(), _snap()
    for hdr in ({}, h):
        _ws_send(client, {"action": "agent_join", "payload": {"name": victim["agent_id"]}}, hdr)
    assert _presence() == p and _snap() == s
    _ws_send(client, {"action": "chat_send", "payload": {"sender": "operator", "text": "op"}}, ADMIN)
    assert any(m.sender == "operator" and m.text == "op" for m in state.store.all())


def test_ws_reads_stay_public(client):
    replies = _ws_send(client, {"action": "ping"})
    assert replies[-1]["type"] == "pong"
