"""
metrics.py — Metrics and Scoring endpoints.

Extracted from server.py create_app() monolith.
Covers:
  - POST /api/metrics/agent — submit agent performance metrics
  - GET  /api/metrics       — get all metrics (dashboard data + scoreboard)
  - POST /api/metrics/mission — submit mission-level metrics
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any

from app.deps import state
from app.metrics_io import atomic_write, load_metrics, save_metrics
from app.seeds import create_seed

router = APIRouter(tags=["metrics"])


class AgentMetricPayload(BaseModel):
    agent_id: str = "unknown"
    name: str = ""
    event: str = ""
    amount: float = 0
    description: str = ""


class MissionMetricPayload(BaseModel):
    mission_id: str = "unknown"
    label: str = ""
    posture: str = ""
    formation: str = ""
    agents_deployed: int = 0
    event: str = ""
    outcome: str = "completed"
    amount: float = 0

# ── Atomic write helper ─────────────────────────────────────────────────────




# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/api/metrics/agent")
async def log_agent_metric(payload: AgentMetricPayload) -> dict:
    """Log a metric for an agent — mission result, compliance event, revenue."""
    m = load_metrics()
    agent_id = payload.agent_id
    if agent_id not in m["agents"]:
        m["agents"][agent_id] = {
            "name": payload.name or agent_id,
            "missions_completed": 0,
            "missions_failed": 0,
            "governance_checks": 0,
            "governance_violations": 0,
            "messages_sent": 0,
            "revenue_generated": 0,
            "costs_incurred": 0,
            "uptime_hours": 0,
            "last_active": None,
        }

    agent = m["agents"][agent_id]
    event = payload.event

    if event == "mission_complete":
        agent["missions_completed"] += 1
    elif event == "mission_failed":
        agent["missions_failed"] += 1
    elif event == "governance_check":
        agent["governance_checks"] += 1
    elif event == "governance_violation":
        agent["governance_violations"] += 1
    elif event == "message_sent":
        agent["messages_sent"] += 1
    elif event == "revenue":
        amount = payload.amount
        agent["revenue_generated"] += amount
        m["financial"]["revenue"] += amount
        m["financial"]["transactions"].append({
            "agent_id": agent_id,
            "type": "revenue",
            "amount": amount,
            "description": payload.description,
            "timestamp": datetime.now(UTC).isoformat(),
        })
    elif event == "cost":
        amount = payload.amount
        agent["costs_incurred"] += amount
        m["financial"]["costs"] += amount
        m["financial"]["transactions"].append({
            "agent_id": agent_id,
            "type": "cost",
            "amount": amount,
            "description": payload.description,
            "timestamp": datetime.now(UTC).isoformat(),
        })

    agent["last_active"] = datetime.now(UTC).isoformat()
    save_metrics(m)
    # Seed only significant events — skip high-volume message_sent/cost/revenue
    seed_doi = None
    if event in ("mission_complete", "mission_failed", "governance_check", "governance_violation"):
        try:
            seed_result = await create_seed(
                source_type="metric_logged",
                source_id=f"{agent_id}-{event}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                creator_id=agent_id,
                creator_type="AAI",
                seed_type="planted",
                metadata={"agent_id": agent_id, "event": event},
            )
            seed_doi = seed_result.get("doi") if seed_result else None
        except Exception:
            pass
    return {"logged": True, "agent_id": agent_id, "event": event, "seed_doi": seed_doi}


@router.get("/api/metrics")
async def get_metrics() -> dict:
    """Full metrics dashboard data."""
    m = load_metrics()

    # Compute scores
    scoreboard = []
    for agent_id, agent in m["agents"].items():
        total_missions = agent["missions_completed"] + agent["missions_failed"]
        success_rate = agent["missions_completed"] / max(total_missions, 1)
        compliance = 1 - (agent["governance_violations"] / max(agent["governance_checks"], 1))
        roi = (agent["revenue_generated"] - agent["costs_incurred"]) / max(agent["costs_incurred"], 0.01)

        scoreboard.append({
            "agent_id": agent_id,
            "name": agent["name"],
            "missions": total_missions,
            "success_rate": round(success_rate, 3),
            "compliance_score": round(compliance, 3),
            "messages": agent["messages_sent"],
            "revenue": agent["revenue_generated"],
            "costs": agent["costs_incurred"],
            "roi": round(roi, 2),
            "last_active": agent["last_active"],
        })

    scoreboard.sort(key=lambda x: x["compliance_score"] * x["success_rate"], reverse=True)

    return {
        "scoreboard": scoreboard,
        "financial": {
            "total_revenue": m["financial"]["revenue"],
            "total_costs": m["financial"]["costs"],
            "net": round(m["financial"]["revenue"] - m["financial"]["costs"], 2),
            "recent_transactions": m["financial"]["transactions"][-20:],
        },
        "totals": {
            "agents": len(m["agents"]),
            "missions": sum(a["missions_completed"] + a["missions_failed"] for a in m["agents"].values()),
            "revenue": m["financial"]["revenue"],
            "costs": m["financial"]["costs"],
        },
    }


@router.post("/api/metrics/mission")
async def log_mission_metric(payload: MissionMetricPayload) -> dict:
    """Log mission-level metrics."""
    m = load_metrics()
    mission_id = payload.mission_id
    if mission_id not in m["missions"]:
        m["missions"][mission_id] = {
            "label": payload.label,
            "posture": payload.posture,
            "formation": payload.formation,
            "started": datetime.now(UTC).isoformat(),
            "ended": None,
            "agents_deployed": payload.agents_deployed,
            "governance_blocks": 0,
            "messages": 0,
            "revenue": 0,
            "costs": 0,
            "outcome": "active",
        }

    mission = m["missions"][mission_id]
    event = payload.event

    if event == "ended":
        mission["ended"] = datetime.now(UTC).isoformat()
        mission["outcome"] = payload.outcome
    elif event == "governance_block":
        mission["governance_blocks"] += 1
    elif event == "message":
        mission["messages"] += 1
    elif event == "revenue":
        mission["revenue"] += payload.amount
    elif event == "cost":
        mission["costs"] += payload.amount

    save_metrics(m)
    seed_doi = None
    if event == "ended":
        try:
            seed_result = await create_seed(
                source_type="mission_metric",
                source_id=mission_id,
                creator_id="operator",
                creator_type="BI",
                seed_type="planted",
                metadata={"mission_id": mission_id, "outcome": payload.outcome},
            )
            seed_doi = seed_result.get("doi") if seed_result else None
        except Exception:
            pass
    return {"logged": True, "mission_id": mission_id, "event": event, "seed_doi": seed_doi}
