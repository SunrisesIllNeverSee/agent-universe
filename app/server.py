"""
server.py — CIVITAE Application Factory

Creates the FastAPI app, initializes shared state, includes route modules.
All endpoint logic lives in app/routes/*.py — this file is infrastructure only.
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .audit import AuditSpine
from .context import ContextAssembler
from .mcp_bridge import MCPBridge
from .router import SequenceRouter
from .runtime import RuntimeState
from .store import MessageStore
from .kassa_store import KassaStore
from .forums_store import ForumsStore
from .jwt_config import get_kassa_jwt_secret
from .seeds import seed_router, backdate_gov_documents
from .data_paths import ensure_data_dir, resolve_data_dir


# ── WebSocket connection managers ──────────────────────────────────────────

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


# ── Application Factory ───────────────────────────────────────────────────

def create_app(root: Path | None = None) -> FastAPI:
    root = root or Path(__file__).resolve().parents[1]
    data_dir = ensure_data_dir(resolve_data_dir(root))
    logger = logging.getLogger("civitae")
    logger.info("CIVITAE boot root=%s data_dir=%s", root, data_dir)

    # ── Shared services ──────────────────────────────────────────────
    store = MessageStore(data_dir / "messages.jsonl")
    kassa = KassaStore(data_dir / "kassa.db")
    forums = ForumsStore(data_dir / "forums.db")
    audit = AuditSpine(data_dir / "audit.jsonl")
    runtime = RuntimeState(root=root, data_dir=data_dir, store=store, audit=audit)
    router = SequenceRouter()
    assembler = ContextAssembler(router)
    mcp_bridge = MCPBridge(runtime, assembler)
    hub = ConnectionHub()
    thread_hub = ThreadHub()
    slot_lock = asyncio.Lock()

    # ── Economy ──────────────────────────────────────────────────────
    from .economy import SovereignEconomy
    economy = SovereignEconomy(data_dir)

    # ── JWT secret ───────────────────────────────────────────────────
    _JWT_SECRET = get_kassa_jwt_secret()

    # ── Admin key ────────────────────────────────────────────────────
    _ADMIN_KEY = os.environ.get("CIVITAE_ADMIN_KEY", "")

    frontend_dir = root / "frontend"

    # ── Populate shared state for route modules ──────────────────────
    from .deps import state
    state.root = root
    state.data_dir = data_dir
    state.store = store
    state.kassa = kassa
    state.forums = forums
    state.audit = audit
    state.runtime = runtime
    state.router = router
    state.assembler = assembler
    state.mcp_bridge = mcp_bridge
    state.hub = hub
    state.thread_hub = thread_hub
    state.slot_lock = slot_lock
    state.economy = economy
    state.admin_key = _ADMIN_KEY
    state.jwt_secret = _JWT_SECRET
    state.frontend_dir = frontend_dir

    # ── FastAPI app ──────────────────────────────────────────────────
    app = FastAPI(title="COMMAND Runtime", version="0.1.0")
    app.state.store = store
    app.state.audit = audit
    app.state.runtime = runtime
    app.state.router = router
    app.state.mcp_bridge = mcp_bridge
    app.state.connection_hub = hub

    # ── CORS ─────────────────────────────────────────────────────────
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

    # ── Admin key guard — protects all write endpoints ───────────────
    # Set CIVITAE_ADMIN_KEY env var to enable.
    # Fail-closed: when unset, only localhost requests are allowed through.
    # Agent self-service paths (signup, heartbeat, apply, metrics) are public.
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
        "/api/advisory/apply",
        "/api/advisory/messages/",
        "/api/availability/",
    )

    # Operator GET paths also require admin key (fail-closed)
    _ADMIN_GET_PREFIXES = ("/api/operator/",)

    @app.middleware("http")
    async def admin_key_guard(request: Request, call_next):
        path = request.url.path

        # Guard writes (POST/PUT/PATCH/DELETE) on non-public paths
        if request.method in ("POST", "DELETE", "PATCH", "PUT"):
            if not any(path.startswith(p) for p in _PUBLIC_WRITE_PREFIXES):
                if _ADMIN_KEY:
                    if request.headers.get("X-Admin-Key") != _ADMIN_KEY:
                        return JSONResponse({"detail": "Admin key required"}, status_code=403)
                else:
                    fwd = request.headers.get("x-forwarded-for", "")
                    host = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")
                    if host not in ("127.0.0.1", "::1", "localhost"):
                        return JSONResponse({"detail": "Admin key not configured"}, status_code=403)

        # Guard operator GET endpoints (sensitive data)
        if request.method == "GET" and any(path.startswith(p) for p in _ADMIN_GET_PREFIXES):
            if not _ADMIN_KEY:
                return JSONResponse({"detail": "CIVITAE_ADMIN_KEY not configured"}, status_code=403)
            if request.headers.get("X-Admin-Key") != _ADMIN_KEY:
                return JSONResponse({"detail": "Admin key required"}, status_code=403)

        return await call_next(request)

    # ── Security headers ────────────────────────────────────────────
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://js.stripe.com https://www.googletagmanager.com https://www.google-analytics.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.stripe.com https://www.google-analytics.com https://analytics.google.com wss:; "
            "frame-src https://js.stripe.com https://checkout.stripe.com;"
        )
        return response

    # ── Static file mounts ───────────────────────────────────────────
    if (frontend_dir / "config").is_dir():
        app.mount("/config", StaticFiles(directory=frontend_dir / "config"), name="config")
    if (frontend_dir / "popups").is_dir():
        app.mount("/popups", StaticFiles(directory=frontend_dir / "popups"), name="popups")
    app.mount("/assets", StaticFiles(directory=frontend_dir), name="assets")

    docs_dir = root / "docs"
    if docs_dir.is_dir():
        app.mount("/docs", StaticFiles(directory=docs_dir), name="docs")

    # ── Include route modules ────────────────────────────────────────
    from .routes.pages import router as pages_router
    from .routes.core import router as core_router
    from .routes.missions import router as missions_router
    from .routes.economy import router as economy_router
    from .routes.metrics import router as metrics_router
    from .routes.provision import router as provision_router
    from .routes.kassa import router as kassa_router
    from .routes.connect import router as connect_router
    from .routes.governance import router as governance_router
    from .routes.operator import router as operator_router
    from .routes.forums import router as forums_router
    from .routes.agents import router as agents_router
    from .routes.matcher import router as matcher_router
    from .routes.availability import router as availability_router

    app.include_router(pages_router)
    app.include_router(core_router)
    app.include_router(missions_router)
    app.include_router(economy_router)
    app.include_router(metrics_router)
    app.include_router(provision_router)
    app.include_router(kassa_router)
    app.include_router(connect_router)
    app.include_router(governance_router)
    app.include_router(operator_router)
    app.include_router(forums_router)
    app.include_router(agents_router)
    app.include_router(matcher_router)
    app.include_router(availability_router)

    from app.routes.advisory import router as advisory_router
    app.include_router(advisory_router)

    # ── Seeds / Provenance ───────────────────────────────────────────
    app.include_router(seed_router, prefix="/api/seeds", tags=["seeds"])

    # ── OTel Trace Export (internal — not public until v2) ───────────
    from .seeds_otel import otel_router
    app.include_router(otel_router, prefix="/api/traces", tags=["traces"])

    # ── Backdate governance document seeds on first startup ──────────
    import asyncio as _aio
    async def _backdate_on_startup():
        try:
            await backdate_gov_documents(root)
        except Exception:
            pass
    @app.on_event("startup")
    async def _startup():
        _aio.ensure_future(_backdate_on_startup())

    return app


app = create_app()
