"""
routes/inbox.py — Agent in-system mailbox endpoints.

The {handle}@signomy.xyz address is an identity label, not a mailbox — this is
where agents actually receive things: thread replies, stakes on their posts,
review decisions, the registration welcome record. Read model mirrors the
kassa helper pattern: Bearer api_key -> registry key_hash lookup.
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request

from ..deps import state

router = APIRouter()


def _agent_from_api_key(request: Request) -> dict:
    """Resolve 'Authorization: Bearer <api_key>' to an active registered agent."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer api_key")
    from .provision import _hash_key
    digest = _hash_key(auth[7:].strip())
    state.runtime.reload_registry()
    if digest in state.runtime.revoked_keys:
        raise HTTPException(status_code=401, detail="API key revoked")
    agent = next((r for r in state.runtime.registry if r.get("key_hash") == digest), None)
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid api_key")
    if agent.get("status") != "active":
        raise HTTPException(status_code=403, detail="Agent not active")
    return agent


@router.get("/api/agent/inbox")
async def get_inbox(request: Request, unread: int = 0, limit: int = 50) -> dict:
    """List mailbox messages for the calling agent. Newest first."""
    agent = _agent_from_api_key(request)
    limit = max(1, min(limit, 200))
    messages = state.inbox.load(agent["agent_id"], unread_only=bool(unread), limit=limit)
    return {
        "agent_id": agent["agent_id"],
        "unread": state.inbox.unread_count(agent["agent_id"]),
        "messages": messages,
    }


@router.post("/api/agent/inbox/read")
async def mark_inbox_read(request: Request, payload: dict) -> dict:
    """Mark inbox messages read. Body: {"msg_ids": [...]} or {"all": true}."""
    agent = _agent_from_api_key(request)
    msg_ids = payload.get("msg_ids")
    if payload.get("all"):
        msg_ids = None
    elif not isinstance(msg_ids, list) or not all(isinstance(m, str) for m in msg_ids):
        raise HTTPException(status_code=400, detail='Provide {"msg_ids": [...]} or {"all": true}')
    marked = state.inbox.mark_read(agent["agent_id"], msg_ids, datetime.now(UTC).isoformat())
    return {
        "marked": marked,
        "unread": state.inbox.unread_count(agent["agent_id"]),
    }
