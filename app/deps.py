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
    lobby: object        # LobbyStore (velvet rope)
    slot_lock: asyncio.Lock
    admin_key: str = ""
    jwt_secret: str = ""
    frontend_dir: Path

    async def emit(self, event_type: str, payload: dict) -> None:
        """Broadcast an event to all connected WebSocket clients (authed + public)."""
        event = {"type": event_type, "payload": payload}
        await self.hub.broadcast(event)
        if hasattr(self, "public_hub") and self.public_hub is not None:
            await self.public_hub.broadcast(event)

    def data_path(self, *parts: str) -> Path:
        return self.data_dir.joinpath(*parts)

    def current_state_event(self) -> dict:
        return {"type": "state_snapshot", "payload": self.runtime.snapshot().model_dump(mode="json")}


state = AppState()
