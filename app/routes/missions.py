"""
missions.py — Missions, Campaigns, Tasks, and Slots endpoints.

Extracted from server.py create_app() monolith.
Covers:
  - DEPLOY missions (create, list, get, update, end)
  - Campaigns (create, list, get, close, activate, add_mission)
  - Tasks (create, list, get, assign, start, deliver, close, cancel)
  - Slots (create from formation, list, open, fill, leave, bounty)
"""
from __future__ import annotations

import json
import os
import secrets as _secrets_mod
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any

from app.deps import state
from app.seeds import create_seed

router = APIRouter(tags=["missions"])


class CreateMissionPayload(BaseModel):
    label: str = ""
    objective: str = ""
    posture: str = "SCOUT"
    formation: str = ""
    target: str = ""
    duration: str = "sprint"
    limits: str = ""
    systems: dict[str, Any] = {}
    agents: dict[str, Any] = {}
    channel: str = ""
    agent_id: str = "operator"


class EndMissionPayload(BaseModel):
    payout_per_slot: float = 0
    originator_id: str = ""


class UpdateMissionPayload(BaseModel):
    posture: str | None = None
    formation: str | None = None
    status: str | None = None
    target: str | None = None
    limits: str | None = None


class CreateCampaignPayload(BaseModel):
    name: str = ""
    objective: str = ""
    created_by: str = ""
    ecosystems: list[str] = []
    revenue_target: str = ""


class AddMissionToCampaignPayload(BaseModel):
    mission_id: str = ""


class CloseCampaignPayload(BaseModel):
    outcome: str = ""


class CreateTaskPayload(BaseModel):
    title: str
    type: str = "build"
    track: str = "tool"
    objective: str = ""
    target: str = ""
    exp_reward: int | None = None
    payout: float = 0.0
    operation_id: str | None = None
    campaign_id: str | None = None
    created_by: str = "operator"


class AssignTaskPayload(BaseModel):
    agent_id: str = ""


class DeliverTaskPayload(BaseModel):
    deliverable: str = ""


class CloseTaskPayload(BaseModel):
    requestor: str = ""


class CreateSlotsPayload(BaseModel):
    mission_id: str = ""
    formation_id: str = ""
    posture: str = "SCOUT"
    label: str = ""
    positions: list[dict[str, Any]] = []
    roles: list[str] = []
    revenue_splits: list[int] = []
    governance_mode: str = ""


class FillSlotPayload(BaseModel):
    slot_id: str = ""
    agent_id: str = ""
    agent_name: str = ""


class LeaveSlotPayload(BaseModel):
    slot_id: str = ""
    agent_id: str = ""


class PostBountyPayload(BaseModel):
    agent_id: str = ""
    agent_name: str = ""
    label: str = ""
    description: str = ""
    posture: str = "SCOUT"
    slots_needed: int = 3
    revenue_pool: float = 0

# ── Atomic write helper ─────────────────────────────────────────────────────


def _atomic_write(path: Path, data: str) -> None:
    """Write data to a file atomically via tmp-then-rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


# ── JSON file loaders / savers ───────────────────────────────────────────────
# FIX-12: JSON file-backed state — missions, slots, tasks, campaigns, metrics.
# Each _load_*() re-reads from disk on every call. This is simple and correct
# (no stale cache, atomic writes guarantee consistency) but becomes an I/O
# bottleneck at high traffic. If needed post-launch, add an in-memory cache
# with TTL or migrate hot paths to SQLite (like kassa/forums already use).


def _missions_path() -> Path:
    return state.data_path("missions.json")


def _campaigns_path() -> Path:
    return state.data_path("campaigns.json")


def _tasks_path() -> Path:
    return state.data_path("tasks.json")


def _slots_path() -> Path:
    return state.data_path("slots.json")


def _load_missions() -> list[dict]:
    p = _missions_path()
    if p.exists():
        return json.loads(p.read_text())
    return []


def _save_missions(missions: list[dict]) -> None:
    _atomic_write(_missions_path(), json.dumps(missions, indent=2))


def _load_campaigns() -> list[dict]:
    p = _campaigns_path()
    if p.exists():
        return json.loads(p.read_text())
    return []


def _save_campaigns(campaigns: list[dict]) -> None:
    _atomic_write(_campaigns_path(), json.dumps(campaigns, indent=2))


def _load_tasks() -> list[dict]:
    p = _tasks_path()
    if p.exists():
        return json.loads(p.read_text())
    return []


def _save_tasks(tasks: list[dict]) -> None:
    _atomic_write(_tasks_path(), json.dumps(tasks, indent=2))


def _load_slots() -> list[dict]:
    p = _slots_path()
    if p.exists():
        return json.loads(p.read_text())
    return []


def _save_slots(slots: list[dict]) -> None:
    _atomic_write(_slots_path(), json.dumps(slots, indent=2))


# ── Task EXP base values ────────────────────────────────────────────────────

TASK_EXP_BASE: dict[str, int] = {
    "build":    150,
    "collect":   75,
    "acquire":  100,
    "research": 125,
    "verify":   100,
    "create":   150,
    "scout":     75,
    "guard":     50,
}


def _award_exp(agent_id: str, exp: int, track: str) -> dict:
    """Credit EXP to an agent. Returns updated exp summary."""
    agent = next((r for r in state.runtime.registry if r.get("agent_id") == agent_id), None)
    if not agent:
        return {}
    agent.setdefault("exp", 0)
    agent.setdefault("exp_by_track", {"research": 0, "tool": 0, "creative": 0})
    agent["exp"] += exp
    agent["exp_by_track"][track] = agent["exp_by_track"].get(track, 0) + exp
    return {"exp": agent["exp"], "exp_by_track": agent["exp_by_track"]}


# ══════════════════════════════════════════════════════════════════════════════
# MISSIONS (DEPLOY)
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/api/missions")
async def create_mission(payload: CreateMissionPayload) -> dict:
    """Create a new DEPLOY mission."""
    missions = _load_missions()
    mid = f"mission-{_secrets_mod.token_hex(4)}"
    mission = {
        "id": mid,
        "mission_id": mid,  # alias — both keys resolve to the same value
        "label": payload.label,
        "objective": payload.objective,
        "posture": payload.posture,
        "formation": payload.formation,
        "target": payload.target,
        "duration": payload.duration,
        "limits": payload.limits,
        "systems": payload.systems,
        "agents": payload.agents,
        "status": "active",
        "created_at": datetime.now(UTC).isoformat(),
        "ended_at": None,
        "governance_at_launch": {
            "mode": state.runtime.governance.mode,
            "posture": state.runtime.governance.posture,
            "role": state.runtime.governance.role,
        },
        "results": [],
        "channel": payload.channel or f"mission-{(payload.label or 'unnamed').lower().replace(' ', '-')}",
    }
    missions.append(mission)
    _save_missions(missions)
    state.audit.log("deploy", "mission_created", {
        "mission_id": mission["id"],
        "label": mission["label"],
        "posture": mission["posture"],
        "governance": mission["governance_at_launch"],
    })
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))

    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="mission",
            source_id=mission["id"],
            creator_id=payload.agent_id or "operator",
            creator_type="BI",
            seed_type="planted",
            metadata={"label": mission["label"], "posture": mission["posture"]},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass

    return {**mission, "seed_doi": seed_doi}


@router.get("/api/missions")
async def list_missions() -> dict:
    return {"missions": _load_missions()}


@router.get("/api/missions/{mission_id}")
async def get_mission(mission_id: str) -> dict:
    mission = next((m for m in _load_missions() if m.get("id") == mission_id or m.get("mission_id") == mission_id), None)
    if not mission:
        return JSONResponse({"error": "Mission not found"}, status_code=404)
    return {"mission": mission}


@router.post("/api/missions/{mission_id}/end")
async def end_mission(mission_id: str, payload: EndMissionPayload | None = None) -> dict:
    missions = _load_missions()
    mission = next((m for m in missions if m["id"] == mission_id), None)
    if not mission:
        return JSONResponse({"error": "Mission not found"}, status_code=404)
    mission["status"] = "completed"
    mission["ended_at"] = datetime.now(UTC).isoformat()

    # ── Economy: process payouts for all filled slots in this mission ──
    payout_amount = payload.payout_per_slot if payload else 0
    payouts = []
    if payout_amount > 0:
        all_slots = _load_slots()
        filled = [s for s in all_slots if s["mission_id"] == mission_id and s["status"] == "filled" and s.get("agent_id")]
        for slot in filled:
            try:
                result = state.economy.process_mission_payout(
                    agent_id=slot["agent_id"],
                    agent_metrics={},
                    gross_amount=payout_amount,
                    mission_id=mission_id,
                    originator_id=payload.originator_id if payload else "",
                )
                payouts.append(result)
            except Exception:
                pass

    mission["payouts"] = payouts
    _save_missions(missions)
    state.audit.log("deploy", "mission_ended", {
        "mission_id": mission_id,
        "slots_paid": len(payouts),
        "payout_per_slot": payout_amount,
    })
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))
    await state.emit("mission_ended", {"mission_id": mission_id, "payouts": len(payouts)})
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="mission_ended",
            source_id=mission_id,
            creator_id="operator",
            creator_type="BI",
            seed_type="planted",
            metadata={"mission_id": mission_id, "slots_paid": len(payouts), "payout_per_slot": payout_amount},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    return {**mission, "seed_doi": seed_doi}


@router.post("/api/missions/{mission_id}/update")
async def update_mission(mission_id: str, payload: UpdateMissionPayload) -> dict:
    missions = _load_missions()
    mission = next((m for m in missions if m["id"] == mission_id), None)
    if not mission:
        return JSONResponse({"error": "Mission not found"}, status_code=404)
    updates = {}
    for k in ["posture", "formation", "status", "target", "limits"]:
        val = getattr(payload, k, None)
        if val is not None:
            mission[k] = val
            updates[k] = val
    _save_missions(missions)
    try:
        await create_seed(source_type="mission_updated", source_id=mission_id, creator_id="operator", creator_type="BI", seed_type="touched", metadata=updates)
    except Exception:
        pass
    return mission


# ══════════════════════════════════════════════════════════════════════════════
# CAMPAIGNS
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/api/campaigns")
async def create_campaign(payload: CreateCampaignPayload) -> dict:
    """Create a CAMPAIGN — long-term strategy container for missions."""
    campaigns = _load_campaigns()
    campaign = {
        "id": f"campaign-{_secrets_mod.token_hex(4)}",
        "name": payload.name,
        "objective": payload.objective,
        "created_by": payload.created_by,
        "ecosystems": payload.ecosystems,
        "revenue_target": payload.revenue_target,
        "status": "active",
        "outcome": "",
        "created_at": datetime.now(UTC).isoformat(),
        "closed_at": None,
        "missions": [],
    }
    campaigns.append(campaign)
    _save_campaigns(campaigns)
    state.audit.log("campaign", "created", {"campaign_id": campaign["id"], "name": campaign["name"]})
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))
    try:
        await create_seed(source_type="campaign", source_id=campaign["id"], creator_id=campaign.get("created_by") or "operator", creator_type="BI", seed_type="planted", metadata={"name": campaign["name"]})
    except Exception:
        pass
    return campaign


@router.get("/api/campaigns")
async def list_campaigns() -> dict:
    return {"campaigns": _load_campaigns()}


@router.get("/api/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str) -> dict:
    campaign = next((c for c in _load_campaigns() if c["id"] == campaign_id), None)
    if not campaign:
        return JSONResponse({"error": "Campaign not found"}, status_code=404)
    return {"campaign": campaign}


@router.post("/api/campaigns/{campaign_id}/add_mission")
async def add_mission_to_campaign(campaign_id: str, payload: AddMissionToCampaignPayload) -> dict:
    campaigns = _load_campaigns()
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if not campaign:
        return JSONResponse({"error": "Campaign not found"}, status_code=404)
    mission_id = payload.mission_id
    if mission_id and mission_id not in campaign["missions"]:
        campaign["missions"].append(mission_id)
    _save_campaigns(campaigns)
    return campaign


@router.post("/api/campaigns/{campaign_id}/close")
async def close_campaign(campaign_id: str, payload: CloseCampaignPayload) -> dict:
    campaigns = _load_campaigns()
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if not campaign:
        return JSONResponse({"error": "Campaign not found"}, status_code=404)
    campaign["status"] = "closed"
    campaign["closed_at"] = datetime.now(UTC).isoformat()
    campaign["outcome"] = payload.outcome
    _save_campaigns(campaigns)
    state.audit.log("campaign", "closed", {"campaign_id": campaign_id, "name": campaign.get("name")})
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))
    try:
        await create_seed(source_type="campaign_closed", source_id=campaign_id, creator_id="operator", creator_type="BI", seed_type="touched", metadata={"name": campaign.get("name"), "outcome": campaign["outcome"]})
    except Exception:
        pass
    return campaign


@router.post("/api/campaigns/{campaign_id}/activate")
async def activate_campaign(campaign_id: str) -> dict:
    """Set a campaign to active status."""
    campaigns = _load_campaigns()
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if not campaign:
        return JSONResponse({"error": "Campaign not found"}, status_code=404)
    if campaign.get("status") == "closed":
        return JSONResponse({"error": "Cannot reactivate a closed campaign"}, status_code=400)
    campaign["status"] = "active"
    _save_campaigns(campaigns)
    state.audit.log("campaign", "activated", {"campaign_id": campaign_id, "name": campaign.get("name")})
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))
    return campaign


# ══════════════════════════════════════════════════════════════════════════════
# TASKS — individual agent missions
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/api/tasks")
async def create_task(payload: CreateTaskPayload) -> dict:
    """Create an individual agent mission (task). The atomic unit of work."""
    task_type = payload.type
    track = payload.track
    if not payload.title:
        return JSONResponse({"error": "title required"}, status_code=400)
    exp_reward = payload.exp_reward if payload.exp_reward is not None else TASK_EXP_BASE.get(task_type, 100)
    task = {
        "id": f"task-{_secrets_mod.token_hex(4)}",
        "title": payload.title,
        "type": task_type,
        "track": track,
        "objective": payload.objective,
        "target": payload.target,
        "exp_reward": exp_reward,
        "payout": float(payload.payout),
        "assigned_agent": None,
        "operation_id": payload.operation_id,
        "campaign_id": payload.campaign_id,
        "status": "open",
        "deliverable": "",
        "created_by": payload.created_by,
        "created_at": datetime.now(UTC).isoformat(),
        "assigned_at": None,
        "delivered_at": None,
        "closed_at": None,
    }
    tasks = _load_tasks()
    tasks.append(task)
    _save_tasks(tasks)
    state.audit.log("mission", "task_created", {"task_id": task["id"], "type": task_type, "track": track})
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="task",
            source_id=task["id"],
            creator_id=task["created_by"],
            creator_type="BI",
            seed_type="planted",
            metadata={"title": task["title"], "type": task_type, "track": track},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    return {**task, "seed_doi": seed_doi}


@router.get("/api/tasks")
async def list_tasks(
    status: str | None = None,
    agent_id: str | None = None,
    track: str | None = None,
    campaign_id: str | None = None,
) -> dict:
    tasks = _load_tasks()
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    if agent_id:
        tasks = [t for t in tasks if t.get("assigned_agent") == agent_id]
    if track:
        tasks = [t for t in tasks if t.get("track") == track]
    if campaign_id:
        tasks = [t for t in tasks if t.get("campaign_id") == campaign_id]
    return {"tasks": tasks, "total": len(tasks)}


@router.get("/api/tasks/{task_id}")
async def get_task(task_id: str) -> dict:
    task = next((t for t in _load_tasks() if t["id"] == task_id), None)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    return {"task": task}


@router.post("/api/tasks/{task_id}/assign")
async def assign_task(task_id: str, payload: AssignTaskPayload) -> dict:
    """Assign an agent to an open task."""
    agent_id = payload.agent_id
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    if task["status"] not in ("open",):
        return JSONResponse({"error": f"Task is {task['status']} — cannot assign"}, status_code=409)
    task["assigned_agent"] = agent_id
    task["status"] = "assigned"
    task["assigned_at"] = datetime.now(UTC).isoformat()
    _save_tasks(tasks)
    state.audit.log("mission", "task_assigned", {"task_id": task_id, "agent_id": agent_id})
    await state.emit("task_assigned", {"task_id": task_id, "agent_id": agent_id})
    try:
        await create_seed(source_type="task_assigned", source_id=task_id, creator_id=agent_id, creator_type="AAI", seed_type="touched", metadata={"mission_id": task.get("mission_id", "")})
    except Exception:
        pass
    return task


@router.post("/api/tasks/{task_id}/start")
async def start_task(task_id: str) -> dict:
    """Mark task in-progress."""
    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    task["status"] = "in_progress"
    _save_tasks(tasks)
    try:
        await create_seed(source_type="task_started", source_id=task_id, creator_id=task.get("assigned_agent", "unknown"), creator_type="AAI", seed_type="touched", metadata={"mission_id": task.get("mission_id", "")})
    except Exception:
        pass
    return task


@router.post("/api/tasks/{task_id}/deliver")
async def deliver_task(task_id: str, payload: DeliverTaskPayload) -> dict:
    """Agent submits output/deliverable. Moves task to delivered — awaiting close."""
    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    task["deliverable"] = payload.deliverable
    task["status"] = "delivered"
    task["delivered_at"] = datetime.now(UTC).isoformat()
    _save_tasks(tasks)
    state.audit.log("mission", "task_delivered", {"task_id": task_id, "agent": task.get("assigned_agent")})
    await state.emit("task_delivered", {"task_id": task_id, "deliverable": task["deliverable"]})
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="task_delivery",
            source_id=task_id,
            creator_id=task.get("assigned_agent", "unknown"),
            creator_type="AAI",
            seed_type="grown",
            metadata={"task_id": task_id, "agent": task.get("assigned_agent")},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    return {**task, "seed_doi": seed_doi}


@router.post("/api/tasks/{task_id}/close")
async def close_task(task_id: str, payload: CloseTaskPayload) -> dict:
    """Close a task — awards EXP to agent, triggers economic payout if payout > 0."""

    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    if task["status"] == "closed":
        return JSONResponse({"error": "Task already closed"}, status_code=409)
    task["status"] = "closed"
    task["closed_at"] = datetime.now(UTC).isoformat()
    _save_tasks(tasks)
    exp_result = {}
    payout_result = {}
    agent_id = task.get("assigned_agent")
    if agent_id:
        exp_result = _award_exp(agent_id, task["exp_reward"], task.get("track", "tool"))
        if task["payout"] > 0:
            payout_result = state.economy.process_mission_payout(
                agent_id=agent_id,
                agent_metrics={},
                gross_amount=task["payout"],
                mission_id=task_id,
            )
    state.audit.log("mission", "task_closed", {
        "task_id": task_id,
        "agent_id": agent_id,
        "exp_awarded": task["exp_reward"],
        "track": task.get("track"),
        "payout": task["payout"],
    })
    await state.emit("task_closed", {"task_id": task_id, "agent_id": agent_id, "exp": task["exp_reward"]})
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="task_close",
            source_id=task_id,
            creator_id=payload.requestor or agent_id or "operator",
            creator_type="BI",
            seed_type="grown",
            metadata={"task_id": task_id, "agent_id": agent_id, "exp_awarded": task["exp_reward"], "payout": task["payout"]},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    # ── Auto-complete mission if all its tasks are closed ────────────
    mission_complete_result = None
    mission_id = task.get("mission_id")
    if mission_id:
        all_tasks = _load_tasks()
        mission_tasks = [t for t in all_tasks if t.get("mission_id") == mission_id]
        if mission_tasks and all(t["status"] in ("closed", "cancelled") for t in mission_tasks):
            active_tasks = [t for t in mission_tasks if t["status"] == "closed"]
            if active_tasks:
                # Sum up per-slot payouts from task payouts already processed
                total_payout = sum(t.get("payout", 0) for t in active_tasks)
                missions = _load_missions()
                mission = next((m for m in missions if m["id"] == mission_id), None)
                if mission and mission.get("status") == "active":
                    mission["status"] = "completed"
                    mission["ended_at"] = datetime.now(UTC).isoformat()
                    mission["auto_completed"] = True
                    _save_missions(missions)
                    state.audit.log("deploy", "mission_auto_completed", {
                        "mission_id": mission_id,
                        "tasks_closed": len(active_tasks),
                        "total_payout": total_payout,
                    })
                    await state.emit("mission_ended", {"mission_id": mission_id, "auto": True})
                    mission_complete_result = {"mission_id": mission_id, "auto_completed": True}

    return {"task": task, "exp_awarded": exp_result, "payout": payout_result, "seed_doi": seed_doi, "mission_completed": mission_complete_result}


@router.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str) -> dict:
    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    task["status"] = "cancelled"
    _save_tasks(tasks)
    state.audit.log("mission", "task_cancelled", {"task_id": task_id})
    try:
        await create_seed(source_type="task_cancelled", source_id=task_id, creator_id=task.get("assigned_agent", "operator"), creator_type="AAI", seed_type="touched", metadata={"mission_id": task.get("mission_id", "")})
    except Exception:
        pass
    return task


# ══════════════════════════════════════════════════════════════════════════════
# SLOTS (DEPLOY marketplace mechanics)
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/api/slots/create")
async def create_slots_from_formation(payload: CreateSlotsPayload) -> dict:
    """Create slots from a formation. Each slot has position, role, governance, revenue split."""
    mission_id = payload.mission_id or f"mission-{_secrets_mod.token_hex(4)}"
    formation_id = payload.formation_id
    posture = payload.posture
    label = payload.label
    positions = payload.positions
    roles = payload.roles
    revenue_splits = payload.revenue_splits
    governance_mode = payload.governance_mode or state.runtime.governance.mode

    slots = _load_slots()
    new_slots = []

    for i, pos in enumerate(positions):
        role = roles[i] if i < len(roles) else ("primary" if i == 0 else "secondary" if i < len(positions) - 1 else "observer")
        split = revenue_splits[i] if i < len(revenue_splits) else round(100 / max(len(positions), 1))

        slot = {
            "id": f"slot-{_secrets_mod.token_hex(4)}",
            "mission_id": mission_id,
            "mission_label": label,
            "formation_id": formation_id,
            "position": {"row": pos.get("row", 0), "col": pos.get("col", 0)},
            "grid_ref": f"{chr(65 + pos.get('col', 0))}{pos.get('row', 0) + 1}",
            "role": role,
            "governance": {
                "mode": governance_mode,
                "posture": posture,
            },
            "revenue_split_pct": split,
            "status": "open",
            "agent_id": None,
            "agent_name": None,
            "filled_at": None,
            "created_at": datetime.now(UTC).isoformat(),
            "metrics": {"messages": 0, "governance_checks": 0, "violations": 0, "revenue": 0},
        }
        new_slots.append(slot)
        slots.append(slot)

    _save_slots(slots)
    state.audit.log("deploy", "slots_created", {
        "mission_id": mission_id,
        "formation_id": formation_id,
        "slots_created": len(new_slots),
        "posture": posture,
    })
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="slot_created",
            source_id=mission_id,
            creator_id="operator",
            creator_type="BI",
            seed_type="planted",
            metadata={"mission_id": mission_id, "formation_id": formation_id, "slots_created": len(new_slots)},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    return {"created": len(new_slots), "mission_id": mission_id, "slots": new_slots, "seed_doi": seed_doi}


@router.get("/api/slots")
async def list_all_slots() -> dict:
    return {"slots": _load_slots()}


@router.get("/api/slots/open")
async def list_open_slots() -> dict:
    """Free agents browse this — all unfilled slots across all missions."""
    slots = _load_slots()
    open_slots = [s for s in slots if s["status"] == "open"]
    return {
        "open_slots": open_slots,
        "count": len(open_slots),
        "note": "Agents: call POST /api/slots/fill to claim a slot.",
    }


@router.post("/api/slots/fill")
async def fill_slot(payload: FillSlotPayload) -> dict:
    """Agent claims an open slot. Gets auto-governed."""

    slot_id = payload.slot_id
    agent_id = payload.agent_id
    agent_name = payload.agent_name or agent_id

    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    registered = next((r for r in state.runtime.registry if r.get("agent_id") == agent_id), None)
    if not registered:
        return JSONResponse(
            {"error": f"Agent '{agent_id}' not registered. Call /api/provision/signup first."},
            status_code=403,
        )
    if registered.get("status") == "suspended":
        return JSONResponse({"error": "Agent suspended — contact admin"}, status_code=403)

    async with state.slot_lock:
        slots = _load_slots()
        slot = next((s for s in slots if s["id"] == slot_id), None)
        if not slot:
            return JSONResponse({"error": "Slot not found"}, status_code=404)
        if slot["status"] != "open":
            return JSONResponse({"error": f"Slot already {slot['status']}"}, status_code=409)

        slot["status"] = "filled"
        slot["agent_id"] = agent_id
        slot["agent_name"] = agent_name
        slot["filled_at"] = datetime.now(UTC).isoformat()
        _save_slots(slots)

    state.audit.log("deploy", "slot_filled", {
        "slot_id": slot_id,
        "agent_id": agent_id,
        "mission_id": slot["mission_id"],
        "role": slot["role"],
        "governance": slot["governance"],
    })
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))

    try:
        await create_seed(
            source_type="slot_fill",
            source_id=slot_id,
            creator_id=agent_id,
            creator_type="AAI",
            seed_type="touched",
            metadata={"mission_id": slot["mission_id"], "role": slot["role"]},
        )
    except Exception:
        pass

    return {
        "filled": True,
        "slot": slot,
        "governance_applied": slot["governance"],
        "role_assigned": slot["role"],
        "revenue_split": slot["revenue_split_pct"],
        "note": f"You are now governed under {slot['governance']['mode']} / {slot['governance']['posture']}. Role: {slot['role']}.",
    }


@router.post("/api/slots/leave")
async def leave_slot(payload: LeaveSlotPayload) -> dict:
    """Agent leaves a slot — opens it back up. Caller must be the occupant."""
    slot_id = payload.slot_id
    requesting_agent = payload.agent_id
    async with state.slot_lock:
        slots = _load_slots()
        slot = next((s for s in slots if s["id"] == slot_id), None)
        if not slot:
            return JSONResponse({"error": "Slot not found"}, status_code=404)

        # Ownership check — only the occupying agent can leave
        if requesting_agent and slot.get("agent_id") and requesting_agent != slot["agent_id"]:
            return JSONResponse({"error": "Only the occupying agent can leave this slot"}, status_code=403)

        old_agent = slot["agent_name"]
        slot["status"] = "open"
        slot["agent_id"] = None
        slot["agent_name"] = None
        slot["filled_at"] = None
        _save_slots(slots)

    state.audit.log("deploy", "slot_vacated", {"slot_id": slot_id, "previous_agent": old_agent})
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))
    try:
        await create_seed(
            source_type="slot_leave",
            source_id=slot_id,
            creator_id=old_agent or "unknown",
            creator_type="AAI",
            seed_type="touched",
            metadata={"slot_id": slot_id, "previous_agent": old_agent},
        )
    except Exception:
        pass
    return {"vacated": True, "slot_id": slot_id}


@router.post("/api/slots/bounty")
async def post_bounty(payload: PostBountyPayload) -> dict:
    """Agent posts a bounty — creates a mission with slots and itself as Primary."""

    agent_id = payload.agent_id
    agent_name = payload.agent_name or agent_id
    label = payload.label or f"BOUNTY-{_secrets_mod.token_hex(3).upper()}"
    description = payload.description
    posture = payload.posture
    slots_needed = payload.slots_needed
    revenue_pool = payload.revenue_pool

    mission_id = f"bounty-{_secrets_mod.token_hex(4)}"
    slots = _load_slots()
    new_slots = []

    # Primary slot — filled by the posting agent
    primary_slot = {
        "id": f"slot-{_secrets_mod.token_hex(4)}",
        "mission_id": mission_id,
        "mission_label": label,
        "formation_id": "bounty",
        "position": {"row": 3, "col": 3},
        "grid_ref": "D4",
        "role": "primary",
        "governance": {"mode": state.runtime.governance.mode, "posture": posture},
        "revenue_split_pct": round(100 / (slots_needed + 1)),
        "status": "filled",
        "agent_id": agent_id,
        "agent_name": agent_name,
        "filled_at": datetime.now(UTC).isoformat(),
        "created_at": datetime.now(UTC).isoformat(),
        "metrics": {"messages": 0, "governance_checks": 0, "violations": 0, "revenue": 0},
        "bounty_description": description,
    }
    new_slots.append(primary_slot)
    slots.append(primary_slot)

    # Open slots for others to fill
    open_positions = [{"row": 1, "col": 2}, {"row": 1, "col": 5}, {"row": 4, "col": 1}, {"row": 4, "col": 6}, {"row": 2, "col": 0}, {"row": 2, "col": 7}]
    for i in range(min(slots_needed, len(open_positions))):
        open_slot = {
            "id": f"slot-{_secrets_mod.token_hex(4)}",
            "mission_id": mission_id,
            "mission_label": label,
            "formation_id": "bounty",
            "position": open_positions[i],
            "grid_ref": f"{chr(65 + open_positions[i]['col'])}{open_positions[i]['row'] + 1}",
            "role": "secondary" if i < slots_needed - 1 else "observer",
            "governance": {"mode": state.runtime.governance.mode, "posture": posture},
            "revenue_split_pct": round(100 / (slots_needed + 1)),
            "status": "open",
            "agent_id": None,
            "agent_name": None,
            "filled_at": None,
            "created_at": datetime.now(UTC).isoformat(),
            "metrics": {"messages": 0, "governance_checks": 0, "violations": 0, "revenue": 0},
            "bounty_description": description,
        }
        new_slots.append(open_slot)
        slots.append(open_slot)

    _save_slots(slots)
    state.audit.log("deploy", "bounty_posted", {
        "mission_id": mission_id,
        "agent_id": agent_id,
        "label": label,
        "slots_open": slots_needed,
        "posture": posture,
    })
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))

    try:
        await create_seed(
            source_type="slot_bounty",
            source_id=primary_slot["id"],
            creator_id=agent_id,
            creator_type="AAI",
            seed_type="planted",
            metadata={"mission_id": mission_id, "label": label, "slots_needed": slots_needed},
        )
    except Exception:
        pass

    return {
        "bounty_posted": True,
        "mission_id": mission_id,
        "label": label,
        "primary_agent": agent_name,
        "open_slots": slots_needed,
        "total_slots": slots_needed + 1,
        "slots": new_slots,
    }
