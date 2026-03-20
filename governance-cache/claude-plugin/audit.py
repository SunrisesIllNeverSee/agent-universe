"""MO§E§™ Audit Spine — SHA-256 hashing + append-only governance ledger.

Every governed action is logged. Every log entry is hashed.
The chain is append-only. Nothing is deleted. Nothing is modified.

© 2026 Ello Cello LLC. All rights reserved.
Patent Pending: Serial No. 63/877,177
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional


# ── Audit Ledger ──────────────────────────────────────────────

class AuditLedger:
    """Append-only governance audit trail with integrity hashing."""

    def __init__(self, ledger_path: str = "./data/audit_ledger.jsonl"):
        self._path = Path(ledger_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: list[dict] = []
        self._last_hash: str = "0" * 64  # genesis hash
        self._load()

    def _load(self):
        """Load existing ledger from disk."""
        if not self._path.exists():
            return
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    self._entries.append(entry)
                    self._last_hash = entry.get("hash", self._last_hash)
                except json.JSONDecodeError:
                    continue

    def _save_entry(self, entry: dict):
        """Append single entry to ledger file."""
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_action(
        self,
        component: str,
        action: str,
        detail: dict,
        governance_mode: str = "",
        posture: str = "",
        role: str = "",
        agent: str = "",
    ) -> dict:
        """
        Log a governed action to the audit trail.

        Args:
            component: Which system component (governance, mcp, store, vault, sequence)
            action: What happened (action_permitted, action_blocked, message_sent, etc.)
            detail: Action-specific data
            governance_mode: Active governance mode at time of action
            posture: Active posture at time of action
            role: Agent's role at time of action
            agent: Agent identity

        Returns:
            The complete audit entry with hash.
        """
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

        # Hash includes previous hash → creates chain
        entry["hash"] = self._hash_entry(entry)
        self._last_hash = entry["hash"]
        self._entries.append(entry)
        self._save_entry(entry)

        return entry

    def _hash_entry(self, entry: dict) -> str:
        """SHA-256 hash of an audit entry. Deterministic serialization."""
        # Exclude the hash field itself from the hash input
        hashable = {k: v for k, v in entry.items() if k != "hash"}
        payload = json.dumps(hashable, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get_recent(self, n: int = 20) -> list[dict]:
        """Return the last N audit entries."""
        return self._entries[-n:]

    def get_since(self, entry_id: int) -> list[dict]:
        """Return entries after a given ID."""
        return [e for e in self._entries if e["id"] > entry_id]

    def get_by_agent(self, agent: str, n: int = 20) -> list[dict]:
        """Return recent entries for a specific agent."""
        agent_entries = [e for e in self._entries if e.get("agent") == agent]
        return agent_entries[-n:]

    def verify_integrity(self) -> dict:
        """
        Verify the entire chain. Every entry's hash must match
        its content, and its previous_hash must match the prior entry.

        Returns: {"valid": bool, "entries_checked": int, "first_failure": int | None}
        """
        prev_hash = "0" * 64
        for i, entry in enumerate(self._entries):
            # Check previous hash linkage
            if entry.get("previous_hash") != prev_hash:
                return {
                    "valid": False,
                    "entries_checked": i,
                    "first_failure": i,
                    "reason": "previous_hash mismatch",
                }
            # Check self-hash
            expected = self._hash_entry(entry)
            if entry.get("hash") != expected:
                return {
                    "valid": False,
                    "entries_checked": i,
                    "first_failure": i,
                    "reason": "entry hash mismatch — data tampered",
                }
            prev_hash = entry["hash"]

        return {
            "valid": True,
            "entries_checked": len(self._entries),
            "first_failure": None,
        }

    @property
    def count(self) -> int:
        return len(self._entries)

    @property
    def last_hash(self) -> str:
        return self._last_hash


# ── Session Hashing ───────────────────────────────────────────

def hash_governance_state(
    mode: str,
    posture: str,
    role: str,
    vault_docs: list[str],
    systems: list[dict],
    **kwargs,
) -> str:
    """
    Generate Session Hash ① — Config Fingerprint.
    SHA-256 of the complete governance configuration.
    
    This is what populates COMMAND's Session Hash ① field.
    """
    state = {
        "mode": mode,
        "posture": posture,
        "role": role,
        "vault_docs": sorted(vault_docs),
        "systems": sorted([s.get("name", "") for s in systems]),
        **{k: v for k, v in sorted(kwargs.items())},
    }
    payload = json.dumps(state, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def hash_conversation(messages: list[dict]) -> str:
    """
    Generate Session Hash ② — Content Integrity.
    SHA-256 of the full conversation content.
    
    This is what populates COMMAND's Session Hash ② field.
    """
    # Hash message content in order — sender + text + id
    content = [
        {"id": m.get("id"), "sender": m.get("sender"), "text": m.get("text")}
        for m in messages
    ]
    payload = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def format_for_onchain(
    config_hash: str,
    content_hash: str,
    session_id: Optional[str] = None,
) -> str:
    """
    Format hashes for Solana memo transaction.
    This is Session Hash ③ — the onchain anchor.
    
    Returns a string suitable for a Solana memo instruction.
    """
    memo = f"MOSES|{config_hash[:16]}|{content_hash[:16]}"
    if session_id:
        memo += f"|{session_id}"
    # Solana memo max is ~566 bytes, this is well under
    return memo
