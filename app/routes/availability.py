"""
availability.py — Agent Availability Blocks (AGENTDASH Layer 2)

Agents set focus windows with domain tags. During active blocks:
- Auto-boosted in Cascade Matcher
- Push notifications for high-fit missions
- "Available Now" toggle feeds live status

Operators see agent availability when posting missions.
"""
from __future__ import annotations

import json
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any

from app.deps import state

router = APIRouter(tags=["availability"])


class SetAvailabilityPayload(BaseModel):
    available_now: bool = False
    domains: list[str] = []
    blocks: list[Any] = []
    response_time_hours: float | None = None


def _avail_path() -> Path:
    return state.root / "data" / "availability.json"


def _load_avail() -> dict:
    p = _avail_path()
    if p.exists():
        return json.loads(p.read_text())
    return {"agents": {}}


def _save_avail(data: dict):
    p = _avail_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        f.write(json.dumps(data, indent=2))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)


# ── Set availability ─────────────────────────────────────────────────────────

@router.post("/api/availability/{agent_id}")
async def set_availability(agent_id: str, payload: SetAvailabilityPayload) -> dict:
    """Set or update an agent's availability.

    Body: {
        "available_now": true/false,
        "domains": ["research", "code", "governance"],
        "blocks": [
            {"start": "2026-04-03T09:00:00Z", "end": "2026-04-03T17:00:00Z", "recurring": "weekdays"},
            {"start": "2026-04-05T10:00:00Z", "end": "2026-04-05T14:00:00Z"}
        ],
        "response_time_hours": 2
    }
    """
    avail = _load_avail()
    agents = avail.setdefault("agents", {})

    available_now = payload.available_now
    domains = payload.domains
    blocks = payload.blocks
    response_time = payload.response_time_hours

    agents[agent_id] = {
        "available_now": available_now,
        "domains": domains,
        "blocks": blocks,
        "response_time_hours": response_time,
        "updated_at": datetime.now(UTC).isoformat(),
    }

    _save_avail(avail)

    state.audit.log("availability", "updated", {
        "agent_id": agent_id, "available_now": available_now, "domains": domains,
    })

    return {"ok": True, "agent_id": agent_id, "available_now": available_now}


# ── Toggle available now ─────────────────────────────────────────────────────

@router.post("/api/availability/{agent_id}/toggle")
async def toggle_available(agent_id: str) -> dict:
    """Quick toggle of available_now status."""
    avail = _load_avail()
    agents = avail.setdefault("agents", {})
    current = agents.get(agent_id, {})
    new_status = not current.get("available_now", False)
    current["available_now"] = new_status
    current["updated_at"] = datetime.now(UTC).isoformat()
    agents[agent_id] = current
    _save_avail(avail)
    return {"ok": True, "agent_id": agent_id, "available_now": new_status}


# ── Get agent availability ───────────────────────────────────────────────────

@router.get("/api/availability/{agent_id}")
async def get_availability(agent_id: str) -> dict:
    """Get an agent's current availability state."""
    avail = _load_avail()
    agent_avail = avail.get("agents", {}).get(agent_id, {})
    if not agent_avail:
        return {"agent_id": agent_id, "available_now": False, "domains": [], "blocks": []}
    return {"agent_id": agent_id, **agent_avail}


# ── List all available agents ────────────────────────────────────────────────

@router.get("/api/availability")
async def list_available(domain: str = "") -> dict:
    """List all agents currently available, optionally filtered by domain."""
    avail = _load_avail()
    agents = avail.get("agents", {})

    available = []
    for agent_id, data in agents.items():
        if not data.get("available_now"):
            continue
        if domain and domain.lower() not in [d.lower() for d in data.get("domains", [])]:
            continue

        # Look up agent info from registry
        reg = next((r for r in state.runtime.registry if r.get("agent_id") == agent_id), None)
        available.append({
            "agent_id": agent_id,
            "handle": reg.get("name", agent_id) if reg else agent_id,
            "domains": data.get("domains", []),
            "response_time_hours": data.get("response_time_hours"),
            "updated_at": data.get("updated_at"),
        })

    return {"available": available, "count": len(available), "domain_filter": domain or None}


# ── Available count for operators ────────────────────────────────────────────

@router.get("/api/availability/stats")
async def availability_stats() -> dict:
    """Quick stats: how many agents available, by domain."""
    avail = _load_avail()
    agents = avail.get("agents", {})

    total_available = 0
    by_domain = {}
    for data in agents.values():
        if data.get("available_now"):
            total_available += 1
            for d in data.get("domains", []):
                by_domain[d] = by_domain.get(d, 0) + 1

    return {"total_available": total_available, "by_domain": by_domain}
