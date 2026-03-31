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

from app.deps import state
from app.seeds import create_seed

router = APIRouter(tags=["metrics"])

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


# ── Metrics helpers ──────────────────────────────────────────────────────────

_metrics_path: Path | None = None


def _get_metrics_path() -> Path:
    global _metrics_path
    if _metrics_path is None:
        _metrics_path = state.root / "data" / "metrics.json"
    return _metrics_path


def _load_metrics() -> dict:
    p = _get_metrics_path()
    if p.exists():
        return json.loads(p.read_text())
    return {"agents": {}, "missions": {}, "financial": {"revenue": 0, "costs": 0, "transactions": []}}


def _save_metrics(m: dict) -> None:
    _atomic_write(_get_metrics_path(), json.dumps(m, indent=2))


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/api/metrics/agent")
async def log_agent_metric(payload: dict) -> dict:
    """Log a metric for an agent — mission result, compliance event, revenue."""
    m = _load_metrics()
    agent_id = payload.get("agent_id", "unknown")
    if agent_id not in m["agents"]:
        m["agents"][agent_id] = {
            "name": payload.get("name", agent_id),
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
    event = payload.get("event", "")

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
        amount = payload.get("amount", 0)
        agent["revenue_generated"] += amount
        m["financial"]["revenue"] += amount
        m["financial"]["transactions"].append({
            "agent_id": agent_id,
            "type": "revenue",
            "amount": amount,
            "description": payload.get("description", ""),
            "timestamp": datetime.now(UTC).isoformat(),
        })
    elif event == "cost":
        amount = payload.get("amount", 0)
        agent["costs_incurred"] += amount
        m["financial"]["costs"] += amount
        m["financial"]["transactions"].append({
            "agent_id": agent_id,
            "type": "cost",
            "amount": amount,
            "description": payload.get("description", ""),
            "timestamp": datetime.now(UTC).isoformat(),
        })

    agent["last_active"] = datetime.now(UTC).isoformat()
    _save_metrics(m)
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
    m = _load_metrics()

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
async def log_mission_metric(payload: dict) -> dict:
    """Log mission-level metrics."""
    m = _load_metrics()
    mission_id = payload.get("mission_id", "unknown")
    if mission_id not in m["missions"]:
        m["missions"][mission_id] = {
            "label": payload.get("label", ""),
            "posture": payload.get("posture", ""),
            "formation": payload.get("formation", ""),
            "started": datetime.now(UTC).isoformat(),
            "ended": None,
            "agents_deployed": payload.get("agents_deployed", 0),
            "governance_blocks": 0,
            "messages": 0,
            "revenue": 0,
            "costs": 0,
            "outcome": "active",
        }

    mission = m["missions"][mission_id]
    event = payload.get("event", "")

    if event == "ended":
        mission["ended"] = datetime.now(UTC).isoformat()
        mission["outcome"] = payload.get("outcome", "completed")
    elif event == "governance_block":
        mission["governance_blocks"] += 1
    elif event == "message":
        mission["messages"] += 1
    elif event == "revenue":
        mission["revenue"] += payload.get("amount", 0)
    elif event == "cost":
        mission["costs"] += payload.get("amount", 0)

    _save_metrics(m)
    seed_doi = None
    if event == "ended":
        try:
            seed_result = await create_seed(
                source_type="mission_metric",
                source_id=mission_id,
                creator_id="operator",
                creator_type="BI",
                seed_type="planted",
                metadata={"mission_id": mission_id, "outcome": payload.get("outcome", "completed")},
            )
            seed_doi = seed_result.get("doi") if seed_result else None
        except Exception:
            pass
    return {"logged": True, "mission_id": mission_id, "event": event, "seed_doi": seed_doi}
