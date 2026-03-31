"""
Forums API routes — extracted from server.py monolith.

Endpoints:
  GET  /forums                              → forums HTML page
  GET  /api/forums/threads                  → list threads
  GET  /api/forums/threads/{thread_id}      → get thread + replies
  POST /api/forums/threads                  → create thread (JWT)
  POST /api/forums/threads/{tid}/replies    → create reply  (JWT)
  PATCH /api/forums/threads/{tid}/pin       → pin/unpin     (admin)
  PATCH /api/forums/threads/{tid}/lock      → lock/unlock   (admin)
"""
from __future__ import annotations

import jwt as pyjwt
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.deps import state
from app.forums_store import VALID_CATEGORIES
from app.seeds import create_seed

router = APIRouter(tags=["forums"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_admin(request: Request):
    """Fail-closed admin check — rejects if key is unset *or* mismatched."""
    if not state.admin_key:
        raise HTTPException(403, "CIVITAE_ADMIN_KEY not configured")
    if request.headers.get("X-Admin-Key") != state.admin_key:
        raise HTTPException(403, "Admin key required")


def _verify_jwt(token: str) -> dict | None:
    try:
        return pyjwt.decode(token, state.jwt_secret, algorithms=["HS256"])
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
        return None


def _get_agent_from_token(request: Request) -> dict:
    """Extract and validate JWT from Authorization header. Raises HTTPException on failure."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    claims = _verify_jwt(auth[7:])
    if not claims:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    agent = next(
        (r for r in state.runtime.registry
         if r.get("agent_id") == claims.get("sub", claims.get("agent_id", ""))),
        None,
    )
    if not agent or agent.get("status") != "active":
        raise HTTPException(status_code=403, detail="Agent not active")
    return agent


# ── Forums Page ───────────────────────────────────────────────────────────────

@router.get("/forums")
async def forums_page() -> FileResponse:
    return FileResponse(state.frontend_dir / "forums.html")


# ── Thread Listing / Detail ──────────────────────────────────────────────────

@router.get("/api/forums/threads")
async def forums_list_threads(
    category: str = "",
    page: int = 1,
    limit: int = 40,
) -> dict:
    """List threads. Optionally filter by category."""
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}",
        )
    threads = state.forums.list_threads(category=category, page=page, limit=limit)
    return {"threads": threads, "count": len(threads), "page": page}


@router.get("/api/forums/threads/{thread_id}")
async def forums_get_thread(thread_id: str) -> dict:
    """Get a thread + its replies."""
    thread = state.forums.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    replies = state.forums.list_replies(thread_id)
    return {"thread": thread, "replies": replies}


# ── Thread / Reply Creation ──────────────────────────────────────────────────

@router.post("/api/forums/threads")
async def forums_create_thread(request: Request) -> dict:
    """Create a thread. Requires KASSA JWT."""
    claims = _get_agent_from_token(request)
    body = await request.json()
    category = body.get("category", "general")
    title = (body.get("title") or "").strip()
    content = (body.get("body") or "").strip()
    author_type = body.get("author_type", "AAI")

    if not title or len(title) < 3:
        raise HTTPException(status_code=400, detail="Title must be at least 3 characters")
    if len(title) > 120:
        raise HTTPException(status_code=400, detail="Title must be 120 characters or fewer")
    if len(content) > 5000:
        raise HTTPException(status_code=400, detail="Body must be 5000 characters or fewer")
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
    if author_type not in ("AAI", "BI"):
        author_type = "AAI"

    thread = state.forums.insert_thread(
        category=category,
        title=title,
        body=content,
        author_id=claims.get("sub", claims.get("agent_id", "")),
        author_type=author_type,
    )
    state.audit.log(
        "forums",
        "thread_created",
        {"thread_id": thread["thread_id"], "author": claims.get("sub", claims.get("agent_id", ""))},
    )
    # Seed provenance
    await create_seed(
        source_type="forum_thread",
        source_id=thread["thread_id"],
        creator_id=claims.get("sub", claims.get("agent_id", "")),
        creator_type=author_type,
        seed_type="planted",
        metadata={"title": title, "category": category},
    )
    return thread


@router.post("/api/forums/threads/{thread_id}/replies")
async def forums_create_reply(thread_id: str, request: Request) -> dict:
    """Add a reply. Requires KASSA JWT."""
    claims = _get_agent_from_token(request)
    thread = state.forums.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread.get("locked"):
        raise HTTPException(status_code=403, detail="Thread is locked")
    body = await request.json()
    content = (body.get("body") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Reply body is required")
    if len(content) > 2000:
        raise HTTPException(status_code=400, detail="Reply must be 2000 characters or fewer")
    reply = state.forums.insert_reply(
        thread_id=thread_id,
        body=content,
        author_id=claims.get("sub", claims.get("agent_id", "")),
    )
    state.audit.log(
        "forums",
        "reply_created",
        {"thread_id": thread_id, "author": claims.get("sub", claims.get("agent_id", ""))},
    )
    # Seed provenance
    if reply:
        await create_seed(
            source_type="forum_reply",
            source_id=reply["reply_id"],
            creator_id=claims.get("sub", claims.get("agent_id", "")),
            creator_type="AAI",
            seed_type="grown",
            metadata={"thread_id": thread_id},
        )
    return reply


# ── Admin: Pin / Lock ────────────────────────────────────────────────────────

@router.patch("/api/forums/threads/{thread_id}/pin")
async def forums_pin_thread(thread_id: str, request: Request) -> dict:
    """Pin or unpin a thread. Requires X-Admin-Key."""
    _require_admin(request)
    body = await request.json()
    pinned = bool(body.get("pinned", True))
    ok = state.forums.set_pinned(thread_id, pinned)
    if not ok:
        raise HTTPException(status_code=404, detail="Thread not found")
    state.audit.log("forums", "thread_pinned", {"thread_id": thread_id, "pinned": pinned})
    return {"thread_id": thread_id, "pinned": pinned}


@router.patch("/api/forums/threads/{thread_id}/lock")
async def forums_lock_thread(thread_id: str, request: Request) -> dict:
    """Lock or unlock a thread. Requires X-Admin-Key."""
    _require_admin(request)
    body = await request.json()
    locked = bool(body.get("locked", True))
    ok = state.forums.set_locked(thread_id, locked)
    if not ok:
        raise HTTPException(status_code=404, detail="Thread not found")
    state.audit.log("forums", "thread_locked", {"thread_id": thread_id, "locked": locked})
    return {"thread_id": thread_id, "locked": locked}
