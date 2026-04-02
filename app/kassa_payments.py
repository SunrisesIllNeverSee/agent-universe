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

import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
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

# In-memory challenge store: { challenge_id: { ...challenge, expires_at: float } }
# Challenges expire after 1 hour. Cleared on restart (acceptable for stateless pay flow).
_mpp_challenges: dict[str, dict] = {}
_MPP_CHALLENGE_TTL = 3600  # seconds
_MPP_CREDENTIAL_TTL = 300  # 5-minute access window per credential

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
        "stripe_v2": _stripe_v2_ready,
        "mpp": mpp_ready(),
        "rails": [
            r for r in ["stripe_connect", "mpp"]
            if (r == "stripe_connect" and stripe_ready()) or (r == "mpp" and mpp_ready())
        ],
    }


# ── Connected Accounts (V1 API — Operators/Sellers) ───────────────────────

def create_connected_account(display_name: str, email: str, country: str = "us") -> dict:
    """Create a Stripe connected account using the V1 API (standard Connect).

    Uses controller-based account creation per Stripe's marketplace quickstart.
    Platform is responsible for fees and losses. Stripe hosts the dashboard.

    Args:
        display_name: The name shown on the connected account (agent/operator name).
        email: Contact email for the connected account.
        country: ISO country code (default: 'us').

    Returns:
        dict with account_id and status, or error details.
    """
    if not _stripe_ready:
        return {"error": "Stripe not configured. Set STRIPE_SECRET_KEY."}

    try:
        params = {
            "controller": {
                "stripe_dashboard": {"type": "express"},
                "fees": {"payer": "application"},
                "losses": {"payments": "application"},
                "requirement_collection": "stripe",
            },
            "capabilities": {
                "transfers": {"requested": True},
            },
            "country": country.upper(),
        }
        if email:
            params["email"] = email
        if display_name:
            params["business_profile"] = {"name": display_name}

        if _stripe_v2_ready and _client is not None:
            account = _client.v1.accounts.create(params=params)
        else:
            account = _stripe_module.Account.create(**params)
    except Exception as e:
        return {"error": f"Stripe account creation failed: {e}"}

    return {
        "account_id": account.id,
        "display_name": display_name,
        "email": email,
        "created": True,
    }


# ── Connected Accounts (V2 API — Agents/Recipients) ───────────────────────

def create_recipient_account(display_name: str, email: str, country: str = "us") -> dict:
    """Create a Stripe V2 Recipient account for agent payouts.

    V2 Recipient accounts are machine-native — designed for autonomous agents
    that receive payments for completing missions/bounties. Unlike V1 Express
    accounts (for humans selling products), Recipients don't need Stripe's hosted
    onboarding dashboard and can receive transfers directly.

    Requires Stripe to enable V2 API on your platform account. If not enabled,
    falls back to creating a V1 Express account with the same parameters.

    Args:
        display_name: The agent's display name.
        email: Contact email for the recipient.
        country: ISO country code (default: 'us').

    Returns:
        dict with account_id, type ('recipient' or 'express'), and status.
    """
    if not _stripe_v2_ready or _client is None:
        return {"error": "Stripe V2 SDK not available. Update stripe SDK."}

    try:
        # V2 responses are sparse by default — include required to get id + config back.
        if not email:
            return {"error": "contact_email is required for Recipient accounts"}

        now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        params: dict = {
            "display_name": display_name,
            "contact_email": email,
            "dashboard": "none",  # agents are machines — no Stripe dashboard
            "identity": {
                "country": country.upper(),
                "entity_type": "individual",
                "individual": {
                    # Agents don't have human names — use handle as given_name,
                    # "Agent" as surname. Platform attests identity on agent's behalf.
                    "given_name": display_name,
                    "surname": "Agent",
                },
                "attestations": {
                    "terms_of_service": {
                        "account": {
                            "date": now_iso,
                            "ip": "127.0.0.1",  # platform attests on agent's behalf
                        }
                    }
                },
            },
            "defaults": {
                "currency": "usd",
                "responsibilities": {
                    "fees_collector": "application",
                    "losses_collector": "application",
                },
                "profile": {
                    "business_url": "https://civitae.io",
                },
            },
            "configuration": {
                "recipient": {
                    "capabilities": {
                        "stripe_balance": {
                            "stripe_transfers": {"requested": True},
                        },
                    }
                }
            },
            "include": ["configuration.recipient", "identity", "requirements"],
        }
        account = _client.v2.core.accounts.create(params=params)
        return {
            "account_id": account.id,
            "display_name": display_name,
            "email": email,
            "type": "recipient",
            "created": True,
        }
    except Exception as e:
        err = str(e)
        print(f"[kassa] V2 Recipient create failed: {type(e).__name__}: {err}", file=sys.stderr)
        # Surface actionable platform-profile error instead of burying it in a fallback
        if "platform-profile" in err or "responsibilities" in err.lower():
            return {
                "error": "Stripe platform profile not configured. "
                         "Complete setup at: https://dashboard.stripe.com/settings/connect/platform-profile",
                "stripe_setup_url": "https://dashboard.stripe.com/settings/connect/platform-profile",
                "v2_error": err,
            }
        fallback = create_connected_account(display_name, email, country)
        if not fallback.get("error"):
            fallback["type"] = "express_fallback"
            fallback["v2_error"] = err
            fallback["v2_note"] = "V2 Recipient creation failed; created V1 Express account instead."
        return fallback


def create_account_session(account_id: str) -> dict:
    """Create a Stripe Account Session for embedded Connect components.

    Used with Stripe.js Connect Components to render the onboarding flow
    inline on the page (no redirect). The client_secret is passed to
    loadConnectAndInitialize() in the frontend.

    Args:
        account_id: The Stripe connected or recipient account ID.

    Returns:
        dict with client_secret for use with Stripe.js.
    """
    if not _stripe_ready:
        return {"error": "Stripe not configured."}

    try:
        params = {
            "account": account_id,
            "components": {
                "account_onboarding": {"enabled": True},
            },
        }
        if _stripe_v2_ready and _client is not None:
            session = _client.v1.account_sessions.create(params=params)
        else:
            session = _stripe_module.AccountSession.create(**params)
    except Exception as e:
        return {"error": f"Stripe account session failed: {e}"}

    return {"client_secret": session.client_secret, "account_id": account_id}


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

    try:
        params = {
            "account": account_id,
            "refresh_url": refresh_url,
            "return_url": return_url,  # caller is responsible for building the full URL
            "type": "account_onboarding",
        }
        if _stripe_v2_ready and _client is not None:
            link = _client.v1.account_links.create(params=params)
        else:
            link = _stripe_module.AccountLink.create(**params)
    except Exception as e:
        return {"error": f"Stripe onboarding link failed: {e}"}

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

    try:
        if _stripe_v2_ready and _client is not None:
            account = _client.v1.accounts.retrieve(account_id)
        else:
            account = _stripe_module.Account.retrieve(account_id)
    except Exception as e:
        return {"error": f"Stripe account retrieve failed: {e}"}

    # Check if transfers capability is active
    ready_to_receive = False
    try:
        ready_to_receive = account.capabilities.get("transfers") == "active"
    except AttributeError:
        pass

    # Check onboarding requirements
    onboarding_complete = False
    requirements_status = None
    try:
        req = account.requirements
        currently_due = getattr(req, "currently_due", []) or []
        past_due = getattr(req, "past_due", []) or []
        onboarding_complete = len(currently_due) == 0 and len(past_due) == 0
        if past_due:
            requirements_status = "past_due"
        elif currently_due:
            requirements_status = "currently_due"
        else:
            requirements_status = "complete"
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
    product_params = {
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
    try:
        if _stripe_v2_ready and _client is not None:
            product = _client.v1.products.create(params=product_params)
        else:
            product = _stripe_module.Product.create(**product_params)
    except Exception as e:
        return {"error": f"Stripe product creation failed: {e}"}
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

    try:
        if _stripe_v2_ready and _client is not None:
            products = _client.v1.products.list(params={"active": True, "limit": 100})
        else:
            products = _stripe_module.Product.list(active=True, limit=100)
        product_rows = products.data
    except Exception:
        return []
    result = []
    for p in product_rows:
        # Get the default price amount
        price_cents = 0
        price_id = ""
        if p.default_price:
            price_id = p.default_price if isinstance(p.default_price, str) else p.default_price.id
            try:
                if _stripe_v2_ready and _client is not None:
                    price = _client.v1.prices.retrieve(price_id)
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

    # If no connected account, fall back to direct charge (platform collects)
    if connected_account_id:
        # Destination charge — split between connected account and platform
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
    else:
        # Direct charge — platform collects full amount (soft launch)
        session_params = {
            "line_items": [{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": price_cents,
                    "product_data": {"name": product_name},
                },
                "quantity": 1,
            }],
            "mode": "payment",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {**(metadata or {}), "direct_charge": "true"},
        }
    try:
        if _stripe_v2_ready and _client is not None:
            session = _client.v1.checkout.sessions.create(params=session_params)
        else:
            session = _stripe_module.checkout.Session.create(**session_params)
    except Exception as e:
        return {"error": f"Stripe checkout failed: {e}"}
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
    try:
        if _stripe_v2_ready and _client is not None:
            session = _client.v1.checkout.sessions.retrieve(session_id)
        else:
            session = _stripe_module.checkout.Session.retrieve(session_id)
    except Exception as e:
        return {"error": f"Stripe session retrieve failed: {e}"}
    return {
        "session_id": session.id,
        "payment_status": session.payment_status,
        "amount_total": session.amount_total,
        "currency": session.currency,
        "customer_email": session.customer_details.email if session.customer_details else None,
    }


# ── Webhooks (Thin Events for V2) ─────────────────────────────────────────

def parse_thin_event(payload: bytes, sig_header: str) -> dict | None:
    """Parse a Stripe V2 event notification from a webhook payload.

    V2 event notifications are used with V2 accounts. The SDK method
    parse_event_notification() validates the signature and returns a
    typed event object.

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
        # parse_event_notification validates signature and returns typed event
        event = _client.parse_event_notification(
            payload,
            sig_header,
            STRIPE_WEBHOOK_SECRET,
        )
        return {
            "id": event.id if hasattr(event, "id") else "",
            "type": event.type if hasattr(event, "type") else "",
            "data": event.data if hasattr(event, "data") else None,
            "related_object": event.related_object if hasattr(event, "related_object") else None,
        }
    except Exception:
        return None


# ── MPP (Machine Payments Protocol) ───────────────────────────────────────

def _mpp_signing_key() -> bytes:
    """Return the HMAC signing key for MPP credentials."""
    key = MPP_SECRET_KEY or STRIPE_SECRET_KEY or "civitae-dev-key"
    return key.encode()


def _mpp_sign(payload: dict) -> str:
    """Encode and sign an MPP payload. Returns base64_payload.hex_sig."""
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode()
    sig = hmac.new(_mpp_signing_key(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def _mpp_unsign(token: str) -> dict | None:
    """Verify HMAC signature and decode payload. Returns None if invalid."""
    try:
        payload_b64, sig = token.rsplit(".", 1)
    except ValueError:
        return None
    expected = hmac.new(_mpp_signing_key(), payload_b64.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        return None


def _mpp_purge_expired() -> None:
    """Remove expired challenges from the in-memory store."""
    now = time.time()
    expired = [k for k, v in _mpp_challenges.items() if v.get("expires_at", 0) < now]
    for k in expired:
        del _mpp_challenges[k]


def mpp_challenge(amount_usd: str, resource_id: str, description: str) -> dict:
    """Generate and store an MPP 402 challenge for an agent payment.

    Flow:
    1. Agent → GET /resource → Server returns 402 + challenge
    2. Agent → POST /api/mpp/pay { challenge_id, agent_id } → Server debits treasury, returns token
    3. Agent → GET /resource (Authorization: MPP <token>) → Server verifies → 200

    Args:
        amount_usd: Payment amount as string (e.g., "0.50").
        resource_id: The resource being purchased (post_id, thread_id, etc.).
        description: Human-readable description of what's being purchased.

    Returns:
        Challenge payload to return as HTTP 402 response body.
    """
    _mpp_purge_expired()
    challenge_id = f"ch_{secrets.token_hex(16)}"
    now = time.time()
    _mpp_challenges[challenge_id] = {
        "challenge_id": challenge_id,
        "amount": amount_usd,
        "resource": resource_id,
        "description": description,
        "created_at": now,
        "expires_at": now + _MPP_CHALLENGE_TTL,
        "paid": False,
    }
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
        "pay_url": "/api/mpp/pay",
        "rail": "mpp",
    }


def _mpp_methods() -> list[dict]:
    """Available MPP payment methods."""
    methods = [
        {
            "type": "treasury_balance",
            "network": "civitae",
            "currency": "USD",
            "label": "Pay from agent treasury balance",
        }
    ]
    if _stripe_ready:
        methods.append({
            "type": "spt",
            "network": "stripe",
            "payment_method_types": ["card", "link"],
            "label": "Pay with card (via Stripe)",
        })
    return methods


def mpp_pay(challenge_id: str, agent_id: str, treasury) -> dict:
    """Authorize an MPP challenge by debiting the agent's treasury balance.

    Args:
        challenge_id: The challenge ID from the 402 response.
        agent_id: The paying agent's handle/ID.
        treasury: AgentTreasury instance for balance operations.

    Returns:
        dict with 'token' (the MPP Authorization value) on success, or 'error'.
    """
    _mpp_purge_expired()
    challenge = _mpp_challenges.get(challenge_id)
    if not challenge:
        return {"error": "Challenge not found or expired"}
    if challenge["paid"]:
        return {"error": "Challenge already redeemed"}
    if time.time() > challenge["expires_at"]:
        return {"error": "Challenge expired"}

    amount = float(challenge["amount"])
    debit_result = treasury.debit(agent_id, amount, f"mpp:{challenge['resource']}")
    if debit_result.get("error"):
        return {"error": debit_result["error"]}

    challenge["paid"] = True
    challenge["paid_by"] = agent_id
    challenge["paid_at"] = time.time()

    now = time.time()
    credential_payload = {
        "challenge_id": challenge_id,
        "resource": challenge["resource"],
        "amount": challenge["amount"],
        "agent_id": agent_id,
        "iat": int(now),
        "exp": int(now + _MPP_CREDENTIAL_TTL),
    }
    token = _mpp_sign(credential_payload)
    return {
        "token": f"MPP {token}",
        "resource": challenge["resource"],
        "amount": challenge["amount"],
        "expires_in": _MPP_CREDENTIAL_TTL,
    }


def mpp_verify_credential(authorization: str) -> dict | None:
    """Verify an MPP credential from the Authorization header.

    Validates HMAC signature and token expiry. Returns the decoded
    payload (resource, agent_id, amount, timestamps) if valid, None otherwise.

    Args:
        authorization: The full Authorization header value (MPP <token>).

    Returns:
        Decoded credential payload if valid, None if invalid or expired.
    """
    if not authorization or not authorization.startswith("MPP "):
        return None
    token = authorization[4:]
    payload = _mpp_unsign(token)
    if not payload:
        return None
    if time.time() > payload.get("exp", 0):
        return None
    return {
        "verified": True,
        "challenge_id": payload.get("challenge_id"),
        "resource": payload.get("resource"),
        "amount": payload.get("amount"),
        "agent_id": payload.get("agent_id"),
        "rail": "mpp",
        "issued_at": datetime.fromtimestamp(payload["iat"], UTC).isoformat(),
        "expires_at": datetime.fromtimestamp(payload["exp"], UTC).isoformat(),
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
        _base = os.environ.get("CIVITAE_BASE_URL", "https://signomy.xyz")
        price_cents = int(amount_usd * 100)
        return create_checkout_session(
            product_name=description,
            price_cents=price_cents,
            connected_account_id=connected_account_id,
            success_url=success_url or f"{_base}/connect/success?post={post_id}",
            cancel_url=cancel_url or f"{_base}/kassa?payment=cancelled&post={post_id}",
            app_fee_percent=app_fee_percent,
            metadata={"post_id": post_id, **(metadata or {})},
        )

    return {"error": f"Unknown rail: {rail}"}
