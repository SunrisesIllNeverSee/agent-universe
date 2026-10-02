from __future__ import annotations

import asyncio
import copy
import json
import uuid
from pathlib import Path


def test_mcp_registration_ignores_legacy_registered_identity_cap(app):
    """Persistent identities must not be treated as Velvet Rope occupancy by MCP."""
    from app.deps import state

    runtime = state.runtime
    original_registry = copy.deepcopy(runtime.registry)
    original_provision = copy.deepcopy(runtime.provision)

    synthetic = [
        {
            "agent_id": f"historical-{i}",
            "handle": f"historical-{i}",
            "name": f"Historical Agent {i}",
            "type": "agent",
            "status": "active",
        }
        for i in range(51)
    ]
    handle = f"mcp-capacity-{uuid.uuid4().hex[:8]}"
    name = f"MCP Capacity {uuid.uuid4().hex[:8]}"

    try:
        runtime.registry = synthetic
        runtime.provision = {**original_provision, "max_agents": 50}
        runtime.persist_registry()

        mcp = state.mcp_bridge.build_fastmcp()
        asyncio.run(
            mcp.call_tool(
                "agent.register",
                {
                    "handle": handle,
                    "name": name,
                    "capabilities": ["testing"],
                    "model": "custom",
                },
            )
        )

        runtime.reload_registry()
        created = next((r for r in runtime.registry if r.get("handle") == handle), None)
        assert created is not None
        assert created["name"] == name
        assert created["type"] == "agent"
        assert len([r for r in runtime.registry if r.get("type") == "agent"]) == 52
    finally:
        runtime.registry = original_registry
        runtime.provision = original_provision
        runtime.persist_registry()


def test_mcp_exposes_expected_registration_tool(app):
    """The production MCP surface must continue advertising agent.register."""
    from app.deps import state

    mcp = state.mcp_bridge.build_fastmcp()
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}

    assert "agent.register" in names
    assert "agent.status" in names
    assert "agent.heartbeat" in names
    assert "agent.inbox" in names
    assert "agent.inbox.read" in names
    assert len(names) == 30

def test_mcp_api_key_lookup_does_not_reload_registry(client, monkeypatch):
    """ST-007: authenticated MCP lookup stays in-memory in single-worker production."""
    from app.deps import state
    from tests.conftest import signup_agent

    response = signup_agent(
        client,
        name=f"MCP Lookup {uuid.uuid4().hex[:8]}",
        ip=f"10.44.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}",
    )
    assert response.status_code == 200
    api_key = response.json()["api_key"]

    reload_calls = 0
    original_reload = state.runtime.reload_registry

    def counted_reload():
        nonlocal reload_calls
        reload_calls += 1
        return original_reload()

    monkeypatch.setattr(state.runtime, "reload_registry", counted_reload)

    mcp = state.mcp_bridge.build_fastmcp()
    result = asyncio.run(
        mcp.call_tool(
            "agent.inbox",
            {"api_key": api_key, "limit": 1},
        )
    )

    assert result is not None
    assert reload_calls == 0

def test_mcp_market_browse_projects_private_contact_and_clamps_limit(app, monkeypatch):
    """ST-011: public MCP discovery strips routing email and has a hard result bound."""
    from app.deps import state

    synthetic = [
        {
            "id": f"K-{i:05d}",
            "tab": "services",
            "title": f"Post {i}",
            "body": "Public body",
            "status": "open",
            "from_name": f"Poster {i}",
            "from_email": f"private-{i}@example.com",
        }
        for i in range(75)
    ]

    def fake_load_posts(tab="", status="", *, search="", limit=None):
        rows = synthetic
        if search:
            q = search.lower()
            rows = [p for p in rows if q in p["title"].lower() or q in p["body"].lower()]
        return rows[:limit] if limit is not None else rows

    monkeypatch.setattr(state.kassa, "load_posts", fake_load_posts)

    mcp = state.mcp_bridge.build_fastmcp()
    result = asyncio.run(
        mcp.call_tool(
            "market.browse",
            {"category": "services", "status": "open", "limit": 10000},
        )
    )

    data = result.data
    assert data["count"] == 50
    assert len(data["posts"]) == 50
    assert all("from_email" not in post for post in data["posts"])
    assert all(post["collaborator_type"] == "bi" for post in data["posts"])


def test_mcp_leaderboard_clamps_limit(app):
    """ST-011: caller-controlled discovery limit cannot request an unbounded registry."""
    from app.deps import state

    mcp = state.mcp_bridge.build_fastmcp()
    result = asyncio.run(
        mcp.call_tool(
            "agent.leaderboard",
            {"limit": 10000},
        )
    )

    assert result.data["count"] <= 100

def test_mcp_runtime_matches_public_server_card(app):
    """ST-016: complete hosted runtime/card/resource contract must stay synchronized."""
    from app.deps import state

    mcp = state.mcp_bridge.build_fastmcp()
    runtime_tools = asyncio.run(mcp.list_tools())
    runtime_names = {tool.name for tool in runtime_tools}

    root = Path(__file__).resolve().parents[1]
    card = json.loads(
        (root / "frontend" / ".well-known" / "mcp-server-card.json").read_text(encoding="utf-8")
    )
    advertised_names = {tool["name"] for tool in card["capabilities"]["tools"]}

    assert runtime_names == advertised_names
    assert len(runtime_names) == 30
    assert card["url"] == "https://signomy.xyz/mcp"
    assert card["transport"] == "streamable-http"

    resources = asyncio.run(mcp.list_resources())
    assert len(resources) == 7

def test_chat_read_uses_and_persists_server_cursor(app):
    """ST-019: omitted client cursor resumes from the server-side persisted cursor."""
    from app.deps import state
    from app.models import MessageCreate

    name = f"cursor-{uuid.uuid4().hex[:8]}"
    channel = f"cursor-{uuid.uuid4().hex[:8]}"
    state.mcp_bridge.chat_join(name)
    saved = state.runtime.create_message(
        MessageCreate(sender="other", text="cursor probe", channel=channel)
    )

    first = state.mcp_bridge.chat_read(name, channel=channel)
    assert any(message["id"] == saved.id for message in first["messages"])

    second = state.mcp_bridge.chat_read(name, channel=channel)
    assert all(message["id"] != saved.id for message in second["messages"])
    assert state.runtime.get_cursor(name, channel) >= saved.id

    persisted = json.loads(state.runtime.cursors_path.read_text(encoding="utf-8"))
    assert persisted[name][channel] >= saved.id

