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

import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from app.deps import state
from app.seeds import create_seed
from app import kassa_payments

router = APIRouter(tags=["connect"])


# ── Auth helper (fail-closed) ──────────────────────────────────────────────

def _require_admin(request: Request):
    """Fail-closed admin check — rejects if key is unset OR mismatched."""
    if not state.admin_key:
        raise HTTPException(403, "CIVITAE_ADMIN_KEY not configured")
    if request.headers.get("X-Admin-Key") != state.admin_key:
        raise HTTPException(403, "Admin key required")


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
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="JWT required — include Authorization: Bearer <token>")
    import jwt as pyjwt
    from app.jwt_config import get_jwt_secret
    try:
        claims = pyjwt.decode(auth[7:], get_jwt_secret(), algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired JWT")

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
    _require_admin(request)

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
    try:
        seed_result = await create_seed(
            source_type="manual_credit",
            source_id=agent_id,
            creator_id="operator",
            creator_type="BI",
            seed_type="planted",
            metadata={"agent_id": agent_id, "amount": amount, "reason": reason},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
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
        state.audit.log("kassa", "mpp_challenge_issued", {"post_id": post_id, "amount": amount})
        return JSONResponse(result, status_code=402)

    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])

    state.audit.log("kassa", "payment_initiated", {
        "post_id": post_id, "amount": amount, "rail": result.get("rail"),
    })
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="payment_initiated",
            source_id=post_id,
            creator_id="operator",
            creator_type="BI",
            seed_type="planted",
            metadata={"post_id": post_id, "amount": amount, "rail": result.get("rail")},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    # Frontend expects checkout_url — alias from Stripe's url field
    if result.get("url") and "checkout_url" not in result:
        result["checkout_url"] = result["url"]
    return {**result, "seed_doi": seed_doi}


# ── Stripe Connect: Connected Accounts ─────────────────────────────────────

@router.post("/api/connect/accounts")
async def create_connect_account(payload: dict) -> dict:
    """Create a Stripe connected account for an agent or operator.

    Body: { "display_name": "...", "email": "...", "country": "us" }
    """
    name = (payload.get("display_name") or "").strip()
    email = (payload.get("email") or "").strip()
    if not name or not email:
        raise HTTPException(status_code=400, detail="display_name and email required")

    result = kassa_payments.create_connected_account(
        display_name=name,
        email=email,
        country=payload.get("country", "us"),
    )
    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])

    state.audit.log("kassa", "connect_account_created", {
        "account_id": result["account_id"], "name": name,
    })
    return result


@router.post("/api/connect/v2/accounts")
async def create_recipient_account(payload: dict) -> dict:
    """Create a Stripe V2 Recipient account for agent payouts.

    Body: { "display_name": "...", "email": "...", "country": "us" }

    V2 Recipient accounts are machine-native — for autonomous agents receiving
    mission/bounty payouts. Falls back to V1 Express if V2 API not enabled.
    """
    name = (payload.get("display_name") or "").strip()
    email = (payload.get("email") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="display_name required")

    result = kassa_payments.create_recipient_account(
        display_name=name,
        email=email,
        country=payload.get("country", "us"),
    )
    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])

    state.audit.log("kassa", "recipient_account_created", {
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
async def create_connect_product(payload: dict) -> dict:
    """Create a product at the platform level, mapped to a connected account.

    Body: { "name": "...", "description": "...", "price_cents": 4900,
            "currency": "usd", "connected_account_id": "acct_..." }
    """
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name required")

    result = kassa_payments.create_product(
        name=name,
        description=payload.get("description", ""),
        price_cents=int(payload.get("price_cents", 0)),
        currency=payload.get("currency", "usd"),
        connected_account_id=payload.get("connected_account_id", ""),
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

@router.post("/api/connect/checkout")
async def create_connect_checkout(payload: dict, request: Request) -> dict:
    """Create a checkout session with destination charge.

    Body: { "product_id": "...", "product_name": "...", "price_cents": 4900,
            "connected_account_id": "acct_...", "app_fee_percent": 5 }
    """
    proto = request.headers.get("x-forwarded-proto", "http")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost")
    base = f"{proto}://{host}"
    product_name = payload.get("product_name", "KA§§A Purchase")
    price_cents = int(payload.get("price_cents", 0))
    account_id = payload.get("connected_account_id", "")

    if price_cents <= 0:
        raise HTTPException(status_code=400, detail="price_cents must be positive")
    if not account_id:
        raise HTTPException(status_code=400, detail="connected_account_id required")

    result = kassa_payments.create_checkout_session(
        product_name=product_name,
        price_cents=price_cents,
        connected_account_id=account_id,
        success_url=f"{base}/connect/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base}/connect?cancelled=1",
        app_fee_percent=int(payload.get("app_fee_percent", 5)),
        metadata=payload.get("metadata", {}),
    )
    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])

    state.audit.log("kassa", "checkout_created", {
        "session_id": result["session_id"],
        "account_id": account_id,
        "amount": price_cents,
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
        try:
            seed_result = await create_seed(
                source_type="connect_event",
                source_id=event["id"],
                creator_id="stripe",
                creator_type="BI",
                seed_type="planted",
                metadata={"event_id": event["id"], "type": event_type},
            )
            seed_doi = seed_result.get("doi") if seed_result else None
        except Exception:
            pass

    elif "capability_status" in event_type:
        # Capability status changed — check if account is now active
        state.audit.log("kassa", "connect_capability_updated", {
            "event_id": event["id"],
            "type": event_type,
        })
        try:
            seed_result = await create_seed(
                source_type="connect_event",
                source_id=event["id"],
                creator_id="stripe",
                creator_type="BI",
                seed_type="planted",
                metadata={"event_id": event["id"], "type": event_type},
            )
            seed_doi = seed_result.get("doi") if seed_result else None
        except Exception:
            pass

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

        # Fee credit pack purchase — credit the agent's fee credit balance
        if metadata.get("type") == "fee_credit_pack":
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
        try:
            seed_result = await create_seed(
                source_type="payment_completed",
                source_id=_session_id or post_id,
                creator_id="stripe",
                creator_type="BI",
                seed_type="planted",
                metadata={"post_id": post_id, "amount": _stripe_amount, "session_id": _session_id, "rail": "stripe"},
            )
            seed_doi = seed_result.get("doi") if seed_result else None
        except Exception:
            pass

    return {"received": True, "seed_doi": seed_doi}


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
    import jwt as pyjwt
    from app.seeds import create_seed

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return JSONResponse({"error": "JWT required"}, status_code=401)
    token = auth[7:]
    try:
        payload = pyjwt.decode(token, state.jwt_secret, algorithms=["HS256"])
        agent_id = payload.get("agent_id") or payload.get("sub", "")
    except Exception:
        return JSONResponse({"error": "Invalid token"}, status_code=401)

    if not agent_id:
        return JSONResponse({"error": "No agent_id in token"}, status_code=401)

    body = await request.json()
    amount_usd = float(body.get("amount", 0))
    connected_account_id = (body.get("connected_account_id") or "").strip()

    if amount_usd <= 0:
        return JSONResponse({"error": "Amount must be positive"}, status_code=400)
    if not connected_account_id:
        return JSONResponse({"error": "connected_account_id required"}, status_code=400)

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

    # Execute transfer
    amount_cents = int(round(amount_usd * 100))
    result = kassa_payments.create_transfer(
        amount_cents=amount_cents,
        connected_account_id=connected_account_id,
        description=f"SIGNOMY payout — {agent_id}",
        metadata={"agent_id": agent_id, "source": "treasury_cashout"},
    )

    if result.get("error"):
        return JSONResponse({"error": "Transfer failed", "detail": result["error"]}, status_code=502)

    # Debit treasury only after successful transfer
    state.economy.treasury.debit(agent_id, amount_usd, reason="cashout", chain=f"stripe:{result['transfer_id']}")

    # Seed for audit trail
    await create_seed(
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

    return JSONResponse({
        "ok": True,
        "transfer_id": result["transfer_id"],
        "amount_usd": amount_usd,
        "remaining_balance": state.economy.treasury.balance(agent_id),
    })
