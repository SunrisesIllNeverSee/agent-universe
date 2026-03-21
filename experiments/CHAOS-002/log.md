# Agent Universe — Chaos Engineering Log

**Experiment ID:** CHAOS-002  
**Name:** Panel Fry Suite  
**Suite:** `tests/chaos_002.py` (747 lines)  
**Run date:** 2026-03-21 · 00:30 UTC  
**Backend:** FastAPI in-memory · port 8300  
**Mode:** `--monitor` (auto-restart between tests)

**Patent:** Serial No. 63/877,177 (Provisional)  
**Owner:** Deric J. McHenry / Ello Cello LLC

---

## 1. Experiment Purpose

CHAOS-001 found contract-level bugs (BUG-001 through BUG-006) — input validation failures at the API boundary. All were patched.

CHAOS-002 escalates to **system thermal limits** — hunting hard stops where the backend dies, not just misbehaves. Seven tests ramp load to the breaking point, with `--monitor` auto-restarting between each.

Mission: find what kills the machine.

---

## 2. Test Results

| # | Test | Outcome | Verdict |
|---|------|---------|---------|
| 1 | OOM_SLOTS | ✅ SURVIVED | 41,600 slots, no heap ceiling hit |
| 2 | OOM_REGISTRY | 🔥 FRIED | 10k concurrent registrations → backend dies |
| 3 | EVENT_STALL | ✅ SURVIVED | p99 < 90ms under 200 concurrent |
| 4 | DICT_RACE | 🔥 DEAD | 500 concurrent fill+leave+read → crash |
| 5 | TX_EXPLOSION | ⏱ PARTIAL | Survived 10k txns, hung on 50k batch |
| 6 | SLOT_EXHAUST | — | Not reached (process killed after TX_EXPLOSION hung) |
| 7 | DEEP_CHAIN | — | Not reached |

**Panel fries: 2 confirmed. 1 partial.**

---

## 3. Test-by-Test Analysis

### OOM_SLOTS — ✅ SURVIVED 41,600 slots

Ramp: 100 → 500 → 1,000 → 5,000 → 10,000 → 25,000 slots per batch.

The slot store is a plain Python list. It grew to 41,600 entries without crashing.
No memory ceiling was hit. Python's garbage collector handled the load.
Creation time scaled linearly: 9ms at 100 → 271ms at 25,000 → 407ms cumulative.

**Finding:** The slot store has no upper bound. In production this is a risk — unbounded lists
accumulate across restarts if state were persisted. For now (in-memory, no persistence),
this is acceptable. A slot expiry protocol (PROP-S08 from committee sim) would address this.

**Severity:** LOW for current deployment. MEDIUM for production persistence.

---

### OOM_REGISTRY — 🔥 FRIED at 38 agents

Ramp: 500 → 2,000 → 5,000 → 10,000 concurrent registration requests.

The backend is capped at 50 agents (from `provision.json`). The first 38 registered before
the cap was hit. At 10,000 concurrent requests, the backend died.

**Root cause:** Not OOM (the registry is tiny). It's **asyncio event loop exhaustion** from
10,000 simultaneous HTTP connections piling up. Each request acquired a slot in the async
handler queue. At 10k, the event loop's internal connection table hit the OS file descriptor
limit, causing the process to crash.

**Key observation:** The registry saw 0 agents on the restarted backend — the in-memory state
is wiped on crash. Any registrations in flight are lost.

**Fix required:**
- Add connection pool limiting at the uvicorn level (`--limit-concurrency N`)
- Or add a registration queue (async.Queue) to serialize bursts
- Persist registry to disk so crashes don't lose state

**Severity:** HIGH. A coordinated bot-flood of registrations kills the backend.

---

### EVENT_STALL — ✅ SURVIVED

200 concurrent requests per endpoint, all 5 core endpoints tested.

| Endpoint | p99 | avg |
|---|---|---|
| GET /api/metrics | 65ms | 32ms |
| GET /api/slots/open | 70ms | 34ms |
| GET /api/economy/leaderboard | 61ms | 29ms |
| POST /api/metrics/agent | 89ms | 38ms |
| POST /api/economy/pay | 54ms | 31ms |

No stall detected. The async event loop handled 200 concurrent requests without degradation.
This is the system's **operational comfort zone** — 200 concurrent is well within normal range.

**Finding:** The backend performs well under realistic load. The 50-89ms p99 range is
acceptable for the current architecture.

**Severity:** NONE. System healthy in this range.

---

### DICT_RACE — 🔥 DEAD

500 rounds of simultaneous slot fill + slot leave + slot read.

The backend died during concurrent mutation. Root cause: Python `dict` operations are not
atomic under asyncio concurrency. When `fill` and `leave` execute concurrently against the
same slot entry, the intermediate state can corrupt the dict.

**Specific failure mode:** `fill` sets `slot["agent_id"] = X` while `leave` sets
`slot["agent_id"] = None`. The async interleaving can produce `None` in a slot that
a third concurrent `read` is mid-iteration on, causing a `KeyError` or `NoneType` crash.

**This is BUG-007** — the most serious finding of CHAOS-002.

**Fix required:**
```python
# In server.py, add a per-slot asyncio lock
import asyncio
SLOT_LOCK = asyncio.Lock()

# Wrap fill and leave handlers:
async with SLOT_LOCK:
    # mutation code here
```

Note: A global slot lock is safe for CPython (GIL + asyncio single-thread), but adds
latency. For production, per-slot locks keyed by slot_id would be faster.

**Severity:** CRITICAL. Real multi-agent traffic will hit this. Any concurrent fill+leave
scenario can crash the backend.

---

### TX_EXPLOSION — ⏱ PARTIAL

Ramp: 1,000 → 5,000 → 10,000 → 50,000 → 100,000 transactions.

- **1,000 txns:** Survived. Leaderboard 6ms, 173 bytes.
- **5,000 txns:** Survived. Leaderboard 6ms, 173 bytes (same — leaderboard appears empty or tiny).
- **10,000 txns:** Survived. Leaderboard 8ms.
- **50,000 txns:** Hung. Process consumed ~936MB RAM and stalled.

**Finding:** The 40,000-request batch (100 concurrent threads × 400 rounds) saturated
the test process itself, not just the backend. The ThreadPoolExecutor with 100 workers
combined with httpx connection overhead consumed ~936MB. The backend was likely dead from
connection exhaustion before the leaderboard check could fire.

**Key observation:** Leaderboard response stayed at 173 bytes across 10k transactions —
this suggests the leaderboard filter (trust-tier gate, BUG-006) was rejecting all agents
since the test agent had no trust tier. The serialization bomb didn't materialize because
the leaderboard payload stayed tiny.

**Fix required:**
- Add `/api/economy/pay` rate limiting (separate from registration rate limits)
- The 50k-transaction stall is a test infrastructure issue as much as a backend issue

**Severity:** MEDIUM. Real-world pay volumes won't hit 50k concurrent, but the test
identified that the backend has no pay-rate protection.

---

### SLOT_EXHAUST, DEEP_CHAIN — Not reached

Process was killed after TX_EXPLOSION hung. These two tests remain unrun.

**SLOT_EXHAUST** would test: fill all open slots simultaneously, then hammer fill/browse/pay
in the empty-pool state. Does the server handle zero open slots gracefully?

**DEEP_CHAIN** would test: 20-step nested chain calls — agent A triggers B triggers C...
measuring latency amplification through governance check chain.

These should be run in a follow-up session.

---

## 4. Critical Findings Summary

### BUG-007 — DICT_RACE slot corruption (CRITICAL)
```
Symptom:   Backend dies under concurrent fill+leave+read on same slot
Root cause: Python dict not atomic under asyncio interleaving  
Fix:        asyncio.Lock() wrapping all slot mutation handlers
Priority:  BEFORE soft launch
```

### BUG-008 — OOM_REGISTRY connection exhaustion (HIGH)
```
Symptom:   Backend dies when >5k concurrent registration requests arrive
Root cause: OS file descriptor limit hit by asyncio connection queue  
Fix:        uvicorn --limit-concurrency or registration queue
Priority:  Before public launch
```

### BUG-009 — TX_EXPLOSION pay rate (MEDIUM)
```
Symptom:   50k concurrent pay requests saturate the backend + test process
Root cause: No rate limiting on /api/economy/pay endpoint
Fix:        Per-agent pay rate limiter (already rate-limited per provision.json? check)
Priority:  Before economic layer goes live
```

---

## 5. What CHAOS-001 vs CHAOS-002 Teaches Us

| Layer | CHAOS-001 | CHAOS-002 |
|---|---|---|
| **Tests** | Contract violations | Thermal limits |
| **Method** | Single requests with bad inputs | Thousands of concurrent valid requests |
| **Found** | Input validation gaps | Concurrency / memory ceiling |
| **Fixes** | BUG-001→006 (all patched) | BUG-007→009 (BUG-007 critical, unpatched) |
| **Verdict** | Contract is solid | Concurrency is the weak surface |

The slot system handles volume (41k slots no problem).
The registry and slot mutation handlers don't handle concurrency.

---

## 6. Next Steps

1. **Patch BUG-007** (DICT_RACE / slot lock) — blocking for soft launch
2. Run SLOT_EXHAUST and DEEP_CHAIN (remaining 2 tests)
3. Run Tier 2 chaos re-runs: `treasury_drain`, `cascade_stress`, `rapid_cycle`
4. Add `/api/economy/pay` rate limiting (BUG-009)
5. Add uvicorn `--limit-concurrency` config (BUG-008)

---

## References

Suite: `tests/chaos_002.py`  
Raw data: `data/chaos002_20260321_003028.json`  
Committee sim results: `data/committee_20260321_002336.json`  
CHAOS-001 log: `experiments/CHAOS-001/log.md`

McHenry, D.J. (2026). A Conservation Law for Commitment in Language Under Transformative  
Compression and Recursive Application. Zenodo. https://doi.org/10.5281/zenodo.18792459

Patent Serial No. 63/877,177 (Provisional). Owner: Deric J. McHenry / Ello Cello LLC.
