"""
seed_card.py — Seed Card Loyalty API routes.

Endpoints:
  GET  /api/seed-card/{agent_id}          → full seed card summary
  GET  /api/seed-card/{agent_id}/history  → point earning history
  POST /api/seed-card/collect             → manual trigger for 48h collection
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.deps import state

router = APIRouter(tags=["seed-card"])


@router.get("/api/seed-card/{agent_id}")
async def get_seed_card(agent_id: str) -> dict:
    """Return the full seed card summary for an agent."""
    try:
        return state.seed_card.card_summary(agent_id)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get("/api/seed-card/{agent_id}/history")
async def get_seed_card_history(agent_id: str, limit: int = 50) -> dict:
    """Return point earning history for an agent."""
    try:
        history = state.seed_card.get_history(agent_id, limit=min(limit, 200))
        return {"agent_id": agent_id, "history": history, "count": len(history)}
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.post("/api/seed-card/collect")
async def trigger_collection() -> dict:
    """Manual trigger for 48h window collection (also runs on startup and hourly)."""
    try:
        result = state.seed_card.collect_all_expired_windows()
        return result
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
