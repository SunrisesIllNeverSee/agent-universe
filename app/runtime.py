from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from .audit import AuditSpine
from .models import (
    AgentConfig,
    DeployState,
    GovernanceState,
    MessageCreate,
    MessageRecord,
    RuntimeSnapshot,
    SystemConfig,
    SystemRuntime,
)
from .moses_core.governance import check_action_permitted
from .store import MessageStore
from .vault import VaultState


class RuntimeState:
    def __init__(
        self,
        *,
        root: Path,
        data_dir: Path,
        store: MessageStore,
        audit: AuditSpine,
    ) -> None:
        self.root = root
        self.store = store
        self.audit = audit
        self.config_dir = root / "config"
        self.data_dir = data_dir
        self.state_path = self.data_dir / "runtime_state.json"
        self.cursors_path = self.data_dir / "mcp_cursors.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

        self.system_configs = [
            SystemConfig.model_validate(item)
            for item in json.loads((self.config_dir / "systems.json").read_text(encoding="utf-8"))["systems"]
        ]
        self.agent_configs = [
            AgentConfig.model_validate(item)
            for item in json.loads((self.config_dir / "agents.json").read_text(encoding="utf-8"))["agents"]
        ]
        provision_data = json.loads((self.config_dir / "provision.json").read_text(encoding="utf-8"))
        self.provision = provision_data.get("provision", {})
        self.registry = provision_data.get("registry", [])
        self.vault = VaultState(json.loads((self.config_dir / "vault.json").read_text(encoding="utf-8"))["vault"])

        self.governance = GovernanceState()
        self.systems = {
            config.id: SystemRuntime(active=config.online and config.id in {"claude", "gpt"}, role="none", seq=None)
            for config in self.system_configs
        }
        self.systems["claude"].role = "primary"
        self.systems["claude"].seq = 1
        self.systems["gpt"].role = "secondary"
        self.systems["gpt"].seq = 2
        self.deploy = DeployState()
        self.presence: dict[str, dict[str, Any]] = {}
        self.cursors: dict[str, dict[str, int]] = {}
        self._load_state()

    def _load_state(self) -> None:
        if not self.state_path.exists():
            self._load_cursors()
            return
        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.governance = GovernanceState.model_validate(payload.get("governance", {}))
        self.systems = {
            system_id: SystemRuntime.model_validate(runtime)
            for system_id, runtime in payload.get("systems", {}).items()
        }
        self.vault.set_loaded(payload.get("loaded_context", []))
        self.deploy = DeployState.model_validate(payload.get("deploy", {}))
        self.presence = payload.get("presence", {})
        self._load_cursors()

    def _load_cursors(self) -> None:
        if not self.cursors_path.exists():
            return
        payload = json.loads(self.cursors_path.read_text(encoding="utf-8"))
        self.cursors = {
            agent: {channel: int(cursor) for channel, cursor in channels.items()}
            for agent, channels in payload.items()
        }

    def _atomic_write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)

    def persist_registry(self) -> None:
        """Write provision.json back with current registry state."""
        payload = {"provision": self.provision, "registry": self.registry}
        with self._lock:
            self._atomic_write_json(self.config_dir / "provision.json", payload)

    def persist(self) -> None:
        payload = {
            "governance": self.governance.model_dump(mode="json"),
            "systems": {system_id: runtime.model_dump(mode="json") for system_id, runtime in self.systems.items()},
            "loaded_context": self.vault.loaded,
            "deploy": self.deploy.model_dump(mode="json"),
            "presence": self.presence,
        }
        cursor_payload = {
            agent: {channel: cursor for channel, cursor in channels.items()}
            for agent, channels in self.cursors.items()
        }
        with self._lock:
            self._atomic_write_json(self.state_path, payload)
            self._atomic_write_json(self.cursors_path, cursor_payload)

    def snapshot(self) -> RuntimeSnapshot:
        return RuntimeSnapshot(
            governance=self.governance,
            systems=self.systems,
            loaded_context=self.vault.loaded,
            deploy=self.deploy,
            provision=self.provision,
            registry=self.registry,
            agents=self.agent_configs,
            config_systems=self.system_configs,
            vault=self.vault.manifest,
            recent_messages=self.store.recent(),
            audit_events=self.audit.recent(),
        )

    def create_message(self, payload: MessageCreate) -> MessageRecord:
        message = MessageRecord(
            id=0,
            sender=payload.sender,
            text=payload.text,
            timestamp=datetime.now(UTC),
            channel=payload.channel,
            governance=self.governance,
            role_context=payload.role_context,
            vault_loaded=list(self.vault.loaded),
            systems=payload.systems,
            meta=payload.meta,
        )
        saved = self.store.add(message)
        self.audit.log(
            "store",
            "message_added",
            {
                "sender": saved.sender,
                "id": saved.id,
                "governance": {
                    "mode": self.governance.mode,
                    "posture": self.governance.posture,
                    "role": self.governance.role,
                },
            },
        )
        return saved

    def update_governance(self, changes: dict[str, Any]) -> GovernanceState:
        self.governance = self.governance.model_copy(update={k: v for k, v in changes.items() if v is not None})
        self.persist()
        self.audit.log("governance", "updated", {**self.governance.model_dump(mode="json"), "governance": {
            "mode": self.governance.mode,
            "posture": self.governance.posture,
            "role": self.governance.role,
        }})
        return self.governance

    def update_system(self, system_id: str, changes: dict[str, Any]) -> SystemRuntime:
        next_changes = {k: v for k, v in changes.items() if v is not None}
        if next_changes.get("role") == "primary":
            for other_id, other_runtime in self.systems.items():
                if other_id != system_id and other_runtime.role == "primary":
                    self.systems[other_id] = other_runtime.model_copy(update={"role": "secondary", "seq": 2})
        if next_changes.get("active") is False:
            next_changes["role"] = "none"
            next_changes["seq"] = None
        runtime = self.systems[system_id].model_copy(update=next_changes)
        self.systems[system_id] = runtime
        self.persist()
        self.audit.log("systems", "updated", {"system_id": system_id, **runtime.model_dump(mode="json"), "governance": {
            "mode": self.governance.mode,
            "posture": self.governance.posture,
            "role": self.governance.role,
        }})
        return runtime

    def load_context(self, filename: str) -> list[str]:
        loaded = self.vault.load(filename)
        self.persist()
        self.audit.log("vault", "loaded", {"file": filename, "governance": {
            "mode": self.governance.mode,
            "posture": self.governance.posture,
            "role": self.governance.role,
        }})
        return loaded

    def unload_context(self, filename: str) -> list[str]:
        loaded = self.vault.unload(filename)
        self.persist()
        self.audit.log("vault", "unloaded", {"file": filename, "governance": {
            "mode": self.governance.mode,
            "posture": self.governance.posture,
            "role": self.governance.role,
        }})
        return loaded

    def update_deploy(self, changes: dict[str, Any]) -> DeployState:
        self.deploy = self.deploy.model_copy(update={k: v for k, v in changes.items() if v is not None})
        self.persist()
        self.audit.log("deploy", "updated", {**self.deploy.model_dump(mode="json"), "governance": {
            "mode": self.governance.mode,
            "posture": self.governance.posture,
            "role": self.governance.role,
        }})
        return self.deploy

    def join_agent(self, agent_name: str) -> dict[str, Any]:
        record = {
            "agent": agent_name,
            "joined_at": datetime.now(UTC).isoformat(),
        }
        self.presence[agent_name] = record
        self.cursors.setdefault(agent_name, {})
        self.persist()
        self.audit.log("presence", "agent_joined", {**record, "governance": {
            "mode": self.governance.mode,
            "posture": self.governance.posture,
            "role": self.governance.role,
        }})
        return record

    def update_cursor(self, agent_name: str, channel: str, message_id: int) -> None:
        self.cursors.setdefault(agent_name, {})[channel] = message_id
        self.persist()

    def get_cursor(self, agent_name: str, channel: str) -> int:
        return self.cursors.get(agent_name, {}).get(channel, 0)

    def check_action(self, action_description: str) -> dict[str, Any]:
        from .moses_core.governance import GovernanceStateData
        return check_action_permitted(
            action_description,
            governance=GovernanceStateData(**self.governance.model_dump()),
        )
