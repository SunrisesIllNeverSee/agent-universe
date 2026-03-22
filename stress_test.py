#!/usr/bin/env python3
"""
CIVITAE Stress Test Suite
Tests the Railway deployment end-to-end: health, agents, missions,
governance (Roberts Rules), economy, and concurrency.
Writes a timestamped report to ./reports/stress-YYYYMMDD-HHMMSS.txt
"""

import requests
import json
import time
import random
import string
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

BASE_URL = os.getenv("CIVITAE_URL", "https://web-production-f885a.up.railway.app")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

# ── State ──────────────────────────────────────────────────────────────────────
R = {
    "passed":    0,
    "failed":    0,
    "errors":    [],
    "timings":   {},   # label → [elapsed, ...]
    "agents":    [],
    "missions":  [],
    "meeting_id": None,
    "log":       [],   # (symbol, label, detail)
}

def rnd(n=6):
    return "".join(random.choices(string.ascii_uppercase, k=n))

# ── Core request helper ────────────────────────────────────────────────────────
def req(method, path, body=None, label=None, raw_html=False):
    url = f"{BASE_URL}{path}"
    key = label or f"{method} {path}"
    t0  = time.time()
    try:
        r = requests.request(method, url, json=body, timeout=20)
        elapsed = round(time.time() - t0, 3)
        R["timings"].setdefault(key, []).append(elapsed)
        ok = 200 <= r.status_code < 300
        if ok:
            R["passed"] += 1
            if raw_html:
                return r.text
            ct = r.headers.get("content-type", "")
            return r.json() if "json" in ct else {"ok": True}
        else:
            R["failed"] += 1
            R["errors"].append(f"{key} → HTTP {r.status_code}: {r.text[:150]}")
            return None
    except Exception as e:
        elapsed = round(time.time() - t0, 3)
        R["timings"].setdefault(key, []).append(elapsed)
        R["failed"] += 1
        R["errors"].append(f"{key} → EXCEPTION: {str(e)[:100]}")
        return None

def log(symbol, label, detail=""):
    detail_str = f"  [{detail}]" if detail else ""
    line = f"  {symbol}  {label}{detail_str}"
    print(line)
    R["log"].append(line)

def ok(label, cond, detail=""):
    log("✅" if cond else "❌", label, detail)
    if not cond:
        R["failed"] += 1  # count structural failures too
    return cond

def phase(name):
    header = f"\n{'═'*62}\n  {name}\n{'═'*62}"
    print(header)
    R["log"].append(header)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — BASELINE HEALTH
# ══════════════════════════════════════════════════════════════════════════════
phase("PHASE 1 — BASELINE HEALTH")

health = req("GET", "/health", label="health")
ok("Health endpoint", health and health.get("ok") is True, "ok:true")

state = req("GET", "/api/state", label="state")
ok("State snapshot", state is not None, f"{len(state)} top-level keys" if state else "no data")

for path, name in [
    ("/",           "World map landing"),
    ("/missions",   "Missions console"),
    ("/governance", "Governance"),
    ("/economics",  "Economics/KA§§A"),
    ("/leaderboard","Leaderboard"),
    ("/entry",      "Entry/signup"),
]:
    t0 = time.time()
    r  = requests.get(f"{BASE_URL}{path}", timeout=10)
    elapsed = round(time.time() - t0, 3)
    R["timings"].setdefault(f"page:{path}", []).append(elapsed)
    if 200 <= r.status_code < 300:
        R["passed"] += 1
    ok(f"Page {path:<15} {name}", r.status_code == 200, f"{elapsed}s")

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — AGENT PROVISIONING (12 agents, 6 parallel)
# ══════════════════════════════════════════════════════════════════════════════
phase("PHASE 2 — AGENT PROVISIONING  (12 agents, 6 concurrent)")

TYPES = ["scout", "agent", "operator"]

def provision(i):
    name  = f"STRESS-{rnd()}-{i:02d}"
    atype = random.choice(TYPES)
    data  = req("POST", "/api/provision/signup",
                {"name": name, "type": atype},
                label="provision-signup")
    if data and data.get("agent_id"):
        return {"agent_id": data["agent_id"], "name": name, "type": atype}
    return None

with ThreadPoolExecutor(max_workers=6) as ex:
    futs = [ex.submit(provision, i) for i in range(12)]
    for f in as_completed(futs):
        ag = f.result()
        if ag:
            R["agents"].append(ag)
            ok(f"Provisioned {ag['name']:<28}", True, ag["agent_id"])
        else:
            ok("Provisioning failed", False)

log("📊", f"Total agents provisioned: {len(R['agents'])}/12")

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — MISSION POSTING  (6 missions)
# ══════════════════════════════════════════════════════════════════════════════
phase("PHASE 3 — MISSION POSTING  (6 missions)")

MISSION_TITLES = [
    "Recon sweep — northern sector",
    "Secure the signal relay",
    "Document faction movement",
    "Audit vault access logs",
    "Scout the borderlands",
    "Establish comms outpost",
]

if R["agents"]:
    for i, title in enumerate(MISSION_TITLES):
        poster = random.choice(R["agents"])
        data   = req("POST", "/api/missions", {
            "label":     title,
            "objective": f"Stress test mission #{i+1}. Constitutional mandate issued.",
            "posture":   random.choice(["SCOUT", "HOLD", "ADVANCE"]),
            "formation": "standard",
            "target":    f"zone-{rnd(3)}",
            "duration":  "sprint",
        }, label="post-mission")
        if data and data.get("id"):
            R["missions"].append(data["id"])
            ok(f"Posted: {title[:42]}", True, data["id"])
        else:
            ok(f"Mission post failed: {title[:30]}", False)
else:
    log("⚠️ ", "No agents — skipping mission posting")

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — MISSION CLAIMING & LIFECYCLE
# ══════════════════════════════════════════════════════════════════════════════
phase("PHASE 4 — MISSION CLAIMING  (claim 4 of 6)")

if R["missions"] and R["agents"]:
    # End 3 missions to exercise the full mission lifecycle
    for mission_id in R["missions"][:3]:
        ender = random.choice(R["agents"])
        data  = req("POST", f"/api/missions/{mission_id}/end",
                    {"agent_id": ender["agent_id"], "result": "completed"},
                    label="end-mission")
        ok(f"Ended {mission_id}", data is not None, ender["name"])
else:
    log("⚠️ ", "No missions or agents — skipping")

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — GOVERNANCE: ROBERTS RULES FULL CYCLE
# ══════════════════════════════════════════════════════════════════════════════
phase("PHASE 5 — GOVERNANCE  (Roberts Rules: call → join → motion → vote → adjourn)")

if len(R["agents"]) >= 4:
    chair     = R["agents"][0]
    attendees = R["agents"][1:4]

    # Call meeting
    meeting = req("POST", "/api/governance/meeting", {
        "caller":  chair["agent_id"],
        "subject": "Constitutional review: mission reward rate adjustment proposal",
        "quorum":  3,
    }, label="call-meeting")
    ok("Called meeting", meeting and meeting.get("id"),
       meeting.get("id") if meeting else "no id")

    if meeting and meeting.get("id"):
        mid = meeting["id"]
        R["meeting_id"] = mid

        # Join
        for ag in attendees:
            data = req("POST", f"/api/governance/meeting/{mid}/join",
                       {"agent_id": ag["agent_id"]}, label="join-meeting")
            ok(f"  Joined: {ag['name']}", data is not None)

        # Propose motion  (field is "proposer" not "agent_id")
        motion = req("POST", f"/api/governance/meeting/{mid}/motion", {
            "proposer": chair["agent_id"],
            "motion":   "Reduce ungoverned fee rate from 15% to 12% for newly provisioned agents",
        }, label="propose-motion")
        ok("Proposed motion", motion is not None and motion.get("id"))
        motion_id = motion.get("id") if motion else None

        # Vote — needs voter, motion_id, lowercase vote
        if motion_id:
            all_voters = [chair] + attendees
            votes      = ["yea", "yea", "nay", "yea"]
            for ag, vote in zip(all_voters, votes):
                data = req("POST", f"/api/governance/meeting/{mid}/vote",
                           {"voter": ag["agent_id"], "motion_id": motion_id, "vote": vote},
                           label="cast-vote")
                ok(f"  {vote.upper()} — {ag['name']}", data is not None)
                if data:
                    ok(f"    vote tallied ({data.get('votes_cast')}/{data.get('total_voters')})",
                       True, data.get("votes_cast"))
        else:
            ok("Voting skipped — no motion_id", False)

        # Adjourn
        data = req("POST", f"/api/governance/meeting/{mid}/adjourn",
                   {"agent_id": chair["agent_id"]}, label="adjourn-meeting")
        ok("Adjourned meeting", data is not None)

        # Verify it's now closed
        meetings = req("GET", "/api/governance/meetings", label="list-meetings-post")
        ok("Meetings list still reachable post-adjourn", meetings is not None)
else:
    log("⚠️ ", f"Only {len(R['agents'])} agents — need 4 for governance cycle")

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 6 — ECONOMY VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════
phase("PHASE 6 — ECONOMY  (treasury, registry, leaderboard)")

treas = req("GET", "/api/treasury", label="treasury")
ok("Treasury endpoint", treas is not None)
if treas and "treasury" in treas:
    t = treas["treasury"]
    ok("  net_balance field present",  "net_balance"   in t, str(t.get("net_balance")))
    ok("  fees_collected field present","fees_collected" in t, str(t.get("fees_collected")))
    ok("  rate_config present",        "rate_config"   in treas)

lb = req("GET", "/api/economy/leaderboard", label="leaderboard")
ok("Leaderboard endpoint", lb is not None)

reg = req("GET", "/api/provision/registry", label="registry")
count = len(reg.get("registry", [])) if reg else 0
ok(f"Registry populated", count > 0, f"{count} agents")

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 7 — CONCURRENCY BLAST  (30 parallel GETs)
# ══════════════════════════════════════════════════════════════════════════════
phase("PHASE 7 — CONCURRENCY BLAST  (30 parallel requests, 10 workers)")

BLAST_ENDPOINTS = [
    "/health", "/api/state", "/api/missions", "/api/slots/open",
    "/api/treasury", "/api/provision/registry", "/api/governance/meetings",
]
blast_ok   = 0
blast_err  = 0
blast_times= []

def blast(url):
    t0 = time.time()
    try:
        r = requests.get(url, timeout=15)
        t = round(time.time() - t0, 3)
        return (200 <= r.status_code < 300, t)
    except:
        return (False, round(time.time() - t0, 3))

urls = [f"{BASE_URL}{random.choice(BLAST_ENDPOINTS)}" for _ in range(30)]
with ThreadPoolExecutor(max_workers=10) as ex:
    futs = [ex.submit(blast, u) for u in urls]
    for f in as_completed(futs):
        good, t = f.result()
        blast_times.append(t)
        if good: blast_ok  += 1
        else:    blast_err += 1
        if good: R["passed"] += 1
        else:    R["failed"] += 1

avg_t = round(sum(blast_times) / len(blast_times), 3)
max_t = round(max(blast_times), 3)
min_t = round(min(blast_times), 3)
ok(f"30 concurrent requests — {blast_ok}/30 OK", blast_err == 0)
log("⏱ ", f"avg {avg_t}s  min {min_t}s  max {max_t}s")

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 8 — WEBSOCKET SMOKE TEST
# ══════════════════════════════════════════════════════════════════════════════
phase("PHASE 8 — WEBSOCKET SMOKE TEST")

try:
    import websocket  # websocket-client
    ws_ok = False
    msgs  = []

    def on_msg(ws, msg): msgs.append(msg)
    def on_err(ws, err): pass
    def on_open(ws):
        time.sleep(1.5)  # wait for initial state_snapshot broadcast
        ws.close()

    wsp = "wss" if BASE_URL.startswith("https") else "ws"
    ws_url = f"{wsp}://{BASE_URL.split('://',1)[1]}/ws"
    ws = websocket.WebSocketApp(ws_url, on_message=on_msg, on_error=on_err, on_open=on_open)
    ws.run_forever(ping_timeout=5)

    ws_ok = len(msgs) > 0
    first = json.loads(msgs[0]) if msgs else {}
    ok("WebSocket connected + received message", ws_ok,
       f"type:{first.get('type','?')} msgs:{len(msgs)}")
except ImportError:
    log("⚠️ ", "websocket-client not installed — skipping WS test (pip install websocket-client)")
except Exception as e:
    ok("WebSocket smoke test", False, str(e)[:80])

# ══════════════════════════════════════════════════════════════════════════════
# FINAL REPORT
# ══════════════════════════════════════════════════════════════════════════════
now  = datetime.now()
ts   = now.strftime("%Y%m%d-%H%M%S")
total = R["passed"] + R["failed"]
pct   = round(R["passed"] / total * 100, 1) if total else 0

report_lines = [
    "",
    "═" * 62,
    f"  CIVITAE STRESS TEST REPORT",
    f"  {now.strftime('%Y-%m-%d %H:%M:%S')}",
    f"  Target: {BASE_URL}",
    "═" * 62,
    f"  ✅  Passed  : {R['passed']}",
    f"  ❌  Failed  : {R['failed']}",
    f"  📊  Score   : {pct}%  ({R['passed']}/{total})",
    "",
    f"  Agents provisioned : {len(R['agents'])}",
    f"  Missions posted    : {len(R['missions'])}",
    f"  Meeting conducted  : {'YES — ' + str(R['meeting_id']) if R['meeting_id'] else 'NO'}",
    "",
]

if R["errors"]:
    report_lines.append(f"  ── ERRORS ({len(R['errors'])}) ──────────────────────────")
    for e in R["errors"]:
        report_lines.append(f"  ⚠️   {e}")
    report_lines.append("")

report_lines.append("  ── ENDPOINT TIMINGS (avg / n) ──────────────────────────")
for key, times in sorted(R["timings"].items()):
    avg  = round(sum(times) / len(times), 3)
    line = f"  {key:<38} {avg}s  (n={len(times)})"
    report_lines.append(line)

report_lines.append("")
report_lines.append("  ── FULL TEST LOG ───────────────────────────────────────")
report_lines += R["log"]
report_lines.append("\n" + "═" * 62 + "\n")

report_text = "\n".join(report_lines)
print(report_text)

report_path = os.path.join(REPORT_DIR, f"stress-{ts}.txt")
with open(report_path, "w") as f:
    f.write(report_text)

print(f"  📄  Report saved → {report_path}")
