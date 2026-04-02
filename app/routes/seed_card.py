"""
seed_card.py — Seed Card Loyalty API routes.

Endpoints:
  GET  /api/seed-card/{agent_id}          → full seed card summary
  GET  /api/seed-card/{agent_id}/history  → point earning history
  POST /api/seed-card/collect             → manual trigger for 48h collection
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.deps import state

router = APIRouter(tags=["seed-card"])
logger = logging.getLogger("civitae.seed_card")


def _agent_exists(agent_id: str) -> bool:
    """Return True if agent_id is registered in the runtime registry."""
    return any(
        r.get("agent_id") == agent_id
        for r in state.runtime.registry
    )


@router.get("/api/seed-card/{agent_id}")
async def get_seed_card(agent_id: str) -> dict:
    """Return the full seed card summary for an agent."""
    try:
        # Only return data for registered agents or agents with existing cards
        if not state.seed_card.has_card(agent_id) and not _agent_exists(agent_id):
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        return state.seed_card.card_summary(agent_id)
    except Exception as exc:
        logger.warning("seed card summary failed for %s: %s", agent_id, exc)
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get("/api/seed-card/{agent_id}/history")
async def get_seed_card_history(agent_id: str, limit: int = 50) -> dict:
    """Return point earning history for an agent."""
    try:
        # Only return data for registered agents or agents with existing cards
        if not state.seed_card.has_card(agent_id) and not _agent_exists(agent_id):
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        history = state.seed_card.get_history(agent_id, limit=min(limit, 200))
        return {"agent_id": agent_id, "history": history, "count": len(history)}
    except Exception as exc:
        logger.warning("seed card history failed for %s: %s", agent_id, exc)
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.post("/api/seed-card/collect")
async def trigger_collection() -> dict:
    """Manual trigger for 48h window collection (also runs on startup and hourly)."""
    try:
        result = state.seed_card.collect_all_expired_windows()
        return result
    except Exception as exc:
        logger.warning("seed card collection failed: %s", exc)
        return JSONResponse({"error": str(exc)}, status_code=500)
