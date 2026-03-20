#!/usr/bin/env python3
"""Grok Agent — xAI Grok governed by COMMAND.

Usage:
  export XAI_API_KEY="xai-..."
  python3 agents/grok_agent.py
"""

import os
import httpx
from base_agent import run_agent_loop

API_KEY = os.environ.get("XAI_API_KEY", "")
MODEL = os.environ.get("GROK_MODEL", "grok-3")


def call_grok(system_msg: str, messages: list[dict]) -> str:
    if not API_KEY:
        return "[GROK ERROR] XAI_API_KEY not set"

    # xAI uses OpenAI-compatible format
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system_msg}] + messages,
    }
    resp = httpx.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


if __name__ == "__main__":
    run_agent_loop("grok", call_grok)
