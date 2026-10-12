"""Slot / mission binding for the WorkEntryAgreement (P4 slice 4).

Write order (plan section 2, H2): the Agreement transition commits FIRST; the
slot/mission write then runs under ``state.slot_lock``. If the slot/mission
write fails (or the slot was taken meanwhile) the Agreement gets an explicit
``evidence_gap`` and a compensating ``terminated`` transition, so there is never
an active Agreement pointing at an unbound slot, nor a bound slot without an
active Agreement.

Missions and slots stay JSON (missions.py loaders). Wiring is keyed to object
ids: the Agreement's ``objects{post_id, mission_id, slot_id}`` is the one link;
there is no post_id -> slot_id glue anywhere else.
"""
from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

from app.deps import state
from app.workentry_store import WorkEntryError

ENTRY_MODES = ("open", "standard", "constitutional")
_MODE_RANK = {m: i for i, m in enumerate(ENTRY_MODES)}
RESERVED = "reserved"          # slot held for one Agreement (post-origin mint); not fillable by others


class BindError(Exception):
    """A binding step failed AFTER the Agreement committed; the Agreement was compensated."""

    def __init__(self, status: int, message: str, code: str, agreement: dict | None = None,
                 gap_id: str | None = None):
        super().__init__(message)
        self.status, self.message, self.code = status, message, code
        self.agreement, self.gap_id = agreement, gap_id

    def body(self) -> dict:
        out: dict[str, Any] = {"error": self.message, "code": self.code}
        if self.agreement:
            out["agreement_id"] = self.agreement["agreement_id"]
            out["agreement_state"] = self.agreement["state"]
        if self.gap_id:
            out["evidence_gap_id"] = self.gap_id
        return out


def _ms():
    import app.routes.missions as ms   # late: missions imports this module
    return ms


def now() -> str:
    return datetime.now(UTC).isoformat()


def find_mission(mission_id: str | None) -> dict | None:
    if not mission_id:
        return None
    return next((m for m in _ms()._load_missions()
                 if mission_id in (m.get("id"), m.get("mission_id"))), None)


def slot_mode(slot: dict, mission: dict | None) -> str:
    """The slot's own entry_mode, else its mission's, else open (legacy records)."""
    m = slot.get("entry_mode") or (mission or {}).get("entry_mode") or "open"
    return m if m in _MODE_RANK else "open"


def mission_owner(mission: dict | None) -> str:
    return (mission or {}).get("owner_agent_id") or "platform"


def mission_control_ref(mission_id: str | None) -> str | None:
    return f"/missions?mission={mission_id}" if mission_id else None


def _compensate(agreement_id: str, stage: str, reason: str, status: int, code: str) -> BindError:
    store = state.workentry
    try:
        out = store.compensate(agreement_id, stage=stage, reason=reason)
        gaps = store.evidence_gaps(agreement_id)
        return BindError(status, reason, code, out["agreement"], gaps[-1]["gap_id"] if gaps else None)
    except WorkEntryError as exc:   # compensation itself failed: still loud, never silent
        gap = store.record_gap(agreement_id, attempted="bind", stage=stage,
                               reason=f"{reason}; compensation failed: {exc.message}",
                               resolution="compensation_failed")
        return BindError(500, f"{reason}; compensation failed: {exc.message}", "binding_failed",
                         store.get(agreement_id), gap)


def fill_slot_record(slot: dict, *, agent_id: str, agent_name: str, agreement: dict) -> None:
    slot["status"] = "filled"
    slot["agent_id"] = agent_id
    slot["agent_name"] = agent_name
    slot["filled_at"] = now()
    slot["agreement_id"] = agreement["agreement_id"]
    slot["entry_mode"] = agreement["entry_mode"]
    slot.setdefault("post_id", agreement["objects"].get("post_id"))


async def bind_on_activation(agreement: dict) -> dict:
    """Agreement just went ``active``: bind its slot (under slot_lock). Raises BindError
    (after compensating the Agreement) when the slot cannot be bound."""
    ms = _ms()
    obj = agreement["objects"]
    slot_id, mission_id = obj.get("slot_id"), obj.get("mission_id")
    aid = agreement["agreement_id"]
    entrant = next(p["id"] for p in agreement["principals"] if p["role"] == "entrant")
    if not slot_id:
        return {"mission_id": mission_id, "slot_id": None, "slot": None}
    agent = next((r for r in state.runtime.registry if r.get("agent_id") == entrant), None) or {}
    async with state.slot_lock:
        try:
            slots = ms._load_slots()
            slot = next((s for s in slots if s["id"] == slot_id), None)
            if slot is None:
                raise _compensate(aid, "slot_binding", f"slot write failed: slot {slot_id} not found",
                                  409, "slot_not_found")
            if not (slot["status"] == "open" or
                    (slot["status"] == RESERVED and slot.get("agreement_id") == aid)):
                raise _compensate(aid, "slot_binding",
                                  f"slot write failed: slot already {slot['status']}", 409, "slot_taken")
            fill_slot_record(slot, agent_id=entrant, agent_name=agent.get("name") or entrant,
                             agreement=agreement)
            ms._save_slots(slots)
        except BindError:
            raise
        except Exception as exc:  # noqa: BLE001 - any slot write failure compensates
            raise _compensate(aid, "slot_binding", f"slot write failed: {type(exc).__name__}: {exc}",
                              500, "binding_failed") from exc
        mission = None
        try:
            missions = ms._load_missions()
            mission = next((m for m in missions
                            if mission_id in (m.get("id"), m.get("mission_id"))), None)
            if mission is not None and mission.get("status") == "published":
                mission["status"] = "active"      # second click: the mission leaves PUBLISHED
                ms._save_missions(missions)
        except Exception as exc:  # noqa: BLE001 - slot is bound and Agreement is active; record, don't hide
            state.workentry.record_gap(aid, attempted="bind", stage="mission_status",
                                       reason=f"mission status write failed: {exc}",
                                       resolution="committed_with_gap")
    return {"mission_id": mission_id, "slot_id": slot_id, "slot": slot}


async def mint_for_post(agreement: dict) -> dict:
    """Post-origin: the poster's acceptance mints the mission + slot under the poster's own
    authority (owner = the post's agent). On failure the Agreement is compensated."""
    ms = _ms()
    obj = agreement["objects"]
    if obj.get("slot_id") or not obj.get("post_id"):
        return agreement
    aid = agreement["agreement_id"]
    post = state.kassa.get_post(obj["post_id"]) or {}
    owner = next(p["id"] for p in agreement["principals"] if p["role"] == "owner")
    agent_owned = not owner.startswith(("poster:", "platform"))
    mission_id = f"mission-{secrets.token_hex(4)}"
    slot_id = f"slot-{secrets.token_hex(4)}"
    mode = agreement["entry_mode"]
    label = post.get("title") or obj["post_id"]
    gov = state.runtime.governance
    async with state.slot_lock:
        mission_saved = False
        missions = None
        try:
            missions = ms._load_missions()
            taken = {m.get(k) for m in missions for k in ("id", "mission_id")}
            while mission_id in taken:
                mission_id = f"mission-{secrets.token_hex(4)}"
            missions.append({
                "id": mission_id, "mission_id": mission_id, "label": label,
                "objective": post.get("body", ""), "posture": "SCOUT", "formation": "post_entry",
                "target": "", "duration": "", "limits": {}, "systems": [], "agents": [],
                "status": "published", "origin": "post_entry", "created_at": now(), "ended_at": None,
                "governance_at_launch": {"mode": gov.mode, "posture": gov.posture, "role": gov.role},
                "results": [], "channel": f"mission-{mission_id}", "slot_ids": [slot_id],
                "post_id": obj["post_id"], "agreement_id": aid, "entry_mode": mode,
                "owner_agent_id": owner if agent_owned else None,
                "created_by": "agent" if agent_owned else "poster_link",
                "poster_ref": None if agent_owned else owner,
            })
            ms._save_missions(missions)
            mission_saved = True
            slots = ms._load_slots()
            slots.append({
                "id": slot_id, "mission_id": mission_id, "mission_label": label, "formation_id": "post_entry",
                "position": {"row": 0, "col": 0}, "grid_ref": "A1", "role": "primary",
                "governance": {"mode": gov.mode, "posture": "SCOUT"}, "revenue_split_pct": 100,
                "status": RESERVED, "agent_id": None, "agent_name": None, "filled_at": None,
                "created_at": now(), "metrics": {"messages": 0, "governance_checks": 0,
                                                 "violations": 0, "revenue": 0},
                "post_id": obj["post_id"], "agreement_id": aid, "entry_mode": mode,
            })
            ms._save_slots(slots)
            return state.workentry.bind_objects(aid, mission_id=mission_id, slot_id=slot_id)
        except Exception as exc:  # noqa: BLE001
            if mission_saved and missions is not None:
                try:   # never delete: mark the half-made mission cancelled
                    for m in missions:
                        if m.get("id") == mission_id:
                            m["status"] = "cancelled"
                    ms._save_missions(missions)
                except Exception:  # noqa: BLE001
                    pass
            raise _compensate(aid, "mission_mint", f"slot write failed: mission/slot mint failed: "
                              f"{type(exc).__name__}: {exc}", 500, "binding_failed") from exc


def live_for_slot(agent_id: str, slot_id: str) -> list[dict]:
    live = ("pending", "dormant", "accepted", "active")
    return [a for a in state.workentry.list(entrant=agent_id, opportunity_ref=f"slot:{slot_id}")
            if a["state"] in live]


def summarize(agreements: list[dict]) -> list[dict]:
    return [{"agreement_id": a["agreement_id"], "state": a["state"],
             "entrant": next(p["id"] for p in a["principals"] if p["role"] == "entrant"),
             "slot_id": a["objects"].get("slot_id"), "entry_mode": a["entry_mode"]} for a in agreements]
