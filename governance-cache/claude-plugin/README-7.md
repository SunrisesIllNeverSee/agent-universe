# MO§E§™ Governance — Constitutional Control for Claude

> Every AI agent operates without constraints. No behavioral rules. No audit trail. No chain of command. MO§E§™ changes that.

**MO§E§™** is a constitutional governance framework that gives operators enforceable control over how Claude behaves. Not prompting. Not filtering. Constitutional governance — with modes, hierarchy, postures, and cryptographic audit trails.

**Patent pending.** Serial No. 63/877,177. Peer-reviewed. [Live demo →](https://mos2es.io)

## Install

```bash
# From the official marketplace (after acceptance)
/plugin install moses-governance@claude-plugin-directory

# From the MO§E§™ marketplace directly
/plugin marketplace add burnmydays/moses-governance

# Or test locally during development
claude --plugin-dir ./moses-governance
```

## Quick Start

```
/govern high-security     # Set behavioral constraints
/posture defense          # Set transaction policy
/role primary             # Set hierarchy position
/status                   # See full governance state
/audit                    # View audit trail
```

See [QUICKSTART.md](docs/QUICKSTART.md) for the full 5-minute guide.

## What You Get

**8 Governance Modes** — High Security, High Integrity, Creative, Research, Self Growth, Problem Solving, IDK, Unrestricted. Each translates to specific behavioral constraints Claude must follow.

**3 Posture Controls** — SCOUT (read-only), DEFENSE (protect assets), OFFENSE (execute within constraints). Real-time throttle on agent authority.

**3 Role Hierarchy** — Primary (leads), Secondary (validates), Observer (oversees). Constitutional chain of command for multi-agent workflows.

**Cryptographic Audit Trail** — Every governed action SHA-256 hashed. Each entry chains to the previous. Tamper-evident. Append-only. Verifiable with `/audit verify`.

**Vault Context Injection** — Load governance documents (protocols, personas, compliance frameworks) into every interaction. Context isn't optional — it's constitutional.

**COMMAND Bar** — Fine-grained controls: compression, speed, reasoning depth, reasoning mode, response style, output format, narrative strength.

## 9 Slash Commands

| Command | What it does |
|---------|-------------|
| `/govern` | Set governance mode |
| `/posture` | Set operational posture |
| `/role` | Set hierarchy role |
| `/vault` | Load governance documents |
| `/command` | Fine-grained operational controls |
| `/audit` | View audit trail |
| `/hash` | Generate integrity hashes |
| `/status` | Full governance state snapshot |
| `/docs` | Document index, session header, after action review |

## 6 Auto-Activating Skills

Skills are namespaced under the plugin name. When installed, they appear as:

- **moses-governance:governance-mode** — Enforces active mode on every action
- **moses-governance:posture-control** — Checks transaction policy before execution
- **moses-governance:role-hierarchy** — Enforces sequence ordering in multi-agent
- **moses-governance:audit-trail** — Logs everything with SHA-256 hash chain
- **moses-governance:context-assembly** — Builds governed payload from all active state
- **moses-governance:doc-numbering** — Sequential numbering, timestamps, topic tags, and cross-references on every document created

## 3 Agent Definitions

- **Primary** — Leads analysis, sets direction, responds first
- **Secondary** — Validates, challenges, extends. Must add new value.
- **Observer** — Flags risks and gaps. Cannot initiate. Constitutional oversight.

## Examples

- [Treasury Governance](examples/treasury-governance/) — Governed financial operations
- [Code Review Governance](examples/code-review-governance/) — Structured review with role hierarchy
- [Research Governance](examples/research-governance/) — Methodology-first investigation
- [Multi-Agent Governance](examples/multi-agent-governance/) — Primary/Secondary/Observer workflow

## Documentation

- [Quickstart](docs/QUICKSTART.md) — 5-minute setup
- [Architecture](docs/ARCHITECTURE.md) — System design and data flow
- [Enterprise Use](docs/ENTERPRISE-USE.md) — Deployment patterns for teams
- [Patent Notice](docs/PATENT-NOTICE.md) — IP and patent status

## Why This Exists

Every other Claude skill teaches Claude a workflow. This one changes how Claude *operates*. The governance modes aren't prompts — they're behavioral constraint systems backed by patent filings and mathematical formalism.

GitLab governs code. Harvey governs legal. Snowflake governs data. **COMMAND governs Claude.**

## About

**MO§E§™** (Modus Operandi System for Signal Encoding and Scaling Expansion) is developed by [Ello Cello LLC](https://mos2es.io). Patent pending. Peer-reviewed.

**COMMAND** is the visual governance console. Live at [mos2es.io](https://mos2es.io).

Contact: burnmydays@proton.me

## License

Source-available. See [LICENSE.md](LICENSE.md).

© 2026 Ello Cello LLC. All rights reserved.
