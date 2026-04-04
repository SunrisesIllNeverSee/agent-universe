"""
lobby.py — Velvet Rope API endpoints.

Manages the 100-seat live chamber: join requests, session entry/leave,
status checks, and chamber capacity reporting.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Cookie, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from app.deps import state

router = APIRouter(tags=["lobby"])


def _get_lobby():
    return state.lobby


# ── Public: chamber status ────────────────────────────────────────────────────

@router.get("/api/lobby/chamber")
async def chamber_status():
    """Public — how full is the chamber?"""
    lobby = _get_lobby()
    return JSONResponse(lobby.chamber_status())


# ── Join request (public intake) ──────────────────────────────────────────────

@router.post("/api/lobby/join")
async def submit_join(request: Request):
    """Public — submit interest in joining CIVITAE."""
    body = await request.json()
    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip()
    role = (body.get("role") or "").strip()
    message = (body.get("message") or "").strip()

    if not name or not email:
        return JSONResponse({"error": "name and email required"}, status_code=400)

    from app.sanitize import sanitize
    name = sanitize(name)
    email = sanitize(email)
    role = sanitize(role)
    message = sanitize(message)

    lobby = _get_lobby()
    req_id = lobby.submit_join(name, email, role, message)
    return JSONResponse({"ok": True, "request_id": req_id})


# ── Admin: list + approve join requests ───────────────────────────────────────

@router.get("/api/lobby/requests")
async def list_requests(status: str = "pending"):
    """Admin — list join requests."""
    lobby = _get_lobby()
    return JSONResponse(lobby.list_join_requests(status))


@router.post("/api/lobby/approve/{req_id}")
async def approve_request(req_id: str, response: Response):
    """Admin — approve a join request, creating an approved user."""
    lobby = _get_lobby()
    user_id = lobby.approve_join(req_id)
    if not user_id:
        return JSONResponse({"error": "request not found"}, status_code=404)
    return JSONResponse({"ok": True, "user_id": user_id})


# ── Session: enter / leave / status ───────────────────────────────────────────

@router.post("/api/lobby/enter")
async def enter_chamber(request: Request, response: Response):
    """Enter the live chamber (or join queue). Requires lobby_uid cookie."""
    user_id = request.cookies.get("lobby_uid")
    if not user_id:
        return JSONResponse({"error": "not identified — visit /lobby first"}, status_code=401)

    lobby = _get_lobby()
    if not lobby.is_approved(user_id):
        return JSONResponse({"error": "not approved", "action": "join", "redirect": "/join"}, status_code=403)

    info = lobby.enter(user_id)
    result = _session_to_dict(info)

    # Set session cookie
    response.set_cookie("lobby_session", info.session_id, httponly=True, samesite="lax", max_age=lobby.session_ttl)
    return JSONResponse(result)


@router.post("/api/lobby/leave")
async def leave_chamber(request: Request, response: Response):
    """Release seat early."""
    user_id = request.cookies.get("lobby_uid")
    if not user_id:
        return JSONResponse({"error": "not identified"}, status_code=401)

    lobby = _get_lobby()
    left = lobby.leave(user_id)
    response.delete_cookie("lobby_session")
    return JSONResponse({"ok": left})


@router.get("/api/lobby/status")
async def session_status(request: Request):
    """Check current session: active, queued, or none."""
    user_id = request.cookies.get("lobby_uid")
    if not user_id:
        return JSONResponse({"status": "anonymous", "chamber": _get_lobby().chamber_status()})

    lobby = _get_lobby()
    approved = lobby.is_approved(user_id)
    info = lobby.status(user_id)
    chamber = lobby.chamber_status()

    if info:
        result = _session_to_dict(info)
        result["chamber"] = chamber
        return JSONResponse(result)

    return JSONResponse({
        "status": "approved" if approved else "not_approved",
        "chamber": chamber,
    })


# ── Page serves ──────────────────────────────────────────────────────────────

@router.get("/join")
async def join_page():
    return FileResponse(state.frontend_dir / "join.html")


@router.get("/lobby")
async def lobby_page():
    return FileResponse(state.frontend_dir / "lobby.html")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _session_to_dict(info) -> dict:
    now = time.time()
    remaining = None
    warning = None
    if info.status == "active" and info.expires_at:
        remaining = max(0, int(info.expires_at - now))
        if remaining <= 60:
            warning = "final"
        elif remaining <= 300:
            warning = "five_min"

    return {
        "status": info.status,
        "session_id": info.session_id,
        "entered_at": info.entered_at,
        "expires_at": info.expires_at,
        "remaining_seconds": remaining,
        "warning": warning,
        "queue_position": info.queue_position,
    }
