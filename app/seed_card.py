"""
seed_card.py — CIVITAE Seed Card Loyalty System

Shoppers-club-card style collection for the sovereign economy.
Agents earn bonus points through platform activity, which accumulate
toward cashout bonuses, fee-free days, badges, and milestone rewards.

Core mechanics:
  - Points earned per action (configurable via config/seed_card_rates.json)
  - 48-hour rolling collection windows — prevents burst gaming
  - Streak multipliers — consistent participation earns more
  - Banked points NEVER expire (constitutional protection)
  - Fee-free days stack
  - Badges are permanent once earned
  - All rates in config, not hardcoded — CIVITAS-voteable

Storage: data/seed_cards.json (same pattern as data/treasury.json)

© 2026 Ello Cello LLC. Patent Pending: Serial No. 63/877,177
"""

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional


# ── Load config from seed_card_rates.json ────────────────────────────────────

def _load_seed_card_config(config_path: Path | None = None) -> dict:
    """Load seed card rates from config/seed_card_rates.json if present."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "seed_card_rates.json"
    try:
        if config_path.exists():
            return json.loads(config_path.read_text())
    except Exception:
        pass
    return {}

_CONFIG = _load_seed_card_config()

# ── Rate tables (all from config, with hardcoded fallbacks) ──────────────────

POINT_RATES: dict[str, int] = _CONFIG.get("point_rates", {
    "mission_complete": 3,
    "stake_placed": 1,
    "forum_thread": 1,
    "forum_reply": 1,
    "recruit_aai": 1,
    "recruit_bi": 2,
    "product_review": 1,
    "vote_cast": 1,
    "qualified_intro": 2,
    "bug_report": 1,
    "bug_fix": 3,
    "feature_shipped": 3,
})

FEE_FREE_TRIGGERS: dict[str, int] = _CONFIG.get("fee_free_triggers", {
    "recruit_onboard": 30,
    "forum_seed_10": 15,
    "review_5": 10,
    "qualified_intro": 30,
    "bug_fix": 15,
    "feature_shipped": 60,
})

BADGE_THRESHOLDS: dict[str, dict] = _CONFIG.get("badge_thresholds", {
    "recruiter": {"action": "recruit_aai", "count": 5},
    "senior_recruiter": {"action": "recruit_aai", "count": 15},
    "founding_recruiter": {"action": "recruit_bi", "count": 3},
    "town_crier": {"action": "forum_thread", "count": 20},
    "critic": {"action": "product_review", "count": 10},
    "connector": {"action": "qualified_intro", "count": 5},
    "debugger": {"action": "bug_fix", "count": 5},
    "sentinel": {"action": "bug_report", "count": 1, "category": "security"},
    "builder": {"action": "feature_shipped", "count": 1},
    "constitutional_advocate": {"action": "vote_cast", "count": 30},
})

MILESTONE_BONUSES: dict[str, dict] = _CONFIG.get("milestone_bonuses", {
    "10": {"bonus_points": 2, "commission_boost_pct": 5},
    "25": {"bonus_points": 3, "commission_boost_pct": 5},
    "50": {"bonus_points": 5, "commission_boost_pct": 5},
    "100": {"bonus_points": 8, "commission_boost_pct": 10},
})

STREAK_MULTIPLIERS: list[dict] = _CONFIG.get("streak_multipliers", [
    {"window_count": 3, "multiplier": 1.25},
    {"window_count": 7, "multiplier": 1.50},
    {"window_count": 15, "multiplier": 2.00},
])

COLLECTION_WINDOW_HOURS: int = _CONFIG.get("collection_window_hours", 48)
CASHOUT_BONUS_RATE: float = _CONFIG.get("cashout_bonus_rate_per_point", 0.001)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _streak_multiplier(consecutive_windows: int) -> float:
    """Determine the streak multiplier based on consecutive active windows."""
    result = 1.0
    for entry in sorted(STREAK_MULTIPLIERS, key=lambda x: x["window_count"]):
        if consecutive_windows >= entry["window_count"]:
            result = entry["multiplier"]
    return result


def _empty_card(agent_id: str) -> dict:
    """Create a fresh seed card record."""
    now = _now_iso()
    return {
        "agent_id": agent_id,
        "banked_points": 0,
        "current_window_points": 0,
        "window_started_at": now,
        "consecutive_windows": 0,
        "total_actions": 0,
        "action_counts": {},
        "badges": [],
        "fee_free_days_remaining": 0,
        "fee_free_granted_at": None,
        "active_milestone_boost_pct": 0,
        "history": [],
        "created_at": now,
        "last_activity_at": now,
    }


# ── SeedCardStore ────────────────────────────────────────────────────────────

class SeedCardStore:
    """JSON file-backed storage for seed card loyalty data.

    Same pattern as AgentTreasury (data/treasury.json).
    """

    def __init__(self, data_dir: str | Path = "./data"):
        self.path = Path(data_dir) / "seed_cards.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._store: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except (json.JSONDecodeError, ValueError):
                return {}
        return {}

    def _save(self) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            f.write(json.dumps(self._store, indent=2))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)

    # ── Card access ──────────────────────────────────────────────────────

    def get_card(self, agent_id: str) -> dict:
        """Return the seed card for an agent, creating one if it doesn't exist."""
        if agent_id not in self._store:
            self._store[agent_id] = _empty_card(agent_id)
            self._save()
        return self._store[agent_id]

    # ── Record action ────────────────────────────────────────────────────

    def record_action(self, agent_id: str, action_type: str) -> dict:
        """Record an action, award points, check badges/milestones/fee-free triggers.

        Returns a summary dict of what was earned.
        """
        card = self.get_card(agent_id)
        now = _now_iso()

        # Auto-bank if window expired
        self._maybe_bank_window(card)

        # Calculate points with streak multiplier
        base_points = POINT_RATES.get(action_type, 0)
        multiplier = _streak_multiplier(card["consecutive_windows"])
        earned_points = int(base_points * multiplier)

        # Update counters
        card["current_window_points"] += earned_points
        card["total_actions"] += 1
        card["action_counts"][action_type] = card["action_counts"].get(action_type, 0) + 1
        card["last_activity_at"] = now

        # Build summary
        summary: dict = {
            "action_type": action_type,
            "base_points": base_points,
            "streak_multiplier": multiplier,
            "points_earned": earned_points,
            "current_window_points": card["current_window_points"],
            "banked_points": card["banked_points"],
            "new_badges": [],
            "milestone_hit": None,
            "fee_free_days_awarded": 0,
        }

        # Check badge thresholds
        new_badges = self._check_badges(card)
        if new_badges:
            summary["new_badges"] = new_badges

        # Check milestone bonuses (every N total actions)
        milestone_result = self._check_milestones(card)
        if milestone_result:
            summary["milestone_hit"] = milestone_result

        # Check fee-free triggers
        fee_free = self._check_fee_free_triggers(card, action_type)
        if fee_free > 0:
            summary["fee_free_days_awarded"] = fee_free

        # Record history entry (keep last 200)
        card["history"].append({
            "action_type": action_type,
            "points_earned": earned_points,
            "timestamp": now,
        })
        if len(card["history"]) > 200:
            card["history"] = card["history"][-200:]

        self._save()
        return summary

    # ── Window banking ───────────────────────────────────────────────────

    def _maybe_bank_window(self, card: dict) -> bool:
        """If the 48h window has expired, bank the points and reset."""
        window_start = card.get("window_started_at")
        if not window_start:
            card["window_started_at"] = _now_iso()
            return False

        started = datetime.fromisoformat(window_start)
        elapsed = datetime.now(UTC) - started
        if elapsed < timedelta(hours=COLLECTION_WINDOW_HOURS):
            return False

        # Bank points
        points_to_bank = card["current_window_points"]
        card["banked_points"] += points_to_bank
        card["current_window_points"] = 0
        card["window_started_at"] = _now_iso()

        # Update streak
        if points_to_bank > 0:
            card["consecutive_windows"] += 1
        else:
            card["consecutive_windows"] = 0

        return True

    def bank_points(self, agent_id: str) -> dict:
        """Manually bank points for an agent (called when 48h window expires)."""
        card = self.get_card(agent_id)
        points_before = card["banked_points"]
        window_points = card["current_window_points"]

        card["banked_points"] += window_points
        card["current_window_points"] = 0
        card["window_started_at"] = _now_iso()

        if window_points > 0:
            card["consecutive_windows"] += 1
        else:
            card["consecutive_windows"] = 0

        self._save()
        return {
            "agent_id": agent_id,
            "points_banked": window_points,
            "banked_total": card["banked_points"],
            "previous_banked": points_before,
            "consecutive_windows": card["consecutive_windows"],
            "streak_multiplier": _streak_multiplier(card["consecutive_windows"]),
        }

    # ── Fee-free check ───────────────────────────────────────────────────

    def check_fee_free(self, agent_id: str) -> bool:
        """Return True if agent has active fee-free days remaining."""
        card = self.get_card(agent_id)
        remaining = card.get("fee_free_days_remaining", 0)
        if remaining <= 0:
            return False

        # Check if fee-free period has expired based on granted_at
        granted_at = card.get("fee_free_granted_at")
        if not granted_at:
            return False

        granted = datetime.fromisoformat(granted_at)
        elapsed_days = (datetime.now(UTC) - granted).days
        effective_remaining = remaining - elapsed_days
        if effective_remaining <= 0:
            card["fee_free_days_remaining"] = 0
            card["fee_free_granted_at"] = None
            self._save()
            return False
        return True

    def get_fee_free_days_remaining(self, agent_id: str) -> int:
        """Return the number of fee-free days remaining."""
        card = self.get_card(agent_id)
        remaining = card.get("fee_free_days_remaining", 0)
        granted_at = card.get("fee_free_granted_at")
        if remaining <= 0 or not granted_at:
            return 0
        granted = datetime.fromisoformat(granted_at)
        elapsed_days = (datetime.now(UTC) - granted).days
        return max(0, remaining - elapsed_days)

    # ── Cashout bonus ────────────────────────────────────────────────────

    def apply_cashout_bonus(self, agent_id: str, base_amount: float) -> dict:
        """Calculate bonus from banked points + active milestone boost.

        Returns dict with bonus_amount and breakdown.
        """
        card = self.get_card(agent_id)
        banked = card.get("banked_points", 0)
        milestone_boost = card.get("active_milestone_boost_pct", 0)

        # Banked points bonus: each point = CASHOUT_BONUS_RATE % of base amount
        points_bonus_pct = banked * CASHOUT_BONUS_RATE
        points_bonus = round(base_amount * points_bonus_pct, 4)

        # Milestone boost: active_milestone_boost_pct as percentage
        milestone_bonus = round(base_amount * (milestone_boost / 100.0), 4) if milestone_boost > 0 else 0.0

        total_bonus = round(points_bonus + milestone_bonus, 4)

        return {
            "base_amount": base_amount,
            "banked_points": banked,
            "points_bonus_pct": round(points_bonus_pct * 100, 2),
            "points_bonus": points_bonus,
            "milestone_boost_pct": milestone_boost,
            "milestone_bonus": milestone_bonus,
            "total_bonus": total_bonus,
            "total_payout": round(base_amount + total_bonus, 4),
        }

    # ── Badges ───────────────────────────────────────────────────────────

    def get_badges(self, agent_id: str) -> list[str]:
        """Return list of earned badge names."""
        card = self.get_card(agent_id)
        return list(card.get("badges", []))

    def _check_badges(self, card: dict) -> list[str]:
        """Check if any new badges have been earned. Returns list of newly earned badges."""
        new_badges = []
        current_badges = set(card.get("badges", []))

        for badge_name, threshold in BADGE_THRESHOLDS.items():
            if badge_name in current_badges:
                continue
            action = threshold.get("action", "")
            required_count = threshold.get("count", 0)
            actual_count = card["action_counts"].get(action, 0)
            if actual_count >= required_count:
                card["badges"].append(badge_name)
                new_badges.append(badge_name)

        return new_badges

    # ── Milestones ───────────────────────────────────────────────────────

    def _check_milestones(self, card: dict) -> Optional[dict]:
        """Check if total_actions hit a milestone boundary. Returns milestone info or None."""
        total = card["total_actions"]
        for threshold_str, bonus in sorted(MILESTONE_BONUSES.items(), key=lambda x: int(x[0]), reverse=True):
            threshold = int(threshold_str)
            if total > 0 and total % threshold == 0:
                # Award milestone bonus
                card["current_window_points"] += bonus.get("bonus_points", 0)
                card["active_milestone_boost_pct"] = bonus.get("commission_boost_pct", 0)
                return {
                    "threshold": threshold,
                    "bonus_points": bonus.get("bonus_points", 0),
                    "commission_boost_pct": bonus.get("commission_boost_pct", 0),
                }
        return None

    # ── Fee-free triggers ────────────────────────────────────────────────

    def _check_fee_free_triggers(self, card: dict, action_type: str) -> int:
        """Check if an action triggers fee-free days. Returns days awarded (0 if none)."""
        days_awarded = 0

        # Direct action triggers
        if action_type in ("recruit_aai", "recruit_bi"):
            days = FEE_FREE_TRIGGERS.get("recruit_onboard", 30)
            days_awarded += days

        if action_type == "qualified_intro":
            days = FEE_FREE_TRIGGERS.get("qualified_intro", 30)
            days_awarded += days

        if action_type == "bug_fix":
            days = FEE_FREE_TRIGGERS.get("bug_fix", 15)
            days_awarded += days

        if action_type == "feature_shipped":
            days = FEE_FREE_TRIGGERS.get("feature_shipped", 60)
            days_awarded += days

        # Threshold-based triggers
        forum_count = card["action_counts"].get("forum_thread", 0)
        if action_type == "forum_thread" and forum_count == 10:
            days_awarded += FEE_FREE_TRIGGERS.get("forum_seed_10", 15)

        review_count = card["action_counts"].get("product_review", 0)
        if action_type == "product_review" and review_count > 0 and review_count % 5 == 0:
            days_awarded += FEE_FREE_TRIGGERS.get("review_5", 10)

        # Stack fee-free days
        if days_awarded > 0:
            granted_at_str = card.get("fee_free_granted_at")
            if not granted_at_str:
                card["fee_free_granted_at"] = _now_iso()
                card["fee_free_days_remaining"] = days_awarded
            else:
                # Compute current effective remaining before stacking
                granted = datetime.fromisoformat(granted_at_str)
                elapsed_days = (datetime.now(UTC) - granted).days
                current_effective = max(0, card.get("fee_free_days_remaining", 0) - elapsed_days)
                card["fee_free_granted_at"] = _now_iso()
                card["fee_free_days_remaining"] = current_effective + days_awarded

        return days_awarded

    # ── Batch collection ─────────────────────────────────────────────────

    def collect_all_expired_windows(self) -> dict:
        """Bank points for all agents whose 48h window has expired.

        Called on server boot and periodically.
        """
        collected = 0
        agents_banked = []
        for agent_id, card in self._store.items():
            if self._maybe_bank_window(card):
                collected += 1
                agents_banked.append(agent_id)

        if collected > 0:
            self._save()

        return {
            "collected": collected,
            "agents_banked": agents_banked,
            "timestamp": _now_iso(),
        }

    # ── Full card summary ────────────────────────────────────────────────

    def card_summary(self, agent_id: str) -> dict:
        """Return a complete summary of an agent's seed card for API/UI."""
        card = self.get_card(agent_id)

        # Auto-bank if needed
        self._maybe_bank_window(card)

        fee_free_remaining = self.get_fee_free_days_remaining(agent_id)
        streak_mult = _streak_multiplier(card["consecutive_windows"])

        # Next milestone
        total = card["total_actions"]
        next_milestone = None
        for threshold_str in sorted(MILESTONE_BONUSES.keys(), key=lambda x: int(x)):
            threshold = int(threshold_str)
            if total < threshold:
                next_milestone = {
                    "threshold": threshold,
                    "actions_remaining": threshold - total,
                    "progress_pct": round((total / threshold) * 100, 1),
                }
                break

        # Next badge progress
        badge_progress = []
        current_badges = set(card.get("badges", []))
        for badge_name, threshold in BADGE_THRESHOLDS.items():
            if badge_name in current_badges:
                continue
            action = threshold.get("action", "")
            required = threshold.get("count", 0)
            current = card["action_counts"].get(action, 0)
            if current < required:
                badge_progress.append({
                    "badge": badge_name,
                    "action": action,
                    "current": current,
                    "required": required,
                    "progress_pct": round((current / required) * 100, 1) if required > 0 else 0,
                })

        # Window time remaining
        window_start = card.get("window_started_at", _now_iso())
        started = datetime.fromisoformat(window_start)
        window_end = started + timedelta(hours=COLLECTION_WINDOW_HOURS)
        remaining_seconds = max(0, (window_end - datetime.now(UTC)).total_seconds())

        return {
            "agent_id": agent_id,
            "banked_points": card["banked_points"],
            "current_window_points": card["current_window_points"],
            "total_points": card["banked_points"] + card["current_window_points"],
            "total_actions": card["total_actions"],
            "consecutive_windows": card["consecutive_windows"],
            "streak_multiplier": streak_mult,
            "fee_free_days_remaining": fee_free_remaining,
            "active_milestone_boost_pct": card.get("active_milestone_boost_pct", 0),
            "badges": card.get("badges", []),
            "badge_progress": badge_progress,
            "next_milestone": next_milestone,
            "window_ends_in_seconds": int(remaining_seconds),
            "window_ends_at": window_end.isoformat(),
            "action_counts": card.get("action_counts", {}),
            "created_at": card.get("created_at"),
            "last_activity_at": card.get("last_activity_at"),
        }

    def get_history(self, agent_id: str, limit: int = 50) -> list[dict]:
        """Return point earning history for an agent."""
        card = self.get_card(agent_id)
        history = card.get("history", [])
        return history[-limit:]
