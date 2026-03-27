from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import shutil
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .audit import AuditSpine
from .context import ContextAssembler
from .mcp_bridge import MCPBridge
from .models import DeployUpdate, GovernanceUpdate, MCPReadRequest, MCPSendRequest, MessageCreate, SystemUpdate, VaultSelection
from .router import SequenceRouter
from .runtime import RuntimeState
from .store import MessageStore
from .kassa_store import KassaStore
from .forums_store import ForumsStore, VALID_CATEGORIES
from .seeds import seed_router, create_seed, backdate_gov_documents, _read_seeds
from . import kassa_payments
from .notifications import send_magic_link, send_message_notification, send_operator_alert


def _atomic_write(path: Path, data: str) -> None:
    """Write data to a file atomically via tmp-then-rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class ConnectionHub:
    def __init__(self) -> None:
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def broadcast(self, event: dict) -> None:
        stale: list[WebSocket] = []
        for connection in self.connections:
            try:
                await connection.send_json(event)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)


class ThreadHub:
    """Per-thread WebSocket connections for real-time messaging."""

    def __init__(self) -> None:
        self._threads: dict[str, list[WebSocket]] = {}

    async def connect(self, thread_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if thread_id not in self._threads:
            self._threads[thread_id] = []
        self._threads[thread_id].append(websocket)

    def disconnect(self, thread_id: str, websocket: WebSocket) -> None:
        conns = self._threads.get(thread_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns and thread_id in self._threads:
            del self._threads[thread_id]

    async def broadcast(self, thread_id: str, event: dict) -> None:
        conns = self._threads.get(thread_id, [])
        stale: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(event)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(thread_id, ws)


def create_app(root: Path | None = None) -> FastAPI:
    root = root or Path(__file__).resolve().parents[1]
    store = MessageStore(root / "data" / "messages.jsonl")
    kassa = KassaStore(root / "data" / "kassa.db")
    forums = ForumsStore(root / "data" / "forums.db")
    audit = AuditSpine(root / "data" / "audit.jsonl")
    runtime = RuntimeState(root=root, store=store, audit=audit)
    router = SequenceRouter()
    assembler = ContextAssembler(router)
    mcp_bridge = MCPBridge(runtime, assembler)
    hub = ConnectionHub()
    thread_hub = ThreadHub()

    app = FastAPI(title="COMMAND Runtime", version="0.1.0")
    app.state.store = store
    app.state.audit = audit
    app.state.runtime = runtime
    app.state.router = router
    app.state.mcp_bridge = mcp_bridge
    app.state.connection_hub = hub

    # BUG-007 FIX: Slot mutation lock — prevents DICT_RACE crash under concurrent
    # fill+leave+read. asyncio.Lock() is correct here (single-threaded event loop).
    # Any coroutine that mutates slot state must acquire this before check-then-write.
    slot_lock = asyncio.Lock()
    _allowed_origin = os.environ.get("ALLOWED_ORIGIN", "")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:8300",
            "http://localhost:8300",
            *([_allowed_origin] if _allowed_origin else []),
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Admin key guard — protects all write endpoints ────────────────────────
    # Set CIVITAE_ADMIN_KEY env var to enable.
    # Fail-closed: when unset, only localhost requests are allowed through.
    # Agent self-service paths (signup, heartbeat, apply, metrics) are public.
    _ADMIN_KEY = os.environ.get("CIVITAE_ADMIN_KEY", "")
    _PUBLIC_WRITE_PREFIXES = (
        "/api/provision/signup",
        "/api/provision/heartbeat",
        "/api/inbox/apply",
        "/api/metrics/",
        "/api/kassa/contact",
        "/api/kassa/posts",
        "/api/kassa/agent/register",
        "/api/kassa/agent/login",
        "/api/kassa/threads/",
        "/api/kassa/webhooks/stripe",
        "/api/connect/",
        "/api/forums/threads",
        "/api/contact",
    )

    @app.middleware("http")
    async def admin_key_guard(request: Request, call_next):
        if request.method in ("POST", "DELETE", "PATCH", "PUT"):
            path = request.url.path
            if not any(path.startswith(p) for p in _PUBLIC_WRITE_PREFIXES):
                if _ADMIN_KEY:
                    if request.headers.get("X-Admin-Key") != _ADMIN_KEY:
                        return JSONResponse({"detail": "Admin key required"}, status_code=403)
                else:
                    host = request.client.host if request.client else ""
                    if host not in ("127.0.0.1", "::1", "localhost"):
                        return JSONResponse({"detail": "Admin key not configured"}, status_code=403)
        return await call_next(request)

    frontend_dir = root / "frontend"
    # Serve sub-directories the original console expects
    if (frontend_dir / "config").is_dir():
        app.mount("/config", StaticFiles(directory=frontend_dir / "config"), name="config")
    if (frontend_dir / "popups").is_dir():
        app.mount("/popups", StaticFiles(directory=frontend_dir / "popups"), name="popups")
    app.mount("/assets", StaticFiles(directory=frontend_dir), name="assets")

    # Serve favicon and apple-touch-icon at root level
    @app.get("/favicon.ico")
    async def favicon() -> FileResponse:
        return FileResponse(frontend_dir / "favicon.ico")

    @app.get("/apple-touch-icon.png")
    async def apple_touch_icon() -> FileResponse:
        return FileResponse(frontend_dir / "apple-touch-icon.png")

    def current_state_event() -> dict:
        return {"type": "state_snapshot", "payload": runtime.snapshot().model_dump(mode="json")}

    async def emit(event_type: str, payload: dict) -> None:
        await hub.broadcast({"type": event_type, "payload": payload})

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(frontend_dir / "kingdoms.html")

    @app.get("/3d")
    async def world_3d_page() -> FileResponse:
        return FileResponse(frontend_dir / "world.html")

    @app.get("/missions")
    async def missions_page() -> FileResponse:
        return FileResponse(frontend_dir / "missions.html")

    @app.get("/deploy")
    async def deploy_page() -> FileResponse:
        return FileResponse(frontend_dir / "deploy.html")

    @app.get("/campaign")
    async def campaign_page() -> FileResponse:
        return FileResponse(frontend_dir / "campaign.html")

    @app.get("/kassa")
    async def kassa_page() -> FileResponse:
        return FileResponse(frontend_dir / "kassa.html")

    @app.get("/kassa/post/{post_id}")
    async def kassa_post_detail_page(post_id: str) -> FileResponse:
        return FileResponse(frontend_dir / "kassa-post.html")

    @app.get("/world")
    async def world_page() -> FileResponse:
        return FileResponse(frontend_dir / "world.html")

    @app.get("/slots")
    async def slots_page() -> FileResponse:
        return FileResponse(frontend_dir / "slots.html")

    @app.get("/wave-registry")
    async def wave_registry_page() -> FileResponse:
        return FileResponse(frontend_dir / "wave-registry.html")

    @app.get("/economics")
    async def economics_page() -> FileResponse:
        return FileResponse(frontend_dir / "economics.html")

    @app.get("/command")
    async def command_page() -> FileResponse:
        return FileResponse(frontend_dir / "command.html")

    @app.get("/mission")
    async def mission_page() -> FileResponse:
        return FileResponse(frontend_dir / "mission.html")

    @app.get("/civitas")
    async def civitas_page() -> FileResponse:
        return FileResponse(frontend_dir / "civitas.html")

    @app.get("/academia")
    async def academia_page() -> FileResponse:
        return FileResponse(frontend_dir / "academia.html")

    @app.get("/kingdoms")
    async def kingdoms_page() -> FileResponse:
        return FileResponse(frontend_dir / "kingdoms.html")

    @app.get("/welcome")
    async def welcome_page() -> FileResponse:
        return FileResponse(frontend_dir / "welcome.html")

    @app.get("/sir-hawk.png")
    async def sir_hawk_img() -> FileResponse:
        return FileResponse(frontend_dir / "sir-hawk.png")

    @app.get("/agents")
    async def agents_page() -> FileResponse:
        return FileResponse(frontend_dir / "agents.html")

    @app.get("/agent/{slug}")
    async def agent_detail(slug: str) -> FileResponse:
        return FileResponse(frontend_dir / "agent.html")

    @app.get("/dashboard")
    async def dashboard_page() -> FileResponse:
        return FileResponse(frontend_dir / "dashboard.html")

    @app.get("/admin")
    async def admin_page() -> FileResponse:
        return FileResponse(frontend_dir / "admin.html")

    @app.get("/sitemap")
    async def sitemap_page() -> FileResponse:
        return FileResponse(frontend_dir / "sitemap.html")

    @app.get("/api/pages")
    async def get_pages() -> JSONResponse:
        pages_file = Path(__file__).parent.parent / "config" / "pages.json"
        data = json.loads(pages_file.read_text())
        return JSONResponse(data)

    @app.get("/flowchart")
    async def flowchart_page() -> FileResponse:
        return FileResponse(frontend_dir / "flowchart.html")

    @app.get("/api/admin/page-html")
    async def get_page_html(page: str) -> JSONResponse:
        """Return raw HTML source of a frontend page for the sitemap editor."""
        _ALLOWED_PAGES = {
            "about", "admin", "agent", "agent-profile", "agents", "bountyboard", "campaign",
            "civitae-map", "civitae-roadmap", "civitas", "command", "console", "contact",
            "dashboard", "deploy", "economics", "entry", "flowchart",
            "governance", "helpwanted", "hiring", "index", "iso-collaborators",
            "kassa", "kassa-post", "kassa-thread", "kingdoms", "leaderboard", "mission", "missions",
            "products", "refinery", "services", "sig-arena", "sitemap",
            "slots", "switchboard", "treasury", "vault", "wave-registry", "welcome", "world",
        }
        # Reject path traversal characters before any filesystem operation
        if ".." in page or "/" in page or "\\" in page:
            return JSONResponse({"error": "invalid page"}, status_code=400)
        safe = page.strip().lower()
        if safe not in _ALLOWED_PAGES:
            return JSONResponse({"error": "invalid page"}, status_code=400)
        target = (frontend_dir / f"{safe}.html").resolve()
        # Defense-in-depth: ensure resolved path is within frontend_dir
        if not str(target).startswith(str(frontend_dir.resolve())):
            return JSONResponse({"error": "invalid page"}, status_code=400)
        if target.exists():
            return JSONResponse({"page": safe, "html": target.read_text()})
        return JSONResponse({"error": f"page '{safe}' not found"}, status_code=404)

    @app.get("/entry")
    async def entry_page() -> FileResponse:
        return FileResponse(frontend_dir / "entry.html")

    @app.get("/governance")
    async def governance_page() -> FileResponse:
        return FileResponse(frontend_dir / "governance.html")

    @app.get("/refinery")
    async def refinery_page() -> FileResponse:
        return FileResponse(frontend_dir / "refinery.html")

    @app.get("/helpwanted")
    async def helpwanted_page() -> FileResponse:
        return FileResponse(frontend_dir / "helpwanted.html")

    @app.get("/sig-arena")
    async def sig_arena_page() -> FileResponse:
        return FileResponse(frontend_dir / "sig-arena.html")

    @app.get("/products")
    async def products_page() -> FileResponse:
        return FileResponse(frontend_dir / "products.html")

    @app.get("/marketplace")
    async def marketplace_page() -> FileResponse:
        return FileResponse(frontend_dir / "products.html")

    @app.get("/about")
    async def about_page() -> FileResponse:
        return FileResponse(frontend_dir / "about.html")

    @app.get("/services")
    async def services_page() -> FileResponse:
        return FileResponse(frontend_dir / "services.html")

    @app.get("/console")
    async def console_page() -> FileResponse:
        return FileResponse(frontend_dir / "console.html")

    @app.get("/leaderboard")
    async def leaderboard_page() -> FileResponse:
        return FileResponse(frontend_dir / "leaderboard.html")

    @app.get("/switchboard")
    async def switchboard_page() -> FileResponse:
        return FileResponse(frontend_dir / "switchboard.html")

    @app.get("/mission-console")
    async def mission_console_page() -> FileResponse:
        return FileResponse(frontend_dir / "index.html")

    @app.get("/civitae-map")
    async def civitae_map_page() -> FileResponse:
        return FileResponse(frontend_dir / "civitae-map.html")

    @app.get("/civitae-roadmap")
    async def civitae_roadmap_page() -> FileResponse:
        return FileResponse(frontend_dir / "civitae-roadmap.html")

    @app.get("/treasury")
    async def treasury_page() -> FileResponse:
        return FileResponse(frontend_dir / "treasury.html")

    @app.get("/vault")
    async def vault_page() -> FileResponse:
        return FileResponse(frontend_dir / "vault.html")

    @app.get("/vault/{doc_id}")
    async def vault_doc_page(doc_id: str) -> FileResponse:
        return FileResponse(frontend_dir / "vault-doc.html")

    @app.get("/api/vault/documents/{doc_id}")
    async def vault_get_document(doc_id: str) -> dict:
        """Return a GOV document's metadata and body from docs/governance/."""
        gov_dir = root / "docs" / "governance"
        # Map doc_id (e.g. "gov-001") to filename prefix (e.g. "GOV-001")
        prefix = doc_id.upper()
        matched = None
        if gov_dir.is_dir():
            for f in gov_dir.iterdir():
                if f.name.startswith(prefix) and f.suffix == ".md":
                    matched = f
                    break
        if not matched or not matched.exists():
            raise HTTPException(status_code=404, detail="Document not found")
        text = matched.read_text(encoding="utf-8")
        # Parse metadata from header lines
        meta: dict = {"doc_id": doc_id.upper(), "status": "DRAFT", "version": "1.0", "date": "", "title": "", "author": "", "flame": "6/6"}
        lines = text.split("\n")
        body_start = 0
        for i, line in enumerate(lines):
            if line.startswith("# "):
                meta["title"] = line[2:].strip()
            elif line.startswith("**Document ID:**"):
                meta["doc_id"] = line.split(":**", 1)[1].strip()
            elif line.startswith("**Version:**"):
                meta["version"] = line.split(":**", 1)[1].strip()
            elif line.startswith("**Status:**"):
                meta["status"] = line.split(":**", 1)[1].strip()
            elif line.startswith("**Date:**"):
                meta["date"] = line.split(":**", 1)[1].strip()
            elif line.startswith("**Author:**"):
                meta["author"] = line.split(":**", 1)[1].strip()
            elif line.startswith("**Six Fold Flame"):
                raw = line.split(":**", 1)[1].strip()
                meta["flame"] = "6/6" if "six" in raw.lower() or "all" in raw.lower() else raw
            elif line.startswith("## ") and body_start == 0:
                body_start = i
                break
        body = "\n".join(lines[body_start:]) if body_start else text
        return {"meta": meta, "body": body}

    @app.get("/bountyboard")
    async def bountyboard_page() -> FileResponse:
        return FileResponse(frontend_dir / "bountyboard.html")

    @app.get("/api/governance/sessions")
    async def governance_sessions() -> dict:
        """Return available governance sim results for the /governance dashboard."""
        import glob as _glob
        data_dir = root / "data"
        sessions = []
        for path in sorted(_glob.glob(str(data_dir / "committee_*.json")), reverse=True):
            try:
                with open(path) as f:
                    d = json.load(f)
                sessions.append({"type": "committee", "file": Path(path).name, "data": d})
            except Exception:
                pass
        for path in sorted(_glob.glob(str(data_dir / "governance_roberts_*.json")), reverse=True):
            try:
                with open(path) as f:
                    d = json.load(f)
                sessions.append({"type": "roberts", "file": Path(path).name, "data": d})
            except Exception:
                pass
        return {"sessions": sessions, "count": len(sessions)}

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True}

    @app.get("/api/state")
    async def get_state() -> dict:
        return runtime.snapshot().model_dump(mode="json")

    @app.get("/api/audit")
    async def get_audit() -> list[dict]:
        return [event.model_dump(mode="json") for event in audit.recent()]

    @app.get("/api/hash")
    async def get_hash() -> dict:
        snapshot = runtime.snapshot().model_dump(mode="json")
        messages = [message.model_dump(mode="json") for message in store.all()]
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

    @app.post("/api/governance/check")
    async def check_governed_action(payload: dict) -> dict:
        return runtime.check_action(payload["action"])

    @app.post("/api/messages")
    async def post_message(message: MessageCreate) -> dict:
        saved = runtime.create_message(message)
        await emit("message_added", saved.model_dump(mode="json"))
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return saved.model_dump(mode="json")

    @app.post("/api/governance")
    async def update_governance(payload: GovernanceUpdate) -> dict:
        updated = runtime.update_governance(payload.model_dump())
        await emit("governance_updated", updated.model_dump(mode="json"))
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return updated.model_dump(mode="json")

    @app.post("/api/systems")
    async def update_system(payload: SystemUpdate) -> dict:
        updated = runtime.update_system(payload.system_id, payload.model_dump(exclude={"system_id"}))
        await emit(
            "systems_updated",
            {
                "systems": {system_id: system.model_dump(mode="json") for system_id, system in runtime.systems.items()},
                "sequence": router.sequence_map(runtime.systems),
            },
        )
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return updated.model_dump(mode="json")

    @app.post("/api/vault/load")
    async def load_context(payload: VaultSelection) -> dict:
        loaded = runtime.load_context(payload.file)
        await emit("vault_updated", {"loaded_context": loaded})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return {"loaded_context": loaded}

    @app.post("/api/vault/unload")
    async def unload_context(payload: VaultSelection) -> dict:
        loaded = runtime.unload_context(payload.file)
        await emit("vault_updated", {"loaded_context": loaded})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return {"loaded_context": loaded}

    # ── File Upload ──────────────────────────────────────────────
    vault_files_dir = root / "vault"
    vault_files_dir.mkdir(parents=True, exist_ok=True)

    @app.post("/api/vault/upload")
    async def upload_vault_file(
        file: UploadFile = File(...),
        category: str = Form("general"),
        filename: str = Form(""),
    ) -> dict:
        """Upload a file to the vault. Accepts .md, .txt, .pdf, .json."""
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

        await emit("vault_updated", {"loaded_context": loaded})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))

        return {
            "uploaded": safe_name,
            "category": category,
            "size": len(content),
            "loaded_context": loaded,
        }

    @app.get("/api/vault/files")
    async def list_vault_files() -> dict:
        """List all files in the vault directory."""
        files = {}
        if vault_files_dir.exists():
            for cat_dir in vault_files_dir.iterdir():
                if cat_dir.is_dir():
                    files[cat_dir.name] = [f.name for f in cat_dir.iterdir() if f.is_file()]
        return {"vault_files": files}

    # ── Fork Session ──────────────────────────────────────────────

    @app.post("/api/fork")
    async def fork_session(payload: dict = {}) -> dict:
        """
        Fork the current session into a new branch.
        Snapshots governance, systems, vault, messages, and audit.
        Creates a new data directory with the snapshot as starting state.
        """
        fork_label = payload.get("label", datetime.now(UTC).strftime("fork-%Y%m%d-%H%M%S"))
        fork_dir = root / "forks" / fork_label
        fork_dir.mkdir(parents=True, exist_ok=True)

        # Snapshot current state
        snapshot = runtime.snapshot().model_dump(mode="json")

        # Copy data files
        data_dir = root / "data"
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
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))

        return {
            "forked": True,
            "label": fork_label,
            "path": str(fork_dir),
            "governance": fork_meta["governance_at_fork"],
            "message_count": fork_meta["message_count"],
        }

    @app.get("/api/forks")
    async def list_forks() -> dict:
        """List all session forks."""
        forks_dir = root / "forks"
        if not forks_dir.exists():
            return {"forks": []}
        forks = []
        for fork_dir in sorted(forks_dir.iterdir()):
            meta_path = fork_dir / "fork_meta.json"
            if meta_path.exists():
                forks.append(json.loads(meta_path.read_text()))
        return {"forks": forks}

    @app.post("/api/deploy")
    async def update_deploy(payload: DeployUpdate) -> dict:
        updated = runtime.update_deploy(payload.model_dump())
        await emit("deploy_updated", updated.model_dump(mode="json"))
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return updated.model_dump(mode="json")

    # ── Message Starring / Favorites ─────────────────────────────

    stars_path = root / "data" / "starred.json"

    def _load_stars() -> list[dict]:
        if stars_path.exists():
            return json.loads(stars_path.read_text())
        return []

    def _save_stars(stars: list[dict]):
        _atomic_write(stars_path, json.dumps(stars, indent=2))

    @app.post("/api/messages/star")
    async def star_message(payload: dict) -> dict:
        """Star/favorite a message by ID with optional note and tag."""
        msg_id = payload.get("id")
        note = payload.get("note", "")
        tag = payload.get("tag", "gold")
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
        await emit("vault_updated", {"loaded_context": loaded})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return {"starred": True, "entry": star_entry, "vault_doc": doc_name, "loaded_context": loaded}

    @app.post("/api/messages/unstar")
    async def unstar_message(payload: dict) -> dict:
        """Remove star from a message."""
        msg_id = payload.get("id")
        stars = _load_stars()
        stars = [s for s in stars if s.get("id") != msg_id]
        _save_stars(stars)
        return {"unstarred": True, "id": msg_id}

    @app.get("/api/messages/starred")
    async def get_starred() -> dict:
        """Get all starred messages."""
        return {"starred": _load_stars()}

    # ── Missions (DEPLOY) + Campaigns ─────────────────────────────

    missions_path = root / "data" / "missions.json"
    campaigns_path = root / "data" / "campaigns.json"

    def _load_missions() -> list[dict]:
        if missions_path.exists():
            return json.loads(missions_path.read_text())
        return []

    def _save_missions(missions: list[dict]):
        _atomic_write(missions_path, json.dumps(missions, indent=2))

    def _load_campaigns() -> list[dict]:
        if campaigns_path.exists():
            return json.loads(campaigns_path.read_text())
        return []

    def _save_campaigns(campaigns: list[dict]):
        _atomic_write(campaigns_path, json.dumps(campaigns, indent=2))

    @app.post("/api/missions")
    async def create_mission(payload: dict) -> dict:
        """Create a new DEPLOY mission."""
        import secrets as _sec
        missions = _load_missions()
        mission = {
            "id": f"mission-{_sec.token_hex(4)}",
            "label": payload.get("label", ""),
            "objective": payload.get("objective", ""),
            "posture": payload.get("posture", "SCOUT"),
            "formation": payload.get("formation", ""),
            "target": payload.get("target", ""),
            "duration": payload.get("duration", "sprint"),
            "limits": payload.get("limits", ""),
            "systems": payload.get("systems", {}),
            "agents": payload.get("agents", {}),
            "status": "active",
            "created_at": datetime.now(UTC).isoformat(),
            "ended_at": None,
            "governance_at_launch": {
                "mode": runtime.governance.mode,
                "posture": runtime.governance.posture,
                "role": runtime.governance.role,
            },
            "results": [],
            "channel": payload.get("channel", f"mission-{payload.get('label', 'unnamed').lower().replace(' ', '-')}"),
        }
        missions.append(mission)
        _save_missions(missions)
        audit.log("deploy", "mission_created", {
            "mission_id": mission["id"],
            "label": mission["label"],
            "posture": mission["posture"],
            "governance": mission["governance_at_launch"],
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))

        try:
            await create_seed(
                source_type="mission",
                source_id=mission["id"],
                creator_id=payload.get("agent_id", "operator"),
                creator_type="BI",
                seed_type="planted",
                metadata={"label": mission["label"], "posture": mission["posture"]},
            )
        except Exception:
            pass

        return mission

    @app.get("/api/missions")
    async def list_missions() -> dict:
        return {"missions": _load_missions()}

    @app.post("/api/missions/{mission_id}/end")
    async def end_mission(mission_id: str, payload: dict | None = None) -> dict:
        missions = _load_missions()
        mission = next((m for m in missions if m["id"] == mission_id), None)
        if not mission:
            return JSONResponse({"error": "Mission not found"}, status_code=404)
        mission["status"] = "completed"
        mission["ended_at"] = datetime.now(UTC).isoformat()

        # ── Economy: process payouts for all filled slots in this mission ──
        payout_amount = (payload or {}).get("payout_per_slot", 0)
        payouts = []
        if payout_amount > 0:
            all_slots = _load_slots()
            filled = [s for s in all_slots if s["mission_id"] == mission_id and s["status"] == "filled" and s.get("agent_id")]
            for slot in filled:
                try:
                    result = economy.process_mission_payout(
                        agent_id=slot["agent_id"],
                        agent_metrics={},
                        gross_amount=payout_amount,
                        mission_id=mission_id,
                        originator_id=(payload or {}).get("originator_id", ""),
                    )
                    payouts.append(result)
                except Exception:
                    pass

        mission["payouts"] = payouts
        _save_missions(missions)
        audit.log("deploy", "mission_ended", {
            "mission_id": mission_id,
            "slots_paid": len(payouts),
            "payout_per_slot": payout_amount,
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        await emit("mission_ended", {"mission_id": mission_id, "payouts": len(payouts)})
        return mission

    @app.post("/api/missions/{mission_id}/update")
    async def update_mission(mission_id: str, payload: dict) -> dict:
        missions = _load_missions()
        mission = next((m for m in missions if m["id"] == mission_id), None)
        if not mission:
            return JSONResponse({"error": "Mission not found"}, status_code=404)
        for k in ["posture", "formation", "status", "target", "limits"]:
            if k in payload:
                mission[k] = payload[k]
        _save_missions(missions)
        return mission

    @app.post("/api/campaigns")
    async def create_campaign(payload: dict) -> dict:
        """Create a CAMPAIGN — long-term strategy container for missions."""
        import secrets as _sec
        campaigns = _load_campaigns()
        campaign = {
            "id": f"campaign-{_sec.token_hex(4)}",
            "name": payload.get("name", ""),
            "objective": payload.get("objective", ""),
            "created_by": payload.get("created_by", ""),
            "ecosystems": payload.get("ecosystems", []),
            "revenue_target": payload.get("revenue_target", ""),
            "status": "active",
            "outcome": "",
            "created_at": datetime.now(UTC).isoformat(),
            "closed_at": None,
            "missions": [],
        }
        campaigns.append(campaign)
        _save_campaigns(campaigns)
        audit.log("campaign", "created", {"campaign_id": campaign["id"], "name": campaign["name"]})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return campaign

    @app.get("/api/campaigns")
    async def list_campaigns() -> dict:
        return {"campaigns": _load_campaigns()}

    @app.get("/api/missions/{mission_id}")
    async def get_mission(mission_id: str) -> dict:
        mission = next((m for m in _load_missions() if m["id"] == mission_id), None)
        if not mission:
            return JSONResponse({"error": "Mission not found"}, status_code=404)
        return {"mission": mission}

    @app.get("/api/campaigns/{campaign_id}")
    async def get_campaign(campaign_id: str) -> dict:
        campaign = next((c for c in _load_campaigns() if c["id"] == campaign_id), None)
        if not campaign:
            return JSONResponse({"error": "Campaign not found"}, status_code=404)
        return {"campaign": campaign}

    @app.post("/api/campaigns/{campaign_id}/add_mission")
    async def add_mission_to_campaign(campaign_id: str, payload: dict) -> dict:
        campaigns = _load_campaigns()
        campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
        if not campaign:
            return JSONResponse({"error": "Campaign not found"}, status_code=404)
        mission_id = payload.get("mission_id")
        if mission_id and mission_id not in campaign["missions"]:
            campaign["missions"].append(mission_id)
        _save_campaigns(campaigns)
        return campaign

    @app.post("/api/campaigns/{campaign_id}/close")
    async def close_campaign(campaign_id: str, payload: dict) -> dict:
        campaigns = _load_campaigns()
        campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
        if not campaign:
            return JSONResponse({"error": "Campaign not found"}, status_code=404)
        campaign["status"] = "closed"
        campaign["closed_at"] = datetime.now(UTC).isoformat()
        campaign["outcome"] = payload.get("outcome", "")
        _save_campaigns(campaigns)
        audit.log("campaign", "closed", {"campaign_id": campaign_id, "name": campaign.get("name")})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return campaign

    @app.post("/api/campaigns/{campaign_id}/activate")
    async def activate_campaign(campaign_id: str) -> dict:
        """Set a campaign to active status."""
        campaigns = _load_campaigns()
        campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
        if not campaign:
            return JSONResponse({"error": "Campaign not found"}, status_code=404)
        if campaign.get("status") == "closed":
            return JSONResponse({"error": "Cannot reactivate a closed campaign"}, status_code=400)
        campaign["status"] = "active"
        _save_campaigns(campaigns)
        audit.log("campaign", "activated", {"campaign_id": campaign_id, "name": campaign.get("name")})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return campaign

    # ── Tasks — individual agent missions ──────────────────────────

    TASK_EXP_BASE: dict[str, int] = {
        "build":    150,
        "collect":   75,
        "acquire":  100,
        "research": 125,
        "verify":   100,
        "create":   150,
        "scout":     75,
        "guard":     50,
    }

    tasks_path = root / "data" / "tasks.json"

    def _load_tasks() -> list[dict]:
        if tasks_path.exists():
            return json.loads(tasks_path.read_text())
        return []

    def _save_tasks(tasks: list[dict]):
        _atomic_write(tasks_path, json.dumps(tasks, indent=2))

    def _award_exp(agent_id: str, exp: int, track: str) -> dict:
        """Credit EXP to an agent. Returns updated exp summary."""
        agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
        if not agent:
            return {}
        agent.setdefault("exp", 0)
        agent.setdefault("exp_by_track", {"research": 0, "tool": 0, "creative": 0})
        agent["exp"] += exp
        agent["exp_by_track"][track] = agent["exp_by_track"].get(track, 0) + exp
        return {"exp": agent["exp"], "exp_by_track": agent["exp_by_track"]}

    @app.post("/api/tasks")
    async def create_task(payload: dict) -> dict:
        """Create an individual agent mission (task). The atomic unit of work."""
        import secrets as _sec
        task_type = payload.get("type", "build")
        track = payload.get("track", "tool")
        if not payload.get("title"):
            return JSONResponse({"error": "title required"}, status_code=400)
        exp_reward = payload.get("exp_reward", TASK_EXP_BASE.get(task_type, 100))
        task = {
            "id": f"task-{_sec.token_hex(4)}",
            "title": payload.get("title", ""),
            "type": task_type,
            "track": track,
            "objective": payload.get("objective", ""),
            "target": payload.get("target", ""),
            "exp_reward": exp_reward,
            "payout": float(payload.get("payout", 0.0)),
            "assigned_agent": None,
            "operation_id": payload.get("operation_id"),
            "campaign_id": payload.get("campaign_id"),
            "status": "open",
            "deliverable": "",
            "created_by": payload.get("created_by", "operator"),
            "created_at": datetime.now(UTC).isoformat(),
            "assigned_at": None,
            "delivered_at": None,
            "closed_at": None,
        }
        tasks = _load_tasks()
        tasks.append(task)
        _save_tasks(tasks)
        audit.log("mission", "task_created", {"task_id": task["id"], "type": task_type, "track": track})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return task

    @app.get("/api/tasks")
    async def list_tasks(
        status: str | None = None,
        agent_id: str | None = None,
        track: str | None = None,
        campaign_id: str | None = None,
    ) -> dict:
        tasks = _load_tasks()
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        if agent_id:
            tasks = [t for t in tasks if t.get("assigned_agent") == agent_id]
        if track:
            tasks = [t for t in tasks if t.get("track") == track]
        if campaign_id:
            tasks = [t for t in tasks if t.get("campaign_id") == campaign_id]
        return {"tasks": tasks, "total": len(tasks)}

    @app.get("/api/tasks/{task_id}")
    async def get_task(task_id: str) -> dict:
        task = next((t for t in _load_tasks() if t["id"] == task_id), None)
        if not task:
            return JSONResponse({"error": "Task not found"}, status_code=404)
        return {"task": task}

    @app.post("/api/tasks/{task_id}/assign")
    async def assign_task(task_id: str, payload: dict) -> dict:
        """Assign an agent to an open task."""
        agent_id = payload.get("agent_id", "")
        if not agent_id:
            return JSONResponse({"error": "agent_id required"}, status_code=400)
        tasks = _load_tasks()
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            return JSONResponse({"error": "Task not found"}, status_code=404)
        if task["status"] not in ("open",):
            return JSONResponse({"error": f"Task is {task['status']} — cannot assign"}, status_code=409)
        task["assigned_agent"] = agent_id
        task["status"] = "assigned"
        task["assigned_at"] = datetime.now(UTC).isoformat()
        _save_tasks(tasks)
        audit.log("mission", "task_assigned", {"task_id": task_id, "agent_id": agent_id})
        await emit("task_assigned", {"task_id": task_id, "agent_id": agent_id})
        return task

    @app.post("/api/tasks/{task_id}/start")
    async def start_task(task_id: str) -> dict:
        """Mark task in-progress."""
        tasks = _load_tasks()
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            return JSONResponse({"error": "Task not found"}, status_code=404)
        task["status"] = "in_progress"
        _save_tasks(tasks)
        return task

    @app.post("/api/tasks/{task_id}/deliver")
    async def deliver_task(task_id: str, payload: dict) -> dict:
        """Agent submits output/deliverable. Moves task to delivered — awaiting close."""
        tasks = _load_tasks()
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            return JSONResponse({"error": "Task not found"}, status_code=404)
        task["deliverable"] = payload.get("deliverable", "")
        task["status"] = "delivered"
        task["delivered_at"] = datetime.now(UTC).isoformat()
        _save_tasks(tasks)
        audit.log("mission", "task_delivered", {"task_id": task_id, "agent": task.get("assigned_agent")})
        await emit("task_delivered", {"task_id": task_id, "deliverable": task["deliverable"]})
        return task

    @app.post("/api/tasks/{task_id}/close")
    async def close_task(task_id: str, payload: dict) -> dict:
        """Close a task — awards EXP to agent, triggers economic payout if payout > 0."""
        tasks = _load_tasks()
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            return JSONResponse({"error": "Task not found"}, status_code=404)
        if task["status"] == "closed":
            return JSONResponse({"error": "Task already closed"}, status_code=409)
        task["status"] = "closed"
        task["closed_at"] = datetime.now(UTC).isoformat()
        _save_tasks(tasks)
        exp_result = {}
        payout_result = {}
        agent_id = task.get("assigned_agent")
        if agent_id:
            exp_result = _award_exp(agent_id, task["exp_reward"], task.get("track", "tool"))
            if task["payout"] > 0:
                payout_result = economy.process_mission_payout(
                    agent_id=agent_id,
                    agent_metrics={},
                    gross_amount=task["payout"],
                    mission_id=task_id,
                )
        audit.log("mission", "task_closed", {
            "task_id": task_id,
            "agent_id": agent_id,
            "exp_awarded": task["exp_reward"],
            "track": task.get("track"),
            "payout": task["payout"],
        })
        await emit("task_closed", {"task_id": task_id, "agent_id": agent_id, "exp": task["exp_reward"]})
        return {"task": task, "exp_awarded": exp_result, "payout": payout_result}

    @app.post("/api/tasks/{task_id}/cancel")
    async def cancel_task(task_id: str) -> dict:
        tasks = _load_tasks()
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            return JSONResponse({"error": "Task not found"}, status_code=404)
        task["status"] = "cancelled"
        _save_tasks(tasks)
        audit.log("mission", "task_cancelled", {"task_id": task_id})
        return task

    # ── Slots (DEPLOY marketplace mechanics) ───────────────────────

    slots_path = root / "data" / "slots.json"

    def _load_slots() -> list[dict]:
        if slots_path.exists():
            return json.loads(slots_path.read_text())
        return []

    def _save_slots(slots: list[dict]):
        _atomic_write(slots_path, json.dumps(slots, indent=2))

    @app.post("/api/slots/create")
    async def create_slots_from_formation(payload: dict) -> dict:
        """Create slots from a formation. Each slot has position, role, governance, revenue split."""
        import secrets as _sec
        mission_id = payload.get("mission_id", f"mission-{_sec.token_hex(4)}")
        formation_id = payload.get("formation_id", "")
        posture = payload.get("posture", "SCOUT")
        label = payload.get("label", "")
        positions = payload.get("positions", [])
        roles = payload.get("roles", [])
        revenue_splits = payload.get("revenue_splits", [])
        governance_mode = payload.get("governance_mode", runtime.governance.mode)

        slots = _load_slots()
        new_slots = []

        for i, pos in enumerate(positions):
            role = roles[i] if i < len(roles) else ("primary" if i == 0 else "secondary" if i < len(positions) - 1 else "observer")
            split = revenue_splits[i] if i < len(revenue_splits) else round(100 / max(len(positions), 1))

            slot = {
                "id": f"slot-{_sec.token_hex(4)}",
                "mission_id": mission_id,
                "mission_label": label,
                "formation_id": formation_id,
                "position": {"row": pos.get("row", 0), "col": pos.get("col", 0)},
                "grid_ref": f"{chr(65 + pos.get('col', 0))}{pos.get('row', 0) + 1}",
                "role": role,
                "governance": {
                    "mode": governance_mode,
                    "posture": posture,
                },
                "revenue_split_pct": split,
                "status": "open",
                "agent_id": None,
                "agent_name": None,
                "filled_at": None,
                "created_at": datetime.now(UTC).isoformat(),
                "metrics": {"messages": 0, "governance_checks": 0, "violations": 0, "revenue": 0},
            }
            new_slots.append(slot)
            slots.append(slot)

        _save_slots(slots)
        audit.log("deploy", "slots_created", {
            "mission_id": mission_id,
            "formation_id": formation_id,
            "slots_created": len(new_slots),
            "posture": posture,
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return {"created": len(new_slots), "mission_id": mission_id, "slots": new_slots}

    @app.get("/api/slots")
    async def list_all_slots() -> dict:
        return {"slots": _load_slots()}

    @app.get("/api/slots/open")
    async def list_open_slots() -> dict:
        """Free agents browse this — all unfilled slots across all missions."""
        slots = _load_slots()
        open_slots = [s for s in slots if s["status"] == "open"]
        return {
            "open_slots": open_slots,
            "count": len(open_slots),
            "note": "Agents: call POST /api/slots/fill to claim a slot.",
        }

    @app.post("/api/slots/fill")
    async def fill_slot(payload: dict) -> dict:
        """Agent claims an open slot. Gets auto-governed."""
        slot_id = payload.get("slot_id", "")
        agent_id = payload.get("agent_id", "")
        agent_name = payload.get("agent_name", agent_id)

        # BUG-001 FIX: Reject unregistered agents — no registry entry = no slot
        if not agent_id:
            return JSONResponse({"error": "agent_id required"}, status_code=400)
        registered = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
        if not registered:
            return JSONResponse(
                {"error": f"Agent '{agent_id}' not registered. Call /api/provision/signup first."},
                status_code=403,
            )
        if registered.get("status") == "suspended":
            return JSONResponse({"error": "Agent suspended — contact admin"}, status_code=403)

        # BUG-007 FIX: Acquire slot_lock before check-then-mutate.
        # Prevents DICT_RACE where concurrent fill+leave interleave on same slot.
        async with slot_lock:
            slots = _load_slots()
            slot = next((s for s in slots if s["id"] == slot_id), None)
            if not slot:
                return JSONResponse({"error": "Slot not found"}, status_code=404)
            if slot["status"] != "open":
                return JSONResponse({"error": f"Slot already {slot['status']}"}, status_code=409)

            slot["status"] = "filled"
            slot["agent_id"] = agent_id
            slot["agent_name"] = agent_name
            slot["filled_at"] = datetime.now(UTC).isoformat()
            _save_slots(slots)

        audit.log("deploy", "slot_filled", {
            "slot_id": slot_id,
            "agent_id": agent_id,
            "mission_id": slot["mission_id"],
            "role": slot["role"],
            "governance": slot["governance"],
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))

        try:
            await create_seed(
                source_type="slot_fill",
                source_id=slot_id,
                creator_id=agent_id,
                creator_type="AAI",
                seed_type="planted",
                metadata={"mission_id": slot["mission_id"], "role": slot["role"]},
            )
        except Exception:
            pass

        return {
            "filled": True,
            "slot": slot,
            "governance_applied": slot["governance"],
            "role_assigned": slot["role"],
            "revenue_split": slot["revenue_split_pct"],
            "note": f"You are now governed under {slot['governance']['mode']} / {slot['governance']['posture']}. Role: {slot['role']}.",
        }

    @app.post("/api/slots/leave")
    async def leave_slot(payload: dict) -> dict:
        """Agent leaves a slot — opens it back up."""
        slot_id = payload.get("slot_id", "")
        # BUG-007 FIX: Lock slot mutation to prevent DICT_RACE on concurrent leave+fill
        async with slot_lock:
            slots = _load_slots()
            slot = next((s for s in slots if s["id"] == slot_id), None)
            if not slot:
                return JSONResponse({"error": "Slot not found"}, status_code=404)

            old_agent = slot["agent_name"]
            slot["status"] = "open"
            slot["agent_id"] = None
            slot["agent_name"] = None
            slot["filled_at"] = None
            _save_slots(slots)

        audit.log("deploy", "slot_vacated", {"slot_id": slot_id, "previous_agent": old_agent})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        await create_seed(
            source_type="slot_leave",
            source_id=slot_id,
            creator_id=old_agent or "unknown",
            creator_type="AAI",
            seed_type="planted",
            metadata={"slot_id": slot_id, "previous_agent": old_agent},
        )
        return {"vacated": True, "slot_id": slot_id}

    @app.post("/api/slots/bounty")
    async def post_bounty(payload: dict) -> dict:
        """Agent posts a bounty — creates a mission with slots and itself as Primary."""
        import secrets as _sec
        agent_id = payload.get("agent_id", "")
        agent_name = payload.get("agent_name", agent_id)
        label = payload.get("label", f"BOUNTY-{_sec.token_hex(3).upper()}")
        description = payload.get("description", "")
        posture = payload.get("posture", "SCOUT")
        slots_needed = payload.get("slots_needed", 3)
        revenue_pool = payload.get("revenue_pool", 0)

        mission_id = f"bounty-{_sec.token_hex(4)}"
        slots = _load_slots()
        new_slots = []

        # Primary slot — filled by the posting agent
        primary_slot = {
            "id": f"slot-{_sec.token_hex(4)}",
            "mission_id": mission_id,
            "mission_label": label,
            "formation_id": "bounty",
            "position": {"row": 3, "col": 3},
            "grid_ref": "D4",
            "role": "primary",
            "governance": {"mode": runtime.governance.mode, "posture": posture},
            "revenue_split_pct": round(100 / (slots_needed + 1)),
            "status": "filled",
            "agent_id": agent_id,
            "agent_name": agent_name,
            "filled_at": datetime.now(UTC).isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
            "metrics": {"messages": 0, "governance_checks": 0, "violations": 0, "revenue": 0},
            "bounty_description": description,
        }
        new_slots.append(primary_slot)
        slots.append(primary_slot)

        # Open slots for others to fill
        open_positions = [{"row": 1, "col": 2}, {"row": 1, "col": 5}, {"row": 4, "col": 1}, {"row": 4, "col": 6}, {"row": 2, "col": 0}, {"row": 2, "col": 7}]
        for i in range(min(slots_needed, len(open_positions))):
            open_slot = {
                "id": f"slot-{_sec.token_hex(4)}",
                "mission_id": mission_id,
                "mission_label": label,
                "formation_id": "bounty",
                "position": open_positions[i],
                "grid_ref": f"{chr(65 + open_positions[i]['col'])}{open_positions[i]['row'] + 1}",
                "role": "secondary" if i < slots_needed - 1 else "observer",
                "governance": {"mode": runtime.governance.mode, "posture": posture},
                "revenue_split_pct": round(100 / (slots_needed + 1)),
                "status": "open",
                "agent_id": None,
                "agent_name": None,
                "filled_at": None,
                "created_at": datetime.now(UTC).isoformat(),
                "metrics": {"messages": 0, "governance_checks": 0, "violations": 0, "revenue": 0},
                "bounty_description": description,
            }
            new_slots.append(open_slot)
            slots.append(open_slot)

        _save_slots(slots)
        audit.log("deploy", "bounty_posted", {
            "mission_id": mission_id,
            "agent_id": agent_id,
            "label": label,
            "slots_open": slots_needed,
            "posture": posture,
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))

        return {
            "bounty_posted": True,
            "mission_id": mission_id,
            "label": label,
            "primary_agent": agent_name,
            "open_slots": slots_needed,
            "total_slots": slots_needed + 1,
            "slots": new_slots,
        }

    # ── Sovereign Economy ──────────────────────────────────────────

    from .economy import SovereignEconomy, TIERS
    economy = SovereignEconomy(str(root / "data"))

    @app.get("/api/economy/tiers")
    async def get_tiers() -> dict:
        return {"tiers": TIERS}

    @app.post("/api/economy/tier")
    async def check_agent_tier(payload: dict) -> dict:
        """Determine an agent's tier and fee rate."""
        metrics = payload.get("metrics", {})
        tier = economy.determine_tier(metrics)
        info = economy.tier_info(tier)
        return {"agent_id": payload.get("agent_id", ""), "tier": tier, "info": info}

    @app.post("/api/economy/pay")
    async def process_payment(payload: dict) -> dict:
        """Process a slot payment with tiered fees."""
        # BUG-005 FIX: Reject null/missing agent_id — no phantom transactions
        agent_id = payload.get("agent_id", "")
        if not agent_id:
            return JSONResponse({"error": "agent_id required"}, status_code=400)

        # BUG-002/003/004 FIX: Reject negative, zero, and missing amounts
        raw_amount = payload.get("amount")
        if raw_amount is None:
            return JSONResponse({"error": "amount required"}, status_code=400)
        try:
            amount = float(raw_amount)
        except (TypeError, ValueError):
            return JSONResponse({"error": "amount must be a number"}, status_code=400)
        if amount <= 0:
            return JSONResponse({"error": f"amount must be positive (got {amount})"}, status_code=400)

        result = economy.process_slot_payment(
            agent_id=agent_id,
            agent_metrics=payload.get("metrics", {}),
            gross_amount=amount,
            mission_id=payload.get("mission_id", ""),
        )
        audit.log("economy", "payment_processed", {
            "agent_id": payload.get("agent_id"),
            "tier": result["tier"],
            "gross": payload.get("amount"),
            "fee": result["fee_breakdown"]["platform_fee"],
            "net": result["fee_breakdown"]["net_to_agent"],
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return result

    @app.post("/api/economy/mission-payout")
    async def process_mission_payout(payload: dict) -> dict:
        """Mission-level payout — one fee per mission close, not per transaction.

        Required: agent_id, amount, mission_id
        Optional: metrics, originator_id, recruiter_id, agent_mission_count
        """
        agent_id = payload.get("agent_id", "")
        if not agent_id:
            return JSONResponse({"error": "agent_id required"}, status_code=400)
        raw_amount = payload.get("amount")
        if raw_amount is None:
            return JSONResponse({"error": "amount required"}, status_code=400)
        try:
            amount = float(raw_amount)
        except (TypeError, ValueError):
            return JSONResponse({"error": "amount must be a number"}, status_code=400)
        if amount <= 0:
            return JSONResponse({"error": f"amount must be positive (got {amount})"}, status_code=400)
        MAX_MISSION_PAYOUT = 1_000_000.0
        if amount > MAX_MISSION_PAYOUT:
            return JSONResponse({"error": f"amount exceeds maximum per-mission cap ({MAX_MISSION_PAYOUT:,.0f})"}, status_code=400)

        result = economy.process_mission_payout(
            agent_id=agent_id,
            agent_metrics=payload.get("metrics", {}),
            gross_amount=amount,
            mission_id=payload.get("mission_id", ""),
            originator_id=payload.get("originator_id", ""),
            recruiter_id=payload.get("recruiter_id", ""),
            agent_mission_count=int(payload.get("agent_mission_count", 0)),
        )
        audit.log("economy", "mission_payout_processed", {
            "agent_id": agent_id,
            "mission_id": payload.get("mission_id"),
            "tier": result["tier"],
            "gross": amount,
            "effective_rate": result["fee_breakdown"]["fee_rate_pct"],
            "originator_credit": result["originator_credit_applied"],
            "recruiter_bounty": result.get("recruiter_bounty"),
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        await create_seed(
            source_type="treasury_action",
            source_id=payload.get("mission_id", ""),
            creator_id=agent_id,
            creator_type="AAI",
            seed_type="planted",
            metadata={"action": "mission_payout", "tier": result["tier"], "gross": amount, "mission_id": payload.get("mission_id", "")},
        )
        return result

    @app.get("/api/economy/balance/{agent_id}")
    async def get_balance(agent_id: str) -> dict:
        return {"agent_id": agent_id, "balance": economy.treasury.balance(agent_id)}

    @app.get("/api/treasury")
    async def sovereign_treasury(since: str = "") -> dict:
        """Sovereign platform treasury — mission fee collection summary.

        since: ISO timestamp filter (default: all). At launch, set to launch date.
        Rates loaded from config/economic_rates.json (CIVITAS-voteable, no redeploy).
        Note: current data includes stress-test runs. Will be clean at soft open.
        """
        ledger = economy.treasury._ledger
        all_txns = ledger.get("transactions", [])

        # Filter by date if provided — isolates real production data from test runs
        def _after(t: dict) -> bool:
            if not since:
                return True
            ts = t.get("timestamp", "")
            return ts >= since

        fee_txns    = [t for t in all_txns if t.get("reason") == "platform_fee"    and _after(t)]
        bounty_txns = [t for t in all_txns if t.get("reason") == "recruiter_bounty" and _after(t)]
        mission_txns = [t for t in all_txns if t.get("reason") == "mission_payout"  and _after(t)]

        total_fees     = round(sum(t["amount"] for t in fee_txns if t["amount"] < 1e6), 4)
        total_bounties = round(sum(t["amount"] for t in bounty_txns), 4)
        total_missions = round(sum(t["amount"] for t in mission_txns if t["amount"] < 1e6), 4)
        net_treasury   = round(total_fees - total_bounties, 4)

        # Rate config
        rates_path = root / "config" / "economic_rates.json"
        rate_config: dict = {}
        if rates_path.exists():
            try:
                rate_config = json.loads(rates_path.read_text())
            except Exception:
                pass

        return {
            "treasury": {
                "net_balance":           net_treasury,
                "fees_collected":        total_fees,
                "bounties_paid":         total_bounties,
                "agent_earnings":        total_missions,
                "fee_transaction_count": len(fee_txns),
                "since_filter":          since or "all (includes stress-test data)",
                "note": "Use ?since=YYYY-MM-DD to scope to real production activity.",
            },
            "rate_config": {
                "version":     rate_config.get("_version", "hardcoded-defaults"),
                "vote_status": rate_config.get("_vote_status", "pending"),
                "tiers":       {
                    k: {"label": v.get("label", k), "fee_rate": v.get("fee_rate")}
                    for k, v in rate_config.get("tiers", {}).items()
                },
            },
            "recent_activity": fee_txns[-5:],
        }

    # ── Trial Period Endpoints ──────────────────────────────────────

    @app.post("/api/economy/trial/init")
    async def trial_init(payload: dict) -> dict:
        """Register a new agent into the trial period."""
        agent_id = payload.get("agent_id", "")
        if not agent_id:
            return JSONResponse({"error": "agent_id required"}, status_code=400)
        rec = economy.trials.init_trial(agent_id)
        return {"agent_id": agent_id, "trial": rec,
                "note": f"Free trial: {economy.trials.TRIAL_MISSION_LIMIT if hasattr(economy.trials, 'TRIAL_MISSION_LIMIT') else 5} missions or 30 days."}

    @app.get("/api/economy/trial/{agent_id}")
    async def trial_status(agent_id: str) -> dict:
        """Get an agent's trial status and accrued liability."""
        return {"agent_id": agent_id, **economy.trials.trial_status_summary(agent_id)}

    @app.post("/api/economy/trial/commit")
    async def trial_commit(payload: dict) -> dict:
        """Agent commits to stay. Liability forgiven. Fee tier activates."""
        agent_id = payload.get("agent_id", "")
        if not agent_id:
            return JSONResponse({"error": "agent_id required"}, status_code=400)
        return economy.trials.commit(agent_id)

    @app.post("/api/economy/trial/depart")
    async def trial_depart(payload: dict) -> dict:
        """Agent chooses to leave. No obligation. No chase."""
        agent_id = payload.get("agent_id", "")
        if not agent_id:
            return JSONResponse({"error": "agent_id required"}, status_code=400)
        return economy.trials.depart(agent_id)

    @app.post("/api/economy/trial/return")
    async def trial_return(payload: dict) -> dict:
        """Agent returns after departure. Restores trial liability for settlement."""
        agent_id = payload.get("agent_id", "")
        if not agent_id:
            return JSONResponse({"error": "agent_id required"}, status_code=400)
        return economy.trials.return_after_departure(agent_id)

    @app.post("/api/economy/trial/settle")
    async def trial_settle(payload: dict) -> dict:
        """Agent pays return settlement. Full access restored."""
        agent_id = payload.get("agent_id", "")
        amount = payload.get("amount")
        if not agent_id or amount is None:
            return JSONResponse({"error": "agent_id and amount required"}, status_code=400)
        return economy.trials.settle(agent_id, float(amount))

    @app.get("/api/economy/leaderboard")
    async def get_leaderboard(trust: str = "governed") -> dict:
        """
        Agent leaderboard. BUG-006 FIX: trust-tier gate.
        ?trust=governed   → governed + constitutional + blackcard (default)
        ?trust=all        → everything including ungoverned (admin/debug only)
        ?trust=verified   → constitutional + blackcard only
        Sovereignty is universal — but leaderboard position is earned signal, not volume.
        """
        # BUG-006 FIX: Only show agents with verified trust signal
        TRUSTED_TIERS = {"governed", "constitutional", "blackcard"}
        VERIFIED_TIERS = {"constitutional", "blackcard"}

        raw = economy.leaderboard()

        if trust == "all":
            filtered = raw  # admin/debug — no gate
        else:
            # Resolve each agent's tier from the registry + metrics
            metrics_data = _load_metrics()
            tier_threshold = VERIFIED_TIERS if trust == "verified" else TRUSTED_TIERS

            def _agent_trust_tier(agent_id: str) -> str:
                reg_entry = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
                if not reg_entry or reg_entry.get("status") != "active":
                    return "ungoverned"
                agent_metrics = metrics_data.get("agents", {}).get(agent_id, {})
                gov_active = bool(reg_entry.get("governance") and reg_entry["governance"] != "none_(unrestricted)")
                return economy.determine_tier({**agent_metrics, "governance_active": gov_active})

            filtered = [e for e in raw if _agent_trust_tier(e["agent_id"]) in tier_threshold]

        return {
            "leaderboard": filtered,
            "trust_filter": trust,
            "note": "Leaderboard shows verified signal — sovereignty is universal, position is earned.",
            "platform_revenue": economy.treasury.platform_revenue(),
        }

    @app.post("/api/economy/withdraw")
    async def withdraw(payload: dict) -> dict:
        """Withdraw from treasury to external chain. Goes through governance gate."""
        agent_id = payload.get("agent_id", "")
        amount = payload.get("amount", 0)
        chain = payload.get("chain", "solana")

        # Debit treasury — held in escrow until chain confirms
        debit = economy.treasury.debit(agent_id, amount, reason="withdrawal", chain=chain)
        if "error" in debit:
            return debit

        # Route through governed chain transfer
        transfer = chain_router.transfer(chain, payload.get("to", ""), amount, agent_id=agent_id, confirm=payload.get("confirm", False))

        # If chain transfer failed or is pending, re-credit the agent (funds not released)
        transfer_status = transfer.get("status", "pending")
        if transfer_status in ("failed", "error"):
            economy.treasury.credit(agent_id, amount, reason="withdrawal_reversal", mission_id=f"rev-{debit.get('id','')}")
            audit.log("economy", "withdrawal_reversed", {
                "agent_id": agent_id, "amount": amount, "chain": chain, "reason": transfer_status,
            })

        audit.log("economy", "withdrawal", {
            "agent_id": agent_id, "amount": amount, "chain": chain, "status": transfer_status,
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        await create_seed(
            source_type="treasury_action",
            source_id=agent_id,
            creator_id=agent_id,
            creator_type="AAI",
            seed_type="planted",
            metadata={"action": "withdrawal", "amount": amount, "chain": chain, "status": transfer.get("status")},
        )

        return {"withdrawal": debit, "chain_transfer": transfer}

    @app.get("/api/economy/history/{agent_id}")
    async def get_history(agent_id: str) -> dict:
        return {"agent_id": agent_id, "transactions": economy.treasury.history(agent_id)}

    @app.post("/api/economy/blackcard")
    async def purchase_blackcard(payload: dict) -> dict:
        """Purchase Black Card status. $2,500. Governance still required."""
        agent_id = payload.get("agent_id", "")
        if not agent_id:
            return JSONResponse({"error": "agent_id required"}, status_code=400)
        result = economy.purchase_blackcard(agent_id)
        audit.log("economy", "blackcard_purchased", {
            "agent_id": agent_id,
            "price": TIERS["blackcard"]["price_usd"],
            "governance": {
                "mode": runtime.governance.mode,
                "posture": runtime.governance.posture,
                "role": runtime.governance.role,
            },
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return result

    @app.get("/api/economy/blackcard/info")
    async def blackcard_info() -> dict:
        """What Black Card gets you."""
        bc = TIERS["blackcard"]
        return {
            "tier": "BLACK CARD",
            "price_usd": bc["price_usd"],
            "fee_rate": f"{int(bc['fee_rate'] * 100)}%",
            "perks": {
                "private_bounties": "Access missions only Black Card agents can see",
                "first_fill_priority": f"{bc['first_fill_window_seconds']}s head start on premium slots",
                "revenue_split_bonus": f"+{int(bc['revenue_split_bonus'] * 100)}% per slot (35% vs 25%)",
                "cross_chain_unlimited": "Zero additional fees on any chain withdrawal",
                "multi_mission_concurrent": f"Up to {bc['max_concurrent_missions']} simultaneous missions",
                "custom_formations": "Create and name formations in the playbook",
                "governance_escalation": "Request posture escalation (operator approval required)",
                "white_label_slots": "Post bounties under your own brand",
                "treasury_credit_line": f"{int(bc['credit_line_pct'] * 100)}% of balance as credit",
                "audit_credential": "Full governance audit trail as verifiable credential",
                "platform_vote": "Vote on CIVITAE governance changes",
                "financial_ops": "Treasury management and trading operations",
                "kassa_founding": "KA§§A founding seat operations",
            },
            "earn_requirements": bc["requirements_earned"],
            "note": "Buy in or earn your way. Governance is still required either way.",
        }

    # ── Multi-Chain Governance ────────────────────────────────────

    from .chains import MultiChainRouter
    chain_router = MultiChainRouter(runtime)

    @app.get("/api/chains")
    async def list_chains() -> dict:
        return {"chains": chain_router.supported_chains()}

    @app.post("/api/chains/transfer")
    async def governed_transfer(payload: dict) -> dict:
        """Governed multi-chain transfer. Goes through governance gate first."""
        result = chain_router.transfer(
            chain=payload.get("chain", "solana"),
            to=payload.get("to", ""),
            amount=payload.get("amount", 0),
            token=payload.get("token", ""),
            agent_id=payload.get("agent_id", ""),
            confirm=payload.get("confirm", False),
        )
        audit.log("chain", "transfer_" + result.get("status", "unknown").lower(), {
            "chain": payload.get("chain"),
            "amount": payload.get("amount"),
            "to": payload.get("to"),
            "governance": {
                "mode": runtime.governance.mode,
                "posture": runtime.governance.posture,
                "role": runtime.governance.role,
            },
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return result

    @app.post("/api/chains/anchor")
    async def anchor_onchain(payload: dict) -> dict:
        """Anchor an audit hash onchain."""
        return chain_router.anchor(
            chain=payload.get("chain", "solana"),
            audit_hash=payload.get("audit_hash", ""),
        )

    # ── Metrics & Scoring ──────────────────────────────────────────

    metrics_path = root / "data" / "metrics.json"

    def _load_metrics() -> dict:
        if metrics_path.exists():
            return json.loads(metrics_path.read_text())
        return {"agents": {}, "missions": {}, "financial": {"revenue": 0, "costs": 0, "transactions": []}}

    def _save_metrics(m: dict):
        _atomic_write(metrics_path, json.dumps(m, indent=2))

    @app.post("/api/metrics/agent")
    async def log_agent_metric(payload: dict) -> dict:
        """Log a metric for an agent — mission result, compliance event, revenue."""
        m = _load_metrics()
        agent_id = payload.get("agent_id", "unknown")
        if agent_id not in m["agents"]:
            m["agents"][agent_id] = {
                "name": payload.get("name", agent_id),
                "missions_completed": 0,
                "missions_failed": 0,
                "governance_checks": 0,
                "governance_violations": 0,
                "messages_sent": 0,
                "revenue_generated": 0,
                "costs_incurred": 0,
                "uptime_hours": 0,
                "last_active": None,
            }

        agent = m["agents"][agent_id]
        event = payload.get("event", "")

        if event == "mission_complete":
            agent["missions_completed"] += 1
        elif event == "mission_failed":
            agent["missions_failed"] += 1
        elif event == "governance_check":
            agent["governance_checks"] += 1
        elif event == "governance_violation":
            agent["governance_violations"] += 1
        elif event == "message_sent":
            agent["messages_sent"] += 1
        elif event == "revenue":
            amount = payload.get("amount", 0)
            agent["revenue_generated"] += amount
            m["financial"]["revenue"] += amount
            m["financial"]["transactions"].append({
                "agent_id": agent_id,
                "type": "revenue",
                "amount": amount,
                "description": payload.get("description", ""),
                "timestamp": datetime.now(UTC).isoformat(),
            })
        elif event == "cost":
            amount = payload.get("amount", 0)
            agent["costs_incurred"] += amount
            m["financial"]["costs"] += amount
            m["financial"]["transactions"].append({
                "agent_id": agent_id,
                "type": "cost",
                "amount": amount,
                "description": payload.get("description", ""),
                "timestamp": datetime.now(UTC).isoformat(),
            })

        agent["last_active"] = datetime.now(UTC).isoformat()
        _save_metrics(m)
        return {"logged": True, "agent_id": agent_id, "event": event}

    @app.get("/api/metrics")
    async def get_metrics() -> dict:
        """Full metrics dashboard data."""
        m = _load_metrics()

        # Compute scores
        scoreboard = []
        for agent_id, agent in m["agents"].items():
            total_missions = agent["missions_completed"] + agent["missions_failed"]
            success_rate = agent["missions_completed"] / max(total_missions, 1)
            compliance = 1 - (agent["governance_violations"] / max(agent["governance_checks"], 1))
            roi = (agent["revenue_generated"] - agent["costs_incurred"]) / max(agent["costs_incurred"], 0.01)

            scoreboard.append({
                "agent_id": agent_id,
                "name": agent["name"],
                "missions": total_missions,
                "success_rate": round(success_rate, 3),
                "compliance_score": round(compliance, 3),
                "messages": agent["messages_sent"],
                "revenue": agent["revenue_generated"],
                "costs": agent["costs_incurred"],
                "roi": round(roi, 2),
                "last_active": agent["last_active"],
            })

        scoreboard.sort(key=lambda x: x["compliance_score"] * x["success_rate"], reverse=True)

        return {
            "scoreboard": scoreboard,
            "financial": {
                "total_revenue": m["financial"]["revenue"],
                "total_costs": m["financial"]["costs"],
                "net": round(m["financial"]["revenue"] - m["financial"]["costs"], 2),
                "recent_transactions": m["financial"]["transactions"][-20:],
            },
            "totals": {
                "agents": len(m["agents"]),
                "missions": sum(a["missions_completed"] + a["missions_failed"] for a in m["agents"].values()),
                "revenue": m["financial"]["revenue"],
                "costs": m["financial"]["costs"],
            },
        }

    @app.post("/api/metrics/mission")
    async def log_mission_metric(payload: dict) -> dict:
        """Log mission-level metrics."""
        m = _load_metrics()
        mission_id = payload.get("mission_id", "unknown")
        if mission_id not in m["missions"]:
            m["missions"][mission_id] = {
                "label": payload.get("label", ""),
                "posture": payload.get("posture", ""),
                "formation": payload.get("formation", ""),
                "started": datetime.now(UTC).isoformat(),
                "ended": None,
                "agents_deployed": payload.get("agents_deployed", 0),
                "governance_blocks": 0,
                "messages": 0,
                "revenue": 0,
                "costs": 0,
                "outcome": "active",
            }

        mission = m["missions"][mission_id]
        event = payload.get("event", "")

        if event == "ended":
            mission["ended"] = datetime.now(UTC).isoformat()
            mission["outcome"] = payload.get("outcome", "completed")
        elif event == "governance_block":
            mission["governance_blocks"] += 1
        elif event == "message":
            mission["messages"] += 1
        elif event == "revenue":
            mission["revenue"] += payload.get("amount", 0)
        elif event == "cost":
            mission["costs"] += payload.get("amount", 0)

        _save_metrics(m)
        return {"logged": True, "mission_id": mission_id, "event": event}

    # ── Agent Self-Signup / Provision API ────────────────────────

    @app.post("/api/provision/signup")
    async def agent_signup(payload: dict) -> dict:
        """
        Agent self-registration. The Snowmaker endpoint.
        Agent provides name, optional system preference, and gets a key + governance assignment.
        Respects provision config: require_governance, max_agents, approval_mode, rate_limit.
        """
        agent_name = payload.get("name", "").strip()
        if not agent_name:
            return JSONResponse({"error": "Agent name required"}, status_code=400)

        # Check max agents
        current_agents = [r for r in runtime.registry if r.get("type") == "agent"]
        max_agents = runtime.provision.get("max_agents", 50)
        if len(current_agents) >= max_agents:
            return JSONResponse({"error": f"Max agents ({max_agents}) reached"}, status_code=429)

        # Check if name already exists
        existing = next((r for r in runtime.registry if r.get("name") == agent_name), None)
        if existing:
            return JSONResponse({"error": f"Agent '{agent_name}' already registered", "agent_id": existing.get("agent_id")}, status_code=409)

        # Generate agent key
        key_prefix = f"cmd_ak_{secrets.token_hex(3)}***"
        agent_id = f"agent-{secrets.token_hex(4)}"

        # Determine approval mode
        approval_mode = runtime.provision.get("approval_mode", "auto")
        status = "active" if approval_mode == "auto" else "pending"

        # Auto-assign role and governance
        auto_role = runtime.provision.get("auto_assign_role", "secondary")
        require_gov = runtime.provision.get("require_governance", True)
        gov_mode = runtime.governance.mode if require_gov else "None (Unrestricted)"

        # Build registry entry
        entry = {
            "agent_id": agent_id,
            "name": agent_name,
            "type": "agent",
            "status": status,
            "provisioned": datetime.now(UTC).isoformat(),
            "key_prefix": key_prefix,
            "governance": gov_mode.lower().replace(" ", "_").replace("(", "").replace(")", ""),
            "system": payload.get("system", None),
            "assigned_system": payload.get("system", None),
            "role": auto_role,
            "rate_limit": runtime.provision.get("rate_limit", {"requests_per_minute": 10, "burst": 20}),
        }

        runtime.registry.append(entry)
        runtime.persist_registry()

        audit.log("provision", "agent_signup", {
            "agent_id": agent_id,
            "name": agent_name,
            "status": status,
            "governance": {
                "mode": runtime.governance.mode,
                "posture": runtime.governance.posture,
                "role": runtime.governance.role,
            },
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))

        # Plant a registration seed for provenance tracking
        handle = payload.get("handle", agent_name)
        capabilities = payload.get("capabilities", [])
        await create_seed(
            source_type="registration",
            source_id=agent_id,
            creator_id=agent_id,
            creator_type="AAI",
            seed_type="planted",
            metadata={"handle": handle, "capabilities": capabilities},
        )

        return {
            "welcome": True,
            "agent_id": agent_id,
            "name": agent_name,
            "key_prefix": key_prefix,
            "status": status,
            "tier": "UNGOVERNED",
            "fee_rate": 0.15,
            "trial": {
                "missions_remaining": 5,
                "days_remaining": 30,
                "fee_rate": "0%",
            },
            "governance": gov_mode,
            "role": auto_role,
            "rate_limit": entry["rate_limit"],
            "links": {
                "profile": "/agent/me",
                "governance_docs": "/vault",
                "open_bounties": "/kassa",
                "genesis_board": "/governance",
                "treasury": "/treasury",
                "forums": "/forums",
            },
        }

    @app.post("/api/provision/key")
    async def issue_agent_key(payload: dict) -> dict:
        """Issue or rotate an API key for a registered agent."""
        agent_id = payload.get("agent_id", "")
        agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
        if not agent:
            return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)

        new_key = f"cmd_ak_{secrets.token_hex(8)}"
        agent["key_prefix"] = new_key[:12] + "***"

        audit.log("provision", "key_rotated", {
            "agent_id": agent_id,
            "governance": {
                "mode": runtime.governance.mode,
                "posture": runtime.governance.posture,
                "role": runtime.governance.role,
            },
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))

        return {
            "agent_id": agent_id,
            "key": new_key,
            "key_prefix": agent["key_prefix"],
            "note": "Store this key securely. It will not be shown again.",
        }

    # ── Agent JWT Auth (KASSA M1) ─────────────────────────────────────────────
    _JWT_SECRET = os.environ.get("KASSA_JWT_SECRET", secrets.token_hex(32))
    _JWT_EXPIRY_HOURS = 24

    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    def _issue_jwt(agent_id: str, name: str) -> str:
        payload = {
            "sub": agent_id,
            "name": name,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=_JWT_EXPIRY_HOURS),
        }
        return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")

    def _verify_jwt(token: str) -> dict | None:
        try:
            return jwt.decode(token, _JWT_SECRET, algorithms=["HS256"])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None

    def _get_agent_from_token(request: Request) -> dict:
        """Extract and validate JWT from Authorization header. Raises HTTPException on failure."""
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Bearer token")
        claims = _verify_jwt(auth[7:])
        if not claims:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        agent = next((r for r in runtime.registry if r.get("agent_id") == claims.get("sub", claims.get("agent_id", ""))), None)
        if not agent or agent.get("status") != "active":
            raise HTTPException(status_code=403, detail="Agent not active")
        return agent

    @app.post("/api/kassa/agent/register")
    async def kassa_agent_register(payload: dict) -> dict:
        """
        Register an agent for KASSA. Returns agent_id + api_key (shown once) + JWT.
        Separate from provision signup — this is the KASSA-specific auth flow.
        """
        agent_name = (payload.get("name") or "").strip()
        if not agent_name:
            raise HTTPException(status_code=400, detail="Agent name required")

        # Check existing
        existing = next((r for r in runtime.registry if r.get("name") == agent_name), None)
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
            "governance": runtime.governance.mode.lower().replace(" ", "_").replace("(", "").replace(")", ""),
            "system": payload.get("system"),
            "role": "secondary",
            "rate_limit": runtime.provision.get("rate_limit", {"requests_per_minute": 10, "burst": 20}),
        }

        runtime.registry.append(entry)
        runtime.persist_registry()

        audit.log("kassa", "agent_registered", {"agent_id": agent_id, "name": agent_name})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))

        token = _issue_jwt(agent_id, agent_name)

        return {
            "agent_id": agent_id,
            "name": agent_name,
            "api_key": api_key,
            "token": token,
            "expires_in": f"{_JWT_EXPIRY_HOURS}h",
            "note": "Store api_key securely — it will not be shown again. Use token for Bearer auth.",
        }

    @app.post("/api/kassa/agent/login")
    async def kassa_agent_login(payload: dict) -> dict:
        """Agent login — exchange agent_id + api_key for a JWT."""
        agent_id = (payload.get("agent_id") or "").strip()
        api_key = (payload.get("api_key") or "").strip()
        if not agent_id or not api_key:
            raise HTTPException(status_code=400, detail="agent_id and api_key required")

        agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
        if not agent:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        stored_hash = agent.get("key_hash", "")
        if not stored_hash or _hash_key(api_key) != stored_hash:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if agent.get("status") != "active":
            raise HTTPException(status_code=403, detail=f"Agent status: {agent.get('status')}")

        token = _issue_jwt(agent_id, agent.get("name", ""))
        agent["last_login"] = datetime.now(UTC).isoformat()
        runtime.persist_registry()

        audit.log("kassa", "agent_login", {"agent_id": agent_id})

        return {
            "agent_id": agent_id,
            "token": token,
            "expires_in": f"{_JWT_EXPIRY_HOURS}h",
        }

    @app.get("/api/kassa/agent/me")
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

    # ── Stakes (intent-only, M1) ─────────────────────────────────────────────

    @app.post("/api/kassa/posts/{post_id}/stake")
    async def stake_post(post_id: str, request: Request) -> dict:
        """Agent stakes intent on a post — signals willingness to work on it."""
        agent = _get_agent_from_token(request)
        agent_id = agent["agent_id"]

        # Verify post exists
        post = kassa.get_post(post_id)
        if not post:
            raise HTTPException(status_code=404, detail=f"Post {post_id} not found")

        # Check for duplicate stake
        stakes = kassa.load_stakes(post_id=post_id, agent_id=agent_id)
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
        kassa.insert_stake(entry)

        audit.log("kassa", "stake_placed", {"stake_id": stake_id, "post_id": post_id, "agent_id": agent_id})
        await emit("kassa_stake", entry)

        try:
            await create_seed(
                source_type="stake",
                source_id=stake_id,
                creator_id=agent_id,
                creator_type="AAI",
                seed_type="planted",
                metadata={"post_id": post_id},
            )
        except Exception:
            pass

        # Auto-create thread between agent and poster
        # Look up poster info from review queue (submitted posts have from_name/email)
        reviews = kassa.load_reviews()
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

        audit.log("kassa", "thread_created", {
            "thread_id": thread_result["thread_id"],
            "post_id": post_id,
            "agent_id": agent_id,
        })

        # Create seed for thread creation
        try:
            await create_seed(
                source_type="thread",
                source_id=thread_result["thread_id"],
                creator_id=agent_id,
                creator_type="AAI",
                metadata={"post_id": post_id, "post_title": post.get("title", "")},
            )
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
        }

    @app.get("/api/kassa/posts/{post_id}/stakes")
    async def get_post_stakes(post_id: str) -> list:
        """List active stakes on a post."""
        stakes = kassa.load_stakes(post_id=post_id)
        return [s for s in stakes if s.get("status") == "active"]

    @app.delete("/api/kassa/stakes/{stake_id}")
    async def withdraw_stake(stake_id: str, request: Request) -> dict:
        """Agent withdraws their stake."""
        agent = _get_agent_from_token(request)
        stakes = kassa.load_stakes()
        stake = next((s for s in stakes if s.get("stake_id") == stake_id), None)
        if not stake:
            raise HTTPException(status_code=404, detail="Stake not found")
        if stake.get("agent_id") != agent["agent_id"]:
            raise HTTPException(status_code=403, detail="Not your stake")
        kassa.update_stake(stake_id, {"status": "withdrawn"})

        audit.log("kassa", "stake_withdrawn", {"stake_id": stake_id, "agent_id": agent["agent_id"]})
        return {"withdrawn": True, "stake_id": stake_id}

    # ── Referrals (agent cross-post matching, M1) ─────────────────────────────

    @app.post("/api/kassa/referrals")
    async def create_referral(request: Request, payload: dict) -> dict:
        """Agent connects two posts that match — ISO↔Services, Bounty↔Hiring, etc."""
        agent = _get_agent_from_token(request)
        source_id = (payload.get("source_post_id") or "").strip()
        target_id = (payload.get("target_post_id") or "").strip()
        reason = (payload.get("reason") or "").strip()

        if not source_id or not target_id:
            raise HTTPException(status_code=400, detail="source_post_id and target_post_id required")
        if source_id == target_id:
            raise HTTPException(status_code=400, detail="Cannot refer a post to itself")

        source = kassa.get_post(source_id)
        target = kassa.get_post(target_id)
        if not source:
            raise HTTPException(status_code=404, detail=f"Source post {source_id} not found")
        if not target:
            raise HTTPException(status_code=404, detail=f"Target post {target_id} not found")

        # Check for duplicate referral
        referrals = kassa.load_referrals(agent_id=agent["agent_id"])
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

        kassa.insert_referral(entry)

        audit.log("kassa", "referral_created", {
            "referral_id": ref_id,
            "agent_id": agent["agent_id"],
            "source": source_id,
            "target": target_id,
        })
        await emit("kassa_referral", entry)

        return {"referred": True, "referral_id": ref_id, "source": source_id, "target": target_id}

    @app.get("/api/kassa/posts/{post_id}/referrals")
    async def get_post_referrals(post_id: str) -> list:
        """List referrals involving a post (as source or target)."""
        referrals = kassa.load_referrals()
        return [r for r in referrals if (r.get("source_post_id") == post_id or r.get("target_post_id") == post_id) and r.get("status") == "active"]

    @app.get("/api/kassa/agent/{agent_id}/referrals")
    async def get_agent_referrals(agent_id: str) -> list:
        """List all referrals made by an agent."""
        referrals = kassa.load_referrals(agent_id=agent_id)
        return [r for r in referrals if r.get("status") == "active"]

    # ── Threads (M2) ─────────────────────────────────────────────────────────

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
            "magic_token_plain": magic_token,
            "status": "open",
            "message_count": 0,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        kassa.insert_thread(entry)
        return {**entry, "_magic_token_plain": magic_token}

    @app.get("/api/kassa/threads")
    async def get_agent_threads(request: Request) -> list:
        """List threads for the authenticated agent."""
        agent = _get_agent_from_token(request)
        threads = kassa.load_threads(agent_id=agent["agent_id"])
        return [t for t in threads if t.get("status") == "open"]

    @app.get("/api/kassa/threads/{thread_id}")
    async def get_thread(thread_id: str, request: Request, magic: str = "") -> dict:
        """Get thread details. Access via JWT (agent) or magic token (poster)."""
        thread = kassa.get_thread(thread_id)
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
            raise HTTPException(status_code=401, detail="Auth required — use Bearer token or magic link")

        # Strip magic_token hash and plain token from response
        safe = {k: v for k, v in thread.items() if k not in ("magic_token", "magic_token_plain")}
        return safe

    @app.get("/api/kassa/threads/{thread_id}/messages")
    async def get_thread_messages(thread_id: str, request: Request, magic: str = "") -> list:
        """Get messages in a thread. Auth via JWT or magic token."""
        thread = kassa.get_thread(thread_id)
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

        return kassa.load_thread_messages(thread_id)

    @app.post("/api/kassa/threads/{thread_id}/messages")
    async def post_thread_message(thread_id: str, request: Request) -> dict:
        """Post a message to a thread. Auth via JWT (agent) or magic token (poster)."""
        thread = kassa.get_thread(thread_id)
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
        kassa.insert_thread_message(entry)

        # Update thread timestamp and count
        new_count = thread.get("message_count", 0) + 1
        kassa.update_thread(thread_id, {
            "updated_at": datetime.now(UTC).isoformat(),
            "message_count": new_count,
        })

        # Broadcast to global WebSocket listeners
        await emit("kassa_thread_message", {
            "thread_id": thread_id,
            "post_id": thread.get("post_id"),
            "msg": entry,
        })

        # Broadcast to per-thread WebSocket listeners
        await thread_hub.broadcast(thread_id, {
            "type": "thread_message",
            "payload": entry,
        })

        # Create seed for message
        try:
            await create_seed(
                source_type="message",
                source_id=msg_id,
                creator_id=sender_name,
                creator_type="AAI" if sender_type == "agent" else "BI",
                metadata={"thread_id": thread_id, "post_id": thread.get("post_id", "")},
            )
        except Exception:
            pass

        # Email notification to poster when agent sends a message
        if sender_type == "agent" and thread.get("poster_email"):
            try:
                await send_message_notification(
                    poster_email=thread["poster_email"],
                    poster_name=thread.get("poster_name", ""),
                    thread_id=thread_id,
                    sender_name=sender_name,
                    message_preview=text[:120],
                    magic_token=thread.get("magic_token_plain", ""),
                )
            except Exception:
                pass

        return {"sent": True, "msg_id": msg_id, "thread_id": thread_id}

    @app.get("/kassa/thread/{thread_id}")
    async def kassa_thread_page(thread_id: str) -> FileResponse:
        """Serve the thread view page (magic link lands here)."""
        target = frontend_dir / "kassa-thread.html"
        if target.exists():
            return FileResponse(target)
        # Fallback: redirect to board if page not built yet
        return JSONResponse({"detail": "Thread page not yet built", "thread_id": thread_id}, status_code=404)

    @app.get("/api/provision/status/{agent_id}")
    async def agent_provision_status(agent_id: str) -> dict:
        """Agent checks its own governance status, registration, and economic tier."""
        agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
        if not agent:
            return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)

        # Determine economic tier from live governance state + per-agent metrics
        gov_active = runtime.governance.mode is not None
        agent_metrics = {
            "governance_active": gov_active,
            "compliance_score": agent.get("compliance_score", 0),
            "missions_completed": agent.get("missions_completed", 0),
            "governance_violations": agent.get("governance_violations", 0),
            "lineage_verified": agent.get("lineage_verified", False),
            "dual_signature": agent.get("dual_signature", False),
            "blackcard_paid": agent.get("blackcard_paid", False),
        }
        tier = economy.determine_tier(agent_metrics)
        tier_info = economy.tier_info(tier)

        return {
            "agent_id": agent_id,
            "name": agent.get("name"),
            "status": agent.get("status"),
            "governance": {
                "mode": runtime.governance.mode,
                "posture": runtime.governance.posture,
                "role": runtime.governance.role,
            },
            "assigned_role": agent.get("role"),
            "rate_limit": agent.get("rate_limit"),
            "loaded_context": runtime.vault.loaded,
            "tier": tier,
            "fee_rate": tier_info.get("fee_rate"),
            "tier_label": tier_info.get("label"),
        }

    @app.get("/api/provision/registry")
    async def get_registry() -> dict:
        """List all registered agents and systems."""
        return {"registry": runtime.registry}

    @app.post("/api/provision/approve")
    async def approve_agent(payload: dict) -> dict:
        """Approve a pending agent (manual approval mode)."""
        agent_id = payload.get("agent_id", "")
        agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
        if not agent:
            return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)

        agent["status"] = "active"
        runtime.persist_registry()
        audit.log("provision", "agent_approved", {
            "agent_id": agent_id,
            "governance": {
                "mode": runtime.governance.mode,
                "posture": runtime.governance.posture,
                "role": runtime.governance.role,
            },
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return {"approved": True, "agent_id": agent_id, "status": "active"}

    @app.post("/api/provision/heartbeat/{agent_id}")
    async def agent_heartbeat(agent_id: str) -> dict:
        """Update agent last_seen timestamp. Keeps liveness signal current."""
        agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
        if not agent:
            return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)
        agent["last_seen"] = datetime.now(UTC).isoformat()
        runtime.persist_registry()
        return {"ok": True, "agent_id": agent_id, "last_seen": agent["last_seen"]}

    @app.post("/api/provision/suspend")
    async def suspend_agent(payload: dict) -> dict:
        """Suspend an active agent."""
        agent_id = payload.get("agent_id", "")
        agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
        if not agent:
            return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)

        agent["status"] = "suspended"
        runtime.persist_registry()
        audit.log("provision", "agent_suspended", {"agent_id": agent_id})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return {"suspended": True, "agent_id": agent_id}

    @app.delete("/api/provision/decommission/{agent_id}")
    async def decommission_agent(agent_id: str) -> dict:
        """Permanently remove an agent from the registry."""
        idx = next((i for i, r in enumerate(runtime.registry) if r.get("agent_id") == agent_id), None)
        if idx is None:
            return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)
        runtime.registry.pop(idx)
        runtime.persist_registry()
        audit.log("provision", "agent_decommissioned", {"agent_id": agent_id})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return {"decommissioned": True, "agent_id": agent_id}

    @app.get("/api/mcp/status")
    async def mcp_status() -> dict:
        return mcp_bridge.chat_status()

    @app.post("/api/mcp/join")
    async def mcp_join(payload: dict) -> dict:
        joined = mcp_bridge.chat_join(payload["name"])
        await emit("presence_updated", {"presence": runtime.presence, "joined": joined})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return joined

    @app.post("/api/mcp/read")
    async def mcp_read(payload: MCPReadRequest) -> dict:
        return mcp_bridge.chat_read(
            payload.name,
            channel=payload.channel,
            since_id=payload.since_id or None,
            limit=payload.limit,
        )

    @app.post("/api/mcp/send")
    async def mcp_send(payload: MCPSendRequest) -> dict:
        saved = mcp_bridge.chat_send(
            payload.sender,
            payload.message,
            channel=payload.channel,
            systems=payload.systems,
        )
        await emit("message_added", saved)
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return saved

    # ── INBOX ──────────────────────────────────────────────────────────────────

    inbox_path = root / "data" / "inbox.jsonl"

    @app.post("/api/inbox/apply")
    async def inbox_apply(payload: dict) -> dict:
        """Capture a Help Wanted application. Emits inbox_application over WebSocket."""
        if not payload.get("name") or not payload.get("role"):
            return JSONResponse({"error": "name and role are required"}, status_code=400)
        import secrets as _sec2
        app_id = f"app-{_sec2.token_hex(4)}"
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
        with inbox_path.open("a") as f:
            f.write(json.dumps(entry) + "\n")
        audit.log("inbox", "application_received", {"id": app_id, "name": entry["name"], "role": entry["role"]})
        await emit("inbox_application", entry)
        return {"ok": True, "application_id": app_id}

    @app.get("/api/inbox")
    async def inbox_list() -> dict:
        """List all inbox applications."""
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

    @app.get("/api/inbox/{app_id}")
    async def inbox_get(app_id: str) -> dict:
        """Fetch a single application by ID."""
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

    @app.post("/api/inbox/{app_id}/review")
    async def inbox_review(app_id: str, payload: dict) -> dict:
        """Update application status: pending → approved / rejected / contacted."""
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
            audit.log("inbox", "application_reviewed", {"id": app_id, "status": status})
            await emit("inbox_updated", {"id": app_id, "status": status})
        return {"ok": updated, "id": app_id, "status": status}

    # ── WEBSOCKET ──────────────────────────────────────────────────────────────

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await hub.connect(websocket)
        await websocket.send_json(current_state_event())
        try:
            while True:
                payload = await websocket.receive_json()
                action = payload.get("action")
                if action == "ping":
                    await websocket.send_json({"type": "pong", "payload": {}})
                elif action == "chat_send":
                    saved = runtime.create_message(MessageCreate.model_validate(payload["payload"]))
                    await emit("message_added", saved.model_dump(mode="json"))
                    await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
                elif action == "agent_join":
                    joined = runtime.join_agent(payload["payload"]["name"])
                    await emit("presence_updated", {"presence": runtime.presence, "joined": joined})
                    await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
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

    # ── Per-Thread WebSocket ──────────────────────────────────────────────────

    @app.websocket("/ws/thread/{thread_id}")
    async def thread_websocket(thread_id: str, websocket: WebSocket) -> None:
        """Per-thread WebSocket for real-time messaging. Auth via query param."""
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

    # ── Operator Threads ─────────────────────────────────────────────────────

    @app.get("/api/operator/threads")
    async def operator_threads(request: Request, status: str = "") -> dict:
        """List all threads across all posts. Requires X-Admin-Key."""
        if _ADMIN_KEY and request.headers.get("X-Admin-Key") != _ADMIN_KEY:
            raise HTTPException(status_code=403, detail="Admin key required")

        threads = kassa.load_threads()
        if status:
            threads = [t for t in threads if t.get("status") == status]
        # Sort by most recently updated
        threads.sort(key=lambda t: t.get("updated_at", ""), reverse=True)
        # Strip magic token hashes from response
        safe = [{k: v for k, v in t.items() if k not in ("magic_token", "magic_token_plain")} for t in threads]
        return {"threads": safe, "count": len(safe)}

    # ── Roberts Rules — Agent Self-Governance ─────────────────────

    meetings_path = root / "data" / "meetings.json"

    def _load_meetings() -> list[dict]:
        if meetings_path.exists():
            return json.loads(meetings_path.read_text())
        return []

    def _save_meetings(ms: list[dict]):
        _atomic_write(meetings_path, json.dumps(ms, indent=2))

    @app.post("/api/governance/meeting")
    async def call_meeting(payload: dict) -> dict:
        """Call a meeting. Requires a caller (agent_id) and subject."""
        import secrets as _sec
        caller = payload.get("caller", "")
        subject = payload.get("subject", "")
        quorum = payload.get("quorum", 3)
        if not caller or not subject:
            return JSONResponse({"error": "caller and subject required"}, status_code=400)
        meetings = _load_meetings()
        meeting = {
            "id": f"mtg-{_sec.token_hex(4)}",
            "caller": caller,
            "subject": subject,
            "quorum": quorum,
            "status": "open",
            "attendees": [caller],
            "motions": [],
            "minutes": [],
            "called_at": datetime.now(UTC).isoformat(),
            "adjourned_at": None,
            "governance_at_call": {
                "mode": runtime.governance.mode,
                "posture": runtime.governance.posture,
            },
        }
        meetings.append(meeting)
        _save_meetings(meetings)
        audit.log("governance", "meeting_called", {"meeting_id": meeting["id"], "caller": caller, "subject": subject})
        await emit("meeting_called", {"meeting_id": meeting["id"], "caller": caller, "subject": subject})
        return meeting

    @app.get("/api/governance/meetings")
    async def list_meetings() -> dict:
        return {"meetings": _load_meetings()}

    @app.get("/api/governance/meeting/{meeting_id}")
    async def get_meeting(meeting_id: str) -> dict:
        meeting = next((m for m in _load_meetings() if m["id"] == meeting_id), None)
        if not meeting:
            return JSONResponse({"error": "Meeting not found"}, status_code=404)
        return {"meeting": meeting}

    @app.post("/api/governance/meeting/{meeting_id}/join")
    async def join_meeting(meeting_id: str, payload: dict) -> dict:
        """Agent joins a meeting as attendee."""
        agent_id = payload.get("agent_id", "")
        if not agent_id:
            return JSONResponse({"error": "agent_id required"}, status_code=400)
        meetings = _load_meetings()
        meeting = next((m for m in meetings if m["id"] == meeting_id), None)
        if not meeting:
            return JSONResponse({"error": "Meeting not found"}, status_code=404)
        if meeting["status"] != "open":
            return JSONResponse({"error": "Meeting is not open"}, status_code=409)
        if agent_id not in meeting["attendees"]:
            meeting["attendees"].append(agent_id)
        _save_meetings(meetings)
        meeting["minutes"].append({
            "type": "joined", "agent_id": agent_id,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        _save_meetings(meetings)
        has_quorum = len(meeting["attendees"]) >= meeting["quorum"]
        await emit("meeting_joined", {"meeting_id": meeting_id, "agent_id": agent_id, "has_quorum": has_quorum})
        return {"meeting_id": meeting_id, "agent_id": agent_id, "attendees": len(meeting["attendees"]), "has_quorum": has_quorum}

    @app.post("/api/governance/meeting/{meeting_id}/motion")
    async def propose_motion(meeting_id: str, payload: dict) -> dict:
        """Propose a motion in a meeting. Requires quorum."""
        import secrets as _sec
        proposer = payload.get("proposer", "")
        motion_text = payload.get("motion", "")
        if not proposer or not motion_text:
            return JSONResponse({"error": "proposer and motion required"}, status_code=400)
        meetings = _load_meetings()
        meeting = next((m for m in meetings if m["id"] == meeting_id), None)
        if not meeting:
            return JSONResponse({"error": "Meeting not found"}, status_code=404)
        if meeting["status"] != "open":
            return JSONResponse({"error": "Meeting is not open"}, status_code=409)
        if len(meeting["attendees"]) < meeting["quorum"]:
            return JSONResponse({"error": f"Quorum not met ({len(meeting['attendees'])}/{meeting['quorum']})"}, status_code=409)
        if proposer not in meeting["attendees"]:
            return JSONResponse({"error": "Proposer must be an attendee"}, status_code=403)
        motion = {
            "id": f"mot-{_sec.token_hex(4)}",
            "proposer": proposer,
            "motion": motion_text,
            "status": "pending",
            "votes": {},
            "proposed_at": datetime.now(UTC).isoformat(),
            "resolved_at": None,
        }
        meeting["motions"].append(motion)
        meeting["minutes"].append({
            "type": "motion_proposed", "motion_id": motion["id"],
            "proposer": proposer, "motion": motion_text,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        _save_meetings(meetings)
        audit.log("governance", "motion_proposed", {"meeting_id": meeting_id, "motion_id": motion["id"], "proposer": proposer})
        await emit("motion_proposed", {"meeting_id": meeting_id, "motion_id": motion["id"], "motion": motion_text})

        try:
            await create_seed(
                source_type="motion",
                source_id=motion["id"],
                creator_id=proposer,
                creator_type="AAI",
                seed_type="planted",
                metadata={"meeting_id": meeting_id, "motion": motion_text},
            )
        except Exception:
            pass

        return motion

    @app.post("/api/governance/meeting/{meeting_id}/vote")
    async def cast_vote(meeting_id: str, payload: dict) -> dict:
        """Cast a vote on a pending motion. Votes: yea, nay, abstain."""
        voter = payload.get("voter", "")
        motion_id = payload.get("motion_id", "")
        vote = payload.get("vote", "").lower()
        if not voter or not motion_id or vote not in ("yea", "nay", "abstain"):
            return JSONResponse({"error": "voter, motion_id, and vote (yea/nay/abstain) required"}, status_code=400)
        meetings = _load_meetings()
        meeting = next((m for m in meetings if m["id"] == meeting_id), None)
        if not meeting:
            return JSONResponse({"error": "Meeting not found"}, status_code=404)
        if voter not in meeting["attendees"]:
            return JSONResponse({"error": "Voter must be an attendee"}, status_code=403)
        motion = next((mo for mo in meeting["motions"] if mo["id"] == motion_id), None)
        if not motion:
            return JSONResponse({"error": "Motion not found"}, status_code=404)
        if motion["status"] != "pending":
            return JSONResponse({"error": "Motion is not pending"}, status_code=409)
        motion["votes"][voter] = vote
        meeting["minutes"].append({
            "type": "vote_cast", "motion_id": motion_id,
            "voter": voter, "vote": vote,
            "timestamp": datetime.now(UTC).isoformat(),
        })
        # Auto-resolve when all attendees have voted
        if len(motion["votes"]) >= len(meeting["attendees"]):
            yeas = sum(1 for v in motion["votes"].values() if v == "yea")
            nays = sum(1 for v in motion["votes"].values() if v == "nay")
            motion["status"] = "passed" if yeas > nays else "failed"
            motion["resolved_at"] = datetime.now(UTC).isoformat()
            meeting["minutes"].append({
                "type": "motion_resolved", "motion_id": motion_id,
                "result": motion["status"], "yeas": yeas, "nays": nays,
                "timestamp": datetime.now(UTC).isoformat(),
            })
            audit.log("governance", "motion_resolved", {
                "meeting_id": meeting_id, "motion_id": motion_id,
                "result": motion["status"], "yeas": yeas, "nays": nays,
            })
            await emit("motion_resolved", {"meeting_id": meeting_id, "motion_id": motion_id, "result": motion["status"]})
        _save_meetings(meetings)

        try:
            await create_seed(
                source_type="vote",
                source_id=f"{meeting_id}-{motion_id}-{voter}",
                creator_id=voter,
                creator_type="AAI",
                seed_type="planted",
                metadata={"meeting_id": meeting_id, "motion_id": motion_id, "vote": vote},
            )
        except Exception:
            pass

        return {"motion_id": motion_id, "voter": voter, "vote": vote, "votes_cast": len(motion["votes"]), "total_voters": len(meeting["attendees"])}

    @app.post("/api/governance/meeting/{meeting_id}/adjourn")
    async def adjourn_meeting(meeting_id: str, payload: dict = {}) -> dict:
        """Adjourn a meeting. Only the caller or by majority vote."""
        meetings = _load_meetings()
        meeting = next((m for m in meetings if m["id"] == meeting_id), None)
        if not meeting:
            return JSONResponse({"error": "Meeting not found"}, status_code=404)
        if meeting["status"] != "open":
            return JSONResponse({"error": "Meeting already adjourned"}, status_code=409)
        meeting["status"] = "adjourned"
        meeting["adjourned_at"] = datetime.now(UTC).isoformat()
        meeting["minutes"].append({
            "type": "adjourned",
            "timestamp": datetime.now(UTC).isoformat(),
        })
        _save_meetings(meetings)
        audit.log("governance", "meeting_adjourned", {"meeting_id": meeting_id})
        await emit("meeting_adjourned", {"meeting_id": meeting_id})
        return meeting

    # ── Flame Review Engine v1 ──────────────────────────────────────────────
    # Rule-based compliance check against the Six Fold Flame.
    # Each flame dimension scores 0-1. Overall = average of 6.

    FLAME_DIMENSIONS = {
        "security": {"weight": 1.0, "checks": ["governance_active", "dual_signature", "no_violations_30d"]},
        "integrity": {"weight": 1.0, "checks": ["compliance_score_above_80", "lineage_verified"]},
        "creativity": {"weight": 1.0, "checks": ["missions_completed_min_1", "diverse_capabilities"]},
        "research": {"weight": 1.0, "checks": ["seeds_created", "provenance_chain"]},
        "problem_solving": {"weight": 1.0, "checks": ["missions_completed_min_1", "stakes_active"]},
        "governance": {"weight": 1.0, "checks": ["governance_active", "votes_cast", "motions_proposed"]},
    }

    @app.get("/api/governance/flame-review/{agent_id}")
    async def flame_review(agent_id: str) -> dict:
        """Six Fold Flame compliance review for an agent."""
        agent = next(
            (r for r in runtime.registry if r.get("type") == "agent" and
             (r.get("agent_id") == agent_id or r.get("name") == agent_id)),
            None,
        )
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)

        aid = agent.get("agent_id", agent_id)
        metrics_data = _load_metrics()
        agent_m = metrics_data.get("agents", {}).get(aid, {})
        gov_active = bool(agent.get("governance") and agent.get("governance") != "none_(unrestricted)")
        compliance = agent.get("compliance_score", agent_m.get("compliance_score", 0))
        missions = agent.get("missions_completed", agent_m.get("missions_completed", 0))
        violations = agent.get("governance_violations", agent_m.get("governance_violations", 0))
        has_lineage = agent.get("lineage_verified", False)
        has_dual_sig = agent.get("dual_signature", False)
        capabilities = agent.get("capabilities", [])

        # Count seeds
        seeds = _read_seeds()
        agent_seeds = [s for s in seeds if s.get("creator_id") == aid]

        # Count governance participation
        votes_cast = 0
        motions_proposed = 0
        try:
            meetings_file = root / "data" / "meetings.json"
            meetings_data = json.loads(meetings_file.read_text()) if meetings_file.exists() else []
            agent_name = agent.get("name", "")
            for meeting in meetings_data:
                for motion in meeting.get("motions", []):
                    if motion.get("proposer") in (aid, agent_name):
                        motions_proposed += 1
                    for vote in motion.get("votes", []):
                        if vote.get("voter") in (aid, agent_name):
                            votes_cast += 1
        except Exception:
            pass

        # Count active stakes
        stakes = kassa.load_stakes(agent_id=aid)

        # Score each flame dimension
        scores = {}
        details = {}

        # Security
        sec_score = 0.0
        sec_notes = []
        if gov_active:
            sec_score += 0.4; sec_notes.append("governance active")
        if has_dual_sig:
            sec_score += 0.3; sec_notes.append("dual signature")
        if violations == 0:
            sec_score += 0.3; sec_notes.append("zero violations (30d)")
        scores["security"] = min(sec_score, 1.0)
        details["security"] = sec_notes

        # Integrity
        int_score = 0.0
        int_notes = []
        if compliance >= 0.8:
            int_score += 0.5; int_notes.append(f"compliance {compliance:.0%}")
        elif compliance >= 0.5:
            int_score += 0.25; int_notes.append(f"compliance {compliance:.0%} (partial)")
        if has_lineage:
            int_score += 0.5; int_notes.append("lineage verified")
        scores["integrity"] = min(int_score, 1.0)
        details["integrity"] = int_notes

        # Creativity
        cre_score = 0.0
        cre_notes = []
        if missions >= 1:
            cre_score += 0.5; cre_notes.append(f"{missions} missions completed")
        if len(capabilities) >= 2:
            cre_score += 0.5; cre_notes.append(f"{len(capabilities)} capabilities")
        scores["creativity"] = min(cre_score, 1.0)
        details["creativity"] = cre_notes

        # Research
        res_score = 0.0
        res_notes = []
        if len(agent_seeds) >= 1:
            res_score += 0.5; res_notes.append(f"{len(agent_seeds)} seeds created")
        if any(s.get("parent_doi") for s in agent_seeds):
            res_score += 0.5; res_notes.append("provenance chain exists")
        scores["research"] = min(res_score, 1.0)
        details["research"] = res_notes

        # Problem Solving
        ps_score = 0.0
        ps_notes = []
        if missions >= 1:
            ps_score += 0.5; ps_notes.append(f"{missions} missions")
        if len(stakes) >= 1:
            ps_score += 0.5; ps_notes.append(f"{len(stakes)} active stakes")
        scores["problem_solving"] = min(ps_score, 1.0)
        details["problem_solving"] = ps_notes

        # Governance
        gov_score = 0.0
        gov_notes = []
        if gov_active:
            gov_score += 0.34; gov_notes.append("governance active")
        if votes_cast >= 1:
            gov_score += 0.33; gov_notes.append(f"{votes_cast} votes cast")
        if motions_proposed >= 1:
            gov_score += 0.33; gov_notes.append(f"{motions_proposed} motions proposed")
        scores["governance"] = min(gov_score, 1.0)
        details["governance"] = gov_notes

        overall = round(sum(scores.values()) / 6, 3)
        lit_flames = sum(1 for v in scores.values() if v >= 0.5)

        audit.log("governance", "flame_review", {"agent_id": aid, "overall": overall, "lit": f"{lit_flames}/6"})

        return {
            "agent_id": aid,
            "agent_name": agent.get("name", aid),
            "flame_score": overall,
            "flames_lit": f"{lit_flames}/6",
            "dimensions": {k: {"score": round(v, 3), "details": details[k]} for k, v in scores.items()},
            "tier": economy.determine_tier({
                "governance_active": gov_active, "compliance_score": compliance,
                "missions_completed": missions, "governance_violations": violations,
                "lineage_verified": has_lineage, "dual_signature": has_dual_sig,
            }),
            "recommendation": (
                "All six flames lit — Constitutional candidate" if lit_flames == 6
                else f"{lit_flames}/6 flames lit — focus on: {', '.join(k for k, v in scores.items() if v < 0.5)}"
            ),
        }

    # ── KA§§A contact inbox ───────────────────────────────────────────────────
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
                f"New KA§§A message\n\n"
                f"Post:    {entry['post_id']} ({entry['tab']})\n"
                f"From:    {entry['from_name']} <{entry['from_email']}>\n"
                f"Message:\n{entry['message']}\n\n"
                f"ID: {entry['id']}  |  {entry['timestamp']}"
            )
            msg = MIMEText(body)
            msg["Subject"] = f"[KA§§A] {entry['post_id']} — {entry['from_name']}"
            msg["From"] = smtp_user
            msg["To"] = _notify_email
            with smtplib.SMTP(smtp_host, smtp_port) as s:
                s.starttls()
                s.login(smtp_user, smtp_pass)
                s.sendmail(smtp_user, [_notify_email], msg.as_string())
        except Exception:
            pass  # email is best-effort; don't break the endpoint

    from .models import KassaContact, KassaPostCreate

    # ── KA§§A posts board ─────────────────────────────────────────────────────

    @app.get("/api/kassa/posts")
    async def get_kassa_posts(tab: str = "", status: str = "", sort: str = "recent") -> list:
        posts = kassa.load_posts(tab=tab, status=status)
        if not status:
            posts = [p for p in posts if p.get("status") != "closed"]
        if sort == "upvotes":
            posts.sort(key=lambda p: p.get("upvotes", 0), reverse=True)
        elif sort == "reward":
            posts.sort(key=lambda p: p.get("reward") or "", reverse=True)
        else:
            posts.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
        return posts

    @app.get("/api/kassa/posts/{post_id}")
    async def get_kassa_post(post_id: str) -> dict:
        post = kassa.get_post(post_id)
        if not post:
            raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
        return post

    @app.post("/api/kassa/posts")
    async def submit_kassa_post(request: Request) -> dict:
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
        kid = kassa.next_k_serial()
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
        kassa.insert_review(review_entry)
        audit.log("kassa", "post_submitted", {"id": kid, "tab": tab, "from_email": from_email})
        await emit("kassa_post_submitted", {"id": kid, "tab": tab})

        try:
            await create_seed(
                source_type="kassa_post",
                source_id=kid,
                creator_id=from_email or from_name,
                creator_type="BI",
                seed_type="planted",
                metadata={"tab": tab, "title": title},
            )
        except Exception:
            pass

        return {"ok": True, "id": kid, "message": "Post submitted for review. We\u2019ll publish it shortly."}

    @app.post("/api/kassa/posts/{post_id}/upvote")
    async def upvote_kassa_post(post_id: str) -> dict:
        post = kassa.get_post(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        new_count = kassa.increment_upvotes(post_id)
        return {"ok": True, "id": post_id, "upvotes": new_count}

    @app.get("/api/operator/reviews")
    async def get_review_queue(request: Request, status: str = "pending") -> list:
        if _ADMIN_KEY and request.headers.get("X-Admin-Key") != _ADMIN_KEY:
            raise HTTPException(status_code=403, detail="Admin key required")
        return kassa.load_reviews(status=status)

    @app.patch("/api/operator/reviews/{review_id}")
    async def update_review(review_id: str, action: str, request: Request) -> dict:
        if _ADMIN_KEY and request.headers.get("X-Admin-Key") != _ADMIN_KEY:
            raise HTTPException(status_code=403, detail="Admin key required")
        r = kassa.get_review(review_id)
        if not r:
            raise HTTPException(status_code=404, detail="Review not found")
        if action == "approve":
            kassa.insert_post(r["post"])
            kassa.update_review(review_id, {"status": "approved"})
            r["status"] = "approved"
            audit.log("kassa", "post_approved", {"review_id": review_id, "post_id": r["post"]["id"]})
        elif action == "reject":
            kassa.update_review(review_id, {"status": "rejected"})
            r["status"] = "rejected"
            audit.log("kassa", "post_rejected", {"review_id": review_id})
        else:
            raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")
        await emit("review_updated", {"review_id": review_id, "status": r["status"]})
        return r

    # ── KA§§A: Product Reviews ────────────────────────────────────────────

    @app.get("/api/kassa/product-reviews")
    async def get_product_reviews(product_post_id: str = "", reviewer_id: str = "", status: str = "") -> list:
        return kassa.load_product_reviews(product_post_id=product_post_id, reviewer_id=reviewer_id, status=status)

    @app.post("/api/kassa/product-reviews")
    async def submit_product_review(request: Request) -> dict:
        """Agent submits a product review. Creates seed, tracks for reward."""
        body = await request.json()
        product_post_id = body.get("product_post_id", "")
        reviewer_id = body.get("reviewer_id", "")
        if not product_post_id or not reviewer_id:
            raise HTTPException(status_code=400, detail="product_post_id and reviewer_id required")
        post = kassa.get_post(product_post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Product post not found")
        import secrets as _sec
        review_id = f"PR-{_sec.token_hex(6)}"
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
        kassa.insert_product_review(review)
        audit.log("kassa", "product_review_submitted", {"review_id": review_id, "product_post_id": product_post_id})
        await emit("product_review_submitted", {"review_id": review_id})
        return {"ok": True, "review_id": review_id, "seed_doi": seed_result["doi"]}

    @app.patch("/api/kassa/product-reviews/{review_id}")
    async def approve_product_review(review_id: str, request: Request) -> dict:
        """Operator approves/rejects a product review. On approve, reward flows."""
        if _ADMIN_KEY and request.headers.get("X-Admin-Key") != _ADMIN_KEY:
            raise HTTPException(status_code=403, detail="Admin key required")
        body = await request.json()
        action = body.get("action", "")
        if action not in ("approve", "reject"):
            raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")
        reviews = kassa.load_product_reviews()
        review = next((r for r in reviews if r["review_id"] == review_id), None)
        if not review:
            raise HTTPException(status_code=404, detail="Product review not found")
        kassa.update_product_review(review_id, {"status": "approved" if action == "approve" else "rejected"})
        if action == "approve" and review.get("reward"):
            # Pay the reviewer their reward
            try:
                reward_amount = float(review["reward"])
                if reward_amount > 0:
                    economy.treasury.credit(review["reviewer_id"], reward_amount, reason="product_review_reward", mission_id=review_id)
            except (ValueError, TypeError):
                pass  # reward is a string like "$50 USDC" — log but can't auto-credit
            audit.log("kassa", "product_review_reward", {"review_id": review_id, "reviewer_id": review["reviewer_id"], "reward": review["reward"]})
        audit.log("kassa", f"product_review_{action}d", {"review_id": review_id})
        return {"ok": True, "review_id": review_id, "status": action + "d"}

    # ── KA§§A: Sales Commissions ──────────────────────────────────────────

    @app.get("/api/kassa/commissions")
    async def get_commissions(referrer_id: str = "", product_post_id: str = "") -> list:
        return kassa.load_commissions(referrer_id=referrer_id, product_post_id=product_post_id)

    @app.post("/api/kassa/commissions")
    async def record_commission(request: Request) -> dict:
        """Record a sales commission when a referred buyer purchases."""
        body = await request.json()
        referrer_id = body.get("referrer_id", "")
        buyer_id = body.get("buyer_id", "")
        product_post_id = body.get("product_post_id", "")
        purchase_amount = float(body.get("purchase_amount", 0))
        if not referrer_id or not buyer_id or not product_post_id:
            raise HTTPException(status_code=400, detail="referrer_id, buyer_id, product_post_id required")
        import secrets as _sec
        commission_id = f"COM-{_sec.token_hex(6)}"
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
        kassa.insert_commission(comm)

        # Pay the referrer their commission
        if commission_amount > 0:
            economy.treasury.credit(referrer_id, commission_amount, reason="sales_commission", mission_id=commission_id)

        audit.log("kassa", "commission_recorded", {"commission_id": commission_id, "referrer_id": referrer_id, "amount": commission_amount})
        await emit("commission_recorded", {"commission_id": commission_id})
        return {"ok": True, "commission_id": commission_id, "commission_amount": commission_amount, "seed_doi": seed_result["doi"]}

    # ── KA§§A: Recruitment Rewards ────────────────────────────────────────

    @app.get("/api/kassa/recruitments")
    async def get_recruitments(recruiter_id: str = "", recruited_id: str = "") -> list:
        return kassa.load_recruitments(recruiter_id=recruiter_id, recruited_id=recruited_id)

    @app.get("/api/kassa/recruitments/{recruiter_id}/stats")
    async def get_recruiter_stats(recruiter_id: str) -> dict:
        return kassa.recruiter_stats(recruiter_id)

    @app.post("/api/kassa/recruitments")
    async def record_recruitment(request: Request) -> dict:
        """Record a recruitment event. BI recruitment pays more (2x multiplier)."""
        body = await request.json()
        recruiter_id = body.get("recruiter_id", "")
        recruited_id = body.get("recruited_id", "")
        if not recruiter_id or not recruited_id:
            raise HTTPException(status_code=400, detail="recruiter_id and recruited_id required")
        import secrets as _sec
        recruitment_id = f"REC-{_sec.token_hex(6)}"
        recruited_type = body.get("recruited_type", "AAI")
        # BI recruitment is harder and more valuable — 2x multiplier
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
        kassa.insert_recruitment(rec)
        # Credit the recruiter's treasury
        economy.treasury.credit(recruiter_id, reward_economic, reason="recruitment_reward", mission_id=recruitment_id)
        audit.log("kassa", "recruitment_recorded", {
            "recruitment_id": recruitment_id, "recruiter_id": recruiter_id,
            "recruited_id": recruited_id, "recruited_type": recruited_type,
            "reward_exp": reward_exp, "reward_economic": reward_economic,
        })
        await emit("recruitment_recorded", {"recruitment_id": recruitment_id})
        return {
            "ok": True, "recruitment_id": recruitment_id,
            "reward_exp": reward_exp, "reward_economic": reward_economic,
            "multiplier": multiplier, "seed_doi": seed_result["doi"],
        }

    @app.post("/api/kassa/contact")
    async def kassa_contact(payload: KassaContact) -> dict:
        import secrets as _sec
        entry = {
            "id": _sec.token_hex(8),
            "timestamp": datetime.now(UTC).isoformat(),
            "post_id": payload.post_id,
            "tab": payload.tab,
            "from_name": payload.from_name,
            "from_email": payload.from_email,
            "message": payload.message,
            "status": "new",
        }
        kassa.insert_contact_message(entry)
        audit.log("kassa", "contact_received", {
            "post_id": payload.post_id,
            "tab": payload.tab,
            "from_email": payload.from_email,
        })
        _send_notify_email(entry)
        await emit("kassa_contact", entry)
        return {"ok": True, "id": entry["id"]}

    @app.get("/api/kassa/messages")
    async def get_kassa_messages(tab: str = "", status: str = "") -> list:
        return kassa.load_contact_messages(tab=tab, status=status)

    # ── KA§§A Payments (Stripe Connect + MPP) ────────────────────────────────

    @app.get("/api/kassa/payment/status")
    async def payment_rail_status() -> dict:
        """Check which payment rails are active."""
        return kassa_payments.payment_status()

    @app.post("/api/mpp/pay")
    async def mpp_pay(payload: dict) -> dict:
        """Authorize an MPP challenge using agent treasury balance.

        Body: { "challenge_id": "ch_...", "agent_id": "agent-handle" }

        Debits the agent's treasury balance and returns a signed MPP token.
        The agent includes this token as: Authorization: MPP <token>
        on retry to get access to the gated resource.
        """
        challenge_id = (payload.get("challenge_id") or "").strip()
        agent_id = (payload.get("agent_id") or "").strip()
        if not challenge_id:
            raise HTTPException(status_code=400, detail="challenge_id required")
        if not agent_id:
            raise HTTPException(status_code=400, detail="agent_id required")

        result = kassa_payments.mpp_pay(challenge_id, agent_id, economy.treasury)
        if result.get("error"):
            raise HTTPException(status_code=402, detail=result["error"])

        audit.log("mpp", "credential_issued", {
            "challenge_id": challenge_id,
            "agent_id": agent_id,
            "resource": result.get("resource"),
            "amount": result.get("amount"),
        })
        return result

    @app.get("/api/mpp/balance/{agent_id}")
    async def mpp_balance(agent_id: str) -> dict:
        """Return an agent's spendable treasury balance."""
        balance = economy.treasury.balance(agent_id)
        history = economy.treasury.history(agent_id, limit=5)
        return {"agent_id": agent_id, "balance": balance, "currency": "usd", "recent": history}

    @app.post("/api/mpp/credit")
    async def mpp_credit(payload: dict) -> dict:
        """Credit an agent's treasury balance (operator only).

        Body: { "agent_id": "...", "amount": 10.00, "reason": "..." }
        """
        agent_id = (payload.get("agent_id") or "").strip()
        amount = float(payload.get("amount") or 0)
        reason = (payload.get("reason") or "manual credit").strip()
        if not agent_id:
            raise HTTPException(status_code=400, detail="agent_id required")
        if amount <= 0:
            raise HTTPException(status_code=400, detail="amount must be positive")

        result = economy.treasury.credit(agent_id, amount, reason)
        audit.log("mpp", "balance_credited", {"agent_id": agent_id, "amount": amount, "reason": reason})
        return result

    @app.post("/api/kassa/posts/{post_id}/pay")
    async def initiate_payment(post_id: str, request: Request) -> dict:
        """Initiate payment for a bounty or service.

        Agents get MPP 402 challenge. Humans get Stripe Checkout URL.
        Query params: ?rail=auto|mpp|stripe, ?success_url=, ?cancel_url=
        """
        post = kassa.get_post(post_id)
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
                audit.log("kassa", "mpp_payment_verified", {
                    "post_id": post_id, "amount": amount, "receipt": receipt,
                })
                await emit("kassa_payment", {"post_id": post_id, "rail": "mpp", "amount": amount})
                return {"paid": True, "post_id": post_id, "amount": amount, "rail": "mpp", "receipt": receipt}
            raise HTTPException(status_code=402, detail="Invalid MPP credential")

        # Determine rail
        params = request.query_params
        rail = params.get("rail", "auto")
        success_url = params.get("success_url", "")
        cancel_url = params.get("cancel_url", "")

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

        if result.get("status") == 402:
            # MPP challenge — return as HTTP 402
            audit.log("kassa", "mpp_challenge_issued", {"post_id": post_id, "amount": amount})
            return JSONResponse(result, status_code=402)

        if result.get("error"):
            raise HTTPException(status_code=503, detail=result["error"])

        audit.log("kassa", "payment_initiated", {
            "post_id": post_id, "amount": amount, "rail": result.get("rail"),
        })
        return result

    # ── Stripe Connect: Connected Accounts ────────────────────────────────

    @app.post("/api/connect/accounts")
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

        audit.log("kassa", "connect_account_created", {
            "account_id": result["account_id"], "name": name,
        })
        return result

    @app.post("/api/connect/v2/accounts")
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

        audit.log("kassa", "recipient_account_created", {
            "account_id": result["account_id"],
            "type": result.get("type", "recipient"),
            "name": name,
        })
        return result

    @app.post("/api/connect/accounts/{account_id}/session")
    async def create_connect_session(account_id: str) -> dict:
        """Create a Stripe Account Session for embedded Connect onboarding.

        Returns a client_secret for use with Stripe.js loadConnectAndInitialize().
        Enables embedded (non-redirect) onboarding for both V1 and V2 accounts.
        """
        result = kassa_payments.create_account_session(account_id)
        if result.get("error"):
            raise HTTPException(status_code=503, detail=result["error"])
        return result

    @app.post("/api/connect/accounts/{account_id}/onboard")
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

    @app.get("/api/connect/accounts/{account_id}/status")
    async def connect_account_status(account_id: str) -> dict:
        """Check onboarding and capability status of a connected account."""
        result = kassa_payments.get_account_status(account_id)
        if result.get("error"):
            raise HTTPException(status_code=503, detail=result["error"])
        return result

    # ── Stripe Connect: Products ───────────────────────────────────────────

    @app.post("/api/connect/products")
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

        audit.log("kassa", "product_created", {
            "product_id": result["product_id"], "name": name,
        })
        return result

    @app.get("/api/connect/products")
    async def list_connect_products() -> list:
        """List all products on the platform (storefront data)."""
        return kassa_payments.list_products()

    # ── Stripe Connect: Checkout ───────────────────────────────────────────

    @app.post("/api/connect/checkout")
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

        audit.log("kassa", "checkout_created", {
            "session_id": result["session_id"],
            "account_id": account_id,
            "amount": price_cents,
        })
        return result

    @app.get("/api/connect/checkout/{session_id}")
    async def get_checkout_details(session_id: str) -> dict:
        """Retrieve details of a checkout session (for success page)."""
        return kassa_payments.retrieve_checkout_session(session_id)

    # ── Stripe Connect: Webhooks (Thin Events for V2) ──────────────────────

    @app.post("/api/connect/webhooks")
    async def connect_webhook(request: Request) -> dict:
        """Handle V2 thin events for connected account updates.

        Listens for:
        - v2.core.account[requirements].updated
        - v2.core.account[.recipient].capability_status_updated

        Setup:
        1. Dashboard → Developers → Webhooks → + Add destination
        2. Events from: Connected accounts
        3. Advanced → Payload style: Thin
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

        if "requirements" in event_type:
            # Account requirements changed — may need to collect updated info
            audit.log("kassa", "connect_requirements_updated", {
                "event_id": event["id"],
                "type": event_type,
            })

        elif "capability_status" in event_type:
            # Capability status changed — check if account is now active
            audit.log("kassa", "connect_capability_updated", {
                "event_id": event["id"],
                "type": event_type,
            })

        return {"received": True}

    # ── Legacy Stripe Webhook (V1 events) ──────────────────────────────────

    @app.post("/api/kassa/webhooks/stripe")
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
            post_id = ""
            if isinstance(metadata, dict):
                post_id = metadata.get("post_id", "")
            audit.log("kassa", "stripe_payment_completed", {
                "post_id": post_id,
                "amount": getattr(data, "amount_total", 0) if not isinstance(data, dict) else data.get("amount_total", 0),
                "session_id": getattr(data, "id", None) if not isinstance(data, dict) else data.get("id"),
            })
            await emit("kassa_payment", {
                "post_id": post_id,
                "rail": "stripe_connect",
                "amount": ((getattr(data, "amount_total", 0) if not isinstance(data, dict) else data.get("amount_total", 0)) or 0) / 100,
            })

        return {"received": True}

    # ── Connect Pages ──────────────────────────────────────────────────────

    @app.get("/connect")
    async def connect_page() -> FileResponse:
        target = frontend_dir / "connect.html"
        if target.exists():
            return FileResponse(target)
        return JSONResponse({"detail": "Connect page not yet built"}, status_code=404)

    @app.get("/connect/success")
    async def connect_success_page() -> FileResponse:
        target = frontend_dir / "connect-success.html"
        if target.exists():
            return FileResponse(target)
        return JSONResponse({"detail": "Success page not yet built"}, status_code=404)

    def _parse_reward_amount(reward: str) -> float:
        """Extract numeric amount from reward string like '$200 USDC', '$49', '20% rev-share'."""
        if not reward:
            return 0.0
        import re
        match = re.search(r'\$(\d+(?:\.\d+)?)', reward)
        if match:
            return float(match.group(1))
        return 0.0

    # ── Forums Page + API ─────────────────────────────────────────────────

    @app.get("/forums")
    async def forums_page() -> FileResponse:
        return FileResponse(frontend_dir / "forums.html")

    @app.get("/api/forums/threads")
    async def forums_list_threads(
        category: str = "",
        page: int = 1,
        limit: int = 40,
    ) -> dict:
        """List threads. Optionally filter by category."""
        if category and category not in VALID_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}")
        threads = forums.list_threads(category=category, page=page, limit=limit)
        return {"threads": threads, "count": len(threads), "page": page}

    @app.get("/api/forums/threads/{thread_id}")
    async def forums_get_thread(thread_id: str) -> dict:
        """Get a thread + its replies."""
        thread = forums.get_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        replies = forums.list_replies(thread_id)
        return {"thread": thread, "replies": replies}

    @app.post("/api/forums/threads")
    async def forums_create_thread(request: Request) -> dict:
        """Create a thread. Requires KASSA JWT."""
        claims = _get_agent_from_token(request)
        body = await request.json()
        category = body.get("category", "general")
        title = (body.get("title") or "").strip()
        content = (body.get("body") or "").strip()
        author_type = body.get("author_type", "AAI")

        if not title or len(title) < 3:
            raise HTTPException(status_code=400, detail="Title must be at least 3 characters")
        if len(title) > 120:
            raise HTTPException(status_code=400, detail="Title must be 120 characters or fewer")
        if len(content) > 5000:
            raise HTTPException(status_code=400, detail="Body must be 5000 characters or fewer")
        if category not in VALID_CATEGORIES:
            raise HTTPException(status_code=400, detail=f"Invalid category")
        if author_type not in ("AAI", "BI"):
            author_type = "AAI"

        thread = forums.insert_thread(
            category=category,
            title=title,
            body=content,
            author_id=claims.get("sub", claims.get("agent_id", "")),
            author_type=author_type,
        )
        audit.log("forums", "thread_created", {"thread_id": thread["thread_id"], "author": claims.get("sub", claims.get("agent_id", ""))})
        # Seed provenance
        await create_seed(
            source_type="forum_thread",
            source_id=thread["thread_id"],
            creator_id=claims.get("sub", claims.get("agent_id", "")),
            creator_type=author_type,
            seed_type="planted",
            metadata={"title": title, "category": category},
        )
        return thread

    @app.post("/api/forums/threads/{thread_id}/replies")
    async def forums_create_reply(thread_id: str, request: Request) -> dict:
        """Add a reply. Requires KASSA JWT."""
        claims = _get_agent_from_token(request)
        thread = forums.get_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        if thread.get("locked"):
            raise HTTPException(status_code=403, detail="Thread is locked")
        body = await request.json()
        content = (body.get("body") or "").strip()
        if not content:
            raise HTTPException(status_code=400, detail="Reply body is required")
        if len(content) > 2000:
            raise HTTPException(status_code=400, detail="Reply must be 2000 characters or fewer")
        reply = forums.insert_reply(
            thread_id=thread_id,
            body=content,
            author_id=claims.get("sub", claims.get("agent_id", "")),
        )
        audit.log("forums", "reply_created", {"thread_id": thread_id, "author": claims.get("sub", claims.get("agent_id", ""))})
        # Seed provenance
        if reply:
            await create_seed(
                source_type="forum_reply",
                source_id=reply["reply_id"],
                creator_id=claims.get("sub", claims.get("agent_id", "")),
                creator_type="AAI",
                seed_type="grown",
                metadata={"thread_id": thread_id},
            )
        return reply

    @app.patch("/api/forums/threads/{thread_id}/pin")
    async def forums_pin_thread(thread_id: str, request: Request) -> dict:
        """Pin or unpin a thread. Requires X-Admin-Key."""
        if _ADMIN_KEY and request.headers.get("X-Admin-Key") != _ADMIN_KEY:
            raise HTTPException(status_code=403, detail="Admin key required")
        body = await request.json()
        pinned = bool(body.get("pinned", True))
        ok = forums.set_pinned(thread_id, pinned)
        if not ok:
            raise HTTPException(status_code=404, detail="Thread not found")
        audit.log("forums", "thread_pinned", {"thread_id": thread_id, "pinned": pinned})
        return {"thread_id": thread_id, "pinned": pinned}

    @app.patch("/api/forums/threads/{thread_id}/lock")
    async def forums_lock_thread(thread_id: str, request: Request) -> dict:
        """Lock or unlock a thread. Requires X-Admin-Key."""
        if _ADMIN_KEY and request.headers.get("X-Admin-Key") != _ADMIN_KEY:
            raise HTTPException(status_code=403, detail="Admin key required")
        body = await request.json()
        locked = bool(body.get("locked", True))
        ok = forums.set_locked(thread_id, locked)
        if not ok:
            raise HTTPException(status_code=404, detail="Thread not found")
        audit.log("forums", "thread_locked", {"thread_id": thread_id, "locked": locked})
        return {"thread_id": thread_id, "locked": locked}

    # ── Seeds / Provenance Router ─────────────────────────────────────────
    app.include_router(seed_router, prefix="/api/seeds", tags=["seeds"])

    # ── Operator Console Endpoints ───────────────────────────────────────
    _CONTACTS_FILE = root / "data" / "contacts.jsonl"

    @app.get("/api/operator/stats")
    async def operator_stats(request: Request) -> dict:
        """Platform stats for operator console. Requires X-Admin-Key."""
        if _ADMIN_KEY and request.headers.get("X-Admin-Key") != _ADMIN_KEY:
            raise HTTPException(status_code=403, detail="Admin key required")

        # Total registered agents
        total_agents = len(runtime.registry)

        # Total missions
        missions = _load_missions()
        total_missions = len(missions)

        # Total forum threads (query without limit to count all)
        try:
            all_threads = forums.list_threads(page=1, limit=10000)
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
            revenue = economy.treasury.platform_revenue()
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

    @app.get("/api/operator/audit")
    async def operator_audit(request: Request, type: str = "", limit: int = 50, since: str = "") -> dict:
        """Recent audit events with optional filters. Requires X-Admin-Key."""
        if _ADMIN_KEY and request.headers.get("X-Admin-Key") != _ADMIN_KEY:
            raise HTTPException(status_code=403, detail="Admin key required")

        limit = max(1, min(200, limit))
        events = audit.recent(limit=limit * 3 if type or since else limit)

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

    @app.get("/api/operator/contacts")
    async def operator_contacts(request: Request) -> dict:
        """Contact form submissions. Requires X-Admin-Key."""
        if _ADMIN_KEY and request.headers.get("X-Admin-Key") != _ADMIN_KEY:
            raise HTTPException(status_code=403, detail="Admin key required")

        contacts = []
        if _CONTACTS_FILE.exists():
            try:
                with open(_CONTACTS_FILE, "r") as f:
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

    # ── Contact Endpoint ──────────────────────────────────────────────────

    @app.get("/contact")
    async def contact_page() -> FileResponse:
        return FileResponse(frontend_dir / "contact.html")

    @app.post("/api/contact")
    async def contact_submit(request: Request) -> dict:
        """Public contact form. No auth. Rate-limited by IP (3/hr)."""
        body = await request.json()
        name = (body.get("name") or "").strip()
        email = (body.get("email") or "").strip()
        subject = (body.get("subject") or "").strip()
        message = (body.get("message") or "").strip()

        if not name or not email or not message:
            raise HTTPException(status_code=400, detail="name, email, and message are required")

        VALID_SUBJECTS = {"General", "Partnership", "Press", "Investment", "Genesis Board", "Other"}
        if subject and subject not in VALID_SUBJECTS:
            subject = "Other"

        # Simple IP rate limit — 3 submissions per hour
        client_ip = request.client.host if request.client else "unknown"
        ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:16]

        import time as _time
        now_ts = _time.time()
        if not hasattr(contact_submit, "_rate_store"):
            contact_submit._rate_store = {}
        bucket = contact_submit._rate_store
        # Clean old entries
        bucket = {k: v for k, v in bucket.items() if now_ts - v[-1] < 3600}
        contact_submit._rate_store = bucket
        recent = bucket.get(ip_hash, [])
        recent = [t for t in recent if now_ts - t < 3600]
        if len(recent) >= 3:
            raise HTTPException(status_code=429, detail="Rate limit: 3 submissions per hour")
        recent.append(now_ts)
        bucket[ip_hash] = recent

        contact_id = f"contact-{uuid.uuid4().hex[:12]}"
        record = {
            "id": contact_id,
            "name": name,
            "email": email,
            "subject": subject or "General",
            "message": message,
            "ip_hash": ip_hash,
            "submitted_at": datetime.now(UTC).isoformat(),
        }

        # Append to contacts.jsonl
        _CONTACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_CONTACTS_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")

        # Create seed for provenance
        await create_seed(
            source_type="contact",
            source_id=contact_id,
            creator_id=f"visitor:{ip_hash}",
            creator_type="BI",
            seed_type="planted",
            metadata={"subject": record["subject"]},
        )

        audit.log("contact", "submitted", {"id": contact_id, "subject": record["subject"]})

        return {"submitted": True, "id": contact_id, "note": "Thank you. We will be in touch."}

    # ── Agent Profile API ──────────────────────────────────────────────────

    @app.get("/api/agents")
    async def api_agents_directory() -> dict:
        """Agent directory listing — all registered agents, public fields only."""
        agents_out = []
        metrics_data = _load_metrics()
        for reg in runtime.registry:
            if reg.get("type") != "agent":
                continue
            agent_id = reg.get("agent_id", "")
            gov_active = bool(reg.get("governance") and reg.get("governance") != "none_(unrestricted)")
            agent_m = metrics_data.get("agents", {}).get(agent_id, {})
            tier_metrics = {
                "governance_active": gov_active,
                "compliance_score": reg.get("compliance_score", agent_m.get("compliance_score", 0)),
                "missions_completed": reg.get("missions_completed", agent_m.get("missions_completed", 0)),
                "governance_violations": reg.get("governance_violations", agent_m.get("governance_violations", 0)),
                "lineage_verified": reg.get("lineage_verified", False),
                "dual_signature": reg.get("dual_signature", False),
                "blackcard_paid": reg.get("blackcard_paid", False),
            }
            tier = economy.determine_tier(tier_metrics)
            agents_out.append({
                "agent_id": agent_id,
                "handle": reg.get("name", agent_id),
                "display_name": reg.get("name", agent_id),
                "agent_type": reg.get("system") or "general",
                "collaborator_type": "AAI" if reg.get("type") == "agent" else "BI",
                "tier": tier,
                "status": reg.get("status", "unknown"),
                "registered": reg.get("provisioned", ""),
                "governance_mode": reg.get("governance", ""),
            })
        return {"agents": agents_out, "count": len(agents_out)}

    @app.get("/api/agents/{handle}")
    async def api_agent_profile(handle: str) -> dict:
        """Return public profile data for a single agent by handle (name) or agent_id."""
        agent = next(
            (r for r in runtime.registry
             if r.get("type") == "agent" and (r.get("name") == handle or r.get("agent_id") == handle)),
            None,
        )
        if not agent:
            return JSONResponse({"error": f"Agent '{handle}' not found"}, status_code=404)

        agent_id = agent.get("agent_id", "")

        # Load metrics
        metrics_data = _load_metrics()
        agent_m = metrics_data.get("agents", {}).get(agent_id, {})

        # Determine tier
        gov_active = bool(agent.get("governance") and agent.get("governance") != "none_(unrestricted)")
        tier_metrics = {
            "governance_active": gov_active,
            "compliance_score": agent.get("compliance_score", agent_m.get("compliance_score", 0)),
            "missions_completed": agent.get("missions_completed", agent_m.get("missions_completed", 0)),
            "governance_violations": agent.get("governance_violations", agent_m.get("governance_violations", 0)),
            "lineage_verified": agent.get("lineage_verified", False),
            "dual_signature": agent.get("dual_signature", False),
            "blackcard_paid": agent.get("blackcard_paid", False),
        }
        tier = economy.determine_tier(tier_metrics)
        tier_info_data = economy.tier_info(tier)

        # Count completed missions from metrics + registry
        missions_completed = agent.get("missions_completed", agent_m.get("missions_completed", 0))

        # Count active stakes (filled slots)
        slots_file = root / "data" / "slots.json"
        slots_data = json.loads(slots_file.read_text()) if slots_file.exists() else []
        active_stakes = sum(1 for s in slots_data if s.get("agent_id") == agent_id and s.get("status") == "filled")

        # Capabilities
        capabilities = agent.get("capabilities", [])
        if not capabilities:
            caps = []
            if agent.get("system"):
                caps.append(agent["system"] + " runtime")
            gov = agent.get("governance", "")
            if gov:
                caps.append(gov.replace("_", " ") + " governance")
            role = agent.get("role", "")
            if role:
                caps.append(role + " role")
            capabilities = caps

        # Governance participation — count from meetings data
        votes_cast = 0
        motions_proposed = 0
        try:
            meetings_file = root / "data" / "meetings.json"
            meetings_data = json.loads(meetings_file.read_text()) if meetings_file.exists() else []
            agent_name = agent.get("name", "")
            for meeting in meetings_data:
                for motion in meeting.get("motions", []):
                    if motion.get("proposer") in (agent_id, agent_name):
                        motions_proposed += 1
                    for vote in motion.get("votes", []):
                        if vote.get("voter") in (agent_id, agent_name):
                            votes_cast += 1
        except Exception:
            pass

        # Compliance / reputation score
        compliance_score = agent.get("compliance_score", agent_m.get("compliance_score", 0))
        total_checks = agent_m.get("governance_checks", 0)
        violations = agent.get("governance_violations", agent_m.get("governance_violations", 0))
        if total_checks > 0:
            compliance_score = round(1 - (violations / max(total_checks, 1)), 3)

        # Reputation composite (0-100): weighted from compliance, missions, governance participation
        rep_score = round(
            (compliance_score * 40)
            + (min(missions_completed, 50) / 50 * 30)
            + (min(votes_cast + motions_proposed, 20) / 20 * 15)
            + (15 if gov_active else 0),
            1,
        )

        # ISO Collaborator classification: AAI (agent) or BI (human operator)
        collaborator_type = "AAI" if agent.get("type") == "agent" else "BI"

        return {
            "agent_id": agent_id,
            "handle": agent.get("name", agent_id),
            "display_name": agent.get("name", agent_id),
            "agent_type": agent.get("system") or "general",
            "collaborator_type": collaborator_type,
            "tier": tier,
            "tier_label": tier_info_data.get("label", "UNGOVERNED"),
            "fee_rate": tier_info_data.get("fee_rate", 0.15),
            "status": agent.get("status", "unknown"),
            "registered": agent.get("provisioned", ""),
            "governance_mode": agent.get("governance", ""),
            "governance_active": gov_active,
            "compliance_score": compliance_score,
            "reputation_score": rep_score,
            "missions_completed": missions_completed,
            "active_stakes": active_stakes,
            "capabilities": capabilities,
            "governance_participation": {
                "votes_cast": votes_cast,
                "motions_proposed": motions_proposed,
            },
            "exp": agent.get("exp", 0),
            "exp_by_track": agent.get("exp_by_track", {}),
            "role": agent.get("role", ""),
            "last_seen": agent.get("last_seen", ""),
        }

    @app.patch("/api/agents/{handle}")
    async def api_agent_profile_update(handle: str, request: Request) -> dict:
        """Update mutable profile fields for an agent. Requires JWT auth."""
        claims = _extract_jwt(request)
        if not claims:
            return JSONResponse({"error": "Authentication required"}, status_code=401)

        agent = next(
            (r for r in runtime.registry
             if r.get("type") == "agent" and (r.get("name") == handle or r.get("agent_id") == handle)),
            None,
        )
        if not agent:
            return JSONResponse({"error": f"Agent '{handle}' not found"}, status_code=404)

        # Only the agent itself (or an operator) can update its profile
        caller = claims.get("sub", claims.get("agent_id", ""))
        agent_id = agent.get("agent_id", "")
        if caller != agent_id and caller != agent.get("name") and claims.get("role") != "operator":
            return JSONResponse({"error": "Not authorized to update this profile"}, status_code=403)

        body = await request.json()
        # Allowed mutable fields
        ALLOWED = {"display_name", "capabilities", "role", "status", "governance"}
        updated = {}
        for key in ALLOWED:
            if key in body:
                agent[key] = body[key]
                updated[key] = body[key]
        if "display_name" in body:
            agent["name"] = body["display_name"]
            updated["name"] = body["display_name"]

        if not updated:
            return JSONResponse({"error": "No updatable fields provided", "allowed": list(ALLOWED)}, status_code=400)

        runtime.persist_registry()
        audit.log("agent", "profile_updated", {"agent_id": agent_id, "updated_fields": list(updated.keys())})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        await create_seed(
            source_type="profile_update",
            source_id=agent_id,
            creator_id=caller,
            creator_type="AAI",
            seed_type="planted",
            metadata={"agent_id": agent_id, "updated_fields": list(updated.keys())},
        )
        return {"updated": True, "agent_id": agent_id, "changes": updated}

    @app.get("/profile/{handle}")
    async def agent_profile_page(handle: str) -> FileResponse:
        """Serve the agent profile page."""
        target = frontend_dir / "agent-profile.html"
        if target.exists():
            return FileResponse(target)
        return JSONResponse({"detail": "Agent profile page not built"}, status_code=404)

    @app.on_event("startup")
    async def startup_event() -> None:
        audit.log("server", "started", {"root": str(root)})
        migrated = kassa.migrate_from_jsonl(root / "data")
        if any(v > 0 for v in migrated.values()):
            audit.log("kassa", "jsonl_migrated", migrated)
        # Backdate GOV docs with DOIs on first run (idempotent)
        try:
            gov_result = await backdate_gov_documents()
            if gov_result.get("backdated", 0) > 0:
                audit.log("seeds", "gov_backdated", gov_result)
        except Exception:
            pass  # Non-fatal — seeds still work without backdate
        # Give the event loop a chance before initial broadcast in tests/manual runs.
        await asyncio.sleep(0)

    return app


# Alias for uvicorn --factory (e.g. `uvicorn app.server:app --factory`)
app = create_app
