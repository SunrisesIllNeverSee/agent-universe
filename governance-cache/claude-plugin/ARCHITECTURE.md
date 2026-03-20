# Architecture — MO§E§™ Governance Plugin

## Design Principle

Governance and execution are woven together, not layered. Every component has both a governance dimension and an execution dimension.

## Components

**Context Assembler** (`scripts/governance.py`) — The core. Reads mode + posture + vault + profile + messages and builds the governed payload agents receive. This is where governance becomes behavior.

**Audit Spine** (`scripts/audit.py`) — Runs through everything. Every state change, every message, every config change is hashed and logged to an append-only chain.

**Governance Modes** (`references/modes.md`) — 8 modes, each translating to specific behavioral constraints and prohibitions. Modes set the rules.

**Posture Controls** (`references/postures.md`) — 3 postures controlling transaction policy and action scope. Postures set the throttle.

**Role Hierarchy** (`references/roles.md`) — 3 roles with enforced sequence ordering. Roles set the chain of command.

**Slash Commands** (`commands/`) — 8 commands giving operators real-time governance control. The interface.

**Auto-Activating Skills** (`skills/`) — 5 skills that enforce governance on every action without the operator needing to invoke them. The enforcement layer.

**Agent Definitions** (`agents/`) — 3 agent configurations for Primary, Secondary, and Observer roles. The hierarchy.

**Hooks** (`hooks/`) — Pre-execute blocks ungoverned actions. Post-execute logs everything. The guardrails.

## Data Flow

```
Operator sets governance → /govern, /posture, /role, /vault, /command
         ↓
State stored in memory/file
         ↓
On any action → governance-mode skill checks constraints
         ↓
On any execution → posture-control skill checks transaction policy
         ↓
Context Assembler builds governed payload
         ↓
Claude operates within constitutional constraints
         ↓
Audit Spine logs action + governance state + SHA-256 hash
         ↓
Chain links to previous hash → tamper-evident trail
```

## Schema

See `assets/governance-schema.json` for the complete governed context payload specification.
