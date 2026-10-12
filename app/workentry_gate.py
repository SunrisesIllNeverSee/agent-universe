"""Constitutional gate consumer - P4 slice 5.

Reads typed governance motions ``{kind: 'work_entry_gate', agreement_id}`` out of the meetings
store, evaluates them under GOV-005 (constitutional quorum = 50% of eligible attendees; async
window >= the configured minimum, default 24 h) and records the result on the Agreement.

Whether the result BINDS is decided in the store (``binding_authority``):
  advisory_with_owner_countersign (default, GOV-001 s9.3) - a passed motion is advisory; an
      owner-held (operator) countersign is the binding act.
  council_delegated - after a two-thirds Council delegation, a passed motion suffices.

Time comes from the store's injectable clock, so tests can advance it.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, UTC
from typing import Any

from app.workentry_store import GATE_QUORUM_FRACTION, WorkEntryStore

GATE_KIND = "work_entry_gate"


def default_motion_text(agreement_id: str) -> str:
    return (f"Constitutional gate for work entry {agreement_id}: the body recommends the entry be "
            "accepted under constitutional governance.")


def window_for(store: WorkEntryStore) -> timedelta:
    return timedelta(hours=store.gate_window_hours)


def open_motion(store: WorkEntryStore, motion: dict[str, Any], agreement_id: str) -> None:
    """Stamp a freshly proposed gate motion with its window (mutates ``motion``)."""
    opened = datetime.fromisoformat(motion["proposed_at"])
    motion["kind"] = GATE_KIND
    motion["agreement_id"] = agreement_id
    motion["closes_at"] = (opened + window_for(store)).isoformat()
    motion["binding"] = False   # the motion result is advisory unless binding_authority says otherwise


def tally(motion: dict[str, Any], eligible: int) -> dict[str, Any]:
    votes = motion.get("votes", {})
    yeas = sum(1 for v in votes.values() if v == "yea")
    nays = sum(1 for v in votes.values() if v == "nay")
    abstain = sum(1 for v in votes.values() if v == "abstain")
    required = max(1, math.ceil(GATE_QUORUM_FRACTION * eligible))
    met = (yeas + nays + abstain) >= required
    return {"yeas": yeas, "nays": nays, "abstain": abstain, "eligible": eligible,
            "quorum_required": required, "quorum_met": met,
            "result": "passed" if (met and yeas > nays) else "failed"}


def sync(store: WorkEntryStore, agreement_id: str, meetings: list[dict]) -> tuple[list[dict], bool, dict]:
    """Evaluate every gate motion for the agreement.

    Returns (meetings, changed, {"open_motions": [...], "recorded": [...]}). ``meetings`` is mutated
    in place; the caller persists it when ``changed``. Recording on the agreement is idempotent per
    motion. A motion resolves only once its window has elapsed (never early, even if all voted).
    """
    now = store.now_dt()
    changed = False
    open_motions, recorded = [], []
    for meeting in meetings:
        eligible = len(meeting.get("attendees", []))
        for motion in meeting.get("motions", []):
            if motion.get("kind") != GATE_KIND or motion.get("agreement_id") != agreement_id:
                continue
            if motion.get("status") == "pending":
                closes = datetime.fromisoformat(motion["closes_at"])
                if now < closes:
                    open_motions.append({"meeting_id": meeting["id"], "motion_id": motion["id"],
                                         "closes_at": motion["closes_at"], "votes_cast": len(motion.get("votes", {})),
                                         "eligible": eligible})
                    continue
                t = tally(motion, eligible)
                motion["status"] = t["result"]
                motion["resolved_at"] = now.astimezone(UTC).isoformat()
                motion["tally"] = t
                meeting.setdefault("minutes", []).append({
                    "type": "motion_resolved", "motion_id": motion["id"], "result": t["result"],
                    "yeas": t["yeas"], "nays": t["nays"], "quorum_met": t["quorum_met"],
                    "timestamp": motion["resolved_at"]})
                changed = True
            if motion.get("status") in ("passed", "failed"):
                t = motion.get("tally") or tally(motion, eligible)
                out = store.record_gate_result(
                    agreement_id, meeting_id=meeting["id"], motion_id=motion["id"], result=motion["status"],
                    yeas=t["yeas"], nays=t["nays"], abstain=t["abstain"], eligible=t["eligible"],
                    quorum_required=t["quorum_required"], quorum_met=t["quorum_met"],
                    opened_at=motion.get("proposed_at"), closes_at=motion.get("closes_at"))
                if not out["replayed"]:
                    recorded.append(out["gate"])
    return meetings, changed, {"open_motions": open_motions, "recorded": recorded}
