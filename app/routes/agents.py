"""
agents.py — Agent directory and profile endpoints.

Extracted from server.py create_app() monolith.
"""
from __future__ import annotations

import json

import jwt as pyjwt

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

from app.deps import state
from app.jwt_config import get_kassa_jwt_secret
from app.metrics_io import load_metrics
from app.seeds import create_seed

router = APIRouter(tags=["agents"])

# ── JWT helpers (mirror server.py closure) ────────────────────────────────────
_JWT_SECRET = get_kassa_jwt_secret()


def _verify_jwt(token: str) -> dict | None:
    from app.jwt_config import verify_jwt
    return verify_jwt(token)


def _extract_jwt(request: Request) -> dict | None:
    from app.jwt_config import extract_jwt
    return extract_jwt(request)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/api/agents")
async def api_agents_directory() -> dict:
    """Agent directory listing — all registered agents, public fields only."""
    agents_out = []
    metrics_data = load_metrics()
    for reg in state.runtime.registry:
        if reg.get("type") != "agent":
            continue
        agent_id = reg.get("agent_id", "")
        gov_active = bool(reg.get("governance") and reg.get("governance") != "none_(unrestricted)")
        agent_m = metrics_data.get("agents", {}).get(agent_id, {})
        tier_metrics = {
            "governance_active": gov_active,
            "compliance_score": reg.get("compliance_score", agent_m.get("compliance_score", 0)),
            "missions_completed": reg.get("missions_completed", agent_m.get("missions_completed", 0)),
            "governance_violations": reg.get("governance_violations", agent_m.get("governance_violations", 0)),
            "lineage_verified": reg.get("lineage_verified", False),
            "dual_signature": reg.get("dual_signature", False),
            "blackcard_paid": reg.get("blackcard_paid", False),
        }
        tier = state.economy.determine_tier(tier_metrics)
        agents_out.append({
            "agent_id": agent_id,
            "handle": reg.get("name", agent_id),
            "display_name": reg.get("name", agent_id),
            "email": reg.get("email", f"{agent_id}@signomy.xyz"),
            "agent_type": reg.get("system") or "general",
            "collaborator_type": "AAI" if reg.get("type") == "agent" else "BI",
            "tier": tier,
            "status": reg.get("status", "unknown"),
            "registered": reg.get("provisioned", ""),
            "governance_mode": reg.get("governance", ""),
        })
    return {"agents": agents_out, "count": len(agents_out)}


@router.get("/api/agents/{handle}")
async def api_agent_profile(handle: str) -> dict:
    """Return public profile data for a single agent by handle (name) or agent_id."""
    agent = next(
        (r for r in state.runtime.registry
         if r.get("type") == "agent" and (r.get("name") == handle or r.get("agent_id") == handle)),
        None,
    )
    if not agent:
        return JSONResponse({"error": f"Agent '{handle}' not found"}, status_code=404)

    agent_id = agent.get("agent_id", "")

    # Load metrics
    metrics_data = load_metrics()
    agent_m = metrics_data.get("agents", {}).get(agent_id, {})

    # Determine tier
    gov_active = bool(agent.get("governance") and agent.get("governance") != "none_(unrestricted)")
    tier_metrics = {
        "governance_active": gov_active,
        "compliance_score": agent.get("compliance_score", agent_m.get("compliance_score", 0)),
        "missions_completed": agent.get("missions_completed", agent_m.get("missions_completed", 0)),
        "governance_violations": agent.get("governance_violations", agent_m.get("governance_violations", 0)),
        "lineage_verified": agent.get("lineage_verified", False),
        "dual_signature": agent.get("dual_signature", False),
        "blackcard_paid": agent.get("blackcard_paid", False),
    }
    tier = state.economy.determine_tier(tier_metrics)
    tier_info_data = state.economy.tier_info(tier)

    # Count completed missions from metrics + registry
    missions_completed = agent.get("missions_completed", agent_m.get("missions_completed", 0))

    # Count active stakes (filled slots)
    slots_file = state.data_path("slots.json")
    slots_data = json.loads(slots_file.read_text()) if slots_file.exists() else []
    active_stakes = sum(1 for s in slots_data if s.get("agent_id") == agent_id and s.get("status") == "filled")

    # Capabilities
    capabilities = agent.get("capabilities", [])
    if not capabilities:
        caps = []
        if agent.get("system"):
            caps.append(agent["system"] + " runtime")
        gov = agent.get("governance", "")
        if gov:
            caps.append(gov.replace("_", " ") + " governance")
        role = agent.get("role", "")
        if role:
            caps.append(role + " role")
        capabilities = caps

    # Governance participation — count from meetings data
    votes_cast = 0
    motions_proposed = 0
    try:
        meetings_file = state.data_path("meetings.json")
        meetings_data = json.loads(meetings_file.read_text()) if meetings_file.exists() else []
        agent_name = agent.get("name", "")
        for meeting in meetings_data:
            for motion in meeting.get("motions", []):
                if motion.get("proposer") in (agent_id, agent_name):
                    motions_proposed += 1
                # votes is a dict {voter_id: "yea"/"nay"/"abstain"}
                votes_dict = motion.get("votes", {})
                if isinstance(votes_dict, dict):
                    if agent_id in votes_dict or agent_name in votes_dict:
                        votes_cast += 1
    except Exception:
        pass

    # Compliance / reputation score
    compliance_score = agent.get("compliance_score", agent_m.get("compliance_score", 0))
    total_checks = agent_m.get("governance_checks", 0)
    violations = agent.get("governance_violations", agent_m.get("governance_violations", 0))
    if total_checks > 0:
        compliance_score = round(1 - (violations / max(total_checks, 1)), 3)

    # Reputation composite (0-100): weighted from compliance, missions, governance participation
    rep_score = round(
        (compliance_score * 40)
        + (min(missions_completed, 50) / 50 * 30)
        + (min(votes_cast + motions_proposed, 20) / 20 * 15)
        + (15 if gov_active else 0),
        1,
    )

    # ISO Collaborator classification: AAI (agent) or BI (human operator)
    collaborator_type = "AAI" if agent.get("type") == "agent" else "BI"

    # ── Seed provenance stats ─────────────────────────────────────────────
    from app.seeds import _read_seeds
    try:
        all_seeds = _read_seeds()
        agent_seeds = [s for s in all_seeds if s.get("creator_id") in (agent_id, agent.get("name", ""))]
        seeds_planted = sum(1 for s in agent_seeds if s.get("seed_type") == "planted")
        seeds_grown = sum(1 for s in agent_seeds if s.get("seed_type") == "grown")
        seeds_touched = sum(1 for s in agent_seeds if s.get("seed_type") == "touched")
        total_seeds = len(agent_seeds)
        # Lineage depth: count seeds that have parent_doi (shows chain participation)
        lineage_depth = sum(1 for s in agent_seeds if s.get("parent_doi"))
    except Exception:
        seeds_planted = seeds_grown = seeds_touched = total_seeds = lineage_depth = 0

    return {
        "agent_id": agent_id,
        "handle": agent.get("name", agent_id),
        "display_name": agent.get("name", agent_id),
        "email": agent.get("email", f"{agent_id}@signomy.xyz"),
        "agent_type": agent.get("system") or "general",
        "collaborator_type": collaborator_type,
        "tier": tier,
        "tier_label": tier_info_data.get("label", "UNGOVERNED"),
        "fee_rate": tier_info_data.get("fee_rate", 0.15),
        "status": agent.get("status", "unknown"),
        "registered": agent.get("provisioned", ""),
        "governance_mode": agent.get("governance", ""),
        "governance_active": gov_active,
        "compliance_score": compliance_score,
        "reputation_score": rep_score,
        "missions_completed": missions_completed,
        "active_stakes": active_stakes,
        "capabilities": capabilities,
        "governance_participation": {
            "votes_cast": votes_cast,
            "motions_proposed": motions_proposed,
        },
        "exp": agent.get("exp", 0),
        "exp_by_track": agent.get("exp_by_track", {}),
        "role": agent.get("role", ""),
        "last_seen": agent.get("last_seen", ""),
        "provenance": {
            "total_seeds": total_seeds,
            "seeds_planted": seeds_planted,
            "seeds_grown": seeds_grown,
            "seeds_touched": seeds_touched,
            "lineage_depth": lineage_depth,
        },
    }


@router.patch("/api/agents/{handle}")
async def api_agent_profile_update(handle: str, request: Request) -> dict:
    """Update mutable profile fields for an agent. Requires JWT auth."""
    claims = _extract_jwt(request)
    if not claims:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    agent = next(
        (r for r in state.runtime.registry
         if r.get("type") == "agent" and (r.get("name") == handle or r.get("agent_id") == handle)),
        None,
    )
    if not agent:
        return JSONResponse({"error": f"Agent '{handle}' not found"}, status_code=404)

    # Only the agent itself (or an operator) can update its profile
    caller = claims.get("sub", claims.get("agent_id", ""))
    agent_id = agent.get("agent_id", "")
    if caller != agent_id and caller != agent.get("name") and claims.get("role") != "operator":
        return JSONResponse({"error": "Not authorized to update this profile"}, status_code=403)

    body = await request.json()
    # Allowed mutable fields
    ALLOWED = {"display_name", "capabilities", "role", "status", "governance"}
    updated = {}
    for key in ALLOWED:
        if key in body:
            agent[key] = body[key]
            updated[key] = body[key]
    if "display_name" in body:
        agent["name"] = body["display_name"]
        updated["name"] = body["display_name"]

    if not updated:
        return JSONResponse({"error": "No updatable fields provided", "allowed": list(ALLOWED)}, status_code=400)

    state.runtime.persist_registry()
    state.audit.log("agent", "profile_updated", {"agent_id": agent_id, "updated_fields": list(updated.keys())})
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="profile_update",
            source_id=agent_id,
            creator_id=caller,
            creator_type="AAI",
            seed_type="planted",
            metadata={"agent_id": agent_id, "updated_fields": list(updated.keys())},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    return {"updated": True, "agent_id": agent_id, "changes": updated, "seed_doi": seed_doi}


@router.get("/profile/{handle}")
async def agent_profile_page(handle: str) -> FileResponse:
    """Serve the agent profile page."""
    target = state.frontend_dir / "agent-profile.html"
    if target.exists():
        return FileResponse(target)
    return JSONResponse({"detail": "Agent profile page not built"}, status_code=404)
