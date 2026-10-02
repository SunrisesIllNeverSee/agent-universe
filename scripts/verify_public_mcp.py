#!/usr/bin/env python3
"""Verify the live SIGNOMY MCP contract through the public custom domain.

Run after a production deployment:
    python scripts/verify_public_mcp.py

This intentionally performs no state-changing calls.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.error
import urllib.request

from fastmcp import Client


EXPECTED_TOOL_COUNT = 30
CRITICAL_TOOLS = {
    "agent.register",
    "agent.status",
    "agent.heartbeat",
    "agent.inbox",
    "market.browse",
    "agent.leaderboard",
    "platform.health",
}


def fetch_json(url: str, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "signomy-release-verifier/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} returned HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


async def verify_mcp(endpoint: str, timeout: float) -> set[str]:
    client = Client(endpoint)
    async with client:
        tools = await asyncio.wait_for(client.list_tools(), timeout=timeout)
    return {tool.name for tool in tools}


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="https://signomy.xyz")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    base = args.base.rstrip("/")
    endpoint = f"{base}/mcp"

    try:
        health = fetch_json(f"{base}/health", args.timeout)
        if health.get("ok") is not True:
            raise RuntimeError(f"health not ok: {health!r}")
        print(f"PASS health version={health.get('version', 'unknown')}")

        card = fetch_json(f"{base}/.well-known/mcp-server-card.json", args.timeout)
        if card.get("url") != endpoint:
            raise RuntimeError(
                f"server card endpoint mismatch: {card.get('url')!r} != {endpoint!r}"
            )
        if card.get("transport") != "streamable-http":
            raise RuntimeError(f"unexpected transport: {card.get('transport')!r}")
        advertised = {
            tool["name"]
            for tool in card.get("capabilities", {}).get("tools", [])
            if isinstance(tool, dict) and tool.get("name")
        }
        if len(advertised) != EXPECTED_TOOL_COUNT:
            raise RuntimeError(
                f"server card advertises {len(advertised)} tools; expected {EXPECTED_TOOL_COUNT}"
            )
        print(f"PASS server-card version={card.get('version')} tools={len(advertised)}")

        runtime = await verify_mcp(endpoint, args.timeout)
        if len(runtime) != EXPECTED_TOOL_COUNT:
            raise RuntimeError(
                f"runtime exposes {len(runtime)} tools; expected {EXPECTED_TOOL_COUNT}"
            )
        missing = CRITICAL_TOOLS - runtime
        if missing:
            raise RuntimeError(f"runtime missing critical tools: {sorted(missing)}")
        if runtime != advertised:
            raise RuntimeError(
                "runtime/server-card drift: "
                f"missing_from_runtime={sorted(advertised - runtime)} "
                f"missing_from_card={sorted(runtime - advertised)}"
            )
        print(f"PASS public MCP transport tools={len(runtime)}")
        print("PUBLIC CONTRACT HEALTHY")
        return 0

    except (RuntimeError, OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # FastMCP transport/protocol failures
        print(f"FAIL MCP protocol error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
