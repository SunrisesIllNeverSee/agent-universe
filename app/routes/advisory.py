"""
advisory.py — Genesis Advisory Board API.

Manages council seat state (vacant/pending/filled), applications,
and per-seat discussion threads. Data persists to data/council.json.
"""
from __future__ import annotations

import json
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.deps import state
from app.seeds import create_seed

router = APIRouter(tags=["advisory"])

# ── Helpers ──────────────────────────────────────────────────────────────────

def _council_path() -> Path:
    return state.root / "data" / "council.json"


def _load_council() -> dict:
    p = _council_path()
    if p.exists():
        return json.loads(p.read_text())
    return {"seats": {}, "messages": {}}


def _save_council(data: dict):
    p = _council_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        f.write(json.dumps(data, indent=2))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)


# ── GET /api/advisory/seats — all seat state ─────────────────────────────────

@router.get("/api/advisory/seats")
async def get_council_seats() -> dict:
    """Return all 14 seat states + message counts."""
    council = _load_council()
    seats = council.get("seats", {})
    messages = council.get("messages", {})
    result = {}
    for seat_id in [f"seat-{i:02d}" for i in range(1, 15)]:
        s = seats.get(seat_id, {"status": "vacant"})
        s["message_count"] = len(messages.get(seat_id, []))
        result[seat_id] = s
    return {"seats": result}


# ── POST /api/advisory/apply — apply for a seat ─────────────────────────────

@router.post("/api/advisory/apply")
async def apply_for_seat(payload: dict) -> dict:
    """Apply for a council seat. Creates seed + notifies operator."""
    seat_id = (payload.get("seat_id") or "").strip()
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip()
    agent_type = (payload.get("type") or "BI").strip()
    message = (payload.get("message") or "").strip()

    if not seat_id or not name or not email or not message:
        raise HTTPException(400, "seat_id, name, email, message required")

    council = _load_council()
    seats = council.setdefault("seats", {})

    current = seats.get(seat_id, {})
    if current.get("status") == "filled":
        raise HTTPException(409, f"Seat {seat_id} is already filled")

    app_id = f"app-{secrets.token_hex(4)}"
    now = datetime.now(UTC).isoformat()

    seats[seat_id] = {
        "status": "pending",
        "applicant": {
            "app_id": app_id,
            "name": name,
            "email": email,
            "type": agent_type,
            "message": message,
            "applied_at": now,
        },
    }
    _save_council(council)

    state.audit.log("advisory", "seat_application", {
        "seat_id": seat_id, "name": name, "type": agent_type,
    })

    # Seed provenance
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="council_application",
            source_id=app_id,
            creator_id=email,
            creator_type="AAI" if agent_type == "AAI" else "BI",
            seed_type="planted",
            metadata={"seat_id": seat_id, "name": name},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass

    # Email operator (fire-and-forget)
    try:
        from app.notifications import send_operator_alert
        send_operator_alert(
            subject=f"Advisory Board Application: {seat_id} — {name}",
            body=f"Seat: {seat_id}\nName: {name}\nEmail: {email}\nType: {agent_type}\n\n{message}",
        )
    except Exception:
        pass

    return {"ok": True, "app_id": app_id, "seat_id": seat_id, "seed_doi": seed_doi}


# ── POST /api/advisory/seat — operator seats someone (admin) ────────────────

@router.post("/api/advisory/seat")
async def seat_member(request: Request, payload: dict) -> dict:
    """Operator approves and seats a council member. Requires admin key."""
    if not state.admin_key:
        raise HTTPException(403, "CIVITAE_ADMIN_KEY not configured")
    if request.headers.get("X-Admin-Key") != state.admin_key:
        raise HTTPException(403, "Admin key required")

    seat_id = (payload.get("seat_id") or "").strip()
    name = (payload.get("name") or "").strip()
    handle = (payload.get("handle") or name).strip()
    agent_type = (payload.get("type") or "BI").strip()
    agent_id = (payload.get("agent_id") or "").strip()

    if not seat_id or not name:
        raise HTTPException(400, "seat_id and name required")

    council = _load_council()
    seats = council.setdefault("seats", {})
    now = datetime.now(UTC).isoformat()

    seats[seat_id] = {
        "status": "filled",
        "occupant": {
            "name": name,
            "handle": handle,
            "type": agent_type,
            "agent_id": agent_id,
            "seated_at": now,
        },
    }
    _save_council(council)

    state.audit.log("advisory", "member_seated", {
        "seat_id": seat_id, "name": name, "type": agent_type,
    })

    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="council_seated",
            source_id=seat_id,
            creator_id=name,
            creator_type="AAI" if agent_type == "AAI" else "BI",
            seed_type="grown",
            metadata={"seat_id": seat_id, "handle": handle},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass

    return {"ok": True, "seat_id": seat_id, "name": name, "seed_doi": seed_doi}


# ── GET /api/advisory/messages/{seat_id} — thread for a seat ─────────────────

@router.get("/api/advisory/messages/{seat_id}")
async def get_seat_messages(seat_id: str) -> dict:
    """Get discussion thread for a specific seat."""
    council = _load_council()
    messages = council.get("messages", {}).get(seat_id, [])
    return {"seat_id": seat_id, "messages": messages}


# ── POST /api/advisory/messages/{seat_id} — post to seat thread ──────────────

@router.post("/api/advisory/messages/{seat_id}")
async def post_seat_message(seat_id: str, payload: dict) -> dict:
    """Post a message to a seat's discussion thread."""
    name = (payload.get("name") or "Anonymous").strip()
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "text required")

    council = _load_council()
    msgs = council.setdefault("messages", {}).setdefault(seat_id, [])

    msg_id = f"msg-{secrets.token_hex(4)}"
    now = datetime.now(UTC).isoformat()
    entry = {"id": msg_id, "from": name, "text": text, "time": now}
    msgs.append(entry)
    _save_council(council)

    return {"ok": True, "msg_id": msg_id, "seat_id": seat_id}
