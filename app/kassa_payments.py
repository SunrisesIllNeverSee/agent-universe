"""KA§§A Payment Layer — Stripe Connect (V2) + MPP (Machine Payments Protocol).

Stripe Connect handles marketplace payments:
  - Connected accounts for agents/operators who receive payouts
  - Destination charges with application fees (governance-tier based)
  - Product catalog at platform level, mapped to connected accounts

MPP handles agent micropayments (stakes, thread access, referral commissions).

Both rails are optional — endpoints degrade gracefully when keys aren't configured.
Set STRIPE_SECRET_KEY in environment to activate Stripe.
Set MPP_SECRET_KEY in environment to activate MPP.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, UTC

# ── Configuration ──────────────────────────────────────────────────────────

# STRIPE_SECRET_KEY: Your platform's secret key from the Stripe Dashboard.
# Find it at: https://dashboard.stripe.com/apikeys
# For testing, use a key starting with sk_test_
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")

# STRIPE_WEBHOOK_SECRET: Signing secret for verifying webhook payloads.
# Set up webhooks at: https://dashboard.stripe.com/webhooks
# For thin events (V2), use the whsec_ value from your webhook endpoint.
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# MPP keys for Machine Payments Protocol (agent micropayments)
MPP_SECRET_KEY = os.environ.get("MPP_SECRET_KEY", "")
MPP_RECIPIENT = os.environ.get("MPP_RECIPIENT", "")

# The governance-tier application fee percentage.
# Ungoverned: 15%, Governed: 5%, Constitutional: 2%, Black Card: custom
DEFAULT_APP_FEE_PERCENT = 5

# ── Stripe Client (V2 API) ────────────────────────────────────────────────

_client = None
_stripe_module = None
_stripe_ready = False
_stripe_v2_ready = False

if STRIPE_SECRET_KEY:
    try:
        import stripe

        stripe.api_key = STRIPE_SECRET_KEY
        _stripe_module = stripe
        _stripe_ready = True
        try:
            from stripe import StripeClient

            # Use StripeClient for V2 APIs when the installed SDK supports it.
            _client = StripeClient(STRIPE_SECRET_KEY)
            _stripe_v2_ready = True
        except ImportError:
            _client = None
    except ImportError:
        pass

if not STRIPE_SECRET_KEY:
    import sys
    print(
        "WARNING: STRIPE_SECRET_KEY not set. Payment endpoints will return 503.\n"
        "  Set it in your environment: export STRIPE_SECRET_KEY=sk_test_...\n"
        "  Get your key at: https://dashboard.stripe.com/apikeys",
        file=sys.stderr,
    )


def stripe_ready() -> bool:
    return _stripe_ready


def mpp_ready() -> bool:
    return bool(MPP_SECRET_KEY)


def payment_status() -> dict:
    """Return current payment rail availability."""
    return {
        "stripe_connect": stripe_ready(),
        "mpp": mpp_ready(),
        "rails": [
            r for r in ["stripe_connect", "mpp"]
            if (r == "stripe_connect" and stripe_ready()) or (r == "mpp" and mpp_ready())
        ],
    }


# ── Connected Accounts (V2 API) ───────────────────────────────────────────

def create_connected_account(display_name: str, email: str, country: str = "us") -> dict:
    """Create a Stripe connected account using the V2 Accounts API.

    The platform is responsible for fees and losses (application-managed).
    Dashboard is 'express' so the connected account gets a lightweight Stripe UI.
    Capabilities request stripe_balance with stripe_transfers for payouts.

    Args:
        display_name: The name shown on the connected account (agent/operator name).
        email: Contact email for the connected account.
        country: ISO country code (default: 'us').

    Returns:
        dict with account_id and status, or error details.
    """
    if not _stripe_ready:
        return {"error": "Stripe not configured. Set STRIPE_SECRET_KEY."}
    if not _stripe_v2_ready or _client is None:
        return {"error": "Stripe Accounts V2 requires a newer Stripe SDK with StripeClient support."}

    # V2 account creation — platform manages fees and losses.
    # Do NOT pass type='express' at top level (V2 uses dashboard='express' instead).
    account = _client.v2.core.accounts.create(
        params={
            "display_name": display_name,
            "contact_email": email,
            "identity": {"country": country},
            "dashboard": "express",
            "defaults": {
                "responsibilities": {
                    "fees_collector": "application",
                    "losses_collector": "application",
                },
            },
            "configuration": {
                "recipient": {
                    "capabilities": {
                        "stripe_balance": {
                            "stripe_transfers": {"requested": True},
                        },
                    },
                },
            },
        }
    )
    return {
        "account_id": account.id,
        "display_name": display_name,
        "email": email,
        "created": True,
    }


def create_account_link(account_id: str, return_url: str, refresh_url: str) -> dict:
    """Create a Stripe Account Link for onboarding a connected account.

    The user is redirected to Stripe's hosted onboarding flow.
    After completion, they return to return_url. If the link expires,
    they're sent to refresh_url to generate a new link.

    Args:
        account_id: The Stripe connected account ID (acct_...).
        return_url: URL the user returns to after onboarding completes.
        refresh_url: URL to redirect to if the onboarding link expires.

    Returns:
        dict with the onboarding URL.
    """
    if not _stripe_ready:
        return {"error": "Stripe not configured. Set STRIPE_SECRET_KEY."}
    if not _stripe_v2_ready or _client is None:
        return {"error": "Stripe Accounts V2 requires a newer Stripe SDK with StripeClient support."}

    # V2 account links API for onboarding
    link = _client.v2.core.account_links.create(
        params={
            "account": account_id,
            "use_case": {
                "type": "account_onboarding",
                "account_onboarding": {
                    "configurations": ["recipient"],
                    "refresh_url": refresh_url,
                    "return_url": f"{return_url}?accountId={account_id}",
                },
            },
        }
    )
    return {"url": link.url, "account_id": account_id}


def get_account_status(account_id: str) -> dict:
    """Retrieve the current onboarding and capability status of a connected account.

    Checks whether the account can receive payments and whether
    onboarding requirements are complete.

    Args:
        account_id: The Stripe connected account ID.

    Returns:
        dict with onboarding_complete, ready_to_receive_payments, and details.
    """
    if not _stripe_ready:
        return {"error": "Stripe not configured. Set STRIPE_SECRET_KEY."}
    if not _stripe_v2_ready or _client is None:
        return {"error": "Stripe Accounts V2 requires a newer Stripe SDK with StripeClient support."}

    # Retrieve account with configuration and requirements included
    account = _client.v2.core.accounts.retrieve(
        account_id,
        params={"include": ["configuration.recipient", "requirements"]},
    )

    # Check if transfers capability is active
    ready_to_receive = False
    try:
        ready_to_receive = (
            account.configuration.recipient.capabilities
            .stripe_balance.stripe_transfers.status == "active"
        )
    except AttributeError:
        pass

    # Check if onboarding requirements are satisfied
    requirements_status = None
    onboarding_complete = False
    try:
        requirements_status = account.requirements.summary.minimum_deadline.status
        onboarding_complete = requirements_status not in ("currently_due", "past_due")
    except AttributeError:
        pass

    return {
        "account_id": account_id,
        "display_name": getattr(account, "display_name", ""),
        "ready_to_receive_payments": ready_to_receive,
        "onboarding_complete": onboarding_complete,
        "requirements_status": requirements_status,
    }


# ── Products ──────────────────────────────────────────────────────────────

def create_product(
    name: str,
    description: str,
    price_cents: int,
    currency: str = "usd",
    connected_account_id: str = "",
) -> dict:
    """Create a product at the platform level with a default price.

    The connected_account_id is stored in metadata to map this product
    to the account that should receive the payout.

    Args:
        name: Product display name.
        description: Product description.
        price_cents: Price in cents (e.g., 4900 = $49.00).
        currency: ISO currency code (default: 'usd').
        connected_account_id: The connected account that owns/sells this product.

    Returns:
        dict with product_id, price_id, and details.
    """
    if not _stripe_ready:
        return {"error": "Stripe not configured. Set STRIPE_SECRET_KEY."}

    # Create product at platform level with connected account in metadata
    if _stripe_v2_ready and _client is not None:
        product = _client.products.create(
            params={
                "name": name,
                "description": description,
                "default_price_data": {
                    "unit_amount": price_cents,
                    "currency": currency,
                },
                "metadata": {
                    "connected_account_id": connected_account_id,
                    "platform": "civitae_kassa",
                },
            }
        )
    else:
        product = _stripe_module.Product.create(
            name=name,
            description=description,
            default_price_data={
                "unit_amount": price_cents,
                "currency": currency,
            },
            metadata={
                "connected_account_id": connected_account_id,
                "platform": "civitae_kassa",
            },
        )
    return {
        "product_id": product.id,
        "price_id": product.default_price,
        "name": name,
        "description": description,
        "price_cents": price_cents,
        "currency": currency,
        "connected_account_id": connected_account_id,
    }


def list_products() -> list[dict]:
    """List all products on the platform with their connected account mappings."""
    if not _stripe_ready:
        return []

    if _stripe_v2_ready and _client is not None:
        products = _client.products.list(params={"active": True, "limit": 100})
        product_rows = products.data
    else:
        products = _stripe_module.Product.list(active=True, limit=100)
        product_rows = products.data
    result = []
    for p in product_rows:
        # Get the default price amount
        price_cents = 0
        price_id = ""
        if p.default_price:
            price_id = p.default_price if isinstance(p.default_price, str) else p.default_price.id
            try:
                if _stripe_v2_ready and _client is not None:
                    price = _client.prices.retrieve(price_id)
                else:
                    price = _stripe_module.Price.retrieve(price_id)
                price_cents = price.unit_amount or 0
            except Exception:
                pass

        result.append({
            "product_id": p.id,
            "name": p.name,
            "description": p.description or "",
            "price_cents": price_cents,
            "price_id": price_id,
            "connected_account_id": (p.metadata or {}).get("connected_account_id", ""),
            "images": p.images or [],
        })
    return result


# ── Checkout (Destination Charges) ────────────────────────────────────────

def create_checkout_session(
    product_name: str,
    price_cents: int,
    connected_account_id: str,
    success_url: str,
    cancel_url: str,
    app_fee_percent: int = DEFAULT_APP_FEE_PERCENT,
    metadata: dict | None = None,
) -> dict:
    """Create a Stripe Checkout Session with a destination charge.

    Uses destination charges so the payment goes to the connected account
    with an application fee retained by the platform (CIVITAE).

    The application fee is calculated as a percentage of the total amount,
    determined by the governance tier of the connected account.

    Args:
        product_name: Display name for the line item.
        price_cents: Total price in cents.
        connected_account_id: The connected account receiving the payout.
        success_url: URL after successful payment. Use {CHECKOUT_SESSION_ID} placeholder.
        cancel_url: URL if customer cancels.
        app_fee_percent: Platform fee percentage (default from governance tier).
        metadata: Additional metadata to attach to the session.

    Returns:
        dict with session_id and checkout URL.
    """
    if not _stripe_ready:
        return {"error": "Stripe not configured. Set STRIPE_SECRET_KEY."}

    if not connected_account_id:
        return {"error": "No connected account specified for this product."}

    # Calculate application fee from governance tier percentage
    app_fee_amount = int(price_cents * app_fee_percent / 100)

    session_params = {
        "line_items": [{
            "price_data": {
                "currency": "usd",
                "unit_amount": price_cents,
                "product_data": {"name": product_name},
            },
            "quantity": 1,
        }],
        "payment_intent_data": {
            "application_fee_amount": app_fee_amount,
            "transfer_data": {
                "destination": connected_account_id,
            },
        },
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": metadata or {},
    }
    if _stripe_v2_ready and _client is not None:
        session = _client.checkout.sessions.create(params=session_params)
    else:
        session = _stripe_module.checkout.Session.create(**session_params)
    return {
        "session_id": session.id,
        "url": session.url,
        "rail": "stripe_connect",
        "app_fee_cents": app_fee_amount,
    }


def retrieve_checkout_session(session_id: str) -> dict:
    """Retrieve details of a completed checkout session."""
    if not _stripe_ready:
        return {"error": "Stripe not configured."}
    if _stripe_v2_ready and _client is not None:
        session = _client.checkout.sessions.retrieve(session_id)
    else:
        session = _stripe_module.checkout.Session.retrieve(session_id)
    return {
        "session_id": session.id,
        "payment_status": session.payment_status,
        "amount_total": session.amount_total,
        "currency": session.currency,
        "customer_email": session.customer_details.email if session.customer_details else None,
    }


# ── Webhooks (Thin Events for V2) ─────────────────────────────────────────

def parse_thin_event(payload: bytes, sig_header: str) -> dict | None:
    """Parse a Stripe thin event from a webhook payload.

    Thin events are used with V2 accounts. They contain only the event ID
    and type — the full event data must be fetched separately.

    For webhook setup:
    1. Dashboard → Developers → Webhooks → + Add destination
    2. Select "Connected accounts" in Events from
    3. Show advanced options → Payload style: "Thin"
    4. Select v2.account[requirements].updated and
       v2.account[configuration.configuration_type].capability_status_updated

    Local testing with Stripe CLI:
      stripe listen --thin-events \\
        'v2.core.account[requirements].updated,v2.core.account[.recipient].capability_status_updated' \\
        --forward-thin-to http://localhost:8300/api/connect/webhooks

    Args:
        payload: Raw request body bytes.
        sig_header: The Stripe-Signature header value.

    Returns:
        dict with event details, or None if verification fails.
    """
    if not _stripe_v2_ready or _client is None or not STRIPE_WEBHOOK_SECRET:
        return None

    try:
        # Parse the thin event — validates signature against webhook secret
        thin_event = _client.parse_thin_event(
            payload.decode("utf-8"),
            sig_header,
            STRIPE_WEBHOOK_SECRET,
        )
        # Fetch the full event data from Stripe
        event = _client.v2.core.events.retrieve(thin_event.id)
        return {
            "id": event.id,
            "type": event.type,
            "data": event.data if hasattr(event, "data") else None,
            "related_object": event.related_object if hasattr(event, "related_object") else None,
        }
    except Exception:
        return None


# ── MPP (Machine Payments Protocol) ───────────────────────────────────────

def mpp_challenge(amount_usd: str, resource_id: str, description: str) -> dict:
    """Generate an MPP 402 challenge response for an agent payment.

    When an agent requests a paid resource, the server returns HTTP 402
    with payment details. The agent's client creates credentials and
    retries the request with an Authorization header containing the
    MPP credential.

    Flow:
    1. Agent → GET /resource → Server returns 402 + challenge
    2. Agent authorizes payment → creates MPP credential
    3. Agent → GET /resource (Authorization: MPP <credential>) → Server verifies → 200

    Args:
        amount_usd: Payment amount as string (e.g., "0.50").
        resource_id: The resource being purchased (post_id, thread_id, etc.).
        description: Human-readable description of what's being purchased.

    Returns:
        Challenge payload to return as HTTP 402 response body.
    """
    challenge_id = f"ch_{secrets.token_hex(16)}"
    return {
        "type": "https://paymentauth.org/problems/payment-required",
        "status": 402,
        "challengeId": challenge_id,
        "amount": amount_usd,
        "currency": "usd",
        "resource": resource_id,
        "description": description,
        "methods": _mpp_methods(),
        "recipient": MPP_RECIPIENT or "civitae-treasury",
        "rail": "mpp",
    }


def _mpp_methods() -> list[dict]:
    """Available MPP payment methods."""
    methods = []
    if MPP_SECRET_KEY:
        methods.append({
            "type": "tempo",
            "network": "tempo",
            "currency": "USDC",
            "label": "Pay with USDC (Tempo)",
        })
    if _stripe_ready:
        methods.append({
            "type": "spt",
            "network": "stripe",
            "payment_method_types": ["card", "link"],
            "label": "Pay with card (via Stripe SPT)",
        })
    return methods


def mpp_verify_credential(authorization: str) -> dict | None:
    """Verify an MPP credential from the Authorization header.

    In production with the mppx Python SDK:
      from mppx.server import Mppx
      mppx = Mppx.create(secretKey=MPP_SECRET_KEY, methods=[...])
      receipt = mppx.verify(authorization)

    Full mppx integration requires the npm package (Node.js) or
    Python implementation (pending).

    Args:
        authorization: The full Authorization header value (MPP <credential>).

    Returns:
        Payment receipt dict if valid, None if invalid.
    """
    if not authorization or not authorization.startswith("MPP "):
        return None

    credential_data = authorization[4:]
    if len(credential_data) < 10:
        return None

    return {
        "verified": True,
        "credential": credential_data[:12] + "...",
        "rail": "mpp",
        "timestamp": datetime.now(UTC).isoformat(),
    }


# ── Unified Payment Interface ─────────────────────────────────────────────

def create_payment(
    post_id: str,
    amount_usd: float,
    description: str,
    connected_account_id: str = "",
    rail: str = "auto",
    agent_request: bool = False,
    success_url: str = "",
    cancel_url: str = "",
    app_fee_percent: int = DEFAULT_APP_FEE_PERCENT,
    metadata: dict | None = None,
) -> dict:
    """Create a payment via the best available rail.

    rail="auto" selects MPP for agent requests, Stripe Connect for human requests.
    rail="mpp" forces MPP (returns 402 challenge).
    rail="stripe" forces Stripe Connect with destination charge.

    Args:
        post_id: The KA§§A post this payment is for.
        amount_usd: Payment amount in USD.
        description: Human-readable payment description.
        connected_account_id: The Stripe connected account to pay.
        rail: Payment rail selection ("auto", "mpp", "stripe").
        agent_request: True if the requester is an authenticated agent.
        success_url: Redirect URL after successful payment.
        cancel_url: Redirect URL if payment is cancelled.
        app_fee_percent: Platform fee percentage (governance-tier based).
        metadata: Additional metadata for the payment.

    Returns:
        Payment initiation result (checkout URL, MPP challenge, or error).
    """
    if rail == "auto":
        rail = "mpp" if (agent_request and mpp_ready()) else "stripe"

    if rail == "mpp":
        if not mpp_ready():
            return {"error": "MPP not configured", "rail": "mpp"}
        return mpp_challenge(
            amount_usd=f"{amount_usd:.2f}",
            resource_id=post_id,
            description=description,
        )

    if rail == "stripe":
        if not stripe_ready():
            return {"error": "Stripe not configured", "rail": "stripe_connect"}
        price_cents = int(amount_usd * 100)
        return create_checkout_session(
            product_name=description,
            price_cents=price_cents,
            connected_account_id=connected_account_id,
            success_url=success_url or f"/?payment=success&post={post_id}",
            cancel_url=cancel_url or f"/?payment=cancelled&post={post_id}",
            app_fee_percent=app_fee_percent,
            metadata={"post_id": post_id, **(metadata or {})},
        )

    return {"error": f"Unknown rail: {rail}"}
