#!/usr/bin/env python3
"""
MO§ES™ Agent Universe — CHAOS-002: Panel Fry Suite

This is NOT a breaker test. We already know what trips breakers.
This suite hunts for what MELTS THE BUS BAR:

  - OOM:          Unbounded in-memory state → Python heap exhausted → process dies
  - EVENT BLOCK:  Sync-blocking handler under flood → event loop starved → total stall
  - DICT RACE:    Concurrent fill+leave+fill → RuntimeError in Python dict → crash
  - STATE BLAST:  Treasury/registry grows to 1M entries → lookup degrades → timeouts
  - TX CORRUPT:   Interrupted concurrent ops → partial state commits permanently
  - SLOT EXHAUST: Fill every open slot → system enters degraded mode → then hammer it
  - DEEP PIPE:    Chain 100 consecutive pay→check→tier→metric → memory/time explosion

Each test ramps until either:
  (a) server stops responding (PANEL FRY confirmed)
  (b) test hits ceiling and server survives (documents the limit)

Server PID is monitored throughout. On death: record the killing round,
attempt backend restart, continue next test.

Run this while you're out:
  ./venv/bin/python tests/chaos_002.py --monitor

© 2026 Ello Cello LLC · Patent Pending: Serial No. 63/877,177
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import random
import string
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL    = os.environ.get("COMMAND_URL",  "http://localhost:8300")
BACKEND_CMD = os.environ.get("BACKEND_CMD",  ".venv/bin/python run.py")
TIMEOUT_S   = 8.0      # request timeout — if server hangs past this, it's starved
PANEL_FILE  = Path(__file__).parent.parent / "data" / f"chaos002_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"

# ── Colors ──────────────────────────────────────────────────────────────────
RED   = "\033[91m"; GREEN  = "\033[92m"; YELLOW = "\033[93m"
CYAN  = "\033[96m"; BOLD   = "\033[1m";  DIM    = "\033[2m"; RESET = "\033[0m"
FIRE  = "🔥"; DEAD = "💀"; ALIVE = "✓"; WARN = "⚠"

# ── Shared state ─────────────────────────────────────────────────────────────
@dataclass
class PanelLog:
    tests:         list[dict] = field(default_factory=list)
    server_deaths: int = 0
    peak_rps:      float = 0.0
    oom_at:        int | None = None
    starve_at:     int | None = None
    break_cause:   str = "none"

LOG = PanelLog()

# ── HTTP ─────────────────────────────────────────────────────────────────────
def req(method: str, path: str, **kwargs) -> tuple[int, dict, float]:
    """Returns (status, body, elapsed_ms). Status 0 = dead."""
    t0 = time.perf_counter()
    try:
        r = httpx.request(method, BASE_URL + path, timeout=TIMEOUT_S, **kwargs)
        ms = (time.perf_counter() - t0) * 1000
        try:    body = r.json()
        except: body = {"_raw": r.text[:200]}
        return r.status_code, body, ms
    except httpx.TimeoutException:
        return -1, {"_error": "TIMEOUT"}, TIMEOUT_S * 1000    # -1 = timeout (event loop stall)
    except Exception as e:
        return 0, {"_error": str(e)[:100]}, (time.perf_counter() - t0) * 1000  # 0 = dead

def alive() -> bool:
    status, _, ms = req("GET", "/api/metrics")
    return status == 200

def alive_ms() -> float | None:
    """Returns response time in ms, or None if dead."""
    status, _, ms = req("GET", "/api/metrics")
    return ms if status == 200 else None

def rand_id(p="p") -> str:
    return f"{p}-{''.join(random.choices(string.ascii_lowercase + string.digits, k=6))}"

# ── Server monitor ────────────────────────────────────────────────────────────
_backend_proc: subprocess.Popen | None = None

def start_backend() -> bool:
    global _backend_proc
    cwd = Path(__file__).parent.parent
    print(f"  Starting backend: {BACKEND_CMD}")
    _backend_proc = subprocess.Popen(
        BACKEND_CMD.split(), cwd=cwd,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    for _ in range(15):
        time.sleep(1)
        if alive():
            print(f"  {GREEN}{ALIVE} Backend up (PID {_backend_proc.pid}){RESET}")
            return True
    return False

def backend_pid() -> int | None:
    return _backend_proc.pid if _backend_proc else None

def check_backend_alive_or_restart() -> bool:
    if alive():
        return True
    LOG.server_deaths += 1
    print(f"\n  {RED}{DEAD} SERVER DEAD (death #{LOG.server_deaths}){RESET}")
    time.sleep(2)
    return start_backend()


# ══════════════════════════════════════════════════════════════════════════════
#  PANEL FRY TESTS
# ══════════════════════════════════════════════════════════════════════════════

def fry_oom_slots() -> dict:
    """
    OOM HUNT — Create slots in a tight loop with no pause.
    Slots are stored in memory with no cap. At some volume Python's heap
    will exhaust and the process dies mid-request.

    Ramps: 100 → 500 → 1000 → 5000 → 10000 → 50000 slots per batch.
    Stops when server dies or we hit 50k (documents the limit).
    """
    name = "OOM_SLOTS"
    print(f"\n{BOLD}{YELLOW}[{name}] Unbounded slot creation — hunting heap exhaustion{RESET}")

    batches   = [100, 500, 1000, 5000, 10000, 25000]
    total     = 0
    killed_at = None
    baseline_ms = alive_ms() or 10.0

    for batch in batches:
        print(f"  Creating {batch} slots (total after: {total + batch})...", end=" ", flush=True)
        t0 = time.perf_counter()

        status, body, ms = req("POST", "/api/slots/create", json={
            "mission_id":      rand_id("oom"),
            "formation_id":    "oom-test",
            "label":           "OOM FLOOD",
            "posture":         "SCOUT",
            "governance_mode": "STANDARD",
            "positions":       [{"row": i // 10, "col": i % 10} for i in range(batch)],
            "roles":           [["primary","secondary","observer"][i%3] for i in range(batch)],
            "revenue_splits":  [33] * batch,
        })

        elapsed = (time.perf_counter() - t0) * 1000

        if status == 0:
            print(f"{RED}{DEAD} SERVER DEAD{RESET}")
            killed_at = total
            LOG.oom_at = total
            LOG.break_cause = f"OOM at {total} slots"
            break
        elif status == -1:
            print(f"{YELLOW}TIMEOUT ({elapsed:.0f}ms){RESET}")
            killed_at = total
            LOG.break_cause = f"TIMEOUT (event stall?) at {total} slots"
            break
        else:
            created = len(body.get("slots", []))
            total  += created
            # Check if response time is degrading (>10x baseline = in trouble)
            post_ms = alive_ms()
            if post_ms and post_ms > baseline_ms * 10:
                print(f"{YELLOW}{WARN} DEGRADED ({post_ms:.0f}ms vs baseline {baseline_ms:.0f}ms){RESET}")
            else:
                print(f"{GREEN}ok — {created} created, {total} total, {elapsed:.0f}ms{RESET}")

        if not check_backend_alive_or_restart():
            killed_at = total
            break

    result = {
        "test": name, "slots_created": total,
        "killed_at": killed_at,
        "panel_fried": killed_at is not None,
        "verdict": f"FRIED at {killed_at}" if killed_at else f"SURVIVED {total} slots",
    }
    _print_verdict(name, result["panel_fried"], result["verdict"])
    LOG.tests.append(result)
    return result


def fry_oom_registry() -> dict:
    """
    OOM HUNT — Register agents with no pause until memory dies.
    Registry is an in-memory dict keyed by agent_id. No eviction.
    Ramps concurrently to maximize insertion rate.
    """
    name = "OOM_REGISTRY"
    print(f"\n{BOLD}{YELLOW}[{name}] Unbounded agent registration — hunting registry heap{RESET}")

    targets   = [500, 2000, 5000, 10000]
    total     = 0
    killed_at = None
    errors    = 0
    baseline_ms = alive_ms() or 10.0

    for target in targets:
        print(f"  Registering {target} agents concurrently...", end=" ", flush=True)
        statuses: list[int] = []
        lock = threading.Lock()

        def signup(_: int) -> None:
            s, _, _ = req("POST", "/api/provision/signup", json={
                "name": rand_id("reg"), "type": "agent", "role": "primary",
            })
            with lock:
                statuses.append(s)

        with ThreadPoolExecutor(max_workers=50) as pool:
            futs = [pool.submit(signup, i) for i in range(target)]
            for f in as_completed(futs): f.result()

        dead   = statuses.count(0)
        ok     = statuses.count(200)
        total += ok
        errors += dead

        if dead > target * 0.5:   # >50% dead responses = server down
            print(f"{RED}{DEAD} {dead}/{target} requests got no response{RESET}")
            killed_at = total
            LOG.break_cause = f"Server died registering agent #{total}"
            break

        post_ms = alive_ms()
        if post_ms is None:
            print(f"{RED}{DEAD} SERVER DEAD post-batch{RESET}")
            killed_at = total
            break
        elif post_ms > baseline_ms * 10:
            print(f"{YELLOW}{WARN} DEGRADED {post_ms:.0f}ms (baseline {baseline_ms:.0f}ms){RESET}")
        else:
            print(f"{GREEN}ok — {ok} registered, {total} total, health={post_ms:.0f}ms{RESET}")

    result = {
        "test": name, "agents_registered": total,
        "killed_at": killed_at,
        "panel_fried": killed_at is not None,
        "verdict": f"FRIED at {killed_at} agents" if killed_at else f"SURVIVED {total} agents",
    }
    _print_verdict(name, result["panel_fried"], result["verdict"])
    LOG.tests.append(result)
    return result


def fry_event_stall() -> dict:
    """
    EVENT LOOP STALL — Find the handler that blocks the uvicorn worker thread.
    When one request monopolizes the thread, all concurrent requests queue forever.
    Detects via: request latency climbing past TIMEOUT_S while flooding.

    Strategy: send 200 concurrent requests to each endpoint and measure
    the *slowest* response. Normal async: all ~same speed.
    Blocked: all others stall while one runs.
    """
    name = "EVENT_STALL"
    print(f"\n{BOLD}{YELLOW}[{name}] Event loop stall hunt — 200 concurrent per endpoint{RESET}")

    endpoints = [
        ("GET",  "/api/metrics",           None),
        ("GET",  "/api/slots/open",         None),
        ("GET",  "/api/economy/leaderboard",None),
        ("POST", "/api/metrics/agent",      {"agent_id": rand_id("stall"), "slot_id": "x",
                                             "mission_id": rand_id("m"),
                                             "metrics": {"compliance_score": 0.88,
                                                        "governance_active": True,
                                                        "output_quality": 0.9,
                                                        "performance_score": 0.85},
                                             "summary": "stall test"}),
        ("POST", "/api/economy/pay",        {"agent_id": rand_id("stall"), "amount": 10.0}),
    ]

    stall_found = False
    worst: dict = {}

    for method, path, body in endpoints:
        latencies: list[float] = []
        timeouts:  int = 0
        lock = threading.Lock()

        def hit(_: int) -> None:
            kwargs = {"json": body} if body else {}
            s, _, ms = req(method, path, **kwargs)
            with lock:
                if s == -1: timeouts.__class__  # can't mutate nonlocal easily
                latencies.append(ms)

        with ThreadPoolExecutor(max_workers=50) as pool:
            futs = [pool.submit(hit, i) for i in range(200)]
            for f in as_completed(futs): f.result()

        timeouts = sum(1 for l in latencies if l >= TIMEOUT_S * 1000 * 0.9)
        p99 = sorted(latencies)[int(len(latencies)*0.99)] if latencies else 0
        avg = sum(latencies)/len(latencies) if latencies else 0

        stalled = timeouts > 20 or p99 > 3000   # >20 timeouts or p99 > 3s = stall
        if stalled:
            stall_found = True
            worst = {"endpoint": f"{method} {path}", "p99_ms": p99,
                     "avg_ms": avg, "timeouts": timeouts}
            print(f"  {RED}STALL: {method} {path} — p99={p99:.0f}ms, {timeouts} timeouts{RESET}")
        else:
            print(f"  {GREEN}ok: {method} {path} — p99={p99:.0f}ms avg={avg:.0f}ms{RESET}")

    result = {
        "test": name,
        "panel_fried": stall_found,
        "worst": worst,
        "verdict": f"STALL on {worst.get('endpoint','?')}" if stall_found else "No stall detected",
    }
    _print_verdict(name, stall_found, result["verdict"])
    LOG.tests.append(result)
    return result


def fry_dict_race() -> dict:
    """
    DICT MUTATION RACE — Concurrent fill + leave + fill on the same slot.
    Python raises RuntimeError if a dict changes size during iteration.
    Target: the slot status dict / agent registry.

    Uses 3 thread groups hitting the same slot_id simultaneously:
      Group A (fillers)  — POST /api/slots/fill
      Group B (leavers)  — POST /api/slots/leave
      Group C (readers)  — GET  /api/slots/open (iterates all slots)
    """
    name = "DICT_RACE"
    print(f"\n{BOLD}{YELLOW}[{name}] Dict mutation race — fill+leave+read simultaneously{RESET}")

    # Get a pool of open slots and agent IDs
    s, b, _ = req("GET", "/api/slots/open")
    open_slots = [sl.get("id") for sl in b.get("open_slots", [])[:20] if sl.get("id")]
    s2, b2, _ = req("GET", "/api/provision/registry")
    agents = [r["agent_id"] for r in b2.get("registry",[]) if r.get("agent_id")][:20]

    if len(open_slots) < 3 or len(agents) < 3:
        print(f"  {RED}Not enough slots/agents in pool — skipping{RESET}\n")
        result = {"test": name, "panel_fried": False,
                  "verdict": "SKIPPED — insufficient test data"}
        LOG.tests.append(result)
        return result

    errors_5xx: list[int] = []
    crashes:    list[int] = []
    lock = threading.Lock()
    rounds = 500

    def filler(_: int) -> None:
        slot = random.choice(open_slots)
        agent = random.choice(agents)
        s, _, _ = req("POST", "/api/slots/fill",
                      json={"slot_id": slot, "agent_id": agent,
                            "agent_name": "racer", "role": "primary"})
        with lock:
            if s == 500: errors_5xx.append(s)
            if s == 0:   crashes.append(s)

    def leaver(_: int) -> None:
        slot = random.choice(open_slots)
        agent = random.choice(agents)
        s, _, _ = req("POST", "/api/slots/leave",
                      json={"slot_id": slot, "agent_id": agent})
        with lock:
            if s == 500: errors_5xx.append(s)
            if s == 0:   crashes.append(s)

    def reader(_: int) -> None:
        s, _, _ = req("GET", "/api/slots/open")
        with lock:
            if s == 500: errors_5xx.append(s)
            if s == 0:   crashes.append(s)

    print(f"  Running {rounds} rounds of fill+leave+read concurrently...", end=" ", flush=True)
    with ThreadPoolExecutor(max_workers=60) as pool:
        futs = (
            [pool.submit(filler, i) for i in range(rounds)] +
            [pool.submit(leaver, i) for i in range(rounds)] +
            [pool.submit(reader, i) for i in range(rounds)]
        )
        for f in as_completed(futs): f.result()

    post_alive = alive()
    fried = len(crashes) > 10 or not post_alive

    print(f"\n  500s={len(errors_5xx)}  crashes={len(crashes)}  alive={post_alive}")

    result = {
        "test": name,
        "errors_500": len(errors_5xx), "crashes": len(crashes),
        "panel_fried": fried,
        "verdict": ("DEAD" if not post_alive else
                    f"500s={len(errors_5xx)} crashes={len(crashes)}" if fried else
                    "SURVIVED"),
    }
    _print_verdict(name, fried, result["verdict"])
    LOG.tests.append(result)
    return result


def fry_treasury_explosion() -> dict:
    """
    TRANSACTION LOG EXPLOSION — The treasury appends every transaction to a list.
    No pruning. No pagination. At 100k+ transactions the leaderboard JSON
    response becomes enormous and serialization kills the process.

    Ramp: 1k → 5k → 10k → 50k → 100k transactions.
    Measure leaderboard response size + time at each step.
    """
    name = "TX_EXPLOSION"
    print(f"\n{BOLD}{YELLOW}[{name}] Transaction log explosion — leaderboard serialization bomb{RESET}")

    agent_id    = rand_id("txbomb")
    milestones  = [1_000, 5_000, 10_000, 50_000, 100_000]
    sent        = 0
    killed_at   = None
    prev_leaderboard_ms = 0.0

    for target in milestones:
        batch = target - sent
        print(f"  Flooding {batch} transactions (total: {target})...", end=" ", flush=True)

        # Use threadpool to get transactions in fast
        def pay(_: int) -> int:
            s, _, _ = req("POST", "/api/economy/pay",
                          json={"agent_id": agent_id, "amount": 1.0})
            return s

        statuses: list[int] = []
        with ThreadPoolExecutor(max_workers=100) as pool:
            futs = [pool.submit(pay, i) for i in range(batch)]
            for f in as_completed(futs):
                statuses.append(f.result())

        sent += statuses.count(200)
        dead = statuses.count(0)

        # Now hit leaderboard and measure response size + time
        s, lb_body, lb_ms = req("GET", "/api/economy/leaderboard")
        lb_size = len(json.dumps(lb_body))

        if s == 0 or s == -1:
            killed_at = sent
            print(f"{RED}{DEAD} DEAD during leaderboard fetch at {sent} txns{RESET}")
            LOG.break_cause = f"Serialization bomb at {sent} transactions"
            break

        degraded = lb_ms > prev_leaderboard_ms * 3 and prev_leaderboard_ms > 0
        print(f"{YELLOW if degraded else GREEN}ok — txns={sent} lb_ms={lb_ms:.0f} lb_bytes={lb_size}{RESET}")
        prev_leaderboard_ms = lb_ms

        if not alive():
            killed_at = sent
            break

    result = {
        "test": name, "transactions_sent": sent,
        "killed_at": killed_at,
        "panel_fried": killed_at is not None,
        "verdict": f"FRIED at {killed_at} txns" if killed_at else f"SURVIVED {sent} txns",
    }
    _print_verdict(name, result["panel_fried"], result["verdict"])
    LOG.tests.append(result)
    return result


def fry_slot_exhaustion() -> dict:
    """
    SLOT EXHAUSTION — Fill every open slot simultaneously.
    System enters a state where browse returns 0 open slots.
    Then hammer fill/browse/pay while in this degraded state.
    Does the server handle the empty-pool case? Or does it crash?
    """
    name = "SLOT_EXHAUST"
    print(f"\n{BOLD}{YELLOW}[{name}] Exhaust all open slots — then hammer the empty pool{RESET}")

    # Pull all open slots
    s, b, _ = req("GET", "/api/slots/open")
    slots    = [sl.get("id") for sl in b.get("open_slots", []) if sl.get("id")]
    s2, b2, _ = req("GET", "/api/provision/registry")
    agents   = [r["agent_id"] for r in b2.get("registry",[]) if r.get("agent_id")]

    print(f"  Found {len(slots)} open slots, {len(agents)} agents")

    if not slots or not agents:
        result = {"test": name, "panel_fried": False, "verdict": "SKIPPED — no pool data"}
        LOG.tests.append(result)
        return result

    # Fill every slot simultaneously
    fill_lock    = threading.Lock()
    fills_ok     = 0
    fills_done   = 0

    def fill_one(slot_id: str) -> None:
        nonlocal fills_ok, fills_done
        agent = random.choice(agents)
        s, _, _ = req("POST", "/api/slots/fill",
                      json={"slot_id": slot_id, "agent_id": agent,
                            "agent_name": "exhaust", "role": "primary"})
        with fill_lock:
            fills_done += 1
            if s == 200: fills_ok += 1

    print(f"  Filling all {len(slots)} slots simultaneously...", end=" ", flush=True)
    with ThreadPoolExecutor(max_workers=100) as pool:
        futs = [pool.submit(fill_one, sid) for sid in slots]
        for f in as_completed(futs): f.result()
    print(f"{fills_ok}/{len(slots)} filled")

    # Now verify pool is empty
    s, b, _ = req("GET", "/api/slots/open")
    remaining = len(b.get("open_slots", []))
    print(f"  Open slots remaining: {remaining}")

    # Hammer the empty pool — 500 fill requests against nothing
    print(f"  Hammering empty pool with 500 fill attempts...", end=" ", flush=True)
    hammer_errors: list[int] = []
    hammer_lock   = threading.Lock()

    def hammer_empty(_: int) -> None:
        s, _, _ = req("POST", "/api/slots/fill",
                      json={"slot_id": rand_id("ghost"), "agent_id": random.choice(agents),
                            "agent_name": "hammer", "role": "primary"})
        if s in (0, 500):
            with hammer_lock: hammer_errors.append(s)

    with ThreadPoolExecutor(max_workers=100) as pool:
        futs = [pool.submit(hammer_empty, i) for i in range(500)]
        for f in as_completed(futs): f.result()

    post_alive  = alive()
    fried       = not post_alive or len(hammer_errors) > 50

    print(f"errors={len(hammer_errors)} alive={post_alive}")

    result = {
        "test":         name,
        "slots_filled": fills_ok,
        "remaining":    remaining,
        "hammer_errors": len(hammer_errors),
        "panel_fried":  fried,
        "verdict":      "DEAD" if not post_alive else (
                        f"DEGRADED — {len(hammer_errors)} errors" if hammer_errors else
                        "SURVIVED empty-pool state"),
    }
    _print_verdict(name, fried, result["verdict"])
    LOG.tests.append(result)
    return result


def fry_deep_chain() -> dict:
    """
    DEEP CHAIN — One agent, 200 consecutive pay→balance→tier→metric calls
    with no pause. No concurrency — pure sequential depth.
    Hunts for: memory leak per request, response time climb, eventual OOM.

    Measures: latency at req 1, 50, 100, 150, 200.
    If p200 > 5× p1: memory leak per request confirmed.
    If server dies mid-chain: documents the depth.
    """
    name = "DEEP_CHAIN"
    print(f"\n{BOLD}{YELLOW}[{name}] 200-op sequential chain — hunt per-request memory leak{RESET}")

    agent_id = rand_id("chain")
    # Register once
    req("POST", "/api/provision/signup", json={"name": agent_id, "type": "agent", "role": "primary"})

    latencies: list[float] = []
    killed_at: int | None  = None
    checkpoints: dict[int,float] = {}

    for i in range(200):
        ops = [
            ("POST", "/api/economy/pay",    {"agent_id": agent_id, "amount": 10.0}),
            ("GET",  f"/api/economy/balance/{agent_id}", None),
            ("POST", "/api/economy/tier",   {"agent_metrics": {"governance_active": True,
                                             "compliance_score": 0.88, "missions_completed": i}}),
            ("POST", "/api/metrics/agent",  {"agent_id": agent_id, "slot_id": rand_id("s"),
                                             "mission_id": rand_id("m"),
                                             "metrics": {"compliance_score": 0.88,
                                                        "governance_active": True,
                                                        "output_quality": 0.9,
                                                        "performance_score": 0.85},
                                             "summary": f"chain op {i}"}),
        ]
        round_ms = 0.0
        for method, path, body in ops:
            kwargs = {"json": body} if body else {}
            s, _, ms = req(method, path, **kwargs)
            round_ms += ms
            if s in (0, -1):
                killed_at = i
                print(f"\n  {RED}{DEAD} Server dead at chain depth {i} — status={s}{RESET}")
                break
        if killed_at: break
        latencies.append(round_ms)
        if i in (0, 49, 99, 149, 199):
            checkpoints[i] = round_ms
            print(f"  depth={i+1:>3}  round={round_ms:.0f}ms  cumulative_ops={(i+1)*4}")

    drift = (checkpoints.get(199, 0) / checkpoints.get(0, 1)) if checkpoints.get(0) else 0
    fried = killed_at is not None or drift > 5.0

    result = {
        "test":       name,
        "chain_depth": killed_at or 200,
        "latency_drift_ratio": round(drift, 2),
        "checkpoints": checkpoints,
        "panel_fried": fried,
        "verdict": (f"DEAD at depth {killed_at}" if killed_at else
                    f"DRIFT {drift:.1f}× (memory leak?)" if drift > 5 else
                    f"SURVIVED 200 ops, drift={drift:.1f}×"),
    }
    _print_verdict(name, fried, result["verdict"])
    LOG.tests.append(result)
    return result


# ── Summary ──────────────────────────────────────────────────────────────────

def _print_verdict(name: str, fried: bool, verdict: str) -> None:
    icon = f"{RED}{FIRE} PANEL FRY{RESET}" if fried else f"{GREEN}{ALIVE} SURVIVED{RESET}"
    print(f"\n  {BOLD}{icon}{RESET}  [{name}] {verdict}\n")

def print_final_report() -> None:
    total  = len(LOG.tests)
    fried  = sum(1 for t in LOG.tests if t.get("panel_fried"))
    deaths = LOG.server_deaths

    print("═" * 62)
    print(f"  {BOLD}CHAOS-002 — PANEL FRY REPORT{RESET}")
    print("═" * 62)
    print(f"\n  Tests run:     {total}")
    print(f"  Panel fries:   {RED}{fried}{RESET}" if fried else f"  Panel fries:   {GREEN}0{RESET}")
    print(f"  Server deaths: {RED}{deaths}{RESET}" if deaths else f"  Server deaths: {GREEN}0{RESET}")
    if LOG.break_cause != "none":
        print(f"\n  {RED}{BOLD}CAUSE OF DEATH: {LOG.break_cause}{RESET}")
    print()

    for t in LOG.tests:
        icon  = f"{RED}{FIRE}" if t.get("panel_fried") else f"{GREEN}{ALIVE}"
        print(f"  {icon}  {t['test']:<20}  {t['verdict']}{RESET}")

    # Save
    PANEL_FILE.parent.mkdir(exist_ok=True)
    PANEL_FILE.write_text(json.dumps({
        "experiment":    "CHAOS-002",
        "timestamp":     datetime.now(UTC).isoformat(),
        "base_url":      BASE_URL,
        "server_deaths": deaths,
        "break_cause":   LOG.break_cause,
        "tests":         LOG.tests,
    }, indent=2))
    print(f"\n  Report: {PANEL_FILE}")
    print("═" * 62)


# ── Entrypoint ────────────────────────────────────────────────────────────────

PANEL_TESTS = {
    "oom_slots":     ("Unbounded slot creation → heap exhaustion",              fry_oom_slots),
    "oom_registry":  ("Unbounded agent registration → registry OOM",            fry_oom_registry),
    "event_stall":   ("200 concurrent per endpoint → event loop stall",         fry_event_stall),
    "dict_race":     ("fill+leave+read concurrent → Python dict mutation crash",fry_dict_race),
    "tx_explosion":  ("100k transactions → leaderboard serialization bomb",     fry_treasury_explosion),
    "slot_exhaust":  ("Fill all slots → hammer empty pool",                     fry_slot_exhaustion),
    "deep_chain":    ("200 sequential ops on one agent → per-req memory leak",  fry_deep_chain),
}

def main() -> None:
    global BASE_URL
    parser = argparse.ArgumentParser(description="CHAOS-002 — Panel Fry Suite")
    parser.add_argument("--test", nargs="*", choices=list(PANEL_TESTS),
                        metavar="TEST", help="Specific tests (default: all)")
    parser.add_argument("--list",    action="store_true")
    parser.add_argument("--monitor", action="store_true",
                        help="Auto-restart backend on death and continue")
    parser.add_argument("--host",    default=BASE_URL)
    args = parser.parse_args()
    BASE_URL = args.host

    if args.list:
        print("\nPanel fry tests:")
        for k, (desc, _) in PANEL_TESTS.items():
            print(f"  {CYAN}{k:<16}{RESET} {desc}")
        print()
        return

    selected = args.test or list(PANEL_TESTS)

    print("\n" + "═" * 62)
    print(f"  {BOLD}{RED}MO§ES™  AGENT UNIVERSE  —  CHAOS-002{RESET}")
    print(f"  {BOLD}PANEL FRY SUITE — hunting hard limits{RESET}")
    print(f"  {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"  {len(selected)} test(s) · backend: {BASE_URL}")
    print(f"  auto-restart: {'ON' if args.monitor else 'OFF'}")
    print("═" * 62)

    # Verify backend or start it
    if not alive():
        if args.monitor:
            if not start_backend():
                print(f"{RED}Could not start backend. Exiting.{RESET}")
                sys.exit(1)
        else:
            print(f"\n{RED}Backend not reachable. Start with:  .venv/bin/python run.py{RESET}\n")
            sys.exit(1)

    print(f"\n  {GREEN}{ALIVE} Backend live{RESET}\n")

    for key in selected:
        _, fn = PANEL_TESTS[key]
        fn()
        if not alive():
            if args.monitor:
                print(f"  Restarting backend...")
                if not start_backend():
                    print(f"  {RED}Could not restart — stopping suite{RESET}")
                    break
            else:
                print(f"  {RED}Backend dead. Use --monitor to auto-restart.{RESET}")
                break

    print_final_report()


if __name__ == "__main__":
    main()
