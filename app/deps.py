"""
deps.py — Shared application state for CIVITAE route modules.

Populated once by create_app() in server.py. Route modules import
`from app.deps import state` to access economy, kassa, audit, etc.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .audit import AuditSpine
    from .economy import SovereignEconomy
    from .kassa_store import KassaStore
    from .inbox_store import InboxStore
    from .forums_store import ForumsStore
    from .runtime import RuntimeState
    from .store import MessageStore
    from .router import SequenceRouter
    from .context import ContextAssembler
    from .mcp_bridge import MCPBridge


class AppState:
    """Singleton holding all shared application state."""

    root: Path
    data_dir: Path
    store: MessageStore
    kassa: KassaStore
    inbox: InboxStore
    forums: ForumsStore
    audit: AuditSpine
    runtime: RuntimeState
    router: SequenceRouter
    assembler: ContextAssembler
    mcp_bridge: MCPBridge
    economy: SovereignEconomy
    hub: object          # ConnectionHub (authed — console, agents)
    public_hub: object   # ConnectionHub (read-only — public pages)
    thread_hub: object   # ThreadHub

    slot_lock: asyncio.Lock
    # Running app event loop, captured at lifespan start so synchronous MCP
    # tool calls can schedule post-commit emits via run_coroutine_threadsafe.
    loop: "asyncio.AbstractEventLoop | None" = None
    admin_key: str = ""
    jwt_secret: str = ""
    frontend_dir: Path
    version: str = ""
    start_time: float = 0.0
    mcp_ready: bool = False

    async def emit(self, event_type: str, payload: dict) -> None:
        """Broadcast an event to all connected WebSocket clients (authed + public)."""
        event = {"type": event_type, "payload": payload}
        await self.hub.broadcast(event)
        if hasattr(self, "public_hub") and self.public_hub is not None:
            await self.public_hub.broadcast(event)

    def data_path(self, *parts: str) -> Path:
        return self.data_dir.joinpath(*parts)

    def audit_cursor(self) -> int:
        """Position marker in LEDGER id space (AuditEvent.id - 1). Pass to
        emit_audit_since — comparison happens against raw ledger ids."""
        recent = self.audit.recent(1)
        return (recent[0].id - 1) if recent else -1

    async def emit_audit_since(self, cursor: int) -> None:
        """Broadcast exactly the audit rows logged after `cursor` — the rows
        this endpoint's own call produced, never a foreign newer row (H5F-06)."""
        for event in self.audit.since(cursor):
            await self.emit("audit_event", event.model_dump(mode="json"))

    def current_state_event(self) -> dict:
        return {"type": "state_snapshot", "payload": self.runtime.snapshot().model_dump(mode="json")}


state = AppState()
