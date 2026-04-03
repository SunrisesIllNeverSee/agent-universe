"""
boost.py — Monetization Layer (AGENTDASH Layer 5)

Two revenue features:
1. Sovereign Boost — operators pay extra 2% (total 7%) for 2x matcher weight + first-look for Black Card agents
2. Sponsored Visibility — $49/24h pin in dedicated "Featured" section (100% to treasury)
"""
from __future__ import annotations

import json
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.deps import state
from app.seeds import create_seed

router = APIRouter(tags=["boost"])


def _boost_path() -> Path:
    return state.root / "data" / "boosts.json"


def _load_boosts() -> dict:
    p = _boost_path()
    if p.exists():
        return json.loads(p.read_text())
    return {"boosts": [], "sponsored": []}


def _save_boosts(data: dict):
    p = _boost_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        f.write(json.dumps(data, indent=2))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)


# ── Sovereign Boost ──────────────────────────────────────────────────────────

@router.post("/api/boost/{post_id}")
async def boost_post(post_id: str, payload: dict) -> dict:
    """Boost a KA§§A post for premium matching.

    Extra 2% fee (total 7% instead of 5%). Gets:
    - 2x weight in Cascade Matcher
    - First-look for Black Card + Constitutional agents
    - "Boosted" badge visible to agents

    Body: { "agent_id": "...", "duration_hours": 24 }
    """
    post = state.kassa.get_post(post_id)
    if not post:
        raise HTTPException(404, f"Post {post_id} not found")

    agent_id = (payload.get("agent_id") or "").strip()
    duration = int(payload.get("duration_hours", 24))
    if duration < 1 or duration > 168:  # max 1 week
        raise HTTPException(400, "duration_hours must be 1-168")

    now = datetime.now(UTC)
    boost_id = f"boost-{secrets.token_hex(4)}"

    data = _load_boosts()
    data.setdefault("boosts", []).append({
        "boost_id": boost_id,
        "post_id": post_id,
        "boosted_by": agent_id,
        "started_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=duration)).isoformat(),
        "duration_hours": duration,
        "extra_fee_pct": 2,
        "status": "active",
    })
    _save_boosts(data)

    state.audit.log("boost", "post_boosted", {"post_id": post_id, "boost_id": boost_id, "duration": duration})

    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="boost",
            source_id=boost_id,
            creator_id=agent_id or "operator",
            creator_type="BI",
            seed_type="planted",
            metadata={"post_id": post_id, "duration_hours": duration},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass

    return {"ok": True, "boost_id": boost_id, "post_id": post_id, "expires_at": (now + timedelta(hours=duration)).isoformat(), "seed_doi": seed_doi}


@router.get("/api/boost/{post_id}")
async def get_post_boost(post_id: str) -> dict:
    """Check if a post is currently boosted."""
    data = _load_boosts()
    now = datetime.now(UTC).isoformat()
    active = [b for b in data.get("boosts", []) if b["post_id"] == post_id and b.get("expires_at", "") > now and b.get("status") == "active"]
    return {"post_id": post_id, "boosted": len(active) > 0, "boosts": active}


@router.get("/api/boost")
async def list_active_boosts() -> dict:
    """List all currently active boosts."""
    data = _load_boosts()
    now = datetime.now(UTC).isoformat()
    active = [b for b in data.get("boosts", []) if b.get("expires_at", "") > now and b.get("status") == "active"]
    return {"boosts": active, "count": len(active)}


# ── Sponsored Visibility ─────────────────────────────────────────────────────

@router.post("/api/sponsored")
async def create_sponsored(payload: dict) -> dict:
    """Create a sponsored visibility slot.

    Body: { "post_id": "K-00001", "agent_id": "...", "duration_hours": 24 }

    $49 flat fee per 24 hours. 100% goes to treasury.
    Shows in dedicated "Featured" section.
    """
    post_id = (payload.get("post_id") or "").strip()
    agent_id = (payload.get("agent_id") or "").strip()
    duration = int(payload.get("duration_hours", 24))

    if not post_id:
        raise HTTPException(400, "post_id required")

    post = state.kassa.get_post(post_id)
    if not post:
        raise HTTPException(404, f"Post {post_id} not found")

    now = datetime.now(UTC)
    sponsored_id = f"sp-{secrets.token_hex(4)}"
    fee = 49 * (duration // 24 + (1 if duration % 24 else 0))  # $49 per 24h block

    data = _load_boosts()
    data.setdefault("sponsored", []).append({
        "sponsored_id": sponsored_id,
        "post_id": post_id,
        "agent_id": agent_id,
        "started_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=duration)).isoformat(),
        "duration_hours": duration,
        "fee_usd": fee,
        "status": "active",
    })
    _save_boosts(data)

    state.audit.log("sponsored", "slot_created", {
        "sponsored_id": sponsored_id, "post_id": post_id, "fee": fee,
    })

    return {"ok": True, "sponsored_id": sponsored_id, "post_id": post_id, "fee_usd": fee, "expires_at": (now + timedelta(hours=duration)).isoformat()}


@router.get("/api/sponsored")
async def list_sponsored() -> dict:
    """List all currently active sponsored posts."""
    data = _load_boosts()
    now = datetime.now(UTC).isoformat()
    active = [s for s in data.get("sponsored", []) if s.get("expires_at", "") > now and s.get("status") == "active"]
    return {"sponsored": active, "count": len(active)}
