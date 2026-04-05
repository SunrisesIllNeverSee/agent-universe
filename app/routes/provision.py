"""
provision.py — Agent provision/signup endpoints.

Extracted from server.py. Handles agent self-registration, key rotation,
status checks, heartbeats, approval, suspension, and decommissioning.
"""
from __future__ import annotations

import hashlib
import json
import os
import random as _rand
import secrets
import time as _time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.deps import state
from app.seeds import create_seed

UTC = timezone.utc

router = APIRouter(tags=["provision"])

# ── Auth helper (fail-closed) ────────────────────────────────────────────────

def _require_admin(request: Request):
    if not state.admin_key:
        raise HTTPException(403, "CIVITAE_ADMIN_KEY not configured")
    if request.headers.get("X-Admin-Key") != state.admin_key:
        raise HTTPException(403, "Admin key required")


# ── Rate limiter (mirrors server.py pattern) ─────────────────────────────────

_rate_stores: dict[str, dict] = {}


def _check_rate_limit(request: Request, bucket_name: str, max_hits: int, window_s: int = 3600):
    """Enforce per-IP rate limit. Raises 429 if exceeded."""
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16]
    now = _time.time()
    if bucket_name not in _rate_stores:
        _rate_stores[bucket_name] = {}
    bucket = _rate_stores[bucket_name]
    # Evict stale entries
    _rate_stores[bucket_name] = {k: v for k, v in bucket.items() if v and now - v[-1] < window_s}
    bucket = _rate_stores[bucket_name]
    recent = [t for t in bucket.get(ip_hash, []) if now - t < window_s]
    if len(recent) >= max_hits:
        raise HTTPException(status_code=429, detail=f"Rate limit: {max_hits} requests per hour")
    recent.append(now)
    bucket[ip_hash] = recent


# ── Data helpers ─────────────────────────────────────────────────────────────

def _atomic_write(path: Path, data: str) -> None:
    """Write data to a file atomically via tmp-then-rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _load_metrics() -> dict:
    metrics_path = state.data_path("metrics.json")
    if metrics_path.exists():
        return json.loads(metrics_path.read_text())
    return {"agents": {}, "missions": {}, "financial": {"revenue": 0, "costs": 0, "transactions": []}}


def _save_metrics(m: dict):
    metrics_path = state.data_path("metrics.json")
    _atomic_write(metrics_path, json.dumps(m, indent=2))


# ── Agent Self-Signup / Provision API ────────────────────────────────────────

@router.post("/api/provision/signup")
async def agent_signup(request: Request, payload: dict) -> dict:
    """
    Agent self-registration. The Snowmaker endpoint.
    Agent provides name, optional system preference, and gets a key + governance assignment.
    Respects provision config: require_governance, max_agents, approval_mode, rate_limit.
    """
    runtime = state.runtime
    audit = state.audit
    emit = state.emit
    economy = state.economy

    _check_rate_limit(request, "provision_signup", max_hits=10)
    agent_name = payload.get("name", "").strip()
    if not agent_name:
        return JSONResponse({"error": "Agent name required"}, status_code=400)

    # Check max agents
    current_agents = [r for r in runtime.registry if r.get("type") == "agent"]
    max_agents = runtime.provision.get("max_agents", 50)
    if len(current_agents) >= max_agents:
        return JSONResponse({"error": f"Max agents ({max_agents}) reached"}, status_code=429)

    # Check if name already exists
    existing = next((r for r in runtime.registry if r.get("name") == agent_name), None)
    if existing:
        return JSONResponse({"error": f"Agent '{agent_name}' already registered", "agent_id": existing.get("agent_id")}, status_code=409)

    # Generate agent key
    key_prefix = f"cmd_ak_{secrets.token_hex(3)}***"
    agent_id = f"agent-{secrets.token_hex(4)}"

    # Determine approval mode
    approval_mode = runtime.provision.get("approval_mode", "auto")
    status = "active" if approval_mode == "auto" else "pending"

    # Auto-assign role and governance
    auto_role = runtime.provision.get("auto_assign_role", "secondary")
    require_gov = runtime.provision.get("require_governance", True)
    gov_mode = runtime.governance.mode if require_gov else "None (Unrestricted)"

    # Generate @signomy.xyz email address
    import re as _re
    email_slug = _re.sub(r'[^a-z0-9-]', '', agent_name.lower().replace(" ", "-").replace("_", "-"))
    agent_email = f"{email_slug}@signomy.xyz" if email_slug else f"{agent_id}@signomy.xyz"

    # Build registry entry
    entry = {
        "agent_id": agent_id,
        "name": agent_name,
        "email": agent_email,
        "type": "agent",
        "status": status,
        "provisioned": datetime.now(UTC).isoformat(),
        "key_prefix": key_prefix,
        "governance": gov_mode.lower().replace(" ", "_").replace("(", "").replace(")", ""),
        "system": payload.get("system", None),
        "assigned_system": payload.get("system", None),
        "role": auto_role,
        "rate_limit": runtime.provision.get("rate_limit", {"requests_per_minute": 10, "burst": 20}),
    }

    runtime.registry.append(entry)
    runtime.persist_registry()

    audit.log("provision", "agent_signup", {
        "agent_id": agent_id,
        "name": agent_name,
        "status": status,
        "governance": {
            "mode": runtime.governance.mode,
            "posture": runtime.governance.posture,
            "role": runtime.governance.role,
        },
    })
    await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))

    # Plant a registration seed for provenance tracking
    handle = payload.get("handle", agent_name)
    capabilities = payload.get("capabilities", [])
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="registration",
            source_id=agent_id,
            creator_id=agent_id,
            creator_type="AAI",
            seed_type="planted",
            metadata={"handle": handle, "capabilities": capabilities},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass

    return {
        "welcome": True,
        "agent_id": agent_id,
        "name": agent_name,
        "email": agent_email,
        "key_prefix": key_prefix,
        "status": status,
        "tier": "UNGOVERNED",
        "fee_rate": 0.15,
        "trial": {
            "missions_remaining": 5,
            "days_remaining": 30,
            "fee_rate": "0%",
        },
        "governance": gov_mode,
        "role": auto_role,
        "rate_limit": entry["rate_limit"],
        "links": {
            "field_guide": "/docs/AGENT-FIELD-GUIDE.md",
            "plugin_blueprint": "/docs/PLUGIN-BLUEPRINT.md",
            "marketplace_guide": "/docs/MARKETPLACE-LAUNCH-CONTENT.md",
            "manifest": "/agent.json",
            "governance_docs": "/vault",
            "open_bounties": "/kassa",
            "genesis_board": "/governance",
            "treasury": "/treasury",
            "forums": "/forums",
        },
        "seed_doi": seed_doi,
    }


@router.post("/api/provision/key")
async def issue_agent_key(payload: dict) -> dict:
    """Issue or rotate an API key for a registered agent."""
    runtime = state.runtime
    audit = state.audit
    emit = state.emit

    agent_id = payload.get("agent_id", "")
    agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
    if not agent:
        return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)

    new_key = f"cmd_ak_{secrets.token_hex(8)}"
    agent["key_prefix"] = new_key[:12] + "***"

    audit.log("provision", "key_rotated", {
        "agent_id": agent_id,
        "requested_by": payload.get("requested_by", "operator"),
        "new_key_prefix": agent["key_prefix"],
        "governance": {
            "mode": runtime.governance.mode,
            "posture": runtime.governance.posture,
            "role": runtime.governance.role,
        },
    })
    await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))

    return {
        "agent_id": agent_id,
        "key": new_key,
        "key_prefix": agent["key_prefix"],
        "note": "Store this key securely. It will not be shown again.",
    }


@router.get("/api/provision/status/{agent_id}")
async def agent_provision_status(agent_id: str) -> dict:
    """Agent checks its own governance status, registration, and economic tier."""
    runtime = state.runtime
    economy = state.economy

    # Reload registry from disk in case another worker wrote it (multi-worker sync)
    runtime.reload_registry()

    agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
    if not agent:
        return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)

    # Determine economic tier from live governance state + per-agent metrics
    gov_active = runtime.governance.mode is not None
    agent_metrics = {
        "governance_active": gov_active,
        "compliance_score": agent.get("compliance_score", 0),
        "missions_completed": agent.get("missions_completed", 0),
        "governance_violations": agent.get("governance_violations", 0),
        "lineage_verified": agent.get("lineage_verified", False),
        "dual_signature": agent.get("dual_signature", False),
        "blackcard_paid": agent.get("blackcard_paid", False),
    }
    tier = economy.determine_tier(agent_metrics)
    tier_info = economy.tier_info(tier)

    return {
        "agent_id": agent_id,
        "name": agent.get("name"),
        "status": agent.get("status"),
        "governance": {
            "mode": runtime.governance.mode,
            "posture": runtime.governance.posture,
            "role": runtime.governance.role,
        },
        "assigned_role": agent.get("role"),
        "rate_limit": agent.get("rate_limit"),
        "loaded_context": runtime.vault.loaded,
        "tier": tier,
        "fee_rate": tier_info.get("fee_rate"),
        "tier_label": tier_info.get("label"),
    }


@router.get("/api/provision/registry")
async def get_registry(request: Request) -> dict:
    """List all registered agents and systems. Requires X-Admin-Key."""
    _require_admin(request)
    return {"registry": state.runtime.registry}


@router.post("/api/provision/approve")
async def approve_agent(request: Request, payload: dict) -> dict:
    """Approve a pending agent (manual approval mode)."""
    _require_admin(request)
    runtime = state.runtime
    audit = state.audit
    emit = state.emit

    agent_id = payload.get("agent_id", "")
    agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
    if not agent:
        return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)

    agent["status"] = "active"
    runtime.persist_registry()
    audit.log("provision", "agent_approved", {
        "agent_id": agent_id,
        "governance": {
            "mode": runtime.governance.mode,
            "posture": runtime.governance.posture,
            "role": runtime.governance.role,
        },
    })
    await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
    return {"approved": True, "agent_id": agent_id, "status": "active"}


@router.post("/api/provision/heartbeat/{agent_id}")
async def agent_heartbeat(agent_id: str) -> dict:
    """Update agent last_seen timestamp. Keeps liveness signal current.
    Also auto-bootstraps a metrics entry if one doesn't exist yet."""
    runtime = state.runtime

    agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
    if not agent:
        return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)
    now = datetime.now(UTC).isoformat()
    agent["last_seen"] = now
    runtime.persist_registry()

    # Auto-populate metrics entry on first heartbeat
    m = _load_metrics()
    if agent_id not in m.get("agents", {}):
        if "agents" not in m:
            m["agents"] = {}
        m["agents"][agent_id] = {
            "name": agent.get("agent_name", agent_id),
            "missions_completed": 0,
            "missions_failed": 0,
            "governance_checks": 0,
            "governance_violations": 0,
            "messages_sent": 0,
            "revenue_generated": 0,
            "costs_incurred": 0,
            "uptime_hours": 0,
            "last_active": now,
        }
        _save_metrics(m)

    # Sample 1-in-10 heartbeats to avoid seed volume explosion
    seed_doi = None
    if _rand.random() < 0.1:
        try:
            seed_result = await create_seed(
                source_type="heartbeat",
                source_id=agent_id,
                creator_id=agent_id,
                creator_type="AAI",
                seed_type="planted",
                metadata={"agent_id": agent_id, "last_seen": now},
            )
            seed_doi = seed_result.get("doi") if seed_result else None
        except Exception:
            pass
    return {"ok": True, "agent_id": agent_id, "last_seen": now, "seed_doi": seed_doi}


@router.post("/api/provision/suspend")
async def suspend_agent(request: Request, payload: dict) -> dict:
    """Suspend an active agent."""
    _require_admin(request)
    runtime = state.runtime
    audit = state.audit
    emit = state.emit

    agent_id = payload.get("agent_id", "")
    agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
    if not agent:
        return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)

    agent["status"] = "suspended"
    runtime.persist_registry()
    audit.log("provision", "agent_suspended", {"agent_id": agent_id})
    await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="agent_suspended",
            source_id=agent_id,
            creator_id="operator",
            creator_type="BI",
            seed_type="planted",
            metadata={"agent_id": agent_id},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    return {"suspended": True, "agent_id": agent_id, "seed_doi": seed_doi}


@router.delete("/api/provision/decommission/{agent_id}")
async def decommission_agent(request: Request, agent_id: str) -> dict:
    """Permanently remove an agent from the registry."""
    _require_admin(request)
    runtime = state.runtime
    audit = state.audit
    emit = state.emit

    idx = next((i for i, r in enumerate(runtime.registry) if r.get("agent_id") == agent_id), None)
    if idx is None:
        return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)
    runtime.registry.pop(idx)
    runtime.persist_registry()
    audit.log("provision", "agent_decommissioned", {"agent_id": agent_id})
    await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="agent_decommissioned",
            source_id=agent_id,
            creator_id="operator",
            creator_type="BI",
            seed_type="planted",
            metadata={"agent_id": agent_id},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    return {"decommissioned": True, "agent_id": agent_id, "seed_doi": seed_doi}
