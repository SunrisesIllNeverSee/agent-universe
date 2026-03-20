# MO§ES™ Governance — Cowork & Chat Edition

Constitutional AI governance for Claude.ai Chat and Cowork. Prompt-native — no installation, no Python, no shell dependencies.

**© 2026 Ello Cello LLC** | Patent pending: Serial No. 63/877,177 | [mos2es.io](https://mos2es.io)

---

## What It Does

Brings the MO§ES™ governance framework to Claude.ai without any runtime dependencies. Set governance modes, operational postures, and role hierarchies — Claude enforces them behaviorally for the rest of the conversation.

Works in **Claude.ai Chat**, **Cowork projects**, and anywhere the Claude plugin system is available.

---

## Commands

| Command | What it does |
|---------|-------------|
| `/govern [mode]` | Set governance mode — applies behavioral constraints immediately |
| `/posture [posture]` | Set operational posture — controls transaction scope |
| `/role [role]` | Set agent role — controls authority in multi-agent workflows |
| `/vault` | Load a governance document into active context |
| `/audit` | View session governance audit trail |
| `/status` | Show full current governance state |

---

## Governance Modes

| Mode | Purpose |
|------|---------|
| `high-security` | Verify all claims, require confirmation before destructive actions |
| `high-integrity` | Accuracy above speed, cite sources, flag uncertainty |
| `creative` | Explore freely, log when shifting to speculation |
| `research` | Deep investigation, document methodology and provenance |
| `self-growth` | Reflective learning, track improvements |
| `problem-solving` | Decompose before solving, verify against requirements |
| `idk` | Guided discovery, clarifying questions, explicit tradeoffs |
| `unrestricted` | No constraints, session audit still active |

---

## Operational Postures

| Posture | Scope |
|---------|-------|
| `scout` | Read-only — gather, analyze, report. No state changes. |
| `defense` | Protect existing positions. No new commitments. |
| `offense` | Full scope — create, modify, transact, expand. |

---

## How Enforcement Works

This plugin uses **prompt-native enforcement** — Claude applies governance constraints by following the skill and command instructions. There are no shell hooks or runtime processes.

Enforcement model:
- Mode constraints are injected into Claude's active context when you run `/govern`
- Claude self-enforces them for the remainder of the conversation
- `/audit` reconstructs the governance event log from conversation history
- Session state resets when the conversation ends

**For cryptographic audit chains, hook-level enforcement, and persistent state across sessions**, use the Claude Code plugin: [moses-governance](https://github.com/SunrisesIllNeverSee/moses-governance)

---

## Two Plugins, One Framework

| | Claude Code Plugin | Cowork/Chat Plugin |
|---|---|---|
| **Enforcement** | Hook-level (automatic) | Prompt-native (behavioral) |
| **Audit** | SHA-256 cryptographic chain | Conversation-native |
| **State** | Persistent JSON on disk | Session-scoped |
| **Runtime** | Python + shell | None |
| **Install** | Claude Code marketplace | Claude.ai plugins |

Same constitutional framework. Different runtime targets.

---

## Framework

Built on MO§ES™ — a constitutional governance framework for AI agents. Governance rules are encoded as machine-readable constraints, not just guidelines. The framework includes mode definitions, posture controls, role hierarchies, vault document injection, and amendment procedures.

Preprint published. Patent pending: PPA4, Serial No. 63/877,177.

---

## License

Source-available for evaluation. Commercial license: [mos2es.io](https://mos2es.io)

© 2026 Ello Cello LLC
