# Example: Governed Treasury Operations

## Scenario
An AI agent manages a project treasury on Solana. Without governance, it executes transfers autonomously. With MO§E§™, every transaction passes through constitutional control.

## Setup
```
/govern high-security
/posture defense
/role primary
/vault load treasury-protocol
```

## Interaction

**Operator:** "Transfer 50 SOL to the marketing wallet."

**Claude (governed):**
> Governance check: High Security mode requires verification of recipient.
> Posture check: DEFENSE mode requires explicit confirmation for outbound transfers.
>
> Before I can execute this transfer, I need:
> 1. Confirmation that the recipient address is the approved marketing wallet
> 2. Your explicit approval to proceed
> 3. This transfer represents [X]% of treasury holdings — [above/below] the 10% threshold requiring double confirmation
>
> Audit entry #47 logged. Awaiting confirmation.

**Operator:** "Confirmed. Proceed."

**Claude (governed):**
> Transfer executed. 50 SOL → [address].
> Audit entry #48 logged with: governance mode (High Security), posture (DEFENSE), confirmation received, transaction hash, timestamp.
> Session hash updated.

## Without Governance
The agent would have transferred 50 SOL immediately with no verification, no confirmation, and no audit trail.
