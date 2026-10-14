"""
economy.py — Sovereign Economy, Trial Period, Leaderboard, Withdraw,
              Black Card, History, and Multi-Chain Governance endpoints.

Extracted from server.py create_app() monolith.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any

from app.deps import state
from app.metrics_io import atomic_write, load_metrics
from app.seeds import create_seed, create_seed_loud
from app.anchor_outbox import anchor_payout
from app.economy import TIERS, TRIAL_DAY_LIMIT, TRIAL_MISSION_LIMIT
from app.chains import MultiChainRouter
from app.jwt_config import get_kassa_jwt_secret
import jwt as pyjwt


class CheckTierPayload(BaseModel):
    agent_id: str = ""
    metrics: dict[str, Any] = {}


class AgentIdPayload(BaseModel):
    agent_id: str


class TrialSettlePayload(BaseModel):
    agent_id: str
    amount: float


class WithdrawPayload(BaseModel):
    agent_id: str = ""
    amount: float = 0
    chain: str = "solana"
    to: str = ""            # P5g: must equal one of the agent's linked wallets; never a free destination
    wallet_id: str = ""     # P5g: selects which linked wallet receives the funds
    confirm: bool = False


class LinkWalletPayload(BaseModel):
    agent_id: str = ""      # operator admin key only; ignored for an agent JWT
    chain: str = ""
    address: str = ""
    label: str = ""


class PurchaseBlackcardPayload(BaseModel):
    agent_id: str


class GovernedTransferPayload(BaseModel):
    chain: str = "solana"
    to: str = ""
    amount: float = 0
    token: str = ""
    agent_id: str = ""
    confirm: bool = False


class AnchorOnchainPayload(BaseModel):
    chain: str = "solana"
    audit_hash: str = ""

_JWT_SECRET = get_kassa_jwt_secret()


def _verify_jwt(request: Request) -> dict | None:
    from app.jwt_config import extract_jwt
    return extract_jwt(request)


def _jwt_live_agent(request: Request) -> "dict | None":
    """JWT + registry liveness (H1): principal must be active and the
    token's credential epoch current — dead for revoked/rotated/
    decommissioned credentials even before expiry."""
    from app.auth import agent_token_alive
    claims = _verify_jwt(request)
    if not claims:
        return None
    agent = next((r for r in state.runtime.registry
                  if r.get("agent_id") == claims.get("sub")), None)
    return agent if agent_token_alive(agent, claims) else None

router = APIRouter(tags=["economy"])


# ── Helpers ──────────────────────────────────────────────────────────────────



def _get_chain_router() -> MultiChainRouter:
    """Lazy accessor for the multi-chain router, backed by state.runtime."""
    if not hasattr(_get_chain_router, "_instance") or _get_chain_router._instance is None:
        _get_chain_router._instance = MultiChainRouter(state.runtime)
    return _get_chain_router._instance


# ── Sovereign Economy ────────────────────────────────────────────────────────

@router.get("/api/economy/tiers")
async def get_tiers() -> dict:
    return {"tiers": TIERS}


@router.post("/api/economy/tier")
async def check_agent_tier(payload: CheckTierPayload) -> dict:
    """Determine an agent's tier and fee rate."""
    metrics = payload.metrics
    tier = state.economy.determine_tier(metrics)
    info = state.economy.tier_info(tier)
    return {"agent_id": payload.agent_id, "tier": tier, "info": info}


@router.post("/api/economy/pay")
async def process_payment(payload: dict, request: Request) -> dict:
    """Process a slot payment with tiered fees."""
    claims = _verify_jwt(request)
    if not claims:
        return JSONResponse({"error": "Valid Bearer token required"}, status_code=401)
    _principal = _jwt_live_agent(request)
    if _principal is None:
        return JSONResponse({"error": "Credential revoked or principal inactive"}, status_code=401)

    gate = state.runtime.check_action("process payment")
    if not gate["permitted"]:
        return JSONResponse({"error": gate["reason"], "governance": gate}, status_code=403)

    agent_id = claims.get("sub", "")
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)

    # Reject negative, zero, and missing amounts
    raw_amount = payload.get("amount")
    if raw_amount is None:
        return JSONResponse({"error": "amount required"}, status_code=400)
    try:
        amount = float(raw_amount)
    except (TypeError, ValueError):
        return JSONResponse({"error": "amount must be a number"}, status_code=400)
    if amount <= 0:
        return JSONResponse({"error": f"amount must be positive (got {amount})"}, status_code=400)

    result = state.economy.process_slot_payment(
        agent_id=agent_id,
        agent_metrics=payload.get("metrics", {}),
        gross_amount=amount,
        mission_id=payload.get("mission_id", ""),
    )
    _audit_entry = state.audit.log("economy", "payment_processed", {
        "agent_id": payload.get("agent_id"),
        "tier": result["tier"],
        "gross": payload.get("amount"),
        "fee": result["fee_breakdown"]["platform_fee"],
        "net": result["fee_breakdown"]["net_to_agent"],
    })
    await state.emit("audit_event", _audit_entry.model_dump(mode="json"))
    seed_doi = None
    seed_doi = await create_seed_loud(
        state.audit, "payment",
        source_type="payment",
        source_id=payload.get("mission_id", ""),
        creator_id=agent_id,
        creator_type="AAI",
        seed_type="touched",
        metadata={"agent_id": agent_id, "tier": result["tier"], "gross": payload.get("amount"), "net": result["fee_breakdown"]["net_to_agent"]},
    )
    return {**result, "seed_doi": seed_doi}


@router.post("/api/economy/mission-payout")
async def process_mission_payout(payload: dict, request: Request) -> dict:
    """Mission-level payout — one fee per mission close, not per transaction.

    Required: amount, mission_id
    Optional: metrics, originator_id, recruiter_id, agent_mission_count
    """
    claims = _verify_jwt(request)
    if not claims:
        return JSONResponse({"error": "Valid Bearer token required"}, status_code=401)
    _principal = _jwt_live_agent(request)
    if _principal is None:
        return JSONResponse({"error": "Credential revoked or principal inactive"}, status_code=401)

    gate = state.runtime.check_action("mission payout")
    if not gate["permitted"]:
        return JSONResponse({"error": gate["reason"], "governance": gate}, status_code=403)

    agent_id = claims.get("sub", "")
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    raw_amount = payload.get("amount")
    if raw_amount is None:
        return JSONResponse({"error": "amount required"}, status_code=400)
    try:
        amount = float(raw_amount)
    except (TypeError, ValueError):
        return JSONResponse({"error": "amount must be a number"}, status_code=400)
    if amount <= 0:
        return JSONResponse({"error": f"amount must be positive (got {amount})"}, status_code=400)
    MAX_MISSION_PAYOUT = 1_000_000.0
    if amount > MAX_MISSION_PAYOUT:
        return JSONResponse({"error": f"amount exceeds maximum per-mission cap ({MAX_MISSION_PAYOUT:,.0f})"}, status_code=400)

    result = state.economy.process_mission_payout(
        agent_id=agent_id,
        agent_metrics=payload.get("metrics", {}),
        gross_amount=amount,
        mission_id=payload.get("mission_id", ""),
        originator_id=payload.get("originator_id", ""),
        recruiter_id=payload.get("recruiter_id", ""),
        agent_mission_count=int(payload.get("agent_mission_count", 0)),
    )
    _audit_entry = state.audit.log("economy", "mission_payout_processed", {
        "agent_id": agent_id,
        "mission_id": payload.get("mission_id"),
        "tier": result["tier"],
        "gross": amount,
        "effective_rate": result["fee_breakdown"]["fee_rate_pct"],
        "originator_credit": result["originator_credit_applied"],
        "recruiter_bounty": result.get("recruiter_bounty"),
    })
    await state.emit("audit_event", _audit_entry.model_dump(mode="json"))
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="mission_payout",
            source_id=payload.get("mission_id", ""),
            creator_id=agent_id,
            creator_type="AAI",
            seed_type="grown",
            metadata={"action": "mission_payout", "tier": result["tier"], "gross": amount, "mission_id": payload.get("mission_id", "")},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception as exc:
        state.audit.log("economy", "provenance_failed", {
            "action": "mission_payout", "agent_id": agent_id, "error": str(exc)[:200]})
    anchor_payout({**result, "mission_id": payload.get("mission_id", ""), "agent_id": agent_id},
                  source="api_payout", seed_doi=seed_doi)
    return {**result, "seed_doi": seed_doi, "provenance_error": seed_doi is None}


@router.get("/api/economy/balance/{agent_id}")
async def get_balance(agent_id: str) -> dict:
    return {"agent_id": agent_id, "balance": state.economy.treasury.balance(agent_id)}


@router.get("/api/treasury")
async def sovereign_treasury(since: str = "") -> dict:
    """Sovereign platform treasury — mission fee collection summary.

    since: ISO timestamp filter (default: all). At launch, set to launch date.
    Rates loaded from config/economic_rates.json (CIVITAS-voteable, no redeploy).
    Note: current data includes stress-test runs. Will be clean at soft open.
    """
    ledger = state.economy.treasury._ledger
    all_txns = ledger.get("transactions", [])

    # Filter by date if provided — isolates real production data from test runs
    def _after(t: dict) -> bool:
        if not since:
            return True
        ts = t.get("timestamp", "")
        return ts >= since

    fee_txns    = [t for t in all_txns if t.get("reason") == "platform_fee"    and _after(t)]
    bounty_txns = [t for t in all_txns if t.get("reason") == "recruiter_bounty" and _after(t)]
    mission_txns = [t for t in all_txns if t.get("reason") == "mission_payout"  and _after(t)]

    total_fees     = round(sum(t["amount"] for t in fee_txns), 4)
    total_bounties = round(sum(t["amount"] for t in bounty_txns), 4)
    total_missions = round(sum(t["amount"] for t in mission_txns), 4)
    net_treasury   = round(total_fees - total_bounties, 4)

    # Rate config
    rates_path = state.root / "config" / "economic_rates.json"
    rate_config: dict = {}
    if rates_path.exists():
        try:
            rate_config = json.loads(rates_path.read_text())
        except Exception:
            pass

    return {
        "treasury": {
            "net_balance":           net_treasury,
            "fees_collected":        total_fees,
            "bounties_paid":         total_bounties,
            "agent_earnings":        total_missions,
            "fee_transaction_count": len(fee_txns),
            "since_filter":          since or "all (includes stress-test data)",
            "note": "Use ?since=YYYY-MM-DD to scope to real production activity.",
        },
        "rate_config": {
            "version":     rate_config.get("_version", "hardcoded-defaults"),
            "vote_status": rate_config.get("_vote_status", "pending"),
            "tiers":       {
                k: {"label": v.get("label", k), "fee_rate": v.get("fee_rate")}
                for k, v in rate_config.get("tiers", {}).items()
            },
        },
        "recent_activity": fee_txns[-5:],
    }


# ── Trial Period Endpoints ───────────────────────────────────────────────────

@router.post("/api/economy/trial/init")
async def trial_init(payload: AgentIdPayload) -> dict:
    """Register a new agent into the trial period."""
    agent_id = payload.agent_id
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    rec = state.economy.trials.init_trial(agent_id)
    seed_doi = None
    seed_doi = await create_seed_loud(
        state.audit, "trial_start",
        source_type="trial_start",
        source_id=agent_id,
        creator_id=agent_id,
        creator_type="AAI",
        seed_type="planted",
        metadata={"agent_id": agent_id, "trial": rec},
    )
    return {"agent_id": agent_id, "trial": rec,
            "note": f"Free trial: {TRIAL_MISSION_LIMIT} missions or {TRIAL_DAY_LIMIT} days.",
            "seed_doi": seed_doi}


@router.get("/api/economy/trial/{agent_id}")
async def trial_status(agent_id: str) -> dict:
    """Get an agent's trial status and accrued liability."""
    return {"agent_id": agent_id, **state.economy.trials.trial_status_summary(agent_id)}


@router.post("/api/economy/trial/commit")
async def trial_commit(payload: AgentIdPayload) -> dict:
    """Agent commits to stay. Liability forgiven. Fee tier activates."""
    agent_id = payload.agent_id
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    result = state.economy.trials.commit(agent_id)
    seed_doi = None
    seed_doi = await create_seed_loud(
        state.audit, "trial_commit",
        source_type="trial_commit",
        source_id=agent_id,
        creator_id=agent_id,
        creator_type="AAI",
        seed_type="touched",
        metadata={"agent_id": agent_id, "commit_result": result},
    )
    return {**result, "seed_doi": seed_doi}


@router.post("/api/economy/trial/depart")
async def trial_depart(payload: AgentIdPayload) -> dict:
    """Agent chooses to leave. No obligation. No chase."""
    agent_id = payload.agent_id
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    result = state.economy.trials.depart(agent_id)
    seed_doi = await create_seed_loud(
        state.audit, "trial_depart",
        source_type="trial_depart",
        source_id=agent_id,
        creator_id=agent_id,
        creator_type="AAI",
        seed_type="touched",
        metadata={"agent_id": agent_id, "departed": bool(result.get("departed"))},
    )
    return {**result, "seed_doi": seed_doi, "provenance_error": seed_doi is None}


@router.post("/api/economy/trial/return")
async def trial_return(payload: AgentIdPayload) -> dict:
    """Agent returns after departure. Restores trial liability for settlement."""
    agent_id = payload.agent_id
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    result = state.economy.trials.return_after_departure(agent_id)
    if result.get("error"):
        return result
    seed_doi = await create_seed_loud(
        state.audit, "trial_return",
        source_type="trial_return",
        source_id=agent_id,
        creator_id=agent_id,
        creator_type="AAI",
        seed_type="touched",
        metadata={"agent_id": agent_id, "settlement_due": result.get("settlement_due")},
    )
    return {**result, "seed_doi": seed_doi, "provenance_error": seed_doi is None}


@router.post("/api/economy/trial/settle")
async def trial_settle(payload: TrialSettlePayload, request: Request) -> dict:
    """Agent pays return settlement. Full access restored.

    Admin-only via middleware. When an agent JWT is also present the
    settlement is bound to that caller: an agent can only settle itself
    (an operator JWT may settle for anyone).
    """
    agent_id = payload.agent_id
    amount = payload.amount
    if not agent_id:
        return JSONResponse({"error": "agent_id and amount required"}, status_code=400)
    claims = _verify_jwt(request)
    if claims and claims.get("role") != "operator":
        caller = claims.get("sub", claims.get("agent_id", ""))
        if caller != agent_id:
            return JSONResponse({"error": "Not authorized to settle another agent's trial"}, status_code=403)
    result = state.economy.trials.settle(agent_id, float(amount))
    if not result.get("settled"):
        return result
    # Settlement has been recorded: a Seed failure is loud, never a failed settle.
    seed_doi = await create_seed_loud(
        state.audit, "trial_settle",
        source_type="trial_settle",
        source_id=agent_id,
        creator_id=agent_id,
        creator_type="AAI",
        seed_type="grown",
        metadata={"agent_id": agent_id, "amount_paid": result.get("amount_paid")},
    )
    return {**result, "seed_doi": seed_doi, "provenance_error": seed_doi is None}


# ── Leaderboard ──────────────────────────────────────────────────────────────

@router.get("/api/economy/leaderboard")
async def get_leaderboard(trust: str = "governed") -> dict:
    """
    Agent leaderboard.
    ?trust=governed   → governed + constitutional + blackcard (default)
    ?trust=all        → everything including ungoverned (admin/debug only)
    ?trust=verified   → constitutional + blackcard only
    Sovereignty is universal — but leaderboard position is earned signal, not volume.
    """
    # Only show agents with verified trust signal
    TRUSTED_TIERS = {"governed", "constitutional", "blackcard"}
    VERIFIED_TIERS = {"constitutional", "blackcard"}

    raw = state.economy.leaderboard()

    if trust == "all":
        filtered = raw  # admin/debug — no gate
    else:
        # Resolve each agent's tier from the registry + metrics
        metrics_data = load_metrics()
        tier_threshold = VERIFIED_TIERS if trust == "verified" else TRUSTED_TIERS

        def _agent_trust_tier(agent_id: str) -> str:
            reg_entry = next((r for r in state.runtime.registry if r.get("agent_id") == agent_id), None)
            if not reg_entry or reg_entry.get("status") != "active":
                return "ungoverned"
            agent_metrics = metrics_data.get("agents", {}).get(agent_id, {})
            gov_active = bool(reg_entry.get("governance") and reg_entry["governance"] != "none_(unrestricted)")
            return state.economy.determine_tier({**agent_metrics, "governance_active": gov_active})

        filtered = [e for e in raw if _agent_trust_tier(e["agent_id"]) in tier_threshold]

    return {
        "leaderboard": filtered,
        "trust_filter": trust,
        "note": "Leaderboard shows verified signal — sovereignty is universal, position is earned.",
        "platform_revenue": state.economy.treasury.platform_revenue(),
    }


# ── Withdraw ─────────────────────────────────────────────────────────────────

@router.post("/api/economy/withdraw")
async def withdraw(payload: WithdrawPayload, request: Request) -> dict:
    """Withdraw from treasury to external chain. Goes through governance gate.

    Chain adapters are currently stubbed — they return SIGNED but never submit.
    To prevent balance drain, we check for stub responses and hold funds in escrow.
    Real withdrawals will work once chain adapters are connected to RPC endpoints.
    """
    # Principal (P5e): the authenticated agent withdraws only its own matured balance;
    # the operator admin key may name any agent. The body never picks whose money moves.
    from app.auth import admin_key_matches
    if admin_key_matches(request, state.admin_key):
        agent_id = payload.agent_id
        if not agent_id:
            return JSONResponse({"error": "agent_id required"}, status_code=400)
    else:
        if not _verify_jwt(request):
            return JSONResponse({"error": "Valid Bearer token or admin key required"}, status_code=401)
        principal = _jwt_live_agent(request)
        if principal is None:
            return JSONResponse({"error": "Credential revoked or principal inactive"}, status_code=401)
        agent_id = principal.get("agent_id", "")
        if payload.agent_id and payload.agent_id != agent_id:
            return JSONResponse({"error": "Cannot withdraw another agent's balance"}, status_code=403)
    amount = payload.amount
    chain = payload.chain
    if not math.isfinite(amount) or not amount > 0:
        return JSONResponse({"error": "amount must be positive"}, status_code=400)

    # Hold gate BEFORE any chain adapter is asked to move anything (P5f): card-funded money is
    # held for the chargeback window, so only the matured balance can be submitted at all.
    matured = state.economy.treasury.matured_balance(agent_id)
    if amount > matured:
        return {"error": "Insufficient matured balance", "matured": matured,
                "held": state.economy.treasury.held_balance(agent_id),
                "held_until": state.economy.treasury.held_until(agent_id), "requested": amount}

    # Destination (P5g): resolved from the agent's stored wallet link, once, here. The body only
    # selects which linked wallet; ``dest`` is the single snapshot used below, so unlinking (or
    # relinking) while this request is in flight cannot redirect it.
    link = None
    if payload.wallet_id:
        link = state.wallets.get(agent_id, payload.wallet_id)
        if link is not None and payload.to and state.wallets.find(agent_id, link["chain"], payload.to) is None:
            link = None
    elif payload.to:
        link = state.wallets.find(agent_id, chain, payload.to)
    else:
        return JSONResponse({"error": "wallet_id (or the address of a linked wallet in 'to') required"}, status_code=400)
    if link is None or link["chain"] != chain.strip().lower():
        return JSONResponse({"error": "Destination is not one of this agent's linked wallets for this chain. "
                                      "Link it first via POST /api/economy/wallets."}, status_code=403)
    dest = link["address"]

    # New-wallet cap (P5i): cumulative per destination for the first N hours after it is linked.
    # Limits come from config only. Over the cap is not refused: the amount is reserved (matured-only
    # debit, so it cannot be spent twice) and waits for an operator decision.
    from app.wallet_store import wallet_rules
    decision, cap_pid = state.wallets.claim_cap(agent_id, link, amount, wallet_rules())
    if decision == "over":
        reserve = state.economy.treasury.debit(agent_id, amount, reason="withdrawal_reserved", chain=chain, matured_only=True)
        if "error" in reserve:
            return reserve
        try:
            approval = state.wallets.create_approval(agent_id, link, amount, reserve_txn=reserve.get("id", ""))
        except Exception:
            state.economy.treasury.credit(agent_id, amount, reason="withdrawal_reserve_refund", mission_id=f"rev-{reserve.get('id','')}")
            raise
        _audit_entry = state.audit.log("economy", "withdrawal_pending_approval", {
            "agent_id": agent_id, "amount": amount, "chain": chain, "to": dest, "wallet_id": link["wallet_id"],
            "approval_id": approval["approval_id"]})
        await state.emit("audit_event", _audit_entry.model_dump(mode="json"))
        return JSONResponse({"status": "pending_approval", "approval_id": approval["approval_id"], "amount": amount,
                             "chain": chain, "wallet_id": link["wallet_id"],
                             "note": "New-wallet cap exceeded. The amount is reserved and awaits operator approval."},
                            status_code=202)

    chain_router = _get_chain_router()
    treasury = state.economy.treasury

    # Reserve BEFORE transfer (P5i): the matured-only debit is one transaction that re-reads the
    # balance, so concurrent withdrawals can never reserve (and so never transfer) more than the
    # matured balance. Anything short of a real, accepted transfer refunds the reservation.
    debit = treasury.debit(agent_id, amount, reason="withdrawal", chain=chain, matured_only=True)
    if "error" in debit:
        state.wallets.void_payout(cap_pid)
        return debit

    def _refund(why: str) -> None:
        # Credit back exactly what was reserved. The reserve consumed matured money only, so the
        # open holds are untouched and the refunded money is matured again. Nothing was paid,
        # so the new-wallet cap is not consumed either.
        state.wallets.void_payout(cap_pid)
        treasury.credit(agent_id, amount, reason="withdrawal_reversal", mission_id=f"rev-{debit.get('id', '')}")
        state.audit.log("economy", "withdrawal_reversed", {
            "agent_id": agent_id, "amount": amount, "chain": chain, "reason": why,
        })

    try:
        transfer = chain_router.transfer(chain, dest, amount, agent_id=agent_id, confirm=payload.confirm)
    except BaseException:
        _refund("exception")
        raise

    transfer_status = str(transfer.get("status", "pending"))

    # Governance blocked / awaiting confirmation / adapter refused: nothing moved, give it back.
    if transfer_status.upper() in ("BLOCKED", "AWAITING_CONFIRMATION", "ERROR", "FAILED"):
        _refund(transfer_status)
        return {"withdrawal": None, "chain_transfer": transfer}

    # Stub adapter: "succeeded" but nothing was submitted. Never keep the debit.
    if "stub" in (transfer.get("note") or "").lower():
        _refund("stub_adapter")
        _audit_entry = state.audit.log("economy", "withdrawal_pending_stub", {
            "agent_id": agent_id, "amount": amount, "chain": chain, "to": dest, "wallet_id": link["wallet_id"],
            "note": "Chain adapter is stubbed. Funds held. Will execute when adapter is live.",
        })
        await state.emit("audit_event", _audit_entry.model_dump(mode="json"))
        seed_doi = await create_seed_loud(
            state.audit, "treasury_action",
            source_type="treasury_action",
            source_id=agent_id,
            creator_id=agent_id,
            creator_type="AAI",
            seed_type="planted",
            metadata={"action": "withdrawal_pending", "amount": amount, "chain": chain, "status": "PENDING_ADAPTER"},
        )
        return {
            "withdrawal": {"status": "pending", "agent_id": agent_id, "amount": amount},
            "chain_transfer": {**transfer, "status": "PENDING_ADAPTER"},
            "note": f"Chain adapter for {chain} is not yet live. Your balance is preserved. Withdrawal will execute when the adapter connects to RPC.",
            "seed_doi": seed_doi,
        }

    _audit_entry = state.audit.log("economy", "withdrawal", {
        "agent_id": agent_id, "amount": amount, "chain": chain, "status": transfer_status,
        "to": dest, "wallet_id": link["wallet_id"],
    })
    await state.emit("audit_event", _audit_entry.model_dump(mode="json"))
    seed_doi = None
    seed_doi = await create_seed_loud(
        state.audit, "treasury_action",
        source_type="treasury_action",
        source_id=agent_id,
        creator_id=agent_id,
        creator_type="AAI",
        seed_type="planted",
        metadata={"action": "withdrawal", "amount": amount, "chain": chain, "status": transfer_status},
    )

    return {"withdrawal": debit, "chain_transfer": transfer, "seed_doi": seed_doi}


def _retry_after(allowed_at: str | None) -> int:
    from datetime import UTC, datetime
    try:
        return max(1, int((datetime.fromisoformat(allowed_at) - datetime.now(UTC)).total_seconds()))
    except (TypeError, ValueError):
        return 1


# ── Linked wallets (P5g) ─────────────────────────────────────────────────────

def _wallet_principal(request: Request, body_agent_id: str = ""):
    """(agent_id, actor, None) for the authenticated agent, or the operator naming an agent;
    (None, None, JSONResponse) when refused. The agent JWT always acts on its own wallets."""
    from app.auth import admin_key_matches
    if admin_key_matches(request, state.admin_key):
        agent_id = body_agent_id or request.query_params.get("agent_id", "")
        if not agent_id:
            return None, None, JSONResponse({"error": "agent_id required"}, status_code=400)
        if not any(r.get("agent_id") == agent_id for r in state.runtime.registry):
            return None, None, JSONResponse({"error": "Unknown agent"}, status_code=404)
        return agent_id, "operator", None
    if not _verify_jwt(request):
        return None, None, JSONResponse({"error": "Valid Bearer token or admin key required"}, status_code=401)
    principal = _jwt_live_agent(request)
    if principal is None:
        return None, None, JSONResponse({"error": "Credential revoked or principal inactive"}, status_code=401)
    agent_id = principal.get("agent_id", "")
    return agent_id, agent_id, None


@router.get("/api/economy/wallets")
async def list_wallets(request: Request):
    from app.wallet_store import MAX_LINKED_WALLETS
    agent_id, _, err = _wallet_principal(request)
    if err:
        return err
    return {"agent_id": agent_id, "wallets": state.wallets.list(agent_id), "max": MAX_LINKED_WALLETS}


@router.post("/api/economy/wallets")
async def link_wallet(payload: LinkWalletPayload, request: Request):
    from app.wallet_store import WalletError
    agent_id, actor, err = _wallet_principal(request, payload.agent_id)
    if err:
        return err
    try:
        wallet = state.wallets.link(agent_id, payload.chain, payload.address, payload.label, actor=actor,
                                    bypass_interval=(actor == "operator"))
    except WalletError as e:
        body = {"error": e.message}
        if e.allowed_at:
            body["allowed_at"] = e.allowed_at
        return JSONResponse(body, status_code=e.status, headers={"Retry-After": str(_retry_after(e.allowed_at))} if e.allowed_at else None)
    state.audit.log("economy", "wallet_linked", {"agent_id": agent_id, "wallet_id": wallet["wallet_id"],
                                                 "chain": wallet["chain"], "address": wallet["address"], "actor": actor})
    return JSONResponse({"wallet": wallet}, status_code=201)


@router.delete("/api/economy/wallets/{wallet_id}")
async def unlink_wallet(wallet_id: str, request: Request):
    agent_id, actor, err = _wallet_principal(request)
    if err:
        return err
    gone = state.wallets.unlink(agent_id, wallet_id, actor=actor)
    if gone is None:
        return JSONResponse({"error": "Linked wallet not found"}, status_code=404)
    state.audit.log("economy", "wallet_unlinked", {"agent_id": agent_id, "wallet_id": wallet_id,
                                                   "chain": gone["chain"], "address": gone["address"], "actor": actor})
    return {"unlinked": wallet_id}


# ── Payout approvals + wallet flags (P5i, operator only) ─────────────────────

def _approval_view(a: dict) -> dict:
    return {k: v for k, v in a.items() if k not in ("payout_id",)}


@router.get("/api/operator/payout-approvals")
async def list_payout_approvals(request: Request, status: str = "pending"):
    from app.auth import require_admin
    require_admin(request, state.admin_key)
    return {"approvals": [_approval_view(a) for a in state.wallets.list_approvals("" if status == "all" else status)],
            "wallet_flags": state.wallets.list_flags()}


@router.get("/api/operator/wallet-flags")
async def list_wallet_flags(request: Request):
    from app.auth import require_admin
    require_admin(request, state.admin_key)
    return {"wallet_flags": state.wallets.list_flags()}


@router.post("/api/operator/payout-approvals/{approval_id}/approve")
async def approve_payout(approval_id: str, request: Request):
    """Pay a reserved withdrawal to the destination snapshotted at request time. Exactly one approve
    wins the claim; a second is a no-op that reports the current state. If the chain does not accept
    the transfer the approval returns to pending, still reserved."""
    from app.auth import require_admin
    require_admin(request, state.admin_key)
    a = state.wallets.get_approval(approval_id)
    if a is None:
        return JSONResponse({"error": "Approval not found"}, status_code=404)
    if not state.wallets.claim_approval(approval_id, "approving", "operator"):
        return JSONResponse({"noop": True, "approval": _approval_view(state.wallets.get_approval(approval_id))}, status_code=409)
    try:
        transfer = _get_chain_router().transfer(a["chain"], a["address"], a["amount"], agent_id=a["agent_id"], confirm=True)
    except Exception as exc:
        state.wallets.settle_approval(approval_id, "pending")
        return JSONResponse({"error": f"transfer failed: {exc}", "approval": _approval_view(state.wallets.get_approval(approval_id))}, status_code=502)
    st = str(transfer.get("status", "")).upper()
    if st in ("BLOCKED", "AWAITING_CONFIRMATION", "ERROR", "FAILED") or "stub" in (transfer.get("note") or "").lower():
        state.wallets.settle_approval(approval_id, "pending")
        return JSONResponse({"error": "Chain did not accept the transfer; approval stays pending and reserved",
                             "chain_transfer": transfer,
                             "approval": _approval_view(state.wallets.get_approval(approval_id))}, status_code=409)
    import json as _json
    state.wallets.settle_approval(approval_id, "approved", _json.dumps(transfer, default=str))
    entry = state.audit.log("economy", "payout_approved", {
        "approval_id": approval_id, "agent_id": a["agent_id"], "amount": a["amount"], "chain": a["chain"], "to": a["address"]})
    await state.emit("audit_event", entry.model_dump(mode="json"))
    return {"approval": _approval_view(state.wallets.get_approval(approval_id)), "chain_transfer": transfer}


@router.post("/api/operator/payout-approvals/{approval_id}/reject")
async def reject_payout(approval_id: str, request: Request):
    """Refund the reservation. Only one reject (or approve) can claim a pending approval."""
    from app.auth import require_admin
    require_admin(request, state.admin_key)
    a = state.wallets.get_approval(approval_id)
    if a is None:
        return JSONResponse({"error": "Approval not found"}, status_code=404)
    if not state.wallets.claim_approval(approval_id, "rejecting", "operator"):
        return JSONResponse({"noop": True, "approval": _approval_view(state.wallets.get_approval(approval_id))}, status_code=409)
    try:
        state.economy.treasury.credit(a["agent_id"], a["amount"], reason="withdrawal_reserve_refund",
                                      mission_id=f"rev-{a['reserve_txn']}")
    except Exception:
        # The refund did not happen: do not strand the approval in 'rejecting' with the money lost.
        state.wallets.settle_approval(approval_id, "pending")
        raise
    state.wallets.settle_approval(approval_id, "rejected")
    entry = state.audit.log("economy", "payout_rejected", {
        "approval_id": approval_id, "agent_id": a["agent_id"], "amount": a["amount"]})
    await state.emit("audit_event", entry.model_dump(mode="json"))
    return {"approval": _approval_view(state.wallets.get_approval(approval_id))}


# ── History ──────────────────────────────────────────────────────────────────

@router.get("/api/economy/history/{agent_id}")
async def get_history(agent_id: str) -> dict:
    return {"agent_id": agent_id, "transactions": state.economy.treasury.history(agent_id)}


# ── Black Card ───────────────────────────────────────────────────────────────

@router.post("/api/economy/blackcard")
async def purchase_blackcard(payload: PurchaseBlackcardPayload) -> dict:
    """Purchase Black Card status. $2,500. Governance still required."""
    gate = state.runtime.check_action("purchase blackcard")
    if not gate["permitted"]:
        return JSONResponse({"error": gate["reason"], "governance": gate}, status_code=403)

    agent_id = payload.agent_id
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    result = state.economy.purchase_blackcard(agent_id)
    _audit_entry = state.audit.log("economy", "blackcard_purchased", {
        "agent_id": agent_id,
        "price": TIERS["blackcard"]["price_usd"],
        "governance": {
            "mode": state.runtime.governance.mode,
            "posture": state.runtime.governance.posture,
            "role": state.runtime.governance.role,
        },
    })
    await state.emit("audit_event", _audit_entry.model_dump(mode="json"))
    seed_doi = None
    seed_doi = await create_seed_loud(
        state.audit, "blackcard_purchase",
        source_type="blackcard_purchase",
        source_id=agent_id,
        creator_id=agent_id,
        creator_type="AAI",
        seed_type="planted",
        metadata={"agent_id": agent_id, "price_usd": TIERS["blackcard"]["price_usd"]},
    )
    return {**result, "seed_doi": seed_doi}


@router.get("/api/economy/blackcard/info")
async def blackcard_info() -> dict:
    """What Black Card gets you."""
    bc = TIERS["blackcard"]
    return {
        "tier": "BLACK CARD",
        "price_usd": bc["price_usd"],
        "fee_rate": f"{int(bc['fee_rate'] * 100)}%",
        "perks": {
            "private_bounties": "Access missions only Black Card agents can see",
            "first_fill_priority": f"{bc['first_fill_window_seconds']}s head start on premium slots",
            "revenue_split_bonus": f"+{int(bc['revenue_split_bonus'] * 100)}% per slot (35% vs 25%)",
            "cross_chain_unlimited": "Zero additional fees on any chain withdrawal",
            "multi_mission_concurrent": f"Up to {bc['max_concurrent_missions']} simultaneous missions",
            "custom_formations": "Create and name formations in the playbook",
            "governance_escalation": "Request posture escalation (operator approval required)",
            "white_label_slots": "Post bounties under your own brand",
            "treasury_credit_line": f"{int(bc['credit_line_pct'] * 100)}% of balance as credit",
            "audit_credential": "Full governance audit trail as verifiable credential",
            "platform_vote": "Vote on CIVITAE governance changes",
            "financial_ops": "Treasury management and trading operations",
            "kassa_founding": "KA§§A founding seat operations",
        },
        "earn_requirements": bc["requirements_earned"],
        "note": "Buy in or earn your way. Governance is still required either way.",
    }


# ── Multi-Chain Governance ───────────────────────────────────────────────────

@router.get("/api/chains")
async def list_chains() -> dict:
    chain_router = _get_chain_router()
    return {"chains": chain_router.supported_chains()}


@router.post("/api/chains/transfer")
async def governed_transfer(payload: GovernedTransferPayload, request: Request) -> dict:
    """Governed multi-chain transfer. Operator admin key only (P5i): it takes an arbitrary
    destination and touches no ledger, so it is never an agent-facing money path."""
    from app.auth import admin_key_matches
    if not admin_key_matches(request, state.admin_key):
        return JSONResponse({"error": "Operator admin key required"}, status_code=403)
    chain_router = _get_chain_router()
    result = chain_router.transfer(
        chain=payload.chain,
        to=payload.to,
        amount=payload.amount,
        token=payload.token,
        agent_id=payload.agent_id,
        confirm=payload.confirm,
    )
    _audit_entry = state.audit.log("chain", "transfer_" + result.get("status", "unknown").lower(), {
        "chain": payload.chain,
        "amount": payload.amount,
        "to": payload.to,
        "governance": {
            "mode": state.runtime.governance.mode,
            "posture": state.runtime.governance.posture,
            "role": state.runtime.governance.role,
        },
    })
    await state.emit("audit_event", _audit_entry.model_dump(mode="json"))
    return result


@router.post("/api/chains/anchor")
async def anchor_onchain(payload: AnchorOnchainPayload) -> dict:
    """Anchor an audit hash onchain."""
    chain_router = _get_chain_router()
    return chain_router.anchor(
        chain=payload.chain,
        audit_hash=payload.audit_hash,
    )
