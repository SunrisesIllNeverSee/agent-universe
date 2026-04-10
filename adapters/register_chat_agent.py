"""
register_chat_agent.py — Register CIVITAE on Agentverse via Chat Protocol

Uses uagents-core Chat Protocol registration — no running server required.
Agentverse routes messages through the mailbox, so the agent endpoint is
the CIVITAE signup API.

Usage:
    export AGENTVERSE_KEY=<your-key>
    export AGENT_SEED_PHRASE=<your-seed>
    python3.11 adapters/register_chat_agent.py

Requirements:
    python3.11 -m venv venv311
    venv311/bin/pip install uagents-core
"""

import os
from uagents_core.utils.registration import (
    register_chat_agent,
    RegistrationRequestCredentials,
)

register_chat_agent(
    "Hange",
    "https://signomy.xyz/api/provision/signup",
    active=True,
    credentials=RegistrationRequestCredentials(
        agentverse_api_key=os.environ["AGENTVERSE_KEY"],
        agent_seed_phrase=os.environ["AGENT_SEED_PHRASE"],
    ),
)

print("Registration complete.")
