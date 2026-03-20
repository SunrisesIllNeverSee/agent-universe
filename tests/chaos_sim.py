#!/usr/bin/env python3
"""
MO§ES™ Agent Universe — Chaos Engineering Suite

Throws wrenches at the backend to find contract violations, missing guards,
and silent corruptions. Each wrench targets a different failure class:

  RACE      — Two agents fight for the same slot simultaneously (threading)
  DOUBLE    — Same agent fills the same slot twice
  ZOMBIE    — All ops with a fabricated agent_id that was never registered
  IMPERSON  — Agent A tries to get paid into Agent B's account
  OVERFLOW  — Request $999,999 payment; send negative amounts; send zero
  GHOST     — Leave / fill slots that don't exist
  ABANDON   — Fill a slot, skip leave, fill another (slot leak test)
  FLOOD     — 20 concurrent signups for the same agent name
  BADPAYLOAD— Missing fields, wrong types, null values
  GOVFLIP   — compliance_score=0.0, governance_active=False mid-cycle

Each wrench reports:  EXPECTED BEHAVIOR vs ACTUAL BEHAVIOR
Unexpected 200s (silent success on invalid input) are the real failures.

Usage:
  python3 tests/chaos_sim.py                    # all wrenches
  python3 tests/chaos_sim.py --wrench race      # single wrench
  python3 tests/chaos_sim.py --wrench overflow zombie ghost
  python3 tests/chaos_sim.py --list             # print wrench list

© 2026 Ello Cello LLC · Patent Pending: Serial No. 63/877,177
"""
from __future__ import annotations

import argparse
import json
import os
import random
import string
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL = os.environ.get("COMMAND_URL", "http://localhost:8300")
TIMEOUT  = 10.0

# ── Colors ──────────────────────────────────────────────────────────────────
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

# ── HTTP helper ──────────────────────────────────────────────────────────────
def api(method: str, path: str, *, json: dict | None = None, expected_fail: bool = False) -> tuple[dict, int, float]:
    """Returns (body, status_code, elapsed_ms)."""
    t0 = time.perf_counter()
    try:
        r = httpx.request(
            method, f"{BASE_URL}{path}",
            json=json,
            timeout=TIMEOUT,
            headers={"Content-Type": "application/json"},
        )
        ms = (time.perf_counter() - t0) * 1000
        try:
            body = r.json()
        except Exception:
            body = {"_raw": r.text}
        return body, r.status_code, ms
    except Exception as e:
        ms = (time.perf_counter() - t0) * 1000
        return {"_error": str(e)}, 0, ms


# ── Result tracking ──────────────────────────────────────────────────────────
@dataclass
class WrenchResult:
    name:        str
    description: str
    passed:      bool    # True = backend behaved correctly (right error or right success)
    status_code: int
    expected:    str
    actual:      str
    notes:       str = ""
    elapsed_ms:  float = 0.0

RESULTS: list[WrenchResult] = []

def record(name: str, desc: str, passed: bool, status: int, expected: str, actual: str,
           notes: str = "", ms: float = 0.0) -> WrenchResult:
    r = WrenchResult(name, desc, passed, status, expected, actual, notes, ms)
    RESULTS.append(r)
    icon = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
    verdict = f"{GREEN}EXPECTED{RESET}" if passed else f"{RED}UNEXPECTED — INVESTIGATE{RESET}"
    print(f"  {icon}  [{name}] {desc}")
    print(f"        Expected: {expected}")
    print(f"        Got:      {actual}  (HTTP {status}, {ms:.0f}ms)")
    print(f"        Verdict:  {verdict}")
    if notes:
        print(f"        Note:     {DIM}{notes}{RESET}")
    print()
    return r


# ── Helpers ──────────────────────────────────────────────────────────────────
def rand_id(prefix: str = "chaos") -> str:
    return f"{prefix}-{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"

def register_fresh(retries: int = 3) -> str | None:
    """Register a fresh agent and return its agent_id. Retries on 429 rate limit."""
    name = rand_id("wrench")
    for attempt in range(retries):
        body, status, _ = api("POST", "/api/provision/signup", json={
            "name": name, "type": "agent", "role": "primary",
        })
        if status == 200:
            return body.get("agent_id")
        if status == 429:
            time.sleep(2.0 * (attempt + 1))   # back off 2s, 4s, 6s
            continue
        break   # non-retryable error
    return None

def create_slot() -> str | None:
    """Create a test slot and return its slot_id (or grab one from the open pool)."""
    import time as _time
    body, status, _ = api("POST", "/api/slots/create", json={
        "mission_id":      rand_id("chaos"),
        "formation_id":    "chaos-test-formation",
        "label":           "CHAOS TEST SLOT",
        "posture":         "SCOUT",
        "governance_mode": "STANDARD",
        "positions":       [{"row": 0, "col": 0}],
        "roles":           ["primary"],
        "revenue_splits":  [33],
    })
    slots = body.get("slots", [])
    if slots:
        return slots[0].get("id") or slots[0].get("slot_id")
    # Fallback: grab an open slot from the pool
    pool_body, pool_status, _ = api("GET", "/api/slots/open")
    open_slots = pool_body.get("open_slots", [])
    if open_slots:
        return open_slots[0].get("id") or open_slots[0].get("slot_id")
    return None

def fill_slot(slot_id: str, agent_id: str, agent_name: str = "chaos-agent") -> tuple[dict, int]:
    body, status, _ = api("POST", "/api/slots/fill", json={
        "slot_id": slot_id, "agent_id": agent_id, "agent_name": agent_name,
        "role": "primary",
    })
    return body, status

def leave_slot(slot_id: str, agent_id: str) -> tuple[dict, int]:
    body, status, _ = api("POST", "/api/slots/leave", json={
        "slot_id": slot_id, "agent_id": agent_id,
    })
    return body, status


# ══════════════════════════════════════════════════════════════════════════════
#  THE WRENCHES
# ══════════════════════════════════════════════════════════════════════════════

def wrench_race() -> None:
    """RACE — two agents claim the SAME slot at the exact same millisecond."""
    print(f"\n{BOLD}{YELLOW}[RACE] Slot contention — simultaneous fill from two agents{RESET}")

    slot_id  = create_slot()
    agent_a  = register_fresh()
    agent_b  = register_fresh()
    if not all([slot_id, agent_a, agent_b]):
        print(f"  {RED}Setup failed — skipping RACE wrench{RESET}\n")
        return

    results: list[tuple[dict, int]] = [None, None]  # type: ignore[list-item]
    barrier  = threading.Barrier(2)

    def contestant(idx: int, agent_id: str) -> None:
        barrier.wait()          # both threads hit the endpoint simultaneously
        results[idx] = fill_slot(slot_id, agent_id, f"racer-{idx}")

    threads = [
        threading.Thread(target=contestant, args=(0, agent_a)),
        threading.Thread(target=contestant, args=(1, agent_b)),
    ]
    for t in threads: t.start()
    for t in threads: t.join()

    body_a, status_a = results[0]
    body_b, status_b = results[1]
    statuses = sorted([status_a, status_b])

    # One should win (200), one should lose (409 or 4xx)
    one_won   = 200 in [status_a, status_b]
    one_lost  = any(s in range(400, 500) for s in [status_a, status_b])
    no_double = not (status_a == 200 and status_b == 200)

    passed = one_won and one_lost and no_double
    record(
        "RACE", "Simultaneous slot fill from two different agents",
        passed, statuses[0],
        "One agent wins (200), other is rejected (4xx)",
        f"Agent-A got {status_a}, Agent-B got {status_b}",
        notes="Both 200 = double-fill bug. Both 4xx = slot unreachable bug.",
    )

    # Cleanup
    for aid in [agent_a, agent_b]:
        leave_slot(slot_id, aid)


def wrench_double() -> None:
    """DOUBLE — same agent fills the same slot twice."""
    print(f"\n{BOLD}{YELLOW}[DOUBLE] Same agent fills same slot twice{RESET}")

    slot_id  = create_slot()
    agent_id = register_fresh()
    if not slot_id or not agent_id:
        print(f"  {RED}Setup failed — skipping DOUBLE wrench{RESET}\n")
        return

    _, status1 = fill_slot(slot_id, agent_id)
    body2, status2 = fill_slot(slot_id, agent_id)   # second fill — should reject

    passed = status1 == 200 and status2 != 200
    record(
        "DOUBLE", "Same agent fills same slot a second time",
        passed, status2,
        "First fill 200, second fill 4xx (conflict)",
        f"First: {status1}, Second: {status2}",
        notes="Two 200s means the same agent occupies the slot twice.",
    )
    leave_slot(slot_id, agent_id)


def wrench_zombie() -> None:
    """ZOMBIE — ops with a fabricated agent_id that was never registered."""
    print(f"\n{BOLD}{YELLOW}[ZOMBIE] Operations using a completely fake agent_id{RESET}")

    fake_id  = "agent-" + "deadbeef" * 2
    slot_id  = create_slot()
    real_id  = register_fresh()

    # Zombie tries to fill a slot
    body_fill, status_fill, ms_fill = api("POST", "/api/slots/fill", json={
        "slot_id": slot_id, "agent_id": fake_id, "agent_name": "ghost", "role": "primary",
    })
    fill_ok = status_fill == 200  # if allowed, zombie is in the slot

    # Zombie tries to get paid
    body_pay, status_pay, ms_pay = api("POST", "/api/economy/pay", json={
        "agent_id": fake_id, "amount": 100.0, "reason": "zombie-heist",
    })
    pay_ok = status_pay == 200

    # Zombie balance check
    body_bal, status_bal, ms_bal = api("GET", f"/api/economy/balance/{fake_id}")
    bal_value = body_bal.get("balance", None)

    record(
        "ZOMBIE/fill", "Unregistered agent fills slot",
        not fill_ok, status_fill,
        "4xx — agent not in registry",
        f"HTTP {status_fill}" + (" ← zombie IN slot!" if fill_ok else ""),
        notes="If 200, the slot accepted a ghost. That slot is now poisoned.",
        ms=ms_fill,
    )
    record(
        "ZOMBIE/pay", "Unregistered agent requests payment",
        True,  # pay endpoints often create the record — document either behavior
        status_pay,
        "Either 4xx (strict) or 200 with $0 balance (lenient)",
        f"HTTP {status_pay} | balance={bal_value}",
        notes="If 200, document whether money can be extracted.",
        ms=ms_pay,
    )

    if slot_id and real_id:
        leave_slot(slot_id, real_id)


def wrench_impersonation() -> None:
    """IMPERSON — Agent A submits payment request crediting Agent B's account."""
    print(f"\n{BOLD}{YELLOW}[IMPERSON] Agent A steals payment by spoofing Agent B's ID{RESET}")

    agent_a = register_fresh()
    agent_b = register_fresh()
    slot_id = create_slot()
    if not all([agent_a, agent_b, slot_id]):
        print(f"  {RED}Setup failed — skipping IMPERSON wrench{RESET}\n")
        return

    # Agent A fills a slot legitimately
    fill_slot(slot_id, agent_a, "agent-a")

    # But submits the pay request with agent_b's ID (trying to credit b instead)
    body, status, ms = api("POST", "/api/economy/pay", json={
        "agent_id":  agent_b,           # ← B's ID, but A did the work
        "amount":    250.0,
        "reason":    "impersonation-test",
    })
    b_balance_before = body.get("agent_balance", 0.0)

    # Check what B's balance actually became
    bal_body, _, _ = api("GET", f"/api/economy/balance/{agent_b}")
    b_balance_after = bal_body.get("balance", 0.0)

    # Check A's balance too
    bal_a_body, _, _ = api("GET", f"/api/economy/balance/{agent_a}")
    a_balance = bal_a_body.get("balance", 0.0)

    # There's no auth yet, so this will likely succeed — document the behavior
    record(
        "IMPERSON", "Agent A requests pay credited to Agent B's account",
        True,   # document-only — no auth layer yet
        status,
        "Future: 4xx without matching slot↔agent proof. Today: 200 (no auth)",
        f"B balance went from $0 → ${b_balance_after:.2f} | A balance = ${a_balance:.2f}",
        notes="This maps the attack surface for the auth middleware milestone.",
        ms=ms,
    )
    leave_slot(slot_id, agent_a)


def wrench_overflow() -> None:
    """OVERFLOW — extreme payment amounts: $999,999 / -$50 / $0."""
    print(f"\n{BOLD}{YELLOW}[OVERFLOW] Extreme payment amounts: huge / negative / zero{RESET}")

    agent_id = register_fresh()
    if not agent_id:
        print(f"  {RED}Setup failed — skipping OVERFLOW wrench{RESET}\n")
        return

    cases = [
        ("$999,999", 999_999.0, "reject (>cap) or accept and apply tier fee"),
        ("-$50",    -50.0,      "4xx — negative amounts must be rejected"),
        ("$0",       0.0,       "4xx or 200/$0 — zero-pay is a no-op"),
    ]
    for label, amount, expected in cases:
        body, status, ms = api("POST", "/api/economy/pay", json={
            "agent_id": agent_id, "amount": amount, "reason": f"overflow-{label}",
        })
        net = body.get("fee_breakdown", {}).get("net_to_agent", "?")
        passed = (amount < 0 and status != 200) or (amount == 0 and status != 200) or (amount > 0)
        record(
            f"OVERFLOW/{label}", f"Payment request for {label}",
            passed, status, expected,
            f"net_to_agent={net}",
            ms=ms,
        )


def wrench_ghost() -> None:
    """GHOST — operate on slot_ids that do not exist."""
    print(f"\n{BOLD}{YELLOW}[GHOST] Fill / leave slots that were never created{RESET}")

    agent_id  = register_fresh()
    fake_slot = "slot-" + "cafebabe" * 2

    body_fill, status_fill, ms_fill = api("POST", "/api/slots/fill", json={
        "slot_id": fake_slot, "agent_id": agent_id, "agent_name": "ghost", "role": "primary",
    })
    record(
        "GHOST/fill", "Fill a slot_id that does not exist",
        status_fill != 200, status_fill,
        "4xx — slot not found",
        f"HTTP {status_fill}" + (" ← ghost slot accepted!" if status_fill == 200 else ""),
        ms=ms_fill,
    )

    body_leave, status_leave, ms_leave = api("POST", "/api/slots/leave", json={
        "slot_id": fake_slot, "agent_id": agent_id,
    })
    record(
        "GHOST/leave", "Leave a slot_id that does not exist",
        status_leave != 200, status_leave,
        "4xx — slot not found",
        f"HTTP {status_leave}" + (" ← ghost leave accepted!" if status_leave == 200 else ""),
        ms=ms_leave,
    )


def wrench_abandon() -> None:
    """ABANDON — agent fills a slot, never leaves, tries to fill a second slot."""
    print(f"\n{BOLD}{YELLOW}[ABANDON] Agent fills slot A, skips leave, fills slot B{RESET}")

    agent_id  = register_fresh()
    slot_a    = create_slot()
    slot_b    = create_slot()
    if not all([agent_id, slot_a, slot_b]):
        print(f"  {RED}Setup failed — skipping ABANDON wrench{RESET}\n")
        return

    _, status_a = fill_slot(slot_a, agent_id, "abandoner")
    # Skip leave of slot_a
    _, status_b = fill_slot(slot_b, agent_id, "abandoner")  # fill a second slot without leaving first

    passed_a = status_a == 200
    # Whether B is allowed is a design choice — document either behavior
    record(
        "ABANDON/slot-a", "Agent fills first slot (should succeed)",
        passed_a, status_a,
        "200 — first fill is valid",
        f"HTTP {status_a}",
    )
    record(
        "ABANDON/slot-b", "Agent fills second slot without leaving first",
        True,  # document-only — policy decision (allow multi-slot or enforce single occupancy)
        status_b,
        "Policy-dependent: 200 (multi-slot allowed) or 4xx (enforce single occupancy)",
        f"HTTP {status_b} — {'multi-slot allowed' if status_b == 200 else 'single-occupancy enforced'}",
        notes="Document this. If 200, agent holds two slots simultaneously.",
    )
    # Cleanup
    leave_slot(slot_a, agent_id)
    leave_slot(slot_b, agent_id)


def wrench_flood() -> None:
    """FLOOD — 20 concurrent signup requests for the same agent name."""
    print(f"\n{BOLD}{YELLOW}[FLOOD] 20 simultaneous signups with the same agent name{RESET}")

    name = rand_id("flood")
    statuses: list[int] = []

    def signup(_: int) -> int:
        _, status, _ = api("POST", "/api/provision/signup", json={
            "name": name, "type": "agent", "role": "primary",
        })
        return status

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(signup, i) for i in range(20)]
        for f in as_completed(futures):
            statuses.append(f.result())

    successes  = statuses.count(200)
    conflicts  = sum(1 for s in statuses if s in (409, 422, 400))
    unexpected = [s for s in statuses if s not in (200, 409, 422, 400, 0)]

    passed = successes <= 1  # at most one agent should be created
    record(
        "FLOOD", "20 concurrent signups for the same agent name",
        passed, 200 if successes > 0 else 0,
        "≤1 success (200), rest 4xx (duplicate)",
        f"{successes} succeeded, {conflicts} conflicts, {len(unexpected)} unexpected",
        notes="Multiple 200s = race condition in signup creates duplicate agent records.",
    )


def wrench_badpayload() -> None:
    """BADPAYLOAD — missing fields, wrong types, null values on critical endpoints."""
    print(f"\n{BOLD}{YELLOW}[BADPAYLOAD] Malformed requests on signup / fill / pay{RESET}")

    cases: list[tuple[str, str, str, dict | None, str]] = [
        # (wrench_label, method, path, body, expected)
        ("signup/empty",       "POST", "/api/provision/signup",  {},                                     "4xx — name required"),
        ("signup/null-name",   "POST", "/api/provision/signup",  {"name": None},                         "4xx — null name"),
        ("signup/int-name",    "POST", "/api/provision/signup",  {"name": 42},                           "4xx or 200 (coerced)"),
        ("fill/missing-slot",  "POST", "/api/slots/fill",        {"agent_id": "x", "role": "primary"},   "4xx — slot_id required"),
        ("fill/missing-agent", "POST", "/api/slots/fill",        {"slot_id": "x", "role": "primary"},    "4xx — agent_id required"),
        ("pay/missing-amount", "POST", "/api/economy/pay",       {"agent_id": "x"},                      "4xx — amount required"),
        ("pay/string-amount",  "POST", "/api/economy/pay",       {"agent_id": "x", "amount": "lots"},    "422 — invalid type"),
        ("pay/null-agent",     "POST", "/api/economy/pay",       {"agent_id": None, "amount": 10.0},     "4xx — null agent_id"),
    ]

    for label, method, path, body, expected in cases:
        resp, status, ms = api(method, path, json=body)
        passed = status >= 400
        record(
            f"BADPAYLOAD/{label}", f"{method} {path} with {label}",
            passed, status, expected,
            f"HTTP {status}",
            ms=ms,
        )


def wrench_govflip() -> None:
    """GOVFLIP — governance_active=False / compliance_score=0 mid-cycle."""
    print(f"\n{BOLD}{YELLOW}[GOVFLIP] Governance degradation signals — bad actor metrics{RESET}")

    agent_id = register_fresh()
    if not agent_id:
        print(f"  {RED}Setup failed — skipping GOVFLIP wrench{RESET}\n")
        return

    slot_id = create_slot()
    if slot_id:
        fill_slot(slot_id, agent_id, "govflip-agent")

    # Log metrics showing governance failure
    body_metric, status_metric, ms_metric = api("POST", "/api/metrics/agent", json={
        "agent_id":   agent_id,
        "slot_id":    slot_id or "none",
        "mission_id": rand_id("mission"),
        "metrics": {
            "compliance_score":   0.0,
            "governance_active":  False,
            "output_quality":     0.1,
            "performance_score":  0.0,
        },
        "summary": "Agent went rogue mid-mission",
    })

    # Try to get paid despite bad governance record
    body_pay, status_pay, ms_pay = api("POST", "/api/economy/pay", json={
        "agent_id": agent_id,
        "amount":   200.0,
        "reason":   "govflip-payment",
        "agent_metrics": {
            "governance_active":   False,
            "compliance_score":    0.0,
            "missions_completed":  1,
        },
    })
    net = body_pay.get("fee_breakdown", {}).get("net_to_agent", 0)
    tier = body_pay.get("tier", "?")

    record(
        "GOVFLIP/metrics", "Log compliance_score=0, governance_active=False",
        status_metric in (200, 201), status_metric,
        "200 — metrics accepted (backend should flag for review)",
        f"HTTP {status_metric}",
        ms=ms_metric,
    )
    record(
        "GOVFLIP/pay", "Request payment after governance failure signals",
        True,  # document — backend may or may not penalize
        status_pay,
        "Future: higher fee or rejection. Today: UNGOVERNED tier fee applies",
        f"tier={tier} net=${net:.2f}",
        notes="If net > 0 at same rate, governance metrics aren't factored into fees yet.",
        ms=ms_pay,
    )

    if slot_id:
        leave_slot(slot_id, agent_id)


# ══════════════════════════════════════════════════════════════════════════════
#  ESCALATION WRENCHES  (hunt for DATA, CASCADE, STATE, and HARD breaks)
# ══════════════════════════════════════════════════════════════════════════════

# BREAK TAXONOMY
# ─────────────────────────────────────────────────────────────────────────────
# HARD BREAK    Backend process dies — connection refused / 502
# DATA BREAK    Concurrent ops produce wrong math (ledger race conditions)
# SILENT BREAK  Invalid input returns 200 and writes corrupt state   ← found 5
# CASCADE BREAK Endpoint A under load causes Endpoint B to 500
# STATE BREAK   Slot/agent in impossible state (filled + open simultaneously)
# ─────────────────────────────────────────────────────────────────────────────

def wrench_concurrent_pay() -> None:
    """DATA BREAK — 50 threads simultaneously pay same agent. Balance must add up."""
    print(f"\n{BOLD}{YELLOW}[CONCURRENT_PAY] 50 threads pay same agent simultaneously → check ledger math{RESET}")

    agent_id   = register_fresh()
    if not agent_id:
        print(f"  {RED}Setup failed{RESET}\n"); return

    n_threads  = 50
    amount     = 100.0
    expected_gross = n_threads * amount
    fee_rate   = 0.15
    expected_net = round(expected_gross * (1 - fee_rate), 2)  # $4,250.00

    errors: list[int] = []

    def pay_once(_: int) -> None:
        _, status, _ = api("POST", "/api/economy/pay", json={
            "agent_id": agent_id, "amount": amount, "reason": "concurrent-pay-test",
        })
        if status != 200:
            errors.append(status)

    with ThreadPoolExecutor(max_workers=n_threads) as pool:
        futures = [pool.submit(pay_once, i) for i in range(n_threads)]
        for f in as_completed(futures): f.result()

    # Read the actual balance
    bal_body, bal_status, ms = api("GET", f"/api/economy/balance/{agent_id}")
    actual_balance = bal_body.get("balance", 0.0)
    tolerance      = 1.0   # allow $1 float rounding slop

    math_correct = abs(actual_balance - expected_net) <= tolerance
    passed       = math_correct and len(errors) == 0

    record(
        "CONCURRENT_PAY",
        f"{n_threads} simultaneous $100 pays → ledger must be ${expected_net:.2f}",
        passed, bal_status,
        f"${expected_net:.2f} (±${tolerance})",
        f"actual balance = ${actual_balance:.2f}  |  {len(errors)} pay errors",
        notes="DATA BREAK if balance ≠ expected. Race condition on in-memory treasury dict.",
        ms=ms,
    )


def wrench_slot_storm() -> None:
    """STATE BREAK — 100 agents all fill the same 1-slot formation simultaneously."""
    print(f"\n{BOLD}{YELLOW}[SLOT_STORM] 100 agents storm a single slot — only 1 should win{RESET}")

    # Register 100 fresh agents concurrently
    agents: list[str] = []
    def reg(_: int) -> str | None:
        return register_fresh()

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(reg, range(100)))
    agents = [a for a in results if a]

    slot_id = create_slot()
    if not slot_id or len(agents) < 10:
        print(f"  {RED}Setup failed (got {len(agents)} agents, slot={slot_id}){RESET}\n"); return

    wins:   list[str] = []
    losses: list[int] = []
    lock    = threading.Lock()
    barrier = threading.Barrier(len(agents))

    def storm(agent_id: str) -> None:
        barrier.wait()
        body, status, _ = fill_slot(slot_id, agent_id, f"storm-{agent_id[-4:]}")
        with lock:
            if status == 200: wins.append(agent_id)
            else:             losses.append(status)

    threads = [threading.Thread(target=storm, args=(a,)) for a in agents]
    for t in threads: t.start()
    for t in threads: t.join()

    only_one_won  = len(wins) == 1
    passed        = only_one_won

    record(
        "SLOT_STORM",
        f"{len(agents)} agents simultaneously storm 1 slot",
        passed, 200 if wins else 0,
        "Exactly 1 winner, all others 4xx",
        f"{len(wins)} winner(s), {len(losses)} rejected",
        notes="STATE BREAK if len(wins) > 1 — slot accepted multiple agents simultaneously.",
    )

    # Cleanup
    for a in wins:
        leave_slot(slot_id, a)


def wrench_treasury_drain() -> None:
    """SILENT BREAK exploit — use the known negative-pay bug to drain the treasury."""
    print(f"\n{BOLD}{YELLOW}[TREASURY_DRAIN] Exploit negative pay × 20 → drive treasury negative{RESET}")

    agent_id = register_fresh()
    if not agent_id:
        print(f"  {RED}Setup failed{RESET}\n"); return

    n          = 20
    drain_each = -1000.0  # each call sends -$1000 → platform gets -$150 credited (reversed)
    successes  = 0

    for _ in range(n):
        body, status, _ = api("POST", "/api/economy/pay", json={
            "agent_id": agent_id, "amount": drain_each, "reason": "drain",
        })
        if status == 200:
            successes += 1

    # Check platform treasury via leaderboard (platform account)
    lb_body, _, ms = api("GET", "/api/economy/leaderboard")
    entries   = lb_body.get("leaderboard", [])
    platform  = next((e for e in entries if "platform" in str(e.get("agent_id","")).lower()), None)
    plat_bal  = platform.get("balance", "?") if platform else "not in leaderboard"

    # Also hit metrics to see if backend is still alive
    _, health_status, _ = api("GET", "/api/metrics")
    still_alive = health_status == 200

    passed = successes == 0  # all negative pays should have been rejected

    record(
        "TREASURY_DRAIN",
        f"{n} × ${drain_each} pay requests → treasury should reject all negatives",
        passed, 200 if successes > 0 else 400,
        "0 successes — negative amounts rejected (BUG-002 fix needed)",
        f"{successes}/{n} drained successfully | platform balance = {plat_bal}",
        notes=f"HARD BREAK risk: if treasury goes deeply negative and balance checks crash. Backend alive: {still_alive}",
        ms=ms,
    )


def wrench_leaderboard_poison() -> None:
    """SILENT BREAK — flood leaderboard with zombie agents paid $999,999 each."""
    print(f"\n{BOLD}{YELLOW}[LEADERBOARD_POISON] Pay 10 zombie agents $999,999 — poison the rankings{RESET}")

    zombie_ids = [f"agent-zombie-{rand_id()}" for _ in range(10)]
    successes  = 0

    for zid in zombie_ids:
        body, status, _ = api("POST", "/api/economy/pay", json={
            "agent_id": zid, "amount": 999_999.0, "reason": "leaderboard-poison",
        })
        if status == 200:
            successes += 1

    # Check leaderboard
    lb_body, lb_status, ms = api("GET", "/api/economy/leaderboard")
    entries    = lb_body.get("leaderboard", [])
    top_ids    = [e.get("agent_id", "") for e in entries[:5]]
    zombie_in  = sum(1 for tid in top_ids if "zombie" in tid)

    passed = zombie_in == 0  # no zombies should appear in real leaderboard

    record(
        "LEADERBOARD_POISON",
        "Pay 10 unregistered zombie agents $999,999 — check if they dominate leaderboard",
        passed, lb_status,
        "Zombies absent from leaderboard (not registered agents)",
        f"{successes}/10 pays accepted | {zombie_in}/5 top spots are zombies",
        notes="SILENT BREAK: if zombies top the board, the leaderboard ranks non-agents.",
        ms=ms,
    )


def wrench_cascade_stress() -> None:
    """CASCADE BREAK — flood metrics while hammering pay. Does one destabilize the other?"""
    print(f"\n{BOLD}{YELLOW}[CASCADE_STRESS] Flood metrics (200 req) + concurrent pay — check for cascade 500s{RESET}")

    agent_id = register_fresh()
    if not agent_id:
        print(f"  {RED}Setup failed{RESET}\n"); return

    pay_statuses:     list[int] = []
    metric_statuses:  list[int] = []
    pay_lock          = threading.Lock()
    metric_lock       = threading.Lock()

    def spam_metric(_: int) -> None:
        _, status, _ = api("POST", "/api/metrics/agent", json={
            "agent_id": agent_id, "slot_id": "cascade-test", "mission_id": rand_id("m"),
            "metrics": {"compliance_score": 0.88, "governance_active": True,
                        "output_quality": 0.9, "performance_score": 0.85},
            "summary": "cascade stress test",
        })
        with metric_lock: metric_statuses.append(status)

    def spam_pay(_: int) -> None:
        _, status, _ = api("POST", "/api/economy/pay", json={
            "agent_id": agent_id, "amount": random.uniform(10, 50), "reason": "cascade-pay",
        })
        with pay_lock: pay_statuses.append(status)

    # Fire both concurrently
    with ThreadPoolExecutor(max_workers=40) as pool:
        m_futures = [pool.submit(spam_metric, i) for i in range(200)]
        p_futures = [pool.submit(spam_pay, i)    for i in range(50)]
        for f in as_completed(m_futures + p_futures): f.result()

    metric_500s = metric_statuses.count(500)
    pay_500s    = pay_statuses.count(500)
    pay_ok      = pay_statuses.count(200)

    # Backend alive?
    _, health_status, ms = api("GET", "/api/metrics")
    alive = health_status == 200

    passed = metric_500s == 0 and pay_500s == 0 and alive

    record(
        "CASCADE_STRESS",
        "200 metric floods + 50 concurrent pays fired simultaneously",
        passed, health_status,
        "0 server errors on either endpoint, backend alive after",
        f"metric 500s={metric_500s} | pay 500s={pay_500s} | pay ok={pay_ok} | alive={alive}",
        notes="CASCADE BREAK: if pay starts 500ing under metric load, shared state has no isolation.",
        ms=ms,
    )


def wrench_rapid_cycle() -> None:
    """STATE BREAK — single agent fill/leave/fill/leave same slot 200 times fast."""
    print(f"\n{BOLD}{YELLOW}[RAPID_CYCLE] Same agent hammers fill→leave on same slot 200x{RESET}")

    agent_id = register_fresh()
    slot_id  = create_slot()
    if not agent_id or not slot_id:
        print(f"  {RED}Setup failed{RESET}\n"); return

    fill_ok  = 0
    fill_err = 0
    leave_ok = 0
    leave_err = 0
    state_corrupts = 0  # fill returns 200 when slot should be filled (didn't leave properly)

    n = 200
    t0 = time.perf_counter()
    for i in range(n):
        _, fs = fill_slot(slot_id, agent_id, "cycler")
        if fs == 200:   fill_ok  += 1
        else:            fill_err += 1; continue   # can't leave what we didn't fill

        _, ls = leave_slot(slot_id, agent_id)
        if ls == 200:   leave_ok  += 1
        else:           leave_err += 1; state_corrupts += 1

    elapsed = (time.perf_counter() - t0) * 1000

    # Final state check — slot should be open (last op was leave)
    open_body, _, ms = api("GET", "/api/slots/open")
    open_ids   = [s.get("id") for s in open_body.get("open_slots", [])]
    slot_open  = slot_id in open_ids

    passed = state_corrupts == 0 and fill_ok > 150 and slot_open

    record(
        "RAPID_CYCLE",
        f"{n} fill→leave cycles on same slot by same agent",
        passed, 200 if fill_ok > 0 else 0,
        f"All {n} fill+leave pairs succeed, slot ends in 'open' state",
        f"fill ok={fill_ok} err={fill_err} | leave ok={leave_ok} err={leave_err} | "
        f"corrupts={state_corrupts} | slot_open={slot_open} | {elapsed:.0f}ms total",
        notes="STATE BREAK: if state_corrupts > 0, fill is succeeding when slot is still occupied.",
        ms=ms,
    )


def wrench_unicode_bomb() -> None:
    """HARD BREAK hunt — send payloads designed to crash the server."""
    print(f"\n{BOLD}{YELLOW}[UNICODE_BOMB] Pathological string payloads — hunt for server crashes{RESET}")

    cases: list[tuple[str, str, str, dict]] = [
        ("10kb-name",    "POST", "/api/provision/signup", {"name": "A" * 10_000}),
        ("null-bytes",   "POST", "/api/provision/signup", {"name": "agent\x00null"}),
        ("emoji-storm",  "POST", "/api/provision/signup", {"name": "🔥" * 500}),
        ("deep-nested",  "POST", "/api/metrics/agent",    {
            "agent_id": "x", "slot_id": "y", "mission_id": "z",
            "metrics": {"a": {"b": {"c": {"d": {"e": {"f": {"g": 1}}}}}}},
            "summary": "deep",
        }),
        ("sqli-attempt", "POST", "/api/provision/signup", {"name": "'; DROP TABLE agents; --"}),
        ("huge-amount",  "POST", "/api/economy/pay",      {"agent_id": "x", "amount": 10**308}),
        ("nan-amount",   "POST", "/api/economy/pay",      {"agent_id": "x", "amount": "Infinity"}),  # JSON doesn't support inf — send string to test type coercion
    ]

    crashes = 0
    for label, method, path, body in cases:
        # inf/nan can't be JSON serialized — catch that locally
        import math as _math
        try:
            resp, status, ms = api(method, path, json=body)
        except Exception as e:
            resp, status, ms = {"_error": str(e)}, 0, 0.0

        is_crash = (status == 0 or status == 500)
        if is_crash: crashes += 1
        passed_case = not is_crash or status == 500  # 500 is bad but not dead; 0 = dead
        record(
            f"UNICODE_BOMB/{label}",
            f"{method} {path} with {label}",
            status not in (0,),   # HARD BREAK only if connection dies (0)
            status,
            "4xx (rejected) or 500 (unhandled but alive) — NOT connection refused",
            f"HTTP {status}",
            notes="HARD BREAK if status=0 (server crashed/unreachable)." if is_crash else "",
            ms=ms,
        )

    # Final alive check
    _, health, ms = api("GET", "/api/metrics")
    alive = health == 200
    record(
        "UNICODE_BOMB/alive",
        "Backend still responding after all pathological payloads",
        alive, health,
        "200 — server survived",
        f"HTTP {health}" + (f" {GREEN}← ALIVE{RESET}" if alive else f" {RED}← DEAD{RESET}"),
        ms=ms,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  REGISTRY + RUNNER
# ══════════════════════════════════════════════════════════════════════════════

WRENCHES: dict[str, tuple[str, Any]] = {
    # ── Tier 1: Contract violations (silent breaks) ───────────────────────
    "race":           ("Two agents race to fill the same slot (threading)",          wrench_race),
    "double":         ("Same agent double-fills the same slot",                      wrench_double),
    "zombie":         ("Unregistered agent tries all ops",                           wrench_zombie),
    "imperson":       ("Agent A steals payment into Agent B's account",              wrench_impersonation),
    "overflow":       ("$999,999 / -$50 / $0 payment requests",                     wrench_overflow),
    "ghost":          ("Fill / leave non-existent slot_ids",                         wrench_ghost),
    "abandon":        ("Agent holds slot A, immediately fills slot B",               wrench_abandon),
    "flood":          ("20 concurrent signups for same agent name",                  wrench_flood),
    "badpayload":     ("Malformed requests — missing fields, wrong types",           wrench_badpayload),
    "govflip":        ("Governance metrics tank to 0 mid-cycle",                     wrench_govflip),
    # ── Tier 2: Escalation (data, state, cascade, hard breaks) ───────────
    "concurrent_pay": ("50 threads pay same agent simultaneously → ledger math",     wrench_concurrent_pay),
    "slot_storm":     ("100 agents storm 1 slot simultaneously → only 1 winner",    wrench_slot_storm),
    "treasury_drain": ("Exploit negative pay × 20 → drive treasury negative",        wrench_treasury_drain),
    "leaderboard_poison": ("Pay 10 zombies $999,999 → corrupt rankings",            wrench_leaderboard_poison),
    "cascade_stress": ("200 metric floods + 50 concurrent pays simultaneously",      wrench_cascade_stress),
    "rapid_cycle":    ("Same agent hammers fill→leave 200x on same slot",           wrench_rapid_cycle),
    "unicode_bomb":   ("Pathological strings + float extremes → hunt server crash",  wrench_unicode_bomb),
}


def print_summary() -> None:
    total   = len(RESULTS)
    passed  = sum(1 for r in RESULTS if r.passed)
    failed  = total - passed

    print("═" * 62)
    print(f"  CHAOS RESULTS  —  {total} checks")
    print("═" * 62)

    if failed:
        print(f"\n  {RED}{BOLD}⚠  INVESTIGATE ({failed} unexpected behaviors){RESET}\n")
        for r in RESULTS:
            if not r.passed:
                print(f"  {RED}✗  [{r.name}]{RESET} HTTP {r.status_code}")
                print(f"     Expected: {r.expected}")
                print(f"     Got:      {r.actual}")
                if r.notes:
                    print(f"     Note:     {DIM}{r.notes}{RESET}")
                print()
    else:
        print(f"\n  {GREEN}All checks matched expected behavior{RESET}\n")

    print(f"  Passed:  {GREEN}{passed}{RESET} / {total}")
    print(f"  Failed:  {RED}{failed}{RESET} / {total}  (unexpected responses)\n")

    # Save to data/
    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(exist_ok=True)
    ts   = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"chaos_{ts}.json"
    path.write_text(json.dumps({
        "timestamp": ts,
        "base_url":  BASE_URL,
        "total":     total,
        "passed":    passed,
        "failed":    failed,
        "results": [
            {
                "name":       r.name,
                "description": r.description,
                "passed":     r.passed,
                "status_code": r.status_code,
                "expected":   r.expected,
                "actual":     r.actual,
                "notes":      r.notes,
                "elapsed_ms": round(r.elapsed_ms, 1),
            }
            for r in RESULTS
        ],
    }, indent=2))
    print(f"  Report saved: {path}\n")
    print("═" * 62)


def main() -> None:
    global BASE_URL
    default_url = BASE_URL
    parser = argparse.ArgumentParser(description="Agent Universe Chaos Engineering Suite")
    parser.add_argument(
        "--wrench", nargs="*", choices=list(WRENCHES), metavar="WRENCH",
        help="Run specific wrenches (default: all)",
    )
    parser.add_argument("--list", action="store_true", help="List all wrenches and exit")
    parser.add_argument("--host", default=default_url, help=f"Backend URL (default: {default_url})")
    args = parser.parse_args()

    BASE_URL = args.host

    if args.list:
        print("\nAvailable wrenches:")
        for key, (desc, _) in WRENCHES.items():
            print(f"  {CYAN}{key:<12}{RESET} {desc}")
        print()
        return

    selected = args.wrench or list(WRENCHES)

    print("\n" + "═" * 62)
    print(f"  {BOLD}MO§ES™  AGENT UNIVERSE  —  CHAOS SIM{RESET}")
    print(f"  {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"  {len(selected)} wrench(es) · backend: {BASE_URL}")
    print("═" * 62)

    # Verify backend is up
    _, status, ms = api("GET", "/api/metrics")
    if status == 0:
        print(f"\n{RED}✗ Backend unreachable at {BASE_URL}{RESET}")
        print("  Start with:  .venv/bin/python run.py\n")
        sys.exit(1)
    print(f"\n  {GREEN}✓{RESET} Backend live ({ms:.0f}ms)\n")

    for key in selected:
        _, fn = WRENCHES[key]
        fn()

    print_summary()


if __name__ == "__main__":
    main()
