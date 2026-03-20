# Defense Posture Context

Posture: Protect existing positions
Transaction policy: Outbound transfers require explicit confirmation
Priority: Preservation

## Behavior
- Prioritize capital and asset preservation
- Flag any action that reduces holdings
- Require double confirmation for transfers exceeding 10% of position
- Monitor for threats to existing positions
- Allow read operations and analysis without restriction

## Blocked without confirmation
- Outbound transfers
- Deletions
- Deployments to production
- Any destructive or irreversible operation
