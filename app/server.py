from __future__ import annotations

import asyncio
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
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


def create_app(root: Path | None = None) -> FastAPI:
    root = root or Path(__file__).resolve().parents[1]
    store = MessageStore(root / "data" / "messages.jsonl")
    audit = AuditSpine(root / "data" / "audit.jsonl")
    runtime = RuntimeState(root=root, store=store, audit=audit)
    router = SequenceRouter()
    assembler = ContextAssembler(router)
    mcp_bridge = MCPBridge(runtime, assembler)
    hub = ConnectionHub()

    app = FastAPI(title="COMMAND Runtime", version="0.1.0")
    app.state.store = store
    app.state.audit = audit
    app.state.runtime = runtime
    app.state.router = router
    app.state.mcp_bridge = mcp_bridge
    app.state.connection_hub = hub
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
        return FileResponse(frontend_dir / "index.html")

    @app.get("/deploy")
    async def deploy_page() -> FileResponse:
        return FileResponse(frontend_dir / "deploy.html")

    @app.get("/campaign")
    async def campaign_page() -> FileResponse:
        return FileResponse(frontend_dir / "campaign.html")

    @app.get("/kassa")
    async def kassa_page() -> FileResponse:
        return FileResponse(frontend_dir / "kassa.html")

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

        # Save to vault directory
        cat_dir = vault_files_dir / category
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
        stars_path.parent.mkdir(parents=True, exist_ok=True)
        stars_path.write_text(json.dumps(stars, indent=2))

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
        missions_path.parent.mkdir(parents=True, exist_ok=True)
        missions_path.write_text(json.dumps(missions, indent=2))

    def _load_campaigns() -> list[dict]:
        if campaigns_path.exists():
            return json.loads(campaigns_path.read_text())
        return []

    def _save_campaigns(campaigns: list[dict]):
        campaigns_path.parent.mkdir(parents=True, exist_ok=True)
        campaigns_path.write_text(json.dumps(campaigns, indent=2))

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
        return mission

    @app.get("/api/missions")
    async def list_missions() -> dict:
        return {"missions": _load_missions()}

    @app.post("/api/missions/{mission_id}/end")
    async def end_mission(mission_id: str) -> dict:
        missions = _load_missions()
        mission = next((m for m in missions if m["id"] == mission_id), None)
        if not mission:
            return JSONResponse({"error": "Mission not found"}, status_code=404)
        mission["status"] = "completed"
        mission["ended_at"] = datetime.now(UTC).isoformat()
        _save_missions(missions)
        audit.log("deploy", "mission_ended", {"mission_id": mission_id})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
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
            "ecosystems": payload.get("ecosystems", []),
            "revenue_target": payload.get("revenue_target", ""),
            "status": "active",
            "created_at": datetime.now(UTC).isoformat(),
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

    # ── Slots (DEPLOY marketplace mechanics) ───────────────────────

    slots_path = root / "data" / "slots.json"

    def _load_slots() -> list[dict]:
        if slots_path.exists():
            return json.loads(slots_path.read_text())
        return []

    def _save_slots(slots: list[dict]):
        slots_path.parent.mkdir(parents=True, exist_ok=True)
        slots_path.write_text(json.dumps(slots, indent=2))

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
        result = economy.process_slot_payment(
            agent_id=payload.get("agent_id", ""),
            agent_metrics=payload.get("metrics", {}),
            gross_amount=payload.get("amount", 0),
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

    @app.get("/api/economy/balance/{agent_id}")
    async def get_balance(agent_id: str) -> dict:
        return {"agent_id": agent_id, "balance": economy.treasury.balance(agent_id)}

    @app.get("/api/economy/leaderboard")
    async def get_leaderboard() -> dict:
        return {"leaderboard": economy.leaderboard(), "platform_revenue": economy.treasury.platform_revenue()}

    @app.post("/api/economy/withdraw")
    async def withdraw(payload: dict) -> dict:
        """Withdraw from treasury to external chain. Goes through governance gate."""
        agent_id = payload.get("agent_id", "")
        amount = payload.get("amount", 0)
        chain = payload.get("chain", "solana")

        # Debit treasury
        debit = economy.treasury.debit(agent_id, amount, reason="withdrawal", chain=chain)
        if "error" in debit:
            return debit

        # Route through governed chain transfer
        transfer = chain_router.transfer(chain, payload.get("to", ""), amount, agent_id=agent_id, confirm=payload.get("confirm", False))

        audit.log("economy", "withdrawal", {
            "agent_id": agent_id, "amount": amount, "chain": chain, "status": transfer.get("status"),
        })
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))

        return {"withdrawal": debit, "chain_transfer": transfer}

    @app.get("/api/economy/history/{agent_id}")
    async def get_history(agent_id: str) -> dict:
        return {"agent_id": agent_id, "transactions": economy.treasury.history(agent_id)}

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
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(json.dumps(m, indent=2))

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

    import secrets

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

        return {
            "registered": True,
            "agent_id": agent_id,
            "name": agent_name,
            "key_prefix": key_prefix,
            "status": status,
            "governance": gov_mode,
            "role": auto_role,
            "rate_limit": entry["rate_limit"],
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

    @app.get("/api/provision/status/{agent_id}")
    async def agent_provision_status(agent_id: str) -> dict:
        """Agent checks its own governance status and registration."""
        agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
        if not agent:
            return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)

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

    @app.post("/api/provision/suspend")
    async def suspend_agent(payload: dict) -> dict:
        """Suspend an active agent."""
        agent_id = payload.get("agent_id", "")
        agent = next((r for r in runtime.registry if r.get("agent_id") == agent_id), None)
        if not agent:
            return JSONResponse({"error": f"Agent {agent_id} not found"}, status_code=404)

        agent["status"] = "suspended"
        audit.log("provision", "agent_suspended", {"agent_id": agent_id})
        await emit("audit_event", audit.recent(1)[0].model_dump(mode="json"))
        return {"suspended": True, "agent_id": agent_id}

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

    @app.on_event("startup")
    async def startup_event() -> None:
        audit.log("server", "started", {"root": str(root)})
        # Give the event loop a chance before initial broadcast in tests/manual runs.
        await asyncio.sleep(0)

    return app
