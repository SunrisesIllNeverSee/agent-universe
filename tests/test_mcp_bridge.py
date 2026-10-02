from __future__ import annotations

import asyncio
import copy
import uuid


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

