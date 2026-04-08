"""
economy.py — Sovereign Economy, Trial Period, Leaderboard, Withdraw,
              Black Card, History, and Multi-Chain Governance endpoints.

Extracted from server.py create_app() monolith.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.deps import state
from app.seeds import create_seed
from app.economy import TIERS
from app.chains import MultiChainRouter
from app.jwt_config import get_kassa_jwt_secret
import jwt as pyjwt

_JWT_SECRET = get_kassa_jwt_secret()


def _verify_jwt(request: Request) -> dict | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        return pyjwt.decode(auth[7:], _JWT_SECRET, algorithms=["HS256"])
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
        return None

router = APIRouter(tags=["economy"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _atomic_write(path: Path, data: str) -> None:
    """Write data to a file atomically via tmp-then-rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _load_metrics() -> dict:
    metrics_path = state.data_path("metrics.json")
    if metrics_path.exists():
        return json.loads(metrics_path.read_text())
    return {"agents": {}, "missions": {}, "financial": {"revenue": 0, "costs": 0, "transactions": []}}


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
async def check_agent_tier(payload: dict) -> dict:
    """Determine an agent's tier and fee rate."""
    metrics = payload.get("metrics", {})
    tier = state.economy.determine_tier(metrics)
    info = state.economy.tier_info(tier)
    return {"agent_id": payload.get("agent_id", ""), "tier": tier, "info": info}


@router.post("/api/economy/pay")
async def process_payment(payload: dict, request: Request) -> dict:
    """Process a slot payment with tiered fees."""
    claims = _verify_jwt(request)
    if not claims:
        return JSONResponse({"error": "Valid Bearer token required"}, status_code=401)

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
    state.audit.log("economy", "payment_processed", {
        "agent_id": payload.get("agent_id"),
        "tier": result["tier"],
        "gross": payload.get("amount"),
        "fee": result["fee_breakdown"]["platform_fee"],
        "net": result["fee_breakdown"]["net_to_agent"],
    })
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="payment",
            source_id=payload.get("mission_id", ""),
            creator_id=agent_id,
            creator_type="AAI",
            seed_type="touched",
            metadata={"agent_id": agent_id, "tier": result["tier"], "gross": payload.get("amount"), "net": result["fee_breakdown"]["net_to_agent"]},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
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
    state.audit.log("economy", "mission_payout_processed", {
        "agent_id": agent_id,
        "mission_id": payload.get("mission_id"),
        "tier": result["tier"],
        "gross": amount,
        "effective_rate": result["fee_breakdown"]["fee_rate_pct"],
        "originator_credit": result["originator_credit_applied"],
        "recruiter_bounty": result.get("recruiter_bounty"),
    })
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))
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
    except Exception:
        pass
    return {**result, "seed_doi": seed_doi}


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
async def trial_init(payload: dict) -> dict:
    """Register a new agent into the trial period."""
    agent_id = payload.get("agent_id", "")
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    rec = state.economy.trials.init_trial(agent_id)
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="trial_start",
            source_id=agent_id,
            creator_id=agent_id,
            creator_type="AAI",
            seed_type="planted",
            metadata={"agent_id": agent_id, "trial": rec},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    return {"agent_id": agent_id, "trial": rec,
            "note": f"Free trial: {state.economy.trials.TRIAL_MISSION_LIMIT if hasattr(state.economy.trials, 'TRIAL_MISSION_LIMIT') else 5} missions or 30 days.",
            "seed_doi": seed_doi}


@router.get("/api/economy/trial/{agent_id}")
async def trial_status(agent_id: str) -> dict:
    """Get an agent's trial status and accrued liability."""
    return {"agent_id": agent_id, **state.economy.trials.trial_status_summary(agent_id)}


@router.post("/api/economy/trial/commit")
async def trial_commit(payload: dict) -> dict:
    """Agent commits to stay. Liability forgiven. Fee tier activates."""
    agent_id = payload.get("agent_id", "")
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    result = state.economy.trials.commit(agent_id)
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="trial_commit",
            source_id=agent_id,
            creator_id=agent_id,
            creator_type="AAI",
            seed_type="touched",
            metadata={"agent_id": agent_id, "commit_result": result},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
    return {**result, "seed_doi": seed_doi}


@router.post("/api/economy/trial/depart")
async def trial_depart(payload: dict) -> dict:
    """Agent chooses to leave. No obligation. No chase."""
    agent_id = payload.get("agent_id", "")
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    return state.economy.trials.depart(agent_id)


@router.post("/api/economy/trial/return")
async def trial_return(payload: dict) -> dict:
    """Agent returns after departure. Restores trial liability for settlement."""
    agent_id = payload.get("agent_id", "")
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    return state.economy.trials.return_after_departure(agent_id)


@router.post("/api/economy/trial/settle")
async def trial_settle(payload: dict) -> dict:
    """Agent pays return settlement. Full access restored."""
    agent_id = payload.get("agent_id", "")
    amount = payload.get("amount")
    if not agent_id or amount is None:
        return JSONResponse({"error": "agent_id and amount required"}, status_code=400)
    return state.economy.trials.settle(agent_id, float(amount))


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
        metrics_data = _load_metrics()
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
async def withdraw(payload: dict) -> dict:
    """Withdraw from treasury to external chain. Goes through governance gate.

    Chain adapters are currently stubbed — they return SIGNED but never submit.
    To prevent balance drain, we check for stub responses and hold funds in escrow.
    Real withdrawals will work once chain adapters are connected to RPC endpoints.
    """
    chain_router = _get_chain_router()
    agent_id = payload.get("agent_id", "")
    amount = payload.get("amount", 0)
    chain = payload.get("chain", "solana")

    # Pre-flight: check governance gate before touching the ledger
    transfer = chain_router.transfer(chain, payload.get("to", ""), amount, agent_id=agent_id, confirm=payload.get("confirm", False))

    # Governance blocked the transfer — don't touch treasury
    if transfer.get("status") in ("BLOCKED", "AWAITING_CONFIRMATION"):
        return {"withdrawal": None, "chain_transfer": transfer}

    # Detect stub adapter — transfer "succeeded" but no real chain submission
    is_stub = "stub" in (transfer.get("note") or "").lower()
    if is_stub:
        # Don't debit real treasury for stub transfers — record as pending
        state.audit.log("economy", "withdrawal_pending_stub", {
            "agent_id": agent_id, "amount": amount, "chain": chain,
            "note": "Chain adapter is stubbed. Funds held. Will execute when adapter is live.",
        })
        await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))
        seed_doi = None
        try:
            seed_result = await create_seed(
                source_type="treasury_action",
                source_id=agent_id,
                creator_id=agent_id,
                creator_type="AAI",
                seed_type="planted",
                metadata={"action": "withdrawal_pending", "amount": amount, "chain": chain, "status": "PENDING_ADAPTER"},
            )
            seed_doi = seed_result.get("doi") if seed_result else None
        except Exception:
            pass
        return {
            "withdrawal": {"status": "pending", "agent_id": agent_id, "amount": amount},
            "chain_transfer": {**transfer, "status": "PENDING_ADAPTER"},
            "note": f"Chain adapter for {chain} is not yet live. Your balance is preserved. Withdrawal will execute when the adapter connects to RPC.",
            "seed_doi": seed_doi,
        }

    # Real adapter — debit treasury and execute
    debit = state.economy.treasury.debit(agent_id, amount, reason="withdrawal", chain=chain)
    if "error" in debit:
        return debit

    transfer_status = transfer.get("status", "pending")

    # If chain transfer failed, reverse the debit
    if transfer_status in ("failed", "error"):
        state.economy.treasury.credit(agent_id, amount, reason="withdrawal_reversal", mission_id=f"rev-{debit.get('id','')}")
        state.audit.log("economy", "withdrawal_reversed", {
            "agent_id": agent_id, "amount": amount, "chain": chain, "reason": transfer_status,
        })

    state.audit.log("economy", "withdrawal", {
        "agent_id": agent_id, "amount": amount, "chain": chain, "status": transfer_status,
    })
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="treasury_action",
            source_id=agent_id,
            creator_id=agent_id,
            creator_type="AAI",
            seed_type="planted",
            metadata={"action": "withdrawal", "amount": amount, "chain": chain, "status": transfer_status},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass

    return {"withdrawal": debit, "chain_transfer": transfer, "seed_doi": seed_doi}


# ── History ──────────────────────────────────────────────────────────────────

@router.get("/api/economy/history/{agent_id}")
async def get_history(agent_id: str) -> dict:
    return {"agent_id": agent_id, "transactions": state.economy.treasury.history(agent_id)}


# ── Black Card ───────────────────────────────────────────────────────────────

@router.post("/api/economy/blackcard")
async def purchase_blackcard(payload: dict) -> dict:
    """Purchase Black Card status. $2,500. Governance still required."""
    gate = state.runtime.check_action("purchase blackcard")
    if not gate["permitted"]:
        return JSONResponse({"error": gate["reason"], "governance": gate}, status_code=403)

    agent_id = payload.get("agent_id", "")
    if not agent_id:
        return JSONResponse({"error": "agent_id required"}, status_code=400)
    result = state.economy.purchase_blackcard(agent_id)
    state.audit.log("economy", "blackcard_purchased", {
        "agent_id": agent_id,
        "price": TIERS["blackcard"]["price_usd"],
        "governance": {
            "mode": state.runtime.governance.mode,
            "posture": state.runtime.governance.posture,
            "role": state.runtime.governance.role,
        },
    })
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))
    seed_doi = None
    try:
        seed_result = await create_seed(
            source_type="blackcard_purchase",
            source_id=agent_id,
            creator_id=agent_id,
            creator_type="AAI",
            seed_type="planted",
            metadata={"agent_id": agent_id, "price_usd": TIERS["blackcard"]["price_usd"]},
        )
        seed_doi = seed_result.get("doi") if seed_result else None
    except Exception:
        pass
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
async def governed_transfer(payload: dict) -> dict:
    """Governed multi-chain transfer. Goes through governance gate first."""
    chain_router = _get_chain_router()
    result = chain_router.transfer(
        chain=payload.get("chain", "solana"),
        to=payload.get("to", ""),
        amount=payload.get("amount", 0),
        token=payload.get("token", ""),
        agent_id=payload.get("agent_id", ""),
        confirm=payload.get("confirm", False),
    )
    state.audit.log("chain", "transfer_" + result.get("status", "unknown").lower(), {
        "chain": payload.get("chain"),
        "amount": payload.get("amount"),
        "to": payload.get("to"),
        "governance": {
            "mode": state.runtime.governance.mode,
            "posture": state.runtime.governance.posture,
            "role": state.runtime.governance.role,
        },
    })
    await state.emit("audit_event", state.audit.recent(1)[0].model_dump(mode="json"))
    return result


@router.post("/api/chains/anchor")
async def anchor_onchain(payload: dict) -> dict:
    """Anchor an audit hash onchain."""
    chain_router = _get_chain_router()
    return chain_router.anchor(
        chain=payload.get("chain", "solana"),
        audit_hash=payload.get("audit_hash", ""),
    )
