"""One principal, many doors (P4 slice 2, H1 / 1G 5.B / O-IA-3).

Both credential doors -- a provision ``api_key`` (Bearer, hashed lookup +
revoked-key deny-list) and a KA§§A JWT (Bearer, signature + token_epoch
liveness) -- resolve to the ONE registry agent. A third, narrower door, the
thread magic link, resolves to a *post-scoped* principal that exists only for
email-only posters and can act only on entries for its own post.

Receipts must name the credential type: ``Principal.credential_type`` is one
of ``api_key`` / ``jwt`` / ``magic_link`` / ``admin_key`` and ``Principal.ref``
renders the stable string recorded in receipts and audit entries.

Status codes: 401 = no/forged/revoked/superseded credential; 403 = a genuine
credential that is not authorised for this object.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request

from app.auth import (
    active_agent_from_bearer,
    admin_key_matches,
    agent_token_alive,
    secret_matches,
)

CRED_API_KEY = "api_key"
CRED_JWT = "jwt"
CRED_MAGIC = "magic_link"
CRED_ADMIN = "admin_key"

MAGIC_HEADER = "X-Magic-Token"


@dataclass(frozen=True)
class Principal:
    kind: str                      # "agent" | "poster_link" | "operator"
    credential_type: str           # api_key | jwt | magic_link | admin_key
    agent_id: str | None = None
    agent_name: str | None = None
    thread_id: str | None = None   # magic link only
    post_id: str | None = None     # magic link only: the single post it may act on

    @property
    def ref(self) -> str:
        """Stable string naming principal + credential type for receipts."""
        if self.kind == "agent":
            return f"{self.agent_id}#{self.credential_type}"
        if self.kind == "poster_link":
            return f"poster-link:{self.thread_id}#{self.credential_type}"
        return f"operator#{self.credential_type}"

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "credential_type": self.credential_type,
                "agent_id": self.agent_id, "thread_id": self.thread_id,
                "post_id": self.post_id}

    def require_agent(self) -> str:
        if self.kind != "agent" or not self.agent_id:
            raise HTTPException(403, "A registered-agent credential is required")
        return self.agent_id

    def require_post(self, post_id: str) -> None:
        """A magic link is usable only for its own post's entries."""
        if self.kind == "poster_link" and self.post_id != post_id:
            raise HTTPException(403, "This link is not valid for that post")


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _find_agent(registry: list[dict], agent_id: Any) -> dict | None:
    return next((r for r in registry if r.get("agent_id") == agent_id), None)


def resolve_agent_credential(request: Request, *, registry: list[dict],
                             revoked_keys: "set[str] | None" = None) -> Principal | None:
    """Bearer token -> agent Principal via whichever door it belongs to.

    Returns None when no Bearer token is presented. Raises 401 when one is
    presented but is forged, revoked, superseded or for an inactive agent.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    from app.jwt_config import verify_jwt
    claims = verify_jwt(token)
    if claims:
        agent = _find_agent(registry, claims.get("sub", claims.get("agent_id", "")))
        if not agent_token_alive(agent, claims):
            raise HTTPException(401, "Credential revoked or principal inactive")
        return Principal("agent", CRED_JWT, agent["agent_id"], agent.get("name"))
    agent = active_agent_from_bearer(request, registry, revoked_keys)
    if agent is None:
        raise HTTPException(401, "Invalid, revoked or inactive credential")
    return Principal("agent", CRED_API_KEY, agent["agent_id"], agent.get("name"))


def resolve_magic_credential(request: Request, store: Any, audit: Any = None) -> Principal | None:
    """Thread magic token -> post-scoped Principal (verified against the stored hash).

    Token comes from ``X-Magic-Token`` or the ``magic`` query param. Optional
    ``thread_id`` (query) must match the thread the token belongs to. Every
    resolution -- success or failure -- is audited without the token.
    """
    token = (request.headers.get(MAGIC_HEADER) or request.query_params.get("magic") or "").strip()
    if not token:
        return None
    wanted = request.query_params.get("thread_id") or request.headers.get("X-Thread-Id") or ""
    digest = _hash(token)
    thread = store.get_thread_by_token(digest)
    ok = bool(thread) and secret_matches(digest, thread.get("magic_token")) \
        and (not wanted or wanted == thread.get("thread_id"))
    if audit is not None:
        audit.log("auth", "magic_link_resolved" if ok else "magic_link_rejected", {
            "thread_id": thread.get("thread_id") if ok else wanted or None,
            "post_id": thread.get("post_id") if ok else None,
            "credential_type": CRED_MAGIC,
        })
    if not ok:
        raise HTTPException(401, "Invalid magic link")
    if thread.get("status", "open") != "open":
        raise HTTPException(401, "Magic link is no longer active")
    return Principal("poster_link", CRED_MAGIC, thread_id=thread["thread_id"],
                     post_id=thread["post_id"])


def resolve_principal(request: Request, state: Any, *, allow_magic: bool = False,
                      allow_admin: bool = False) -> Principal:
    """Resolve the acting principal from the request or raise 401.

    Order: Bearer (api_key | JWT) -> magic link (only if ``allow_magic``) ->
    admin key (only if ``allow_admin``). A credential that is presented but
    invalid fails closed (401) rather than falling through to a weaker door.
    """
    p = resolve_agent_credential(request, registry=state.runtime.registry,
                                 revoked_keys=state.runtime.revoked_keys)
    if p is not None:
        return p
    if allow_magic:
        p = resolve_magic_credential(request, state.kassa, state.audit)
        if p is not None:
            return p
    if allow_admin and admin_key_matches(request, state.admin_key):
        return Principal("operator", CRED_ADMIN)
    raise HTTPException(401, "Authentication required")


def acts_for_post_owner(principal: Principal, post: dict) -> bool:
    """May this principal speak for the post's owner (accept/reject entries)?

    Agent: only if it is the recorded ``poster_agent_id``. Magic link: only
    for its own post. Operators never own posts (they act FOR a named
    principal, per 1A F3 / O-IA-5).
    """
    if principal.kind == "agent":
        return bool(post.get("poster_agent_id")) and post["poster_agent_id"] == principal.agent_id
    if principal.kind == "poster_link":
        return principal.post_id == post.get("id")
    return False


def require_money_reader(request: Request, state: Any, agent_id: str) -> Principal:
    """Per-agent money (balances, ledger history, trial liability, fee credits, earnings) is
    private: the agent itself (api_key or JWT) or the operator (X-Admin-Key) only.

    401 = no/invalid credential; 403 = a genuine agent credential for a different agent.
    Ledgers are keyed by ``agent_id``, so the binding is exact (no name/handle aliases).
    """
    p = resolve_principal(request, state, allow_admin=True)
    if p.kind == "operator":
        return p
    if p.kind != "agent" or not p.agent_id or p.agent_id != agent_id:
        raise HTTPException(403, "You can only read your own balance and history")
    return p


def optional_money_viewer(request: Request, state: Any) -> Principal | None:
    """The caller of a public listing that hides per-agent money unless the caller is a party
    or the operator. No credential -> None (public view). A presented but invalid Bearer
    credential still fails closed (401), as everywhere else."""
    p = resolve_agent_credential(request, registry=state.runtime.registry,
                                 revoked_keys=state.runtime.revoked_keys)
    if p is not None:
        return p
    if admin_key_matches(request, state.admin_key):
        return Principal("operator", CRED_ADMIN)
    return None
