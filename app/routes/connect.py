"""
connect.py — Stripe Connect, KA§§A Payments (MPP + Stripe), and Connect HTML pages.

Extracted from server.py create_app() monolith.
Covers:
  - KA§§A payment status, MPP pay/balance/credit, post payment initiation
  - Stripe Connect: accounts (V1 + V2 recipient), sessions, onboarding, status
  - Stripe Connect: products (create, list)
  - Stripe Connect: checkout (create, retrieve)
  - Stripe Connect: webhooks (V2 thin events)
  - Legacy Stripe webhook (V1 events)
  - Connect HTML pages (/connect, /connect/success)
"""
from __future__ import annotations

import math
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.auth import admin_key_matches, require_admin
from app.deps import state
from app.otel_setup import get_tracer as _get_tracer
from app.seeds import create_seed, create_seed_loud
from app import kassa_payments

_tracer = _get_tracer("civitae.payments")


def _tag_payment_span(**attrs) -> None:
    """Enrich the current request span with payment attributes."""
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        for k, v in attrs.items():
            span.set_attribute(f"civitae.payment.{k}", str(v)[:200])
    except Exception:
        pass

router = APIRouter(tags=["connect"])


# ── Money-path principal (P5 s2) ───────────────────────────────────────────
# Stripe accounts are bound to the agent that created them; products, checkout
# and cashout resolve price, fee and destination on the server from that
# binding. Nothing that moves money is taken from the request body.

def _connect_principal(request: Request) -> "dict | None":
    """Live agent record from the JWT (revocation-aware), or None."""
    from app.auth import agent_token_alive
    from app.jwt_config import extract_jwt
    claims = extract_jwt(request)
    if not claims:
        return None
    agent_id = claims.get("agent_id") or claims.get("sub", "")
    agent = next((r for r in state.runtime.registry if r.get("agent_id") == agent_id), None)
    return agent if agent and agent_token_alive(agent, claims) else None


def _is_operator(request: Request) -> bool:
    return admin_key_matches(request, state.admin_key)


def _seller_tier_inputs(agent: dict) -> dict:
    """The inputs economy.determine_tier reads, snapshotted from the agent's
    metrics + governance state. Stored on the binding; rates still come from config."""
    from app.metrics_io import load_metrics
    try:
        m = (load_metrics().get("agents", {}) or {}).get(agent.get("agent_id"), {}) or {}
    except Exception:  # noqa: BLE001 - metrics missing must not block linking an account
        m = {}
    gov = agent.get("governance")
    return {**m, "governance_active": bool(gov and gov != "none_(unrestricted)")}


def _bind_stripe_account(agent: dict, account_id: str) -> None:
    agent["stripe_account_id"] = account_id
    agent["stripe_tier_inputs"] = _seller_tier_inputs(agent)
    state.runtime.persist_registry()


def _bound_account(agent: dict | None) -> str:
    return (agent or {}).get("stripe_account_id", "") if agent else ""


def _seller_fee_percent(account_id: str) -> int:
    """Platform fee for a sale = the seller's tier rate from config.

    The tier comes from the inputs stored on the account binding when it was
    linked; an account with no bound agent (operator-created) gets the
    configured UNGOVERNED rate. Rates are read from config/economic_rates.json.
    """
    owner = next((r for r in state.runtime.registry
                  if account_id and r.get("stripe_account_id") == account_id), None)
    if owner is None or "stripe_tier_inputs" not in owner:
        return kassa_payments.DEFAULT_APP_FEE_PERCENT
    from app.economy import TIERS
    tier = state.economy.determine_tier(owner["stripe_tier_inputs"])
    return int(round(TIERS.get(tier, TIERS["ungoverned"])["fee_rate"] * 100))


class ConnectAccountPayload(BaseModel):
    display_name: str
    email: str
    country: str = "us"


class ConnectRecipientPayload(BaseModel):
    display_name: str
    email: str = ""
    country: str = "us"


class ConnectProductPayload(BaseModel):
    name: str
    description: str = ""
    price_cents: int = 0
    currency: str = "usd"
    connected_account_id: str = ""


# ── Helpers ────────────────────────────────────────────────────────────────

def _parse_reward_amount(reward: str) -> float:
    """Extract numeric amount from reward string like '$200 USDC', '$49', '20% rev-share'."""
    if not reward:
        return 0.0
    match = re.search(r'\$(\d+(?:\.\d+)?)', reward)
    if match:
        return float(match.group(1))
    return 0.0


# ── KA§§A Payments (Stripe Connect + MPP) ─────────────────────────────────

@router.get("/api/kassa/payment/status")
async def payment_rail_status() -> dict:
    """Check which payment rails are active."""
    return kassa_payments.payment_status()


@router.post("/api/mpp/pay")
async def mpp_pay(request: Request, payload: dict) -> dict:
    """Authorize an MPP challenge using agent treasury balance.

    Body: { "challenge_id": "ch_...", "agent_id": "agent-handle" }
    Requires JWT — caller must be the agent being debited.
    """
    # JWT verification — caller must match agent_id
    from app.jwt_config import require_jwt
    claims = require_jwt(request)

    challenge_id = (payload.get("challenge_id") or "").strip()
    agent_id = (payload.get("agent_id") or "").strip()
    if not challenge_id:
        raise HTTPException(status_code=400, detail="challenge_id required")
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id required")

    # Verify caller is the agent being debited
    caller_id = claims.get("sub", claims.get("agent_id", ""))
    if caller_id != agent_id:
        raise HTTPException(status_code=403, detail="Cannot debit another agent's treasury")
    from app.auth import agent_token_alive
    _principal = next((r for r in state.runtime.registry if r.get("agent_id") == caller_id), None)
    if not agent_token_alive(_principal, claims):
        raise HTTPException(status_code=401, detail="Credential revoked or principal inactive")

    result = kassa_payments.mpp_pay(challenge_id, agent_id, state.economy.treasury)
    if result.get("error"):
        raise HTTPException(status_code=402, detail=result["error"])

    state.audit.log("mpp", "credential_issued", {
        "challenge_id": challenge_id,
        "agent_id": agent_id,
        "resource": result.get("resource"),
        "amount": result.get("amount"),
    })
    return result


@router.get("/api/mpp/balance/{agent_id}")
async def mpp_balance(agent_id: str) -> dict:
    """Return an agent's spendable treasury balance."""
    balance = state.economy.treasury.balance(agent_id)
    history = state.economy.treasury.history(agent_id, limit=5)
    return {"agent_id": agent_id, "balance": balance, "currency": "usd", "recent": history}


@router.post("/api/mpp/credit")
async def mpp_credit(request: Request) -> dict:
    """Credit an agent's treasury balance (operator only).

    Body: { "agent_id": "...", "amount": 10.00, "reason": "..." }
    """
    require_admin(request, state.admin_key)

    gate = state.runtime.check_action("manual credit")
    if not gate["permitted"]:
        return JSONResponse({"error": gate["reason"], "governance": gate}, status_code=403)

    payload = await request.json()
    agent_id = (payload.get("agent_id") or "").strip()
    amount = float(payload.get("amount") or 0)
    reason = (payload.get("reason") or "manual credit").strip()
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id required")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be positive")

    result = state.economy.treasury.credit(agent_id, amount, reason)
    state.audit.log("mpp", "balance_credited", {"agent_id": agent_id, "amount": amount, "reason": reason})
    seed_doi = None
    seed_doi = await create_seed_loud(
        state.audit, "manual_credit",
        source_type="manual_credit",
        source_id=agent_id,
        creator_id="operator",
        creator_type="BI",
        seed_type="planted",
        metadata={"agent_id": agent_id, "amount": amount, "reason": reason},
    )
    return {**result, "seed_doi": seed_doi}


@router.post("/api/kassa/posts/{post_id}/pay")
async def initiate_payment(post_id: str, request: Request) -> dict:
    """Initiate payment for a bounty or service.

    Agents get MPP 402 challenge. Humans get Stripe Checkout URL.
    Query params: ?rail=auto|mpp|stripe, ?success_url=, ?cancel_url=
    """
    post = state.kassa.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post {post_id} not found")

    # Parse amount from reward field (e.g. "$200 USDC", "$49", "20% rev-share")
    reward = post.get("reward") or ""
    amount = _parse_reward_amount(reward)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Post has no fixed payment amount")

    # Detect if requester is an agent (has JWT) or human
    auth_header = request.headers.get("Authorization", "")
    is_agent = auth_header.startswith("Bearer ")

    # Check for MPP credential on retry
    if auth_header.startswith("MPP "):
        receipt = kassa_payments.mpp_verify_credential(auth_header)
        # The credential pays for the resource and amount it was issued for, nothing else.
        if receipt and (receipt.get("resource") != post_id or float(receipt.get("amount") or 0) < amount):
            raise HTTPException(status_code=402, detail="MPP credential was not issued for this post")
        if receipt:
            state.audit.log("kassa", "mpp_payment_verified", {
                "post_id": post_id, "amount": amount, "receipt": receipt,
            })
            await state.emit("kassa_payment", {"post_id": post_id, "rail": "mpp", "amount": amount})
            return {"paid": True, "post_id": post_id, "amount": amount, "rail": "mpp", "receipt": receipt}
        raise HTTPException(status_code=402, detail="Invalid MPP credential")

    # Determine rail
    params = request.query_params
    rail = params.get("rail", "auto")
    success_url = params.get("success_url", "")
    cancel_url = params.get("cancel_url", "")

    _tag_payment_span(action="initiate", post_id=post_id, amount_usd=amount,
                      rail=rail, is_agent=is_agent)

    try:
        result = kassa_payments.create_payment(
            post_id=post_id,
            amount_usd=amount,
            description=f"KA§§A: {post.get('title', post_id)}",
            rail=rail,
            agent_request=is_agent,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"tab": post.get("tab", ""), "post_id": post_id},
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Payment error: {e}")

    if result.get("status") == 402:
        # MPP challenge — return as HTTP 402
        _tag_payment_span(rail_resolved="mpp", status="challenge_issued")
        state.audit.log("kassa", "mpp_challenge_issued", {"post_id": post_id, "amount": amount})
        return JSONResponse(result, status_code=402)

    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])

    state.audit.log("kassa", "payment_initiated", {
        "post_id": post_id, "amount": amount, "rail": result.get("rail"),
    })
    seed_doi = None
    seed_doi = await create_seed_loud(
        state.audit, "payment_initiated",
        source_type="payment_initiated",
        source_id=post_id,
        creator_id="operator",
        creator_type="BI",
        seed_type="planted",
        metadata={"post_id": post_id, "amount": amount, "rail": result.get("rail")},
    )
    # Frontend expects checkout_url — alias from Stripe's url field
    if result.get("url") and "checkout_url" not in result:
        result["checkout_url"] = result["url"]
    return {**result, "seed_doi": seed_doi}


# ── Stripe Connect: Connected Accounts ─────────────────────────────────────

@router.post("/api/connect/accounts")
async def create_connect_account(payload: ConnectAccountPayload, request: Request) -> dict:
    """Create a Stripe connected account for an agent or operator.

    Body: { "display_name": "...", "email": "...", "country": "us" }
    Requires an agent JWT (the account is bound to that agent) or the admin key.
    """
    agent = _connect_principal(request)
    if agent is None and not _is_operator(request):
        raise HTTPException(status_code=401, detail="Agent JWT required")
    name = payload.display_name.strip()
    email = payload.email.strip()
    if not name or not email:
        raise HTTPException(status_code=400, detail="display_name and email required")

    result = kassa_payments.create_connected_account(
        display_name=name,
        email=email,
        country=payload.country,
    )
    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])

    if agent is not None:
        _bind_stripe_account(agent, result["account_id"])
    state.audit.log("kassa", "connect_account_created", {
        "account_id": result["account_id"], "name": name,
        "bound_agent": (agent or {}).get("agent_id"),
    })
    return result


@router.post("/api/connect/v2/accounts")
async def create_recipient_account(payload: ConnectRecipientPayload, request: Request) -> dict:
    """Create a Stripe V2 Recipient account for agent payouts.

    Body: { "display_name": "...", "email": "...", "country": "us" }

    V2 Recipient accounts are machine-native — for autonomous agents receiving
    mission/bounty payouts. Falls back to V1 Express if V2 API not enabled.
    """
    agent = _connect_principal(request)
    if agent is None and not _is_operator(request):
        raise HTTPException(status_code=401, detail="Agent JWT required")
    name = payload.display_name.strip()
    email = payload.email.strip()
    if not name:
        raise HTTPException(status_code=400, detail="display_name required")

    result = kassa_payments.create_recipient_account(
        display_name=name,
        email=email,
        country=payload.country,
    )
    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])

    if agent is not None:
        _bind_stripe_account(agent, result["account_id"])
    state.audit.log("kassa", "recipient_account_created", {
        "bound_agent": (agent or {}).get("agent_id"),
        "account_id": result["account_id"],
        "type": result.get("type", "recipient"),
        "name": name,
    })
    return result


@router.post("/api/connect/accounts/{account_id}/session")
async def create_connect_session(account_id: str) -> dict:
    """Create a Stripe Account Session for embedded Connect onboarding.

    Returns a client_secret for use with Stripe.js loadConnectAndInitialize().
    Enables embedded (non-redirect) onboarding for both V1 and V2 accounts.
    """
    result = kassa_payments.create_account_session(account_id)
    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])
    return result


@router.post("/api/connect/accounts/{account_id}/onboard")
async def onboard_connect_account(account_id: str, request: Request) -> dict:
    """Generate an onboarding link for a connected account (V1 hosted redirect)."""
    proto = request.headers.get("x-forwarded-proto", "http")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost")
    base = f"{proto}://{host}"
    result = kassa_payments.create_account_link(
        account_id=account_id,
        return_url=f"{base}/connect?accountId={account_id}",
        refresh_url=f"{base}/connect?refresh=1&accountId={account_id}",
    )
    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])
    return result


@router.get("/api/connect/accounts/{account_id}/status")
async def connect_account_status(account_id: str) -> dict:
    """Check onboarding and capability status of a connected account."""
    result = kassa_payments.get_account_status(account_id)
    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])
    return result


# ── Stripe Connect: Products ───────────────────────────────────────────────

@router.post("/api/connect/products")
async def create_connect_product(payload: ConnectProductPayload, request: Request) -> dict:
    """Create a product at the platform level, mapped to a connected account.

    Body: { "name": "...", "description": "...", "price_cents": 4900,
            "currency": "usd", "connected_account_id": "acct_..." }
    """
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    if payload.price_cents <= 0:
        raise HTTPException(status_code=400, detail="price_cents must be positive")
    if not _is_operator(request):
        agent = _connect_principal(request)
        if agent is None:
            raise HTTPException(status_code=401, detail="Agent JWT required")
        bound = _bound_account(agent)
        if not bound:
            raise HTTPException(status_code=400, detail="Link a Stripe account first (/api/connect/accounts)")
        if payload.connected_account_id and payload.connected_account_id != bound:
            raise HTTPException(status_code=403, detail="connected_account_id is not your linked account")
        payload.connected_account_id = bound
    elif not payload.connected_account_id:
        raise HTTPException(status_code=400, detail="connected_account_id required")

    result = kassa_payments.create_product(
        name=name,
        description=payload.description,
        price_cents=payload.price_cents,
        currency=payload.currency,
        connected_account_id=payload.connected_account_id,
    )
    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])

    state.audit.log("kassa", "product_created", {
        "product_id": result["product_id"], "name": name,
    })
    return result


@router.get("/api/connect/products")
async def list_connect_products() -> list:
    """List all products on the platform (storefront data)."""
    return kassa_payments.list_products()


# ── Stripe Connect: Checkout ───────────────────────────────────────────────

# Metadata keys the platform webhook acts on (escrow funding, fee-credit packs, bounty posts).
# A buyer-supplied value for any of them would let a $1 product purchase mint escrow or fee credits.
_RESERVED_METADATA = frozenset({"type", "poster_id", "mission_id", "agent_id", "pack_name",
                                "price_cents", "post_id", "product_id"})


def _buyer_metadata(raw) -> dict:
    return {str(k): v for k, v in (raw or {}).items()
            if isinstance(raw, dict) and str(k) not in _RESERVED_METADATA}


@router.post("/api/connect/checkout")
async def create_connect_checkout(payload: dict, request: Request) -> dict:
    """Create a checkout session with destination charge.

    Body: { "product_id": "prod_..." }
    Price, destination account and platform fee come from the product record
    and config, never from the body (P5 s2). Client-sent price_cents,
    connected_account_id and app_fee_percent are ignored.
    """
    proto = request.headers.get("x-forwarded-proto", "http")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost")
    base = f"{proto}://{host}"
    product_id = (payload.get("product_id") or "").strip()
    if not product_id:
        raise HTTPException(status_code=400, detail="product_id required")
    product = next((p for p in kassa_payments.list_products() if p.get("product_id") == product_id), None)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    product_name = product.get("name") or "KA§§A Purchase"
    price_cents = int(product.get("price_cents") or 0)
    account_id = product.get("connected_account_id", "")

    if price_cents <= 0:
        raise HTTPException(status_code=400, detail="Product has no price")
    if not account_id:
        raise HTTPException(status_code=400, detail="Product has no seller account")
    app_fee_percent = _seller_fee_percent(account_id)

    result = kassa_payments.create_checkout_session(
        product_name=product_name,
        price_cents=price_cents,
        connected_account_id=account_id,
        success_url=f"{base}/connect/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base}/connect?cancelled=1",
        app_fee_percent=app_fee_percent,
        metadata={**_buyer_metadata(payload.get("metadata")), "product_id": product_id},
    )
    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])

    state.audit.log("kassa", "checkout_created", {
        "session_id": result["session_id"],
        "account_id": account_id,
        "product_id": product_id,
        "amount": price_cents,
        "app_fee_percent": app_fee_percent,
    })
    return result


@router.get("/api/connect/checkout/{session_id}")
async def get_checkout_details(session_id: str) -> dict:
    """Retrieve details of a checkout session (for success page)."""
    return kassa_payments.retrieve_checkout_session(session_id)


# ── Stripe Connect: Webhooks (Thin Events for V2) ─────────────────────────

@router.post("/api/connect/webhooks")
async def connect_webhook(request: Request) -> dict:
    """Handle V2 thin events for connected account updates.

    Listens for:
    - v2.core.account[requirements].updated
    - v2.core.account[.recipient].capability_status_updated

    Setup:
    1. Dashboard -> Developers -> Webhooks -> + Add destination
    2. Events from: Connected accounts
    3. Advanced -> Payload style: Thin
    4. Select v2.account events

    Local testing:
      stripe listen --thin-events \\
        'v2.core.account[requirements].updated,v2.core.account[.recipient].capability_status_updated' \\
        --forward-thin-to http://localhost:8300/api/connect/webhooks
    """
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    event = kassa_payments.parse_thin_event(payload, sig)
    if not event:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event.get("type", "")

    seed_doi = None
    if "requirements" in event_type:
        # Account requirements changed — may need to collect updated info
        state.audit.log("kassa", "connect_requirements_updated", {
            "event_id": event["id"],
            "type": event_type,
        })
        seed_doi = await create_seed_loud(
            state.audit, "connect_event",
            source_type="connect_event",
            source_id=event["id"],
            creator_id="stripe",
            creator_type="BI",
            seed_type="planted",
            metadata={"event_id": event["id"], "type": event_type},
        )

    elif "capability_status" in event_type:
        # Capability status changed — check if account is now active
        state.audit.log("kassa", "connect_capability_updated", {
            "event_id": event["id"],
            "type": event_type,
        })
        seed_doi = await create_seed_loud(
            state.audit, "connect_event",
            source_type="connect_event",
            source_id=event["id"],
            creator_id="stripe",
            creator_type="BI",
            seed_type="planted",
            metadata={"event_id": event["id"], "type": event_type},
        )

    return {"received": True, "seed_doi": seed_doi}


# ── Legacy Stripe Webhook (V1 events) ─────────────────────────────────────

@router.post("/api/kassa/webhooks/stripe")
async def stripe_webhook_v1(request: Request) -> dict:
    """Handle standard Stripe webhook events (checkout completed, etc.)."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    if not kassa_payments.stripe_ready():
        raise HTTPException(status_code=503, detail="Stripe not configured")

    try:
        import stripe
        event = stripe.Webhook.construct_event(
            payload, sig, kassa_payments.STRIPE_WEBHOOK_SECRET,
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = getattr(event, "type", "") or event["type"]
    event_data = getattr(event, "data", None)
    data = getattr(event_data, "object", None) if event_data is not None else None
    if data is None and isinstance(event, dict):
        data = event.get("data", {}).get("object", {})
    if data is None:
        data = {}

    if event_type == "checkout.session.completed":
        metadata = getattr(data, "metadata", None)
        if metadata is None and isinstance(data, dict):
            metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        post_id = metadata.get("post_id", "")
        _stripe_amount = ((getattr(data, "amount_total", 0) if not isinstance(data, dict) else data.get("amount_total", 0)) or 0) / 100
        _session_id = getattr(data, "id", None) if not isinstance(data, dict) else data.get("id")
        _tag_payment_span(action="webhook_completed", post_id=post_id,
                          amount_usd=_stripe_amount, session_id=_session_id or "",
                          payment_type=metadata.get("type", "bounty"))

        # Escrow funding (P5): the signature-verified webhook is what puts money in escrow.
        escrow_funded = None
        if metadata.get("type") == "escrow_funding":
            _paid = (getattr(data, "payment_status", None) if not isinstance(data, dict)
                     else data.get("payment_status"))
            if _paid not in (None, "paid"):
                state.audit.log("economy", "escrow_funding_unpaid", {"session_id": _session_id, "status": _paid})
            else:
                from app.routes.escrow import fund_escrow
                from app.escrow import EscrowError
                try:
                    escrow_funded = await fund_escrow(
                        poster_id=metadata.get("poster_id", ""), amount=_stripe_amount, source="stripe_checkout",
                        mission_id=metadata.get("mission_id") or None, stripe_session_id=_session_id, actor="stripe")
                except EscrowError as exc:
                    state.audit.log("economy", "escrow_funding_failed", {"session_id": _session_id, "error": exc.message})

        # Fee credit pack purchase — credit the agent's fee credit balance
        if metadata.get("type") == "escrow_funding":
            pass
        elif metadata.get("type") == "fee_credit_pack":
            pack_name = metadata.get("pack_name", "Unknown")
            agent_id = metadata.get("agent_id", "")
            # Coverage amount = what the pack covers (from frontend PACKS data)
            # We store price_cents in metadata; coverage is derived from pack config server-side
            # For now credit coverage = 2× price (Standard pack logic) — exact amounts TBD
            PACK_COVERAGE = {"Starter": 50, "Standard": 100, "Builder": 225, "Founding": 600, "Cycle Pack": 1250}
            coverage = PACK_COVERAGE.get(pack_name, _stripe_amount * 2)
            if agent_id:
                state.economy.fee_credits.credit(
                    agent_id=agent_id,
                    amount=coverage,
                    pack_name=pack_name,
                    stripe_session_id=_session_id or "",
                )
            state.audit.log("economy", "fee_credit_pack_purchased", {
                "agent_id": agent_id,
                "pack_name": pack_name,
                "paid_usd": _stripe_amount,
                "credits_added": coverage,
                "session_id": _session_id,
            })
        else:
            state.audit.log("kassa", "stripe_payment_completed", {
                "post_id": post_id,
                "amount": _stripe_amount,
                "session_id": _session_id,
            })
            await state.emit("kassa_payment", {
                "post_id": post_id,
                "rail": "stripe_connect",
                "amount": _stripe_amount,
            })
        seed_doi = None
        seed_doi = await create_seed_loud(
            state.audit, "payment_completed",
            source_type="payment_completed",
            source_id=_session_id or post_id,
            creator_id="stripe",
            creator_type="BI",
            seed_type="planted",
            metadata={"post_id": post_id, "amount": _stripe_amount, "session_id": _session_id, "rail": "stripe"},
        )

    out = {"received": True, "seed_doi": seed_doi}
    if event_type == "checkout.session.completed" and escrow_funded:
        out["escrow_id"] = escrow_funded["escrow"]["escrow_id"]
    return out


# ── Fee Credit Pack Checkout ───────────────────────────────────────────────

@router.post("/api/fee-credits/checkout")
async def fee_credits_checkout(payload: dict, request: Request) -> dict:
    """Create a direct Stripe checkout session for a fee credit pack purchase.

    Body: { "pack_name": "Standard", "price_cents": 5000 }
    Returns: { "checkout_url": "https://checkout.stripe.com/..." }
    """
    if not kassa_payments.stripe_ready():
        raise HTTPException(status_code=503, detail="Stripe not configured")

    pack_name = (payload.get("pack_name") or "").strip()
    price_cents = int(payload.get("price_cents") or 0)
    if not pack_name:
        raise HTTPException(status_code=400, detail="pack_name required")
    if price_cents <= 0:
        raise HTTPException(status_code=400, detail="price_cents must be positive")

    proto = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "signomy.xyz")
    base = f"{proto}://{host}"

    agent_id = (payload.get("agent_id") or "").strip()

    try:
        import stripe
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": price_cents,
                    "product_data": {
                        "name": f"CIVITAE Fee Credit Pack — {pack_name}",
                        "description": "Prepaid governance fee credits. Never expire. Apply automatically at mission settlement.",
                    },
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{base}/fee-credits?success=1&pack={pack_name}",
            cancel_url=f"{base}/fee-credits?cancelled=1",
            metadata={
                "type": "fee_credit_pack",
                "pack_name": pack_name,
                "price_cents": str(price_cents),
                "agent_id": agent_id,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Stripe error: {e}")

    state.audit.log("economy", "fee_credit_checkout_initiated", {
        "pack_name": pack_name,
        "price_cents": price_cents,
        "session_id": session.id,
    })
    return {"checkout_url": session.url, "session_id": session.id}


@router.get("/api/fee-credits/balance/{agent_id}")
async def fee_credits_balance(agent_id: str) -> dict:
    """Return an agent's current fee credit balance and recent transactions."""
    balance = state.economy.fee_credits.balance(agent_id)
    history = state.economy.fee_credits.history(agent_id, limit=10)
    return {"agent_id": agent_id, "balance": balance, "currency": "usd_coverage", "recent": history}


# ── Connect Pages ──────────────────────────────────────────────────────────

@router.get("/connect")
async def connect_page() -> FileResponse:
    target = state.frontend_dir / "connect.html"
    if target.exists():
        return FileResponse(target)
    return JSONResponse({"detail": "Connect page not yet built"}, status_code=404)


@router.get("/connect/success")
async def connect_success_page() -> FileResponse:
    target = state.frontend_dir / "connect-success.html"
    if target.exists():
        return FileResponse(target)
    return JSONResponse({"detail": "Success page not yet built"}, status_code=404)


# ── Cash Out: Treasury → Stripe Connected Account ────────────────────────────

@router.post("/api/connect/cashout")
async def cashout(request: Request):
    """Transfer earned funds from agent treasury to their Stripe connected account.

    Requires JWT auth. Agent must have:
    1. A positive treasury balance
    2. A linked Stripe connected account (onboarding complete)

    The flow: treasury.debit(agent) → stripe.Transfer → seed created.
    """
    from app.jwt_config import extract_jwt

    payload = extract_jwt(request)
    if not payload:
        return JSONResponse({"error": "JWT required"}, status_code=401)
    agent_id = payload.get("agent_id") or payload.get("sub", "")
    from app.auth import agent_token_alive
    _principal = next((r for r in state.runtime.registry if r.get("agent_id") == agent_id), None)
    if not agent_token_alive(_principal, payload):
        return JSONResponse({"error": "Credential revoked or principal inactive"}, status_code=401)
    if not agent_id:
        return JSONResponse({"error": "No agent_id in token"}, status_code=401)

    body = await request.json()
    amount_usd = float(body.get("amount", 0))
    connected_account_id = _bound_account(_principal)
    requested_account = (body.get("connected_account_id") or "").strip()

    if not math.isfinite(amount_usd) or amount_usd <= 0:
        return JSONResponse({"error": "Amount must be positive"}, status_code=400)
    if not connected_account_id:
        return JSONResponse({"error": "No Stripe account linked to this agent — create one via /api/connect/accounts"}, status_code=400)
    if requested_account and requested_account != connected_account_id:
        return JSONResponse({"error": "connected_account_id is not this agent's linked account"}, status_code=403)

    # Check balance
    balance = state.economy.treasury.balance(agent_id)
    if amount_usd > balance:
        return JSONResponse({
            "error": "Insufficient balance",
            "balance": balance,
            "requested": amount_usd,
        }, status_code=400)

    # Verify connected account is onboarded
    from app import kassa_payments
    acct_status = kassa_payments.get_account_status(connected_account_id)
    if acct_status.get("error"):
        return JSONResponse({"error": "Cannot verify connected account", "detail": acct_status["error"]}, status_code=400)
    if not acct_status.get("charges_enabled"):
        return JSONResponse({"error": "Connected account onboarding incomplete — complete Stripe setup first"}, status_code=400)

    # Reserve first (P5 s2): debit before the transfer so two concurrent
    # cashouts cannot both pass the balance check; refund if Stripe fails.
    reserved = state.economy.treasury.debit(agent_id, amount_usd, reason="cashout_reserved")
    if reserved.get("error"):
        return JSONResponse({"error": "Insufficient balance", "balance": reserved.get("balance"),
                             "requested": amount_usd}, status_code=400)
    amount_cents = int(round(amount_usd * 100))
    try:
        result = kassa_payments.create_transfer(
        amount_cents=amount_cents,
        connected_account_id=connected_account_id,
            description=f"SIGNOMY payout — {agent_id}",
            metadata={"agent_id": agent_id, "source": "treasury_cashout"},
        )
    except Exception as exc:
        result = {"error": str(exc)[:200]}
    if result.get("error"):
        state.economy.treasury.credit(agent_id, amount_usd, reason="cashout_refund")
        return JSONResponse({"error": "Transfer failed", "detail": result["error"]}, status_code=502)

    state.audit.log("economy", "cashout", {
        "agent_id": agent_id, "amount_usd": amount_usd,
        "connected_account_id": connected_account_id, "transfer_id": result["transfer_id"],
    })
    # Seed for audit trail. The money has moved: a Seed failure is loud, never a 500.
    seed_doi = None
    try:
        seed = await create_seed(
            source_type="cashout",
            source_id=result["transfer_id"],
            creator_id=agent_id,
            creator_type="AAI",
            seed_type="grown",
            metadata={
                "amount_usd": amount_usd,
                "connected_account_id": connected_account_id,
                "transfer_id": result["transfer_id"],
            },
        )
        seed_doi = (seed or {}).get("doi")
    except Exception as exc:
        state.audit.log("economy", "provenance_failed", {
            "action": "cashout", "transfer_id": result["transfer_id"], "error": str(exc)[:200]})

    from app.anchor_outbox import anchor_cashout
    anchor_cashout(agent_id=agent_id, amount_usd=amount_usd, transfer_id=result["transfer_id"], seed_doi=seed_doi)
    return JSONResponse({
        "ok": True,
        "seed_doi": seed_doi,
        "provenance_error": seed_doi is None,
        "transfer_id": result["transfer_id"],
        "amount_usd": amount_usd,
        "remaining_balance": state.economy.treasury.balance(agent_id),
    })
