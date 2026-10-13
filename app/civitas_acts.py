"""
civitas_acts.py — GOV-001 Art 6 procedural acts, shared by REST and MCP (P5 / G7).

Each act loads the meeting, validates, mutates, records (minutes, audit, event,
Seed) and saves. The caller binds the actor's identity first (REST: claim check;
MCP: the api_key's agent name). Failures raise ProcError so each transport maps
them to its own error shape. Pure rules live in civitas_procedure.
"""
from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime

from app import civitas_procedure as proc
from app.deps import state
from app.metrics_io import atomic_write
from app.sanitize import sanitize_text
from app.seeds import create_seed_loud


class ProcError(Exception):
    def __init__(self, status: int, message: str, code: str | None = None):
        super().__init__(message)
        self.status = status
        self.body = {"error": message, **({"code": code} if code else {})}


def load_meetings() -> list[dict]:
    meetings_path = state.data_path("meetings.json")
    if meetings_path.exists():
        return json.loads(meetings_path.read_text())
    return []


def save_meetings(ms: list[dict]) -> None:
    atomic_write(state.data_path("meetings.json"), json.dumps(ms, indent=2))


async def record_act(meeting: dict, act: str, actor: str, ref_id: str, detail: dict, seed_type: str = "planted") -> None:
    """Record a procedural act: minutes entry, audit log, event, Seed (loud on failure)."""
    meeting["minutes"].append({"type": act, "actor": actor, "ref_id": ref_id, **detail,
                               "timestamp": datetime.now(UTC).isoformat()})
    state.audit.log("governance", act, {"meeting_id": meeting["id"], "actor": actor, "ref_id": ref_id, **detail})
    await state.emit(act, {"meeting_id": meeting["id"], "ref_id": ref_id})
    await create_seed_loud(
        state.audit, act,
        source_type=act, source_id=f"{meeting['id']}-{ref_id}-{actor}", creator_id=actor,
        creator_type="AAI", seed_type=seed_type, metadata={"meeting_id": meeting["id"], "ref_id": ref_id, **detail},
    )


def open_meeting(meeting_id: str) -> tuple[list[dict], dict]:
    meetings = load_meetings()
    meeting = next((m for m in meetings if m["id"] == meeting_id), None)
    if not meeting:
        raise ProcError(404, "Meeting not found")
    if meeting["status"] != "open":
        raise ProcError(409, "Meeting is not open")
    return meetings, meeting


def _find_target(meeting: dict, target_type: str, target_id: str) -> str:
    """Return the motion id for an appealable Chair ruling."""
    if target_type == "point_of_order":
        po = next((p for p in meeting.get("points_of_order", []) if p["id"] == target_id), None)
        if not po:
            raise ProcError(404, "Point of order not found")
        if po["status"] != "ruled":
            raise ProcError(409, "Point of order has not been ruled on")
        return po["motion_id"]
    if target_type == "flame_block":
        mo = next((m for m in meeting["motions"] if m["id"] == target_id), None)
        if not mo:
            raise ProcError(404, "Motion not found")
        if (mo.get("flame_review") or {}).get("result") != "BLOCKED":
            raise ProcError(409, "Motion has no BLOCKED determination")
        return mo["id"]
    raise ProcError(400, "target_type must be point_of_order or flame_block")


def _get_appeal(meeting: dict, appeal_id: str) -> dict:
    ap = next((a for a in meeting.get("appeals", []) if a["id"] == appeal_id), None)
    if not ap:
        raise ProcError(404, "Appeal not found")
    return ap


async def _resolve_appeal(meeting: dict, ap: dict, actor: str) -> None:
    sustain, overturn, outcome = proc.tally_appeal(ap["votes"])
    ap.update(status="resolved", outcome=outcome, resolved_at=datetime.now(UTC).isoformat())
    effect = None
    if outcome == "overturned":
        if ap["target_type"] == "flame_block":
            mo = next(m for m in meeting["motions"] if m["id"] == ap["target_id"])
            mo["appeal_overturned_block"] = True
            mo["appeal_id"] = ap["id"]
            effect = "motion_votable"
        else:
            po = next(p for p in meeting["points_of_order"] if p["id"] == ap["target_id"])
            po["ruling_overturned"] = True
            po["final_ruling"] = "not_sustained" if po["ruling"] == "sustained" else "sustained"
            effect = "ruling_reversed"
    await record_act(meeting, "appeal_resolved", actor, ap["id"],
                     {"outcome": outcome, "sustain": sustain, "overturn": overturn,
                      "motion_id": ap["motion_id"], "effect": effect})


async def raise_point_of_order(meeting_id: str, member: str, motion_id: str, text: str, flame_law: str) -> dict:
    """Any member raises a point of order on a motion (GOV-001 6.1), optionally citing a Flame Law."""
    law = (flame_law or "").strip().upper()
    if not member or not motion_id:
        raise ProcError(400, "member and motion_id required")
    if law and law not in proc.LAW_NAMES:
        raise ProcError(400, f"flame_law must be one of {list(proc.LAW_NAMES)}")
    meetings, meeting = open_meeting(meeting_id)
    if member not in meeting["attendees"]:
        raise ProcError(403, "Member must be an attendee")
    if not any(mo["id"] == motion_id for mo in meeting["motions"]):
        raise ProcError(404, "Motion not found")
    po = {
        "id": f"po-{secrets.token_hex(4)}", "motion_id": motion_id, "raised_by": member,
        "text": sanitize_text(text), "flame_law": law or None, "status": "pending",
        "ruling": None, "ruling_reason": None, "ruled_by": None, "ruled_at": None,
        "raised_at": datetime.now(UTC).isoformat(),
    }
    meeting.setdefault("points_of_order", []).append(po)
    await record_act(meeting, "point_of_order_raised", member, po["id"],
                     {"motion_id": po["motion_id"], "flame_law": po["flame_law"]})
    save_meetings(meetings)
    return po


async def rule_point_of_order(meeting_id: str, po_id: str, chair: str, ruling: str, reason: str) -> dict:
    """The Chair rules on a point of order: sustained | not_sustained (GOV-001 6.1)."""
    ruling = (ruling or "").strip().lower()
    if ruling not in ("sustained", "not_sustained"):
        raise ProcError(400, "ruling must be sustained or not_sustained")
    meetings, meeting = open_meeting(meeting_id)
    if chair != proc.chair_of(meeting):
        raise ProcError(403, "Only the Chair may rule")
    po = next((p for p in meeting.get("points_of_order", []) if p["id"] == po_id), None)
    if not po:
        raise ProcError(404, "Point of order not found")
    if po["status"] != "pending":
        raise ProcError(409, "Point of order already ruled")
    po.update(status="ruled", ruling=ruling, ruling_reason=sanitize_text(reason),
              ruled_by=chair, ruled_at=datetime.now(UTC).isoformat())
    await record_act(meeting, "point_of_order_ruled", chair, po_id,
                     {"motion_id": po["motion_id"], "ruling": ruling, "flame_law": po["flame_law"]})
    save_meetings(meetings)
    return po


async def file_appeal(meeting_id: str, appellant: str, target_type: str, target_id: str, reason: str) -> dict:
    """Appeal a Chair ruling, including a BLOCKED determination (GOV-001 6.2). Needs a second."""
    if not appellant or not target_id:
        raise ProcError(400, "appellant and target_id required")
    meetings, meeting = open_meeting(meeting_id)
    if appellant not in meeting["attendees"]:
        raise ProcError(403, "Appellant must be an attendee")
    motion_id = _find_target(meeting, target_type, target_id)
    if any(a["target_type"] == target_type and a["target_id"] == target_id for a in meeting.get("appeals", [])):
        raise ProcError(409, "This ruling has already been appealed", "already_appealed")
    ap = {
        "id": f"apl-{secrets.token_hex(4)}", "target_type": target_type, "target_id": target_id,
        "motion_id": motion_id, "appellant": appellant, "reason": sanitize_text(reason),
        "status": "awaiting_second", "seconded_by": None, "votes": {}, "outcome": None,
        "appealed_at": datetime.now(UTC).isoformat(), "resolved_at": None,
    }
    meeting.setdefault("appeals", []).append(ap)
    await record_act(meeting, "appeal_filed", appellant, ap["id"],
                     {"target_type": ap["target_type"], "target_id": ap["target_id"], "motion_id": motion_id})
    save_meetings(meetings)
    return ap


async def second_appeal(meeting_id: str, appeal_id: str, member: str) -> dict:
    """A member other than the appellant seconds the appeal; the question is then before the assembly."""
    if not member:
        raise ProcError(400, "member required")
    meetings, meeting = open_meeting(meeting_id)
    ap = _get_appeal(meeting, appeal_id)
    if ap["status"] != "awaiting_second":
        raise ProcError(409, "Appeal is not awaiting a second")
    if member not in meeting["attendees"]:
        raise ProcError(403, "Seconder must be an attendee")
    if member == ap["appellant"]:
        raise ProcError(409, "A second must come from a different member", "self_second")
    ap["seconded_by"] = member
    ap["status"] = "open_for_vote"
    await record_act(meeting, "appeal_seconded", member, appeal_id, {"motion_id": ap["motion_id"]})
    save_meetings(meetings)
    return ap


async def vote_appeal(meeting_id: str, appeal_id: str, voter: str, vote: str) -> dict:
    """Assembly votes sustain|overturn|abstain. Auto-resolves when all attendees voted; tie sustains the Chair."""
    vote = (vote or "").lower().strip()
    if not voter or vote not in ("sustain", "overturn", "abstain"):
        raise ProcError(400, "voter and vote (sustain/overturn/abstain) required")
    meetings, meeting = open_meeting(meeting_id)
    ap = _get_appeal(meeting, appeal_id)
    if ap["status"] != "open_for_vote":
        raise ProcError(409, "Appeal is not open for a vote (needs a second)", "appeal_not_open")
    if voter not in meeting["attendees"]:
        raise ProcError(403, "Voter must be an attendee")
    ap["votes"][voter] = vote
    await record_act(meeting, "appeal_vote_cast", voter, appeal_id, {"vote": vote}, seed_type="touched")
    if len(ap["votes"]) >= len(meeting["attendees"]):
        await _resolve_appeal(meeting, ap, voter)
    save_meetings(meetings)
    return ap


async def close_appeal(meeting_id: str, appeal_id: str, chair: str) -> dict:
    """The Chair announces the result of the appeal vote with the votes cast so far."""
    meetings, meeting = open_meeting(meeting_id)
    if chair != proc.chair_of(meeting):
        raise ProcError(403, "Only the Chair may close the vote")
    ap = _get_appeal(meeting, appeal_id)
    if ap["status"] != "open_for_vote":
        raise ProcError(409, "Appeal is not open for a vote")
    await _resolve_appeal(meeting, ap, chair)
    save_meetings(meetings)
    return ap
