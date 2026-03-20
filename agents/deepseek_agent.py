#!/usr/bin/env python3
"""DeepSeek Agent — DeepSeek governed by COMMAND.

Usage:
  export DEEPSEEK_API_KEY="sk-..."
  python3 agents/deepseek_agent.py
"""

import os
import httpx
from base_agent import run_agent_loop

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")


def call_deepseek(system_msg: str, messages: list[dict]) -> str:
    if not API_KEY:
        return "[DEEPSEEK ERROR] DEEPSEEK_API_KEY not set"

    # DeepSeek uses OpenAI-compatible format
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system_msg}] + messages,
    }
    resp = httpx.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


if __name__ == "__main__":
    run_agent_loop("deepseek", call_deepseek)
