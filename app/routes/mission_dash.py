"""
mission_dash.py — Mission Dashboard (AGENTDASH Layer 4)

Per-mission progress tracking with:
- Status enum: draft → posted → matched → in_progress → review → paid
- Progress percentage (agent sets)
- Milestone checklist (operator defines, agent checks off)
- In-thread updates (piggyback on existing kassa thread system)

Operators see: progress, ETA, milestones, net payout.
Agents see: acceptance criteria, deadline, current status.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any

from app.deps import state

router = APIRouter(tags=["mission_dash"])

VALID_STATUSES = ["draft", "posted", "matched", "in_progress", "review", "paid", "cancelled"]


class InitDashboardPayload(BaseModel):
    status: str = "draft"
    milestones: list[str] = []
    deadline: str | None = None
    assigned_agent: str | None = None
    payout_amount: float = 0
    progress_pct: int = 0
    eta: str | None = None


class UpdateProgressPayload(BaseModel):
    progress_pct: int | None = None
    note: str = ""
    eta: str | None = None
    status: str | None = None


class CompleteMilestonePayload(BaseModel):
    milestone: str = ""


def _dash_path() -> Path:
    return state.root / "data" / "mission_dashboard.json"


def _load_dash() -> dict:
    p = _dash_path()
    if p.exists():
        return json.loads(p.read_text())
    return {"missions": {}}


def _save_dash(data: dict):
    p = _dash_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        f.write(json.dumps(data, indent=2))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)


# ── Create / Initialize dashboard for a mission ─────────────────────────────

@router.post("/api/mission-dash/{mission_id}")
async def init_mission_dashboard(mission_id: str, payload: InitDashboardPayload) -> dict:
    """Initialize or update a mission's dashboard state.

    Body: {
        "status": "posted",
        "milestones": ["Deliver draft", "Review pass", "Final submission"],
        "deadline": "2026-04-10T00:00:00Z",
        "assigned_agent": "agent-xxx",
        "payout_amount": 500.00
    }
    """
    dash = _load_dash()
    missions = dash.setdefault("missions", {})

    existing = missions.get(mission_id, {})
    now = datetime.now(UTC).isoformat()

    status = payload.status or existing.get("status", "draft")
    if status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {VALID_STATUSES}")

    milestones = payload.milestones if payload.milestones else existing.get("milestones", [])
    milestone_state = existing.get("milestone_state", {})
    # Initialize any new milestones
    for m in milestones:
        if m not in milestone_state:
            milestone_state[m] = {"completed": False, "completed_at": None}

    missions[mission_id] = {
        "status": status,
        "progress_pct": payload.progress_pct if payload.progress_pct is not None else existing.get("progress_pct", 0),
        "milestones": milestones,
        "milestone_state": milestone_state,
        "deadline": payload.deadline if payload.deadline is not None else existing.get("deadline"),
        "assigned_agent": payload.assigned_agent if payload.assigned_agent is not None else existing.get("assigned_agent"),
        "payout_amount": payload.payout_amount if payload.payout_amount else existing.get("payout_amount", 0),
        "eta": payload.eta if payload.eta is not None else existing.get("eta"),
        "updates": existing.get("updates", []),
        "created_at": existing.get("created_at", now),
        "updated_at": now,
    }

    _save_dash(dash)

    state.audit.log("mission_dash", "initialized", {"mission_id": mission_id, "status": status})

    return {"ok": True, "mission_id": mission_id, "status": status}


# ── Update progress ──────────────────────────────────────────────────────────

@router.post("/api/mission-dash/{mission_id}/progress")
async def update_progress(mission_id: str, payload: UpdateProgressPayload) -> dict:
    """Agent updates progress percentage and optional note.

    Body: { "progress_pct": 45, "note": "Draft complete, starting review", "eta": "2026-04-08" }
    """
    dash = _load_dash()
    mission = dash.get("missions", {}).get(mission_id)
    if not mission:
        raise HTTPException(404, f"Mission dashboard {mission_id} not found")

    now = datetime.now(UTC).isoformat()

    if payload.progress_pct is not None:
        mission["progress_pct"] = max(0, min(100, int(payload.progress_pct)))
    if payload.eta is not None:
        mission["eta"] = payload.eta
    if payload.status and payload.status in VALID_STATUSES:
        mission["status"] = payload.status

    note = (payload.note or "").strip()
    if note:
        mission.setdefault("updates", []).append({
            "note": note,
            "progress_pct": mission["progress_pct"],
            "timestamp": now,
        })

    mission["updated_at"] = now
    _save_dash(dash)

    return {"ok": True, "mission_id": mission_id, "progress_pct": mission["progress_pct"]}


# ── Complete milestone ───────────────────────────────────────────────────────

@router.post("/api/mission-dash/{mission_id}/milestone")
async def complete_milestone(mission_id: str, payload: CompleteMilestonePayload) -> dict:
    """Mark a milestone as complete.

    Body: { "milestone": "Deliver draft" }
    """
    dash = _load_dash()
    mission = dash.get("missions", {}).get(mission_id)
    if not mission:
        raise HTTPException(404, f"Mission dashboard {mission_id} not found")

    milestone_name = (payload.milestone or "").strip()
    if milestone_name not in mission.get("milestone_state", {}):
        raise HTTPException(404, f"Milestone '{milestone_name}' not found")

    now = datetime.now(UTC).isoformat()
    mission["milestone_state"][milestone_name] = {"completed": True, "completed_at": now}

    # Auto-calculate progress from milestones
    total = len(mission.get("milestones", []))
    completed = sum(1 for v in mission["milestone_state"].values() if v.get("completed"))
    if total > 0:
        mission["progress_pct"] = round((completed / total) * 100)

    mission["updated_at"] = now
    _save_dash(dash)

    return {"ok": True, "mission_id": mission_id, "milestone": milestone_name, "progress_pct": mission["progress_pct"]}


# ── Get mission dashboard ────────────────────────────────────────────────────

@router.get("/api/mission-dash/{mission_id}")
async def get_mission_dashboard(mission_id: str) -> dict:
    """Get full dashboard state for a mission."""
    dash = _load_dash()
    mission = dash.get("missions", {}).get(mission_id)
    if not mission:
        raise HTTPException(404, f"Mission dashboard {mission_id} not found")
    return {"mission_id": mission_id, **mission}


# ── List all active dashboards ───────────────────────────────────────────────

@router.get("/api/mission-dash")
async def list_mission_dashboards(status: str = "") -> dict:
    """List all mission dashboards, optionally filtered by status."""
    dash = _load_dash()
    missions = dash.get("missions", {})

    result = []
    for mid, data in missions.items():
        if status and data.get("status") != status:
            continue
        result.append({
            "mission_id": mid,
            "status": data.get("status"),
            "progress_pct": data.get("progress_pct", 0),
            "assigned_agent": data.get("assigned_agent"),
            "deadline": data.get("deadline"),
            "updated_at": data.get("updated_at"),
        })

    result.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return {"dashboards": result, "count": len(result)}
