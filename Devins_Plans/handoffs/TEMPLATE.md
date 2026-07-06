---
type: Runbook
title: Handoff Template — structured cross-session transfer
description: Template for structured handoffs between sessions. Copy this file, fill in the sections, and the receiving session can pick up cold without reading the entire bus.
tags: [handoff, template, coordination]
timestamp: 2026-01-01T00:00:00Z
last_touched: 2026-01-01 00:00 UTC
---

# Handoff: [TOPIC]

> Copy this file to `handoffs/{date}-{from}-to-{to}-{topic-slug}.md` and fill in.

---
from: [SESSION-ROLE]
to: [SESSION-ROLE]
when: [ISO timestamp]
topic: [what this handoff is about]
status: ready-for-pickup | in-progress | blocked | done
---

## What's done

- [List completed work with commit hashes]

## What's needed

- [List remaining work, ordered by priority]

## Pickup files

- [List the files the receiving session should read first]

## Open questions

- [List unresolved questions that need decisions]

## Authority limits

- [What the receiving session can and cannot do without checking back]
- [e.g., "Do NOT change pricing constants" or "Do NOT push without tests passing"]

## Context

- [Any background the receiving session needs to understand why this work exists]
- [Link to relevant DECISIONS.md entries, SCRATCHPAD bus messages, etc.]
