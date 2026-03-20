#!/usr/bin/env python3
"""GPT Agent — OpenAI GPT-4o governed by COMMAND.

Usage:
  export OPENAI_API_KEY="sk-..."
  python3 agents/gpt_agent.py
"""

import os
import httpx
from base_agent import run_agent_loop

API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")


def call_gpt(system_msg: str, messages: list[dict]) -> str:
    if not API_KEY:
        return "[GPT ERROR] OPENAI_API_KEY not set"

    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system_msg}] + messages,
    }
    resp = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


if __name__ == "__main__":
    run_agent_loop("gpt", call_gpt)
