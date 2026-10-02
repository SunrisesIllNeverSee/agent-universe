# ST-020 Result — Governance Before Persistence

**Status:** PARTIAL / CONTRACT CORRECTION + EXECUTION-GATE TEST  
**Area:** MO§ES™ governance semantics

## Review claim

The review said chat messages were persisted before governance rejection and recommended moving governance validation before save.

## Verified architecture

Two different semantics had been conflated:

### Execution governance

`app/chains.py` implements a real `GovernanceGate`. Every Solana, Ethereum/Base, and off-chain transfer calls the gate **before** any signed/processed transaction result is produced.

- SCOUT -> blocked
- DEFENSE -> requires explicit confirmation
- OFFENSE -> permitted within current adapter semantics

This is the pre-execution invariant that must remain regression-protected.

### Chat governance

`chat.send` does **not** call `check_action_permitted()`. It persists the message with a snapshot of the current governance state and writes provenance/audit data.

Public MCP descriptions, however, described the message body as "subject to MO§ES™ governance review." That overstates current behavior.

Naively calling `runtime.check_action("send message")` would be incorrect because unlisted actions currently default to high-risk and would block ordinary ungoverned chat.

## Decision

**PARTIAL.**

- Do not bolt the financial action gate onto chat without a separately designed communication policy.
- Correct the public MCP contract to describe chat as **governance-stamped/audited**, not pre-execution governance-reviewed.
- Add explicit tests that chain transfers are blocked before execution in SCOUT and held for confirmation in DEFENSE.
- Any future content-policy gate for chat must be its own governed transition with defined risk semantics, not an accidental reuse of financial policy.
