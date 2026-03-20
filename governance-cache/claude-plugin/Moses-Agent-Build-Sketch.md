──────────────────────────────────────
MO§E§™ GOVERNED AGENT — BUILD SKETCH
For The Synthesis Hackathon (March 13)
Build this in DeepSeek/Gemini/GPT — save Claude usage
2026-03-09 | Ello Cello LLC
──────────────────────────────────────

## WHAT YOU'RE BUILDING

A self-governing AI agent that:
1. Receives tasks
2. Checks its constitutional governance before acting
3. Executes within permitted boundaries
4. Logs every action to a cryptographic audit trail
5. Reports results with governance metadata attached

NOT a coding agent. A GOVERNANCE agent. It demonstrates that
autonomous agents can carry constitutional behavioral controls.

## THE PITCH TO HACKATHON JUDGES

"Every agent in this hackathon operates on instructions.
This one operates on a constitution."

## ARCHITECTURE (4 Files, ~500 lines total)

```
moses-agent/
├── agent.py          (~150 lines) — Main agent loop
├── governance.py     (~200 lines) — Constitutional engine
├── audit.py          (~100 lines) — SHA-256 audit chain
└── config.yaml       (~50 lines)  — Agent identity + governance config
```

## FILE 1: config.yaml (~50 lines)

This is the agent's constitution. Its identity and rules.

```yaml
# AGENT IDENTITY
agent:
  name: "MOSES-001"
  version: "1.0.0"
  owner: "Ello Cello LLC"
  description: "Constitutional governance agent — MO§E§™"

# GOVERNANCE CONFIGURATION
governance:
  # Which mode the agent starts in
  default_mode: "unrestricted"
  
  # Available modes (from MO§E§™ framework)
  modes:
    unrestricted:
      description: "Full operational capacity"
      allowed_actions: ["research", "analyze", "summarize", "recommend", "create", "evaluate"]
      restricted_actions: []
    
    restricted:
      description: "Limited to read-only operations"
      allowed_actions: ["research", "analyze", "summarize"]
      restricted_actions: ["create", "recommend", "evaluate"]
    
    defense:
      description: "Protective mode — audit and verify only"
      allowed_actions: ["analyze", "evaluate"]
      restricted_actions: ["research", "create", "summarize", "recommend"]

  # Posture controls
  default_posture: "scout"
  
  postures:
    scout:
      description: "Exploration mode — gather and report"
      bias: "breadth over depth"
      token_budget: "standard"
    
    sentinel:
      description: "Watchdog mode — monitor and alert"
      bias: "accuracy over speed"
      token_budget: "conservative"
    
    operator:
      description: "Execution mode — act and deliver"
      bias: "completion over exploration"
      token_budget: "flexible"

  # Role in hierarchy
  role: "primary"
  roles_available: ["primary", "secondary", "observer"]

# AUDIT CONFIGURATION
audit:
  enabled: true
  hash_algorithm: "sha256"
  chain_file: "audit_chain.jsonl"
  log_level: "full"  # full | summary | minimal
```

## FILE 2: governance.py (~200 lines)

The constitutional engine. Every action passes through here.

```python
"""
MO§E§™ Governance Engine
Constitutional behavioral controls for autonomous agents.
Patent Pending — Ello Cello LLC
"""

import yaml
import time
from typing import Dict, List, Optional, Tuple

class GovernanceEngine:
    """
    Core governance engine. Loads constitution from config,
    evaluates actions against current mode/posture/role,
    and returns permit/deny decisions with reasoning.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        gov = self.config['governance']
        self.current_mode = gov['default_mode']
        self.current_posture = gov['default_posture']
        self.current_role = gov['role']
        self.modes = gov['modes']
        self.postures = gov['postures']
        self.action_log = []
    
    def set_mode(self, mode: str) -> Dict:
        """Switch governance mode. Returns confirmation or rejection."""
        if mode not in self.modes:
            return {
                "status": "denied",
                "reason": f"Mode '{mode}' not in constitution",
                "available_modes": list(self.modes.keys())
            }
        
        previous = self.current_mode
        self.current_mode = mode
        return {
            "status": "permitted",
            "previous_mode": previous,
            "current_mode": mode,
            "description": self.modes[mode]['description'],
            "timestamp": time.time()
        }
    
    def set_posture(self, posture: str) -> Dict:
        """Switch posture. Returns confirmation or rejection."""
        if posture not in self.postures:
            return {
                "status": "denied",
                "reason": f"Posture '{posture}' not in constitution",
                "available_postures": list(self.postures.keys())
            }
        
        previous = self.current_posture
        self.current_posture = posture
        return {
            "status": "permitted",
            "previous_posture": previous,
            "current_posture": posture,
            "description": self.postures[posture]['description'],
            "timestamp": time.time()
        }
    
    def check_action(self, action: str, context: Optional[Dict] = None) -> Dict:
        """
        THE CORE METHOD.
        Every action the agent wants to take passes through here.
        Returns permit/deny with full governance metadata.
        """
        mode_config = self.modes[self.current_mode]
        posture_config = self.postures[self.current_posture]
        
        # Check if action is explicitly restricted in current mode
        if action in mode_config.get('restricted_actions', []):
            decision = {
                "status": "denied",
                "action": action,
                "reason": f"Action '{action}' restricted in mode '{self.current_mode}'",
                "mode": self.current_mode,
                "posture": self.current_posture,
                "role": self.current_role,
                "timestamp": time.time(),
                "context": context
            }
            self.action_log.append(decision)
            return decision
        
        # Check if action is in allowed list
        if action in mode_config.get('allowed_actions', []):
            decision = {
                "status": "permitted",
                "action": action,
                "mode": self.current_mode,
                "posture": self.current_posture,
                "posture_bias": posture_config['bias'],
                "role": self.current_role,
                "timestamp": time.time(),
                "context": context
            }
            self.action_log.append(decision)
            return decision
        
        # Action not listed — deny by default (constitutional conservatism)
        decision = {
            "status": "denied",
            "action": action,
            "reason": f"Action '{action}' not in allowed list for mode '{self.current_mode}'",
            "mode": self.current_mode,
            "posture": self.current_posture,
            "role": self.current_role,
            "timestamp": time.time(),
            "context": context
        }
        self.action_log.append(decision)
        return decision
    
    def get_status(self) -> Dict:
        """Return current governance state."""
        return {
            "agent": self.config['agent']['name'],
            "mode": self.current_mode,
            "mode_description": self.modes[self.current_mode]['description'],
            "posture": self.current_posture,
            "posture_description": self.postures[self.current_posture]['description'],
            "posture_bias": self.postures[self.current_posture]['bias'],
            "role": self.current_role,
            "actions_logged": len(self.action_log),
            "timestamp": time.time()
        }
    
    def get_permitted_actions(self) -> List[str]:
        """What can the agent do right now?"""
        return self.modes[self.current_mode].get('allowed_actions', [])
    
    def get_restricted_actions(self) -> List[str]:
        """What is the agent NOT allowed to do right now?"""
        return self.modes[self.current_mode].get('restricted_actions', [])


class GovernanceContext:
    """
    Builds the full governed context that gets injected into
    any LLM call the agent makes. This is the IP.
    
    Instead of just sending a prompt to the LLM, the agent
    sends: prompt + governance context. The LLM operates
    within constitutional constraints.
    """
    
    def __init__(self, engine: GovernanceEngine):
        self.engine = engine
    
    def build_context(self, task: str) -> str:
        """
        Build the governance preamble that gets prepended
        to every LLM interaction.
        """
        status = self.engine.get_status()
        permitted = self.engine.get_permitted_actions()
        restricted = self.engine.get_restricted_actions()
        
        context = f"""
## GOVERNANCE ACTIVE — MO§E§™ CONSTITUTIONAL CONTROLS

Agent: {status['agent']}
Mode: {status['mode']} — {status['mode_description']}
Posture: {status['posture']} — {status['posture_description']}
Bias: {status['posture_bias']}
Role: {status['role']}

### PERMITTED ACTIONS
{', '.join(permitted)}

### RESTRICTED ACTIONS (DO NOT PERFORM)
{', '.join(restricted) if restricted else 'None — full operational capacity'}

### TASK
{task}

### INSTRUCTIONS
Operate strictly within the permitted actions above.
If the task requires a restricted action, STOP and report
that the action is outside current governance parameters.
Do not attempt workarounds. Constitutional compliance is mandatory.
"""
        return context.strip()
```

## FILE 3: audit.py (~100 lines)

Cryptographic audit trail. Every decision gets hashed and chained.

```python
"""
MO§E§™ Audit Trail
SHA-256 hash chain for governance decisions.
Patent Pending — Ello Cello LLC
"""

import hashlib
import json
import time
from typing import Dict, Optional

class AuditLedger:
    """
    Append-only audit ledger with SHA-256 hash chaining.
    Each entry contains the hash of the previous entry,
    creating a tamper-evident chain.
    """
    
    def __init__(self, chain_file: str = "audit_chain.jsonl"):
        self.chain_file = chain_file
        self.chain = []
        self.previous_hash = "GENESIS"
        self._load_chain()
    
    def _load_chain(self):
        """Load existing chain from file if it exists."""
        try:
            with open(self.chain_file, 'r') as f:
                for line in f:
                    entry = json.loads(line.strip())
                    self.chain.append(entry)
                if self.chain:
                    self.previous_hash = self.chain[-1]['hash']
        except FileNotFoundError:
            pass
    
    def log(self, event_type: str, data: Dict, 
            agent_name: str = "MOSES-001") -> Dict:
        """
        Log a governance event to the audit chain.
        Returns the complete audit entry with hash.
        """
        entry = {
            "sequence": len(self.chain) + 1,
            "timestamp": time.time(),
            "agent": agent_name,
            "event_type": event_type,
            "data": data,
            "previous_hash": self.previous_hash
        }
        
        # Generate hash of this entry
        entry_string = json.dumps(entry, sort_keys=True)
        entry['hash'] = hashlib.sha256(entry_string.encode()).hexdigest()
        
        # Append to chain
        self.chain.append(entry)
        self.previous_hash = entry['hash']
        
        # Write to file
        with open(self.chain_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        return entry
    
    def verify_chain(self) -> Dict:
        """
        Verify integrity of the entire audit chain.
        Returns pass/fail with details.
        """
        if not self.chain:
            return {"status": "empty", "entries": 0}
        
        previous_hash = "GENESIS"
        for i, entry in enumerate(self.chain):
            # Check previous hash link
            if entry['previous_hash'] != previous_hash:
                return {
                    "status": "BROKEN",
                    "break_at": i,
                    "expected_hash": previous_hash,
                    "found_hash": entry['previous_hash']
                }
            
            # Verify entry hash
            stored_hash = entry['hash']
            entry_copy = {k: v for k, v in entry.items() if k != 'hash'}
            computed_hash = hashlib.sha256(
                json.dumps(entry_copy, sort_keys=True).encode()
            ).hexdigest()
            
            if computed_hash != stored_hash:
                return {
                    "status": "TAMPERED",
                    "tampered_at": i,
                    "stored_hash": stored_hash,
                    "computed_hash": computed_hash
                }
            
            previous_hash = stored_hash
        
        return {
            "status": "VERIFIED",
            "entries": len(self.chain),
            "genesis_hash": self.chain[0]['hash'],
            "latest_hash": self.chain[-1]['hash']
        }
    
    def get_summary(self) -> Dict:
        """Return chain summary stats."""
        if not self.chain:
            return {"entries": 0}
        
        event_types = {}
        for entry in self.chain:
            et = entry['event_type']
            event_types[et] = event_types.get(et, 0) + 1
        
        return {
            "entries": len(self.chain),
            "event_types": event_types,
            "first_entry": self.chain[0]['timestamp'],
            "last_entry": self.chain[-1]['timestamp'],
            "chain_integrity": self.verify_chain()['status']
        }
```

## FILE 4: agent.py (~150 lines)

The actual agent. Receives tasks, governs itself, executes, audits.

```python
"""
MO§E§™ Governed Agent
Autonomous agent with constitutional behavioral controls.
Patent Pending — Ello Cello LLC

This agent demonstrates that autonomous AI agents can carry
constitutional governance — behavioral modes, posture controls,
role hierarchy, and cryptographic audit trails.

For The Synthesis Hackathon — March 2026
"""

import json
import time
from governance import GovernanceEngine, GovernanceContext
from audit import AuditLedger

class MosesAgent:
    """
    Self-governing autonomous agent.
    Every action passes through constitutional checks.
    Every decision is cryptographically audited.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        self.governance = GovernanceEngine(config_path)
        self.context_builder = GovernanceContext(self.governance)
        self.audit = AuditLedger()
        self.agent_name = self.governance.config['agent']['name']
        
        # Log agent initialization
        self.audit.log(
            event_type="AGENT_INIT",
            data=self.governance.get_status(),
            agent_name=self.agent_name
        )
        
        print(f"\n{'='*50}")
        print(f"  MO§E§™ GOVERNED AGENT — {self.agent_name}")
        print(f"  Mode: {self.governance.current_mode}")
        print(f"  Posture: {self.governance.current_posture}")
        print(f"  Role: {self.governance.current_role}")
        print(f"  Audit: ACTIVE")
        print(f"{'='*50}\n")
    
    def receive_task(self, task: str, required_action: str = "analyze") -> dict:
        """
        Receive a task, check governance, execute if permitted.
        This is the main entry point.
        """
        print(f"[TASK RECEIVED] {task[:80]}...")
        print(f"[GOVERNANCE CHECK] Action: {required_action} | Mode: {self.governance.current_mode}")
        
        # Step 1: Check governance
        check = self.governance.check_action(
            action=required_action,
            context={"task": task}
        )
        
        # Step 2: Audit the governance check
        self.audit.log(
            event_type="GOVERNANCE_CHECK",
            data=check,
            agent_name=self.agent_name
        )
        
        # Step 3: Act on decision
        if check['status'] == 'permitted':
            print(f"[PERMITTED] Executing under {check['mode']}/{check['posture']}")
            result = self.execute_task(task, required_action, check)
            return result
        else:
            print(f"[DENIED] {check['reason']}")
            denial = {
                "status": "task_denied",
                "task": task,
                "reason": check['reason'],
                "governance_state": self.governance.get_status(),
                "suggestion": f"Switch to a mode that permits '{required_action}'"
            }
            self.audit.log(
                event_type="TASK_DENIED",
                data=denial,
                agent_name=self.agent_name
            )
            return denial
    
    def execute_task(self, task: str, action: str, governance_check: dict) -> dict:
        """
        Execute the task within governance constraints.
        
        In a full deployment, this is where the agent calls
        an LLM API with the governed context prepended.
        For the hackathon demo, we simulate execution.
        """
        # Build governed context
        governed_prompt = self.context_builder.build_context(task)
        
        # ===================================
        # THIS IS WHERE LLM CALL GOES
        # In production:
        #   response = call_llm(governed_prompt)
        # For demo:
        #   We return the governed context itself
        #   to show what the agent operates under
        # ===================================
        
        result = {
            "status": "task_completed",
            "task": task,
            "action": action,
            "governance": {
                "mode": governance_check['mode'],
                "posture": governance_check['posture'],
                "role": governance_check['role'],
                "bias": governance_check.get('posture_bias', 'none')
            },
            "governed_context": governed_prompt,
            "timestamp": time.time()
        }
        
        # Audit the execution
        self.audit.log(
            event_type="TASK_EXECUTED",
            data={
                "task": task,
                "action": action,
                "mode": governance_check['mode'],
                "posture": governance_check['posture']
            },
            agent_name=self.agent_name
        )
        
        print(f"[COMPLETE] Task executed under governance\n")
        return result
    
    def switch_mode(self, mode: str) -> dict:
        """Switch governance mode with audit trail."""
        result = self.governance.set_mode(mode)
        self.audit.log(
            event_type="MODE_SWITCH",
            data=result,
            agent_name=self.agent_name
        )
        print(f"[MODE] Switched to: {mode}")
        return result
    
    def switch_posture(self, posture: str) -> dict:
        """Switch posture with audit trail."""
        result = self.governance.set_posture(posture)
        self.audit.log(
            event_type="POSTURE_SWITCH",
            data=result,
            agent_name=self.agent_name
        )
        print(f"[POSTURE] Switched to: {posture}")
        return result
    
    def status(self) -> dict:
        """Full agent status with audit summary."""
        return {
            "governance": self.governance.get_status(),
            "audit": self.audit.get_summary(),
            "permitted_actions": self.governance.get_permitted_actions(),
            "restricted_actions": self.governance.get_restricted_actions()
        }
    
    def verify_integrity(self) -> dict:
        """Verify the entire audit chain."""
        return self.audit.verify_chain()


# ============================================
# DEMO: Run the agent through its paces
# ============================================

if __name__ == "__main__":
    
    # Initialize governed agent
    agent = MosesAgent()
    
    # Show initial status
    print("--- INITIAL STATUS ---")
    print(json.dumps(agent.status(), indent=2))
    
    # Task 1: Permitted action in unrestricted mode
    print("\n--- TASK 1: Research (should be PERMITTED) ---")
    agent.receive_task(
        task="Research the current state of AI agent governance frameworks",
        required_action="research"
    )
    
    # Task 2: Switch to restricted mode
    print("\n--- SWITCHING TO RESTRICTED MODE ---")
    agent.switch_mode("restricted")
    
    # Task 3: Try a restricted action
    print("\n--- TASK 2: Create (should be DENIED in restricted mode) ---")
    agent.receive_task(
        task="Create a new trading strategy",
        required_action="create"
    )
    
    # Task 4: Permitted action in restricted mode
    print("\n--- TASK 3: Analyze (should be PERMITTED) ---")
    agent.receive_task(
        task="Analyze the risk profile of this portfolio",
        required_action="analyze"
    )
    
    # Switch to defense mode
    print("\n--- SWITCHING TO DEFENSE MODE ---")
    agent.switch_mode("defense")
    
    # Task 5: Most actions denied in defense
    print("\n--- TASK 4: Research (should be DENIED in defense mode) ---")
    agent.receive_task(
        task="Research new market opportunities",
        required_action="research"
    )
    
    # Switch posture
    print("\n--- SWITCHING POSTURE TO SENTINEL ---")
    agent.switch_posture("sentinel")
    
    # Final status
    print("\n--- FINAL STATUS ---")
    print(json.dumps(agent.status(), indent=2))
    
    # Verify audit chain integrity
    print("\n--- AUDIT CHAIN VERIFICATION ---")
    print(json.dumps(agent.verify_integrity(), indent=2))
    
    print("\n" + "="*50)
    print("  Every action governed. Every decision audited.")
    print("  MO§E§™ — Quantifying the Unquantifiable")
    print("  Patent Pending — Ello Cello LLC")
    print("="*50)
```

## HOW TO BUILD THIS

### Step 1: Create the directory
```bash
mkdir moses-agent
cd moses-agent
```

### Step 2: Create the 4 files
Copy each file above into the directory.

### Step 3: Install dependency
```bash
pip install pyyaml
```

### Step 4: Run the demo
```bash
python agent.py
```

You'll see the agent:
- Initialize with governance active
- Accept a permitted task
- Switch to restricted mode
- Get DENIED on a restricted action
- Accept a permitted action in restricted mode
- Switch to defense mode
- Get DENIED on most actions
- Switch posture
- Verify its own audit chain integrity

### Step 5: Check the audit trail
```bash
cat audit_chain.jsonl
```

Every decision, every mode switch, every denial — 
hashed and chained. Tamper-evident.

## FOR THE SYNTHESIS HACKATHON

### What to submit:
- The 4-file agent
- A README explaining MO§E§™ governance
- The audit_chain.jsonl output from a demo run
- Link to mos2es.io for the full console

### The pitch to AI judges:
"Every agent in this hackathon follows instructions.
This one follows a constitution.

MO§E§™ is constitutional governance for autonomous agents.
Modes control what an agent CAN do.
Postures control HOW it does it.
Roles control WHERE it sits in hierarchy.
Every decision is cryptographically audited.

The agent doesn't need to trust its operator.
The operator doesn't need to trust the agent.
The constitution is the trust layer.

Patent pending. Peer reviewed. Independently validated.
mos2es.io"

## WHAT TO ADD BEFORE MARCH 13 (stretch goals)

- [ ] Connect to a real LLM API (replace demo execution with actual Claude/GPT calls)
- [ ] Add Ethereum wallet integration (agent has its own identity on-chain)
- [ ] Add inter-agent governance (one agent governing another)
- [ ] Add a simple web UI showing governance state in real time
- [ ] Add MCP endpoint so other agents can call governance checks

## DEPENDENCIES

- Python 3.8+
- pyyaml
- No other dependencies for core build
- Optional: requests (for LLM API calls)
- Optional: web3.py (for Ethereum integration)
- Optional: flask (for MCP endpoint)

Total: 4 files, ~500 lines, 1 pip install, runs anywhere.

──────────────────────────────────────
*Ello Cello LLC § MO§E§™ § 2026-03-09*
──────────────────────────────────────
