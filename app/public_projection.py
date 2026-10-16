"""Public response projections for records that also carry private routing metadata."""
from __future__ import annotations

import hashlib
from typing import Any


_PRIVATE_KASSA_POST_FIELDS = {
    "from_email",
    "operator_contact",
    "magic_token",
    "magic_token_plain",
}


def public_kassa_post(post: dict[str, Any]) -> dict[str, Any]:
    """Return the public marketplace representation of a stored KA§§A post.

    Contact/routing metadata remains available to internal review and notification
    workflows but is never part of unauthenticated marketplace discovery.
    """
    email = str(post.get("from_email") or "").strip().lower()
    if email.endswith("@signomy.xyz"):
        collaborator_type = "aai"
    elif email:
        collaborator_type = "bi"
    else:
        collaborator_type = "unknown"

    public = {
        key: value
        for key, value in post.items()
        if key not in _PRIVATE_KASSA_POST_FIELDS
    }
    public["collaborator_type"] = collaborator_type
    return public


# ── Shared private-value rules (leak sweep 2026-10-16) ───────────────────────
# Free-form records (audit detail, Seed metadata) cannot carry a fixed field list, so
# their public view drops these keys at any depth and masks external email values.
# Platform mailboxes (``{handle}@signomy.xyz``) are public identity labels, not secrets.
PRIVATE_DETAIL_KEYS = frozenset({
    "address", "to", "dest", "destination", "wallet_address",
    "ip", "signup_ip", "caller_ip",
    "email", "from_email", "poster_email", "contact_email", "operator_contact", "contact",
    "phone", "password",
    "account_id", "stripe_account_id", "stripe_session_id", "client_secret",
    "key_hash", "key_prefix", "new_key_prefix", "api_key", "token", "magic_token", "magic_token_plain",
    "secret", "webhook_secret",
}) | frozenset({
    # Per-agent money (ledger privacy, 2026-10-16): balances, transaction amounts, earnings,
    # commissions, trial liability. Owner + operator read these through principal-bound routes;
    # the public audit feed and the public Seed graph keep the event, never the amount.
    "amount", "gross", "gross_amount", "net", "net_to_agent", "platform_fee", "fee", "fee_amount",
    "fee_breakdown", "balance", "balance_after", "remaining_balance", "matured", "held",
    "purchase_amount", "commission_amount", "buyer_id", "reward", "reward_economic", "total_economic",
    "settlement_due", "settlement_paid", "trial_liability", "would_have_paid", "credited", "consumed",
    "requested", "price_usd", "price_cents",
})
PLATFORM_MAIL_DOMAIN = "@signomy.xyz"
REDACTED = "[redacted]"
# Stripe object ids that identify a payer/payee or a payment (checkout sessions, accounts, ...).
_STRIPE_ID_PREFIXES = ("acct_", "cs_test_", "cs_live_", "pi_", "seti_", "sk_", "rk_", "whsec_", "cus_")


def is_external_email(value: Any) -> bool:
    if not isinstance(value, str) or "@" not in value or " " in value.strip():
        return False
    v = value.strip().lower()
    local, _, domain = v.rpartition("@")
    return bool(local) and "." in domain and not v.endswith(PLATFORM_MAIL_DOMAIN)


def scrub_private(value: Any) -> Any:
    """Recursively drop PRIVATE_DETAIL_KEYS and mask external email strings."""
    if isinstance(value, dict):
        return {k: scrub_private(v) for k, v in value.items() if str(k).lower() not in PRIVATE_DETAIL_KEYS}
    if isinstance(value, list):
        return [scrub_private(v) for v in value]
    if is_external_email(value) or (isinstance(value, str) and value.startswith(_STRIPE_ID_PREFIXES)):
        return REDACTED
    return value


def creator_ref(creator_id: Any) -> Any:
    """Public form of a Seed creator id: agent ids, mailboxes and 'system' pass; an external
    email becomes a stable one-way reference so provenance stays groupable without the address."""
    if is_external_email(creator_id):
        digest = hashlib.sha256(creator_id.strip().lower().encode("utf-8")).hexdigest()[:16]
        return f"bi:{digest}"
    return creator_id


# ── Audit events (public /api/audit, runtime snapshot, /ws + /ws/public) ─────
_PUBLIC_AUDIT_FIELDS = ("id", "timestamp", "component", "action", "detail")


def public_audit_event(event: dict[str, Any]) -> dict[str, Any]:
    """Public view of an audit row. The operator reads raw rows via /api/operator/audit."""
    out = {k: event[k] for k in _PUBLIC_AUDIT_FIELDS if k in event}
    out["detail"] = scrub_private(out.get("detail") or {})
    return out


# ── Seeds (public /api/seeds*, /api/traces/*) ────────────────────────────────
_PUBLIC_SEED_FIELDS = (
    "_v", "doi", "content_hash", "seed_type", "source_type", "source_id", "creator_id",
    "creator_type", "parent_doi", "created_at", "metadata",
)
# Seeds planted by human-facing forms carry the submitter's name in metadata.
_SEED_PRIVATE_METADATA = frozenset({"name", "from_name", "applicant", "message"})


def public_seed(seed: dict[str, Any]) -> dict[str, Any]:
    out = {k: seed[k] for k in _PUBLIC_SEED_FIELDS if k in seed}
    out["creator_id"] = creator_ref(out.get("creator_id"))
    meta = scrub_private(out.get("metadata") or {})
    if isinstance(meta, dict) and (seed.get("creator_type") == "BI" or is_external_email(seed.get("creator_id"))):
        meta = {k: v for k, v in meta.items() if k not in _SEED_PRIVATE_METADATA}
    out["metadata"] = meta
    return out


# ── Agent mailbox label ──────────────────────────────────────────────────────
def public_mailbox(entry: dict[str, Any]) -> str:
    """The agent's public ``@signomy.xyz`` label; never a stored external address."""
    email = str(entry.get("email") or "").strip()
    if email.lower().endswith(PLATFORM_MAIL_DOMAIN):
        return email
    return f"{entry.get('agent_id', '')}{PLATFORM_MAIL_DOMAIN}"


# ── KA§§A negotiation threads ────────────────────────────────────────────────
_THREAD_CREDENTIAL_FIELDS = ("magic_token", "magic_token_plain")


def kassa_thread_view(thread: dict[str, Any], *, viewer_is_poster: bool) -> dict[str, Any]:
    """Thread as shown to a participant. The poster credential never leaves the server; the
    poster's contact address is the poster's own data and is not shown to the staking agent
    (any agent can stake an open post, so showing it would let any agent harvest it)."""
    hidden = set(_THREAD_CREDENTIAL_FIELDS)
    if not viewer_is_poster:
        hidden.add("poster_email")
    return {k: v for k, v in thread.items() if k not in hidden}
