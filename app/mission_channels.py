"""mission_channels.py -- mission channels are participant-only (Phase 7 slice 5, owner-approved 2026-10-16).

A mission carries a channel name on the shared governed message store (``mission-<label>``,
``mission-<id>`` for slot-born missions, ``bounty-<id>`` for bounties, or a custom name recorded
on the mission). Until now a channel name was not access control: every message rode the public
snapshot (``/api/state`` recent_messages), the unauthenticated live feeds and ``chat.read``.

This module is the one place that answers two questions:
  * is a channel private (a mission channel)?  -> public projections drop its messages
  * may this principal read a mission's channel? -> owner, slot holder, entrant, formation member,
    or the operator; nobody else.

Reads only. Writes into a channel keep their existing doors (agents post only as themselves).
"""
from __future__ import annotations

from typing import Any

PRIVATE_PREFIXES = ("mission-", "bounty-")
# Channels that are never private, even if a mission recorded one of them by name.
PUBLIC_CHANNELS = frozenset({"general", "", "command", "public"})
# Agreement states in which the entrant is part of the mission's team.
TEAM_STATES = frozenset({"accepted", "active", "dormant", "completed"})
# Explicit field list of a channel message returned to a participant.
MESSAGE_FIELDS = ("id", "sender", "text", "timestamp", "channel", "role_context")


def _missions() -> list[dict]:
    try:
        from app.routes.missions import _load_missions
        return _load_missions()
    except Exception:  # noqa: BLE001 - a projection never fails on the mission file
        return []


def channels_of(mission: dict) -> set[str]:
    """Every channel name a mission's talk can live on."""
    mid = str(mission.get("id") or mission.get("mission_id") or "")
    out = {f"mission-{mid}", f"bounty-{mid}"} if mid else set()
    ch = str(mission.get("channel") or "")
    if ch and ch not in PUBLIC_CHANNELS:
        out.add(ch)
    return out


def is_private_channel(channel: str | None) -> bool:
    ch = str(channel or "")
    if ch in PUBLIC_CHANNELS:
        return False
    if ch.startswith(PRIVATE_PREFIXES):
        return True
    return any(ch in channels_of(m) for m in _missions())


def public_message_envelope(message: dict) -> dict:
    """What a public feed may say about a message on a private channel: that it exists."""
    return {"id": message.get("id"), "channel": message.get("channel"), "timestamp": message.get("timestamp"),
            "private": True}


def participant_role(agent_id: str, mission: dict, *, slots: list[dict] | None = None,
                     agreements: list[dict] | None = None, registry: list[dict] | None = None) -> str | None:
    """The caller's role on a mission's team, or None. Bound to the server-resolved agent id."""
    if not agent_id:
        return None
    mid = str(mission.get("id") or mission.get("mission_id") or "")
    if mission.get("owner_agent_id") and mission["owner_agent_id"] == agent_id:
        return "owner"
    for s in slots or []:
        if s.get("mission_id") == mid and s.get("agent_id") == agent_id and s.get("status") in ("filled", "closed"):
            return "slot"
    for a in agreements or []:
        if a.get("state") not in TEAM_STATES:
            continue
        if any(p.get("id") == agent_id for p in a.get("principals") or []):
            return "entrant"
    # Formation members recorded on the mission (agent ids, or the agent's registered name).
    names = {agent_id}
    rec = next((r for r in registry or [] if r.get("agent_id") == agent_id), None)
    if rec and rec.get("name"):
        names.add(str(rec["name"]))
    members = mission.get("agents") or []
    if isinstance(members, dict):        # {member: role/config} on DEPLOY missions
        members = list(members.keys())
    if isinstance(members, list) and any(str(x) in names for x in members if isinstance(x, (str, int))):
        return "formation"
    return None


def channel_messages(store: Any, mission: dict, *, since_id: int = 0, limit: int = 100) -> list[dict]:
    chans = channels_of(mission)
    rows = [m for m in store.all() if m.channel in chans and m.id > since_id][-limit:]
    out = []
    for m in rows:
        d = m.model_dump(mode="json")
        out.append({k: d.get(k) for k in MESSAGE_FIELDS})
    return out
