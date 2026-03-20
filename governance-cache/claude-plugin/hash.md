---
description: Generate session integrity hashes for governance state and conversation content. SHA-256 cryptographic verification.
argument-hint: [config|content|full]
---

# /hash

Generate integrity hash. Type: "$ARGUMENTS". If empty, show all current hashes.

## Usage

```
/hash config     # SHA-256 of governance state (mode + posture + role + vault + systems)
/hash content    # SHA-256 of conversation content (all messages in order)
/hash full       # both hashes + formatted for onchain anchoring
/hash            # show all current hashes
```

## Hash Types

- **Config Fingerprint (①)** — Hash of the complete governance configuration. Changes when mode, posture, role, or vault changes.
- **Content Integrity (②)** — Hash of conversation content. Changes with every message.
- **Onchain Anchor (③)** — Both hashes formatted as a Solana memo string for immutable onchain proof.

## Use Cases

Compliance evidence, session verification, tamper detection, audit trail anchoring.
