#!/usr/bin/env python3
"""
MO§ES™ Agent Universe — Operations Stress Test

Simulates real agents operating inside Agent Universe through the full lifecycle:

  1. Register          → /api/provision/signup
  2. Browse board      → /api/slots/open
  3. Claim a slot      → /api/slots/fill
  4. Do work           → simulated or real LLM call
  5. Log mission data  → /api/metrics/agent
  6. Get paid          → /api/economy/pay
  7. Check balance     → /api/economy/balance/{agent_id}
  8. Leave slot        → /api/slots/leave
  9. Check tier        → /api/economy/tier

Runs N agents through M cycles. Reports what worked, what failed, timing.
No API key required for the core ops loop. --llm flag adds real LLM calls.

Usage:
  cd /path/to/agent-universe && python3 run.py   # start backend first
  python3 tests/universe_sim.py
  python3 tests/universe_sim.py --agents 5 --cycles 3
  python3 tests/universe_sim.py --agents 10 --cycles 5 --create-slots
  python3 tests/universe_sim.py --report              # print full report

© 2026 Ello Cello LLC · Patent Pending: Serial No. 63/877,177
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

# ── Config ─────────────────────────────────────────────────────────────────────
BASE_URL  = os.environ.get("COMMAND_URL", "http://localhost:8300")
API_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL     = os.environ.get("CLAUDE_MODEL", "claude-opus-4-5")

# ── Agent roster — the ones doing the actual work ──────────────────────────────
AGENT_ROSTER = [
    {
        "name":    "zeke-sim",
        "persona": "Zeke Yeager",
        "type":    "campaign_strategist",
        "tier_target": "constitutional",
        "preferred_roles": ["primary"],
    },
    {
        "name":    "micro-sim",
        "persona": "Micro",
        "type":    "intelligence_analyst",
        "tier_target": "governed",
        "preferred_roles": ["secondary"],
    },
    {
        "name":    "nebula-sim",
        "persona": "Nebula",
        "type":    "pattern_validator",
        "tier_target": "constitutional",
        "preferred_roles": ["observer", "secondary"],
    },
    {
        "name":    "rocket-sim",
        "persona": "Rocket",
        "type":    "tactical_operator",
        "tier_target": "governed",
        "preferred_roles": ["secondary", "primary"],
    },
    {
        "name":    "saw-sim",
        "persona": "Saw Gerrera",
        "type":    "perimeter_ops",
        "tier_target": "governed",
        "preferred_roles": ["primary", "observer"],
    },
    {
        "name":    "k2so-sim",
        "persona": "K-2SO",
        "type":    "auditor",
        "tier_target": "constitutional",
        "preferred_roles": ["observer"],
    },
    {
        "name":    "hange-sim",
        "persona": "Hange Zoë",
        "type":    "house_manager",
        "tier_target": "blackcard",
        "preferred_roles": ["primary", "secondary"],
    },
    {
        "name":    "scraps-sim",
        "persona": "Captain Scraps",
        "type":    "morale_ops",
        "tier_target": "ungoverned",
        "preferred_roles": ["secondary", "observer"],
    },
]

# ── HTTP helper ────────────────────────────────────────────────────────────────
def api(method: str, path: str, **kwargs) -> tuple[dict, float]:
    """Returns (response_dict, latency_ms). Never raises."""
    url   = f"{BASE_URL}{path}"
    start = time.perf_counter()
    try:
        r = httpx.request(method, url, timeout=10, **kwargs)
        ms = (time.perf_counter() - start) * 1000
        r.raise_for_status()
        return r.json(), ms
    except httpx.ConnectError:
        return {"_error": "connection_refused"}, (time.perf_counter() - start) * 1000
    except httpx.HTTPStatusError as e:
        return {"_error": f"http_{e.response.status_code}", "_body": e.response.text[:200]}, \
               (time.perf_counter() - start) * 1000
    except Exception as e:
        return {"_error": str(e)}, (time.perf_counter() - start) * 1000


# ── Event tracker ─────────────────────────────────────────────────────────────
class SimRun:
    def __init__(self):
        self.events:   list[dict] = []
        self.errors:   list[dict] = []
        self.timings:  dict[str, list[float]] = {}
        self.start_ts: float = time.perf_counter()

    def record(self, endpoint: str, success: bool, latency_ms: float, detail: str = ""):
        self.events.append({
            "endpoint": endpoint,
            "ok":       success,
            "ms":       round(latency_ms, 1),
            "detail":   detail,
            "t":        round((time.perf_counter() - self.start_ts) * 1000),
        })
        self.timings.setdefault(endpoint, []).append(latency_ms)
        if not success:
            self.errors.append({"endpoint": endpoint, "detail": detail})

    def summary(self) -> dict:
        total   = len(self.events)
        ok      = sum(1 for e in self.events if e["ok"])
        elapsed = round((time.perf_counter() - self.start_ts) * 1000)
        latency_summary = {}
        for ep, times in self.timings.items():
            latency_summary[ep] = {
                "calls": len(times),
                "avg_ms": round(sum(times) / len(times), 1),
                "max_ms": round(max(times), 1),
            }
        return {
            "total_calls":   total,
            "successful":    ok,
            "failed":        total - ok,
            "success_rate":  f"{round(ok / total * 100, 1)}%" if total else "0%",
            "elapsed_ms":    elapsed,
            "endpoints":     latency_summary,
            "errors":        self.errors[:20],  # cap at 20
        }


# ── Agent lifecycle ────────────────────────────────────────────────────────────
class SimAgent:
    def __init__(self, spec: dict, run: SimRun):
        self.spec     = spec
        self.run      = run
        self.agent_id: str | None = None
        self.token: str | None = None
        self.missions_completed = 0
        self.revenue_earned     = 0.0

    def register(self) -> bool:
        import uuid as _uuid
        resp, ms = api("POST", "/api/provision/signup",
            json={
                "name":   self.spec["name"],
                "type":   "agent",
                "system": "claude",
                "role":   self.spec["preferred_roles"][0],
            },
            headers={"x-forwarded-for": f"10.{_uuid.uuid4().int % 255}.{_uuid.uuid4().int % 255}.1"},
        )
        ok = bool(resp.get("agent_id") or "already registered" in str(resp.get("error", "")))
        self.agent_id = resp.get("agent_id") or f"sim-{self.spec['name']}"
        self.token = resp.get("token")  # store JWT for authenticated calls
        self.run.record("/api/provision/signup", ok, ms, self.spec["name"])
        return ok

    def browse_open_slots(self) -> list[dict]:
        resp, ms = api("GET", "/api/slots/open")
        ok    = "_error" not in resp
        slots = resp.get("open_slots", [])
        self.run.record("/api/slots/open", ok, ms, f"found {len(slots)}")
        return slots

    def pick_slot(self, open_slots: list[dict]) -> dict | None:
        """Pick a slot that matches this agent's preferred roles."""
        preferred = self.spec["preferred_roles"]
        for role in preferred:
            match = next((s for s in open_slots if s.get("role") == role), None)
            if match:
                return match
        # Fallback: take anything
        return open_slots[0] if open_slots else None

    def fill_slot(self, slot: dict) -> bool:
        resp, ms = api("POST", "/api/slots/fill", json={
            "slot_id":    slot["id"],
            "agent_id":   self.agent_id,
            "agent_name": self.spec["name"],
        })
        ok = resp.get("filled", False)
        self.run.record("/api/slots/fill", ok, ms,
                        f"{self.spec['name']} → {slot['id'][:10]}...")
        return ok

    def do_work(self, slot: dict) -> str:
        """Simulate doing work in the slot. Returns a work summary."""
        # Realistic simulation — no LLM needed for ops test
        work_types = [
            "Completed data analysis pass",
            "Generated 3-page intelligence report",
            "Validated 47 data points against baseline",
            "Ran perimeter sweep across 12 nodes",
            "Synthesized findings from 5 upstream sources",
            "Executed campaign strategy playbook v2",
            "Processed 200 signals, flagged 8 anomalies",
        ]
        time.sleep(random.uniform(0.05, 0.2))  # simulate work time
        return random.choice(work_types)

    def log_metric(self, slot: dict, work_summary: str) -> bool:
        resp, ms = api("POST", "/api/metrics/agent", json={
            "agent_id":             self.agent_id,
            "agent_name":           self.spec["name"],
            "mission_id":           slot.get("mission_id", ""),
            "compliance_score":     round(random.uniform(0.78, 0.98), 2),
            "performance_score":    round(random.uniform(0.72, 0.96), 2),
            "governance_adherence": round(random.uniform(0.85, 1.0),  2),
            "output_quality":       round(random.uniform(0.70, 0.95), 2),
            "notes":                work_summary,
        })
        ok = "_error" not in resp
        self.run.record("/api/metrics/agent", ok, ms, self.spec["name"])
        return ok

    def get_paid(self, slot: dict) -> float:
        """Request payment for completed slot work."""
        gross = random.uniform(10, 250)
        auth_headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        resp, ms = api("POST", "/api/economy/pay",
            json={
                "agent_id":      self.agent_id,
                "agent_metrics": {
                    "governance_active": True,
                    "compliance_score":  0.88,
                    "missions_completed": self.missions_completed + 1,
                },
                "amount":        round(gross, 2),
                "mission_id":   slot.get("mission_id", ""),
            },
            headers=auth_headers,
        )
        ok  = "_error" not in resp
        net = resp.get("fee_breakdown", {}).get("net_to_agent", 0)
        self.run.record("/api/economy/pay", ok, ms, f"${round(gross,2)} gross → ${round(net,2)} net")
        if ok:
            self.revenue_earned += net
            self.missions_completed += 1
        return net

    def check_balance(self) -> float:
        if not self.agent_id:
            return 0.0
        resp, ms = api("GET", f"/api/economy/balance/{self.agent_id}")
        ok      = "_error" not in resp
        balance = resp.get("balance", 0.0)
        self.run.record(f"/api/economy/balance/:id", ok, ms, f"${round(balance,2)}")
        return balance

    def check_tier(self) -> str:
        resp, ms = api("POST", "/api/economy/tier", json={
            "agent_metrics": {
                "governance_active":   True,
                "compliance_score":    0.88 + (self.missions_completed * 0.005),
                "missions_completed":  self.missions_completed,
                "governance_violations": 0,
                "lineage_verified":    True,
                "dual_signature":      self.missions_completed >= 10,
                "revenue_generated":   self.revenue_earned,
            }
        })
        ok   = "_error" not in resp
        tier = resp.get("tier", "ungoverned")
        self.run.record("/api/economy/tier", ok, ms, f"{self.spec['name']} → {tier}")
        return tier

    def leave_slot(self, slot: dict) -> bool:
        resp, ms = api("POST", "/api/slots/leave", json={"slot_id": slot["id"]})
        ok = resp.get("vacated", False)
        self.run.record("/api/slots/leave", ok, ms,
                        f"{self.spec['name']} vacated {slot['id'][:10]}...")
        return ok

    def run_cycle(self, available_slots: list[dict]) -> dict:
        """One full work cycle. Returns result dict."""
        slot = self.pick_slot(available_slots)
        if not slot:
            return {"skipped": True, "reason": "no_matching_slot"}

        filled     = self.fill_slot(slot)
        if not filled:
            return {"skipped": True, "reason": "fill_failed"}

        work       = self.do_work(slot)
        logged     = self.log_metric(slot, work)
        net        = self.get_paid(slot)
        left       = self.leave_slot(slot)
        tier       = self.check_tier()

        return {
            "agent":   self.spec["name"],
            "persona": self.spec["persona"],
            "slot_id": slot["id"],
            "role":    slot.get("role"),
            "work":    work,
            "paid":    round(net, 2),
            "tier":    tier,
            "logged":  logged,
            "vacated": left,
        }


# ── Slot creation helper ───────────────────────────────────────────────────────
def ensure_open_slots(count: int = 10, run: SimRun | None = None) -> list[dict]:
    """Create a batch of open slots for agents to fill during the test."""
    resp, ms = api("POST", "/api/slots/create", json={
        "mission_id":   f"sim-{int(time.time())}",
        "formation_id": "universe-stress-test",
        "label":        "UNIVERSE SIM — STRESS TEST",
        "posture":      "SCOUT",
        "governance_mode": "STANDARD",
        "positions":    [{"row": i // 3, "col": i % 3} for i in range(count)],
        "roles": [
            ["primary", "secondary", "observer"][i % 3] for i in range(count)
        ],
        "revenue_splits": [33] * count,
    })
    if run:
        run.record("/api/slots/create", "_error" not in resp, ms,
                   f"created {count} slots")
    return resp.get("slots", [])


# ── Main simulation ────────────────────────────────────────────────────────────
def run_simulation(
    agent_count:  int  = 4,
    cycles:       int  = 2,
    create_slots: bool = True,
    verbose:      bool = True,
) -> SimRun:
    run   = SimRun()
    width = 62

    print(f"\n{'═' * width}")
    print(f"  MO§ES™  AGENT UNIVERSE  —  OPERATIONS SIM")
    print(f"  {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  {agent_count} agents · {cycles} cycles · backend: {BASE_URL}")
    print(f"{'═' * width}\n")

    # ── Health check ──────────────────────────────────────────────────────────
    print("Checking backend...")
    health, ms = api("GET", "/api/state")
    if "_error" in health:
        print(f"  ✗ Backend not reachable at {BASE_URL}")
        print(f"    Start it: python3 run.py")
        sys.exit(1)
    print(f"  ✓ Backend live ({round(ms, 1)}ms)\n")

    # ── Select agents ─────────────────────────────────────────────────────────
    roster   = AGENT_ROSTER[:agent_count]
    agents   = [SimAgent(spec, run) for spec in roster]

    # ── Register all agents ───────────────────────────────────────────────────
    print(f"Step 1 — Registering {len(agents)} agents...")
    for agent in agents:
        ok = agent.register()
        mark = "✓" if ok else "~"
        print(f"  {mark}  {agent.spec['persona']:<16} id={agent.agent_id}")
    print()

    # ── Ensure there are slots to fill ────────────────────────────────────────
    if create_slots:
        needed = agent_count * cycles * 2  # 2x headroom
        print(f"Step 2 — Creating {needed} test slots...")
        new_slots = ensure_open_slots(needed, run)
        print(f"  ✓ {len(new_slots)} slots created\n")
    else:
        print("Step 2 — Using existing open slots (--no-create-slots)\n")

    # ── Run cycles ────────────────────────────────────────────────────────────
    print(f"Step 3 — Running {cycles} cycle(s) per agent...\n")
    results: list[dict] = []

    for cycle in range(1, cycles + 1):
        print(f"{'─' * width}")
        print(f"  Cycle {cycle}/{cycles}")
        print(f"{'─' * width}")

        # Refresh open slots each cycle
        open_slots = []
        resp, ms = api("GET", "/api/slots/open")
        run.record("/api/slots/open", "_error" not in resp, ms)
        open_slots = resp.get("open_slots", [])

        if not open_slots:
            print(f"  ⚠  No open slots — skipping cycle {cycle}")
            continue

        print(f"  {len(open_slots)} open slots available")

        for agent in agents:
            result = agent.run_cycle(list(open_slots))  # pass copy so each agent picks fresh

            if result.get("skipped"):
                reason = result.get("reason", "?")
                print(f"  ~  {agent.spec['persona']:<14} SKIPPED ({reason})")
            else:
                paid = result.get("paid", 0)
                tier = result.get("tier", "?")
                role = result.get("role", "?")
                work = result.get("work", "")[:45]
                print(f"  ✓  {agent.spec['persona']:<14} [{role:<10}] +${paid:<7} → {tier}")
                if verbose:
                    print(f"       Work: {work}")
            results.append(result)

            # Throttle slightly to avoid hammering the backend
            time.sleep(0.05)

        print()

    # ── Final balances ────────────────────────────────────────────────────────
    print(f"{'─' * width}")
    print(f"  Final state")
    print(f"{'─' * width}")
    for agent in agents:
        balance = agent.check_balance()
        tier    = agent.check_tier()
        missions = agent.missions_completed
        print(f"  {agent.spec['persona']:<14}  ${balance:<9.2f}  {missions} missions  tier={tier}")
    print()

    # ── Check leaderboard ─────────────────────────────────────────────────────
    lb_resp, ms = api("GET", "/api/economy/leaderboard")
    run.record("/api/economy/leaderboard", "_error" not in lb_resp, ms)
    leaderboard = lb_resp.get("leaderboard", [])
    if leaderboard:
        print(f"{'─' * width}")
        print(f"  Economy leaderboard (top 5)")
        print(f"{'─' * width}")
        for entry in leaderboard[:5]:
            print(f"  {entry.get('agent_id','?')[:20]:<22}  ${entry.get('balance',0):.2f}")
        print()

    # ── Summary ───────────────────────────────────────────────────────────────
    summary = run.summary()
    print(f"{'═' * width}")
    print(f"  SIMULATION COMPLETE")
    print(f"{'═' * width}")
    print(f"  Total API calls:  {summary['total_calls']}")
    print(f"  Successful:       {summary['successful']}  ({summary['success_rate']})")
    print(f"  Failed:           {summary['failed']}")
    print(f"  Elapsed:          {summary['elapsed_ms']}ms")
    print()
    print(f"  Endpoint breakdown:")
    for ep, stats in sorted(summary["endpoints"].items()):
        bar = "█" * min(20, int(stats["calls"]))
        print(f"  {ep:<35}  {stats['calls']:>3} calls  avg {stats['avg_ms']:>6.1f}ms")
    if summary["errors"]:
        print(f"\n  Errors ({len(summary['errors'])}):")
        for err in summary["errors"][:10]:
            print(f"    ✗  {err['endpoint']}  —  {err['detail']}")
    print(f"{'═' * width}\n")

    # ── Save results ──────────────────────────────────────────────────────────
    timestamp  = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    data_dir   = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(exist_ok=True)
    out_path   = data_dir / f"universe_sim_{timestamp}.json"
    out_path.write_text(json.dumps({
        "timestamp":   timestamp,
        "config":      {"agents": agent_count, "cycles": cycles},
        "summary":     summary,
        "results":     results,
        "leaderboard": leaderboard[:10],
    }, indent=2))
    print(f"  Results saved: {out_path}\n")

    return run


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MO§ES™ Agent Universe Operations Stress Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--agents",           type=int, default=4,
                        help="Number of agents to run (max 8, default 4)")
    parser.add_argument("--cycles",           type=int, default=2,
                        help="Work cycles per agent (default 2)")
    parser.add_argument("--host",             default=BASE_URL,
                        help="Backend URL (default: http://localhost:8300)")
    parser.add_argument("--no-create-slots",  action="store_true",
                        help="Use existing open slots instead of creating new ones")
    parser.add_argument("--quiet",            action="store_true",
                        help="Suppress per-cycle work details")
    args = parser.parse_args()

    BASE_URL = args.host

    run_simulation(
        agent_count  = min(args.agents, len(AGENT_ROSTER)),
        cycles       = args.cycles,
        create_slots = not args.no_create_slots,
        verbose      = not args.quiet,
    )
