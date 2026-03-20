#!/usr/bin/env python3
"""Claude Agent — Anthropic Claude API governed by COMMAND.

Usage:
  export ANTHROPIC_API_KEY="sk-ant-..."
  python3 agents/claude_agent.py

Note: This is the Claude API agent (separate from Claude Code MCP).
Use this when you want Claude as a system in the COMMAND console
responding through the API rather than through MCP.
"""

import os
import httpx
from base_agent import run_agent_loop

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")


def call_claude(system_msg: str, messages: list[dict]) -> str:
    if not API_KEY:
        return "[CLAUDE ERROR] ANTHROPIC_API_KEY not set"

    # Anthropic uses separate system field
    anthropic_messages = []
    for m in messages:
        anthropic_messages.append({
            "role": m["role"],
            "content": m["content"],
        })

    # Ensure messages alternate user/assistant
    if not anthropic_messages or anthropic_messages[0]["role"] != "user":
        anthropic_messages.insert(0, {"role": "user", "content": "(awaiting input)"})

    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": 2048,
            "system": system_msg,
            "messages": anthropic_messages,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


if __name__ == "__main__":
    run_agent_loop("claude-api", call_claude)
