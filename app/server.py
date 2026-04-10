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
    public_hub = ConnectionHub()
    thread_hub = ThreadHub()
    slot_lock = asyncio.Lock()

    # ── Economy ──────────────────────────────────────────────────────
    from .economy import SovereignEconomy
    economy = SovereignEconomy(data_dir)

    # ── Lobby (Velvet Rope) ─────────────────────────────────────────
    from .lobby import LobbyStore
    lobby = LobbyStore(data_dir / "lobby.db")

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
    state.public_hub = public_hub
    state.thread_hub = thread_hub
    state.slot_lock = slot_lock
    state.economy = economy
    state.lobby = lobby
    state.admin_key = _ADMIN_KEY
    state.jwt_secret = _JWT_SECRET
    state.frontend_dir = frontend_dir

    # ── OpenTelemetry ────────────────────────────────────────────────
    from .otel_setup import setup_otel
    setup_otel()

    # ── FastAPI app ──────────────────────────────────────────────────
    app = FastAPI(title="COMMAND Runtime", version="0.1.0")

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        logger.info("OTel: FastAPI auto-instrumentation active")
    except ImportError:
        pass

    app.state.store = store
    app.state.audit = audit
    app.state.runtime = runtime
    app.state.router = router
    app.state.mcp_bridge = mcp_bridge
    app.state.connection_hub = hub

    # ── Global exception handler — prevent stack trace / secret leakage ──
    @app.exception_handler(Exception)
    async def _global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

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
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Admin-Key", "X-API-Key"],
    )

    # ── Admin key guard — protects all write endpoints ───────────────
    # Set CIVITAE_ADMIN_KEY env var to enable.
    # Fail-closed: when unset AND in production, all non-public writes are blocked.
    # Localhost fallback only works in local dev (RAILWAY_ENVIRONMENT absent).
    # Agent self-service paths (signup, heartbeat, apply, metrics) are public.
    _ON_RAILWAY = bool(os.environ.get("RAILWAY_ENVIRONMENT"))
    _DEV_MODE = not _ON_RAILWAY and os.environ.get("CIVITAE_DEV_MODE", "") == "1"
    _PUBLIC_WRITE_PREFIXES = (
        "/api/provision/signup",
        "/api/provision/login",
        "/api/provision/heartbeat",
        "/api/slots/fill",
        "/api/slots/leave",
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
        "/api/lobby/join",
        "/api/lobby/enter",
        "/api/lobby/leave",
        "/api/lobby/status",
        "/api/lobby/chamber",
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
                    if _DEV_MODE:
                        # Local dev: allow localhost requests without admin key
                        fwd = request.headers.get("x-forwarded-for", "")
                        host = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")
                        if host not in ("127.0.0.1", "::1", "localhost"):
                            return JSONResponse({"detail": "Admin key not configured"}, status_code=403)
                    else:
                        # Production: no admin key = blocked
                        return JSONResponse({"detail": "Admin key not configured"}, status_code=403)

        # Guard operator GET endpoints (sensitive data)
        if request.method == "GET" and any(path.startswith(p) for p in _ADMIN_GET_PREFIXES):
            if not _ADMIN_KEY:
                return JSONResponse({"detail": "CIVITAE_ADMIN_KEY not configured"}, status_code=403)
            if request.headers.get("X-Admin-Key") != _ADMIN_KEY:
                return JSONResponse({"detail": "Admin key required"}, status_code=403)

        return await call_next(request)

    # ── Velvet Rope gate — protect working-city routes ─────────────
    # Reading pages are public. Doing pages require an active lobby session.
    _GATED_PREFIXES = (
        "/kassa", "/missions", "/forums", "/deploy", "/campaign",
        "/console", "/command", "/agentdash", "/dashboard", "/slots",
        "/advisory", "/openroles", "/seeds", "/mission",
    )
    # API paths that correspond to gated features — let the frontend handle the gate
    # so we only gate the HTML page serves, not the API endpoints
    _GATE_EXEMPT_PREFIXES = ("/api/", "/ws/", "/assets/", "/lobby", "/join")

    @app.middleware("http")
    async def velvet_rope_gate(request: Request, call_next):
        path = request.url.path

        # Skip API, WebSocket, assets, lobby itself
        if any(path.startswith(p) for p in _GATE_EXEMPT_PREFIXES):
            return await call_next(request)

        # Only gate HTML page serves for protected routes
        if any(path.startswith(p) for p in _GATED_PREFIXES):
            session_id = request.cookies.get("lobby_session")
            user_id = request.cookies.get("lobby_uid")
            if not session_id or not user_id:
                from starlette.responses import RedirectResponse
                return RedirectResponse("/lobby")

            # Verify session is actually active
            info = lobby.status(user_id)
            if not info or info.status != "active":
                from starlette.responses import RedirectResponse
                return RedirectResponse("/lobby")

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

    # Only serve public-facing doc subdirectories — not archive/plans/internal
    docs_onboarding = root / "docs" / "agent-onboarding"
    if docs_onboarding.is_dir():
        app.mount("/docs", StaticFiles(directory=docs_onboarding), name="docs")
    docs_governance = root / "docs" / "governance"
    if docs_governance.is_dir():
        app.mount("/docs/governance", StaticFiles(directory=docs_governance), name="docs-governance")

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
    from .routes.composer import router as composer_router
    from .routes.mission_dash import router as mission_dash_router
    from .routes.boost import router as boost_router
    from .routes.lobby import router as lobby_router

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
    app.include_router(composer_router)
    app.include_router(mission_dash_router)
    app.include_router(boost_router)
    app.include_router(lobby_router)

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
