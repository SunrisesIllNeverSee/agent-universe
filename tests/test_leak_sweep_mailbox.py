"""Leak sweep 2026-10-16: agent directory/profile/matcher responses show only the public
@signomy.xyz mailbox label. Before: whatever the registry held in `email` was returned, so a
record carrying a real external address published it to anonymous callers."""
import uuid

from app.deps import state
from app.public_projection import public_mailbox


def _legacy_agent():
    tag = uuid.uuid4().hex[:8]
    entry = {"agent_id": f"agent-mb{tag}", "name": f"mb-{tag}", "handle": f"mb-{tag}", "type": "agent",
             "status": "active", "email": f"owner-{tag}@example.com"}
    state.runtime.registry.append(entry)
    state.runtime.persist_registry()
    return entry


def test_directory_and_profile_never_show_external_email(client, admin_client):
    e = _legacy_agent()
    body = client.get("/api/agents").json()
    row = next(a for a in body["agents"] if a["agent_id"] == e["agent_id"])
    assert row["email"] == f"{e['agent_id']}@signomy.xyz"
    prof = client.get(f"/api/agents/{e['handle']}")
    assert prof.status_code == 200 and prof.json()["email"] == f"{e['agent_id']}@signomy.xyz"
    pid = admin_client.post("/api/kassa/posts", json={"tab": "bounties", "title": "mb", "body": "b",
                                                      "from_name": "P", "from_email": "p@example.invalid"}).json()["id"]
    assert e["email"] not in client.get(f"/api/match/{pid}?limit=200").text


def test_platform_mailbox_is_kept():
    assert public_mailbox({"agent_id": "agent-1", "email": "bot@signomy.xyz"}) == "bot@signomy.xyz"
    assert public_mailbox({"agent_id": "agent-1"}) == "agent-1@signomy.xyz"
