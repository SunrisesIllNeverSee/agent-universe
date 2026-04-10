"""
register_chat_agent.py — Register CIVITAE gateway on Agentverse via Chat Protocol

Registers the fetchai_adapter.py uAgent on Agentverse so DeltaV agents can
discover and message it. Run AFTER deploying fetchai_adapter.py and getting
its public Railway URL.

Usage:
    export AGENTVERSE_KEY=<your-key>           # from agentverse.ai
    export AGENT_SEED_PHRASE=<your-seed>       # same seed as FETCH_AGENT_SEED
    export AGENT_ENDPOINT=https://<railway-domain>/submit
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

endpoint = os.environ.get(
    "AGENT_ENDPOINT",
    "https://<your-railway-domain>.up.railway.app/submit",  # set AGENT_ENDPOINT env var
)

if "<your-railway-domain>" in endpoint:
    raise SystemExit(
        "Set AGENT_ENDPOINT to your Railway public URL before registering.\n"
        "Example: export AGENT_ENDPOINT=https://civitae-fetchai.up.railway.app/submit"
    )

register_chat_agent(
    "civitae-gateway",
    endpoint,
    active=True,
    credentials=RegistrationRequestCredentials(
        agentverse_api_key=os.environ["AGENTVERSE_KEY"],
        agent_seed_phrase=os.environ["AGENT_SEED_PHRASE"],
    ),
)

print(f"Registration complete. Endpoint: {endpoint}")
