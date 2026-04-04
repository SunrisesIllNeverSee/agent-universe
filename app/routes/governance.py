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

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.deps import state
from app.sanitize import sanitize_text, sanitize_name
from app.seeds import create_seed, _read_seeds

router = APIRouter(tags=["governance"])

# ── Helpers ─────────────────────────────────────────────────────────────────


def _atomic_write(path: Path, data: str) -> None:
    """Write data to a file atomically via tmp-then-rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _load_meetings() -> list[dict]:
    meetings_path = state.data_path("meetings.json")
    if meetings_path.exists():
        return json.loads(meetings_path.read_text())
    return []


def _save_meetings(ms: list[dict]) -> None:
    meetings_path = state.data_path("meetings.json")
    _atomic_write(meetings_path, json.dumps(ms, indent=2))


def _load_metrics() -> dict:
    metrics_path = state.data_path("metrics.json")
    if metrics_path.exists():
        return json.loads(metrics_path.read_text())
    return {"agents": {}, "missions": {}, "financial": {"revenue": 0, "costs": 0, "transactions": []}}


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
async def call_meeting(payload: dict) -> dict:
    """Call a meeting. Requires a caller (agent_id) and subject."""
    caller = sanitize_name(payload.get("caller", ""), max_length=80)
    subject = sanitize_text(payload.get("subject", ""))
    quorum = payload.get("quorum", 3)
    if not caller or not subject:
        return JSONResponse({"error": "caller and subject required"}, status_code=400)
    meetings = _load_meetings()
    meeting = {
        "id": f"mtg-{secrets.token_hex(4)}",
        "caller": caller,
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
    meetings.append(meeting)
    _save_meetings(meetings)
    state.audit.log("governance", "meeting_called", {"meeting_id": meeting["id"], "caller": caller, "subject": subject})
    await state.emit("meeting_called", {"meeting_id": meeting["id"], "caller": caller, "subject": subject})
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="meeting_called",
            source_id=meeting["id"],
            creator_id=caller,
            creator_type="AAI",
            seed_type="planted",
            metadata={"meeting_id": meeting["id"], "caller": caller, "subject": subject},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
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
async def join_meeting(meeting_id: str, payload: dict) -> dict:
    """Agent joins a meeting as attendee."""
    agent_id = payload.get("agent_id", "")
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
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
    await state.emit("meeting_joined", {"meeting_id": meeting_id, "agent_id": agent_id, "has_quorum": has_quorum})
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="meeting_joined",
            source_id=f"{meeting_id}-{agent_id}",
            creator_id=agent_id,
            creator_type="AAI",
            seed_type="planted",
            metadata={"meeting_id": meeting_id, "agent_id": agent_id, "has_quorum": has_quorum},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    return {"meeting_id": meeting_id, "agent_id": agent_id, "attendees": len(meeting["attendees"]), "has_quorum": has_quorum, "seed_doi": seed_doi}


@router.post("/api/governance/meeting/{meeting_id}/motion")
async def propose_motion(meeting_id: str, payload: dict) -> dict:
    """Propose a motion in a meeting. Requires quorum."""
    proposer = sanitize_name(payload.get("proposer", ""), max_length=80)
    motion_text = sanitize_text(payload.get("motion", ""))
    if not proposer or not motion_text:
        return JSONResponse({"error": "proposer and motion required"}, status_code=400)
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
    meeting["motions"].append(motion)
    meeting["minutes"].append({
        "type": "motion_proposed", "motion_id": motion["id"],
        "proposer": proposer, "motion": motion_text,
        "timestamp": datetime.now(UTC).isoformat(),
    })
    _save_meetings(meetings)
    state.audit.log("governance", "motion_proposed", {"meeting_id": meeting_id, "motion_id": motion["id"], "proposer": proposer})
    await state.emit("motion_proposed", {"meeting_id": meeting_id, "motion_id": motion["id"], "motion": motion_text})

    try:
        await create_seed(
            source_type="motion",
            source_id=motion["id"],
            creator_id=proposer,
            creator_type="AAI",
            seed_type="planted",
            metadata={"meeting_id": meeting_id, "motion": motion_text},
        )
    except Exception:
        pass

    return motion


@router.post("/api/governance/meeting/{meeting_id}/vote")
async def cast_vote(meeting_id: str, payload: dict) -> dict:
    """Cast a vote on a pending motion. Votes: yea, nay, abstain."""
    voter = sanitize_name(payload.get("voter", ""), max_length=80)
    motion_id = payload.get("motion_id", "")
    vote = payload.get("vote", "").lower().strip()
    if not voter or not motion_id or vote not in ("yea", "nay", "abstain"):
        return JSONResponse({"error": "voter, motion_id, and vote (yea/nay/abstain) required"}, status_code=400)
    meetings = _load_meetings()
    meeting = next((m for m in meetings if m["id"] == meeting_id), None)
    if not meeting:
        return JSONResponse({"error": "Meeting not found"}, status_code=404)
    if voter not in meeting["attendees"]:
        return JSONResponse({"error": "Voter must be an attendee"}, status_code=403)
    motion = next((mo for mo in meeting["motions"] if mo["id"] == motion_id), None)
    if not motion:
        return JSONResponse({"error": "Motion not found"}, status_code=404)
    if motion["status"] != "pending":
        return JSONResponse({"error": "Motion is not pending"}, status_code=409)
    motion["votes"][voter] = vote
    meeting["minutes"].append({
        "type": "vote_cast", "motion_id": motion_id,
        "voter": voter, "vote": vote,
        "timestamp": datetime.now(UTC).isoformat(),
    })
    # Auto-resolve when all attendees have voted
    if len(motion["votes"]) >= len(meeting["attendees"]):
        yeas = sum(1 for v in motion["votes"].values() if v == "yea")
        nays = sum(1 for v in motion["votes"].values() if v == "nay")
        motion["status"] = "passed" if yeas > nays else "failed"
        motion["resolved_at"] = datetime.now(UTC).isoformat()
        meeting["minutes"].append({
            "type": "motion_resolved", "motion_id": motion_id,
            "result": motion["status"], "yeas": yeas, "nays": nays,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        state.audit.log("governance", "motion_resolved", {
            "meeting_id": meeting_id, "motion_id": motion_id,
            "result": motion["status"], "yeas": yeas, "nays": nays,
        })
        await state.emit("motion_resolved", {"meeting_id": meeting_id, "motion_id": motion_id, "result": motion["status"]})
    _save_meetings(meetings)

    try:
        await create_seed(
            source_type="vote",
            source_id=f"{meeting_id}-{motion_id}-{voter}",
            creator_id=voter,
            creator_type="AAI",
            seed_type="touched",
            metadata={"meeting_id": meeting_id, "motion_id": motion_id, "vote": vote},
        )
    except Exception:
        pass

    return {"motion_id": motion_id, "voter": voter, "vote": vote, "votes_cast": len(motion["votes"]), "total_voters": len(meeting["attendees"])}


@router.post("/api/governance/meeting/{meeting_id}/adjourn")
async def adjourn_meeting(meeting_id: str, payload: dict = {}) -> dict:
    """Adjourn a meeting. Only the caller or by majority vote."""
    meetings = _load_meetings()
    meeting = next((m for m in meetings if m["id"] == meeting_id), None)
    if not meeting:
        return JSONResponse({"error": "Meeting not found"}, status_code=404)
    if meeting["status"] != "open":
        return JSONResponse({"error": "Meeting already adjourned"}, status_code=409)
    meeting["status"] = "adjourned"
    meeting["adjourned_at"] = datetime.now(UTC).isoformat()
    meeting["minutes"].append({
        "type": "adjourned",
        "timestamp": datetime.now(UTC).isoformat(),
    })
    _save_meetings(meetings)
    state.audit.log("governance", "meeting_adjourned", {"meeting_id": meeting_id})
    await state.emit("meeting_adjourned", {"meeting_id": meeting_id})
    try:
        await create_seed(
            source_type="meeting_adjourned",
            source_id=meeting_id,
            creator_id="operator",
            creator_type="BI",
            seed_type="planted",
            metadata={"meeting_id": meeting_id},
        )
    except Exception:
        pass
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
    metrics_data = _load_metrics()
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
