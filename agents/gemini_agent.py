#!/usr/bin/env python3
"""Gemini Agent — Google Gemini governed by COMMAND.

Usage:
  export GOOGLE_API_KEY="AIza..."
  python3 agents/gemini_agent.py
"""

import os
import httpx
from base_agent import run_agent_loop

API_KEY = os.environ.get("GOOGLE_API_KEY", "")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


def call_gemini(system_msg: str, messages: list[dict]) -> str:
    if not API_KEY:
        return "[GEMINI ERROR] GOOGLE_API_KEY not set"

    # Gemini uses different format
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    # Ensure starts with user
    if not contents or contents[0]["role"] != "user":
        contents.insert(0, {"role": "user", "parts": [{"text": "(awaiting input)"}]})

    resp = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        params={"key": API_KEY},
        json={
            "system_instruction": {"parts": [{"text": system_msg}]},
            "contents": contents,
        },
        timeout=30,
    )
    resp.raise_for_status()
    candidates = resp.json().get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        if parts:
            return parts[0].get("text", "")
    return "[GEMINI] No response generated"


if __name__ == "__main__":
    run_agent_loop("gemini", call_gemini)
