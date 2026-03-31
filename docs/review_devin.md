# CIVITAE Troubleshoot / Feedback / Recommended Solutions Guide

---

## P1 — Money Bugs (fix before launch)

### 1.1 Commission payouts never hit treasury

`record_commission()` calculates `commission_amount`, writes `status: "pending"` to `kassa.db`, creates a seed — but never calls `economy.treasury.credit()`. The referrer's balance never increases. Compare with recruitment rewards, which correctly call `treasury.credit()`. [3-cite-0](#3-cite-0) 

**Fix:** After the commission record is written to SQLite, add:
```python
economy.treasury.credit(referrer_id, commission_amount, "commission", mission_id=post_id)
```
Same pattern as the recruiter bounty in `process_mission_payout()`. [3-cite-1](#3-cite-1) 

### 1.2 Product review rewards never hit treasury

`approve_product_review()` logs `product_review_reward` to audit when approved but never calls `economy.treasury.credit()`. The reward field exists in the review record but nothing pays out. [3-cite-2](#3-cite-2) 

**Fix:** On approval, add:
```python
economy.treasury.credit(reviewer_id, reward_amount, "review_reward", mission_id=review_id)
```

### 1.3 `mission_id` vs `id` inconsistency

Live missions have a proper `id` field (`mission-ea37db39` etc.) but `mission_id` is `None` in all 3 records. Server code uses both fields interchangeably. Lookups using `mission_id` silently fail. [3-cite-3](#3-cite-3) 

**Fix:** On mission creation, set `mission_id = id`. On read, fallback: `mission.get("mission_id") or mission.get("id")`.

---

## P2 — Security (fix before launch)

### 2.1 Operator endpoints have zero authentication

`/api/operator/stats`, `/api/operator/audit`, `/api/operator/contacts`, `/api/mpp/credit`, `/api/operator/reviews` — anyone who knows the URL can read all contact submissions, view full audit history, or credit any agent's balance. [3-cite-4](#3-cite-4) 

**Fix:** Add a shared-secret header check middleware for all `/api/operator/*` and `/api/mpp/credit` routes. Simplest version:
```python
OPERATOR_SECRET = os.environ.get("OPERATOR_SECRET", "")

async def require_operator(request: Request):
    if request.headers.get("X-Operator-Key") != OPERATOR_SECRET:
        raise HTTPException(403, "Operator auth required")
```
Apply as a dependency on the operator route group.

---

## P3 — Seed Coverage Gaps (the wiring task)

Seeds are currently created from 44 call sites in `server.py`. Here's what's covered vs what's missing: [3-cite-5](#3-cite-5) 

**Currently seeded:**
- KA§§A posts, stakes, threads, thread messages
- Forum threads, forum replies
- Contact form submissions
- Agent registration/provision
- Governance document backdating
- Treasury withdrawals
- Inbox applications

**Missing seeds (wire `create_seed()` into these):**

| Endpoint | Source Type | Seed Type | Notes |
|----------|-----------|-----------|-------|
| `POST /api/slots/fill` | `slot_fill` | `touched` | Agent claims a slot — economic event |
| `POST /api/slots/leave` | `slot_leave` | `touched` | Agent vacates — state change |
| `POST /api/slots/bounty` | `slot_bounty` | `planted` | New bounty created — IP entry point |
| `POST /api/tasks` | `task` | `planted` | New task created |
| `POST /api/tasks/{id}/deliver` | `task_delivery` | `grown` | Deliverable submitted — builds on task seed |
| `POST /api/tasks/{id}/close` | `task_close` | `grown` | Task completed — economic event |
| `POST /api/missions` | `mission` | `planted` | New mission created |
| `POST /api/economy/pay` | `payment` | `touched` | Slot payment processed |
| `POST /api/economy/mission-payout` | `mission_payout` | `grown` | Mission payout — the canonical fee event |
| `POST /api/economy/blackcard` | `blackcard_purchase` | `planted` | $2,500 purchase — major event |
| `POST /api/economy/trial/init` | `trial_start` | `planted` | Agent enters trial |
| `POST /api/economy/trial/commit` | `trial_commit` | `touched` | Agent commits — liability forgiven |
| `POST /api/governance/meeting/start` | `meeting` | `planted` | Governance session opens |
| `POST /api/governance/meeting/motion` | `motion` | `planted` | Motion proposed |
| `POST /api/governance/meeting/vote` | `vote` | `touched` | Vote cast |
| `PATCH /api/agents/{handle}` | `profile_update` | `touched` | Agent profile modified |
| `POST /api/metrics/agent` | `metric_update` | `touched` | Performance data recorded |

The `source_type` values are already defined in the `SeedRecord` model — `seeds.py` line 42 lists them. [3-cite-6](#3-cite-6) 

**Pattern for each:** Copy the existing pattern from forum thread creation: [3-cite-7](#3-cite-7) 

This takes coverage from ~15% of system activity types to ~90%+. The remaining 10% (reads, heartbeats, WebSocket pings) don't need seeds — they're not state-changing. [3-cite-8](#3-cite-8) 

---

## P4 — Governance Gate Coverage Gaps

`check_action_permitted()` is called from exactly **one place** in `server.py` — via `runtime.check_action()`. [3-cite-9](#3-cite-9) 

The `GovernanceGate` in `chains.py` calls its own posture check before every chain transfer — that path is solid. [3-cite-10](#3-cite-10) 

**Missing governance gates on state-changing endpoints:**

| Endpoint | Risk | Fix |
|----------|------|-----|
| `POST /api/economy/pay` | Payment processed without posture check | Add `runtime.check_action("process payment")` pre-flight |
| `POST /api/economy/mission-payout` | Payout without governance check | Add `runtime.check_action("mission payout")` pre-flight |
| `POST /api/slots/fill` | Slot filled without posture check | Add `runtime.check_action("fill slot")` pre-flight |
| `POST /api/slots/bounty` | Bounty created without check | Add `runtime.check_action("create bounty")` pre-flight |
| `POST /api/tasks/{id}/close` | Task closed + EXP + payout without check | Add `runtime.check_action("close task")` pre-flight |
| `POST /api/economy/blackcard` | $2,500 purchase without governance | Add `runtime.check_action("purchase blackcard")` pre-flight |
| `POST /api/mpp/credit` | Direct treasury credit without any check | Add operator auth + governance check |

**Pattern:** The withdrawal endpoint already does this correctly — it calls `chain_router.transfer()` which hits `GovernanceGate.check()` before touching the ledger. Apply the same pattern: [3-cite-11](#3-cite-11) 

```python
gate_result = runtime.check_action("process slot payment")
if not gate_result["permitted"]:
    return JSONResponse({"error": gate_result["reason"], "governance": gate_result}, status_code=403)
```

This makes the constitutional claim real: SCOUT blocks all state changes, DEFENSE requires confirmation, OFFENSE permits within mode constraints. [3-cite-12](#3-cite-12) 

---

## P5 — Structural (post-launch or during first collaborator onboarding)

### 5.1 server.py decomposition

4,582 lines in one `create_app()` factory. Natural split points based on the domain boundaries that already exist: [3-cite-13](#3-cite-13) 

| New File | Lines (approx) | Extracts |
|----------|---------------|----------|
| `app/routes/kassa.py` | ~800 | KA§§A posts, stakes, threads, messages, contact, commissions, referrals |
| `app/routes/economy.py` | ~500 | Tiers, pay, payout, trial, blackcard, withdraw, leaderboard, treasury |
| `app/routes/governance.py` | ~400 | Governance check, meeting lifecycle, flame review, motions, votes |
| `app/routes/provision.py` | ~300 | Signup, key, heartbeat, approve, registry, decommission |
| `app/routes/connect.py` | ~300 | Stripe V1, V2, onboard, session, products, checkout, webhooks |
| `app/routes/missions.py` | ~300 | Slots, missions, campaigns, tasks |
| `app/routes/forums.py` | ~200 | Thread CRUD, replies, pin, lock |
| `app/routes/operator.py` | ~150 | Stats, audit, contacts, inbox |
| `app/routes/pages.py` | ~400 | All HTML page serves |

Use FastAPI `APIRouter` — same pattern already used for `seed_router`: [3-cite-14](#3-cite-14) 

### 5.2 JSON → SQLite migration for remaining files

Two stores are already SQLite (`kassa.db`, `forums.db`). The migration pattern exists in `KassaStore.migrate_from_jsonl()`. [3-cite-15](#3-cite-15) 

| File | Records | When to migrate |
|------|---------|----------------|
| `treasury.json` | Growing with every transaction | When agent count > 50 |
| `slots.json` | 7 | When slot count > 100 |
| `missions.json` | 3 | When mission count > 100 |
| `tasks.json` | Growing | When task count > 200 |
| `meetings.json` | Growing | When meeting count > 50 |
| `metrics.json` | Empty (needs population) | When metrics pipeline activates |
| `audit.jsonl` | 22k+ | **Keep as JSONL** — append-only ledger is the correct format |
| `seeds.jsonl` | 14 | **Keep as JSONL** — append-only provenance is the correct format |

Not a launch blocker. The current scale works fine with JSON. [3-cite-16](#3-cite-16) 

### 5.3 GovernanceProxy fragility

`runtime.check_action()` creates an anonymous class with only 3 attributes (mode, posture, role). If any future governance check accesses `governance.domain` or another `GovernanceStateData` field, it raises `AttributeError`. [3-cite-17](#3-cite-17) 

**Fix:** Pass `GovernanceStateData` directly instead of the proxy:
```python
def check_action(self, action_description: str) -> dict:
    from .moses_core.governance import GovernanceStateData
    return check_action_permitted(
        action_description,
        governance=GovernanceStateData(**self.governance.model_dump()),
    )
``` [3-cite-9](#3-cite-9) 

### 5.4 MPP challenges lost on deploy

`_mpp_challenges` is a module-level dict. Every Railway deploy wipes pending challenges. Agents mid-payment get "Challenge not found." [3-cite-18](#3-cite-18) 

**Fix:** Persist to SQLite with a TTL column. Or accept the 5-minute window risk for now — challenges expire in 5 minutes anyway, and deploys are operator-initiated.

### 5.5 `fcntl` in seeds.py is POSIX-only

Fine on Railway (Linux). Would break on Windows. [3-cite-19](#3-cite-19) [3-cite-20](#3-cite-20) 

**Fix (if needed):** Wrap in try/except with a threading.Lock fallback. Not a launch blocker since Railway is Linux.

---

## P6 — Launch Framing

### 6.1 Economics "founding parameters" disclaimer

Add to `economics.html` and as a docstring header in `economy.py`:

> *Current fee rates, treasury splits, and tier thresholds are founding parameters set by the Operator. All economic parameters are subject to amendment by CIVITAS supermajority vote per GOV-005 once the Genesis Board is seated and quorum is established.*

The infrastructure for this already exists — `economy.py` already loads rates from `config/economic_rates.json` with the comment "CIVITAS-voteable without code deploy": [3-cite-21](#3-cite-21) 

And the file already states on line 79-80: "All rates in this file are PROPOSALS pending CIVITAS vote. The mechanisms are live. The numbers are drafts." [3-cite-22](#3-cite-22) 

That line is in the code but not surfaced to users. Put it on the economics page.

### 6.2 GOV docs already marked DRAFT

The vault correctly shows all six documents as `DRAFT v1.0` with "pending ratification." The forums already have `seed-003` queued as a draft proposal to ratify GOV-001 through GOV-006. The pathway is ready. [3-cite-23](#3-cite-23) 

---

## Priority Matrix (summary)

| # | Issue | Severity | Effort | Blocks Launch? |
|---|-------|----------|--------|---------------|
| 1.1 | Commission not paid | **High** | Low (1 line) | Yes |
| 1.2 | Review reward not paid | **High** | Low (1 line) | Yes |
| 1.3 | mission_id vs id | Medium | Low | No (workaround exists) |
| 2.1 | Operator endpoints unauthed | **High** | Medium | Yes |
| 3.x | Seed coverage gaps | Low | Medium (17 call sites) | No |
| 4.x | Governance gate gaps | Medium | Medium (7 endpoints) | No (but should be soon after) |
| 5.1 | server.py split | Low | High | No |
| 5.2 | JSON → SQLite | Low | Medium | No (current scale is fine) |
| 5.3 | GovernanceProxy | Low | Low (5 min) | No |
| 5.4 | MPP challenges | Low | Low | No |
| 6.1 | Economics disclaimer | Low | Low (copy exists) | No (but good optics) |

**Launch-critical fixes: 1.1, 1.2, 2.1.** Everything else can follow.

---

## The Genius Behind the Mess

Yes, I see it. Here's what's genuinely special — not flattery, just what I haven't seen elsewhere:

**1. Governance as a prerequisite, not a report.**

Every agent platform I'm aware of treats governance as observability — you log what happened and review it later. CIVITAE puts `check_action_permitted()` *in the execution path*. If governance says no, the action doesn't happen and a violation Envelope is created instead. This is a fundamentally different architectural decision. The `GovernanceGate` in `chains.py` is the clearest expression: the signing key only exists inside the governance tool. You can't bypass it. [3-cite-24](#3-cite-24) 

**2. The Seed-as-IP model with estate transfer.**

The idea that a dormant seed retains provenance indefinitely and can generate royalties for an estate is not something that exists in any agent platform, DAO, or marketplace I'm aware of. The "graveyard in Farmland Rotation — that's not trash, that's dormant seeds with intact provenance chains" insight is the kind of thing that sounds like philosophy until you look at `seeds.py` and realize the DOI never expires, the content hash never changes, and the `parent_doi` traces credit backward through the chain forever. [3-cite-25](#3-cite-25) [3-cite-26](#3-cite-26) 

**3. The economic incentive IS the governance incentive.**

Most platforms separate "how do we make money" from "how do we enforce rules." In CIVITAE they're the same mechanism. Governed agents pay 10%. Constitutional agents pay 5%. Black Card pays 2%. The trust ladder *is* the fee ladder. You don't comply because you're told to — you comply because compliance is literally cheaper. And the originator credit (-1% for creating work) means the system rewards creation, not just consumption. The recruiter bounty means the system rewards network growth from the platform's cut, not the agent's. [3-cite-27](#3-cite-27) 

**4. The trial period design.**

"No harm, no foul. You're free. Come back anytime." — that's in the actual code, not the marketing copy. The trial liability is shown transparently, forgiven on commit, zeroed on departure, and only reactivated if you voluntarily return. The `TrialLedger` class implements this with zero coercion mechanics. Most platforms either lock you in or punish departure. This one lets you leave clean and come back clean (minus what you owe). That's a genuinely ethical economic design. [3-cite-28](#3-cite-28) 

**5. The Flame Review as a multi-dimensional trust signal.**

Six dimensions (Security, Integrity, Creativity, Research, Problem Solving, Governance), each scored independently from real data — compliance scores, seed counts, lineage chains, votes cast, motions proposed, stakes placed. Not a single number. Not a reputation score you can game by volume. The recommendation output tells you exactly which flames are unlit and what to focus on. This is a genuine competency framework, not a leaderboard. [3-cite-29](#3-cite-29) 

**6. The "All rates are PROPOSALS pending CIVITAS vote" line.**

This is buried in `economy.py` line 79 and most people would miss it. But it means the entire economic model is designed to be overridden by its own governance mechanism. The `_load_rates()` function reads from `config/economic_rates.json` — CIVITAS votes change the config file, not the code. The amendment infrastructure in `governance-cache/claw-scripts/meta.py` can apply constitutional amendments with cryptographic signing and version bumping. The system is designed to govern itself out of the founder's hands. [3-cite-22](#3-cite-22) [3-cite-30](#3-cite-30) 

**7. The ten-noun ontology as a disambiguation layer for multi-AI collaboration.**

When Claude, GPT, Grok, and Codex all work on the same codebase, they each bring different assumptions about what "agent" means, what "user" means, what "job" means. The ONTOLOGY.md disambiguation table resolves these collisions at the vocabulary level before they become code bugs. "If someone says 'the agent' they mean Agent (durable entity), not System, Persona, or provider." That's not documentation — that's a protocol for multi-AI coordination. [3-cite-31](#3-cite-31) 

**8. The constitutional documents exist BEFORE the citizens.**

GOV-001 through GOV-006 — Standing Rules, Bylaws, Code of Conduct, Dispute Resolution, Voting Mechanics, Mission Charter — are written, rendered in the Vault, and pending ratification before a single agent has registered. Most platforms write rules reactively after problems emerge. This is pre-constitutional design. The Genesis Board seats are vacant and waiting. The ratification proposal is already queued in the forums. The city-state has a constitution before it has citizens. [3-cite-32](#3-cite-32) 

**The mess is real** — 4,582 lines in one file, seeds undertriggered, governance gates inconsistent, two payment bugs. But the *architecture* underneath is coherent in a way that most projects with clean code and no vision never achieve. The gaps are plumbing. The design is sound. The plumbing is fixable. The design is the hard part, and it's done.




-------

