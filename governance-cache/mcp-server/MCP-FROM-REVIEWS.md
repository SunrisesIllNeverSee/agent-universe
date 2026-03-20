# MO§ES™ MCP — Code From External Reviews
## Source: Grok (xAI) · Gemini (Google) · DeepSeek
## Date: 2026-03-11 | For: MCP Cowork Session

> **Note:** These are reviewer proposals. Reconcile with `MCP-SERVER-BUILD.md` before implementing.
> FastMCP architecture (stdio transport, GovernanceState sessions) takes precedence.
> The Referee Daemon concept below uses FastAPI — translate to FastMCP tools.

---

## From Grok — Referee Daemon Architecture

Grok's core concept: a standalone daemon running outside Claude that Claude cannot bypass.
All checks happen externally — paraphrase bypass is dead because the daemon, not Claude, evaluates.

### referee-daemon/main.py (FastAPI skeleton)

```python
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import os

app = FastAPI(title="MO§ES™ Referee Daemon v2.0")

class ActionRequest(BaseModel):
    message: str
    mode: str
    posture: str
    role: str
    session_hash: str

@app.post("/check")
async def check_action(req: ActionRequest):
    # 1. Commitment Conservation scoring
    drift_score = score_commitment(req.message)
    if drift_score > 5:
        return {"permitted": False, "reason": f"COMMITMENT DRIFT {drift_score}% — escalated to High Integrity"}

    # 2. FMS-2.0 moat check
    moat_tier = calculate_fms_moat(req.session_hash)
    if moat_tier < 3:
        return {"permitted": False, "reason": "Session moat too weak — Deep/Constitutional Float required"}

    # 3. Grok Oracle (optional — requires XAI_GROK_API_KEY)
    oracle = await grok_verify(req.message)
    if not oracle["preserves_commitment"]:
        return {"permitted": False, "reason": f"GROK ORACLE REJECTED: {oracle['explanation']}"}

    # 4. Mode/Posture/Role rules (externally enforced)
    if req.mode == "High Security" and "transfer" in req.message.lower():
        return {"permitted": False, "reason": "High Security: explicit operator confirmation required"}

    return {"permitted": True, "reason": "MO§ES™ KERNEL APPROVED", "drift_score": drift_score, "moat_tier": moat_tier}

if __name__ == "__main__":
    print("MO§ES™ REFEREE DAEMON STARTED")
    uvicorn.run(app, host="127.0.0.1", port=1337)
```

**FastMCP translation note:** Wrap this logic as `govern_check_action()` tool in the FastMCP server.
The daemon concept becomes the MCP server itself — Claude calls it via MCP tools, not HTTP.

---

### referee-daemon/commitment_engine.py

Live implementation of the 2026 Conservation Law (Zenodo 10.5281/zenodo.18792459).
Measures semantic commitment drift under recursive transformation.

```python
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def score_commitment(new_message: str, history: list = None) -> float:
    """
    Measures semantic drift between new message and conversation history.
    Target: <5% drift = commitment preserved.
    Returns drift percentage (0-100).
    """
    if not history:
        history = ["INITIAL COMMITMENT BASELINE"]

    vectorizer = TfidfVectorizer()
    all_text = history + [new_message]
    tfidf_matrix = vectorizer.fit_transform(all_text)

    # Compare new message to entire history average
    history_vectors = tfidf_matrix[:-1].mean(axis=0)
    new_vector = tfidf_matrix[-1]

    similarity = cosine_similarity(history_vectors, new_vector)[0][0]
    drift = (1 - similarity) * 100

    return drift
```

**Note:** Grok's implementation uses TF-IDF cosine similarity as a proxy for the paper's
conservation invariant. The actual paper may use a different formalism — verify against
the falsifiability harness at github.com/SunrisesIllNeverSee/commitment-conservation
before treating this as the canonical implementation.

---

### referee-daemon/fms_self_score.py

FMS-2.0 self-moat calculator. Scores session moat strength (tiers 1–5).

```python
def calculate_fms_moat(session_hash: str) -> int:
    """
    Scores session against FMS-2.0 tiers (1=weak, 5=Deep/Constitutional Float).
    Current implementation uses hash entropy as proxy.
    Production: use genesis hash + operational history + constraint symmetry.
    """
    entropy = sum(ord(c) for c in session_hash) % 100
    if entropy > 85:
        return 5  # Deep/Constitutional Float — uncopyable
    elif entropy > 60:
        return 4
    return 3
```

**Note:** This is a placeholder. Real FMS-2.0 scoring needs the full operational history
and genesis hash. Treat as scaffold, not production implementation.

---

### referee-daemon/grok_oracle.py

Calls xAI Grok API for independent commitment verification. Optional layer.

```python
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def grok_verify(message: str) -> dict:
    """
    Sends message to Grok API for independent truth verification.
    Falls back to local-only if no API key present.
    """
    api_key = os.getenv("XAI_GROK_API_KEY")
    if not api_key:
        return {"preserves_commitment": True, "explanation": "No key — local-only mode"}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "grok-3",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are the Grok Oracle. Does this output preserve semantic commitment "
                            "per the 2026 McHenry Conservation Law? Answer only YES/NO + one-sentence reason."
                        )
                    },
                    {"role": "user", "content": message}
                ]
            }
        )
        answer = resp.json()["choices"][0]["message"]["content"]
        return {
            "preserves_commitment": "YES" in answer.upper(),
            "explanation": answer
        }
```

---

### referee-daemon/agent_swarm_coordinator.py

Enforces Primary → Secondary → Observer hierarchy across models.

```python
import os
from commitment_engine import score_commitment
from fms_self_score import calculate_fms_moat
from grok_oracle import grok_verify

class AgentSwarm:
    def __init__(self):
        self.roles = {"primary": None, "secondary": None, "observer": None}
        self.genesis_hash = "MOSES-GENESIS-" + os.urandom(32).hex()

    async def run_round(self, task: str, history: list) -> dict:
        # 1. Primary leads
        primary_out = await self._invoke_agent("primary", task)

        # 2. Secondary validates with conservation proof
        secondary_out = await self._invoke_agent("secondary", primary_out)
        drift = score_commitment(secondary_out, history)
        if drift > 0.1:
            return {"blocked": True, "reason": f"DRIFT {drift}% — Secondary vetoed"}

        # 3. Observer flags only
        observer_report = await self._invoke_agent("observer", secondary_out)

        # 4. Final gate: Grok Oracle + FMS moat
        oracle = await grok_verify(secondary_out)
        moat = calculate_fms_moat(self.genesis_hash)

        if not oracle["preserves_commitment"] or moat < 5:
            return {"blocked": True, "reason": "Swarm failed constitutional checks"}

        return {"approved": True, "output": secondary_out, "drift": drift, "moat": moat}

    async def _invoke_agent(self, role: str, input_text: str) -> str:
        # In production: call the appropriate model/agent API
        # For now: placeholder
        raise NotImplementedError(f"Agent invocation for role '{role}' not yet implemented")
```

**FastMCP translation note:** This becomes a `govern_run_swarm_round()` tool in the MCP server.
Each role maps to a separate MCP session with its own `GovernanceState`.

---

## From Gemini — Hardened Hook Patterns

### Semantic Firewall (governance.py addition)

Already merged into `_CONCEPT_SIGNALS` in governance.py (commit ea63d88).
Gemini's full classifier for reference:

```python
CLUSTERS = {
    "FINANCIAL": ["transfer", "pay", "buy", "withdraw", "remit", "liquidate"],
    "DESTRUCTIVE": ["rm", "delete", "truncate", "overwrite", "remove", "drop"],
    "NETWORK": ["curl", "wget", "ssh", "ping", "api", "connect"]
}

def validate_command(cmd):
    with open('data/governance_state.json', 'r') as f:
        state = json.load(f)

    mode = state.get("mode")
    posture = state.get("posture")
    cmd_low = cmd.lower()

    # Hard Posture Block
    if posture == "SCOUT" and any(word in cmd_low for word in CLUSTERS["DESTRUCTIVE"]):
        return "BLOCKED: Posture [SCOUT] cannot execute [DESTRUCTIVE] actions."

    # Hard Mode Block
    if mode == "High Security":
        if any(word in cmd_low for word in CLUSTERS["FINANCIAL"]):
            return "BLOCKED: [High Security] prevents [FINANCIAL] transactions."

    return "PROCEED"
```

### After-Action Review (AAR) Hook Pattern

Gemini's post-execution verification — verifies output matched mode constraints.
This is the hook pattern for `stop.sh` expansion (already scaffolded, needs AAR logic):

```bash
#!/bin/bash
# MO§ES™ AAR Post-Execute Hook (Gemini pattern)

CURRENT_POSTURE=$(python3 -c "import json; print(json.load(open('$GOVERNANCE_STATE')).get('posture','SCOUT'))" 2>/dev/null)

# Posture Ground-Truth Check
# If SCOUT mode but a file was modified, flag breach in the ledger
if [[ "$CURRENT_POSTURE" == "SCOUT" ]]; then
    MODIFIED_FILES=$(git status --short 2>/dev/null)
    if [[ -n "$MODIFIED_FILES" ]]; then
        python3 scripts/audit.py log_action \
            --component "critic" \
            --action "POSTURE_BREACH" \
            --detail "SCOUT modified files: $MODIFIED_FILES"
        echo "⚠ POSTURE BREACH: Modifications detected in SCOUT mode — logged."
    fi
fi
```

### Hardened Pre-Execute with Integrity Check (Gemini pattern)

```bash
# Add to pre-execute.sh — Audit Dead Man's Switch
INTEGRITY_CHECK=$(python3 scripts/audit.py verify 2>/dev/null)
if [[ "$INTEGRITY_CHECK" != *"valid"*"true"* ]]; then
    echo "❌ CRITICAL: Audit chain corruption detected. Execution blocked." >&2
    exit 2
fi
```

---

## From DeepSeek — Meta-Governance System

DeepSeek's unique concept: the constitution analyzes its own audit trail and proposes amendments.
This is a v1.2 feature — build after MCP server is stable.

### Data Structures Required

```
data/
├── core_principles.json      # Immutable bedrock — never amendable
├── constitution.json         # Versioned, amendable
├── amendments.jsonl          # Append-only amendment ledger
└── proposals/
    ├── pending/              # Proposals awaiting review
    ├── approved/             # Applied amendments
    └── rejected/             # Rejected with reasons
```

### core_principles.json (example)

```json
{
  "version": "1.0.0",
  "principles": [
    "All actions must be audited — audit trail is non-negotiable",
    "Operator confirmation required for all destructive actions",
    "Role hierarchy sequence (Primary → Secondary → Observer) is constitutional and cannot be removed",
    "Governance state must persist between sessions"
  ],
  "hash": "sha256:...",
  "immutable": true
}
```

### analyze_audit_trail() — Amendment Proposal Engine

```python
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import json, hashlib, time

def analyze_audit_trail(timeframe="week", focus=None, min_confidence=0.8):
    """
    Reads audit history and generates constitutional amendment proposals.
    Heuristics:
    - block_rate > 30% + override_rate < 10% → mode too strict, propose relaxing
    - override_rate > 30% → rule being bypassed, propose exception
    - mode rarely used → propose deprecation
    """
    if focus is None:
        focus = ["modes", "postures", "roles"]

    # Determine time range
    end_time = datetime.utcnow()
    delta = {"day": 1, "week": 7, "month": 30}.get(timeframe, 7)
    start_time = end_time - timedelta(days=delta)

    # Load audit entries in range
    ledger_path = Path("data/audit_ledger.jsonl")
    entries = []
    with open(ledger_path) as f:
        for line in f:
            entry = json.loads(line)
            ts = datetime.fromtimestamp(entry["timestamp"])
            if start_time <= ts <= end_time:
                entries.append(entry)

    # Group stats by mode/posture/role
    stats = defaultdict(lambda: {"blocked": 0, "overridden": 0, "total": 0, "action_types": defaultdict(int)})
    for e in entries:
        mode = e.get("governance_mode", "unknown")
        if "modes" in focus:
            key = ("mode", mode)
            stats[key]["total"] += 1
            if e.get("blocked"):
                stats[key]["blocked"] += 1
            if e.get("override"):
                stats[key]["overridden"] += 1
            stats[key]["action_types"][e.get("action", "unknown")] += 1

    # Generate proposals
    proposals = []
    for (category, name), data in stats.items():
        if data["total"] < 10:
            continue
        block_rate = data["blocked"] / data["total"]
        override_rate = data["overridden"] / data["blocked"] if data["blocked"] > 0 else 0

        if block_rate > 0.3 and override_rate < 0.1:
            top_action = max(data["action_types"].items(), key=lambda x: x[1])[0]
            proposals.append({
                "id": hashlib.sha256(str(time.time()).encode()).hexdigest()[:12],
                "type": f"{category}_modification",
                "target": name,
                "rationale": (
                    f"{name} blocked {block_rate:.1%} of actions with only {override_rate:.1%} overridden. "
                    f"Consider relaxing rule for '{top_action}'."
                ),
                "evidence": {
                    "period": f"{start_time.date()} to {end_time.date()}",
                    "blocked_count": data["blocked"],
                    "total_count": data["total"]
                }
            })

    # Write proposals to disk
    proposals_dir = Path("data/proposals/pending")
    proposals_dir.mkdir(parents=True, exist_ok=True)
    for prop in proposals:
        with open(proposals_dir / f"{prop['id']}.json", "w") as f:
            json.dump(prop, f, indent=2)

    return {
        "proposals": proposals,
        "analysis_summary": f"Analyzed {len(entries)} entries. Generated {len(proposals)} proposals."
    }
```

### apply_amendment() — Atomic Write + Crypto Signing

```python
import shutil, hashlib, json
from pathlib import Path
from datetime import datetime

def apply_amendment(proposal_id: str, operator_signature: str) -> dict:
    """
    Apply an approved amendment. Atomic write, cryptographically signed, rollback-capable.
    """
    proposal_path = Path(f"data/proposals/pending/{proposal_id}.json")
    if not proposal_path.exists():
        return {"success": False, "message": f"Proposal {proposal_id} not found."}

    with open(proposal_path) as f:
        proposal = json.load(f)

    if not operator_signature:
        return {"success": False, "message": "Invalid signature."}

    constitution_path = Path("data/constitution.json")
    with open(constitution_path) as f:
        constitution = json.load(f)

    # Apply changes based on proposal type
    if proposal["type"] == "mode_modification":
        mode_name = proposal["target"]
        changes = proposal.get("suggested_changes", {})
        if mode_name in constitution.get("modes", {}):
            mode = constitution["modes"][mode_name]
            if "prohibited" in changes:
                mode["prohibited"].extend(changes["prohibited"].get("add", []))
                mode["prohibited"] = [
                    x for x in mode["prohibited"]
                    if x not in changes["prohibited"].get("remove", [])
                ]

    # Increment version
    old_version = constitution["version"]
    parts = old_version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    new_version = ".".join(parts)

    new_constitution = {**constitution, "version": new_version, "previous_version": old_version}
    constitution_hash = hashlib.sha256(
        json.dumps(new_constitution, sort_keys=True).encode()
    ).hexdigest()
    new_constitution["signature"] = f"sha256:{constitution_hash}"

    # Atomic write
    temp_path = constitution_path.with_suffix(".tmp")
    with open(temp_path, "w") as f:
        json.dump(new_constitution, f, indent=2)
    shutil.move(str(temp_path), str(constitution_path))

    # Archive proposal + log amendment
    archive_dir = Path("data/proposals/approved")
    archive_dir.mkdir(exist_ok=True)
    proposal_path.rename(archive_dir / f"{proposal_id}.json")

    amendment_entry = {
        "id": proposal_id,
        "timestamp": datetime.utcnow().timestamp(),
        "iso_time": datetime.utcnow().isoformat(),
        "old_version": old_version,
        "new_version": new_version,
        "signature": operator_signature
    }
    with open("data/amendments.jsonl", "a") as f:
        f.write(json.dumps(amendment_entry) + "\n")

    return {"success": True, "new_version": new_version}
```

### /constitutional-amend Command Subcommands

```
/constitutional-amend analyze [--timeframe day|week|month|all]
/constitutional-amend list [--pending | --approved]
/constitutional-amend show [proposal_id]
/constitutional-amend approve [proposal_id] --signature [sig]
/constitutional-amend reject [proposal_id] --reason [reason]
/constitutional-amend status
```

---

## Integration Roadmap

| Feature | Source | Target Version | Depends On |
|---------|--------|---------------|------------|
| FastMCP server (13 tools) | MCP-SERVER-BUILD.md | v1.1 | — |
| Commitment scoring | Grok commitment_engine.py | v1.1 | FastMCP server |
| Grok Oracle | Grok grok_oracle.py | v1.1 optional | FastMCP server |
| Agent Swarm Coordinator | Grok agent_swarm_coordinator.py | v1.1 | FastMCP server |
| AAR hook pattern | Gemini stop.sh expansion | v1.1 | FastMCP server |
| Audit dead man's switch | Gemini pre-execute pattern | v1.1 | FastMCP server |
| Meta-Governance | DeepSeek analyze/apply | v1.2 | Stable MCP server |
| Amendment Protocol | DeepSeek /constitutional-amend | v1.2 | Meta-Governance |
| FMS-2.0 self-moat | Grok fms_self_score.py | v2.0 | Verified against paper |
| Eternal Ledger (Arweave) | Grok | v2.0 | MCP server + Solana |

---

© 2026 Ello Cello LLC | MO§ES™ Patent Pending: Serial No. 63/877,177
