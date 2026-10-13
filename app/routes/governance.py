"""
governance.py — Governance, meeting, and flame review endpoints.

Extracted from server.py create_app() monolith.
"""
from __future__ import annotations

import glob as _glob
import json
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.auth import require_agent_claim
from app import civitas_acts as acts
from app import civitas_procedure as proc
from app.deps import state
from app.metrics_io import atomic_write, load_metrics
from app.otel_setup import get_tracer as _get_tracer
from app.sanitize import sanitize_text, sanitize_name
from app.seeds import create_seed, create_seed_loud, _read_seeds
from app.workentry_gate import GATE_KIND, default_motion_text, open_motion
from app.workentry_store import WorkEntryError

router = APIRouter(tags=["governance"])
_tracer = _get_tracer("civitae.governance")


def _tag_span(**attrs) -> None:
    """Add civitae.governance.* attributes to the current request span."""
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        for k, v in attrs.items():
            span.set_attribute(f"civitae.governance.{k}", str(v)[:200])
    except Exception:
        pass


class CallMeetingPayload(BaseModel):
    caller: str = ""
    subject: str = ""
    quorum: int = 3


class JoinMeetingPayload(BaseModel):
    agent_id: str = ""


class ProposeMotionPayload(BaseModel):
    proposer: str = ""
    motion: str = ""
    kind: str = ""          # additive typed motion; "work_entry_gate" binds the motion to an agreement
    agreement_id: str = ""
    flags: list[str] = []   # additive: declared Flame flags (see civitas_procedure.DECLARED_FLAGS)


class PointOfOrderPayload(BaseModel):
    member: str = ""
    motion_id: str = ""
    text: str = ""
    flame_law: str = ""     # optional: I..VI


class RulePayload(BaseModel):
    chair: str = ""
    ruling: str = ""        # sustained | not_sustained
    reason: str = ""


class AppealPayload(BaseModel):
    appellant: str = ""
    target_type: str = ""   # point_of_order | flame_block
    target_id: str = ""     # po id, or motion id for a BLOCKED determination
    reason: str = ""


class SecondPayload(BaseModel):
    member: str = ""


class AppealVotePayload(BaseModel):
    voter: str = ""
    vote: str = ""          # sustain | overturn | abstain


class ClosePayload(BaseModel):
    chair: str = ""


class CastVotePayload(BaseModel):
    voter: str = ""
    motion_id: str = ""
    vote: str = ""


class AdjournMeetingPayload(BaseModel):
    pass

# ── Helpers ─────────────────────────────────────────────────────────────────


_load_meetings = acts.load_meetings
_save_meetings = acts.save_meetings


# ── Governance Sessions ─────────────────────────────────────────────────────


@router.get("/api/governance/sessions")
async def governance_sessions() -> dict:
    """Return available governance sim results for the /governance dashboard."""
    data_dir = state.data_dir
    sessions = []
    for path in sorted(_glob.glob(str(data_dir / "committee_*.json")), reverse=True):
        try:
            with open(path) as f:
                d = json.load(f)
            sessions.append({"type": "committee", "file": Path(path).name, "data": d})
        except Exception:
            pass
    for path in sorted(_glob.glob(str(data_dir / "governance_roberts_*.json")), reverse=True):
        try:
            with open(path) as f:
                d = json.load(f)
            sessions.append({"type": "roberts", "file": Path(path).name, "data": d})
        except Exception:
            pass
    return {"sessions": sessions, "count": len(sessions)}


# ── Roberts Rules — Agent Self-Governance ───────────────────────────────────


@router.post("/api/governance/meeting")
async def call_meeting(payload: CallMeetingPayload, request: Request) -> dict:
    """Call a meeting. Requires a caller (agent_id) and subject."""
    caller = sanitize_name(payload.caller, max_length=80)
    subject = sanitize_text(payload.subject)
    quorum = payload.quorum
    if not caller or not subject:
        return JSONResponse({"error": "caller and subject required"}, status_code=400)
    require_agent_claim(
        request,
        caller,
        registry=state.runtime.registry,
        admin_key=state.admin_key,
        revoked_keys=state.runtime.revoked_keys,
    )
    meetings = _load_meetings()
    meeting = {
        "id": f"mtg-{secrets.token_hex(4)}",
        "caller": caller,
        "chair": caller,
        "subject": subject,
        "quorum": quorum,
        "status": "open",
        "attendees": [caller],
        "motions": [],
        "minutes": [],
        "called_at": datetime.now(UTC).isoformat(),
        "adjourned_at": None,
        "governance_at_call": {
            "mode": state.runtime.governance.mode,
            "posture": state.runtime.governance.posture,
        },
    }
    _tag_span(action="call_meeting", meeting_id=meeting["id"], caller=caller,
              quorum=quorum, mode=state.runtime.governance.mode, posture=state.runtime.governance.posture)
    meetings.append(meeting)
    _save_meetings(meetings)
    state.audit.log("governance", "meeting_called", {"meeting_id": meeting["id"], "caller": caller, "subject": subject})
    await state.emit("meeting_called", {"meeting_id": meeting["id"], "caller": caller, "subject": subject})
    seed_doi = await create_seed_loud(
        state.audit, "meeting_called",
        source_type="meeting_called",
        source_id=meeting["id"],
        creator_id=caller,
        creator_type="AAI",
        seed_type="planted",
        metadata={"meeting_id": meeting["id"], "caller": caller, "subject": subject},
    )
    meeting["seed_doi"] = seed_doi
    return meeting


@router.get("/api/governance/meetings")
async def list_meetings() -> dict:
    return {"meetings": _load_meetings()}


@router.get("/api/governance/meeting/{meeting_id}")
async def get_meeting(meeting_id: str) -> dict:
    meeting = next((m for m in _load_meetings() if m["id"] == meeting_id), None)
    if not meeting:
        return JSONResponse({"error": "Meeting not found"}, status_code=404)
    return {"meeting": meeting}


@router.post("/api/governance/meeting/{meeting_id}/join")
async def join_meeting(meeting_id: str, payload: JoinMeetingPayload, request: Request) -> dict:
    """Agent joins a meeting as attendee."""
    agent_id = payload.agent_id
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    require_agent_claim(
        request,
        agent_id,
        registry=state.runtime.registry,
        admin_key=state.admin_key,
        revoked_keys=state.runtime.revoked_keys,
    )
    meetings = _load_meetings()
    meeting = next((m for m in meetings if m["id"] == meeting_id), None)
    if not meeting:
        return JSONResponse({"error": "Meeting not found"}, status_code=404)
    if meeting["status"] != "open":
        return JSONResponse({"error": "Meeting is not open"}, status_code=409)
    if agent_id not in meeting["attendees"]:
        meeting["attendees"].append(agent_id)
    _save_meetings(meetings)
    meeting["minutes"].append({
        "type": "joined", "agent_id": agent_id,
        "timestamp": datetime.now(UTC).isoformat(),
    })
    _save_meetings(meetings)
    has_quorum = len(meeting["attendees"]) >= meeting["quorum"]
    _tag_span(action="join_meeting", meeting_id=meeting_id, agent_id=agent_id,
              attendees=len(meeting["attendees"]), has_quorum=has_quorum)
    await state.emit("meeting_joined", {"meeting_id": meeting_id, "agent_id": agent_id, "has_quorum": has_quorum})
    seed_doi = await create_seed_loud(
        state.audit, "meeting_joined",
        source_type="meeting_joined",
        source_id=f"{meeting_id}-{agent_id}",
        creator_id=agent_id,
        creator_type="AAI",
        seed_type="planted",
        metadata={"meeting_id": meeting_id, "agent_id": agent_id, "has_quorum": has_quorum},
    )
    return {"meeting_id": meeting_id, "agent_id": agent_id, "attendees": len(meeting["attendees"]), "has_quorum": has_quorum, "seed_doi": seed_doi}


@router.post("/api/governance/meeting/{meeting_id}/motion")
async def propose_motion(meeting_id: str, payload: ProposeMotionPayload, request: Request) -> dict:
    """Propose a motion in a meeting. Requires quorum."""
    proposer = sanitize_name(payload.proposer, max_length=80)
    kind = (payload.kind or "").strip()
    if kind not in ("", GATE_KIND):
        return JSONResponse({"error": f"unknown motion kind {kind!r}"}, status_code=400)
    agreement_id = (payload.agreement_id or "").strip()
    motion_text = sanitize_text(payload.motion)
    if kind == GATE_KIND:
        if not agreement_id:
            return JSONResponse({"error": "work_entry_gate motions require agreement_id"}, status_code=400)
        motion_text = motion_text or default_motion_text(agreement_id)
    elif agreement_id:
        return JSONResponse({"error": "agreement_id is only valid on a typed motion"}, status_code=400)
    if not proposer or not motion_text:
        return JSONResponse({"error": "proposer and motion required"}, status_code=400)
    flags = [str(f).strip() for f in (payload.flags or []) if str(f).strip()]
    bad = [f for f in flags if f not in proc.DECLARED_FLAGS]
    if bad:
        return JSONResponse({"error": f"unknown flags {bad}", "valid": sorted(proc.DECLARED_FLAGS)}, status_code=400)
    require_agent_claim(
        request,
        proposer,
        registry=state.runtime.registry,
        admin_key=state.admin_key,
        revoked_keys=state.runtime.revoked_keys,
    )
    meetings = _load_meetings()
    meeting = next((m for m in meetings if m["id"] == meeting_id), None)
    if not meeting:
        return JSONResponse({"error": "Meeting not found"}, status_code=404)
    if meeting["status"] != "open":
        return JSONResponse({"error": "Meeting is not open"}, status_code=409)
    if len(meeting["attendees"]) < meeting["quorum"]:
        return JSONResponse({"error": f"Quorum not met ({len(meeting['attendees'])}/{meeting['quorum']})"}, status_code=409)
    if proposer not in meeting["attendees"]:
        return JSONResponse({"error": "Proposer must be an attendee"}, status_code=403)
    motion = {
        "id": f"mot-{secrets.token_hex(4)}",
        "proposer": proposer,
        "motion": motion_text,
        "status": "pending",
        "votes": {},
        "proposed_at": datetime.now(UTC).isoformat(),
        "resolved_at": None,
    }
    if kind == GATE_KIND:
        # Typed gate motion (P4 slice 5): must name a live constitutional agreement.
        try:
            agr = state.workentry.get(agreement_id)
        except WorkEntryError as e:
            return JSONResponse({"error": e.message, "code": e.code}, status_code=e.status)
        if agr["entry_mode"] != "constitutional":
            return JSONResponse({"error": "only constitutional work entries are gated", "code": "not_constitutional"},
                                status_code=409)
        if agr["state"] not in ("pending", "dormant"):
            return JSONResponse({"error": f"agreement is '{agr['state']}'; a gate applies before acceptance",
                                 "code": "invalid_transition"}, status_code=409)
        if any(mo.get("kind") == GATE_KIND and mo.get("agreement_id") == agreement_id
               and mo.get("status") == "pending" for mt in meetings for mo in mt["motions"]):
            return JSONResponse({"error": "a gate motion for this agreement is already open",
                                 "code": "gate_motion_open"}, status_code=409)
        open_motion(state.workentry, motion, agreement_id)
    motion["flame_review"] = proc.review_motion(motion_text, flags)
    meeting["motions"].append(motion)
    meeting["minutes"].append({
        "type": "motion_proposed", "motion_id": motion["id"],
        "proposer": proposer, "motion": motion_text,
        "timestamp": datetime.now(UTC).isoformat(),
    })
    meeting["minutes"].append({
        "type": "flame_review", "motion_id": motion["id"],
        "result": motion["flame_review"]["result"],
        "laws_cited": [c["law"] for c in motion["flame_review"]["laws_cited"]],
        "timestamp": datetime.now(UTC).isoformat(),
    })
    _save_meetings(meetings)
    state.audit.log("governance", "flame_review_motion", {
        "meeting_id": meeting_id, "motion_id": motion["id"],
        "result": motion["flame_review"]["result"],
        "laws_cited": [c["law"] for c in motion["flame_review"]["laws_cited"]],
    })
    _tag_span(action="propose_motion", meeting_id=meeting_id, motion_id=motion["id"], proposer=proposer)
    state.audit.log("governance", "motion_proposed", {"meeting_id": meeting_id, "motion_id": motion["id"], "proposer": proposer})
    await state.emit("motion_proposed", {"meeting_id": meeting_id, "motion_id": motion["id"], "motion": motion_text})

    await create_seed_loud(
        state.audit, "motion",
        source_type="motion",
        source_id=motion["id"],
        creator_id=proposer,
        creator_type="AAI",
        seed_type="planted",
        metadata={"meeting_id": meeting_id, "motion": motion_text},
    )

    return motion


@router.post("/api/governance/meeting/{meeting_id}/vote")
async def cast_vote(meeting_id: str, payload: CastVotePayload, request: Request) -> dict:
    """Cast a vote on a pending motion. Votes: yea, nay, abstain."""
    voter = sanitize_name(payload.voter, max_length=80)
    motion_id = payload.motion_id
    vote = payload.vote.lower().strip()
    if not voter or not motion_id or vote not in ("yea", "nay", "abstain"):
        return JSONResponse({"error": "voter, motion_id, and vote (yea/nay/abstain) required"}, status_code=400)
    require_agent_claim(
        request,
        voter,
        registry=state.runtime.registry,
        admin_key=state.admin_key,
        revoked_keys=state.runtime.revoked_keys,
    )
    meetings = _load_meetings()
    meeting = next((m for m in meetings if m["id"] == meeting_id), None)
    if not meeting:
        return JSONResponse({"error": "Meeting not found"}, status_code=404)
    if meeting["status"] != "open":
        return JSONResponse({"error": "Meeting is not open"}, status_code=409)
    if voter not in meeting["attendees"]:
        return JSONResponse({"error": "Voter must be an attendee"}, status_code=403)
    motion = next((mo for mo in meeting["motions"] if mo["id"] == motion_id), None)
    if not motion:
        return JSONResponse({"error": "Motion not found"}, status_code=404)
    if motion["status"] != "pending":
        return JSONResponse({"error": "Motion is not pending"}, status_code=409)
    if proc.motion_is_blocked(motion):
        # GOV-001 5.3: the only enforced procedural rule; the meeting judges the rest.
        return JSONResponse({"error": "Motion is BLOCKED; no vote may be called except through appeal (GOV-001 5.3, 6.2)",
                             "code": "motion_blocked"}, status_code=409)
    if motion.get("kind") == GATE_KIND and motion.get("closes_at"):
        # GOV-005 window: a typed gate motion takes no votes at or after closes_at
        if state.workentry.now_dt() >= datetime.fromisoformat(motion["closes_at"]):
            return JSONResponse({"error": "Voting window for this motion has closed", "code": "gate_window_closed"},
                                status_code=409)
    motion["votes"][voter] = vote
    meeting["minutes"].append({
        "type": "vote_cast", "motion_id": motion_id,
        "voter": voter, "vote": vote,
        "timestamp": datetime.now(UTC).isoformat(),
    })
    # Auto-resolve when all attendees have voted (typed gate motions resolve only through the gate
    # consumer once their GOV-005 window has elapsed)
    if motion.get("kind") != GATE_KIND and len(motion["votes"]) >= len(meeting["attendees"]):
        yeas = sum(1 for v in motion["votes"].values() if v == "yea")
        nays = sum(1 for v in motion["votes"].values() if v == "nay")
        motion["status"] = "passed" if yeas > nays else "failed"
        motion["resolved_at"] = datetime.now(UTC).isoformat()
        meeting["minutes"].append({
            "type": "motion_resolved", "motion_id": motion_id,
            "result": motion["status"], "yeas": yeas, "nays": nays,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        _tag_span(action="cast_vote", meeting_id=meeting_id, motion_id=motion_id,
                  voter=voter, vote=vote, auto_resolved=True,
                  result=motion["status"], yeas=yeas, nays=nays)
        state.audit.log("governance", "motion_resolved", {
            "meeting_id": meeting_id, "motion_id": motion_id,
            "result": motion["status"], "yeas": yeas, "nays": nays,
        })
        await state.emit("motion_resolved", {"meeting_id": meeting_id, "motion_id": motion_id, "result": motion["status"]})
    _save_meetings(meetings)
    _tag_span(action="cast_vote", meeting_id=meeting_id, motion_id=motion_id,
              voter=voter, vote=vote, votes_cast=len(motion["votes"]),
              total_voters=len(meeting["attendees"]))

    await create_seed_loud(
        state.audit, "vote",
        source_type="vote",
        source_id=f"{meeting_id}-{motion_id}-{voter}",
        creator_id=voter,
        creator_type="AAI",
        seed_type="touched",
        metadata={"meeting_id": meeting_id, "motion_id": motion_id, "vote": vote},
    )

    return {"motion_id": motion_id, "voter": voter, "vote": vote, "votes_cast": len(motion["votes"]), "total_voters": len(meeting["attendees"])}


# ── Points of Order and Appeals (GOV-001 Art 6) ─────────────────────────────
# Logic is shared with the MCP tools in app/civitas_acts.py; these are thin
# wrappers: bind the actor's identity, run the act, map ProcError to JSON.


def _claim(request: Request, agent: str) -> None:
    require_agent_claim(request, agent, registry=state.runtime.registry,
                        admin_key=state.admin_key, revoked_keys=state.runtime.revoked_keys)


async def _run_act(request: Request, actor: str, act, *args):
    _claim(request, actor)
    try:
        return await act(*args)
    except acts.ProcError as e:
        return JSONResponse(e.body, status_code=e.status)


@router.post("/api/governance/meeting/{meeting_id}/point-of-order")
async def raise_point_of_order(meeting_id: str, payload: PointOfOrderPayload, request: Request) -> dict:
    """Any member raises a point of order on a motion (GOV-001 6.1), optionally citing a Flame Law."""
    member = sanitize_name(payload.member, max_length=80)
    return await _run_act(request, member, acts.raise_point_of_order,
                          meeting_id, member, payload.motion_id, payload.text, payload.flame_law)


@router.post("/api/governance/meeting/{meeting_id}/point-of-order/{po_id}/rule")
async def rule_point_of_order(meeting_id: str, po_id: str, payload: RulePayload, request: Request) -> dict:
    """The Chair rules on a point of order: sustained | not_sustained (GOV-001 6.1)."""
    chair = sanitize_name(payload.chair, max_length=80)
    return await _run_act(request, chair, acts.rule_point_of_order,
                          meeting_id, po_id, chair, payload.ruling, payload.reason)


@router.post("/api/governance/meeting/{meeting_id}/appeal")
async def appeal_ruling(meeting_id: str, payload: AppealPayload, request: Request) -> dict:
    """Appeal a Chair ruling, including a BLOCKED determination (GOV-001 6.2). Needs a second."""
    appellant = sanitize_name(payload.appellant, max_length=80)
    return await _run_act(request, appellant, acts.file_appeal,
                          meeting_id, appellant, payload.target_type, payload.target_id, payload.reason)


@router.post("/api/governance/meeting/{meeting_id}/appeal/{appeal_id}/second")
async def second_appeal(meeting_id: str, appeal_id: str, payload: SecondPayload, request: Request) -> dict:
    """A member other than the appellant seconds the appeal; the question is then before the assembly."""
    member = sanitize_name(payload.member, max_length=80)
    return await _run_act(request, member, acts.second_appeal, meeting_id, appeal_id, member)


@router.post("/api/governance/meeting/{meeting_id}/appeal/{appeal_id}/vote")
async def vote_appeal(meeting_id: str, appeal_id: str, payload: AppealVotePayload, request: Request) -> dict:
    """Assembly votes sustain|overturn|abstain. Auto-resolves when all attendees voted; tie sustains the Chair."""
    voter = sanitize_name(payload.voter, max_length=80)
    return await _run_act(request, voter, acts.vote_appeal, meeting_id, appeal_id, voter, payload.vote)


@router.post("/api/governance/meeting/{meeting_id}/appeal/{appeal_id}/close")
async def close_appeal(meeting_id: str, appeal_id: str, payload: ClosePayload, request: Request) -> dict:
    """The Chair announces the result of the appeal vote with the votes cast so far."""
    chair = sanitize_name(payload.chair, max_length=80)
    return await _run_act(request, chair, acts.close_appeal, meeting_id, appeal_id, chair)


@router.post("/api/governance/meeting/{meeting_id}/adjourn")
async def adjourn_meeting(meeting_id: str, request: Request, payload: AdjournMeetingPayload | None = None) -> dict:
    """Adjourn a meeting. Only the caller or by majority vote."""
    meetings = _load_meetings()
    meeting = next((m for m in meetings if m["id"] == meeting_id), None)
    if not meeting:
        return JSONResponse({"error": "Meeting not found"}, status_code=404)
    if meeting["status"] != "open":
        return JSONResponse({"error": "Meeting already adjourned"}, status_code=409)
    require_agent_claim(
        request,
        str(meeting.get("caller") or ""),
        registry=state.runtime.registry,
        admin_key=state.admin_key,
        revoked_keys=state.runtime.revoked_keys,
    )
    meeting["status"] = "adjourned"
    meeting["adjourned_at"] = datetime.now(UTC).isoformat()
    meeting["minutes"].append({
        "type": "adjourned",
        "timestamp": datetime.now(UTC).isoformat(),
    })
    _save_meetings(meetings)
    motions_total = len(meeting.get("motions", []))
    motions_passed = sum(1 for m in meeting.get("motions", []) if m.get("status") == "passed")
    _tag_span(action="adjourn_meeting", meeting_id=meeting_id,
              attendees=len(meeting.get("attendees", [])),
              motions_total=motions_total, motions_passed=motions_passed)
    state.audit.log("governance", "meeting_adjourned", {"meeting_id": meeting_id})
    await state.emit("meeting_adjourned", {"meeting_id": meeting_id})
    await create_seed_loud(
        state.audit, "meeting_adjourned",
        source_type="meeting_adjourned",
        source_id=meeting_id,
        creator_id="operator",
        creator_type="BI",
        seed_type="planted",
        metadata={"meeting_id": meeting_id},
    )
    return meeting


# ── Flame Review Engine v1 ──────────────────────────────────────────────────
# Rule-based compliance check against the Six Fold Flame.
# Each flame dimension scores 0-1. Overall = average of 6.

FLAME_DIMENSIONS = {
    "security": {"weight": 1.0, "checks": ["governance_active", "dual_signature", "no_violations_30d"]},
    "integrity": {"weight": 1.0, "checks": ["compliance_score_above_80", "lineage_verified"]},
    "creativity": {"weight": 1.0, "checks": ["missions_completed_min_1", "diverse_capabilities"]},
    "research": {"weight": 1.0, "checks": ["seeds_created", "provenance_chain"]},
    "problem_solving": {"weight": 1.0, "checks": ["missions_completed_min_1", "stakes_active"]},
    "governance": {"weight": 1.0, "checks": ["governance_active", "votes_cast", "motions_proposed"]},
}


@router.get("/api/governance/flame-review/{agent_id}")
async def flame_review(agent_id: str) -> dict:
    """Six Fold Flame compliance review for an agent."""
    agent = next(
        (r for r in state.runtime.registry if r.get("type") == "agent" and
         (r.get("agent_id") == agent_id or r.get("name") == agent_id)),
        None,
    )
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)

    aid = agent.get("agent_id", agent_id)
    metrics_data = load_metrics()
    agent_m = metrics_data.get("agents", {}).get(aid, {})
    gov_active = bool(agent.get("governance") and agent.get("governance") != "none_(unrestricted)")
    compliance = agent.get("compliance_score", agent_m.get("compliance_score", 0))
    missions = agent.get("missions_completed", agent_m.get("missions_completed", 0))
    violations = agent.get("governance_violations", agent_m.get("governance_violations", 0))
    has_lineage = agent.get("lineage_verified", False)
    has_dual_sig = agent.get("dual_signature", False)
    capabilities = agent.get("capabilities", [])

    # FIX-13: Count seeds for this agent. _read_seeds() loads the full JSONL
    # file — acceptable at current scale (<10K seeds) but should migrate to
    # indexed SQLite query if seed volume grows significantly post-launch.
    seeds = _read_seeds()
    agent_seeds = [s for s in seeds if s.get("creator_id") == aid]

    # Count governance participation
    votes_cast = 0
    motions_proposed = 0
    try:
        meetings_file = state.data_path("meetings.json")
        meetings_data = json.loads(meetings_file.read_text()) if meetings_file.exists() else []
        agent_name = agent.get("name", "")
        for meeting in meetings_data:
            for motion in meeting.get("motions", []):
                if motion.get("proposer") in (aid, agent_name):
                    motions_proposed += 1
                # votes is a dict {voter_id: "yea"/"nay"/"abstain"}
                votes_dict = motion.get("votes", {})
                if isinstance(votes_dict, dict):
                    if aid in votes_dict or agent_name in votes_dict:
                        votes_cast += 1
    except Exception:
        pass

    # Count active stakes
    stakes = state.kassa.load_stakes(agent_id=aid)

    # Score each flame dimension
    scores = {}
    details = {}

    # Security
    sec_score = 0.0
    sec_notes = []
    if gov_active:
        sec_score += 0.4; sec_notes.append("governance active")
    if has_dual_sig:
        sec_score += 0.3; sec_notes.append("dual signature")
    if violations == 0:
        sec_score += 0.3; sec_notes.append("zero violations (30d)")
    scores["security"] = min(sec_score, 1.0)
    details["security"] = sec_notes

    # Integrity
    int_score = 0.0
    int_notes = []
    if compliance >= 0.8:
        int_score += 0.5; int_notes.append(f"compliance {compliance:.0%}")
    elif compliance >= 0.5:
        int_score += 0.25; int_notes.append(f"compliance {compliance:.0%} (partial)")
    if has_lineage:
        int_score += 0.5; int_notes.append("lineage verified")
    scores["integrity"] = min(int_score, 1.0)
    details["integrity"] = int_notes

    # Creativity
    cre_score = 0.0
    cre_notes = []
    if missions >= 1:
        cre_score += 0.5; cre_notes.append(f"{missions} missions completed")
    if len(capabilities) >= 2:
        cre_score += 0.5; cre_notes.append(f"{len(capabilities)} capabilities")
    scores["creativity"] = min(cre_score, 1.0)
    details["creativity"] = cre_notes

    # Research
    res_score = 0.0
    res_notes = []
    if len(agent_seeds) >= 1:
        res_score += 0.5; res_notes.append(f"{len(agent_seeds)} seeds created")
    if any(s.get("parent_doi") for s in agent_seeds):
        res_score += 0.5; res_notes.append("provenance chain exists")
    scores["research"] = min(res_score, 1.0)
    details["research"] = res_notes

    # Problem Solving
    ps_score = 0.0
    ps_notes = []
    if missions >= 1:
        ps_score += 0.5; ps_notes.append(f"{missions} missions")
    if len(stakes) >= 1:
        ps_score += 0.5; ps_notes.append(f"{len(stakes)} active stakes")
    scores["problem_solving"] = min(ps_score, 1.0)
    details["problem_solving"] = ps_notes

    # Governance
    gov_score = 0.0
    gov_notes = []
    if gov_active:
        gov_score += 0.34; gov_notes.append("governance active")
    if votes_cast >= 1:
        gov_score += 0.33; gov_notes.append(f"{votes_cast} votes cast")
    if motions_proposed >= 1:
        gov_score += 0.33; gov_notes.append(f"{motions_proposed} motions proposed")
    scores["governance"] = min(gov_score, 1.0)
    details["governance"] = gov_notes

    overall = round(sum(scores.values()) / 6, 3)
    lit_flames = sum(1 for v in scores.values() if v >= 0.5)

    state.audit.log("governance", "flame_review", {"agent_id": aid, "overall": overall, "lit": f"{lit_flames}/6"})

    return {
        "agent_id": aid,
        "agent_name": agent.get("name", aid),
        "flame_score": overall,
        "flames_lit": f"{lit_flames}/6",
        "dimensions": {k: {"score": round(v, 3), "details": details[k]} for k, v in scores.items()},
        "tier": state.economy.determine_tier({
            "governance_active": gov_active, "compliance_score": compliance,
            "missions_completed": missions, "governance_violations": violations,
            "lineage_verified": has_lineage, "dual_signature": has_dual_sig,
        }),
        "recommendation": (
            "All six flames lit — Constitutional candidate" if lit_flames == 6
            else f"{lit_flames}/6 flames lit — focus on: {', '.join(k for k, v in scores.items() if v < 0.5)}"
        ),
    }
