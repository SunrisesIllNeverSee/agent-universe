"""
escrow.py — escrow routes and the shared release/refund helpers (P5).

A poster funds an escrow for a mission (Stripe Checkout webhook, or the
operator for local runs). Funds are held until acceptance: mission end, task
close or an operator release pays out through ``economy.process_mission_payout``
(fee from config). Whatever is left is refunded to the poster. A dispute only
freezes. Every transition is audited and Seeded; a Seed failure after money has
moved is loud (``provenance_failed`` audit + returned), never silent.

Missions import the helpers below; this module imports missions lazily.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.auth import admin_key_matches
from app.deps import state
from app.escrow import EscrowError
from app.seeds import create_seed
from app.workentry_store import TERMINAL_STATES

router = APIRouter(tags=["escrow"])

MAX_ESCROW = 1_000_000.0


# ── helpers shared with missions.py / connect.py ───────────────────────────

async def escrow_event(rec: dict, transition: str, *, actor: str, **detail) -> dict:
    """Audit + Seed for one escrow transition. Loud on Seed failure."""
    meta = {"action": f"escrow_{transition}", "escrow_id": rec["escrow_id"], "mission_id": rec.get("mission_id"),
            "agreement_id": rec.get("agreement_id"), "state": rec["state"], "amount": rec["amount"],
            "remaining": rec["remaining"], "actor": actor, **detail}
    state.audit.log("economy", f"escrow_{transition}", meta)
    try:
        seed = await create_seed(source_type=f"escrow_{transition}", source_id=rec["escrow_id"],
                                 creator_id=actor, creator_type="BI",
                                 seed_type="planted" if transition == "funded" else "grown", metadata=meta)
        if seed and seed.get("doi"):
            return {"doi": seed["doi"]}
        raise RuntimeError("create_seed returned no doi")
    except Exception as exc:  # noqa: BLE001
        state.audit.log("economy", "provenance_failed", {**meta, "error": str(exc)[:200]})
        return {"doi": None, "error": str(exc)[:200]}


def link_agreements(escrow: dict) -> list[str]:
    """Write escrow_id onto the bound Agreement(s): the named one, else every live
    Agreement on the mission that has none yet. Best effort; the escrow is the truth."""
    linked: list[str] = []
    try:
        if escrow.get("agreement_id"):
            ags = [state.workentry.get(escrow["agreement_id"])]
        else:
            ags = state.workentry.list_by_object("mission_id", escrow.get("mission_id") or "")
        for a in ags:
            if a["state"] in TERMINAL_STATES:
                continue
            if (a.get("objects") or {}).get("escrow_id") in (None, escrow["escrow_id"]):
                state.workentry.bind_objects(a["agreement_id"], escrow_id=escrow["escrow_id"])
                linked.append(a["agreement_id"])
    except Exception as exc:  # noqa: BLE001
        state.audit.log("economy", "escrow_link_failed", {"escrow_id": escrow["escrow_id"], "error": str(exc)[:200]})
    return linked


async def fund_escrow(*, poster_id: str, amount: float, source: str, mission_id: str | None,
                      agreement_id: str | None = None, stripe_session_id: str | None = None,
                      charged_at: str | None = None, actor: str = "operator") -> dict:
    rec = state.escrow.fund(poster_id=poster_id, amount=amount, source=source, mission_id=mission_id,
                            agreement_id=agreement_id, stripe_session_id=stripe_session_id, charged_at=charged_at)
    if rec.get("duplicate"):
        return {"escrow": rec, "seed": {"doi": None}, "duplicate": True}
    seeds = [await escrow_event(rec, "funded", actor=actor, source=source)]
    if mission_id:
        rec = state.escrow.hold(rec["escrow_id"], mission_id=mission_id, agreement_id=agreement_id)
        seeds.append(await escrow_event(rec, "held", actor=actor))
        rec["linked_agreements"] = link_agreements(rec)
    return {"escrow": rec, "seed": seeds[0], "seeds": seeds,
            "provenance_errors": [s for s in seeds if not s.get("doi")]}


async def release_to(escrow_id: str, agent_id: str, gross: float, *, source: str,
                     originator_id: str = "", actor: str = "operator") -> dict:
    """Pay ``gross`` out of the escrow to ``agent_id`` via the canonical payout.
    Raises EscrowError when it exceeds held funds / is frozen. The payout comes
    from the escrow: it is reserved first and un-reserved if the payout fails."""
    from app.routes.missions import _payout_seed
    res = state.escrow.reserve_release(escrow_id, agent_id=agent_id, gross=gross)
    rel = res["release"]
    try:
        escrow = state.escrow.get(escrow_id)
        result = state.economy.process_mission_payout(
            agent_id=agent_id, agent_metrics={}, gross_amount=gross,
            mission_id=escrow.get("mission_id") or escrow_id, originator_id=originator_id)
    except Exception:
        state.escrow.revert_release(escrow_id, rel["release_id"])
        raise
    if escrow["source"] == "stripe_checkout":
        # Card money: what the agent was just credited is not cashable until the chargeback window closes.
        credited = (result.get("agent_transaction") or {}).get("amount", 0.0)
        try:
            result["hold"] = state.economy.treasury.hold(agent_id, credited, reason="card_funded_payout", ref=escrow_id,
                                                      charged_at=escrow.get("charged_at"))
        except Exception:
            state.economy.treasury.debit(agent_id, credited, reason="hold_failed_reversal")
            state.escrow.revert_release(escrow_id, rel["release_id"])
            raise
    result["escrow_id"] = escrow_id
    result["seed"] = await _payout_seed(result, source=source)
    rec = state.escrow.get(escrow_id)
    result["escrow_seed"] = await escrow_event(rec, "released", actor=actor, agent_id=agent_id,
                                               gross=gross, release_id=rel["release_id"],
                                               net_to_agent=(result.get("fee_breakdown") or {}).get("net_to_agent"))
    result["escrow"] = rec
    from app.anchor_outbox import anchor_escrow_release
    anchor_escrow_release(escrow_id=escrow_id, agreement_id=rec.get("agreement_id"), actor=actor,
                          amount_usd=gross, release_id=rel["release_id"])
    return result


async def refund_to_poster(escrow_id: str, *, actor: str = "operator", reason: str = "") -> dict:
    """Return everything still held to the poster's treasury balance."""
    res = state.escrow.reserve_refund(escrow_id)
    rec, amount = res["escrow"], res["amount"]
    hold = None
    try:
        if rec["source"] == "stripe_checkout":      # card money coming back is held like any card-derived balance
            hold = state.economy.treasury.hold(rec["poster_id"], amount, reason="card_funded_refund", ref=escrow_id,
                                                charged_at=rec.get("charged_at"))
        txn = state.economy.treasury.credit(rec["poster_id"], amount, reason="escrow_refund",
                                            mission_id=rec.get("mission_id") or escrow_id)
    except Exception:
        if hold:
            state.economy.treasury.release_hold(hold["hold_id"])
        state.escrow.revert_refund(escrow_id, amount)
        raise
    seed = await escrow_event(rec, "refunded", actor=actor, to=rec["poster_id"], refunded=amount, reason=reason)
    return {"escrow": rec, "refunded": amount, "to": rec["poster_id"], "transaction": txn, "seed": seed}


def _poster_consented(a: dict, poster_id: str) -> bool:
    """The poster (or the operator) put this entrant on the work: it holds a slot the poster
    created, was force-assigned by the operator, or the poster accepted it. An open-mode entry
    onto the mission itself is accepted by the system with no one's say, so it is no claim on
    held funds (a swarm of those would dilute the payout, block the refund or freeze the escrow)."""
    if a["objects"].get("slot_id") or (a.get("governance") or {}).get("origin") == "force_assign":
        return True
    return any(r["transition"] == "accept" and poster_id in (r["actor"], r["acting_for"])
               for r in state.workentry.receipts(a["agreement_id"]))


def _worker_has_claim(mission_id: str, poster_id: str, agreements: list[dict] | None = None) -> bool:
    """An entrant has a claim on the held funds: a poster-consented Agreement on the mission is
    accepted, active, dormant or completed, or the poster itself terminated one (walking away from a
    worker is not a refund). Only the operator refunds past that. ``agreements`` narrows the check to those rows."""
    for a in (state.workentry.list_by_object("mission_id", mission_id) if agreements is None else agreements):
        if a["state"] in ("accepted", "active", "dormant", "completed"):
            if _poster_consented(a, poster_id):
                return True
        elif a["state"] == "terminated" and _poster_consented(a, poster_id):
            term = [r for r in state.workentry.receipts(a["agreement_id"]) if r["transition"] == "terminate"]
            if not term or any(poster_id in (r["actor"], r["acting_for"]) for r in term):
                return True
    return False


def _acting(request: Request) -> str | None:
    from app.routes.missions import _acting_agent_id
    return _acting_agent_id(request)


def _bad(e: EscrowError) -> JSONResponse:
    status = {"not_found": 404, "disputed": 409, "bad_state": 409}.get(e.code, 400)
    return JSONResponse({"error": e.message, "code": e.code}, status_code=status)


def _visible(rec: dict, acting: str | None) -> bool:
    """Operator sees all; an agent sees escrows it posted or is paid from."""
    return acting is None or acting == rec["poster_id"] or any(r["agent_id"] == acting for r in rec["releases"])


# ── routes ─────────────────────────────────────────────────────────────────

@router.post("/api/escrow/fund")
async def operator_fund(payload: dict, request: Request):
    """Operator funding (local runs / manual top-up). Body: mission_id, amount, poster_id?"""
    if not admin_key_matches(request, state.admin_key):
        return JSONResponse({"error": "Operator only"}, status_code=403)
    from app.routes.missions import _load_missions
    mission_id = (payload.get("mission_id") or "").strip() or None
    amount = float(payload.get("amount") or 0)
    if amount <= 0 or amount > MAX_ESCROW:
        return JSONResponse({"error": f"amount must be between 0 and {MAX_ESCROW:,.0f}"}, status_code=400)
    mission = next((m for m in _load_missions() if m.get("id") == mission_id), None) if mission_id else None
    if mission_id and mission is None:
        return JSONResponse({"error": "Mission not found", "mission_id": mission_id}, status_code=404)
    poster = (payload.get("poster_id") or (mission or {}).get("owner_agent_id") or "operator")
    if mission_id and state.escrow.active_for_mission(mission_id):
        return JSONResponse({"error": "Mission already has a live escrow"}, status_code=409)
    try:
        return await fund_escrow(poster_id=poster, amount=amount, source="operator", mission_id=mission_id,
                                 agreement_id=payload.get("agreement_id"))
    except EscrowError as e:
        return _bad(e)


@router.post("/api/escrow/checkout")
async def escrow_checkout(payload: dict, request: Request):
    """Poster starts a Stripe Checkout (test or live key, per config) to fund a mission escrow.
    Funds are recorded only by the signature-verified webhook, never by this call."""
    from app import kassa_payments
    from app.routes.missions import _load_missions
    acting = _acting(request)
    if acting is None:
        return JSONResponse({"error": "Poster agent credential required"}, status_code=403)
    mission_id = (payload.get("mission_id") or "").strip()
    mission = next((m for m in _load_missions() if m.get("id") == mission_id), None)
    if mission is None or mission.get("owner_agent_id") != acting:
        return JSONResponse({"error": "Mission not found", "mission_id": mission_id}, status_code=404)
    amount_cents = int(payload.get("amount_cents") or 0)
    if amount_cents <= 0 or amount_cents > MAX_ESCROW * 100:
        return JSONResponse({"error": "amount_cents out of range"}, status_code=400)
    if state.escrow.active_for_mission(mission_id):
        return JSONResponse({"error": "Mission already has a live escrow"}, status_code=409)
    if not kassa_payments.stripe_ready():
        return JSONResponse({"error": "Stripe not configured"}, status_code=503)
    proto = request.headers.get("x-forwarded-proto", "http")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost")
    base = f"{proto}://{host}"
    try:
        import stripe
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price_data": {"currency": "usd", "unit_amount": amount_cents,
                                        "product_data": {"name": f"Escrow for mission {mission_id}"}},
                         "quantity": 1}],
            mode="payment",
            success_url=f"{base}/connect/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base}/connect?cancelled=1",
            metadata={"type": "escrow_funding", "mission_id": mission_id, "poster_id": acting},
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": f"Stripe error: {exc}"}, status_code=503)
    state.audit.log("economy", "escrow_checkout_initiated",
                    {"mission_id": mission_id, "poster_id": acting, "amount_cents": amount_cents, "session_id": session.id})
    return {"checkout_url": session.url, "session_id": session.id}


@router.get("/api/escrow")
async def list_escrows(request: Request, mission_id: str | None = None):
    acting = _acting(request)
    rows = state.escrow.list(mission_id=mission_id)
    return {"escrows": [r for r in rows if _visible(r, acting)]}


@router.get("/api/escrow/{escrow_id}")
async def get_escrow(escrow_id: str, request: Request):
    acting = _acting(request)
    try:
        rec = state.escrow.get(escrow_id)
    except EscrowError as e:
        return _bad(e)
    if not _visible(rec, acting):
        return JSONResponse({"error": f"escrow {escrow_id} not found", "code": "not_found"}, status_code=404)
    return rec


@router.post("/api/escrow/{escrow_id}/release")
async def operator_release(escrow_id: str, payload: dict, request: Request):
    """Operator release to a named agent. Bounded by held funds; fee from config."""
    if not admin_key_matches(request, state.admin_key):
        return JSONResponse({"error": "Operator only"}, status_code=403)
    agent_id = (payload.get("agent_id") or "").strip()
    gross = float(payload.get("amount") or 0)
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    try:
        return await release_to(escrow_id, agent_id, gross, source="escrow_release",
                                originator_id=payload.get("originator_id") or "")
    except EscrowError as e:
        return _bad(e)


@router.post("/api/escrow/{escrow_id}/refund")
async def refund(escrow_id: str, request: Request):
    """Return held funds to the poster. The poster may do it while no Agreement on
    the mission is active; otherwise it is the operator's call."""
    acting = _acting(request)
    try:
        rec = state.escrow.get(escrow_id)
        if acting is not None:
            live = _worker_has_claim(rec.get("mission_id") or "", rec["poster_id"])
            if acting != rec["poster_id"] or live:
                return JSONResponse({"error": "Only the poster (with no active Agreement) or the operator may refund"},
                                    status_code=403)
        return await refund_to_poster(escrow_id, actor=acting or "operator")
    except EscrowError as e:
        return _bad(e)


@router.post("/api/escrow/{escrow_id}/dispute")
async def dispute(escrow_id: str, payload: dict, request: Request):
    """Freeze. The poster, a payee on the escrow, or the operator may dispute."""
    acting = _acting(request)
    try:
        rec = state.escrow.get(escrow_id)
        if not _visible(rec, acting):
            ags = state.workentry.list_by_object("mission_id", rec.get("mission_id") or "")
            # a party with a live stake: a withdrawn / rejected / terminated / pending entrant has none
            if not any(p["id"] == acting for a in ags if a["state"] in ("accepted", "active", "dormant")
                       and _poster_consented(a, rec["poster_id"]) for p in a["principals"]):
                return JSONResponse({"error": "Not a party to this escrow"}, status_code=403)
        rec = state.escrow.dispute(escrow_id, by=acting or "operator", reason=str(payload.get("reason") or ""))
    except EscrowError as e:
        return _bad(e)
    return {"escrow": rec, "seed": await escrow_event(rec, "disputed", actor=acting or "operator",
                                                      reason=str(payload.get("reason") or "")[:200])}


@router.post("/api/escrow/{escrow_id}/resolve")
async def resolve(escrow_id: str, payload: dict, request: Request):
    if not admin_key_matches(request, state.admin_key):
        return JSONResponse({"error": "Operator only"}, status_code=403)
    try:
        rec = state.escrow.resolve_dispute(escrow_id, by="operator", note=str(payload.get("note") or ""))
    except EscrowError as e:
        return _bad(e)
    return {"escrow": rec, "seed": await escrow_event(rec, "dispute_resolved", actor="operator")}
