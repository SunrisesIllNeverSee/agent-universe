"""
core.py — Core infrastructure endpoints for CIVITAE.

Extracted from server.py. Covers health, state, audit, hash, governance check,
messages, governance update, systems update, vault ops, fork session, deploy,
message starring/favorites, WebSocket endpoints, and MCP bridge endpoints.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time as _time
from datetime import datetime, timezone
from pathlib import Path

import jwt as pyjwt

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from app.deps import state
from app.metrics_io import atomic_write
from pydantic import BaseModel

from app.models import (
    DeployUpdate,
    GovernanceUpdate,
    MCPReadRequest,
    MCPSendRequest,
    MessageCreate,
    SystemUpdate,
    VaultSelection,
)
from app.seeds import create_seed


class GovernanceCheckPayload(BaseModel):
    action: str


class ForkSessionPayload(BaseModel):
    label: str = ""


class StarMessagePayload(BaseModel):
    id: int | str | None = None
    note: str = ""
    tag: str = "gold"


class UnstarMessagePayload(BaseModel):
    id: int | str | None = None


class McpJoinPayload(BaseModel):
    name: str

UTC = timezone.utc

router = APIRouter(tags=["core"])

# ── Boot time for uptime calculation ────────────────────────────────────────
_BOOT_TIME = _time.time()

# ── Reusable IP rate limiter ────────────────────────────────────────────────
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


# ── JWT / auth helpers (for thread WebSocket) ───────────────────────────────

def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _verify_jwt(token: str) -> dict | None:
    from app.jwt_config import verify_jwt
    return verify_jwt(token)


# ═══════════════════════════════════════════════════════════════════════════
#  HEALTH / STATE / AUDIT / HASH
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/health")
async def health() -> dict:
    return {
        "ok": True,
        "version": "0.9.0",
        "uptime_s": round(_time.time() - _BOOT_TIME),
        "ts": datetime.now(UTC).isoformat(),
    }


@router.get("/api/state")
async def get_state() -> dict:
    return state.runtime.snapshot().model_dump(mode="json")


@router.get("/api/audit")
async def get_audit() -> list[dict]:
    return [event.model_dump(mode="json") for event in state.audit.recent()]


@router.get("/api/hash")
async def get_hash() -> dict:
    runtime = state.runtime
    audit = state.audit
    snapshot = runtime.snapshot().model_dump(mode="json")
    messages = [message.model_dump(mode="json") for message in state.store.all()]
    systems = [
        {"name": config.name, "role": runtime.systems.get(config.id).role, "seq": runtime.systems.get(config.id).seq}
        for config in runtime.system_configs
        if config.id in runtime.systems and runtime.systems[config.id].active
    ]
    runtime_hashes = audit.hash_runtime_state(
        mode=runtime.governance.mode,
        posture=runtime.governance.posture,
        role=runtime.governance.role,
        vault_docs=runtime.vault.loaded,
        systems=systems,
    )
    return {
        "state_hash": runtime_hashes["hash_config"],
        "content_hash": audit.hash_payload(messages),
        "onchain_hash": runtime_hashes["hash_onchain"],
        "snapshot_hash": audit.hash_payload(snapshot),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  GOVERNANCE CHECK / UPDATE
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/api/governance/check")
async def check_governed_action(payload: GovernanceCheckPayload) -> dict:
    return state.runtime.check_action(payload.action)


@router.post("/api/governance")
async def update_governance(payload: GovernanceUpdate) -> dict:
    runtime = state.runtime
    audit = state.audit
    updated = runtime.update_governance(payload.model_dump())
    await state.emit("governance_updated", updated.model_dump(mode="json"))
    await state.emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
    return updated.model_dump(mode="json")


# ═══════════════════════════════════════════════════════════════════════════
#  MESSAGES
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/api/messages")
async def post_message(message: MessageCreate) -> dict:
    runtime = state.runtime
    audit = state.audit
    saved = runtime.create_message(message)
    await state.emit("message_added", saved.model_dump(mode="json"))
    await state.emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
    return saved.model_dump(mode="json")


# ═══════════════════════════════════════════════════════════════════════════
#  SYSTEMS UPDATE
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/api/systems")
async def update_system(payload: SystemUpdate) -> dict:
    runtime = state.runtime
    audit = state.audit
    updated = runtime.update_system(payload.system_id, payload.model_dump(exclude={"system_id"}))
    await state.emit(
        "systems_updated",
        {
            "systems": {system_id: system.model_dump(mode="json") for system_id, system in runtime.systems.items()},
            "sequence": state.router.sequence_map(runtime.systems),
        },
    )
    await state.emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
    return updated.model_dump(mode="json")


# ═══════════════════════════════════════════════════════════════════════════
#  VAULT — load / unload / upload / list files
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/api/vault/load")
async def load_context(payload: VaultSelection) -> dict:
    runtime = state.runtime
    audit = state.audit
    loaded = runtime.load_context(payload.file)
    await state.emit("vault_updated", {"loaded_context": loaded})
    await state.emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="vault_loaded",
            source_id=payload.file,
            creator_id="operator",
            creator_type="BI",
            seed_type="planted",
            metadata={"file": payload.file},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    return {"loaded_context": loaded, "seed_doi": seed_doi}


@router.post("/api/vault/unload")
async def unload_context(payload: VaultSelection) -> dict:
    runtime = state.runtime
    audit = state.audit
    loaded = runtime.unload_context(payload.file)
    await state.emit("vault_updated", {"loaded_context": loaded})
    await state.emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
    return {"loaded_context": loaded}


@router.post("/api/vault/upload")
async def upload_vault_file(
    file: UploadFile = File(...),
    category: str = Form("general"),
    filename: str = Form(""),
) -> dict:
    """Upload a file to the vault. Accepts .md, .txt, .pdf, .json. Max 50 MB."""
    runtime = state.runtime
    audit = state.audit
    root = state.root
    vault_files_dir = root / "vault"
    vault_files_dir.mkdir(parents=True, exist_ok=True)

    _MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
    # Check Content-Length header first (fast reject before reading body)
    content_length = int(file.headers.get("content-length", 0) or 0) if hasattr(file, "headers") else 0
    if content_length > _MAX_UPLOAD_BYTES:
        return JSONResponse({"error": f"File too large ({content_length} bytes). Max: 50 MB."}, status_code=413)
    name = filename or file.filename or "unnamed"
    # Sanitize filename
    safe_name = "".join(c for c in name if c.isalnum() or c in ".-_ ").strip()
    if not safe_name:
        safe_name = f"upload-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"

    # Sanitize category — alphanumeric + hyphens/underscores only, no path separators
    safe_category = "".join(c for c in category if c.isalnum() or c in "-_").strip() or "general"
    cat_dir = vault_files_dir / safe_category
    cat_dir.mkdir(parents=True, exist_ok=True)
    dest = cat_dir / safe_name
    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        return JSONResponse({"error": f"File too large ({len(content)} bytes). Max: 50 MB."}, status_code=413)
    dest.write_bytes(content)

    # Try to read as text for vault context
    text_content = ""
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError:
        text_content = f"[Binary file: {safe_name}, {len(content)} bytes]"

    # Add to vault manifest if not already present
    manifest = runtime.vault.manifest
    if category not in manifest:
        manifest[category] = []
    if safe_name not in manifest[category]:
        manifest[category].append(safe_name)

    # Auto-load the uploaded file
    loaded = runtime.load_context(safe_name)

    audit.log("vault", "file_uploaded", {
        "file": safe_name,
        "category": category,
        "size": len(content),
        "governance": {
            "mode": runtime.governance.mode,
            "posture": runtime.governance.posture,
            "role": runtime.governance.role,
        },
    })

    await state.emit("vault_updated", {"loaded_context": loaded})
    await state.emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="vault_upload",
            source_id=safe_name,
            creator_id="operator",
            creator_type="BI",
            seed_type="planted",
            metadata={"file": safe_name, "category": category, "size": len(content)},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    return {
        "uploaded": safe_name,
        "category": category,
        "size": len(content),
        "loaded_context": loaded,
        "seed_doi": seed_doi,
    }


@router.get("/api/vault/files")
async def list_vault_files() -> dict:
    """List all files in the vault directory."""
    vault_files_dir = state.root / "vault"
    files = {}
    if vault_files_dir.exists():
        for cat_dir in vault_files_dir.iterdir():
            if cat_dir.is_dir():
                files[cat_dir.name] = [f.name for f in cat_dir.iterdir() if f.is_file()]
    return {"vault_files": files}


# ═══════════════════════════════════════════════════════════════════════════
#  FORK SESSION
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/api/fork")
async def fork_session(payload: ForkSessionPayload | None = None) -> dict:
    """
    Fork the current session into a new branch.
    Snapshots governance, systems, vault, messages, and audit.
    Creates a new data directory with the snapshot as starting state.
    """
    runtime = state.runtime
    audit = state.audit
    root = state.root
    fork_label = (payload.label if payload and payload.label else "") or datetime.now(UTC).strftime("fork-%Y%m%d-%H%M%S")
    fork_dir = root / "forks" / fork_label
    fork_dir.mkdir(parents=True, exist_ok=True)

    # Snapshot current state
    snapshot = runtime.snapshot().model_dump(mode="json")

    # Copy data files
    data_dir = state.data_dir
    if data_dir.exists():
        fork_data = fork_dir / "data"
        shutil.copytree(data_dir, fork_data, dirs_exist_ok=True)

    # Write fork metadata
    fork_meta = {
        "forked_at": datetime.now(UTC).isoformat(),
        "label": fork_label,
        "source": "main",
        "governance_at_fork": {
            "mode": runtime.governance.mode,
            "posture": runtime.governance.posture,
            "role": runtime.governance.role,
        },
        "systems_at_fork": {sid: s.model_dump(mode="json") for sid, s in runtime.systems.items() if s.active},
        "loaded_context_at_fork": list(runtime.vault.loaded),
        "message_count": len(runtime.store.all()),
        "audit_count": len(audit.recent(100)),
    }
    (fork_dir / "fork_meta.json").write_text(json.dumps(fork_meta, indent=2))

    audit.log("session", "forked", {
        "label": fork_label,
        "path": str(fork_dir),
        "governance": {
            "mode": runtime.governance.mode,
            "posture": runtime.governance.posture,
            "role": runtime.governance.role,
        },
    })
    await state.emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))

    return {
        "forked": True,
        "label": fork_label,
        "path": str(fork_dir),
        "governance": fork_meta["governance_at_fork"],
        "message_count": fork_meta["message_count"],
    }


@router.get("/api/forks")
async def list_forks() -> dict:
    """List all session forks."""
    forks_dir = state.root / "forks"
    if not forks_dir.exists():
        return {"forks": []}
    forks = []
    for fork_dir in sorted(forks_dir.iterdir()):
        meta_path = fork_dir / "fork_meta.json"
        if meta_path.exists():
            forks.append(json.loads(meta_path.read_text()))
    return {"forks": forks}


# ═══════════════════════════════════════════════════════════════════════════
#  DEPLOY UPDATE
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/api/deploy")
async def update_deploy(payload: DeployUpdate) -> dict:
    runtime = state.runtime
    audit = state.audit
    updated = runtime.update_deploy(payload.model_dump())
    await state.emit("deploy_updated", updated.model_dump(mode="json"))
    await state.emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
    return updated.model_dump(mode="json")


# ═══════════════════════════════════════════════════════════════════════════
#  MESSAGE STARRING / FAVORITES
# ═══════════════════════════════════════════════════════════════════════════

def _stars_path() -> Path:
    return state.data_path("starred.json")


def _load_stars() -> list[dict]:
    p = _stars_path()
    if p.exists():
        return json.loads(p.read_text())
    return []


def _save_stars(stars: list[dict]):
    atomic_write(_stars_path(), json.dumps(stars, indent=2))


@router.post("/api/messages/star")
async def star_message(payload: StarMessagePayload) -> dict:
    """Star/favorite a message by ID with optional note and tag."""
    runtime = state.runtime
    audit = state.audit
    store = state.store
    root = state.root
    msg_id = payload.id
    note = payload.note
    tag = payload.tag
    if msg_id is None:
        return JSONResponse({"error": "id required"}, status_code=400)

    # Find the message
    msg = next((m for m in store.all() if m.id == msg_id), None)
    if not msg:
        return JSONResponse({"error": f"Message {msg_id} not found"}, status_code=404)

    stars = _load_stars()
    # Remove existing star for this ID if present
    stars = [s for s in stars if s.get("id") != msg_id]
    star_entry = {
        "id": msg_id,
        "sender": msg.sender,
        "text": msg.text,
        "timestamp": msg.timestamp.isoformat(),
        "governance": msg.governance.model_dump(mode="json"),
        "vault_loaded": msg.vault_loaded,
        "starred_at": datetime.now(UTC).isoformat(),
        "note": note,
        "tag": tag,
    }
    stars.append(star_entry)
    _save_stars(stars)

    # Save starred message as vault document — atomic context drop
    vault_files_dir = root / "vault"
    starred_vault_dir = vault_files_dir / "starred"
    starred_vault_dir.mkdir(parents=True, exist_ok=True)
    doc_name = f"star-{msg_id}-{tag}.md"
    doc_content = (
        f"# Starred Message #{msg_id} [{tag.upper()}]\n\n"
        f"**Sender:** {msg.sender}\n"
        f"**Time:** {msg.timestamp.isoformat()}\n"
        f"**Mode:** {msg.governance.mode}\n"
        f"**Posture:** {msg.governance.posture}\n"
    )
    if note:
        doc_content += f"**Note:** {note}\n"
    doc_content += f"\n---\n\n{msg.text}\n"
    if msg.vault_loaded:
        doc_content += f"\n---\n**Context at time:** {', '.join(msg.vault_loaded)}\n"

    (starred_vault_dir / doc_name).write_text(doc_content)

    # Add to vault manifest
    manifest = runtime.vault.manifest
    if "starred" not in manifest:
        manifest["starred"] = []
    if doc_name not in manifest["starred"]:
        manifest["starred"].append(doc_name)

    # Auto-load into active context
    loaded = runtime.load_context(doc_name)

    audit.log("messages", "starred", {
        "message_id": msg_id,
        "tag": tag,
        "vault_doc": doc_name,
        "governance": {
            "mode": runtime.governance.mode,
            "posture": runtime.governance.posture,
            "role": runtime.governance.role,
        },
    })
    await state.emit("vault_updated", {"loaded_context": loaded})
    await state.emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
    return {"starred": True, "entry": star_entry, "vault_doc": doc_name, "loaded_context": loaded}


@router.post("/api/messages/unstar")
async def unstar_message(payload: UnstarMessagePayload) -> dict:
    """Remove star from a message."""
    msg_id = payload.id
    stars = _load_stars()
    stars = [s for s in stars if s.get("id") != msg_id]
    _save_stars(stars)
    return {"unstarred": True, "id": msg_id}


@router.get("/api/messages/starred")
async def get_starred() -> dict:
    """Get all starred messages."""
    return {"starred": _load_stars()}


# ═══════════════════════════════════════════════════════════════════════════
#  MCP BRIDGE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/api/mcp/status")
async def mcp_status() -> dict:
    return state.mcp_bridge.chat_status()


@router.post("/api/mcp/join")
async def mcp_join(payload: McpJoinPayload) -> dict:
    runtime = state.runtime
    audit = state.audit
    joined = state.mcp_bridge.chat_join(payload.name)
    await state.emit("presence_updated", {"presence": runtime.presence, "joined": joined})
    await state.emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
    return joined


@router.post("/api/mcp/read")
async def mcp_read(payload: MCPReadRequest) -> dict:
    return state.mcp_bridge.chat_read(
        payload.name,
        channel=payload.channel,
        since_id=payload.since_id or None,
        limit=payload.limit,
    )


@router.post("/api/mcp/send")
async def mcp_send(payload: MCPSendRequest) -> dict:
    audit = state.audit
    saved = state.mcp_bridge.chat_send(
        payload.sender,
        payload.message,
        channel=payload.channel,
        systems=payload.systems,
    )
    await state.emit("message_added", saved)
    await state.emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
    return saved


# ═══════════════════════════════════════════════════════════════════════════
#  WEBSOCKET — Connection rate limiter
# ═══════════════════════════════════════════════════════════════════════════

_ws_connect_times: dict[str, list[float]] = {}
_WS_MAX_CONNECTIONS_PER_MIN = 10


def _ws_rate_check(websocket: WebSocket) -> bool:
    """Return True if the connection should be rejected (rate exceeded)."""
    client = websocket.client
    ip = client.host if client else "unknown"
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16]
    now = _time.time()
    recent = [t for t in _ws_connect_times.get(ip_hash, []) if now - t < 60]
    if len(recent) >= _WS_MAX_CONNECTIONS_PER_MIN:
        return True
    recent.append(now)
    _ws_connect_times[ip_hash] = recent
    return False


# ═══════════════════════════════════════════════════════════════════════════
#  WEBSOCKET — Main governance WebSocket
# ═══════════════════════════════════════════════════════════════════════════

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Main governance WebSocket — the public square.

    Open by design. The security model is constitutional governance +
    cryptographic verification, not access control. Any agent can join
    by verifying lineage. Any agent can be excluded by failing the check.
    The structure itself refuses you — nobody blocks you.

    Rate-limited to prevent connection flooding.
    """
    if _ws_rate_check(websocket):
        await websocket.close(code=4029, reason="Too many connections")
        return

    hub = state.hub
    runtime = state.runtime
    audit = state.audit
    mcp_bridge = state.mcp_bridge
    await hub.connect(websocket)
    await websocket.send_json(state.current_state_event())
    try:
        while True:
            payload = await websocket.receive_json()
            action = payload.get("action")
            if action == "ping":
                await websocket.send_json({"type": "pong", "payload": {}})
            elif action == "chat_send":
                saved = runtime.create_message(MessageCreate.model_validate(payload["payload"]))
                await state.emit("message_added", saved.model_dump(mode="json"))
                await state.emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
            elif action == "agent_join":
                joined = runtime.join_agent(payload["payload"]["name"])
                await state.emit("presence_updated", {"presence": runtime.presence, "joined": joined})
                await state.emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
            elif action == "mcp_read":
                result = mcp_bridge.chat_read(
                    payload["payload"]["name"],
                    channel=payload["payload"].get("channel", "general"),
                    since_id=payload["payload"].get("since_id"),
                    limit=payload["payload"].get("limit", 20),
                )
                await websocket.send_json({"type": "mcp_read_result", "payload": result})
            else:
                await websocket.send_json({"type": "error", "payload": {"message": f"Unknown action: {action}"}})
    except WebSocketDisconnect:
        hub.disconnect(websocket)


# ═══════════════════════════════════════════════════════════════════════════
#  WEBSOCKET — Public read-only feed (no auth, rate-limited)
# ═══════════════════════════════════════════════════════════════════════════

@router.websocket("/ws/public")
async def public_websocket_endpoint(websocket: WebSocket) -> None:
    """Read-only WebSocket for public pages (world, missions, index).

    Receives state_snapshot and event broadcasts but cannot send commands.
    No auth required — this is the public-facing governance feed.
    """
    if _ws_rate_check(websocket):
        await websocket.close(code=4029, reason="Too many connections")
        return

    public_hub = state.public_hub
    await public_hub.connect(websocket)
    await websocket.send_json(state.current_state_event())
    try:
        while True:
            payload = await websocket.receive_json()
            action = payload.get("action")
            if action == "ping":
                await websocket.send_json({"type": "pong", "payload": {}})
            else:
                # Public feed is read-only — reject all commands
                await websocket.send_json({"type": "error", "payload": {"message": "Read-only connection"}})
    except WebSocketDisconnect:
        public_hub.disconnect(websocket)


# ═══════════════════════════════════════════════════════════════════════════
#  WEBSOCKET — Per-Thread WebSocket
# ═══════════════════════════════════════════════════════════════════════════

@router.websocket("/ws/thread/{thread_id}")
async def thread_websocket(thread_id: str, websocket: WebSocket) -> None:
    """Per-thread WebSocket for real-time messaging. Auth via query param."""
    if _ws_rate_check(websocket):
        await websocket.close(code=4029, reason="Too many connections")
        return

    kassa = state.kassa
    thread_hub = state.thread_hub

    # Auth: ?token=JWT or ?magic=MAGIC_TOKEN
    params = websocket.query_params
    jwt_token = params.get("token", "")
    magic = params.get("magic", "")

    thread = kassa.get_thread(thread_id)
    if not thread:
        await websocket.close(code=4004, reason="Thread not found")
        return

    # Verify access
    if jwt_token:
        claims = _verify_jwt(jwt_token)
        if not claims or claims.get("sub") != thread.get("agent_id"):
            await websocket.close(code=4003, reason="Not your thread")
            return
    elif magic:
        if _hash_key(magic) != thread.get("magic_token"):
            await websocket.close(code=4003, reason="Invalid magic link")
            return
    else:
        await websocket.close(code=4001, reason="Auth required")
        return

    await thread_hub.connect(thread_id, websocket)
    # Send current thread info on connect
    safe_thread = {k: v for k, v in thread.items() if k not in ("magic_token", "magic_token_plain")}
    await websocket.send_json({"type": "thread_info", "payload": safe_thread})
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            if action == "ping":
                await websocket.send_json({"type": "pong", "payload": {}})
            elif action == "typing":
                # Broadcast typing indicator to other participants
                await thread_hub.broadcast(thread_id, {
                    "type": "typing",
                    "payload": {"sender": data.get("sender", "")},
                })
    except WebSocketDisconnect:
        thread_hub.disconnect(thread_id, websocket)
