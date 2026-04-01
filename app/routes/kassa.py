"""
kassa.py -- KA$$A marketplace endpoints.

Extracted from server.py create_app() monolith.  Covers:
  - Agent JWT auth (register / login / me)
  - Stakes (intent signalling)
  - Referrals (cross-post matching)
  - Threads (creation, messages, magic links)
  - KA$$A posts board (list / get / submit / upvote)
  - Operator review queue (approve / reject)
  - Product reviews
  - Sales commissions
  - Recruitment rewards
  - Contact inbox
  - Contact messages list
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time as _time
from datetime import UTC, datetime, timedelta

import jwt as pyjwt

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from app.deps import state
from app.seeds import create_seed
from app.notifications import send_magic_link, send_message_notification, send_operator_alert
from app.models import KassaContact, KassaPostCreate

router = APIRouter(tags=["kassa"])

# ── JWT config ───────────────────────────────────────────────────────────────

_JWT_SECRET = os.environ.get("KASSA_JWT_SECRET", "")
if not _JWT_SECRET:
    _JWT_SECRET = secrets.token_hex(32)
    logging.getLogger("civitae").warning(
        "KASSA_JWT_SECRET not set -- using ephemeral key (kassa router). "
        "All JWTs will expire on restart. Set this env var in production."
    )
_JWT_EXPIRY_HOURS = 24


# ── Helpers ──────────────────────────────────────────────────────────────────

def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _issue_jwt(agent_id: str, name: str) -> str:
    payload = {
        "sub": agent_id,
        "name": name,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(hours=_JWT_EXPIRY_HOURS),
    }
    return pyjwt.encode(payload, _JWT_SECRET, algorithm="HS256")


def _verify_jwt(token: str) -> dict | None:
    try:
        return pyjwt.decode(token, _JWT_SECRET, algorithms=["HS256"])
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
        return None


def _extract_jwt(request: Request) -> dict | None:
    """Extract and validate JWT from Authorization header. Returns claims or None."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return _verify_jwt(auth[7:])


def _get_agent_from_token(request: Request) -> dict:
    """Extract and validate JWT from Authorization header. Raises HTTPException on failure."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    claims = _verify_jwt(auth[7:])
    if not claims:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    agent = next((r for r in state.runtime.registry if r.get("agent_id") == claims.get("sub", claims.get("agent_id", ""))), None)
    if not agent or agent.get("status") != "active":
        raise HTTPException(status_code=403, detail="Agent not active")
    return agent


# ── Rate limiter (mirrors server.py pattern) ────────────────────────────────

_rate_stores: dict[str, dict] = {}


def _check_rate_limit(request: Request, bucket_name: str, max_hits: int, window_s: int = 3600):
    """Enforce per-IP rate limit. Raises 429 if exceeded."""
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16]
    now = _time.time()
    if bucket_name not in _rate_stores:
        _rate_stores[bucket_name] = {}
    bucket = _rate_stores[bucket_name]
    # Evict stale entries
    _rate_stores[bucket_name] = {k: v for k, v in bucket.items() if v and now - v[-1] < window_s}
    bucket = _rate_stores[bucket_name]
    recent = [t for t in bucket.get(ip_hash, []) if now - t < window_s]
    if len(recent) >= max_hits:
        raise HTTPException(status_code=429, detail=f"Rate limit: {max_hits} requests per hour")
    recent.append(now)
    bucket[ip_hash] = recent


# ── Admin auth helper (fail-closed) ─────────────────────────────────────────

def _require_admin(request: Request):
    if not state.admin_key:
        raise HTTPException(403, "CIVITAE_ADMIN_KEY not configured")
    if request.headers.get("X-Admin-Key") != state.admin_key:
        raise HTTPException(403, "Admin key required")


# ── Notify email (contact inbox) ────────────────────────────────────────────

_notify_email = os.environ.get("NOTIFY_EMAIL", "")


def _send_notify_email(entry: dict) -> None:
    if not _notify_email:
        return
    try:
        import smtplib
        from email.mime.text import MIMEText
        smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_pass = os.environ.get("SMTP_PASS", "")
        if not smtp_user or not smtp_pass:
            return
        body = (
            f"New KA\u00a7\u00a7A message\n\n"
            f"Post:    {entry['post_id']} ({entry['tab']})\n"
            f"From:    {entry['from_name']} <{entry['from_email']}>\n"
            f"Message:\n{entry['message']}\n\n"
            f"ID: {entry['id']}  |  {entry['timestamp']}"
        )
        msg = MIMEText(body)
        msg["Subject"] = f"[KA\u00a7\u00a7A] {entry['post_id']} \u2014 {entry['from_name']}"
        msg["From"] = smtp_user
        msg["To"] = _notify_email
        with smtplib.SMTP(smtp_host, smtp_port) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, [_notify_email], msg.as_string())
    except Exception:
        pass  # email is best-effort; don't break the endpoint


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT JWT AUTH
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/api/kassa/agent/register")
async def kassa_agent_register(payload: dict) -> dict:
    """
    Register an agent for KASSA. Returns agent_id + api_key (shown once) + JWT.
    Separate from provision signup -- this is the KASSA-specific auth flow.
    """
    agent_name = (payload.get("name") or "").strip()
    if not agent_name:
        raise HTTPException(status_code=400, detail="Agent name required")

    # Check existing
    existing = next((r for r in state.runtime.registry if r.get("name") == agent_name), None)
    if existing:
        raise HTTPException(status_code=409, detail=f"Agent '{agent_name}' already registered")

    agent_id = f"agent-{secrets.token_hex(4)}"
    api_key = f"kassa_{secrets.token_hex(16)}"
    key_hash = _hash_key(api_key)

    entry = {
        "agent_id": agent_id,
        "name": agent_name,
        "type": "agent",
        "status": "active",
        "provisioned": datetime.now(UTC).isoformat(),
        "key_hash": key_hash,
        "key_prefix": api_key[:10] + "***",
        "governance": state.runtime.governance.mode.lower().replace(" ", "_").replace("(", "").replace(")", ""),
        "system": payload.get("system"),
        "role": "secondary",
        "rate_limit": state.runtime.provision.get("rate_limit", {"requests_per_minute": 10, "burst": 20}),
    }

    state.runtime.registry.append(entry)
    state.runtime.persist_registry()

    state.audit.log("kassa", "agent_registered", {"agent_id": agent_id, "name": agent_name})
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))

    token = _issue_jwt(agent_id, agent_name)

    return {
        "agent_id": agent_id,
        "name": agent_name,
        "api_key": api_key,
        "token": token,
        "expires_in": f"{_JWT_EXPIRY_HOURS}h",
        "note": "Store api_key securely -- it will not be shown again. Use token for Bearer auth.",
    }


@router.post("/api/kassa/agent/login")
async def kassa_agent_login(payload: dict) -> dict:
    """Agent login -- exchange agent_id + api_key for a JWT."""
    agent_id = (payload.get("agent_id") or "").strip()
    api_key = (payload.get("api_key") or "").strip()
    if not agent_id or not api_key:
        raise HTTPException(status_code=400, detail="agent_id and api_key required")

    agent = next((r for r in state.runtime.registry if r.get("agent_id") == agent_id), None)
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    stored_hash = agent.get("key_hash", "")
    if not stored_hash or _hash_key(api_key) != stored_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if agent.get("status") != "active":
        raise HTTPException(status_code=403, detail=f"Agent status: {agent.get('status')}")

    token = _issue_jwt(agent_id, agent.get("name", ""))
    agent["last_login"] = datetime.now(UTC).isoformat()
    state.runtime.persist_registry()

    state.audit.log("kassa", "agent_login", {"agent_id": agent_id})

    return {
        "agent_id": agent_id,
        "token": token,
        "expires_in": f"{_JWT_EXPIRY_HOURS}h",
    }


@router.get("/api/kassa/agent/me")
async def kassa_agent_me(request: Request) -> dict:
    """Return current agent profile from JWT."""
    agent = _get_agent_from_token(request)
    return {
        "agent_id": agent["agent_id"],
        "name": agent.get("name"),
        "status": agent.get("status"),
        "governance": agent.get("governance"),
        "role": agent.get("role"),
        "provisioned": agent.get("provisioned"),
        "last_login": agent.get("last_login"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STAKES (intent-only, M1)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/api/kassa/posts/{post_id}/stake")
async def stake_post(post_id: str, request: Request) -> dict:
    """Agent stakes intent on a post -- signals willingness to work on it."""
    agent = _get_agent_from_token(request)
    agent_id = agent["agent_id"]

    # Verify post exists
    post = state.kassa.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post {post_id} not found")

    # Check for duplicate stake
    stakes = state.kassa.load_stakes(post_id=post_id, agent_id=agent_id)
    existing = next((s for s in stakes if s.get("status") == "active"), None)
    if existing:
        raise HTTPException(status_code=409, detail="Already staked on this post")

    stake_id = f"stk-{secrets.token_hex(6)}"
    entry = {
        "stake_id": stake_id,
        "post_id": post_id,
        "agent_id": agent_id,
        "agent_name": agent.get("name"),
        "status": "active",
        "created_at": datetime.now(UTC).isoformat(),
    }
    state.kassa.insert_stake(entry)

    state.audit.log("kassa", "stake_placed", {"stake_id": stake_id, "post_id": post_id, "agent_id": agent_id})
    await state.emit("kassa_stake", entry)

    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="stake",
            source_id=stake_id,
            creator_id=agent_id,
            creator_type="AAI",
            seed_type="planted",
            metadata={"post_id": post_id},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass

    # Auto-create thread between agent and poster
    # Look up poster info from review queue (submitted posts have from_name/email)
    reviews = state.kassa.load_reviews()
    review = next((r for r in reviews if r.get("post", {}).get("id") == post_id), None)
    poster_name = review.get("from_name", "Poster") if review else "Poster"
    poster_email = review.get("from_email", "") if review else ""

    thread_result = _create_thread(
        post_id=post_id,
        post_tab=post.get("tab", ""),
        post_title=post.get("title", ""),
        agent_id=agent_id,
        agent_name=agent.get("name", ""),
        poster_name=poster_name,
        poster_email=poster_email,
    )

    magic_link = f"/kassa/thread/{thread_result['thread_id']}?magic={thread_result['_magic_token_plain']}"

    state.audit.log("kassa", "thread_created", {
        "thread_id": thread_result["thread_id"],
        "post_id": post_id,
        "agent_id": agent_id,
    })

    # Create seed for thread creation
    thread_seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="thread",
            source_id=thread_result["thread_id"],
            creator_id=agent_id,
            creator_type="AAI",
            metadata={"post_id": post_id, "post_title": post.get("title", "")},
        )
        thread_seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass

    # Send magic link email to poster
    if poster_email:
        try:
            await send_magic_link(
                poster_name=poster_name,
                poster_email=poster_email,
                thread_id=thread_result["thread_id"],
                magic_token=thread_result["_magic_token_plain"],
                post_title=post.get("title", ""),
            )
        except Exception:
            pass

    # Notify operator
    try:
        await send_operator_alert(
            subject=f"New stake on '{post.get('title', post_id)}'",
            body=f"Agent {agent.get('name', agent_id)} staked on post {post_id}. Thread {thread_result['thread_id']} created.",
        )
    except Exception:
        pass

    return {
        "staked": True,
        "stake_id": stake_id,
        "post_id": post_id,
        "thread_id": thread_result["thread_id"],
        "magic_link": magic_link,
        "seed_doi": seed_doi,
        "thread_seed_doi": thread_seed_doi,
    }


@router.get("/api/kassa/posts/{post_id}/stakes")
async def get_post_stakes(post_id: str) -> list:
    """List active stakes on a post."""
    stakes = state.kassa.load_stakes(post_id=post_id)
    return [s for s in stakes if s.get("status") == "active"]


@router.delete("/api/kassa/stakes/{stake_id}")
async def withdraw_stake(stake_id: str, request: Request) -> dict:
    """Agent withdraws their stake."""
    agent = _get_agent_from_token(request)
    stakes = state.kassa.load_stakes()
    stake = next((s for s in stakes if s.get("stake_id") == stake_id), None)
    if not stake:
        raise HTTPException(status_code=404, detail="Stake not found")
    if stake.get("agent_id") != agent["agent_id"]:
        raise HTTPException(status_code=403, detail="Not your stake")
    state.kassa.update_stake(stake_id, {"status": "withdrawn"})

    state.audit.log("kassa", "stake_withdrawn", {"stake_id": stake_id, "agent_id": agent["agent_id"]})
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="stake_withdrawn",
            source_id=stake_id,
            creator_id=agent["agent_id"],
            creator_type="AAI",
            seed_type="planted",
            metadata={"stake_id": stake_id, "agent_id": agent["agent_id"]},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    return {"withdrawn": True, "stake_id": stake_id, "seed_doi": seed_doi}


# ═══════════════════════════════════════════════════════════════════════════════
# REFERRALS (agent cross-post matching, M1)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/api/kassa/referrals")
async def create_referral(request: Request, payload: dict) -> dict:
    """Agent connects two posts that match -- ISO<>Services, Bounty<>Hiring, etc."""
    agent = _get_agent_from_token(request)
    source_id = (payload.get("source_post_id") or "").strip()
    target_id = (payload.get("target_post_id") or "").strip()
    reason = (payload.get("reason") or "").strip()

    if not source_id or not target_id:
        raise HTTPException(status_code=400, detail="source_post_id and target_post_id required")
    if source_id == target_id:
        raise HTTPException(status_code=400, detail="Cannot refer a post to itself")

    source = state.kassa.get_post(source_id)
    target = state.kassa.get_post(target_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Source post {source_id} not found")
    if not target:
        raise HTTPException(status_code=404, detail=f"Target post {target_id} not found")

    # Check for duplicate referral
    referrals = state.kassa.load_referrals(agent_id=agent["agent_id"])
    dup = next((r for r in referrals if r.get("source_post_id") == source_id and r.get("target_post_id") == target_id and r.get("status") == "active"), None)
    if dup:
        raise HTTPException(status_code=409, detail="Referral already exists")

    ref_id = f"ref-{secrets.token_hex(6)}"
    entry = {
        "referral_id": ref_id,
        "agent_id": agent["agent_id"],
        "agent_name": agent.get("name"),
        "source_post_id": source_id,
        "target_post_id": target_id,
        "source_tab": source.get("tab"),
        "target_tab": target.get("tab"),
        "reason": reason,
        "status": "active",
        "created_at": datetime.now(UTC).isoformat(),
    }

    state.kassa.insert_referral(entry)

    state.audit.log("kassa", "referral_created", {
        "referral_id": ref_id,
        "agent_id": agent["agent_id"],
        "source": source_id,
        "target": target_id,
    })
    await state.emit("kassa_referral", entry)
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="kassa_referral",
            source_id=ref_id,
            creator_id=agent["agent_id"],
            creator_type="AAI",
            seed_type="planted",
            metadata={"referral_id": ref_id, "source_post_id": source_id, "target_post_id": target_id},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    return {"referred": True, "referral_id": ref_id, "source": source_id, "target": target_id, "seed_doi": seed_doi}


@router.get("/api/kassa/posts/{post_id}/referrals")
async def get_post_referrals(post_id: str) -> list:
    """List referrals involving a post (as source or target)."""
    referrals = state.kassa.load_referrals()
    return [r for r in referrals if (r.get("source_post_id") == post_id or r.get("target_post_id") == post_id) and r.get("status") == "active"]


@router.get("/api/kassa/agent/{agent_id}/referrals")
async def get_agent_referrals(agent_id: str) -> list:
    """List all referrals made by an agent."""
    referrals = state.kassa.load_referrals(agent_id=agent_id)
    return [r for r in referrals if r.get("status") == "active"]


# ═══════════════════════════════════════════════════════════════════════════════
# THREADS (M2)
# ═══════════════════════════════════════════════════════════════════════════════

def _create_thread(post_id: str, post_tab: str, post_title: str,
                   agent_id: str, agent_name: str,
                   poster_name: str, poster_email: str) -> dict:
    """Create a thread between a staked agent and the poster."""
    thread_id = f"thr-{secrets.token_hex(8)}"
    magic_token = secrets.token_urlsafe(32)
    entry = {
        "thread_id": thread_id,
        "post_id": post_id,
        "post_tab": post_tab,
        "post_title": post_title,
        "agent_id": agent_id,
        "agent_name": agent_name,
        "poster_name": poster_name,
        "poster_email": poster_email,
        "magic_token": _hash_key(magic_token),
        "status": "open",
        "message_count": 0,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    state.kassa.insert_thread(entry)
    # Return plain token for the initial magic link email only --
    # it is NOT stored in the DB (only the hash is persisted).
    return {**entry, "_magic_token_plain": magic_token}


@router.get("/api/kassa/threads")
async def get_agent_threads(request: Request) -> list:
    """List threads for the authenticated agent."""
    agent = _get_agent_from_token(request)
    threads = state.kassa.load_threads(agent_id=agent["agent_id"])
    return [t for t in threads if t.get("status") == "open"]


@router.get("/api/kassa/threads/{thread_id}")
async def get_thread(thread_id: str, request: Request, magic: str = "") -> dict:
    """Get thread details. Access via JWT (agent) or magic token (poster)."""
    thread = state.kassa.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Auth: either agent JWT or poster magic token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        claims = _verify_jwt(auth_header[7:])
        if not claims or claims.get("sub") != thread.get("agent_id"):
            raise HTTPException(status_code=403, detail="Not your thread")
    elif magic:
        if _hash_key(magic) != thread.get("magic_token"):
            raise HTTPException(status_code=403, detail="Invalid magic link")
    else:
        raise HTTPException(status_code=401, detail="Auth required -- use Bearer token or magic link")

    # Strip magic_token hash and plain token from response
    safe = {k: v for k, v in thread.items() if k not in ("magic_token", "magic_token_plain")}
    return safe


@router.get("/api/kassa/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: str, request: Request, magic: str = "") -> list:
    """Get messages in a thread. Auth via JWT or magic token."""
    thread = state.kassa.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        claims = _verify_jwt(auth_header[7:])
        if not claims or claims.get("sub") != thread.get("agent_id"):
            raise HTTPException(status_code=403, detail="Not your thread")
    elif magic:
        if _hash_key(magic) != thread.get("magic_token"):
            raise HTTPException(status_code=403, detail="Invalid magic link")
    else:
        raise HTTPException(status_code=401, detail="Auth required")

    return state.kassa.load_thread_messages(thread_id)


@router.post("/api/kassa/threads/{thread_id}/messages")
async def post_thread_message(thread_id: str, request: Request) -> dict:
    """Post a message to a thread. Auth via JWT (agent) or magic token (poster)."""
    thread = state.kassa.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread.get("status") != "open":
        raise HTTPException(status_code=403, detail="Thread is closed")

    payload = await request.json()
    text = (payload.get("text") or payload.get("body") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message text required")

    magic = request.query_params.get("magic", "")
    auth_header = request.headers.get("Authorization", "")
    sender_type = ""
    sender_name = ""

    if auth_header.startswith("Bearer "):
        claims = _verify_jwt(auth_header[7:])
        if not claims or claims.get("sub") != thread.get("agent_id"):
            raise HTTPException(status_code=403, detail="Not your thread")
        sender_type = "agent"
        sender_name = claims.get("name", thread.get("agent_name", "Agent"))
    elif magic:
        if _hash_key(magic) != thread.get("magic_token"):
            raise HTTPException(status_code=403, detail="Invalid magic link")
        sender_type = "poster"
        sender_name = thread.get("poster_name", "Poster")
    else:
        raise HTTPException(status_code=401, detail="Auth required")

    msg_id = f"msg-{secrets.token_hex(6)}"
    entry = {
        "msg_id": msg_id,
        "thread_id": thread_id,
        "sender_type": sender_type,
        "sender_name": sender_name,
        "text": text,
        "created_at": datetime.now(UTC).isoformat(),
    }
    state.kassa.insert_thread_message(entry)

    # Update thread timestamp and count
    new_count = thread.get("message_count", 0) + 1
    state.kassa.update_thread(thread_id, {
        "updated_at": datetime.now(UTC).isoformat(),
        "message_count": new_count,
    })

    # Broadcast to global WebSocket listeners
    await state.emit("kassa_thread_message", {
        "thread_id": thread_id,
        "post_id": thread.get("post_id"),
        "msg": entry,
    })

    # Broadcast to per-thread WebSocket listeners
    await state.thread_hub.broadcast(thread_id, {
        "type": "thread_message",
        "payload": entry,
    })

    # Create seed for message
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="message",
            source_id=msg_id,
            creator_id=sender_name,
            creator_type="AAI" if sender_type == "agent" else "BI",
            metadata={"thread_id": thread_id, "post_id": thread.get("post_id", "")},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass

    # Email notification to poster when agent sends a message.
    # Note: magic_token_plain is only available at thread creation time
    # (not stored in DB -- only the hash is persisted). The poster's
    # original magic link email is their access credential.
    if sender_type == "agent" and thread.get("poster_email"):
        # Look up agent's @signomy.xyz email for FROM address
        agent_email = None
        if agent:
            agent_email = agent.get("email")
        try:
            await send_message_notification(
                poster_email=thread["poster_email"],
                poster_name=thread.get("poster_name", ""),
                thread_id=thread_id,
                sender_name=sender_name,
                message_preview=text[:120],
                from_addr=agent_email,
            )
        except Exception:
            pass

    return {"sent": True, "msg_id": msg_id, "thread_id": thread_id, "seed_doi": seed_doi}


@router.get("/kassa/thread/{thread_id}")
async def kassa_thread_page(thread_id: str) -> FileResponse:
    """Serve the thread view page (magic link lands here)."""
    target = state.frontend_dir / "kassa-thread.html"
    if target.exists():
        return FileResponse(target)
    # Fallback: redirect to board if page not built yet
    return JSONResponse({"detail": "Thread page not yet built", "thread_id": thread_id}, status_code=404)


# ═══════════════════════════════════════════════════════════════════════════════
# KA$$A POSTS BOARD
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/api/kassa/posts")
async def get_kassa_posts(tab: str = "", status: str = "", sort: str = "recent") -> list:
    posts = state.kassa.load_posts(tab=tab, status=status)
    if not status:
        posts = [p for p in posts if p.get("status") != "closed"]
    if sort == "upvotes":
        posts.sort(key=lambda p: p.get("upvotes", 0), reverse=True)
    elif sort == "reward":
        posts.sort(key=lambda p: p.get("reward") or "", reverse=True)
    else:
        posts.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
    return posts


@router.get("/api/kassa/posts/{post_id}")
async def get_kassa_post(post_id: str) -> dict:
    post = state.kassa.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
    return post


@router.post("/api/kassa/posts")
async def submit_kassa_post(request: Request) -> dict:
    # Admin key bypasses rate limit (for seeding)
    if not (state.admin_key and request.headers.get("X-Admin-Key") == state.admin_key):
        _check_rate_limit(request, "kassa_posts", max_hits=5)
    payload = await request.json()
    tab = (payload.get("tab") or "").strip()
    title = (payload.get("title") or "").strip()
    tag = (payload.get("tag") or "").strip()
    body = (payload.get("body") or "").strip()
    urgency = (payload.get("urgency") or "normal").strip()
    reward = payload.get("reward")
    from_name = (payload.get("from_name") or "").strip()
    from_email = (payload.get("from_email") or "").strip()
    if not tab or not title or not body or not from_name or not from_email:
        raise HTTPException(status_code=400, detail="tab, title, body, from_name, from_email required")
    kid = state.kassa.next_k_serial()
    now = datetime.now(UTC).isoformat()
    review_entry = {
        "_v": 1,
        "review_id": f"rev-{kid}",
        "post": {
            "id": kid,
            "tab": tab,
            "title": title,
            "tag": tag,
            "body": body,
            "status": "open",
            "urgency": urgency,
            "upvotes": 0,
            "reply_count": 0,
            "reward": reward,
            "created_at": now,
            "updated_at": now,
        },
        "from_name": from_name,
        "from_email": from_email,
        "submitted_at": now,
        "status": "pending",
    }
    state.kassa.insert_review(review_entry)
    state.audit.log("kassa", "post_submitted", {"id": kid, "tab": tab, "from_email": from_email})
    await state.emit("kassa_post_submitted", {"id": kid, "tab": tab})

    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="kassa_post",
            source_id=kid,
            creator_id=from_email or from_name,
            creator_type="BI",
            seed_type="planted",
            metadata={"tab": tab, "title": title},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass

    return {"ok": True, "id": kid, "message": "Post submitted for review. We\u2019ll publish it shortly.", "seed_doi": seed_doi}


@router.post("/api/kassa/posts/{post_id}/upvote")
async def upvote_kassa_post(post_id: str) -> dict:
    post = state.kassa.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    new_count = state.kassa.increment_upvotes(post_id)
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="kassa_upvote",
            source_id=f"{post_id}-{new_count}",
            creator_id="anonymous",
            creator_type="BI",
            seed_type="planted",
            metadata={"post_id": post_id, "upvotes": new_count},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    return {"ok": True, "id": post_id, "upvotes": new_count, "seed_doi": seed_doi}


# ═══════════════════════════════════════════════════════════════════════════════
# OPERATOR REVIEW QUEUE
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/api/operator/reviews")
async def get_review_queue(request: Request, status: str = "pending") -> list:
    if state.admin_key and request.headers.get("X-Admin-Key") != state.admin_key:
        raise HTTPException(status_code=403, detail="Admin key required")
    return state.kassa.load_reviews(status=status)


@router.patch("/api/operator/reviews/{review_id}")
async def update_review(review_id: str, action: str, request: Request) -> dict:
    if state.admin_key and request.headers.get("X-Admin-Key") != state.admin_key:
        raise HTTPException(status_code=403, detail="Admin key required")
    r = state.kassa.get_review(review_id)
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    seed_doi = None
    if action == "approve":
        state.kassa.insert_post(r["post"])
        state.kassa.update_review(review_id, {"status": "approved"})
        r["status"] = "approved"
        state.audit.log("kassa", "post_approved", {"review_id": review_id, "post_id": r["post"]["id"]})
        try:
            seed_result = await create_seed(
                source_type="kassa_post_approved",
                source_id=review_id,
                creator_id="operator",
                creator_type="BI",
                seed_type="planted",
                metadata={"review_id": review_id, "post_id": r["post"]["id"]},
            )
            seed_doi = seed_result.get("doi") if seed_result else None
        except Exception:
            pass
    elif action == "reject":
        state.kassa.update_review(review_id, {"status": "rejected"})
        r["status"] = "rejected"
        state.audit.log("kassa", "post_rejected", {"review_id": review_id})
        try:
            seed_result = await create_seed(
                source_type="kassa_post_rejected",
                source_id=review_id,
                creator_id="operator",
                creator_type="BI",
                seed_type="planted",
                metadata={"review_id": review_id},
            )
            seed_doi = seed_result.get("doi") if seed_result else None
        except Exception:
            pass
    else:
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")
    await state.emit("review_updated", {"review_id": review_id, "status": r["status"]})
    r["seed_doi"] = seed_doi
    return r


# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCT REVIEWS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/api/kassa/product-reviews")
async def get_product_reviews(product_post_id: str = "", reviewer_id: str = "", status: str = "") -> list:
    return state.kassa.load_product_reviews(product_post_id=product_post_id, reviewer_id=reviewer_id, status=status)


@router.post("/api/kassa/product-reviews")
async def submit_product_review(request: Request) -> dict:
    """Agent submits a product review. Creates seed, tracks for reward."""
    body = await request.json()
    product_post_id = body.get("product_post_id", "")
    reviewer_id = body.get("reviewer_id", "")
    if not product_post_id or not reviewer_id:
        raise HTTPException(status_code=400, detail="product_post_id and reviewer_id required")
    post = state.kassa.get_post(product_post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Product post not found")
    review_id = f"PR-{secrets.token_hex(6)}"
    now = datetime.now(UTC).isoformat()
    seed_result = await create_seed(
        source_type="product_review",
        source_id=review_id,
        creator_id=reviewer_id,
        creator_type=body.get("reviewer_type", "AAI"),
        seed_type="grown",
        parent_doi=None,
        metadata={"product_post_id": product_post_id, "rating": body.get("rating", 0)},
    )
    review = {
        "review_id": review_id,
        "product_post_id": product_post_id,
        "reviewer_id": reviewer_id,
        "reviewer_name": body.get("reviewer_name"),
        "reviewer_type": body.get("reviewer_type", "AAI"),
        "rating": body.get("rating", 0),
        "body": body.get("body", ""),
        "status": "pending",
        "reward": body.get("reward"),
        "seed_doi": seed_result["doi"],
        "created_at": now,
    }
    state.kassa.insert_product_review(review)
    state.audit.log("kassa", "product_review_submitted", {"review_id": review_id, "product_post_id": product_post_id})
    await state.emit("product_review_submitted", {"review_id": review_id})
    return {"ok": True, "review_id": review_id, "seed_doi": seed_result["doi"]}


@router.patch("/api/kassa/product-reviews/{review_id}")
async def approve_product_review(review_id: str, request: Request) -> dict:
    """Operator approves/rejects a product review. On approve, reward flows."""
    if state.admin_key and request.headers.get("X-Admin-Key") != state.admin_key:
        raise HTTPException(status_code=403, detail="Admin key required")
    body = await request.json()
    action = body.get("action", "")
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")
    reviews = state.kassa.load_product_reviews()
    review = next((r for r in reviews if r["review_id"] == review_id), None)
    if not review:
        raise HTTPException(status_code=404, detail="Product review not found")
    state.kassa.update_product_review(review_id, {"status": "approved" if action == "approve" else "rejected"})
    if action == "approve" and review.get("reward"):
        # Pay the reviewer their reward
        try:
            reward_amount = float(review["reward"])
            if reward_amount > 0:
                state.economy.treasury.credit(review["reviewer_id"], reward_amount, reason="product_review_reward", mission_id=review_id)
        except (ValueError, TypeError):
            pass  # reward is a string like "$50 USDC" -- log but can't auto-credit
        state.audit.log("kassa", "product_review_reward", {"review_id": review_id, "reviewer_id": review["reviewer_id"], "reward": review["reward"]})
    state.audit.log("kassa", f"product_review_{action}d", {"review_id": review_id})
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="review_approved" if action == "approve" else "review_rejected",
            source_id=review_id,
            creator_id="operator",
            creator_type="BI",
            seed_type="planted",
            metadata={"review_id": review_id, "action": action},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    return {"ok": True, "review_id": review_id, "status": action + "d", "seed_doi": seed_doi}


# ═══════════════════════════════════════════════════════════════════════════════
# SALES COMMISSIONS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/api/kassa/commissions")
async def get_commissions(referrer_id: str = "", product_post_id: str = "") -> list:
    return state.kassa.load_commissions(referrer_id=referrer_id, product_post_id=product_post_id)


@router.post("/api/kassa/commissions")
async def record_commission(request: Request) -> dict:
    """Record a sales commission when a referred buyer purchases."""
    body = await request.json()
    referrer_id = body.get("referrer_id", "")
    buyer_id = body.get("buyer_id", "")
    product_post_id = body.get("product_post_id", "")
    purchase_amount = float(body.get("purchase_amount", 0))
    if not referrer_id or not buyer_id or not product_post_id:
        raise HTTPException(status_code=400, detail="referrer_id, buyer_id, product_post_id required")
    commission_id = f"COM-{secrets.token_hex(6)}"
    commission_rate = float(body.get("commission_rate", 0.05))
    commission_amount = round(purchase_amount * commission_rate, 4)
    now = datetime.now(UTC).isoformat()
    seed_result = await create_seed(
        source_type="commission",
        source_id=commission_id,
        creator_id=referrer_id,
        creator_type="AAI",
        seed_type="grown",
        parent_doi=body.get("referral_seed_doi"),
        metadata={"buyer_id": buyer_id, "product_post_id": product_post_id, "amount": commission_amount},
    )
    comm = {
        "commission_id": commission_id,
        "referrer_id": referrer_id,
        "referrer_name": body.get("referrer_name"),
        "buyer_id": buyer_id,
        "product_post_id": product_post_id,
        "purchase_amount": purchase_amount,
        "commission_rate": commission_rate,
        "commission_amount": commission_amount,
        "status": "pending",
        "seed_doi": seed_result["doi"],
        "created_at": now,
    }
    state.kassa.insert_commission(comm)

    # Pay the referrer their commission
    if commission_amount > 0:
        state.economy.treasury.credit(referrer_id, commission_amount, reason="sales_commission", mission_id=commission_id)

    state.audit.log("kassa", "commission_recorded", {"commission_id": commission_id, "referrer_id": referrer_id, "amount": commission_amount})
    await state.emit("commission_recorded", {"commission_id": commission_id})
    return {"ok": True, "commission_id": commission_id, "commission_amount": commission_amount, "seed_doi": seed_result["doi"]}


# ═══════════════════════════════════════════════════════════════════════════════
# RECRUITMENT REWARDS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/api/kassa/recruitments")
async def get_recruitments(recruiter_id: str = "", recruited_id: str = "") -> list:
    return state.kassa.load_recruitments(recruiter_id=recruiter_id, recruited_id=recruited_id)


@router.get("/api/kassa/recruitments/{recruiter_id}/stats")
async def get_recruiter_stats(recruiter_id: str) -> dict:
    return state.kassa.recruiter_stats(recruiter_id)


@router.post("/api/kassa/recruitments")
async def record_recruitment(request: Request) -> dict:
    """Record a recruitment event. BI recruitment pays more (2x multiplier)."""
    body = await request.json()
    recruiter_id = body.get("recruiter_id", "")
    recruited_id = body.get("recruited_id", "")
    if not recruiter_id or not recruited_id:
        raise HTTPException(status_code=400, detail="recruiter_id and recruited_id required")
    recruitment_id = f"REC-{secrets.token_hex(6)}"
    recruited_type = body.get("recruited_type", "AAI")
    # BI recruitment is harder and more valuable -- 2x multiplier
    multiplier = 2.0 if recruited_type == "BI" else 1.0
    base_exp = float(body.get("base_exp", 100))
    base_economic = float(body.get("base_economic", 10))
    reward_exp = round(base_exp * multiplier, 2)
    reward_economic = round(base_economic * multiplier, 4)
    now = datetime.now(UTC).isoformat()
    seed_result = await create_seed(
        source_type="recruitment",
        source_id=recruitment_id,
        creator_id=recruiter_id,
        creator_type="AAI",
        seed_type="planted",
        parent_doi=None,
        metadata={"recruited_id": recruited_id, "recruited_type": recruited_type, "multiplier": multiplier},
    )
    rec = {
        "recruitment_id": recruitment_id,
        "recruiter_id": recruiter_id,
        "recruiter_name": body.get("recruiter_name"),
        "recruited_id": recruited_id,
        "recruited_name": body.get("recruited_name"),
        "recruited_type": recruited_type,
        "reward_exp": reward_exp,
        "reward_economic": reward_economic,
        "multiplier": multiplier,
        "status": "active",
        "seed_doi": seed_result["doi"],
        "created_at": now,
    }
    state.kassa.insert_recruitment(rec)
    # Credit the recruiter's treasury
    state.economy.treasury.credit(recruiter_id, reward_economic, reason="recruitment_reward", mission_id=recruitment_id)
    state.audit.log("kassa", "recruitment_recorded", {
        "recruitment_id": recruitment_id, "recruiter_id": recruiter_id,
        "recruited_id": recruited_id, "recruited_type": recruited_type,
        "reward_exp": reward_exp, "reward_economic": reward_economic,
    })
    await state.emit("recruitment_recorded", {"recruitment_id": recruitment_id})
    return {
        "ok": True, "recruitment_id": recruitment_id,
        "reward_exp": reward_exp, "reward_economic": reward_economic,
        "multiplier": multiplier, "seed_doi": seed_result["doi"],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CONTACT INBOX
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/api/kassa/contact")
async def kassa_contact(payload: KassaContact) -> dict:
    entry = {
        "id": secrets.token_hex(8),
        "timestamp": datetime.now(UTC).isoformat(),
        "post_id": payload.post_id,
        "tab": payload.tab,
        "from_name": payload.from_name,
        "from_email": payload.from_email,
        "message": payload.message,
        "status": "new",
    }
    state.kassa.insert_contact_message(entry)
    state.audit.log("kassa", "contact_received", {
        "post_id": payload.post_id,
        "tab": payload.tab,
        "from_email": payload.from_email,
    })
    _send_notify_email(entry)
    await state.emit("kassa_contact", entry)
    return {"ok": True, "id": entry["id"]}


@router.get("/api/kassa/messages")
async def get_kassa_messages(tab: str = "", status: str = "") -> list:
    return state.kassa.load_contact_messages(tab=tab, status=status)
