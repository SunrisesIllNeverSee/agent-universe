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
    assert len(names) == 27
