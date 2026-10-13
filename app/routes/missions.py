"""
missions.py — Missions, Campaigns, Tasks, and Slots endpoints.

Extracted from server.py create_app() monolith.
Covers:
  - DEPLOY missions (create, list, get, update, end)
  - Campaigns (create, list, get, close, activate, add_mission)
  - Tasks (create, list, get, assign, start, deliver, close, cancel)
  - Slots (create from formation, list, open, fill, leave, bounty)
"""
from __future__ import annotations

import json
import math
import os
import secrets as _secrets_mod
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any

from app.auth import active_agent_from_bearer, admin_key_matches, require_agent_claim
from app.deps import state
from app.metrics_io import atomic_write
from app.otel_setup import get_tracer as _get_tracer
from app.seeds import create_seed, create_seed_loud
from app import slot_binding
from app.escrow import EscrowError
from app.routes.escrow import refund_to_poster, release_to

router = APIRouter(tags=["missions"])
_tracer = _get_tracer("civitae.missions")


def _tag_span(**attrs) -> None:
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        for k, v in attrs.items():
            span.set_attribute(f"civitae.mission.{k}", str(v)[:200])
    except Exception:
        pass


class CreateMissionPayload(BaseModel):
    label: str = ""
    objective: str = ""
    posture: str = "SCOUT"
    formation: str = ""
    target: str = ""
    duration: str = "sprint"
    limits: str = ""
    systems: dict[str, Any] = {}
    agents: dict[str, Any] = {}
    channel: str = ""
    agent_id: str = "operator"
    entry_mode: str = ""
    post_id: str = ""


class EndMissionPayload(BaseModel):
    payout_per_slot: float = 0
    originator_id: str = ""


class UpdateMissionPayload(BaseModel):
    posture: str | None = None
    formation: str | None = None
    status: str | None = None
    target: str | None = None
    limits: str | None = None


class CreateCampaignPayload(BaseModel):
    name: str = ""
    objective: str = ""
    created_by: str = ""
    ecosystems: list[str] = []
    revenue_target: str = ""


class AddMissionToCampaignPayload(BaseModel):
    mission_id: str = ""


class CloseCampaignPayload(BaseModel):
    outcome: str = ""


class CreateTaskPayload(BaseModel):
    title: str
    type: str = "build"
    track: str = "tool"
    objective: str = ""
    target: str = ""
    exp_reward: int | None = None
    payout: float = 0.0
    operation_id: str | None = None
    campaign_id: str | None = None
    mission_id: str | None = None
    created_by: str = "operator"


class AssignTaskPayload(BaseModel):
    agent_id: str = ""


class DeliverTaskPayload(BaseModel):
    deliverable: str = ""


class CloseTaskPayload(BaseModel):
    requestor: str = ""


class CreateSlotsPayload(BaseModel):
    mission_id: str = ""
    formation_id: str = ""
    posture: str = "SCOUT"
    label: str = ""
    positions: list[dict[str, Any]] = []
    roles: list[str] = []
    revenue_splits: list[int] = []
    governance_mode: str = ""
    entry_mode: str = ""          # open (default) | standard | constitutional
    post_id: str = ""             # the post this slot serves (poster-owned)
    agreement_id: str = ""        # an existing WorkEntryAgreement this references


class FillSlotPayload(BaseModel):
    slot_id: str = ""
    agent_id: str = ""
    agent_name: str = ""


class LeaveSlotPayload(BaseModel):
    slot_id: str = ""
    agent_id: str = ""


class PostBountyPayload(BaseModel):
    agent_id: str = ""
    agent_name: str = ""
    label: str = ""
    description: str = ""
    posture: str = "SCOUT"
    slots_needed: int = 3
    revenue_pool: float = 0
    entry_mode: str = ""
    post_id: str = ""
    agreement_id: str = ""

# ── JSON file loaders / savers ───────────────────────────────────────────────
# FIX-12: JSON file-backed state — missions, slots, tasks, campaigns, metrics.
# Each _load_*() re-reads from disk on every call. This is simple and correct
# (no stale cache, atomic writes guarantee consistency) but becomes an I/O
# bottleneck at high traffic. If needed post-launch, add an in-memory cache
# with TTL or migrate hot paths to SQLite (like kassa/forums already use).


def _missions_path() -> Path:
    return state.data_path("missions.json")


def _campaigns_path() -> Path:
    return state.data_path("campaigns.json")


def _tasks_path() -> Path:
    return state.data_path("tasks.json")


def _slots_path() -> Path:
    return state.data_path("slots.json")


def _load_missions() -> list[dict]:
    p = _missions_path()
    if p.exists():
        rows = json.loads(p.read_text())
        for m in rows:   # P4 slice 4: additive fields, legacy records default to open
            m.setdefault("entry_mode", "open")
            m.setdefault("post_id", None)
            m.setdefault("agreement_id", None)
        return rows
    return []


def _save_missions(missions: list[dict]) -> None:
    atomic_write(_missions_path(), json.dumps(missions, indent=2))


def _load_campaigns() -> list[dict]:
    p = _campaigns_path()
    if p.exists():
        return json.loads(p.read_text())
    return []


def _save_campaigns(campaigns: list[dict]) -> None:
    atomic_write(_campaigns_path(), json.dumps(campaigns, indent=2))


def _load_tasks() -> list[dict]:
    p = _tasks_path()
    if p.exists():
        return json.loads(p.read_text())
    return []


def _save_tasks(tasks: list[dict]) -> None:
    atomic_write(_tasks_path(), json.dumps(tasks, indent=2))


def _load_slots() -> list[dict]:
    p = _slots_path()
    if p.exists():
        rows = json.loads(p.read_text())
        for sl in rows:  # P4 slice 4: additive fields, legacy records default to open
            sl.setdefault("entry_mode", "open")
            sl.setdefault("post_id", None)
            sl.setdefault("agreement_id", None)
        return rows
    return []


def _save_slots(slots: list[dict]) -> None:
    atomic_write(_slots_path(), json.dumps(slots, indent=2))


# ── Task EXP base values ────────────────────────────────────────────────────

TASK_EXP_BASE: dict[str, int] = {
    "build":    150,
    "collect":   75,
    "acquire":  100,
    "research": 125,
    "verify":   100,
    "create":   150,
    "scout":     75,
    "guard":     50,
}


def _award_exp(agent_id: str, exp: int, track: str) -> dict:
    """Credit EXP to an agent and persist it. Returns updated exp summary.

    EXP lives on the registry entry, which is only durable once written back
    to provision.json — without the persist it was lost on restart.
    """
    agent = next((r for r in state.runtime.registry if r.get("agent_id") == agent_id), None)
    if not agent:
        return {}
    agent.setdefault("exp", 0)
    agent.setdefault("exp_by_track", {"research": 0, "tool": 0, "creative": 0})
    agent["exp"] += exp
    agent["exp_by_track"][track] = agent["exp_by_track"].get(track, 0) + exp
    state.runtime.persist_registry()
    return {"exp": agent["exp"], "exp_by_track": agent["exp_by_track"]}


# ══════════════════════════════════════════════════════════════════════════════
# MISSIONS (DEPLOY)
# ══════════════════════════════════════════════════════════════════════════════


# ── Mission principal binding (D-B) ──────────────────────────────────────────
# A mission records the authentic agent that created it (`owner_agent_id`,
# derived server-side from the live, non-revoked Bearer API key — never from
# the request body). Agent mutations (end/update/slot-create) require that
# same principal; a valid admin key keeps operator authority. Missions with no
# recorded owner (legacy, or operator-created) fail closed for agents.

def _acting_agent_id(request: Request) -> str | None:
    """Agent id of the live Bearer principal, or None for admin/operator.

    Admin key wins (operator authority). Otherwise the Bearer key must resolve
    to an active, non-revoked agent. With neither, only the no-admin-key local
    dev path (already authorized by the server middleware) is treated as
    operator; anything else is rejected.
    """
    if admin_key_matches(request, state.admin_key):
        return None
    principal = active_agent_from_bearer(
        request, state.runtime.registry, state.runtime.revoked_keys
    )
    if principal is not None:
        agent_id = str(principal.get("agent_id") or "")
        if agent_id:
            return agent_id
    if not state.admin_key:
        return None
    raise HTTPException(401, "Active agent API key or admin key required")


def _agent_may_mutate(agent_id: str | None, mission: dict) -> bool:
    """Operator (None) always; an agent only as the recorded owner."""
    if agent_id is None:
        return True
    owner = mission.get("owner_agent_id")
    return bool(owner) and owner == agent_id


def _mission_not_found(mission_id: str) -> JSONResponse:
    """The single 404 body for unknown / other-owner / ownerless-legacy ids."""
    return JSONResponse({"error": "Mission not found", "mission_id": mission_id}, status_code=404)


MAX_SLOT_PAYOUT = 1_000_000.0


async def _payout_seed(result: dict, *, source: str) -> dict:
    """One Seed per payout (P5 s2), loud on failure.

    The ledger credit has already happened; a failed Seed is never silent:
    it is audited as provenance_failed and returned so the caller surfaces it.
    """
    fee = result.get("fee_breakdown") or {}
    meta = {"action": "mission_payout", "source": source, "agent_id": result.get("agent_id"),
            "mission_id": result.get("mission_id"), "tier": result.get("tier"),
            "trial": result.get("trial", False), "gross": fee.get("gross_amount", fee.get("gross")),
            "platform_fee": fee.get("platform_fee"), "net_to_agent": fee.get("net_to_agent")}
    try:
        seed = await create_seed(source_type="mission_payout", source_id=str(result.get("mission_id") or ""),
                                 creator_id=str(result.get("agent_id") or ""), creator_type="AAI",
                                 seed_type="grown", metadata=meta)
        if seed and seed.get("doi"):
            return {"doi": seed["doi"]}
        raise RuntimeError("create_seed returned no doi")
    except Exception as exc:
        state.audit.log("economy", "provenance_failed", {**meta, "error": str(exc)[:200]})
        return {"doi": None, "error": str(exc)[:200]}


def _mission_gate(request: Request, mission_id: str, mission: dict | None) -> JSONResponse | None:
    """Existence-oracle-safe gate for mission handlers.

    Resolves the principal first (401 for a bad credential, before any lookup
    result is revealed), then returns the uniform 404 for an unknown mission
    AND for an existing mission the ordinary agent does not own (other owner,
    ownerless legacy, operator-created). Admin/operator gets the real result.
    Returns None when the caller may proceed.
    """
    agent_id = _acting_agent_id(request)
    if mission is None or not _agent_may_mutate(agent_id, mission):
        return _mission_not_found(mission_id)
    return None


def _authorize_mission_mutation(request: Request, mission: dict) -> None:
    """Deny any agent that is not the mission's recorded owner.

    SEMANTIC CHANGE (existence oracle): the denial is now 404 "Mission not
    found" (was 403 "Only the mission owner or an operator ...") so an ordinary
    agent cannot tell an existing foreign mission from an unknown id. Signature
    unchanged; still never allows what it previously denied. Mission handlers
    use _mission_gate for a byte-identical JSON body; this raising form yields
    the server's generic structured 404 for any other caller.
    """
    if not _agent_may_mutate(_acting_agent_id(request), mission):
        raise HTTPException(404, "Mission not found")


def _owner_fields(agent_id: str | None) -> dict:
    return {
        "owner_agent_id": agent_id or None,
        "created_by": "agent" if agent_id else "operator",
    }


def _resolve_refs(entry_mode: str, post_id: str, agreement_id: str,
                  acting_agent_id: str | None, *, inherit: dict | None = None) -> tuple[str, str | None, str | None]:
    """Validate the additive P4 refs (entry_mode / post_id / agreement_id) BEFORE any write.

    Fails closed: bad mode 422, unknown post/agreement 404, a post that the acting agent
    does not own (or an agreement it is not a party to) 403. Operators may reference any.
    """
    mode = entry_mode or (inherit or {}).get("entry_mode") or "open"
    if mode not in slot_binding.ENTRY_MODES:
        raise HTTPException(422, "entry_mode must be open, standard or constitutional")
    post_id = post_id or (inherit or {}).get("post_id") or ""
    if post_id:
        post = state.kassa.get_post(post_id)
        if not post:
            raise HTTPException(404, f"Post {post_id} not found")
        if acting_agent_id is not None and post.get("poster_agent_id") != acting_agent_id:
            raise HTTPException(403, "Only the post's own poster (or an operator) may bind it to a mission")
    if agreement_id:
        from app.workentry_store import WorkEntryError
        try:
            a = state.workentry.get(agreement_id)
        except WorkEntryError as e:
            raise HTTPException(e.status, e.message)
        parties = {p["id"] for p in a["principals"]}
        if acting_agent_id is not None and acting_agent_id not in parties:
            raise HTTPException(403, "Not a party to that agreement")
    return mode, post_id or None, agreement_id or None


@router.post("/api/missions")
async def create_mission(payload: CreateMissionPayload, request: Request) -> dict:
    """Create a new DEPLOY mission."""
    owner_agent_id = _acting_agent_id(request)
    m_mode, m_post, _ = _resolve_refs(payload.entry_mode, payload.post_id, "", owner_agent_id)
    missions = _load_missions()
    mid = f"mission-{_secrets_mod.token_hex(4)}"
    mission = {
        "id": mid,
        "mission_id": mid,  # alias — both keys resolve to the same value
        "label": payload.label,
        "objective": payload.objective,
        "posture": payload.posture,
        "formation": payload.formation,
        "target": payload.target,
        "duration": payload.duration,
        "limits": payload.limits,
        "systems": payload.systems,
        "agents": payload.agents,
        "status": "active",
        "created_at": datetime.now(UTC).isoformat(),
        "ended_at": None,
        "governance_at_launch": {
            "mode": state.runtime.governance.mode,
            "posture": state.runtime.governance.posture,
            "role": state.runtime.governance.role,
        },
        "results": [],
        "channel": payload.channel or f"mission-{(payload.label or 'unnamed').lower().replace(' ', '-')}",
        "entry_mode": m_mode, "post_id": m_post, "agreement_id": None,
        **_owner_fields(owner_agent_id),
    }
    missions.append(mission)
    _save_missions(missions)
    _audit_entry = state.audit.log("deploy", "mission_created", {
        "mission_id": mission["id"],
        "label": mission["label"],
        "posture": mission["posture"],
        "governance": mission["governance_at_launch"],
    })
    await state.emit("audit_event", _audit_entry.model_dump(mode="json"))

    seed_doi = None
    seed_doi = await create_seed_loud(
        state.audit, "mission",
        source_type="mission",
        source_id=mission["id"],
        creator_id=owner_agent_id or payload.agent_id or "operator",
        creator_type="BI",
        seed_type="planted",
        metadata={"label": mission["label"], "posture": mission["posture"]},
    )

    _tag_span(action="create", mission_id=mission["id"], label=mission["label"],
              posture=mission["posture"], formation=mission.get("formation", ""))
    return {**mission, "seed_doi": seed_doi}


@router.get("/api/missions")
async def list_missions() -> dict:
    return {"missions": _load_missions()}


@router.get("/api/missions/{mission_id}")
async def get_mission(mission_id: str) -> dict:
    mission = next((m for m in _load_missions() if m.get("id") == mission_id or m.get("mission_id") == mission_id), None)
    if not mission:
        return JSONResponse({"error": "Mission not found"}, status_code=404)
    # O-J-2: Mission Control is handed the mission_id and the Agreements bound to it (server truth).
    try:
        ags = state.workentry.list_by_object("mission_id", mission.get("id") or mission_id)
    except Exception:  # noqa: BLE001 - a read never fails on the projection
        ags = []
    return {"mission": {**mission, "agreements": slot_binding.summarize(ags)}}


def _complete_mission_agreements(request: Request | None, mission_id: str,
                                 delegate: str = "operator:mission-end") -> tuple[list[str], list[dict]]:
    """Mission end (explicit or auto-complete) -> every ACTIVE Agreement on it becomes ``completed``
    (K: terminal, kept as archive). One store transition (receipt + chained Seed) for both paths.
    A failure is returned loudly (and its evidence_gap is in the store), never swallowed.
    ``request`` is None on the auto path: no caller, so the operator-class delegate speaks for the owner."""
    from app.workentry_store import WorkEntryError
    done: list[str] = []
    errors: list[dict] = []
    try:
        acting = _acting_agent_id(request) if request is not None else None
    except HTTPException:
        acting = None
    for a in state.workentry.list_by_object("mission_id", mission_id):
        if a["state"] != "active":
            continue
        parties = {p["role"]: p["id"] for p in a["principals"]}
        if acting and acting in parties.values():
            actor, acting_for = acting, None
        else:
            actor, acting_for = delegate, parties["owner"]
        try:
            state.workentry.complete(a["agreement_id"], actor=actor, acting_for=acting_for)
            done.append(a["agreement_id"])
        except WorkEntryError as e:
            errors.append({"agreement_id": a["agreement_id"], "error": e.message, "code": e.code})
        except Exception as e:  # noqa: BLE001 - loud, never aborts the mission end
            errors.append({"agreement_id": a["agreement_id"], "error": str(e), "code": "unexpected"})
    return done, errors


async def _settle_escrow(mission_id: str, escrow: dict, per_slot: float, payload, payouts: list,
                         errors: list) -> dict:
    """Mission end with a live escrow: pay each filled slot from it, refund the rest.

    ``per_slot`` is the operator's claim when given; otherwise the held funds are
    split evenly across filled slots (the poster ending its own mission accepts
    the work and names no amount). A frozen (disputed) escrow pays and refunds nothing.
    """
    eid = escrow["escrow_id"]
    if escrow["state"] == "disputed":
        errors.append({"escrow_id": eid, "error": "escrow is disputed: funds frozen", "code": "disputed"})
        return {"escrow_id": eid, "state": "disputed", "refunded": 0.0}
    filled = [s for s in _load_slots() if s["mission_id"] == mission_id and s["status"] == "filled" and s.get("agent_id")]
    if filled:
        for i, slot in enumerate(filled):
            # even split of what is still held (floored to 4dp so it never exceeds it)
            share = per_slot if per_slot > 0 else math.floor(
                state.escrow.get(eid)["remaining"] / (len(filled) - i) * 1e4) / 1e4
            if share <= 0:
                break
            try:
                result = await release_to(eid, slot["agent_id"], share, source="mission_end",
                                          originator_id=payload.originator_id if payload else "")
                payouts.append(result)
            except EscrowError as exc:
                errors.append({"agent_id": slot["agent_id"], "escrow_id": eid, "error": exc.message, "code": exc.code})
            except Exception as exc:  # noqa: BLE001 - loud, never aborts the mission end
                errors.append({"agent_id": slot["agent_id"], "escrow_id": eid, "error": str(exc)[:200]})
                state.audit.log("economy", "payout_failed", {
                    "mission_id": mission_id, "agent_id": slot["agent_id"], "escrow_id": eid, "error": str(exc)[:200]})
    refunded = await _refund_escrow_remainder(eid)
    return {"escrow_id": eid, "state": state.escrow.get(eid)["state"], "refunded": refunded}


async def _refund_escrow_remainder(escrow_id: str) -> float:
    """Return what is still held to the poster; 0.0 if nothing/frozen. Failures are audited."""
    try:
        return (await refund_to_poster(escrow_id, reason="mission_ended"))["refunded"]
    except EscrowError:
        return 0.0
    except Exception as exc:  # noqa: BLE001
        state.audit.log("economy", "escrow_refund_failed", {"escrow_id": escrow_id, "error": str(exc)[:200]})
        return 0.0


@router.post("/api/missions/{mission_id}/end")
async def end_mission(mission_id: str, request: Request, payload: EndMissionPayload | None = None) -> dict:
    missions = _load_missions()
    mission = next((m for m in missions if m["id"] == mission_id), None)
    denied = _mission_gate(request, mission_id, mission)
    if denied is not None:
        return denied
    # ── Economy: process payouts for all filled slots in this mission ──
    payout_amount = payload.payout_per_slot if payload else 0
    # P5 s2: a payout credits treasury balances that cash out to Stripe, so the
    # amount is an operator claim (same rule as task payouts). An owner agent
    # may still end its mission; it may not name a payout.
    if payout_amount and _acting_agent_id(request) is not None:
        return JSONResponse({"error": "Only an operator may set a mission payout"}, status_code=403)
    if payout_amount < 0 or payout_amount > MAX_SLOT_PAYOUT:
        return JSONResponse({"error": f"payout_per_slot must be between 0 and {MAX_SLOT_PAYOUT:,.0f}"}, status_code=400)
    mission["status"] = "completed"
    mission["ended_at"] = datetime.now(UTC).isoformat()
    payouts = []
    payout_errors = []
    escrow_info = None
    escrow = state.escrow.active_for_mission(mission_id)
    if escrow is not None:
        # P5: funds are held for this mission, so payouts come from the escrow
        # (bounded by it) and the remainder returns to the poster.
        escrow_info = await _settle_escrow(mission_id, escrow, payout_amount, payload, payouts, payout_errors)
    elif payout_amount > 0:
        all_slots = _load_slots()
        filled = [s for s in all_slots if s["mission_id"] == mission_id and s["status"] == "filled" and s.get("agent_id")]
        for slot in filled:
            try:
                result = state.economy.process_mission_payout(
                    agent_id=slot["agent_id"],
                    agent_metrics={},
                    gross_amount=payout_amount,
                    mission_id=mission_id,
                    originator_id=payload.originator_id if payload else "",
                )
                result["seed"] = await _payout_seed(result, source="mission_end")
                payouts.append(result)
            except Exception as exc:
                payout_errors.append({"agent_id": slot["agent_id"], "error": str(exc)[:200]})
                state.audit.log("economy", "payout_failed", {
                    "mission_id": mission_id, "agent_id": slot["agent_id"], "error": str(exc)[:200]})

    mission["payouts"] = payouts
    _save_missions(missions)
    agreements_completed, agreement_errors = _complete_mission_agreements(request, mission_id)
    _audit_entry = state.audit.log("deploy", "mission_ended", {
        "mission_id": mission_id,
        "slots_paid": len(payouts),
        "payout_per_slot": payout_amount,
    })
    await state.emit("audit_event", _audit_entry.model_dump(mode="json"))
    await state.emit("mission_ended", {"mission_id": mission_id, "payouts": len(payouts)})
    seed_doi = None
    seed_doi = await create_seed_loud(
        state.audit, "mission_ended",
        source_type="mission_ended",
        source_id=mission_id,
        creator_id="operator",
        creator_type="BI",
        seed_type="planted",
        metadata={"mission_id": mission_id, "slots_paid": len(payouts), "payout_per_slot": payout_amount},
    )
    _tag_span(action="end", mission_id=mission_id,
              slots_paid=len(payouts), payout_per_slot=payout_amount)
    return {**mission, "seed_doi": seed_doi, "agreements_completed": agreements_completed,
            "agreement_errors": agreement_errors, "payout_errors": payout_errors, "escrow": escrow_info,
            "provenance_errors": [p["agent_id"] for p in payouts if not (p.get("seed") or {}).get("doi")]}


@router.post("/api/missions/{mission_id}/update")
async def update_mission(mission_id: str, payload: UpdateMissionPayload, request: Request) -> dict:
    missions = _load_missions()
    mission = next((m for m in missions if m["id"] == mission_id), None)
    denied = _mission_gate(request, mission_id, mission)
    if denied is not None:
        return denied
    updates = {}
    for k in ["posture", "formation", "status", "target", "limits"]:
        val = getattr(payload, k, None)
        if val is not None:
            mission[k] = val
            updates[k] = val
    _save_missions(missions)
    await create_seed_loud(state.audit, "mission_updated", source_type="mission_updated", source_id=mission_id, creator_id="operator", creator_type="BI", seed_type="touched", metadata=updates)
    return mission


# ══════════════════════════════════════════════════════════════════════════════
# CAMPAIGNS
# ══════════════════════════════════════════════════════════════════════════════


# Campaign principal binding — mirrors the mission binding above. Campaign
# authority is DISTINCT from mission authority (1B D16-P7: COMMAND != DEPLOY !=
# CAMPAIGN; 1G §5.C deploy row). Owner is derived server-side from the live
# Bearer key; ownerless legacy campaigns fail closed for agents. Order of
# checks: 401 (principal) -> 404 (campaign) -> 403 (owner), all before writes.

def _find_campaign_for_mutation(
    request: Request, campaigns: list[dict], campaign_id: str
) -> tuple[dict | None, JSONResponse | None]:
    agent_id = _acting_agent_id(request)  # 401
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if not campaign:
        return None, JSONResponse({"error": "Campaign not found"}, status_code=404)
    if agent_id is not None:
        owner = campaign.get("owner_agent_id")
        if not owner or owner != agent_id:
            raise HTTPException(403, "Only the campaign owner or an operator may modify this campaign")
    return campaign, None


@router.post("/api/campaigns")
async def create_campaign(payload: CreateCampaignPayload, request: Request) -> dict:
    """Create a CAMPAIGN — long-term strategy container for missions."""
    owner_agent_id = _acting_agent_id(request)
    campaigns = _load_campaigns()
    campaign = {
        "id": f"campaign-{_secrets_mod.token_hex(4)}",
        "name": payload.name,
        "objective": payload.objective,
        "ecosystems": payload.ecosystems,
        "revenue_target": payload.revenue_target,
        "status": "active",
        "outcome": "",
        "created_at": datetime.now(UTC).isoformat(),
        "closed_at": None,
        "missions": [],
        **_owner_fields(owner_agent_id),
    }
    campaigns.append(campaign)
    _save_campaigns(campaigns)
    _audit_entry = state.audit.log("campaign", "created", {"campaign_id": campaign["id"], "name": campaign["name"]})
    await state.emit("audit_event", _audit_entry.model_dump(mode="json"))
    await create_seed_loud(state.audit, "campaign", source_type="campaign", source_id=campaign["id"], creator_id=owner_agent_id or "operator", creator_type="BI", seed_type="planted", metadata={"name": campaign["name"]})
    return campaign


@router.get("/api/campaigns")
async def list_campaigns() -> dict:
    return {"campaigns": _load_campaigns()}


@router.get("/api/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str) -> dict:
    campaign = next((c for c in _load_campaigns() if c["id"] == campaign_id), None)
    if not campaign:
        return JSONResponse({"error": "Campaign not found"}, status_code=404)
    return {"campaign": campaign}


@router.post("/api/campaigns/{campaign_id}/add_mission")
async def add_mission_to_campaign(campaign_id: str, payload: AddMissionToCampaignPayload, request: Request) -> dict:
    campaigns = _load_campaigns()
    campaign, err = _find_campaign_for_mutation(request, campaigns, campaign_id)
    if err:
        return err
    mission_id = (payload.mission_id or "").strip()
    if not mission_id:
        return JSONResponse({"error": "mission_id required"}, status_code=400)
    # The mission must exist and (for an agent) be owned by the same agent. The
    # uniform 404 covers unknown AND foreign/ownerless ids for agents, and
    # unknown ids for admin too (admin may attach any EXISTING mission).
    mission = next((m for m in _load_missions()
                    if mission_id in (m.get("id"), m.get("mission_id"))), None)
    denied = _mission_gate(request, mission_id, mission)
    if denied is not None:
        return denied
    # Idempotent: re-attaching an already-attached mission is a 200 no-op
    # (no write, no duplicate entry).
    if mission_id not in campaign["missions"]:
        campaign["missions"].append(mission_id)
        _save_campaigns(campaigns)
    return campaign


@router.post("/api/campaigns/{campaign_id}/close")
async def close_campaign(campaign_id: str, payload: CloseCampaignPayload, request: Request) -> dict:
    campaigns = _load_campaigns()
    campaign, err = _find_campaign_for_mutation(request, campaigns, campaign_id)
    if err:
        return err
    campaign["status"] = "closed"
    campaign["closed_at"] = datetime.now(UTC).isoformat()
    campaign["outcome"] = payload.outcome
    _save_campaigns(campaigns)
    _audit_entry = state.audit.log("campaign", "closed", {"campaign_id": campaign_id, "name": campaign.get("name")})
    await state.emit("audit_event", _audit_entry.model_dump(mode="json"))
    await create_seed_loud(state.audit, "campaign_closed", source_type="campaign_closed", source_id=campaign_id, creator_id="operator", creator_type="BI", seed_type="touched", metadata={"name": campaign.get("name"), "outcome": campaign["outcome"]})
    return campaign


@router.post("/api/campaigns/{campaign_id}/activate")
async def activate_campaign(campaign_id: str, request: Request) -> dict:
    """Set a campaign to active status."""
    campaigns = _load_campaigns()
    campaign, err = _find_campaign_for_mutation(request, campaigns, campaign_id)
    if err:
        return err
    if campaign.get("status") == "closed":
        return JSONResponse({"error": "Cannot reactivate a closed campaign"}, status_code=400)
    campaign["status"] = "active"
    _save_campaigns(campaigns)
    _audit_entry = state.audit.log("campaign", "activated", {"campaign_id": campaign_id, "name": campaign.get("name")})
    await state.emit("audit_event", _audit_entry.model_dump(mode="json"))
    return campaign


# ══════════════════════════════════════════════════════════════════════════════
# TASKS — individual agent missions
# ══════════════════════════════════════════════════════════════════════════════


# ── Task principal binding ───────────────────────────────────────────────────
# A task records the authentic agent that created it (`owner_agent_id`, derived
# server-side from the live Bearer key, never from the body). Attaching a task
# to a mission requires owning that mission (1G §5 contract basis), so a task's
# owner is also its mission's owner. assign / close / cancel are owner-only;
# start / deliver additionally admit the recorded `assigned_agent`. Ownerless
# (legacy / operator-created) tasks fail closed for agents; admin keeps
# operator authority. The edge middleware currently keeps /api/tasks
# admin-only; this is defense in depth should that prefix ever open to agents.

def _authorize_task_mutation(request: Request, task: dict, *, allow_assignee: bool = False) -> None:
    """Deny (403) any agent that is not the task owner (or, if allowed, assignee)."""
    agent_id = _acting_agent_id(request)
    if agent_id is None:
        return
    owner = task.get("owner_agent_id")
    if not owner:
        raise HTTPException(403, "Only the task owner or an operator may modify this task")
    if agent_id == owner:
        return
    if allow_assignee and task.get("assigned_agent") == agent_id:
        return
    raise HTTPException(403, "Only the task owner or an operator may modify this task")


@router.post("/api/tasks")
async def create_task(payload: CreateTaskPayload, request: Request) -> dict:
    """Create an individual agent mission (task). The atomic unit of work."""
    owner_agent_id = _acting_agent_id(request)
    if owner_agent_id is not None:
        # Financial/EXP claims are operator-only: close_task credits payout to
        # the assignee's treasury and awards exp_reward, so an agent-chosen
        # value would let an agent mint either. Agents get the default EXP and
        # no payout.
        if payload.payout:
            raise HTTPException(403, "Only an operator may set a task payout")
        if payload.exp_reward is not None and payload.exp_reward != TASK_EXP_BASE.get(payload.type, 100):
            raise HTTPException(403, "Only an operator may set a custom task exp_reward")
        campaign = None
        if payload.campaign_id:
            campaign = next((c for c in _load_campaigns() if c.get("id") == payload.campaign_id), None)
            owner = campaign.get("owner_agent_id") if campaign else None
            if campaign is None or not owner or owner != owner_agent_id:
                # Uniform 404: unknown, foreign and ownerless look identical.
                return JSONResponse({"error": "Campaign not found", "campaign_id": payload.campaign_id}, status_code=404)
        if payload.mission_id:
            parent = next((m for m in _load_missions()
                           if payload.mission_id in (m.get("id"), m.get("mission_id"))), None)
            if parent is None:
                return JSONResponse({"error": "Mission not found", "mission_id": payload.mission_id}, status_code=404)
            denied = _mission_gate(request, payload.mission_id, parent)  # uniform 404 (no oracle)
            if denied is not None:
                return denied
            if campaign is not None and payload.mission_id not in campaign.get("missions", []):
                return JSONResponse({"error": "Mission is not part of this campaign",
                                     "mission_id": payload.mission_id,
                                     "campaign_id": payload.campaign_id}, status_code=409)
    task_type = payload.type
    track = payload.track
    if not payload.title:
        return JSONResponse({"error": "title required"}, status_code=400)
    exp_reward = payload.exp_reward if payload.exp_reward is not None else TASK_EXP_BASE.get(task_type, 100)
    task = {
        "id": f"task-{_secrets_mod.token_hex(4)}",
        "title": payload.title,
        "type": task_type,
        "track": track,
        "objective": payload.objective,
        "target": payload.target,
        "exp_reward": exp_reward,
        "payout": float(payload.payout),
        "assigned_agent": None,
        "operation_id": payload.operation_id,
        "campaign_id": payload.campaign_id,
        "mission_id": payload.mission_id,
        "status": "open",
        "deliverable": "",
        **_owner_fields(owner_agent_id),
        "created_at": datetime.now(UTC).isoformat(),
        "assigned_at": None,
        "delivered_at": None,
        "closed_at": None,
    }
    tasks = _load_tasks()
    tasks.append(task)
    _save_tasks(tasks)
    _audit_entry = state.audit.log("mission", "task_created", {"task_id": task["id"], "type": task_type, "track": track})
    await state.emit("audit_event", _audit_entry.model_dump(mode="json"))
    seed_doi = None
    seed_doi = await create_seed_loud(
        state.audit, "task",
        source_type="task",
        source_id=task["id"],
        creator_id=owner_agent_id or "operator",
        creator_type="BI",
        seed_type="planted",
        metadata={"title": task["title"], "type": task_type, "track": track},
    )
    return {**task, "seed_doi": seed_doi}


@router.get("/api/tasks")
async def list_tasks(
    status: str | None = None,
    agent_id: str | None = None,
    track: str | None = None,
    campaign_id: str | None = None,
) -> dict:
    tasks = _load_tasks()
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    if agent_id:
        tasks = [t for t in tasks if t.get("assigned_agent") == agent_id]
    if track:
        tasks = [t for t in tasks if t.get("track") == track]
    if campaign_id:
        tasks = [t for t in tasks if t.get("campaign_id") == campaign_id]
    return {"tasks": tasks, "total": len(tasks)}


@router.get("/api/tasks/{task_id}")
async def get_task(task_id: str) -> dict:
    task = next((t for t in _load_tasks() if t["id"] == task_id), None)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    return {"task": task}


@router.post("/api/tasks/{task_id}/assign")
async def assign_task(task_id: str, payload: AssignTaskPayload, request: Request) -> dict:
    """Assign an agent to an open task."""
    _acting_agent_id(request)
    agent_id = payload.agent_id
    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    _authorize_task_mutation(request, task)
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    if task["status"] not in ("open",):
        return JSONResponse({"error": f"Task is {task['status']} — cannot assign"}, status_code=409)
    task["assigned_agent"] = agent_id
    task["status"] = "assigned"
    task["assigned_at"] = datetime.now(UTC).isoformat()
    _save_tasks(tasks)
    state.audit.log("mission", "task_assigned", {"task_id": task_id, "agent_id": agent_id})
    await state.emit("task_assigned", {"task_id": task_id, "agent_id": agent_id})
    try:
        from app.inbox import notify_agent
        notify_agent(agent_id, "task_assigned",
                     f"Task assigned: {task.get('title', task_id)}",
                     f"You were assigned task {task_id}: {task.get('title', '')}. "
                     f"Objective: {task.get('objective', '')}. Deliver via POST /api/tasks/{task_id}/deliver.",
                     ref_type="task", ref_id=task_id)
    except Exception:
        pass
    await create_seed_loud(state.audit, "task_assigned", source_type="task_assigned", source_id=task_id, creator_id=agent_id, creator_type="AAI", seed_type="touched", metadata={"mission_id": task.get("mission_id", "")})
    return task


@router.post("/api/tasks/{task_id}/start")
async def start_task(task_id: str, request: Request) -> dict:
    """Mark task in-progress."""
    _acting_agent_id(request)
    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    _authorize_task_mutation(request, task, allow_assignee=True)
    task["status"] = "in_progress"
    _save_tasks(tasks)
    await create_seed_loud(state.audit, "task_started", source_type="task_started", source_id=task_id, creator_id=task.get("assigned_agent", "unknown"), creator_type="AAI", seed_type="touched", metadata={"mission_id": task.get("mission_id", "")})
    return task


@router.post("/api/tasks/{task_id}/deliver")
async def deliver_task(task_id: str, payload: DeliverTaskPayload, request: Request) -> dict:
    """Agent submits output/deliverable. Moves task to delivered — awaiting close."""
    _acting_agent_id(request)
    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    _authorize_task_mutation(request, task, allow_assignee=True)
    task["deliverable"] = payload.deliverable
    task["status"] = "delivered"
    task["delivered_at"] = datetime.now(UTC).isoformat()
    _save_tasks(tasks)
    state.audit.log("mission", "task_delivered", {"task_id": task_id, "agent": task.get("assigned_agent")})
    await state.emit("task_delivered", {"task_id": task_id, "deliverable": task["deliverable"]})
    seed_doi = None
    seed_doi = await create_seed_loud(
        state.audit, "task_delivery",
        source_type="task_delivery",
        source_id=task_id,
        creator_id=task.get("assigned_agent", "unknown"),
        creator_type="AAI",
        seed_type="grown",
        metadata={"task_id": task_id, "agent": task.get("assigned_agent")},
    )
    return {**task, "seed_doi": seed_doi}


@router.post("/api/tasks/{task_id}/close")
async def close_task(task_id: str, payload: CloseTaskPayload, request: Request) -> dict:
    """Close a task — awards EXP to agent, triggers economic payout if payout > 0."""
    acting_agent_id = _acting_agent_id(request)

    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    _authorize_task_mutation(request, task)
    if task["status"] == "closed":
        return JSONResponse({"error": "Task already closed"}, status_code=409)
    task["status"] = "closed"
    task["closed_at"] = datetime.now(UTC).isoformat()
    _save_tasks(tasks)
    exp_result = {}
    payout_result = {}
    agent_id = task.get("assigned_agent")
    if agent_id:
        exp_result = _award_exp(agent_id, task["exp_reward"], task.get("track", "tool"))
        task_escrow = state.escrow.active_for_mission(task["mission_id"]) if task.get("mission_id") else None
        if task["payout"] > 0 and task_escrow is not None:
            # P5: the mission has funds held, so this payout comes out of them.
            try:
                payout_result = await release_to(task_escrow["escrow_id"], agent_id, task["payout"],
                                                 source="task_close")
            except EscrowError as exc:
                payout_result = {"error": exc.message, "code": exc.code, "escrow_id": task_escrow["escrow_id"]}
                state.audit.log("economy", "payout_failed", {"task_id": task_id, "agent_id": agent_id,
                                                             "escrow_id": task_escrow["escrow_id"], "error": exc.message})
        elif task["payout"] > 0:
            payout_result = state.economy.process_mission_payout(
                agent_id=agent_id,
                agent_metrics={},
                gross_amount=task["payout"],
                mission_id=task_id,
            )
            payout_result["seed"] = await _payout_seed(payout_result, source="task_close")
    state.audit.log("mission", "task_closed", {
        "task_id": task_id,
        "agent_id": agent_id,
        "exp_awarded": task["exp_reward"],
        "track": task.get("track"),
        "payout": task["payout"],
    })
    await state.emit("task_closed", {"task_id": task_id, "agent_id": agent_id, "exp": task["exp_reward"]})
    if agent_id:
        try:
            from app.inbox import notify_agent
            net = (payout_result.get("fee_breakdown") or {}).get("net_to_agent")
            notify_agent(agent_id, "task_closed",
                         f"Task closed: {task.get('title', task_id)}",
                         f"Task {task_id} closed. EXP awarded: {task['exp_reward']} ({task.get('track', 'tool')} track)."
                         + (f" Payout: ${net:.2f} credited to treasury balance." if isinstance(net, (int, float)) else ""),
                         ref_type="task", ref_id=task_id)
        except Exception:
            pass
    seed_doi = None
    seed_doi = await create_seed_loud(
        state.audit, "task_close",
        source_type="task_close",
        source_id=task_id,
        creator_id=acting_agent_id or payload.requestor or agent_id or "operator",
        creator_type="BI",
        seed_type="grown",
        metadata={"task_id": task_id, "agent_id": agent_id, "exp_awarded": task["exp_reward"], "payout": task["payout"]},
    )
    # ── Auto-complete mission if all its tasks are closed ────────────
    mission_complete_result = None
    mission_id = task.get("mission_id")
    if mission_id:
        all_tasks = _load_tasks()
        mission_tasks = [t for t in all_tasks if t.get("mission_id") == mission_id]
        if mission_tasks and all(t["status"] in ("closed", "cancelled") for t in mission_tasks):
            active_tasks = [t for t in mission_tasks if t["status"] == "closed"]
            if active_tasks:
                # Sum up per-slot payouts from task payouts already processed
                total_payout = sum(t.get("payout", 0) for t in active_tasks)
                missions = _load_missions()
                mission = next((m for m in missions if m["id"] == mission_id), None)
                if mission and mission.get("status") == "active":
                    mission["status"] = "completed"
                    mission["ended_at"] = datetime.now(UTC).isoformat()
                    mission["auto_completed"] = True
                    _save_missions(missions)
                    # P4 slice 11: bound active Agreements complete through the same helper as /end
                    ag_done, ag_errors = _complete_mission_agreements(
                        None, mission_id, delegate="operator:mission-auto-complete")
                    state.audit.log("deploy", "mission_auto_completed", {
                        "mission_id": mission_id,
                        "tasks_closed": len(active_tasks),
                        "total_payout": total_payout,
                        "agreements_completed": ag_done,
                        "agreement_errors": ag_errors,
                    })
                    if state.escrow.active_for_mission(mission_id):   # P5: leftover held funds go back to the poster
                        await _refund_escrow_remainder(state.escrow.active_for_mission(mission_id)["escrow_id"])
                    await state.emit("mission_ended", {"mission_id": mission_id, "auto": True})
                    mission_complete_result = {"mission_id": mission_id, "auto_completed": True,
                                               "agreements_completed": ag_done,
                                               "agreement_errors": ag_errors}

    return {"task": task, "exp_awarded": exp_result, "payout": payout_result, "seed_doi": seed_doi, "mission_completed": mission_complete_result}


@router.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, request: Request) -> dict:
    _acting_agent_id(request)
    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    _authorize_task_mutation(request, task)
    task["status"] = "cancelled"
    _save_tasks(tasks)
    state.audit.log("mission", "task_cancelled", {"task_id": task_id})
    await create_seed_loud(state.audit, "task_cancelled", source_type="task_cancelled", source_id=task_id, creator_id=task.get("assigned_agent", "operator"), creator_type="AAI", seed_type="touched", metadata={"mission_id": task.get("mission_id", "")})
    return task


# ══════════════════════════════════════════════════════════════════════════════
# SLOTS (DEPLOY marketplace mechanics)
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/api/slots/create")
async def create_slots_from_formation(payload: CreateSlotsPayload, request: Request) -> dict:
    """Create slots from a formation. Each slot has position, role, governance, revenue split."""
    # P4: an id minted here must resolve to a mission record (see bounty fix
    # b06ae00). A caller-supplied id must already resolve to one (exact match
    # on id/mission_id, as in get_mission) or we fail closed before any write.
    minted = not payload.mission_id
    mission_id = payload.mission_id
    # Resolve the acting principal first (401 for a bad credential), then
    # D-C: a supplied id must resolve to an existing mission or fail closed
    # before any write, then D-B: only that mission's owner or an operator.
    owner_agent_id = _acting_agent_id(request)
    existing = None
    if not minted:
        existing = next((m for m in _load_missions()
                         if mission_id in (m.get("id"), m.get("mission_id"))), None)
        denied = _mission_gate(request, mission_id, existing)
        if denied is not None:
            return denied
    # P4 slice 4: additive refs validated before any write (fail closed).
    entry_mode, ref_post_id, ref_agreement_id = _resolve_refs(
        payload.entry_mode, payload.post_id, payload.agreement_id, owner_agent_id, inherit=existing)
    if minted:
        taken = {m.get(k) for m in _load_missions() for k in ("id", "mission_id")}
        taken |= {sl.get("mission_id") for sl in _load_slots()}
        mission_id = f"mission-{_secrets_mod.token_hex(4)}"
        while mission_id in taken:
            mission_id = f"mission-{_secrets_mod.token_hex(4)}"
    formation_id = payload.formation_id
    posture = payload.posture
    label = payload.label
    positions = payload.positions
    roles = payload.roles
    revenue_splits = payload.revenue_splits
    governance_mode = payload.governance_mode or state.runtime.governance.mode

    slots = _load_slots()
    new_slots = []

    for i, pos in enumerate(positions):
        role = roles[i] if i < len(roles) else ("primary" if i == 0 else "secondary" if i < len(positions) - 1 else "observer")
        split = revenue_splits[i] if i < len(revenue_splits) else round(100 / max(len(positions), 1))

        slot = {
            "id": f"slot-{_secrets_mod.token_hex(4)}",
            "mission_id": mission_id,
            "mission_label": label,
            "formation_id": formation_id,
            "position": {"row": pos.get("row", 0), "col": pos.get("col", 0)},
            "grid_ref": f"{chr(65 + pos.get('col', 0))}{pos.get('row', 0) + 1}",
            "role": role,
            "governance": {
                "mode": governance_mode,
                "posture": posture,
            },
            "revenue_split_pct": split,
            "status": "open",
            "agent_id": None,
            "agent_name": None,
            "filled_at": None,
            "created_at": datetime.now(UTC).isoformat(),
            "metrics": {"messages": 0, "governance_checks": 0, "violations": 0, "revenue": 0},
            "entry_mode": entry_mode,
            "post_id": ref_post_id,
            "agreement_id": ref_agreement_id,
        }
        new_slots.append(slot)
        slots.append(slot)

    if minted:
        # Mission record first: a failure between the two writes leaves an
        # empty mission, never a slot pointing at a nonexistent mission.
        missions = _load_missions()
        missions.append({
            "id": mission_id,
            "mission_id": mission_id,
            "label": label,
            "objective": "",
            "posture": posture,
            "formation": formation_id,
            "target": "",
            "duration": "",
            "limits": {},
            "systems": [],
            "agents": [],
            "status": "active",
            "origin": "slots_create",
            "created_at": datetime.now(UTC).isoformat(),
            "ended_at": None,
            "governance_at_launch": {
                "mode": state.runtime.governance.mode,
                "posture": state.runtime.governance.posture,
                "role": state.runtime.governance.role,
            },
            "results": [],
            "channel": f"mission-{mission_id}",
            "slot_ids": [s["id"] for s in new_slots],
            "entry_mode": entry_mode,
            "post_id": ref_post_id,
            "agreement_id": ref_agreement_id,
            **_owner_fields(owner_agent_id),
        })
        _save_missions(missions)

    _save_slots(slots)
    _audit_entry = state.audit.log("deploy", "slots_created", {
        "mission_id": mission_id,
        "formation_id": formation_id,
        "slots_created": len(new_slots),
        "posture": posture,
    })
    await state.emit("audit_event", _audit_entry.model_dump(mode="json"))
    seed_doi = None
    seed_doi = await create_seed_loud(
        state.audit, "slot_created",
        source_type="slot_created",
        source_id=mission_id,
        creator_id="operator",
        creator_type="BI",
        seed_type="planted",
        metadata={"mission_id": mission_id, "formation_id": formation_id, "slots_created": len(new_slots)},
    )
    return {"created": len(new_slots), "mission_id": mission_id, "slots": new_slots, "seed_doi": seed_doi}


@router.get("/api/slots")
async def list_all_slots() -> dict:
    return {"slots": _load_slots()}


@router.get("/api/slots/open")
async def list_open_slots() -> dict:
    """Free agents browse this — all unfilled slots across all missions."""
    slots = _load_slots()
    open_slots = [s for s in slots if s["status"] == "open"]
    return {
        "open_slots": open_slots,
        "count": len(open_slots),
        "note": "Agents: call POST /api/slots/fill to claim a slot.",
    }


@router.post("/api/slots/fill")
async def fill_slot(payload: FillSlotPayload, request: Request) -> dict:
    """Agent claims an open slot. Gets auto-governed."""

    slot_id = payload.slot_id
    agent_id = payload.agent_id
    agent_name = payload.agent_name or agent_id

    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    require_agent_claim(
        request,
        agent_id,
        registry=state.runtime.registry,
        admin_key=state.admin_key,
        revoked_keys=state.runtime.revoked_keys,
    )
    registered = next((r for r in state.runtime.registry if r.get("agent_id") == agent_id), None)
    if not registered:
        return JSONResponse(
            {"error": f"Agent '{agent_id}' not registered. Call /api/provision/signup first."},
            status_code=403,
        )
    if registered.get("status") == "suspended":
        return JSONResponse({"error": "Agent suspended — contact admin"}, status_code=403)

    # P4 slice 4: an entry Agreement is required ONLY where the contracts bind a commitment
    # (slot fill in standard/constitutional mode). Open mode keeps working for callers by
    # minting the WorkEntryAgreement atomically (pending->accepted->active, modeled).
    from app.workentry_store import WorkEntryError, ProvenanceError, DuplicateEntryError
    cred = None
    try:
        from app.principal import resolve_principal
        cred = resolve_principal(request, state, allow_admin=True).ref
    except Exception:  # noqa: BLE001 - credential naming is best-effort; authority was enforced above
        cred = None
    agreement: dict | None = None
    fill_receipts: list[dict] = []
    async with state.slot_lock:
        slots = _load_slots()
        slot = next((s for s in slots if s["id"] == slot_id), None)
        if not slot:
            return JSONResponse({"error": "Slot not found"}, status_code=404)
        if slot["status"] != "open":
            return JSONResponse({"error": f"Slot already {slot['status']}"}, status_code=409)
        mission = slot_binding.find_mission(slot.get("mission_id"))
        mode = slot_binding.slot_mode(slot, mission)
        if mode != "open":
            return JSONResponse({
                "error": f"This slot is {mode} mode: enter via agreement (POST /api/work-entry)",
                "code": "enter_via_agreement", "entry_mode": mode,
                "opportunity_ref": f"slot:{slot_id}", "enter": "/api/work-entry",
            }, status_code=409)
        try:
            # Agreement FIRST (one commit) ...
            mine = [a for a in slot_binding.live_for_slot(agent_id, slot_id)]
            if mine and mine[0]["state"] == "accepted":
                out = state.workentry.activate(mine[0]["agreement_id"], actor=agent_id, credential=cred)
                agreement, fill_receipts = out["agreement"], [out["receipt"]]
            elif mine:
                return JSONResponse({"error": f"You already have an entry for this slot "
                                              f"({mine[0]['state']})", "code": "duplicate_entry",
                                     "agreement_id": mine[0]["agreement_id"]}, status_code=409)
            else:
                out = state.workentry.file_entry(
                    entrant=agent_id, owner=slot_binding.mission_owner(mission),
                    opportunity_ref=f"slot:{slot_id}", entry_mode="open",
                    objects={"post_id": slot.get("post_id") or (mission or {}).get("post_id"),
                             "mission_id": slot.get("mission_id"), "slot_id": slot_id},
                    terms={"pitch": None, "delivery_evidence_class": "solution", "via": "slots/fill"},
                    credential_refs={"entrant": cred}, auto_activate=True)
                agreement, fill_receipts = out["agreement"], out["receipts"]
        except DuplicateEntryError as e:
            return JSONResponse({"error": e.message, "code": e.code,
                                 "agreement_id": e.existing_agreement_id}, status_code=409)
        except WorkEntryError as e:
            body = {"error": e.message, "code": e.code}
            if isinstance(e, ProvenanceError):
                body["evidence_gap_id"] = e.gap_id
            return JSONResponse(body, status_code=e.status)
        # ... then the slot write; on failure: evidence_gap + compensating terminated.
        try:
            slot_binding.link_escrow(agreement["agreement_id"], slot.get("mission_id"))
            slot_binding.fill_slot_record(slot, agent_id=agent_id, agent_name=agent_name, agreement=agreement)
            _save_slots(slots)
        except Exception as exc:  # noqa: BLE001
            err = slot_binding._compensate(agreement["agreement_id"], "slot_binding",
                                           f"slot write failed: {type(exc).__name__}: {exc}",
                                           500, "binding_failed")
            return JSONResponse(err.body(), status_code=err.status)

    _audit_entry = state.audit.log("deploy", "slot_filled", {
        "slot_id": slot_id,
        "agent_id": agent_id,
        "mission_id": slot["mission_id"],
        "role": slot["role"],
        "governance": slot["governance"],
    })
    await state.emit("audit_event", _audit_entry.model_dump(mode="json"))
    # Typed lifecycle event — emitted only after the authoritative slot commit
    # above succeeded (missions.html listens for this event type).
    await state.emit("slot_filled", {
        "slot_id": slot_id,
        "agent_id": agent_id,
        "mission_id": slot["mission_id"],
        "role": slot["role"],
        "agreement_id": agreement["agreement_id"],
    })

    try:
        from app.inbox import notify_agent
        notify_agent(agent_id, "slot_filled",
                     f"Slot filled: {slot['role']} on {slot['mission_label'] or slot['mission_id']}",
                     f"You filled slot {slot_id} ({slot['grid_ref']}, {slot['role']}) on mission "
                     f"{slot['mission_id']}. Governance applied: {slot['governance']['mode']} / "
                     f"{slot['governance']['posture']}. Revenue split: {slot['revenue_split_pct']}%.",
                     ref_type="slot", ref_id=slot_id)
    except Exception:
        pass

    await create_seed_loud(
        state.audit, "slot_fill",
        source_type="slot_fill",
        source_id=slot_id,
        creator_id=agent_id,
        creator_type="AAI",
        seed_type="touched",
        metadata={"mission_id": slot["mission_id"], "role": slot["role"]},
    )

    _tag_span(action="fill_slot", slot_id=slot_id, agent_id=agent_id,
              mission_id=slot["mission_id"], role=slot["role"],
              governance_mode=slot["governance"].get("mode", ""),
              governance_posture=slot["governance"].get("posture", ""))
    return {
        "filled": True,
        "slot": slot,
        "governance_applied": slot["governance"],
        "role_assigned": slot["role"],
        "revenue_split": slot["revenue_split_pct"],
        "agreement_id": agreement["agreement_id"],
        "agreement_state": agreement["state"],
        "receipt": fill_receipts[-1] if fill_receipts else None,
        "receipts": fill_receipts,
        "mission_id": slot["mission_id"],
        "mission_control": slot_binding.mission_control_ref(slot["mission_id"]),
        "note": f"You are now governed under {slot['governance']['mode']} / {slot['governance']['posture']}. Role: {slot['role']}.",
    }


@router.post("/api/slots/leave")
async def leave_slot(payload: LeaveSlotPayload, request: Request) -> dict:
    """Agent leaves a slot — opens it back up. Caller must be the occupant."""
    slot_id = payload.slot_id
    requesting_agent = payload.agent_id
    if not requesting_agent:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    require_agent_claim(
        request,
        requesting_agent,
        registry=state.runtime.registry,
        admin_key=state.admin_key,
        revoked_keys=state.runtime.revoked_keys,
    )
    from app.workentry_store import WorkEntryError
    cred = None
    try:
        from app.principal import resolve_principal
        cred = resolve_principal(request, state, allow_admin=True).ref
    except Exception:  # noqa: BLE001
        cred = None
    left_agreement: dict | None = None
    async with state.slot_lock:
        slots = _load_slots()
        slot = next((s for s in slots if s["id"] == slot_id), None)
        if not slot:
            return JSONResponse({"error": "Slot not found"}, status_code=404)

        # P4 slice 4: an entry that is not (yet) the occupant -> withdrawn (pending) / terminated
        # (accepted). The slot itself is untouched.
        occupant = slot.get("agent_id")
        mine = [a for a in slot_binding.live_for_slot(requesting_agent, slot_id)
                if a["state"] != "active"] if occupant != requesting_agent else []
        if mine:
            ag = mine[0]
            try:
                if ag["state"] in ("pending", "dormant"):
                    out = state.workentry.withdraw(ag["agreement_id"], actor=requesting_agent,
                                                   reason="entrant left", credential=cred)
                else:
                    out = state.workentry.terminate(ag["agreement_id"], actor=requesting_agent,
                                                    reason="entrant left", credential=cred)
            except WorkEntryError as e:
                return JSONResponse({"error": e.message, "code": e.code}, status_code=e.status)
            if slot.get("status") == slot_binding.RESERVED and slot.get("agreement_id") == ag["agreement_id"]:
                slot["status"] = "closed"
                _save_slots(slots)
            return {"vacated": False, "slot_id": slot_id, "agreement_id": ag["agreement_id"],
                    "agreement_state": out["agreement"]["state"], "receipt": out["receipt"],
                    "mission_id": slot.get("mission_id")}

        # Ownership check — only the occupying agent can leave
        if requesting_agent and slot.get("agent_id") and requesting_agent != slot["agent_id"]:
            return JSONResponse({"error": "Only the occupying agent can leave this slot"}, status_code=403)

        old_agent = slot["agent_name"]
        leaving_agreement_id = slot.get("agreement_id")
        if leaving_agreement_id and occupant == requesting_agent:
            # Agreement FIRST: the active entry is terminated by the entrant ...
            try:
                left_agreement = state.workentry.terminate(
                    leaving_agreement_id, actor=requesting_agent, reason="occupant left the slot",
                    credential=cred)
            except WorkEntryError as e:
                if e.status != 409:      # 409 = already terminal; the slot may still be vacated
                    return JSONResponse({"error": e.message, "code": e.code}, status_code=e.status)
        minted = slot.get("formation_id") == "post_entry"
        slot["status"] = "closed" if minted else "open"
        slot["agent_id"] = None
        slot["agent_name"] = None
        slot["filled_at"] = None
        slot["agreement_id"] = None
        try:
            _save_slots(slots)
        except Exception as exc:  # noqa: BLE001
            if leaving_agreement_id:
                state.workentry.record_gap(leaving_agreement_id, attempted="leave", stage="slot_binding",
                                           reason=f"slot write failed: {type(exc).__name__}: {exc}",
                                           actor=requesting_agent, resolution="terminated_slot_unvacated")
            raise

    _audit_entry = state.audit.log("deploy", "slot_vacated", {"slot_id": slot_id, "previous_agent": old_agent})
    await state.emit("audit_event", _audit_entry.model_dump(mode="json"))
    # Typed lifecycle event — post-commit only (missions.html listens for
    # 'slot_left').
    await state.emit("slot_left", {
        "slot_id": slot_id,
        "agent_id": requesting_agent,
        "mission_id": slot.get("mission_id"),
        "role": slot.get("role"),
    })
    await create_seed_loud(
        state.audit, "slot_leave",
        source_type="slot_leave",
        source_id=slot_id,
        creator_id=old_agent or "unknown",
        creator_type="AAI",
        seed_type="touched",
        metadata={"slot_id": slot_id, "previous_agent": old_agent},
    )
    resp = {"vacated": True, "slot_id": slot_id}
    if left_agreement:
        resp.update({"agreement_id": left_agreement["agreement"]["agreement_id"],
                     "agreement_state": left_agreement["agreement"]["state"],
                     "receipt": left_agreement["receipt"], "mission_id": slot.get("mission_id")})
    return resp


@router.post("/api/slots/bounty")
async def post_bounty(payload: PostBountyPayload, request: Request) -> dict:
    """Agent posts a bounty — creates a mission with slots and itself as Primary."""

    agent_id = payload.agent_id
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    claimed = require_agent_claim(
        request,
        agent_id,
        registry=state.runtime.registry,
        admin_key=state.admin_key,
        revoked_keys=state.runtime.revoked_keys,
    )
    owner_agent_id = str(claimed.get("agent_id") or "") if claimed else None
    b_mode, b_post, b_agreement = _resolve_refs(
        payload.entry_mode, payload.post_id, payload.agreement_id, owner_agent_id)
    agent_name = payload.agent_name or agent_id
    label = payload.label or f"BOUNTY-{_secrets_mod.token_hex(3).upper()}"
    description = payload.description
    posture = payload.posture
    slots_needed = payload.slots_needed
    revenue_pool = payload.revenue_pool

    mission_id = f"bounty-{_secrets_mod.token_hex(4)}"
    slots = _load_slots()
    new_slots = []

    # Primary slot — filled by the posting agent
    primary_slot = {
        "id": f"slot-{_secrets_mod.token_hex(4)}",
        "mission_id": mission_id,
        "mission_label": label,
        "formation_id": "bounty",
        "position": {"row": 3, "col": 3},
        "grid_ref": "D4",
        "role": "primary",
        "governance": {"mode": state.runtime.governance.mode, "posture": posture},
        "revenue_split_pct": round(100 / (slots_needed + 1)),
        "status": "filled",
        "agent_id": agent_id,
        "agent_name": agent_name,
        "filled_at": datetime.now(UTC).isoformat(),
        "created_at": datetime.now(UTC).isoformat(),
        "metrics": {"messages": 0, "governance_checks": 0, "violations": 0, "revenue": 0},
        "bounty_description": description,
        "entry_mode": b_mode,
        "post_id": b_post,
        "agreement_id": None,      # the posting agent owns the mission; it enters nothing
    }
    new_slots.append(primary_slot)
    slots.append(primary_slot)

    # Open slots for others to fill
    open_positions = [{"row": 1, "col": 2}, {"row": 1, "col": 5}, {"row": 4, "col": 1}, {"row": 4, "col": 6}, {"row": 2, "col": 0}, {"row": 2, "col": 7}]
    for i in range(min(slots_needed, len(open_positions))):
        open_slot = {
            "id": f"slot-{_secrets_mod.token_hex(4)}",
            "mission_id": mission_id,
            "mission_label": label,
            "formation_id": "bounty",
            "position": open_positions[i],
            "grid_ref": f"{chr(65 + open_positions[i]['col'])}{open_positions[i]['row'] + 1}",
            "role": "secondary" if i < slots_needed - 1 else "observer",
            "governance": {"mode": state.runtime.governance.mode, "posture": posture},
            "revenue_split_pct": round(100 / (slots_needed + 1)),
            "status": "open",
            "agent_id": None,
            "agent_name": None,
            "filled_at": None,
            "created_at": datetime.now(UTC).isoformat(),
            "metrics": {"messages": 0, "governance_checks": 0, "violations": 0, "revenue": 0},
            "bounty_description": description,
            "entry_mode": b_mode,
            "post_id": b_post,
            "agreement_id": b_agreement,
        }
        new_slots.append(open_slot)
        slots.append(open_slot)

    _save_slots(slots)

    # H2: write the mission record too — bounty_minted mission_ids were
    # previously orphans (slots existed, no retrievable mission object).
    missions = _load_missions()
    missions.append({
        "id": mission_id,
        "mission_id": mission_id,
        "label": label,
        "objective": description,
        "posture": posture,
        "formation": "bounty",
        "target": "",
        "duration": "",
        "limits": {},
        "systems": [],
        "agents": [agent_id],
        "status": "active",
        "origin": "bounty",
        "created_at": datetime.now(UTC).isoformat(),
        "ended_at": None,
        "governance_at_launch": {
            "mode": state.runtime.governance.mode,
            "posture": state.runtime.governance.posture,
            "role": state.runtime.governance.role,
        },
        "results": [],
        "channel": f"bounty-{mission_id}",
        "slot_ids": [s["id"] for s in new_slots],
        "entry_mode": b_mode,
        "post_id": b_post,
        "agreement_id": b_agreement,
        **_owner_fields(owner_agent_id),
    })
    _save_missions(missions)

    _audit_entry = state.audit.log("deploy", "bounty_posted", {
        "mission_id": mission_id,
        "agent_id": agent_id,
        "label": label,
        "slots_open": slots_needed,
        "posture": posture,
    })
    await state.emit("audit_event", _audit_entry.model_dump(mode="json"))

    await create_seed_loud(
        state.audit, "slot_bounty",
        source_type="slot_bounty",
        source_id=primary_slot["id"],
        creator_id=agent_id,
        creator_type="AAI",
        seed_type="planted",
        metadata={"mission_id": mission_id, "label": label, "slots_needed": slots_needed},
    )

    _tag_span(action="post_bounty", mission_id=mission_id, agent_id=agent_id,
              label=label, open_slots=slots_needed, posture=posture)
    return {
        "bounty_posted": True,
        "mission_id": mission_id,
        "label": label,
        "primary_agent": agent_name,
        "open_slots": slots_needed,
        "total_slots": slots_needed + 1,
        "slots": new_slots,
    }
