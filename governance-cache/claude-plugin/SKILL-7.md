---
name: context-assembly
description: "Core MO§E§™ engine. Assembles the full governed context payload from active mode + posture + role + vault documents + user profile + conversation history. This is the constitutional intelligence layer. Use when: any governed interaction is occurring, any agent reads context, any response is being generated under governance."
origin: MO§E§™
---

# Context Assembly — The Core

This is the central intelligence of MO§E§™. Every other skill feeds into this one.

## What It Does

When an agent needs to respond under governance, Context Assembly reads all active state and builds a single governed payload:

1. **Governance Mode** → translated to behavioral constraints via `scripts/governance.py`
2. **Posture** → translated to transaction policy and action scope
3. **Role** → translated to authority level and behavioral instruction
4. **Vault Documents** → loaded into context by category
5. **User Profile** → expertise level, domain, communication preference, goal
6. **COMMAND Bar Settings** → compression, speed, reasoning depth/mode, style, format
7. **Conversation History** → messages with governance metadata stamps
8. **Prior Responses** → (for Secondary/Observer) previous agent outputs to build on

## The Output

A single governed context object (see `assets/governance-schema.json` for full schema) that defines:
- What Claude must do (mode constraints)
- What Claude must not do (mode prohibitions)
- How Claude should prioritize (mode priority)
- What Claude can execute (posture policy)
- Where Claude sits in hierarchy (role assignment)
- What documents inform the response (vault context)
- How Claude should communicate (profile + COMMAND bar)

## Why This Matters

Without Context Assembly, governance is just a label. With it, governance is a structured payload that shapes every word Claude generates. This is the difference between "Claude, be careful" and "Claude, here are your constitutional constraints, your role, your posture, your loaded protocols, and your audit obligations."

The implementation is in `scripts/governance.py` — specifically the `assemble_context()` function.
