from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


class AuditLedger:
    def __init__(self, ledger_path: str | Path):
        self._path = Path(ledger_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: list[dict] = []
        self._last_hash = "0" * 64
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                self._entries.append(entry)
                self._last_hash = entry.get("hash", self._last_hash)

    def _hash_entry(self, entry: dict) -> str:
        hashable = {key: value for key, value in entry.items() if key != "hash"}
        payload = json.dumps(hashable, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def log_action(
        self,
        *,
        component: str,
        action: str,
        detail: dict[str, Any],
        governance_mode: str = "",
        posture: str = "",
        role: str = "",
        agent: str = "",
    ) -> dict:
        entry = {
            "id": len(self._entries),
            "timestamp": time.time(),
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "component": component,
            "action": action,
            "agent": agent,
            "governance": {
                "mode": governance_mode,
                "posture": posture,
                "role": role,
            },
            "detail": detail,
            "previous_hash": self._last_hash,
        }
        entry["hash"] = self._hash_entry(entry)
        self._last_hash = entry["hash"]
        self._entries.append(entry)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return entry

    def recent(self, n: int = 20) -> list[dict]:
        return self._entries[-n:]

    def since(self, entry_id: int) -> list[dict]:
        return [entry for entry in self._entries if entry["id"] > entry_id]

    def verify_integrity(self) -> dict:
        prev_hash = "0" * 64
        for index, entry in enumerate(self._entries):
            if entry.get("previous_hash") != prev_hash:
                return {"valid": False, "entries_checked": index, "first_failure": index, "reason": "previous_hash mismatch"}
            if entry.get("hash") != self._hash_entry(entry):
                return {"valid": False, "entries_checked": index, "first_failure": index, "reason": "entry hash mismatch"}
            prev_hash = entry["hash"]
        return {"valid": True, "entries_checked": len(self._entries), "first_failure": None}


def hash_governance_state(*, mode: str, posture: str, role: str, vault_docs: list[str], systems: list[dict], **kwargs) -> str:
    payload = json.dumps(
        {
            "mode": mode,
            "posture": posture,
            "role": role,
            "vault_docs": sorted(vault_docs),
            "systems": sorted(system.get("name", "") for system in systems),
            **{key: value for key, value in sorted(kwargs.items())},
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def hash_conversation(messages: list[dict]) -> str:
    content = [{"id": message.get("id"), "sender": message.get("sender"), "text": message.get("text")} for message in messages]
    payload = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def format_for_onchain(config_hash: str, content_hash: str, session_id: str | None = None) -> str:
    memo = f"MOSES|{config_hash[:16]}|{content_hash[:16]}"
    if session_id:
        memo += f"|{session_id}"
    return memo
