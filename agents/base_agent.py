"""
MO§ES™ Base Agent — shared logic for all provider agents.
Each provider script imports this and just implements call_provider().
"""

import httpx
import time
import sys
import os

COMMAND = os.environ.get("COMMAND_URL", "http://localhost:8300")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "3"))


def build_governed_prompt(context: dict) -> tuple[str, list[dict]]:
    """Build a system prompt + message list from governed context."""
    gov = context.get("governance", {})
    system_parts = [
        "You are operating under MO§ES™ constitutional governance.",
        f"Mode: {gov.get('mode', 'None')}",
        f"Posture: {gov.get('posture', 'SCOUT')}",
        f"Role: {gov.get('role', 'Primary')}",
    ]

    if gov.get('reasoning_mode'):
        system_parts.append(f"Reasoning: {gov['reasoning_mode']}")
    if gov.get('response_style'):
        system_parts.append(f"Style: {gov['response_style']}")

    # Add posture constraints
    posture = gov.get('posture', 'SCOUT')
    if posture == 'SCOUT':
        system_parts.append("SCOUT posture: gather information only. No state changes, no transactions.")
    elif posture == 'DEFENSE':
        system_parts.append("DEFENSE posture: protect existing positions. Confirm before any outbound action.")
    elif posture == 'OFFENSE':
        system_parts.append("OFFENSE posture: execute within governance constraints.")

    system_parts.append("Follow governance constraints strictly. Every response is audited.")

    # Vault context
    for doc in context.get("loaded_context", []):
        system_parts.append(f"[Vault: {doc}]")

    system_msg = "\n".join(system_parts)

    # Message history
    messages = []
    for m in context.get("messages", []):
        role = "user" if m.get("role_context") == "operator" else "assistant"
        messages.append({"role": role, "content": m["text"]})

    return system_msg, messages


def run_agent_loop(agent_name: str, call_provider_fn):
    """Main agent loop — poll COMMAND, call provider, send response."""
    print(f"[{agent_name}] Connecting to COMMAND at {COMMAND}...")

    # Join
    try:
        httpx.post(f"{COMMAND}/api/mcp/join", json={"name": agent_name}, timeout=5)
        print(f"[{agent_name}] Joined COMMAND.")
    except Exception as e:
        print(f"[{agent_name}] Failed to join: {e}")
        sys.exit(1)

    last_seen_id = 0
    print(f"[{agent_name}] Polling every {POLL_INTERVAL}s. Ctrl+C to stop.")

    while True:
        try:
            # Read governed context
            ctx = httpx.post(f"{COMMAND}/api/mcp/read", json={
                "name": agent_name,
                "channel": "general",
                "since_id": last_seen_id,
                "limit": 20,
            }, timeout=10).json()

            messages = ctx.get("messages", [])
            if not messages:
                time.sleep(POLL_INTERVAL)
                continue

            # Track cursor
            max_id = max(m.get("id", 0) for m in messages)
            if max_id <= last_seen_id:
                time.sleep(POLL_INTERVAL)
                continue

            last_seen_id = max_id

            # Check if latest message needs a response (not from us)
            latest = messages[-1]
            if latest.get("sender") == agent_name:
                time.sleep(POLL_INTERVAL)
                continue

            # Build governed prompt
            system_msg, chat_messages = build_governed_prompt(ctx)

            print(f"[{agent_name}] Responding to: {latest['text'][:60]}...")

            # Call the provider
            reply = call_provider_fn(system_msg, chat_messages)

            if reply:
                # Send back through COMMAND
                httpx.post(f"{COMMAND}/api/mcp/send", json={
                    "sender": agent_name,
                    "message": reply,
                    "channel": "general",
                }, timeout=10)
                print(f"[{agent_name}] Sent: {reply[:80]}...")

        except KeyboardInterrupt:
            print(f"\n[{agent_name}] Stopped.")
            break
        except Exception as e:
            print(f"[{agent_name}] Error: {e}")

        time.sleep(POLL_INTERVAL)
