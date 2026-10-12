"""Entry API -- /api/work-entry (P4 slice 3).

File an entry intent against an opportunity (post, slot or mission), and
resolve it per mode:

    open            click 1 (file) -> accepted; click 2 (activate) -> active
    standard        the owner (or an operator acting FOR the named owner) accepts/rejects
    constitutional  owner resolves AND a governance gate is required (lands in
                    slice 5; until then accept returns 409 "governance gate required")

No auto-expiry: 48 h with no answer -> the poster is asked (keep / decline /
retire); 14 days -> ``dormant`` (non-terminal, hidden from live lists, revives on
any activity). ``retired`` happens only by a party decision. Evaluation is lazy
(on read/list) plus an idempotent sweep (``sweep_entries`` / POST .../sweep).

Authority is resolved in-handler through the one principal resolver
(app.principal): either credential door -> the registry agent; the thread
magic link for email-only posters; the admin key as an operator who must name
the principal it acts FOR. Notifications (inbox + poster email) carry no
authority. Wiring is keyed to object ids; nothing here binds a slot (slice 4).
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.deps import state
from app.principal import Principal, resolve_principal
from app.sanitize import sanitize_text
from app.workentry_store import (
    DuplicateEntryError,
    ProvenanceError,
    WorkEntryError,
)

logger = logging.getLogger("civitae.workentry")
router = APIRouter(tags=["work-entry"])

ASK_POSTER_AFTER = timedelta(hours=48)
DORMANT_AFTER = timedelta(days=14)

_MODE_RANK = {"open": 0, "standard": 1, "constitutional": 2}
# 1C delivery evidence classes (evidence scope, not merit).
_EVIDENCE_CLASSES = {
    "1": "solution", "solution": "solution",
    "2": "solution_proof", "solution_proof": "solution_proof", "solution+proof": "solution_proof",
    "3": "solution_proof_work_access", "solution_proof_work_access": "solution_proof_work_access",
    "solution+proof+work_access": "solution_proof_work_access",
}
GATE_REQUIRED = {
    "error": "governance gate required",
    "code": "governance_gate_required",
    "detail": "Constitutional entries need the governance gate (typed motion bound to the "
              "agreement) before they can be accepted. The gate lands in P4 slice 5.",
}


# ── payloads ─────────────────────────────────────────────────────────────

class FileEntryPayload(BaseModel):
    opportunity_ref: str
    pitch: str = Field(default="", max_length=4000)
    terms: dict[str, Any] = Field(default_factory=dict)
    delivery_evidence_class: str | int | None = None
    acceptance_payload: dict[str, Any] | str | None = None
    stake_ref: str | None = None          # a reference only; stake never auto-converts to entry
    entry_mode: str | None = None         # may only escalate the opportunity's own mode
    idempotency_key: str | None = None
    supersedes: str | None = None


class ActionPayload(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)
    acting_for: str | None = None         # operator / magic link: the named principal
    idempotency_key: str | None = None


# ── helpers ──────────────────────────────────────────────────────────────

def _err(e: WorkEntryError) -> JSONResponse:
    body: dict[str, Any] = {"error": e.message, "code": e.code}
    if isinstance(e, DuplicateEntryError):
        body["agreement_id"] = e.existing_agreement_id
    if isinstance(e, ProvenanceError):
        body["evidence_gap_id"] = e.gap_id
    return JSONResponse(body, status_code=e.status)


def _principal(request: Request) -> Principal:
    return resolve_principal(request, state, allow_magic=True, allow_admin=True)


def _store():
    return state.workentry


def _kind_of(ref: str) -> tuple[str, str]:
    if ":" in ref:
        kind, _, ident = ref.partition(":")
        if kind in ("post", "slot", "mission") and ident:
            return kind, ident
    if ref.startswith("slot-"):
        return "slot", ref
    if ref.startswith(("mission-", "bounty-")):
        return "mission", ref
    return "post", ref


def _load_mission(mission_id: str) -> dict | None:
    from app.routes.missions import _load_missions
    return next((m for m in _load_missions()
                 if mission_id in (m.get("id"), m.get("mission_id"))), None)


def _mission_owner(mission: dict | None) -> str:
    return (mission or {}).get("owner_agent_id") or "platform"


def _resolve_opportunity(ref: str) -> dict:
    """opportunity ref -> {ref, kind, owner, base_mode, objects, title, post}."""
    kind, ident = _kind_of(ref)
    if kind == "post":
        post = state.kassa.get_post(ident)
        if not post or post.get("status", "open") not in ("open", "live", "active"):
            raise HTTPException(404, "Opportunity not found")
        return {"ref": f"post:{ident}", "kind": "post", "post": post,
                "owner": post.get("poster_agent_id") or f"poster:{ident}",
                "base_mode": post.get("entry_mode") or "standard",
                "objects": {"post_id": ident, "mission_id": None, "slot_id": None},
                "title": post.get("title", "")}
    if kind == "slot":
        from app.routes.missions import _load_slots
        slot = next((s for s in _load_slots() if s.get("id") == ident), None)
        if not slot:
            raise HTTPException(404, "Opportunity not found")
        if slot.get("status") != "open":
            raise HTTPException(409, f"Slot already {slot.get('status')}")
        mission = _load_mission(slot.get("mission_id", ""))
        post_id = slot.get("post_id") or (mission or {}).get("post_id")
        post = state.kassa.get_post(post_id) if post_id else None
        return {"ref": f"slot:{ident}", "kind": "slot", "post": post,
                "owner": _mission_owner(mission),
                "base_mode": slot.get("entry_mode") or (mission or {}).get("entry_mode") or "open",
                "objects": {"post_id": post_id, "mission_id": slot.get("mission_id"), "slot_id": ident},
                "title": slot.get("mission_label") or slot.get("role", "")}
    mission = _load_mission(ident)
    if not mission:
        raise HTTPException(404, "Opportunity not found")
    post_id = mission.get("post_id")
    return {"ref": f"mission:{ident}", "kind": "mission",
            "post": state.kassa.get_post(post_id) if post_id else None,
            "owner": _mission_owner(mission),
            "base_mode": mission.get("entry_mode") or "open",
            "objects": {"post_id": post_id, "mission_id": mission.get("id") or ident, "slot_id": None},
            "title": mission.get("label", "")}


def _is_party_view(p: Principal, a: dict) -> bool:
    if p.kind == "operator":
        return True
    if p.kind == "agent":
        return p.agent_id in (_entrant(a), _owner(a))
    if p.kind == "poster_link":
        return bool(a["objects"].get("post_id")) and a["objects"]["post_id"] == p.post_id
    return False


def _entrant(a: dict) -> str:
    return next(x["id"] for x in a["principals"] if x["role"] == "entrant")


def _owner(a: dict) -> str:
    return next(x["id"] for x in a["principals"] if x["role"] == "owner")


def _actor(p: Principal, a: dict, body: ActionPayload | None) -> tuple[str, str | None, str]:
    """(actor, acting_for, credential_ref) for a store transition."""
    if p.kind == "agent":
        return p.agent_id, None, p.ref
    if p.kind == "operator":
        return "operator:admin", (body.acting_for if body else None), p.ref
    # magic link: speaks FOR the post's owner, only on its own post's entries
    p.require_post(a["objects"].get("post_id") or "")
    if not a["objects"].get("post_id"):
        raise HTTPException(403, "This link is not valid for that entry")
    return f"poster-link:{p.thread_id}", _owner(a), p.ref


def _get_or_404(aid: str) -> dict:
    try:
        return _store().get(aid)
    except WorkEntryError as e:
        raise HTTPException(e.status, e.message)


# ── notifications (non-authoritative) ────────────────────────────────────

_NOTE = {
    "file": "A new entry intent was filed",
    "resolve_open": "Entry accepted (open mode)",
    "accept": "Entry accepted",
    "reject": "Entry rejected",
    "withdraw": "Entry withdrawn by the entrant",
    "retire": "Entry retired",
    "activate": "Entry is now active",
    "revive": "Entry revived by new activity",
    "go_dormant": "Entry went dormant (no activity for 14 days; kept, revives on activity)",
}


def _poster_email(a: dict) -> str:
    post_id = a["objects"].get("post_id")
    post = state.kassa.get_post(post_id) if post_id else None
    return (post or {}).get("from_email", "") or ""


def _notify(a: dict, transition: str, actor_agent: str | None, title: str = "") -> None:
    """Inbox the counterparty and email the poster. Never raises; carries no authority."""
    try:
        from app.inbox import notify_agent
        text = _NOTE.get(transition, transition)
        aid = a["agreement_id"]
        body = (f"{text}. Agreement {aid} for {a['opportunity_ref']} is now '{a['state']}'. "
                f"This notice carries no authority; the record is the agreement.")
        for who in {_entrant(a), _owner(a)} - {actor_agent}:
            if who and not who.startswith(("poster:", "platform")):
                notify_agent(who, f"work_entry_{transition}", f"{text}: {title or a['opportunity_ref']}",
                             body, ref_type="agreement", ref_id=aid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("work-entry inbox notify failed: %s", exc)
    try:
        to = _poster_email(a)
        if to:
            from app.notifications import _send_email
            from app.routes.kassa import _poster_mail_target
            poster_agent = None
            if _owner(a) and not _owner(a).startswith(("poster:", "platform")):
                poster_agent = next((r for r in state.runtime.registry
                                     if r.get("agent_id") == _owner(a)), None)
            target = _poster_mail_target(to, poster_agent)
            if target:
                _send_email(target, f"[CIVITAE] {_NOTE.get(transition, transition)}",
                            f"{_NOTE.get(transition, transition)}.\n\nAgreement: {a['agreement_id']}\n"
                            f"Opportunity: {a['opportunity_ref']}\nState: {a['state']}\n\n"
                            "This email carries no authority. - CIVITAE\n")
    except Exception as exc:  # noqa: BLE001
        logger.warning("work-entry poster email failed: %s", exc)


# ── maintenance: 48 h ask-the-poster, 14 d dormant (lazy + idempotent sweep) ──

def sweep_entries() -> dict:
    """Idempotent. pending >=14 d quiet -> dormant; pending >=48 h quiet -> ask the
    poster once per quiet spell. Safe to call from a scheduler, a read, or by hand."""
    store = _store()
    dormant: list[str] = []
    asked: list[str] = []
    try:
        dormant = store.sweep_dormant(after=DORMANT_AFTER)
    except WorkEntryError as e:
        logger.error("work-entry dormant sweep failed: %s", e.message)
    for aid in dormant:
        try:
            _notify(store.get(aid), "go_dormant", None)
        except Exception:  # noqa: BLE001
            pass
    for a in store.pending_stale(older_than=ASK_POSTER_AFTER):
        if store.claim_flag(a["agreement_id"], "ask_poster", a["last_activity_at"]):
            asked.append(a["agreement_id"])
            try:
                from app.inbox import notify_agent
                owner = _owner(a)
                if owner and not owner.startswith(("poster:", "platform")):
                    notify_agent(
                        owner, "work_entry_ask_poster",
                        f"Entry waiting 48 h: {a['opportunity_ref']}",
                        f"Agreement {a['agreement_id']} has had no answer for 48 hours. Keep it live, "
                        "decline it (reject with a reason), or retire it. Nothing expires; after 14 days "
                        "it goes dormant and revives on any activity.",
                        ref_type="agreement", ref_id=a["agreement_id"])
                to = _poster_email(a)
                if to:
                    from app.notifications import _send_email
                    _send_email(to, "[CIVITAE] An entry is waiting for your answer",
                                f"Agreement {a['agreement_id']} for {a['opportunity_ref']} has had no answer "
                                "for 48 hours. Keep it live, decline it, or retire it. Nothing expires.\n")
            except Exception as exc:  # noqa: BLE001
                logger.warning("ask-poster notify failed: %s", exc)
    return {"dormant": dormant, "asked_poster": asked}


def _lazy() -> None:
    try:
        sweep_entries()
    except Exception as exc:  # noqa: BLE001 - a read must never fail on maintenance
        logger.warning("work-entry lazy sweep failed: %s", exc)


def _revive_if_dormant(aid: str, actor: str, acting_for: str | None, cred: str) -> None:
    """Any activity revives a dormant entry (accept/reject/activity on a dormant one)."""
    if _store().get(aid)["state"] == "dormant":
        _store().record_activity(aid, actor=actor, acting_for=acting_for, credential=cred)


# ── routes ───────────────────────────────────────────────────────────────

@router.post("/api/work-entry")
def file_entry(payload: FileEntryPayload, request: Request):
    p = _principal(request)
    entrant = p.require_agent()   # only a registered agent can file intent
    opp = _resolve_opportunity(payload.opportunity_ref.strip())
    if opp["owner"] == entrant:
        return JSONResponse({"error": "You cannot enter your own opportunity", "code": "own_opportunity"},
                            status_code=409)
    mode = opp["base_mode"] if opp["base_mode"] in _MODE_RANK else "standard"
    if payload.entry_mode:
        if payload.entry_mode not in _MODE_RANK:
            raise HTTPException(422, "entry_mode must be open, standard or constitutional")
        if _MODE_RANK[payload.entry_mode] > _MODE_RANK[mode]:
            mode = payload.entry_mode   # may only escalate, never relax
    ev = None
    if payload.delivery_evidence_class is not None:
        ev = _EVIDENCE_CLASSES.get(str(payload.delivery_evidence_class).strip().lower())
        if ev is None:
            raise HTTPException(422, "delivery_evidence_class must be 1/2/3 or "
                                     "solution / solution_proof / solution_proof_work_access")
    terms = {**payload.terms,
             "pitch": sanitize_text(payload.pitch) if payload.pitch else None,
             "acceptance_payload": payload.acceptance_payload,
             "delivery_evidence_class": ev or "solution",
             "stake_ref": payload.stake_ref}
    key = payload.idempotency_key or request.headers.get("Idempotency-Key")
    try:
        out = _store().file_entry(
            entrant=entrant, owner=opp["owner"], opportunity_ref=opp["ref"], entry_mode=mode,
            objects=opp["objects"], terms=terms, credential_refs={"entrant": p.ref},
            idempotency_key=key, supersedes=payload.supersedes)
    except WorkEntryError as e:
        return _err(e)
    a = out["agreement"]
    if not out["replayed"]:
        _notify(a, "file" if mode != "open" else "resolve_open", entrant, opp["title"])
    return JSONResponse({**out, "next": _next_hint(a)}, status_code=200 if out["replayed"] else 201)


def _next_hint(a: dict) -> str:
    return {"pending": "awaiting the opportunity owner's resolution",
            "accepted": "entrant (or owner) activates to begin; the second step is explicit",
            "active": "entry is active", "dormant": "dormant; any activity revives it"}.get(
        a["state"], "terminal; kept as the archive")


def _act(request: Request, aid: str, name: str, body: ActionPayload | None):
    p = _principal(request)
    a = _get_or_404(aid)
    body = body or ActionPayload()
    actor, acting_for, cred = _actor(p, a, body)
    store = _store()
    try:
        if name == "accept" and a["state"] in ("pending", "dormant") and a["governance"]["mode"] == "constitutional":
            # authority first so a stranger learns nothing, then the gate
            if _actor_may_resolve(p, a, actor, acting_for):
                return JSONResponse(GATE_REQUIRED, status_code=409)
        if name in ("accept", "reject"):
            _revive_if_dormant(aid, actor, acting_for, cred)
        kw = dict(actor=actor, acting_for=acting_for, idempotency_key=body.idempotency_key, credential=cred)
        if name == "reject":
            out = store.reject(aid, reason=body.reason or "", **kw)
        elif name in ("withdraw", "retire"):
            out = getattr(store, name)(aid, reason=body.reason, **kw)
        else:
            out = getattr(store, name)(aid, **kw)
    except WorkEntryError as e:
        return _err(e)
    if not out["replayed"]:
        _notify(out["agreement"], name, actor if p.kind == "agent" else acting_for,
                out["agreement"]["opportunity_ref"])
    return {**out, "next": _next_hint(out["agreement"])}


def _actor_may_resolve(p: Principal, a: dict, actor: str, acting_for: str | None) -> bool:
    who = acting_for if actor.startswith(("operator:", "poster-link:")) else actor
    return who == _owner(a)


@router.post("/api/work-entry/sweep")
def sweep(request: Request):
    p = _principal(request)
    if p.kind != "operator":
        raise HTTPException(403, "Operator credential required")
    return sweep_entries()


@router.post("/api/work-entry/{agreement_id}/accept")
def accept(agreement_id: str, request: Request, body: ActionPayload | None = None):
    return _act(request, agreement_id, "accept", body)


@router.post("/api/work-entry/{agreement_id}/reject")
def reject(agreement_id: str, request: Request, body: ActionPayload | None = None):
    if not (body and body.reason and body.reason.strip()):
        _principal(request)
        _get_or_404(agreement_id)
        return JSONResponse({"error": "'reject' requires a named reason", "code": "reason_required"},
                            status_code=400)
    return _act(request, agreement_id, "reject", body)


@router.post("/api/work-entry/{agreement_id}/withdraw")
def withdraw(agreement_id: str, request: Request, body: ActionPayload | None = None):
    return _act(request, agreement_id, "withdraw", body)


@router.post("/api/work-entry/{agreement_id}/retire")
def retire(agreement_id: str, request: Request, body: ActionPayload | None = None):
    return _act(request, agreement_id, "retire", body)


@router.post("/api/work-entry/{agreement_id}/activate")
def activate(agreement_id: str, request: Request, body: ActionPayload | None = None):
    return _act(request, agreement_id, "activate", body)


@router.post("/api/work-entry/{agreement_id}/activity")
def activity(agreement_id: str, request: Request, body: ActionPayload | None = None):
    """Any activity by either party; revives a dormant entry to pending."""
    p = _principal(request)
    a = _get_or_404(agreement_id)
    actor, acting_for, cred = _actor(p, a, body)
    try:
        out = _store().record_activity(agreement_id, actor=actor, acting_for=acting_for, credential=cred)
    except WorkEntryError as e:
        return _err(e)
    if out.get("receipt"):
        _notify(out["agreement"], "revive", actor if p.kind == "agent" else acting_for)
    return out


@router.get("/api/work-entry/{agreement_id}")
def get_entry(agreement_id: str, request: Request):
    p = _principal(request)
    _lazy()
    a = _get_or_404(agreement_id)
    if not _is_party_view(p, a):
        raise HTTPException(403, "Only the parties to an entry (or an operator) may read it")
    return {"agreement": a, "receipts": _store().receipts(agreement_id),
            "evidence_gaps": _store().evidence_gaps(agreement_id)}


@router.get("/api/work-entry")
def list_entries(request: Request, entrant: str | None = None, owner: str | None = None,
                 opportunity_ref: str | None = None, state_: str | None = None,
                 live: bool = False, include_dormant: bool = False):
    p = _principal(request)
    _lazy()
    q = request.query_params
    st = state_ or q.get("state")
    opp = None
    if opportunity_ref:
        k, i = _kind_of(opportunity_ref.strip())
        opp = f"{k}:{i}"
    rows = _store().list(entrant=entrant, owner=owner, opportunity_ref=opp, state=st)
    if p.kind == "agent":
        rows = [a for a in rows if _is_party_view(p, a)]
    elif p.kind == "poster_link":
        rows = [a for a in rows if _is_party_view(p, a)]
    if live:
        rows = [a for a in rows if a["state"] not in
                ("rejected", "withdrawn", "retired", "terminated", "completed", "dormant")]
    elif not include_dormant and st != "dormant":
        rows = [a for a in rows if a["state"] != "dormant"]
    return {"entries": rows, "count": len(rows)}
