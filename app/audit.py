from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import AuditEvent
from .moses_core.audit import AuditLedger, format_for_onchain, hash_conversation, hash_governance_state


class AuditSpine:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.ledger = AuditLedger(path)

    def log(self, component: str, action: str, detail: dict[str, Any] | None = None) -> AuditEvent:
        governance = detail.get("governance", {}) if detail else {}
        entry = self.ledger.log_action(
            component=component,
            action=action,
            detail=detail or {},
            governance_mode=governance.get("mode", ""),
            posture=governance.get("posture", ""),
            role=governance.get("role", ""),
            agent=(detail or {}).get("agent", ""),
        )
        return self._to_event(entry)

    def recent(self, limit: int = 200) -> list[AuditEvent]:
        return [self._to_event(entry) for entry in self.ledger.recent(limit)]

    def since(self, event_id: int) -> list[AuditEvent]:
        return [self._to_event(entry) for entry in self.ledger.since(event_id)]

    @staticmethod
    def _to_event(entry: dict[str, Any]) -> AuditEvent:
        raw_timestamp = entry.get("timestamp")
        if isinstance(raw_timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(raw_timestamp, UTC)
        else:
            try:
                timestamp = datetime.fromisoformat(str(raw_timestamp).replace("Z", "+00:00"))
            except Exception:
                timestamp = datetime.now(UTC)
        return AuditEvent(
            id=int(entry.get("id", 0)) + 1,
            timestamp=timestamp,
            component=entry.get("component", "audit"),
            action=entry.get("action", "unknown"),
            detail={
                **entry.get("detail", {}),
                "governance": entry.get("governance", {}),
                "hash": entry.get("hash"),
                "previous_hash": entry.get("previous_hash"),
                "agent": entry.get("agent", ""),
            },
        )

    @staticmethod
    def hash_payload(payload: Any) -> str:
        return hash_conversation([{"id": 0, "sender": "payload", "text": str(payload)}])

    @staticmethod
    def hash_runtime_state(*, mode: str, posture: str, role: str, vault_docs: list[str], systems: list[dict], session_id: str = "default") -> dict[str, str]:
        config_hash = hash_governance_state(
            mode=mode,
            posture=posture,
            role=role,
            vault_docs=vault_docs,
            systems=systems,
        )
        content_hash = hash_conversation([])
        return {
            "hash_config": config_hash,
            "hash_content": content_hash,
            "hash_onchain": format_for_onchain(config_hash, content_hash, session_id),
        }
