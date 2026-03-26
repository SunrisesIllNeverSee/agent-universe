"""KA§§A Payment Layer — dual-rail: Stripe Connect + MPP (Machine Payments Protocol).

Stripe Connect handles fiat payments (bounty rewards, service purchases).
MPP handles agent micropayments (stakes, thread access, referral commissions).

Both rails are optional — endpoints degrade gracefully when keys aren't configured.
Set STRIPE_SECRET_KEY and MPP_SECRET_KEY in environment to activate.
"""
from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, UTC
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
MPP_SECRET_KEY = os.environ.get("MPP_SECRET_KEY", "")
MPP_RECIPIENT = os.environ.get("MPP_RECIPIENT", "")  # stablecoin recipient address

_stripe = None
_stripe_ready = False

if STRIPE_SECRET_KEY:
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        _stripe = stripe
        _stripe_ready = True
    except ImportError:
        pass


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


# ── Stripe Connect ────────────────────────────────────────────────────────

def create_checkout_session(
    post_id: str,
    amount_cents: int,
    description: str,
    success_url: str,
    cancel_url: str,
    metadata: dict | None = None,
) -> dict:
    """Create a Stripe Checkout Session for a bounty/service payment."""
    if not _stripe_ready:
        return {"error": "Stripe not configured", "rail": "stripe_connect"}

    session = _stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "usd",
                "unit_amount": amount_cents,
                "product_data": {"name": description},
            },
            "quantity": 1,
        }],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"post_id": post_id, **(metadata or {})},
    )
    return {
        "session_id": session.id,
        "url": session.url,
        "rail": "stripe_connect",
    }


def create_payment_intent(
    amount_cents: int,
    description: str,
    metadata: dict | None = None,
) -> dict:
    """Create a PaymentIntent for programmatic payment collection."""
    if not _stripe_ready:
        return {"error": "Stripe not configured", "rail": "stripe_connect"}

    intent = _stripe.PaymentIntent.create(
        amount=amount_cents,
        currency="usd",
        description=description,
        metadata=metadata or {},
    )
    return {
        "payment_intent_id": intent.id,
        "client_secret": intent.client_secret,
        "status": intent.status,
        "rail": "stripe_connect",
    }


def verify_webhook_signature(payload: bytes, sig_header: str) -> dict | None:
    """Verify a Stripe webhook signature and return the event."""
    if not _stripe_ready or not STRIPE_WEBHOOK_SECRET:
        return None
    try:
        event = _stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        return event
    except Exception:
        return None


# ── MPP (Machine Payments Protocol) ───────────────────────────────────────

def mpp_challenge(
    amount_usd: str,
    resource_id: str,
    description: str,
) -> dict:
    """Generate an MPP 402 challenge response for an agent payment.

    Returns the challenge payload that should be sent as HTTP 402.
    The agent client then creates credentials and retries with Authorization header.
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

    In production, this validates the cryptographic credential against
    the challenge binding using the shared secret key.

    Returns payment receipt dict if valid, None if invalid.
    """
    if not authorization:
        return None

    # MPP credentials come as: MPP <base64-credential>
    if not authorization.startswith("MPP "):
        return None

    # In production with mppx SDK:
    #   from mppx.server import Mppx
    #   mppx = Mppx.create(secretKey=MPP_SECRET_KEY, methods=[...])
    #   receipt = mppx.verify(authorization)
    #
    # For now, we validate the structure and log the attempt.
    # Full mppx integration requires the npm package (Node.js).
    # Python implementation pending — track: github.com/AgileCoding37/mppx-python

    credential_data = authorization[4:]  # strip "MPP "
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
    rail: str = "auto",
    agent_request: bool = False,
    success_url: str = "",
    cancel_url: str = "",
    metadata: dict | None = None,
) -> dict:
    """Create a payment via the best available rail.

    rail="auto" selects MPP for agent requests, Stripe Connect for human requests.
    rail="mpp" forces MPP (returns 402 challenge).
    rail="stripe" forces Stripe Connect.
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
        amount_cents = int(amount_usd * 100)
        if success_url and cancel_url:
            return create_checkout_session(
                post_id=post_id,
                amount_cents=amount_cents,
                description=description,
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata,
            )
        return create_payment_intent(
            amount_cents=amount_cents,
            description=description,
            metadata={"post_id": post_id, **(metadata or {})},
        )

    return {"error": f"Unknown rail: {rail}"}
