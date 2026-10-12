"""Entry API -- /api/work-entry (P4 slice 3).

File an entry intent against an opportunity (post, slot or mission), and
resolve it per mode:

    open            click 1 (file) -> accepted; click 2 (activate) -> active
    standard        the owner (or an operator acting FOR the named owner) accepts/rejects
    constitutional  owner resolves AND the governance gate is required (slice 5): a typed
                    motion {kind: work_entry_gate, agreement_id}; advisory result + owner
                    countersign by default, council_delegated switches it (see workentry_gate)

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
from app import slot_binding
from app import workentry_gate
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
    "terminate": "Entry terminated (the slot could not be bound; evidence_gap recorded)",
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

def _bind_hint(a: dict, extra: dict | None = None) -> dict:
    """O-J-2: hand Mission Control the mission_id (and slot) this agreement is bound to."""
    mid = a["objects"].get("mission_id")
    return {"mission_id": mid, "slot_id": a["objects"].get("slot_id"),
            "mission_control": slot_binding.mission_control_ref(mid), **(extra or {})}


def _bind_failed(e: "slot_binding.BindError") -> JSONResponse:
    if e.agreement:
        _notify(e.agreement, "terminate", None)
    return JSONResponse(e.body(), status_code=e.status)


@router.post("/api/work-entry")
async def file_entry(payload: FileEntryPayload, request: Request):
    return await svc_file_entry(_principal(request), payload,
                                payload.idempotency_key or request.headers.get("Idempotency-Key"))


async def svc_file_entry(p: Principal, payload: FileEntryPayload, key: str | None):
    """Service layer for filing an entry: shared by HTTP (/api/work-entry) and the MCP verbs.
    Returns a dict / JSONResponse; raises HTTPException for authority and validation errors."""
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
    try:
        out = _store().file_entry(
            entrant=entrant, owner=opp["owner"], opportunity_ref=opp["ref"], entry_mode=mode,
            objects=opp["objects"], terms=terms, credential_refs={"entrant": p.ref},
            idempotency_key=key, supersedes=payload.supersedes)
    except WorkEntryError as e:
        return _err(e)
    a = out["agreement"]
    if not out["replayed"]:
        if a["state"] == "accepted":
            # open-mode post-origin: acceptance is immediate, so the slot/mission is minted now
            try:
                a = await slot_binding.mint_for_post(a)
                out = {**out, "agreement": a}
            except slot_binding.BindError as e:
                return _bind_failed(e)
        _notify(a, "file" if mode != "open" else "resolve_open", entrant, opp["title"])
    return JSONResponse({**out, **_bind_hint(a), "next": _next_hint(a)},
                        status_code=200 if out["replayed"] else 201)


def _next_hint(a: dict) -> str:
    return {"pending": "awaiting the opportunity owner's resolution",
            "accepted": "entrant (or owner) activates to begin; the second step is explicit",
            "active": "entry is active", "dormant": "dormant; any activity revives it"}.get(
        a["state"], "terminal; kept as the archive")


async def _act(request: Request, aid: str, name: str, body: ActionPayload | None):
    return await svc_act(_principal(request), aid, name, body)


async def svc_act(p: Principal, aid: str, name: str, body: ActionPayload | None):
    """Service layer for accept/reject/withdraw/retire/activate: shared by HTTP and MCP."""
    if name == "reject" and not (body and body.reason and body.reason.strip()):
        _get_or_404(aid)
        return JSONResponse({"error": "'reject' requires a named reason", "code": "reason_required"},
                            status_code=400)
    a = _get_or_404(aid)
    body = body or ActionPayload()
    actor, acting_for, cred = _actor(p, a, body)
    store = _store()
    try:
        if name in ("accept", "activate") and a["governance"]["mode"] == "constitutional" \
                and a["state"] in ("pending", "dormant", "accepted") \
                and (name == "activate" or _actor_may_resolve(p, a, actor, acting_for)):
            # authority first so a stranger learns nothing; then read any passed gate motion (the
            # consumer) so the store's gate check sees it. The store enforces the gate itself.
            _sync_gate(aid)
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
        # Slice 4: acceptance mints the slot/mission for a post-origin entry; activation binds the
        # slot (Agreement-first, then slot write; failure -> evidence_gap + compensating terminated).
        try:
            if name == "accept" and out["agreement"]["state"] == "accepted":
                out = {**out, "agreement": await slot_binding.mint_for_post(out["agreement"])}
            elif name == "activate":
                await slot_binding.bind_on_activation(out["agreement"])
        except slot_binding.BindError as e:
            return _bind_failed(e)
        _notify(out["agreement"], name, actor if p.kind == "agent" else acting_for,
                out["agreement"]["opportunity_ref"])
    return {**out, **_bind_hint(out["agreement"]), "next": _next_hint(out["agreement"])}


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
async def accept(agreement_id: str, request: Request, body: ActionPayload | None = None):
    return await _act(request, agreement_id, "accept", body)


@router.post("/api/work-entry/{agreement_id}/reject")
async def reject(agreement_id: str, request: Request, body: ActionPayload | None = None):
    return await _act(request, agreement_id, "reject", body)


@router.post("/api/work-entry/{agreement_id}/withdraw")
async def withdraw(agreement_id: str, request: Request, body: ActionPayload | None = None):
    return await _act(request, agreement_id, "withdraw", body)


@router.post("/api/work-entry/{agreement_id}/retire")
async def retire(agreement_id: str, request: Request, body: ActionPayload | None = None):
    return await _act(request, agreement_id, "retire", body)


@router.post("/api/work-entry/{agreement_id}/activate")
async def activate(agreement_id: str, request: Request, body: ActionPayload | None = None):
    return await _act(request, agreement_id, "activate", body)


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


# ── constitutional gate (slice 5) ────────────────────────────────────────

def _sync_gate(aid: str) -> dict:
    """The consumer: read gate motions for this agreement from the meetings store, resolve any whose
    window has elapsed, and record the result on the agreement. Persists meetings only on success."""
    from app.routes.governance import _load_meetings, _save_meetings
    meetings = _load_meetings()
    meetings, changed, out = workentry_gate.sync(_store(), aid, meetings)
    if changed:
        _save_meetings(meetings)
    return out


def _require_party_or_operator(p: Principal, a: dict) -> None:
    if not _is_party_view(p, a):
        raise HTTPException(403, "Only the parties to an entry (or an operator) may act on its gate")


@router.get("/api/work-entry/gate/settings")
def gate_settings_get(request: Request):
    p = _principal(request)
    if p.kind != "operator":
        raise HTTPException(403, "Operator credential required")
    return _store().gate_settings()


@router.post("/api/work-entry/gate/settings")
async def gate_settings_set(request: Request):
    """Owner-held: flip binding_authority (advisory_with_owner_countersign | council_delegated)
    or the async window (hours) without code change."""
    p = _principal(request)
    if p.kind != "operator":
        raise HTTPException(403, "Operator credential required")
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    if not isinstance(body, dict):
        raise HTTPException(422, "JSON object required")
    window = body.get("gate_window_hours")
    if window is not None and (isinstance(window, bool) or not isinstance(window, (int, float))):
        raise HTTPException(422, "gate_window_hours must be a number")
    try:
        return _store().set_gate_settings(binding_authority=body.get("binding_authority"),
                                          gate_window_hours=window, actor="operator:admin")
    except WorkEntryError as e:
        raise HTTPException(422, e.message)


@router.get("/api/work-entry/{agreement_id}/gate")
def gate_get(agreement_id: str, request: Request):
    p = _principal(request)
    a = _get_or_404(agreement_id)
    _require_party_or_operator(p, a)
    try:
        sync_out = _sync_gate(agreement_id)
    except WorkEntryError as e:
        return _err(e)
    return {**_store().gate_status(agreement_id), "open_motions": sync_out["open_motions"]}


@router.post("/api/work-entry/{agreement_id}/gate/sync")
def gate_sync(agreement_id: str, request: Request):
    p = _principal(request)
    a = _get_or_404(agreement_id)
    _require_party_or_operator(p, a)
    try:
        out = _sync_gate(agreement_id)
    except WorkEntryError as e:
        return _err(e)
    st = _store().gate_status(agreement_id)
    return {**st, "open_motions": out["open_motions"], "recorded": out["recorded"]}


@router.post("/api/work-entry/{agreement_id}/gate/countersign")
def gate_countersign(agreement_id: str, request: Request):
    """The owner-held binding act while the body is advisory (GOV-001 s9.3). Operator only."""
    p = _principal(request)
    _get_or_404(agreement_id)
    if p.kind != "operator":
        raise HTTPException(403, "The gate countersign is owner-held: operator credential required")
    try:
        _sync_gate(agreement_id)
        out = _store().countersign_gate(agreement_id, actor="operator:admin", credential=p.ref)
    except WorkEntryError as e:
        return _err(e)
    return {**out, "gate_status": _store().gate_status(agreement_id)}


# ── agreement-bound deploy (slice 6) ─────────────────────────────────────
# Mission-scoped DEPLOY: needs an ACTIVE Agreement on the mission whose owner principal holds deploy
# authority there. The gate follows the mission's entry_mode (open: none beyond these checks;
# standard: the resolver -- the owner who accepted -- is the only actor; constitutional: the slice-5
# governance gate must be satisfied). Unavailable while frozen. Emits receipt + Seed. DEPLOY is not
# COMMAND/CAMPAIGN, and the global POST /api/deploy is untouched (operator-only).

class DeployPayload(BaseModel):
    agreement_id: str | None = None
    note: str | None = Field(default=None, max_length=2000)
    acting_for: str | None = None         # operator only: the named principal it acts FOR
    idempotency_key: str | None = None


_ENDED_MISSION = ("completed", "cancelled", "closed", "ended")


def _mission_or_404(mission_id: str) -> dict:
    m = slot_binding.find_mission(mission_id)
    if m is None:
        raise HTTPException(404, "Mission not found")
    return m


def _mission_frozen(m: dict) -> bool:
    return bool(m.get("frozen")) or m.get("status") == "frozen"


def _deploy_mode(m: dict, a: dict | None) -> str:
    """The mission's entry_mode (open when absent); an agreement filed stricter never relaxes it."""
    mm = m.get("entry_mode") if m.get("entry_mode") in _MODE_RANK else "open"
    am = a["entry_mode"] if a and a["entry_mode"] in _MODE_RANK else "open"
    return mm if _MODE_RANK[mm] >= _MODE_RANK[am] else am


def _deploy_gate(mode: str, a: dict | None) -> dict:
    if mode == "open":
        return {"required": False, "kind": "none", "satisfied": True, "blocking": None, "gate_id": None}
    if mode == "standard":
        return {"required": True, "kind": "resolver", "satisfied": a is not None, "blocking": None,
                "gate_id": None, "resolver": _owner(a) if a else None}
    if a is None:
        return {"required": True, "kind": "governance", "satisfied": False,
                "blocking": "governance_gate_required", "gate_id": None}
    if a["entry_mode"] != "constitutional":
        # the mission demands the gate but this agreement never opened one (no motion can bind to it)
        return {"required": True, "kind": "governance", "satisfied": False,
                "blocking": "governance_gate_required", "gate_id": None,
                "binding_authority": _store().binding_authority}
    try:
        _sync_gate(a["agreement_id"])
    except Exception as exc:  # noqa: BLE001 - reading the gate must not fail the preflight
        logger.warning("deploy gate sync failed: %s", exc)
    st = _store().gate_status(a["agreement_id"])
    return {"required": True, "kind": "governance", "satisfied": st["satisfied"], "blocking": st["blocking"],
            "gate_id": st["gate_id"], "binding_authority": st["binding_authority"]}


def _deploy_principal(p: Principal, ags: list[dict], acting_for: str | None) -> tuple[str, str | None, str | None]:
    """(actor, acting_for, who) -- who = the principal the caller speaks AS for deploy authority."""
    if p.kind == "agent":
        return p.agent_id, None, p.agent_id
    if p.kind == "operator":
        return "operator:admin", acting_for, (acting_for or None)
    mine = [a for a in ags if a["objects"].get("post_id") and a["objects"]["post_id"] == p.post_id]
    who = _owner(mine[0]) if mine else None
    return f"poster-link:{p.thread_id}", who, who


def _mission_agreements(mission: dict) -> list[dict]:
    return _store().list_by_object("mission_id", mission.get("id") or mission.get("mission_id"))


def _may_read_mission(p: Principal, mission: dict, ags: list[dict]) -> bool:
    if p.kind == "operator":
        return True
    if p.kind == "agent":
        return mission.get("owner_agent_id") == p.agent_id or any(_is_party_view(p, a) for a in ags)
    return any(_is_party_view(p, a) for a in ags)


def _deploy_view(p: Principal, mission: dict, ags: list[dict], acting_for: str | None,
                 agreement_id: str | None = None) -> dict:
    actor, af, who = _deploy_principal(p, ags, acting_for)
    active = [a for a in ags if a["state"] == "active"]
    holders = [a for a in active if who and _owner(a) == who]
    chosen = None
    if agreement_id:
        chosen = next((a for a in holders if a["agreement_id"] == agreement_id), None)
    elif holders:
        chosen = holders[-1]
    mode = _deploy_mode(mission, chosen or (active[-1] if active else None))
    gate = _deploy_gate(mode, chosen)
    frozen = _mission_frozen(mission)
    blocking = None
    if not active:
        blocking = "no_active_agreement"
    elif chosen is None:
        blocking = "no_deploy_authority"
    elif frozen:
        blocking = "mission_frozen"
    elif mission.get("status") in _ENDED_MISSION:
        blocking = "mission_not_deployable"
    elif not gate["satisfied"]:
        blocking = gate["blocking"] or "governance_gate_required"
    return {
        "actor": actor, "acting_for": af, "who": who, "chosen": chosen, "mode": mode, "gate": gate,
        "frozen": frozen, "blocking": blocking, "active": active,
        "agreements": [{"agreement_id": a["agreement_id"], "state": a["state"], "entry_mode": a["entry_mode"],
                        "owner": _owner(a), "entrant": _entrant(a), "slot_id": a["objects"].get("slot_id"),
                        "holds_deploy_authority": a["state"] == "active" and bool(who) and _owner(a) == who}
                       for a in ags],
    }


@router.get("/api/work-entry/mission/{mission_id}/deploy/preflight")
def deploy_preflight(mission_id: str, request: Request, acting_for: str | None = None,
                     agreement_id: str | None = None):
    """ARM DEPLOY preflight: read-only. The mission's Agreement(s), entry_mode, the gate requirement,
    frozen state, and whether THIS caller may deploy now (and if not, why)."""
    p = _principal(request)
    mission = _mission_or_404(mission_id)
    ags = _mission_agreements(mission)
    if not _may_read_mission(p, mission, ags):
        raise HTTPException(403, "Only a party to an Agreement on this mission (or an operator) may read its deploy preflight")
    v = _deploy_view(p, mission, ags, acting_for, agreement_id)
    mid = mission.get("id") or mission_id
    return {"mission_id": mid, "mission_status": mission.get("status"), "entry_mode": v["mode"],
            "frozen": v["frozen"], "gate": v["gate"], "agreements": v["agreements"],
            "agreement_id": v["chosen"]["agreement_id"] if v["chosen"] else None,
            "can_deploy": v["blocking"] is None, "blocking": v["blocking"],
            "caller": {"principal": v["who"], "credential": p.ref},
            "mission_control": slot_binding.mission_control_ref(mid)}


@router.post("/api/work-entry/mission/{mission_id}/deploy")
async def deploy_mission(mission_id: str, request: Request, body: DeployPayload | None = None):
    body = body or DeployPayload()
    p = _principal(request)
    mission = _mission_or_404(mission_id)
    mid = mission.get("id") or mission_id
    ags = _mission_agreements(mission)
    v = _deploy_view(p, mission, ags, body.acting_for, body.agreement_id)
    if v["blocking"] in ("no_active_agreement", "no_deploy_authority"):
        return JSONResponse({"error": "Deploy requires an active Agreement whose principal holds deploy "
                                      "authority on this mission", "code": v["blocking"]}, status_code=403)
    if v["blocking"] in ("mission_frozen", "mission_not_deployable", "governance_gate_required",
                         "owner_countersign_required"):
        msg = {"mission_frozen": "Mission is frozen; deploy is unavailable until it is unfrozen",
               "mission_not_deployable": f"Mission is {mission.get('status')}; it cannot be deployed",
               "governance_gate_required": "The governance gate for this mission is not satisfied",
               "owner_countersign_required": "The governance motion passed but is advisory; an "
                                             "owner-held countersign is required"}[v["blocking"]]
        return JSONResponse({"error": msg, "code": v["blocking"], "gate": v["gate"]}, status_code=409)
    a = v["chosen"]
    try:
        out = _store().record_deploy(
            a["agreement_id"], mission_id=mid, actor=v["actor"], acting_for=v["acting_for"],
            credential=p.ref, entry_mode=v["mode"], gate_id=v["gate"].get("gate_id"), note=body.note,
            idempotency_key=body.idempotency_key or request.headers.get("Idempotency-Key"))
    except WorkEntryError as e:
        return _err(e)
    if not out["replayed"]:
        try:
            await state.emit("mission_deployed", {"mission_id": mid, "agreement_id": a["agreement_id"],
                                                  "receipt_id": out["receipt"]["receipt_id"]})
        except Exception as exc:  # noqa: BLE001 - the receipt is already durable
            logger.warning("mission_deployed emit failed: %s", exc)
    return JSONResponse({"deployed": True, "replayed": out["replayed"], "receipt": out["receipt"],
                         "agreement_id": a["agreement_id"], "mission_id": mid, "entry_mode": v["mode"],
                         "gate": v["gate"], "mission_control": slot_binding.mission_control_ref(mid)},
                        status_code=200 if out["replayed"] else 201)


# ── screen read models (P4 slice 7): every value the screens show comes from these ──────────

_EVIDENCE_LABELS = [("solution", "Solution"), ("solution_proof", "Solution + Proof"),
                    ("solution_proof_work_access", "Solution + Proof + Work access")]
_LIVE_FOR_PREVIEW = ("pending", "dormant", "accepted", "active")


def _optional_principal(request: Request) -> Principal | None:
    """Public read that personalises when a credential is presented. A presented-but-invalid
    credential still fails closed (401); only 'no credential at all' reads as the public view."""
    try:
        return _principal(request)
    except HTTPException as e:
        if e.status_code == 401 and e.detail == "Authentication required":
            return None
        raise


def _acceptance_view(mode: str) -> dict:
    if mode == "open":
        return {"kind": "auto_accept", "resolver": "none", "clicks": 2, "gate": None,
                "text": "Open mode: the entry is accepted as soon as it is filed; a second explicit "
                        "click activates it. Nothing compresses the Agreement itself."}
    if mode == "standard":
        return {"kind": "resolver", "resolver": "owner", "clicks": 2, "gate": None,
                "text": "The opportunity owner (poster) accepts or rejects. No timer cuts the entry: "
                        "if the poster is silent they are asked to keep it live, decline or retire it."}
    binding = _store().binding_authority
    return {"kind": "governance_gate", "resolver": "owner", "clicks": 2,
            "gate": {"type": "work_entry_gate", "binding_authority": binding},
            "text": "The owner resolves AND a governance gate (a typed motion bound to this Agreement) "
                    "is required; while the body is advisory the owner's countersign is the binding act."}


@router.get("/api/work-entry/opportunity/{ref:path}")
def preview_opportunity(ref: str, request: Request):
    """Terms preview for the Enter flow: mode, acceptance rule, evidence classes, objects, and (when a
    credential is presented) the caller's own standing. The owner's identity is never disclosed."""
    p = _optional_principal(request)
    opp = _resolve_opportunity(ref.strip())
    mode = opp["base_mode"] if opp["base_mode"] in _MODE_RANK else "standard"
    caller = mine = None
    if p is not None and p.kind == "agent":
        caller = {"principal": p.agent_id, "credential_type": p.credential_type,
                  "own_opportunity": opp["owner"] == p.agent_id}
        live = [a for a in _store().list(entrant=p.agent_id, opportunity_ref=opp["ref"])
                if a["state"] in _LIVE_FOR_PREVIEW]
        if live:
            mine = {"agreement_id": live[-1]["agreement_id"], "state": live[-1]["state"],
                    "entry_mode": live[-1]["entry_mode"]}
    return {"ref": opp["ref"], "kind": opp["kind"], "title": opp["title"], "entry_mode": mode,
            "acceptance": _acceptance_view(mode),
            "delivery_evidence_classes": [{"id": i, "label": lbl} for i, lbl in _EVIDENCE_LABELS],
            "objects": opp["objects"],
            "owner_kind": "agent" if not str(opp["owner"]).startswith(("poster:", "platform")) else "poster",
            "withdrawal": "Free to withdraw while pending; retire by either party.",
            "caller": caller, "mine": mine}


def _acceptance_record(a: dict, receipts: list[dict]) -> dict:
    acc = next((r for r in receipts if r["to"] == "accepted"), None)
    act = next((r for r in receipts if r["to"] == "active"), None)
    return {"terms_accepted_at": acc["at"] if acc else None,
            "accepted_by": (acc["acting_for"] or acc["actor"]) if acc else None,
            "accepted_via": acc["credential_ref"] if acc else None,
            "acceptance_receipt_id": acc["receipt_id"] if acc else None,
            "acceptance_seed_doi": acc["seed_doi"] if acc else None,
            "active_at": act["at"] if act else None,
            "delivery_evidence_class": a["terms"].get("delivery_evidence_class"),
            "outcome_reason": a.get("outcome_reason")}


@router.get("/api/work-entry/mission/{mission_id}")
def mission_agreements(mission_id: str, request: Request):
    """Mission Control read model: the Agreement node (terms_accepted -> active), the Acceptance
    record and the receipts for PROGRESS. Party to an Agreement on the mission, its owner, or an operator."""
    p = _principal(request)
    _lazy()
    mission = _mission_or_404(mission_id)
    mid = mission.get("id") or mission_id
    ags = _mission_agreements(mission)
    if not _may_read_mission(p, mission, ags):
        raise HTTPException(403, "Only a party to an Agreement on this mission (or an operator) may read it")
    if p.kind != "operator":
        ags = [a for a in ags if p.kind == "agent" and mission.get("owner_agent_id") == p.agent_id
               or _is_party_view(p, a)]
    rows = []
    for a in ags:
        rc = _store().receipts(a["agreement_id"])
        rows.append({"agreement": a, "receipts": rc, "acceptance": _acceptance_record(a, rc),
                     "gates": _store().gates(a["agreement_id"])})
    chosen = next((r["agreement"] for r in reversed(rows) if r["agreement"]["state"] in _LIVE_FOR_PREVIEW),
                  rows[-1]["agreement"] if rows else None)
    return {"mission_id": mid, "mission_status": mission.get("status"),
            "entry_mode": mission.get("entry_mode") or "open", "frozen": _mission_frozen(mission),
            "agreements": rows,
            "node": ({"label": "terms_accepted \u2192 active", "state": chosen["state"],
                      "agreement_id": chosen["agreement_id"]} if chosen else None),
            "deployments": _store().deployments(mission_id=mid)}


@router.get("/api/work-entry/{agreement_id}")
def get_entry(agreement_id: str, request: Request):
    return svc_get_entry(_principal(request), agreement_id)


def svc_get_entry(p: Principal, agreement_id: str) -> dict:
    _lazy()
    a = _get_or_404(agreement_id)
    if not _is_party_view(p, a):
        raise HTTPException(403, "Only the parties to an entry (or an operator) may read it")
    return {"agreement": a, "receipts": _store().receipts(agreement_id),
            "gates": _store().gates(agreement_id),
            "evidence_gaps": _store().evidence_gaps(agreement_id)}


@router.get("/api/work-entry")
def list_entries(request: Request, entrant: str | None = None, owner: str | None = None,
                 opportunity_ref: str | None = None, state_: str | None = None,
                 live: bool = False, include_dormant: bool = False):
    st = state_ or request.query_params.get("state")
    return svc_list_entries(_principal(request), entrant=entrant, owner=owner,
                            opportunity_ref=opportunity_ref, st=st, live=live,
                            include_dormant=include_dormant)


def svc_list_entries(p: Principal, *, entrant=None, owner=None, opportunity_ref=None, st=None,
                     live: bool = False, include_dormant: bool = False) -> dict:
    _lazy()
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
