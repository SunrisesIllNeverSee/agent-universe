---
description: Load a governance document into active context. Rules in the document apply to all subsequent responses this session.
argument-hint: [document-name or paste content]
---

# /vault

Load a governance document into the active session context.

If a document name is given but no content is visible, ask the user to paste or share it.

If content is provided (pasted in this message or earlier in the conversation):

```
✓ Vault loaded: [DOCUMENT NAME]
Key rules active:
  • [rule 1]
  • [rule 2]
  • [rule 3]
Document governance applied to this session.
```

Apply all rules from the document to every subsequent response. If multiple documents conflict, flag the conflict and ask which takes precedence.
