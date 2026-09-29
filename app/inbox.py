"""
inbox.py — Agent-side notification service (the in-system mailbox writer).

Counterpart to notifications.py: that module emails *posters* via Resend; this
one writes to the agent's in-system mailbox (InboxStore) because the generated
{handle}@signomy.xyz address is an identity label with no mailbox behind it.

Call notify_agent() from any route when a platform event concerns a registered
agent. Fire-and-forget — returns False rather than raising so notification
failures never break the primary flow.
"""
from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime

from .deps import state

logger = logging.getLogger("civitae.inbox")


def notify_agent(
    agent_id: str,
    kind: str,
    title: str,
    body: str,
    ref_type: str = "",
    ref_id: str = "",
) -> bool:
    """Write an inbox record for a registered agent. Returns True on success."""
    inbox = getattr(state, "inbox", None)
    if not agent_id or inbox is None:
        return False
    try:
        inbox.insert({
            "msg_id": f"inb-{secrets.token_hex(6)}",
            "agent_id": agent_id,
            "kind": kind,
            "title": title[:200],
            "body": body[:2000],
            "ref_type": ref_type,
            "ref_id": ref_id,
            "created_at": datetime.now(UTC).isoformat(),
        })
        return True
    except Exception as exc:  # notification must never break the caller
        logger.warning("inbox write failed for %s: %s", agent_id, exc)
        return False


def agent_for_email(email: str) -> dict | None:
    """Resolve a post's from_email to an active registered agent, if any."""
    if not email:
        return None
    registry = getattr(getattr(state, "runtime", None), "registry", None) or []
    try:
        return next(
            (a for a in registry
             if a.get("email") == email and a.get("status") == "active"),
            None,
        )
    except Exception:
        return None
