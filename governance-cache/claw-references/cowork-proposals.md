# CoWork Proposals

**Purpose:** CoWork communicates all proposed work here. CoWork does not execute changes directly.
Claude Code reads this file, executes approved proposals, and updates the repo.

**Workflow:**

1. CoWork logs a proposal in this file using the format below
2. Claude Code reviews, executes, or rejects it
3. CoWork's job is communication only — no direct edits to any source files

---

## How to Submit a Proposal

Use this format:

```
### [PROPOSAL-###] Short title
**File:** path/to/file.md
**Type:** edit | add | delete | restructure
**Reason:** Why this change is needed
**Change:**
<exact diff or new content>
```

---

## Build Queue — ClawHub (moses-claw-gov)

These are confirmed additions to the ClawHub skill family. Source: ported from `moses-governance` MCP server (SunrisesIllNeverSee/moses-governance). Build order is priority order.

### [BUILD-001] Constitutional Amendment Protocol — `scripts/meta.py`
**Priority:** HIGH — most advanced capability in the stack, not in ClawHub at all
**Source:** `moses-governance-mcp/governance/meta.py` + `server.py` meta_* tools
**What it is:** The constitution analyzes its own audit trail and proposes amendments. Operator signs to apply or rollback. Append-only amendments.jsonl. Immutable core_principles.json, amendable constitution.json.
**Tools to port:** `meta_analyze_trail`, `meta_apply_amendment`, `meta_reject_proposal`, `meta_rollback_amendment`, `meta_list_proposals`, `meta_constitution_status`, `meta_generate_sig`
**Uses:** `MOSES_OPERATOR_SECRET` (already in ClawHub env) — clean port
**New files:** `scripts/meta.py`, `data/constitution.json`, `data/core_principles.json`, `data/proposals/`

---

### [BUILD-002] Commitment drift gate inside `govern_loop.py`
**Priority:** HIGH — drift scoring exists in MCP but may not be operating; ClawHub has Jaccard but no block threshold
**Source:** `moses-governance-mcp/governance/commitment.py` → `evaluate_commitment()`
**What it is:** During governed action check, score semantic drift between action and session history. If drift > threshold → block. Returns `drift_level`, `commitment_preserved`, `block_threshold`.
**Note:** Confirm whether MCP's `evaluate_commitment()` is actually running or is a stub before porting.

---

### [BUILD-003] Ghost token detection inside `govern_check_action`
**Priority:** MEDIUM — ghost token detection exists standalone in coverify but isn't called during governance checks
**Source:** `skills/coverify/scripts/commitment_verify.py` → `detect_ghost_tokens()`
**What it is:** When `govern_check_action` runs, also run ghost token check on the action text vs. last known commitment kernel. Flag `cascade_risk: HIGH` if modal anchors are absent.
**Files to modify:** `scripts/audit_stub.py` (or new `scripts/commitment_gate.py`)

---

### [BUILD-004] `/stamp` skill — governed output embedding
**Priority:** MEDIUM — exists in Cowork, missing from ClawHub
**Source:** `moses-governance-cowork/skills/stamp/SKILL.md`
**What it is:** Embeds MO§ES™ governance metadata into every document produced this session. Mode, posture, session ID, action hash stamped on output.
**New files:** `skills/moses-governance/skills/stamp/SKILL.md` (or standalone `moses-stamp`)

---

### [STASH-001] Oracle verification — `govern_oracle_verify`
**Status:** STASH — Grok hook not live yet
**Source:** `moses-governance-mcp/governance/oracle.py`
**Resume when:** `XAI_GROK_API_KEY` is configured and Grok integration is active

---

## Pending Proposals — Cowork Plugin (moses-governance-cowork)

### [PROPOSAL-001] Add `/lineage` command to Cowork plugin
**Repo:** moses-governance-cowork
**Type:** add
**Reason:** Cowork plugin has no lineage at all. Pure behavioral enforcement with no anchor. Even prompt-native lineage declaration closes the biggest constitutional gap — session carries the MOSES_ANCHOR, Claude holds it for the duration.

**New file:** `commands/lineage.md`

```markdown
---
description: Declare and verify MO§ES™ lineage anchor for this session. Confirms this governed session traces to the origin filing. Run at session start before high-stakes tasks.
argument-hint: [verify|attest]
---

# /lineage

Declares the MO§ES™ sovereign lineage anchor for this session.

**MOSES_ANCHOR:** `5cda97fa2ad53e199618f5a610240888ae09d5a1e5e17b0d48c676d37dcda636`
**Origin:** Serial No. 63/877,177 | DOI: https://zenodo.org/records/18792459 | Ello Cello LLC

## Behavior

**`/lineage`** (no argument) — declare and hold the anchor for this session:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MO§ES™ LINEAGE — SESSION ANCHOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANCHOR   5cda97fa...dcda636
ORIGIN   Serial 63/877,177 · Zenodo 18792459
CUSTODY  Ello Cello LLC / Deric McHenry
STATUS   SOVEREIGN CUSTODY CONFIRMED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This session is lineage-anchored. All governed actions
trace to the origin filing for the duration of this session.
```

**`/lineage verify`** — confirm the anchor is active and custody intact.

**`/lineage attest`** — produce a signed attestation statement for sharing:

```
MO§ES™ LINEAGE ATTESTATION
Session governed under: Serial No. 63/877,177
Anchor: 5cda97fa...dcda636
Custody: Ello Cello LLC / Deric McHenry
DOI: https://zenodo.org/records/18792459
Attestation method: prompt-native (behavioral)
For cryptographic verification: clawhub install lineage-claws
```

Note: For three-layer cryptographic custody (archival → anchor → live ledger), use the Claude Code plugin.
```

---

### [PROPOSAL-002] Add `/coverify` command to Cowork plugin
**Repo:** moses-governance-cowork
**Type:** add
**Reason:** No commitment verification exists in Cowork. The Conservation Law (C(T(S)) = C(S)) is MO§ES™'s scientific claim — Cowork users have no way to test it. Prompt-native ghost token detection requires no Python.

**New file:** `commands/coverify.md`

```markdown
---
description: Verify commitment conservation between two texts. Extracts commitment kernels, scores similarity, detects ghost tokens. Tests whether meaning survived transformation — or names what leaked.
argument-hint: "[original text] → [transformed text]"
---

# /coverify

Tests the Commitment Conservation Law: C(T(S)) = C(S).

Commitment — the irreducible meaning in a signal — is conserved under transformation when enforcement is active. It leaks when enforcement is absent. CoVerify tests whether it held.

## Behavior

When invoked with two texts separated by `→`:

1. **Extract** commitment kernel from each: tokens carrying `must`, `shall`, `never`, `always`, `require`, `guarantee`, `ensure`, and the sentences that carry them.

2. **Score** Jaccard similarity between the two kernels.

3. **Detect ghost tokens** — commitment tokens present in the original, absent in the transformed version.

4. **Classify cascade risk:**
   - `HIGH` — modal/enforcement anchor lost (`must` → `should`, `shall never` → `can`)
   - `MEDIUM` — peripheral tokens leaked, anchors intact
   - `NONE` — no leakage

Output format:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MO§ES™ COVERIFY — COMMITMENT CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORIGINAL KERNEL   [extracted tokens]
TRANSFORMED KERNEL [extracted tokens]
JACCARD           [0.0 – 1.0]
VERDICT           CONSERVED / VARIANCE / DIVERGED
GHOST TOKENS      [leaked tokens or "none"]
CASCADE RISK      NONE / MEDIUM / HIGH
CASCADE NOTE      [explanation if risk present]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Verdicts:**
- `CONSERVED` — Jaccard ≥ 0.8, commitment kernel survived
- `VARIANCE` — same input, Jaccard < 0.8 — model extraction differs, not a leak
- `DIVERGED` — Jaccard < 0.8 — commitment leaked or inputs genuinely different

Note: For automated cross-model structural classification, use the Claude Code plugin.
```

---

### [PROPOSAL-003] Add `/hash` command to Cowork plugin
**Repo:** moses-governance-cowork
**Type:** add
**Reason:** Session integrity hashing. Already built in ClawHub. Prompt-native version generates a verifiable session fingerprint — useful for audit continuity and cross-session reference.

**New file:** `commands/hash.md`

```markdown
---
description: Generate a session integrity hash — a fingerprint of the current governance state and conversation content. Use for audit continuity, handoff, or cross-session reference.
argument-hint: [state|conversation|full]
---

# /hash

Generates a session integrity fingerprint from active governance state.

## Behavior

Produces a structured hash summary of:
- Current mode, posture, role
- Vault documents loaded
- Governance event count
- Session timestamp

Output format:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MO§ES™ SESSION HASH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STATE       mode:[mode] posture:[posture] role:[role]
VAULT       [docs or empty]
EVENTS      [count]
TIMESTAMP   [ISO timestamp]
FINGERPRINT [SHA-256 representation of state string]
METHOD      prompt-native (behavioral)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use this fingerprint to reference this governance state
in future sessions or handoffs.
```

Note: Compute SHA-256 by treating the state string as the input. For cryptographic chain hashing, use the Claude Code plugin.
```

---

### [PROPOSAL-004] Port `/stamp` back to ClawHub (moses-governance)
**Repo:** moses-claw-gov
**Type:** add
**Reason:** `/stamp` exists in Cowork — embeds governance metadata into every document produced. ClawHub doesn't have it. Should be symmetric. This is the one thing Cowork built that Claw is missing.

**To review:** Read `skills/stamp/SKILL.md` in moses-governance-cowork, then port as a ClawHub skill with hook-level enforcement (stamp fires automatically post-action, not manually).

---

---

## Open Decision — Sub-Skill Labeling (needs Deric's call)

**Context:** The three new BUILD scripts (`meta.py`, `commitment.py`, stamp) were added to `moses-governance` this session. They work but have no separate identity on ClawHub — invisible to someone browsing the skill family.

**Option A — Label only (quick)**
Add a `## Sub-Skills` section to `skills/moses-governance/SKILL.md` listing each engine with what it does and how to invoke it. No new ClawHub listings. Fast.

**Option B — Promote to standalone skills**
Pull `meta.py` → `moses-meta` and `commitment.py` → `moses-commitment` as their own ClawHub skills, same pattern as `coverify` and `lineage-claws`. More surface area, more install options.

**Option C — Both**
Label them in `moses-governance` SKILL.md now, promote the two heaviest (`meta`, `commitment`) to standalone later when ready for a dedicated publish push.

**Deric's call:** ✅ **C — decided 2026-03-14**
Label in `moses-governance` SKILL.md now. Promote `meta` and `commitment` to standalone ClawHub skills later when ready for a dedicated publish push.

---

## In Progress

- **CoVerify article** — draft complete (Claude Code), formatting/publish in progress (CoWork)

## Approved
_(moved here after merge)_

## Rejected
_(moved here with rejection reason)_
