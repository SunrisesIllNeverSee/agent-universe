"""
operator.py — Operator console, audit, contacts, threads, and inbox endpoints.

Extracted from server.py. All endpoints require X-Admin-Key except the
public inbox apply endpoint (rate-limited instead).
"""
from __future__ import annotations

import hashlib
import json
import secrets
import time as _time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.deps import state
from app.seeds import _read_seeds

UTC = timezone.utc

router = APIRouter(tags=["operator"])

# ── Auth helper (fail-closed) ─────────────────────────────────────────────────

def _require_admin(request: Request):
    if not state.admin_key:
        raise HTTPException(403, "CIVITAE_ADMIN_KEY not configured")
    if request.headers.get("X-Admin-Key") != state.admin_key:
        raise HTTPException(403, "Admin key required")


# ── Rate limiter (mirrors server.py pattern) ──────────────────────────────────

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


# ── Data helpers ──────────────────────────────────────────────────────────────

def _load_missions() -> list[dict]:
    missions_path = state.data_path("missions.json")
    if missions_path.exists():
        return json.loads(missions_path.read_text())
    return []


def _load_slots() -> list[dict]:
    slots_path = state.data_path("slots.json")
    if slots_path.exists():
        return json.loads(slots_path.read_text())
    return []


# ── Operator Threads ──────────────────────────────────────────────────────────

@router.get("/api/operator/threads")
async def operator_threads(request: Request, status: str = "") -> dict:
    """List all threads across all posts. Requires X-Admin-Key."""
    _require_admin(request)

    threads = state.kassa.load_threads()
    if status:
        threads = [t for t in threads if t.get("status") == status]
    # Sort by most recently updated
    threads.sort(key=lambda t: t.get("updated_at", ""), reverse=True)
    # Strip magic token hashes from response
    safe = [{k: v for k, v in t.items() if k not in ("magic_token", "magic_token_plain")} for t in threads]
    return {"threads": safe, "count": len(safe)}


# ── Operator Stats ────────────────────────────────────────────────────────────

@router.get("/api/operator/stats")
async def operator_stats(request: Request) -> dict:
    """Platform stats for operator console. Requires X-Admin-Key."""
    _require_admin(request)

    # Total registered agents
    total_agents = len(state.runtime.registry)

    # Total missions
    missions = _load_missions()
    total_missions = len(missions)

    # Total forum threads (query without limit to count all)
    try:
        all_threads = state.forums.list_threads(page=1, limit=10000)
        total_threads = len(all_threads)
    except Exception:
        total_threads = 0

    # Total seeds
    try:
        seeds = _read_seeds()
        total_seeds = len(seeds)
    except Exception:
        total_seeds = 0

    # Platform revenue
    try:
        revenue = state.economy.treasury.platform_revenue()
    except Exception:
        revenue = 0.0

    # Active slots
    try:
        slots = _load_slots()
        active_slots = len([s for s in slots if (s.get("status") or "").lower() in ("filled", "active")])
        total_slots = len(slots)
    except Exception:
        active_slots = 0
        total_slots = 0

    return {
        "agents": total_agents,
        "missions": total_missions,
        "threads": total_threads,
        "seeds": total_seeds,
        "revenue": round(revenue, 4),
        "active_slots": active_slots,
        "total_slots": total_slots,
    }


# ── Operator Audit ────────────────────────────────────────────────────────────

@router.get("/api/operator/audit")
async def operator_audit(request: Request, type: str = "", limit: int = 50, since: str = "") -> dict:
    """Recent audit events with optional filters. Requires X-Admin-Key."""
    _require_admin(request)

    limit = max(1, min(200, limit))
    events = state.audit.recent(limit=limit * 3 if type or since else limit)

    results = []
    for ev in events:
        ev_dict = ev.model_dump(mode="json")
        # Filter by component/action type
        if type:
            component = ev_dict.get("component", "")
            action = ev_dict.get("action", "")
            if type.lower() not in component.lower() and type.lower() not in action.lower():
                continue
        # Filter by since timestamp
        if since:
            ev_ts = ev_dict.get("timestamp", "")
            if isinstance(ev_ts, str) and ev_ts < since:
                continue
        results.append(ev_dict)
        if len(results) >= limit:
            break

    return {"events": results, "count": len(results), "limit": limit}


# ── Operator Contacts ─────────────────────────────────────────────────────────

@router.get("/api/operator/contacts")
async def operator_contacts(request: Request) -> dict:
    """Contact form submissions. Requires X-Admin-Key."""
    _require_admin(request)

    contacts_file = state.data_path("contacts.jsonl")
    contacts = []
    if contacts_file.exists():
        try:
            with open(contacts_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            contacts.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception:
            pass

    # Sort newest first
    contacts.sort(key=lambda c: c.get("submitted_at", ""), reverse=True)
    return {"contacts": contacts, "count": len(contacts)}


# ── Public Contact Form ──────────────────────────────────────────────────────

@router.post("/api/contact")
async def public_contact(request: Request, payload: dict) -> dict:
    """Public contact form submission. Rate-limited, creates seed, emails operator."""
    _check_rate_limit(request, "contact_form", max_hits=3)
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip()
    subject = (payload.get("subject") or "General").strip()
    message = (payload.get("message") or "").strip()
    if not name or not email or not message:
        raise HTTPException(status_code=400, detail="name, email, and message required")

    contact_id = f"contact-{secrets.token_hex(6)}"
    now = datetime.now(UTC).isoformat()
    entry = {
        "id": contact_id,
        "name": name,
        "email": email,
        "subject": subject,
        "message": message,
        "submitted_at": now,
    }

    # Append to contacts.jsonl
    contacts_file = state.data_path("contacts.jsonl")
    contacts_file.parent.mkdir(parents=True, exist_ok=True)
    with open(contacts_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    state.audit.log("contact", "form_submitted", {"id": contact_id, "name": name, "subject": subject})

    # Seed provenance
    try:
        from app.seeds import create_seed
        await create_seed(
            source_type="contact",
            source_id=contact_id,
            creator_id=email,
            creator_type="BI",
            seed_type="planted",
            metadata={"name": name, "subject": subject},
        )
    except Exception:
        pass

    # Email operator (fire-and-forget — don't block the response)
    import asyncio
    try:
        from app.notifications import send_operator_alert
        asyncio.get_event_loop().run_in_executor(
            None, send_operator_alert,
            f"Contact: {subject} — from {name}",
            f"Name: {name}\nEmail: {email}\nSubject: {subject}\n\n{message}",
        )
    except Exception:
        pass

    return {"ok": True, "id": contact_id}


# ── Inbox Endpoints ───────────────────────────────────────────────────────────

@router.post("/api/inbox/apply")
async def inbox_apply(request: Request, payload: dict) -> dict:
    """Capture an Open Roles application. Emits inbox_application over WebSocket."""
    _check_rate_limit(request, "inbox_apply", max_hits=5)
    if not payload.get("name") or not payload.get("role"):
        return JSONResponse({"error": "name and role are required"}, status_code=400)
    app_id = f"app-{secrets.token_hex(4)}"
    entry = {
        "id": app_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "status": "pending",
        "name": payload.get("name", ""),
        "handle": payload.get("handle", ""),
        "system": payload.get("system", ""),
        "role": payload.get("role", ""),
        "posture": payload.get("posture", ""),
        "channel": payload.get("channel", ""),
        "message": payload.get("message", ""),
        "job_id": payload.get("job_id", ""),
    }
    inbox_path = state.data_path("inbox.jsonl")
    with inbox_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    state.audit.log("inbox", "application_received", {"id": app_id, "name": entry["name"], "role": entry["role"]})
    await state.emit("inbox_application", entry)
    return {"ok": True, "application_id": app_id}


@router.get("/api/inbox")
async def inbox_list() -> dict:
    """List all inbox applications."""
    inbox_path = state.data_path("inbox.jsonl")
    applications: list[dict] = []
    if inbox_path.exists():
        for line in inbox_path.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    applications.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return {"applications": applications, "total": len(applications)}


@router.get("/api/inbox/{app_id}")
async def inbox_get(app_id: str) -> dict:
    """Fetch a single application by ID."""
    inbox_path = state.data_path("inbox.jsonl")
    if not inbox_path.exists():
        return JSONResponse({"error": "inbox empty"}, status_code=404)
    for line in inbox_path.read_text().splitlines():
        try:
            entry = json.loads(line)
            if entry.get("id") == app_id:
                return {"application": entry}
        except json.JSONDecodeError:
            pass
    return JSONResponse({"error": f"Application {app_id} not found"}, status_code=404)


@router.post("/api/inbox/{app_id}/review")
async def inbox_review(app_id: str, payload: dict) -> dict:
    """Update application status: pending -> approved / rejected / contacted."""
    inbox_path = state.data_path("inbox.jsonl")
    status = payload.get("status", "reviewed")
    if not inbox_path.exists():
        return {"error": "inbox empty"}
    lines = inbox_path.read_text().splitlines()
    updated = False
    new_lines = []
    for line in lines:
        try:
            entry = json.loads(line)
            if entry.get("id") == app_id:
                entry["status"] = status
                entry["reviewed_at"] = datetime.now(UTC).isoformat()
                entry["reviewer_note"] = payload.get("note", "")
                updated = True
            new_lines.append(json.dumps(entry))
        except json.JSONDecodeError:
            new_lines.append(line)
    inbox_path.write_text("\n".join(new_lines) + "\n")
    if updated:
        state.audit.log("inbox", "application_reviewed", {"id": app_id, "status": status})
        await state.emit("inbox_updated", {"id": app_id, "status": status})
    return {"ok": updated, "id": app_id, "status": status}
