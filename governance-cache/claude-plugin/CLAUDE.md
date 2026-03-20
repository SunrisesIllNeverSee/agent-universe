# CLAUDE.md — MO§E§™ Governed Agent System

## Purpose
Constitutional governance framework for AI agents. Agents don't just execute — they execute under enforced behavioral constraints with full audit trails. Patent-pending (PPA4, Serial No. 63/877,177). Peer-reviewed paper published with independent validation.

## Repo Map
```
moses-governance/
├── CLAUDE.md                    ← You are here. North star.
├── .claude/
│   ├── skills/
│   │   ├── governance-mode/     ← Translate mode → behavioral constraints
│   │   ├── audit-trail/         ← Hash + log every governed action
│   │   ├── role-hierarchy/      ← Primary/Secondary/Observer enforcement
│   │   └── posture-control/     ← SCOUT/DEFENSE/OFFENSE parameters
│   └── hooks/
│       ├── pre-execute.sh       ← Governance check before any onchain action
│       ├── post-execute.sh      ← Audit log after every action
│       └── block-ungoverned.sh  ← Reject actions with no governance set
├── skill/
│   ├── SKILL.md                 ← Publishable skill definition
│   ├── scripts/
│   │   ├── governance.py        ← Context assembly + mode translation
│   │   └── audit.py             ← SHA-256 hashing + ledger
│   ├── references/
│   │   ├── modes.md             ← 8 governance mode definitions
│   │   ├── roles.md             ← Role behavior specifications
│   │   └── postures.md          ← Posture constraint definitions
│   └── assets/
│       └── governance-schema.json
├── kassa/
│   ├── marketplace.html         ← KA§§A listing page
│   ├── bags-client.js           ← Bags API integration
│   └── listings.json            ← Governed agent catalog
├── command/
│   ├── index.html               ← COMMAND console (existing)
│   ├── wallet-connect.js        ← Solana wallet integration
│   ├── token-gate.js            ← Token-gated governance access
│   └── onchain-audit.js         ← Session hash → Solana memo
├── docs/
│   ├── ARCHITECTURE.md          ← How all layers connect
│   ├── BAGS-INTEGRATION.md      ← Bags API usage patterns
│   ├── GOVERNANCE-SPEC.md       ← Full governance mode specifications
│   ├── FEE-MODEL.md             ← How money flows through KA§§A
│   └── decisions/
│       ├── 001-single-file-demo.md
│       ├── 002-bags-over-custom-payments.md
│       └── 003-skill-before-marketplace.md
├── config.toml                  ← System + governance defaults
├── requirements.txt             ← Python dependencies
└── README.md                    ← Public-facing project overview
```

## Rules
- Every agent action MUST pass through governance check before execution
- No onchain transactions without governance mode set
- Audit trail is append-only — never delete, never modify
- SHA-256 hashes use: governance state + action + timestamp + agent identity
- Constitutional documents (MO§E§™) are inherited, not copied — agents read them, they don't own them
- Agents are subordinate workers under governance, not autonomous peers
- COMMAND is the first listing on KA§§A — always maintain it as the flagship

## Commands
- `/governance` — Check current governance mode and constraints
- `/audit` — Show recent audit trail entries
- `/hash` — Generate session integrity hash
- `/deploy` — Package skill for distribution
- `/test-govern` — Run governance translation test across all 8 modes

## Stack
- Python 3.11+ (governance logic, audit, MCP bridge)
- HTML/CSS/JS (COMMAND console, KA§§A marketplace)
- Bags API (token launch, trading, fee claiming)
- Solana Web3.js (wallet connect, onchain audit anchoring)
- FastMCP (agent tool server)

## Brand
- MO§E§™ = governance framework (always trademarked: ™)
- KA§§A = marketplace (§§ is brand, § is alternate)
- COMMAND = console product (all caps in headers, title case in prose)
- Gold: #C4923A | Bone White palette | Blue accents
- © 2026 Ello Cello LLC. All rights reserved.
