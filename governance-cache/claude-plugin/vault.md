---
description: Load governance documents into active context. Documents are injected into all subsequent Claude interactions.
argument-hint: [list|load name|unload name|active]
---

# /vault

Manage vault documents. Action: "$ARGUMENTS". If empty, show currently loaded documents.

## Usage

```
/vault list                        # show available documents by category
/vault load security-protocol      # load a document into active context
/vault unload security-protocol    # remove from active context
/vault active                      # show currently loaded documents
```

## Document Categories

- **Protocol** — Operational rules, compliance frameworks, security procedures
- **Persona** — Behavioral voice, character, communication style
- **Prompt** — Pre-built query templates, analysis frameworks
- **Personal** — Individual preferences and context
- **Professional** — Role-specific workflows and standards
- **Business** — Organizational policies, brand guidelines, domain knowledge

## Behavior

Loaded vault documents become part of the governed context. Every agent interaction includes the active vault content. Loading and unloading events are logged to the audit trail.
