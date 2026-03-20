---
description: Show document index for current thread, or produce the After Action Review. Tracks all sequentially numbered documents created in the conversation.
argument-hint: [next|aar|header]
---

# /docs

Document management action: "$ARGUMENTS". If empty, show current document index.

## Usage

```
/docs              # show current document index (all docs created this thread)
/docs next         # show what the next doc number will be
/docs aar          # produce the After Action Review (final doc)
/docs header       # produce the Session Header (first doc, if not yet created)
```

## Behavior

- `/docs` lists every document created in the thread with number, name, topic, and timestamp
- `/docs aar` generates the After Action Review with full document index, pivots, accomplishments, and carry-forward items
- The numbering system is automatic — this command is for visibility and manual control
