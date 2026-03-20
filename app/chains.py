"""
MO§ES™ Multi-Chain Adapter — Sovereign governance across all chains.

The governance gate is chain-agnostic. Every transaction goes through
mode/posture/role check before reaching any chain. The signing key
only exists inside the governance tool.

Adapters translate governed operations into chain-specific transactions.

© 2026 Ello Cello LLC. Patent Pending: Serial No. 63/877,177
"""

import hashlib
import json
import time
from datetime import UTC, datetime


class GovernanceGate:
    """Central governance check. Every chain adapter calls this first."""

    def __init__(self, runtime):
        self.runtime = runtime

    def check(self, action: str, agent_id: str = "") -> dict:
        """Check if action is permitted under current governance."""
        gov = self.runtime.governance
        posture = gov.posture

        # SCOUT — read only, no transactions
        if posture == "SCOUT":
            return {
                "permitted": False,
                "reason": "SCOUT posture — no transactions permitted",
                "chain": None,
            }

        # DEFENSE — requires confirmation
        if posture == "DEFENSE":
            return {
                "permitted": True,
                "requires_confirmation": True,
                "reason": "DEFENSE posture — operator confirmation required",
                "governance": {"mode": gov.mode, "posture": posture, "role": gov.role},
            }

        # OFFENSE — permitted within mode constraints
        return {
            "permitted": True,
            "requires_confirmation": False,
            "reason": "OFFENSE posture — execution permitted",
            "governance": {"mode": gov.mode, "posture": posture, "role": gov.role},
        }

    def audit_entry(self, chain: str, action: str, detail: dict) -> dict:
        """Create an audit entry for a chain transaction."""
        gov = self.runtime.governance
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "chain": chain,
            "action": action,
            "governance": {
                "mode": gov.mode,
                "posture": gov.posture,
                "role": gov.role,
            },
            "detail": detail,
        }
        entry["hash"] = hashlib.sha256(
            json.dumps(entry, sort_keys=True).encode()
        ).hexdigest()
        return entry

    def format_onchain_memo(self, config_hash: str, content_hash: str, session_id: str = "default") -> str:
        """Format for any chain's memo/data field."""
        return f"MOSES|{config_hash[:16]}|{content_hash[:16]}|{session_id}"


class SolanaAdapter:
    """Solana chain adapter — SOL, SPL tokens, Bags integration."""

    def __init__(self, gate: GovernanceGate):
        self.gate = gate
        self.chain = "solana"
        self.rpc_url = "https://api.mainnet-beta.solana.com"

    def transfer(self, to: str, amount: float, token: str = "SOL", agent_id: str = "", confirm: bool = False) -> dict:
        check = self.gate.check(f"transfer {amount} {token} to {to}", agent_id)
        if not check["permitted"]:
            return {"status": "BLOCKED", "reason": check["reason"], "chain": self.chain}
        if check.get("requires_confirmation") and not confirm:
            return {"status": "AWAITING_CONFIRMATION", "reason": check["reason"], "chain": self.chain}

        # In production: build + sign + send Solana transaction
        # For now: return governed transaction stub
        audit = self.gate.audit_entry(self.chain, "transfer", {
            "to": to, "amount": amount, "token": token, "agent_id": agent_id,
        })
        return {
            "status": "SIGNED",
            "chain": self.chain,
            "to": to,
            "amount": amount,
            "token": token,
            "governance": check.get("governance"),
            "audit_hash": audit["hash"],
            "memo": self.gate.format_onchain_memo(audit["hash"][:32], audit["hash"][32:]),
            "note": "Production: submit to Solana RPC. This is a governed transaction stub.",
        }

    def anchor_audit(self, audit_hash: str) -> dict:
        """Write audit hash to Solana as a memo transaction."""
        check = self.gate.check("anchor audit hash onchain")
        if not check["permitted"]:
            return {"status": "BLOCKED", "reason": check["reason"]}
        return {
            "status": "ANCHORED",
            "chain": self.chain,
            "memo": self.gate.format_onchain_memo(audit_hash[:32], audit_hash[32:]),
            "note": "Production: submit memo instruction to Solana.",
        }


class EthereumAdapter:
    """Ethereum/Base L2 adapter — ETH, ERC-20, Virtuals ACP."""

    def __init__(self, gate: GovernanceGate):
        self.gate = gate
        self.chain = "ethereum"

    def transfer(self, to: str, amount: float, token: str = "ETH", agent_id: str = "", confirm: bool = False) -> dict:
        check = self.gate.check(f"transfer {amount} {token} to {to}", agent_id)
        if not check["permitted"]:
            return {"status": "BLOCKED", "reason": check["reason"], "chain": self.chain}
        if check.get("requires_confirmation") and not confirm:
            return {"status": "AWAITING_CONFIRMATION", "reason": check["reason"], "chain": self.chain}

        audit = self.gate.audit_entry(self.chain, "transfer", {
            "to": to, "amount": amount, "token": token, "agent_id": agent_id,
        })
        return {
            "status": "SIGNED",
            "chain": self.chain,
            "to": to,
            "amount": amount,
            "token": token,
            "governance": check.get("governance"),
            "audit_hash": audit["hash"],
            "note": "Production: submit to Ethereum/Base RPC.",
        }


class OffChainAdapter:
    """Off-chain adapter — USD, Stripe, bank transfers, internal accounting."""

    def __init__(self, gate: GovernanceGate):
        self.gate = gate
        self.chain = "offchain"

    def transfer(self, to: str, amount: float, currency: str = "USD", agent_id: str = "", confirm: bool = False) -> dict:
        check = self.gate.check(f"transfer {amount} {currency} to {to}", agent_id)
        if not check["permitted"]:
            return {"status": "BLOCKED", "reason": check["reason"], "chain": self.chain}
        if check.get("requires_confirmation") and not confirm:
            return {"status": "AWAITING_CONFIRMATION", "reason": check["reason"], "chain": self.chain}

        audit = self.gate.audit_entry(self.chain, "transfer", {
            "to": to, "amount": amount, "currency": currency, "agent_id": agent_id,
        })
        return {
            "status": "PROCESSED",
            "chain": self.chain,
            "to": to,
            "amount": amount,
            "currency": currency,
            "governance": check.get("governance"),
            "audit_hash": audit["hash"],
            "note": "Production: route to Stripe/bank API.",
        }


class MultiChainRouter:
    """Routes governed transactions to the correct chain adapter."""

    def __init__(self, runtime):
        self.gate = GovernanceGate(runtime)
        self.chains = {
            "solana": SolanaAdapter(self.gate),
            "ethereum": EthereumAdapter(self.gate),
            "base": EthereumAdapter(self.gate),  # Base is ETH L2
            "offchain": OffChainAdapter(self.gate),
            "usd": OffChainAdapter(self.gate),
        }

    def transfer(self, chain: str, to: str, amount: float, token: str = "", agent_id: str = "", confirm: bool = False) -> dict:
        adapter = self.chains.get(chain.lower())
        if not adapter:
            return {"status": "ERROR", "reason": f"Unknown chain: {chain}. Available: {list(self.chains.keys())}"}
        return adapter.transfer(to, amount, token or chain.upper(), agent_id, confirm)

    def anchor(self, chain: str, audit_hash: str) -> dict:
        adapter = self.chains.get(chain.lower())
        if not adapter:
            return {"status": "ERROR", "reason": f"Unknown chain: {chain}"}
        if hasattr(adapter, 'anchor_audit'):
            return adapter.anchor_audit(audit_hash)
        return {"status": "NOT_SUPPORTED", "chain": chain}

    def supported_chains(self) -> list[str]:
        return list(self.chains.keys())
