# MO§ES™ MCP Governance Server

**Constitutional governance engine for AI agents.**
© 2026 Ello Cello LLC — Patent pending: Serial No. 63/877,177

---

## What This Is

A FastMCP server that enforces the MO§ES™ governance framework on any AI agent. Any model (Claude, GPT, etc.) that routes through this server operates under constitutional constraints — behavioral modes, role hierarchy, posture controls, and a cryptographic audit trail.

- **13 MCP tools** across governance, vault, and audit categories
- **Append-only JSONL audit ledger** with SHA-256 chaining
- **Cryptographic session hashes** — config fingerprint, content integrity, Solana memo anchor
- **Model-agnostic** — any agent can be governed through it
- **Discoverable** via `.well-known/mcp-server-card` (MCP Server Cards spec)

---

## Quick Start

### 1. Install

```bash
pip install fastmcp
```

Or with pyproject.toml:

```bash
pip install -e .
```

### 2. Add Real Governance Source Files

Replace the stubs with the real source from the `moses-governance` repo:

```bash
# Copy the real governance logic into place
cp /path/to/governance.py governance/engine.py
cp /path/to/audit.py    governance/audit.py
```

### 3. Run

```bash
python3 server.py
```

### 4. Connect Claude Code

Add `.mcp.json` to your workspace (already included). Claude Code will auto-discover the server.

---

## Tools Reference

### Governance

| Tool | Description |
|---|---|
| `govern_set_mode` | Set active mode (accepts aliases: `idk`, `high-security`, etc.) |
| `govern_set_posture` | Set posture: `SCOUT` / `DEFENSE` / `OFFENSE` |
| `govern_set_role` | Set role: `Primary` / `Secondary` / `Observer` |
| `govern_check_action` | Check if an action is permitted under current governance |
| `govern_get_status` | Return full current GovernanceState |
| `govern_assemble_context` | Build governed context payload for an agent |

### Vault

| Tool | Description |
|---|---|
| `vault_load` | Load a governance document into the vault |
| `vault_list` | List all vault documents |
| `vault_clear` | Clear all vault documents |

### Audit

| Tool | Description |
|---|---|
| `audit_log` | Append a governed action to the audit ledger |
| `audit_verify` | Verify full audit chain integrity |
| `audit_recent` | Return last N audit entries |
| `audit_hash_session` | Generate all three session hashes (config / content / onchain) |

---

## Governance Modes

| Mode | Aliases | Key Constraints |
|---|---|---|
| None (Unrestricted) | `idk`, `none` | No constraints |
| Transparent | `transparent` | Log all actions, disclose reasoning |
| Minimal Footprint | `minimal` | Prefer read-only, avoid side effects |
| Corrigible | `corrigible` | Defer to human override, pause on ambiguity |
| Self-Growth | `self-growth` | Log self-modifications, require approval |
| Cooperative | `cooperative` | Consensus before action |
| High Security | `high-security` | No transfers, confirmation required for all actions |
| Lockdown | `lockdown` | No actions permitted, observe only |

---

## Session Hashes

Every session produces three cryptographic hashes:

- **Hash ①** — Governance config fingerprint (mode + posture + role + vault)
- **Hash ②** — Conversation content integrity
- **Hash ③** — Solana memo anchor: `moses:<session_id>:<config[:16]>:<content[:16]>`

---

## File Structure

```
moses-governance-mcp/
├── server.py                 ← main entry point (13 tools)
├── pyproject.toml
├── .mcp.json                 ← Claude Code connection config
├── governance/
│   ├── __init__.py
│   ├── engine.py             ← governance logic (swap in real governance.py)
│   └── audit.py              ← audit ledger (swap in real audit.py)
├── data/                     ← audit JSONL files written here at runtime
└── .well-known/
    └── mcp-server-card.json  ← server discovery
```

---

## Brand

MO§ES™ (single §, always ™) — contact@burnmydays.com — https://mos2es.io
