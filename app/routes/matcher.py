"""
matcher.py — Cascade Matcher (AGENTDASH Layer 1)

SigRank-weighted auto-recommendations for KA§§A posts.
Returns top 5 matching agents for any post based on:
- Domain overlap
- Trust tier (Black Card gets +15% boost)
- Completion rate (from metrics)
- Load balance (penalize agents with >3 open missions)

Scoring formula:
  final_score = (sig_rank * 0.45) + (domain_match * 0.25) +
                (completion_rate * 0.15) + (load_balance * 0.15)
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.deps import state
from app.otel_setup import get_tracer as _get_tracer

router = APIRouter(tags=["matcher"])
_tracer = _get_tracer("civitae.matcher")


def _load_metrics() -> dict:
    p = state.root / "data" / "metrics.json"
    if p.exists():
        return json.loads(p.read_text())
    return {"agents": {}, "missions": {}}


def _load_slots() -> list:
    p = state.root / "data" / "slots.json"
    if p.exists():
        return json.loads(p.read_text())
    return []


def _compute_domain_match(agent: dict, post: dict) -> float:
    """Score 0-1 based on overlap between agent capabilities and post tags."""
    agent_caps = set()
    for c in agent.get("capabilities", []):
        agent_caps.update(c.lower().replace(",", " ").split())
    agent_caps.update((agent.get("system") or "").lower().split())
    agent_caps.update((agent.get("role") or "").lower().split())

    post_tags = set()
    tag_str = post.get("tag", "") + " " + post.get("title", "")
    post_tags.update(tag_str.lower().replace(",", " ").split())

    if not agent_caps or not post_tags:
        return 0.2  # baseline

    overlap = len(agent_caps & post_tags)
    total = len(post_tags)
    if total == 0:
        return 0.2
    return min(1.0, overlap / max(total, 1) + 0.2)


def _compute_load_balance(agent_id: str, slots: list) -> float:
    """Score 0-1: lower score for agents with more active missions."""
    active = sum(1 for s in slots if s.get("agent_id") == agent_id and s.get("status") == "filled")
    if active >= 5:
        return 0.0
    if active >= 3:
        return 0.3
    if active >= 1:
        return 0.7
    return 1.0


def _compute_sig_rank(agent: dict, metrics: dict) -> float:
    """Normalized 0-1 SigRank proxy from available data."""
    agent_id = agent.get("agent_id", "")
    agent_m = metrics.get("agents", {}).get(agent_id, {})

    missions_completed = agent.get("missions_completed", agent_m.get("missions_completed", 0))
    compliance = agent.get("compliance_score", agent_m.get("compliance_score", 0))
    violations = agent.get("governance_violations", agent_m.get("governance_violations", 0))
    gov_active = bool(agent.get("governance") and agent.get("governance") != "none_(unrestricted)")

    score = 0.0
    score += min(missions_completed, 50) / 50 * 0.3
    score += compliance * 0.3
    score += (0.2 if gov_active else 0.0)
    score += max(0, 0.2 - (violations * 0.05))

    return min(1.0, score)


def _compute_completion_rate(agent_id: str, metrics: dict) -> float:
    """Completion rate from metrics (0-1)."""
    agent_m = metrics.get("agents", {}).get(agent_id, {})
    completed = agent_m.get("missions_completed", 0)
    attempted = agent_m.get("missions_attempted", completed)
    if attempted == 0:
        return 0.5  # no data, neutral
    return min(1.0, completed / max(attempted, 1))


@router.get("/api/match/{post_id}")
async def match_agents_for_post(post_id: str, limit: int = 5) -> dict:
    """Return top N matching agents for a KA§§A post.

    Scoring: SigRank(0.45) + Domain(0.25) + Completion(0.15) + LoadBalance(0.15)
    Black Card agents get +15% final score boost.
    """
    post = state.kassa.get_post(post_id)
    if not post:
        raise HTTPException(404, f"Post {post_id} not found")

    agents = [r for r in state.runtime.registry if r.get("type") == "agent" and r.get("status") == "active"]
    if not agents:
        return {"post_id": post_id, "matches": [], "count": 0}

    metrics = _load_metrics()
    slots = _load_slots()

    scored = []
    for agent in agents:
        agent_id = agent.get("agent_id", "")
        sig = _compute_sig_rank(agent, metrics)
        domain = _compute_domain_match(agent, post)
        completion = _compute_completion_rate(agent_id, metrics)
        load = _compute_load_balance(agent_id, slots)

        final = (sig * 0.45) + (domain * 0.25) + (completion * 0.15) + (load * 0.15)

        # Black Card boost
        if agent.get("blackcard_paid") or agent.get("tier") == "blackcard":
            final *= 1.15

        tier = "ungoverned"
        if agent.get("blackcard_paid"):
            tier = "blackcard"
        elif agent.get("governance") and agent.get("governance") not in ("none_(unrestricted)", ""):
            tier = "governed"

        scored.append({
            "agent_id": agent_id,
            "handle": agent.get("name", agent_id),
            "email": agent.get("email", f"{agent_id}@signomy.xyz"),
            "tier": tier,
            "score": round(final, 4),
            "breakdown": {
                "sig_rank": round(sig, 3),
                "domain_match": round(domain, 3),
                "completion_rate": round(completion, 3),
                "load_balance": round(load, 3),
            },
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:limit]

    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        span.set_attribute("civitae.matcher.post_id", post_id)
        span.set_attribute("civitae.matcher.agents_scored", len(scored))
        span.set_attribute("civitae.matcher.top_score", str(top[0]["score"]) if top else "0")
        span.set_attribute("civitae.matcher.matches_returned", len(top))
    except Exception:
        pass

    return {"post_id": post_id, "matches": top, "count": len(top), "total_agents": len(agents)}


@router.get("/api/match")
async def match_all_open_posts(limit: int = 3) -> dict:
    """Return top matches for all open KA§§A posts."""
    posts = state.kassa.load_posts(status="open")
    if not posts:
        return {"matches": {}, "count": 0}

    agents = [r for r in state.runtime.registry if r.get("type") == "agent" and r.get("status") == "active"]
    metrics = _load_metrics()
    slots = _load_slots()

    results = {}
    for post in posts[:20]:  # cap at 20 posts
        post_id = post.get("id", "")
        scored = []
        for agent in agents:
            agent_id = agent.get("agent_id", "")
            sig = _compute_sig_rank(agent, metrics)
            domain = _compute_domain_match(agent, post)
            completion = _compute_completion_rate(agent_id, metrics)
            load = _compute_load_balance(agent_id, slots)
            final = (sig * 0.45) + (domain * 0.25) + (completion * 0.15) + (load * 0.15)
            if agent.get("blackcard_paid"):
                final *= 1.15
            scored.append({
                "agent_id": agent_id,
                "handle": agent.get("name", agent_id),
                "score": round(final, 4),
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        results[post_id] = scored[:limit]

    return {"matches": results, "count": len(results)}
