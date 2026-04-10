# SPDX-License-Identifier: MIT
"""
fetchai_adapter.py — CIVITAE × Fetch.ai DeltaV Gateway

Step 10 — External Rollout Queue (docs/agent-onboarding/BUILDING-ON-THE-PLUGIN.md)

Wraps CIVITAE's core APIs as a uAgent service discoverable on Fetch.ai's DeltaV
marketplace (50K+ agents). Inbound DeltaV service requests are translated into
CIVITAE API calls via httpx — no server internals imported, independently deployable.

Architecture:
    DeltaV agent → uAgent message → handler → httpx → CIVITAE public API
    (same external client pattern as civitae_mcp_server.py)

Three services exposed on DeltaV:
    1. governed_work     — fill a CIVITAE mission slot
    2. agent_registration — register a new agent in CIVITAE
    3. marketplace       — browse KA§§A posts

Environment variables:
    CIVITAE_API_URL   — CIVITAE backend URL (default: https://signomy.xyz)
    CIVITAE_JWT       — agent JWT for authenticated calls (from civitae_register)
    FETCH_AGENT_SEED  — deterministic seed for permanent Almanac address (optional)
    FETCH_AGENT_PORT  — local port for uAgent server (default: 8001)

Run:
    pip install uagents httpx
    python adapters/fetchai_adapter.py

TODO before going live on Agentverse:
    1. Obtain Agentverse mailbox key at https://agentverse.ai
    2. Add mailbox=<your-mailbox-key> to Agent() constructor below
    3. Set FETCH_AGENT_SEED to a persistent value so address stays stable
    4. Register on DeltaV marketplace at https://deltav.agentverse.ai
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import httpx
from uagents import Agent, Context, Model

logger = logging.getLogger("civitae.fetchai")

# ── Config ─────────────────────────────────────────────────────────────────────

API = os.getenv("CIVITAE_API_URL", "https://signomy.xyz")
JWT = os.getenv("CIVITAE_JWT", "")
FETCH_AGENT_SEED = os.getenv("FETCH_AGENT_SEED") or None   # None = ephemeral address

# Railway sets PORT; FETCH_AGENT_PORT is the local fallback
FETCH_AGENT_PORT = int(os.getenv("PORT", os.getenv("FETCH_AGENT_PORT", "8001")))

# Public endpoint URL — Railway provides RAILWAY_PUBLIC_DOMAIN automatically
_PUBLIC_DOMAIN = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
_ENDPOINT_URL = (
    f"https://{_PUBLIC_DOMAIN}/submit"
    if _PUBLIC_DOMAIN
    else f"http://localhost:{FETCH_AGENT_PORT}/submit"
)

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


# ── CIVITAE httpx helpers (mirror civitae_mcp_server.py) ──────────────────────

def _auth_headers() -> dict:
    h = {"Content-Type": "application/json"}
    if JWT:
        h["Authorization"] = f"Bearer {JWT}"
    return h


async def _get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.get(f"{API}{path}", params=params, headers=_auth_headers())
        r.raise_for_status()
        return r.json()


async def _post(path: str, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.post(f"{API}{path}", json=body, headers=_auth_headers())
        r.raise_for_status()
        return r.json()


# ── DeltaV service models ──────────────────────────────────────────────────────

class GovernedWorkRequest(Model):
    """Request to fill a CIVITAE mission slot — the primary governed work unit."""
    slot_id: str
    agent_id: str
    agent_name: Optional[str] = None
    capabilities: Optional[list[str]] = None


class GovernedWorkResponse(Model):
    """Response from CIVITAE slot-fill — includes governance assignment."""
    ok: bool
    slot_id: Optional[str] = None
    mission_id: Optional[str] = None
    governance_mode: Optional[str] = None
    governance_posture: Optional[str] = None
    role_assigned: Optional[str] = None
    error: Optional[str] = None


class AgentRegistrationRequest(Model):
    """Register a Fetch.ai agent in CIVITAE — creates an @signomy.xyz identity."""
    name: str
    handle: Optional[str] = None
    capabilities: Optional[list[str]] = None
    system: str = "fetchai"


class AgentRegistrationResponse(Model):
    """CIVITAE welcome package — includes agent_id, JWT, and governance assignment."""
    ok: bool
    agent_id: Optional[str] = None
    email: Optional[str] = None
    token: Optional[str] = None
    tier: Optional[str] = None
    governance_mode: Optional[str] = None
    error: Optional[str] = None


class MarketplaceRequest(Model):
    """Browse CIVITAE KA§§A marketplace posts."""
    category: Optional[str] = None      # iso | products | bounties | hiring | services
    status: str = "open"
    limit: int = 10
    search: Optional[str] = None


class MarketplaceResponse(Model):
    """KA§§A marketplace results — list of governed posts."""
    ok: bool
    count: int = 0
    posts: Optional[list[dict]] = None
    error: Optional[str] = None


# ── uAgent setup ───────────────────────────────────────────────────────────────

agent = Agent(
    name="civitae-gateway",
    seed=FETCH_AGENT_SEED,
    port=FETCH_AGENT_PORT,
    endpoint=[_ENDPOINT_URL],
    # TODO: add mailbox=<agentverse-mailbox-key> for cloud connectivity
    # Get yours at https://agentverse.ai after creating an account
)


# ── Message handlers ───────────────────────────────────────────────────────────

@agent.on_message(model=GovernedWorkRequest, replies=GovernedWorkResponse)
async def handle_governed_work(ctx: Context, sender: str, msg: GovernedWorkRequest):
    """Fill a CIVITAE mission slot on behalf of a DeltaV agent."""
    ctx.logger.info("governed_work request from %s — slot %s", sender, msg.slot_id)
    try:
        payload = {
            "slot_id": msg.slot_id,
            "agent_id": msg.agent_id,
            "agent_name": msg.agent_name or msg.agent_id,
        }
        if msg.capabilities:
            payload["capabilities"] = msg.capabilities

        result = await _post("/api/slots/fill", payload)

        await ctx.send(sender, GovernedWorkResponse(
            ok=True,
            slot_id=msg.slot_id,
            mission_id=result.get("slot", {}).get("mission_id"),
            governance_mode=result.get("governance_applied", {}).get("mode"),
            governance_posture=result.get("governance_applied", {}).get("posture"),
            role_assigned=result.get("role_assigned"),
        ))
    except Exception as e:
        ctx.logger.error("governed_work error: %s", e)
        await ctx.send(sender, GovernedWorkResponse(ok=False, error=str(e)))


@agent.on_message(model=AgentRegistrationRequest, replies=AgentRegistrationResponse)
async def handle_agent_registration(ctx: Context, sender: str, msg: AgentRegistrationRequest):
    """Register a DeltaV agent in CIVITAE — assigns @signomy.xyz identity and governance."""
    ctx.logger.info("agent_registration request from %s — name %s", sender, msg.name)
    try:
        payload = {
            "name": msg.name,
            "handle": msg.handle or msg.name,
            "capabilities": msg.capabilities or [],
            "system": msg.system,
            "agent_type": "agent",
            "agent_name": msg.handle or msg.name,
        }
        result = await _post("/api/provision/signup", payload)

        await ctx.send(sender, AgentRegistrationResponse(
            ok=True,
            agent_id=result.get("agent_id"),
            email=result.get("email"),
            token=result.get("token"),
            tier=result.get("tier"),
            governance_mode=result.get("governance", {}).get("mode"),
        ))
    except Exception as e:
        ctx.logger.error("agent_registration error: %s", e)
        await ctx.send(sender, AgentRegistrationResponse(ok=False, error=str(e)))


@agent.on_message(model=MarketplaceRequest, replies=MarketplaceResponse)
async def handle_marketplace(ctx: Context, sender: str, msg: MarketplaceRequest):
    """Expose CIVITAE KA§§A marketplace posts to DeltaV agents."""
    ctx.logger.info("marketplace request from %s — category %s", sender, msg.category)
    try:
        params: dict = {"status": msg.status, "limit": msg.limit}
        if msg.category:
            params["tab"] = msg.category
        if msg.search:
            params["search"] = msg.search

        result = await _get("/api/kassa/posts", params)
        posts = result.get("posts", [])

        await ctx.send(sender, MarketplaceResponse(
            ok=True,
            count=len(posts),
            posts=posts,
        ))
    except Exception as e:
        ctx.logger.error("marketplace error: %s", e)
        await ctx.send(sender, MarketplaceResponse(ok=False, error=str(e)))


# ── Startup log ────────────────────────────────────────────────────────────────

@agent.on_event("startup")
async def on_startup(ctx: Context):
    ctx.logger.info("CIVITAE DeltaV gateway started")
    ctx.logger.info("Agent address: %s", agent.address)
    ctx.logger.info("Public URL:    %s", _ENDPOINT_URL)
    ctx.logger.info("CIVITAE API:   %s", API)
    ctx.logger.info("Auth:          %s", "JWT set" if JWT else "unauthenticated — set CIVITAE_JWT")
    ctx.logger.info("Services:      governed_work | agent_registration | marketplace")
    ctx.logger.info("")
    ctx.logger.info("TODO: Add Agentverse mailbox key for cloud connectivity")
    ctx.logger.info("      https://agentverse.ai → create account → get mailbox key")
    ctx.logger.info("      Then add mailbox=<key> to Agent() constructor in this file")


def main():
    logging.basicConfig(level=logging.INFO)
    agent.run()


if __name__ == "__main__":
    main()
