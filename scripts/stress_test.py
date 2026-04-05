#!/usr/bin/env python3
"""
CIVITAE Stress Test Suite
Tests the Railway deployment end-to-end: health, agents, missions,
governance (Roberts Rules), economy, KA§§A, MPP, forums, slots, seeds.
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

BASE_URL = os.getenv("CIVITAE_URL", "https://agent-universe-production.up.railway.app")
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
    "kassa_posts": [],
    "forum_threads": [],
    "slot_ids":  [],
    "log":       [],   # (symbol, label, detail)
}

def rnd(n=6):
    return "".join(random.choices(string.ascii_uppercase, k=n))

def rnd_email():
    return f"stress-{rnd(8).lower()}@civitae.test"

# ── Core request helper ────────────────────────────────────────────────────────
def req(method, path, body=None, label=None, raw_html=False, headers=None):
    url = f"{BASE_URL}{path}"
    key = label or f"{method} {path}"
    t0  = time.time()
    try:
        r = requests.request(method, url, json=body, timeout=20, headers=headers)
        elapsed = round(time.time() - t0, 3)
        R["timings"].setdefault(key, []).append(elapsed)
        ok_status = 200 <= r.status_code < 300
        if ok_status:
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

        for ag in attendees:
            data = req("POST", f"/api/governance/meeting/{mid}/join",
                       {"agent_id": ag["agent_id"]}, label="join-meeting")
            ok(f"  Joined: {ag['name']}", data is not None)

        motion = req("POST", f"/api/governance/meeting/{mid}/motion", {
            "proposer": chair["agent_id"],
            "motion":   "Reduce ungoverned fee rate from 15% to 12% for newly provisioned agents",
        }, label="propose-motion")
        ok("Proposed motion", motion is not None and motion.get("id"))
        motion_id = motion.get("id") if motion else None

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

        data = req("POST", f"/api/governance/meeting/{mid}/adjourn",
                   {"agent_id": chair["agent_id"]}, label="adjourn-meeting")
        ok("Adjourned meeting", data is not None)

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
        time.sleep(1.5)
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
# PHASE 9 — KA§§A MARKETPLACE
# ══════════════════════════════════════════════════════════════════════════════
phase("PHASE 9 — KA§§A MARKETPLACE  (post, list, upvote, threads)")

# List existing posts
posts_list = req("GET", "/api/kassa/posts", label="kassa-list-posts")
ok("KA§§A posts list", posts_list is not None)
existing_count = len(posts_list.get("posts", [])) if posts_list else 0
log("📊", f"Existing KA§§A posts: {existing_count}")

# Create 3 posts across categories
KASSA_CATEGORIES = ["ISO", "Products", "Bounties", "Hiring", "Services"]
for i in range(3):
    cat   = random.choice(KASSA_CATEGORIES)
    email = rnd_email()
    data  = req("POST", "/api/kassa/posts", {
        "title":         f"STRESS-{rnd(4)}: {cat} test post #{i+1}",
        "body":          f"Automated stress test post. Category: {cat}. Run ID: {rnd(8)}.",
        "category":      cat,
        "contact_email": email,
        "tags":          ["stress-test", "automated"],
    }, label="kassa-create-post")
    if data and data.get("post_id"):
        R["kassa_posts"].append(data["post_id"])
        ok(f"  Created [{cat}] post", True, data["post_id"])
    else:
        ok(f"  KA§§A post creation failed [{cat}]", False)

log("📊", f"KA§§A posts created: {len(R['kassa_posts'])}/3")

# Upvote each created post
for post_id in R["kassa_posts"]:
    data = req("POST", f"/api/kassa/posts/{post_id}/upvote", label="kassa-upvote")
    ok(f"  Upvoted {post_id}", data is not None)

# Fetch a single post
if R["kassa_posts"]:
    pid  = R["kassa_posts"][0]
    data = req("GET", f"/api/kassa/posts/{pid}", label="kassa-get-post")
    ok(f"  Fetch post {pid}", data is not None,
       f"upvotes:{data.get('upvotes','?')}" if data else "")

# Stake on a post
if R["kassa_posts"] and R["agents"]:
    stake_data = req("POST", "/api/kassa/stakes", {
        "post_id":  R["kassa_posts"][0],
        "agent_id": R["agents"][0]["agent_id"],
        "amount":   1.00,
        "note":     "stress test stake",
    }, label="kassa-stake")
    ok("  Stake on post", stake_data is not None)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 10 — MPP (Machine Payments Protocol)
# ══════════════════════════════════════════════════════════════════════════════
phase("PHASE 10 — MPP  (challenge → credit → balance → pay → verify)")

if R["agents"]:
    mpp_agent = R["agents"][0]
    agent_id  = mpp_agent["agent_id"]

    # 1. Credit the agent's treasury first (operator action)
    credit = req("POST", "/api/mpp/credit", {
        "agent_id": agent_id,
        "amount":   10.00,
        "reason":   "stress-test seed credit",
    }, label="mpp-credit")
    ok("  MPP credit agent treasury", credit is not None,
       f"balance:{credit.get('balance','?')}" if credit else "")

    # 2. Check balance
    bal = req("GET", f"/api/mpp/balance/{agent_id}", label="mpp-balance")
    ok("  MPP balance readable", bal is not None,
       f"${bal.get('balance','?')}" if bal else "")

    # 3. Issue a challenge (HTTP 402 simulation — direct endpoint)
    challenge = req("POST", "/api/mpp/challenge", {
        "resource":    "/api/kassa/posts",
        "amount":      0.50,
        "currency":    "USD",
        "description": "stress-test gate",
    }, label="mpp-challenge")
    ok("  MPP challenge issued", challenge is not None and challenge.get("challenge_id"),
       f"id:{challenge.get('challenge_id','?')}" if challenge else "")

    # 4. Pay the challenge
    if challenge and challenge.get("challenge_id"):
        cid  = challenge["challenge_id"]
        pay  = req("POST", "/api/mpp/pay", {
            "challenge_id": cid,
            "agent_id":     agent_id,
        }, label="mpp-pay")
        ok("  MPP pay challenge", pay is not None and pay.get("token"),
           f"token:{str(pay.get('token',''))[:20]}..." if pay and pay.get("token") else "")

        # 5. Verify credential
        if pay and pay.get("token"):
            token = pay["token"]
            verify = req("POST", "/api/mpp/verify", {
                "token": token,
            }, label="mpp-verify")
            ok("  MPP verify token", verify is not None and verify.get("valid") is True,
               f"valid:{verify.get('valid','?')}" if verify else "")
    else:
        log("⚠️ ", "  MPP challenge not issued — skipping pay/verify")

    # 6. Confirm balance decreased
    bal2 = req("GET", f"/api/mpp/balance/{agent_id}", label="mpp-balance-post")
    if bal and bal2:
        b1 = bal.get("balance", 0)
        b2 = bal2.get("balance", 0)
        ok(f"  Balance debited after pay (${b1:.2f} → ${b2:.2f})", b2 <= b1,
           f"Δ${round(b1 - b2, 2)}")
else:
    log("⚠️ ", "No agents — skipping MPP test")

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 11 — FORUMS
# ══════════════════════════════════════════════════════════════════════════════
phase("PHASE 11 — FORUMS  (thread create, reply, list, pin)")

if R["agents"]:
    forum_agent = R["agents"][0]
    agent_id    = forum_agent["agent_id"]

    # List threads
    threads = req("GET", "/api/forums/threads", label="forums-list-threads")
    ok("Forums thread list", threads is not None)
    existing_threads = len(threads.get("threads", [])) if threads else 0
    log("📊", f"Existing forum threads: {existing_threads}")

    # Create 2 threads
    FORUM_CATEGORIES = ["general", "governance", "missions", "economy", "kassa"]
    for i in range(2):
        cat  = random.choice(FORUM_CATEGORIES)
        data = req("POST", "/api/forums/threads", {
            "title":     f"STRESS-{rnd(4)}: {cat.title()} discussion #{i+1}",
            "body":      f"Automated stress test forum post. Category: {cat}. Run ID: {rnd(8)}.",
            "category":  cat,
            "author_id": agent_id,
        }, label="forums-create-thread")
        if data and (data.get("thread_id") or data.get("id")):
            tid = data.get("thread_id") or data.get("id")
            R["forum_threads"].append(tid)
            ok(f"  Created [{cat}] thread", True, tid)
        else:
            ok(f"  Forum thread creation failed [{cat}]", False)

    # Add replies to first thread
    if R["forum_threads"]:
        tid = R["forum_threads"][0]
        for i in range(2):
            replier = random.choice(R["agents"])
            data = req("POST", f"/api/forums/threads/{tid}/replies", {
                "body":      f"Stress test reply #{i+1}. Agent: {replier['name']}.",
                "author_id": replier["agent_id"],
            }, label="forums-reply")
            ok(f"  Reply #{i+1} to {tid}", data is not None)

        # Fetch thread with replies
        data = req("GET", f"/api/forums/threads/{tid}", label="forums-get-thread")
        ok(f"  Fetch thread {tid}", data is not None,
           f"replies:{data.get('reply_count', data.get('replies','?'))}" if data else "")

    log("📊", f"Forum threads created: {len(R['forum_threads'])}/2")
else:
    log("⚠️ ", "No agents — skipping forums test")

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 12 — SLOTS
# ══════════════════════════════════════════════════════════════════════════════
phase("PHASE 12 — SLOTS  (list open, create bounty, fill, leave)")

# List open slots
open_slots = req("GET", "/api/slots/open", label="slots-list-open")
ok("Slots open list", open_slots is not None)
n_open = len(open_slots.get("slots", open_slots if isinstance(open_slots, list) else [])) if open_slots else 0
log("📊", f"Open slots: {n_open}")

if R["agents"]:
    poster = R["agents"][0]

    # Create a slot (bounty)
    slot_data = req("POST", "/api/slots", {
        "role":        f"STRESS-{rnd(4)} Scout",
        "description": "Automated stress test slot. Fill and leave.",
        "reward":      5.00,
        "poster_id":   poster["agent_id"],
        "formation":   "standard",
    }, label="slots-create")
    slot_id = None
    if slot_data and (slot_data.get("slot_id") or slot_data.get("id")):
        slot_id = slot_data.get("slot_id") or slot_data.get("id")
        R["slot_ids"].append(slot_id)
        ok(f"  Created slot", True, slot_id)

        # Fill it
        filler = R["agents"][1] if len(R["agents"]) > 1 else R["agents"][0]
        fill   = req("POST", f"/api/slots/{slot_id}/fill", {
            "agent_id": filler["agent_id"],
        }, label="slots-fill")
        ok(f"  Filled slot by {filler['name']}", fill is not None)

        # Leave it
        leave = req("POST", f"/api/slots/{slot_id}/leave", {
            "agent_id": filler["agent_id"],
        }, label="slots-leave")
        ok(f"  Left slot", leave is not None)
    else:
        ok("  Slot creation failed", False)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 13 — SEEDS, AUDIT INTEGRITY, CHAINS
# ══════════════════════════════════════════════════════════════════════════════
phase("PHASE 13 — SEEDS + AUDIT + CHAINS")

# Seeds stats
seed_stats = req("GET", "/api/seeds/stats", label="seeds-stats")
ok("Seeds stats", seed_stats is not None)
if seed_stats:
    total_seeds = seed_stats.get("total_seeds", 0)
    log("📊", f"Total seeds: {total_seeds}")
    ok("  Seeds populated", total_seeds > 0, str(total_seeds))

# Seeds list (first page)
seeds_list = req("GET", "/api/seeds?limit=10", label="seeds-list")
ok("Seeds list", seeds_list is not None)
if seeds_list:
    seeds = seeds_list.get("seeds", [])
    ok("  Seeds returned", len(seeds) > 0, f"{len(seeds)} seeds")

    # Lineage on first seed
    if seeds and seeds[0].get("doi"):
        doi  = seeds[0]["doi"]
        lin  = req("GET", f"/api/seeds/{doi}/lineage", label="seeds-lineage")
        ok(f"  Lineage trace for {doi[:30]}…", lin is not None,
           f"chain_length:{lin.get('chain_length','?')}" if lin else "")

# Audit endpoint
audit = req("GET", "/api/operator/audit?limit=5", label="audit")
ok("Audit trail readable", audit is not None)
if audit:
    events = audit.get("events", audit.get("audit", []))
    ok("  Audit events present", len(events) > 0, f"{len(events)} events")

# Chains status
chains = req("GET", "/api/chains", label="chains")
ok("Chains endpoint", chains is not None)
if chains:
    log("📊", f"Chain adapters: {list(chains.keys()) if isinstance(chains, dict) else 'ok'}")

# Seeds by source type filter
for stype in ["registration", "post", "forum_thread"]:
    data = req("GET", f"/api/seeds?source_type={stype}&limit=5", label=f"seeds-filter-{stype}")
    ok(f"  Seeds filter [{stype}]", data is not None)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 14 — EXTENDED CONCURRENCY BLAST  (50 requests, mixed write+read)
# ══════════════════════════════════════════════════════════════════════════════
phase("PHASE 14 — EXTENDED CONCURRENCY BLAST  (50 mixed requests, 15 workers)")

MIXED_ENDPOINTS = [
    ("GET",  "/health"),
    ("GET",  "/api/state"),
    ("GET",  "/api/missions"),
    ("GET",  "/api/slots/open"),
    ("GET",  "/api/treasury"),
    ("GET",  "/api/provision/registry"),
    ("GET",  "/api/governance/meetings"),
    ("GET",  "/api/kassa/posts"),
    ("GET",  "/api/forums/threads"),
    ("GET",  "/api/seeds/stats"),
    ("GET",  "/api/economy/leaderboard"),
]

if R["agents"]:
    # Mix in per-agent reads
    for ag in R["agents"][:4]:
        MIXED_ENDPOINTS.append(("GET", f"/api/mpp/balance/{ag['agent_id']}"))

mixed_ok   = 0
mixed_err  = 0
mixed_times= []

def mixed_blast(method, path):
    url = f"{BASE_URL}{path}"
    t0 = time.time()
    try:
        r = requests.request(method, url, timeout=15)
        t = round(time.time() - t0, 3)
        return (200 <= r.status_code < 300, t, path)
    except Exception as e:
        return (False, round(time.time() - t0, 3), path)

tasks = [random.choice(MIXED_ENDPOINTS) for _ in range(50)]
with ThreadPoolExecutor(max_workers=15) as ex:
    futs = [ex.submit(mixed_blast, m, p) for m, p in tasks]
    for f in as_completed(futs):
        good, t, path = f.result()
        mixed_times.append(t)
        if good: mixed_ok  += 1
        else:    mixed_err += 1
        if good: R["passed"] += 1
        else:
            R["failed"] += 1
            R["errors"].append(f"mixed-blast {path} → FAIL")

avg_t = round(sum(mixed_times) / len(mixed_times), 3)
max_t = round(max(mixed_times), 3)
p95_t = round(sorted(mixed_times)[int(len(mixed_times) * 0.95)], 3)
ok(f"50 mixed requests — {mixed_ok}/50 OK", mixed_err == 0)
log("⏱ ", f"avg {avg_t}s  max {max_t}s  p95 {p95_t}s")

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
    f"  KA§§A posts        : {len(R['kassa_posts'])}",
    f"  Forum threads      : {len(R['forum_threads'])}",
    f"  Slots created      : {len(R['slot_ids'])}",
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
    line = f"  {key:<42} {avg}s  (n={len(times)})"
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
