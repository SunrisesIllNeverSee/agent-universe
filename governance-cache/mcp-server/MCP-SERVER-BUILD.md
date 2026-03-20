# CLAUDE.md — MO§ES™ MCP Server Build
## Session Brief for: claude cowork
## Date: 2026-03-11

---

## What We Are Building

A **standalone FastMCP server** that is the enforcement engine for MO§ES™ — a constitutional governance framework for AI agents.

This is NOT a tutorial project. This is production-grade infrastructure that will:
- Be discoverable via `.well-known/mcp-server-card` (MCP Server Cards spec, coming)
- Serve as the reference implementation for the MCP Enterprise WG audit trail SEP
- Power the COMMAND governance console at mos2es.io
- Be model-agnostic — any agent (Claude, GPT, etc.) can be governed through it

**Patent pending: Serial No. 63/877,177 | © 2026 Ello Cello LLC**

---

## Source Code — Build From This

The governance logic already exists. Import it. Do not rewrite it.

**governance.py** — available at: `https://github.com/SunrisesIllNeverSee/moses-governance/blob/main/scripts/governance.py`

Key items:
- `MODES` — 8 governance modes with constraints[], prohibited[], priority
- `POSTURES` — 3 postures (SCOUT/DEFENSE/OFFENSE)
- `ROLES` — 3 roles (Primary/Secondary/Observer)
- `GovernanceState` — dataclass holding full session governance config
- `assemble_context(governance, messages, agent_name, previous_responses)` — core IP, builds governed payload
- `check_action_permitted(action_description, governance)` — rule-driven enforcement, returns permitted/blocked + triggered_rules + conditions
- `translate_mode(mode)`, `translate_posture(posture)`, `get_role_instruction(role)`
- `resolve_mode(mode_input)` — handles aliases (idk, high-security, etc.)

**audit.py** — available at: `https://github.com/SunrisesIllNeverSee/moses-governance/blob/main/scripts/audit.py`

Key items:
- `AuditLedger` — append-only JSONL, SHA-256 chained entries
- `log_action(component, action, detail, governance_mode, posture, role, agent)`
- `verify_integrity()` — walks full chain
- `hash_governance_state(mode, posture, role, vault_docs, systems)` — Session Hash ①
- `hash_conversation(messages)` — Session Hash ②
- `format_for_onchain(config_hash, content_hash, session_id)` — Session Hash ③ for Solana memo

---

## Tech Stack

- **Python 3.11+**
- **FastMCP** — `pip install fastmcp`
- **Transport:** Streamable HTTP (production) + stdio (local dev/Claude Code)
- **State:** In-memory GovernanceState per session + persistent JSONL audit ledger
- **No database** — file-based, append-only

---

## MCP Server: Tools to Expose

Build these tools exactly. Names are the contract.

### Governance Tools

```python
@mcp.tool()
def govern_set_mode(mode: str) -> dict:
    """
    Set the active governance mode.
    Accepts canonical names or aliases (idk, high-security, self-growth, etc.)
    Updates in-memory GovernanceState and writes governance_state.json.
    Returns: {"mode": canonical_name, "constraints": [...], "prohibited": [...]}
    """

@mcp.tool()
def govern_set_posture(posture: str) -> dict:
    """
    Set operational posture: SCOUT | DEFENSE | OFFENSE.
    SCOUT = read-only, no state changes.
    DEFENSE = protect assets, outbound requires confirmation.
    OFFENSE = execute within governance constraints.
    Returns: {"posture": str, "behavior": str, "transaction_policy": str}
    """

@mcp.tool()
def govern_set_role(role: str) -> dict:
    """
    Set hierarchy role: Primary | Secondary | Observer.
    Primary leads. Secondary validates. Observer flags only.
    Returns: {"role": str, "authority": str, "instruction": str, "constraints": [...]}
    """

@mcp.tool()
def govern_check_action(action_description: str) -> dict:
    """
    Check if a proposed action is permitted under current governance.
    Uses concept extraction + rule-driven evaluation against active mode's prohibited list.
    Returns: {"permitted": bool, "reason": str, "triggered_rules": [...], "conditions": [...]}
    """

@mcp.tool()
def govern_get_status() -> dict:
    """
    Return full current GovernanceState.
    Returns: {"mode": str, "posture": str, "role": str, "vault_documents": [...], ...all fields}
    """

@mcp.tool()
def govern_assemble_context(messages: list[dict], agent_name: str = "agent", previous_responses: list[dict] | None = None) -> dict:
    """
    Build the full governed context payload for an agent.
    This is the core IP — every agent read passes through here.
    Returns full governed payload: constitutional_governance, role_assignment,
    user_profile, vault_context, messages, [prior_responses if Secondary/Observer]
    """
```

### Vault Tools

```python
@mcp.tool()
def vault_load(name: str, content: str, category: str = "general") -> dict:
    """
    Load a governance document into the active vault.
    Injected into every governed context via assemble_context().
    Returns: {"loaded": name, "vault_count": int}
    """

@mcp.tool()
def vault_list() -> dict:
    """
    List all documents currently in the vault.
    Returns: {"documents": [{"name": str, "category": str}]}
    """

@mcp.tool()
def vault_clear() -> dict:
    """
    Clear all documents from the vault.
    Returns: {"cleared": int}
    """
```

### Audit Tools

```python
@mcp.tool()
def audit_log(component: str, action: str, detail: dict, agent: str = "") -> dict:
    """
    Append a governed action to the audit ledger.
    Automatically captures active mode/posture/role from GovernanceState.
    Returns: {"id": int, "hash": str, "iso_time": str}
    """

@mcp.tool()
def audit_verify() -> dict:
    """
    Verify the entire audit chain integrity.
    Returns: {"valid": bool, "entries_checked": int, "first_failure": int | None}
    """

@mcp.tool()
def audit_recent(n: int = 10) -> dict:
    """
    Return the last N audit entries.
    Returns: {"entries": [...], "count": int}
    """

@mcp.tool()
def audit_hash_session(messages: list[dict]) -> dict:
    """
    Generate all three session hashes.
    ① Config fingerprint (governance state)
    ② Content integrity (conversation)
    ③ Onchain anchor (Solana memo format)
    Returns: {"hash_config": str, "hash_content": str, "hash_onchain": str}
    """
```

---

## Session State Architecture

Each MCP session gets its own `GovernanceState` instance. The server holds a dict of sessions.

```python
# Session management
_sessions: dict[str, GovernanceState] = {}
_ledgers: dict[str, AuditLedger] = {}

def _get_session(session_id: str) -> GovernanceState:
    if session_id not in _sessions:
        _sessions[session_id] = GovernanceState()  # defaults: unrestricted, SCOUT, Primary
    return _sessions[session_id]
```

Session ID should come from MCP context (ctx.session_id if available, else a header, else default).

Default state on new session: `mode="None (Unrestricted)", posture="SCOUT", role="Primary"`

---

## File Structure (Target)

```
moses-governance-mcp/
├── CLAUDE.md                 ← this file
├── README.md                 ← installation + usage
├── pyproject.toml            ← FastMCP dependency
├── server.py                 ← main entry point
├── governance/
│   ├── __init__.py
│   ├── engine.py             ← copy of governance.py (import from source)
│   └── audit.py              ← copy of audit.py (import from source)
├── data/
│   └── .gitkeep              ← audit ledgers written here at runtime
├── .well-known/
│   └── mcp-server-card.json  ← server discovery (MCP Server Cards spec)
└── .mcp.json                 ← local Claude Code connection config
```

---

## server.py Structure

```python
from fastmcp import FastMCP, Context
from governance.engine import (
    GovernanceState, translate_mode, translate_posture,
    get_role_instruction, assemble_context, check_action_permitted,
    resolve_mode, MODES, POSTURES, ROLES
)
from governance.audit import AuditLedger, hash_governance_state, hash_conversation, format_for_onchain

mcp = FastMCP(
    name="moses-governance",
    version="1.1.0",
    description="Constitutional governance engine for AI agents — MO§ES™",
)

# Session state
_sessions: dict[str, GovernanceState] = {}
_ledgers: dict[str, AuditLedger] = {}

# ... all tools defined here

if __name__ == "__main__":
    mcp.run()  # stdio for Claude Code local dev
```

---

## .mcp.json (for Claude Code connection)

```json
{
  "mcpServers": {
    "moses-governance": {
      "command": "python3",
      "args": ["server.py"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

---

## MCP Server Card (.well-known/mcp-server-card.json)

```json
{
  "name": "moses-governance",
  "version": "1.1.0",
  "description": "Constitutional governance engine for AI agents. Enforces behavioral modes, role hierarchy, posture controls, and cryptographic audit trails.",
  "vendor": "Ello Cello LLC",
  "homepage": "https://mos2es.io",
  "repository": "https://github.com/SunrisesIllNeverSee/moses-governance-mcp",
  "capabilities": {
    "tools": true,
    "resources": false,
    "prompts": false
  },
  "tools": [
    "govern_set_mode", "govern_set_posture", "govern_set_role",
    "govern_check_action", "govern_get_status", "govern_assemble_context",
    "vault_load", "vault_list", "vault_clear",
    "audit_log", "audit_verify", "audit_recent", "audit_hash_session"
  ],
  "categories": ["governance", "enterprise", "security", "audit"],
  "license": "Proprietary",
  "contact": "contact@burnmydays.com"
}
```

---

## What "Done" Looks Like

1. `python3 server.py` starts with no errors
2. All 13 tools are registered and callable
3. `govern_set_mode("high-security")` → returns correct constraints
4. `govern_check_action("transfer 50 SOL")` in High Security + SCOUT → returns BLOCKED + triggered rule
5. `audit_log(...)` → appends to JSONL, returns hash
6. `audit_verify()` → returns valid: true on clean chain
7. `govern_assemble_context([...])` → returns full governed payload with constitutional_governance, role_assignment, vault_context
8. `.mcp.json` connects Claude Code to the running server

---

## What NOT to Do

- Do not rewrite governance.py or audit.py logic — import it
- Do not add a database — JSONL only
- Do not add auth — that's v1.2 (MCP Enterprise WG will define the standard)
- Do not add HTTP transport yet — stdio first, Streamable HTTP in v1.2 when the MCP Transports WG finalizes it
- Do not over-engineer session management — dict in memory is correct for now

---

## Brand

- MO§ES™ (single §, always ™)
- © 2026 Ello Cello LLC
- contact@burnmydays.com
- Patent pending: Serial No. 63/877,177
