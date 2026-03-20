──────────────────────────────────────
REQUIREMENTS SPEC | Document Numbering System
2026-03-07 | Thread: agentchattr comparison + hackathon + plugin build
Purpose: Save-keeping — compare what was asked vs what was built
──────────────────────────────────────

# What Luthen Asked For — Complete Record

## The Original Request (verbatim intent, paraphrased)

"I would like all created docs to be numbered sequentially 1 2 3 or I II III. Versions where applicable. And then when a doc is created later in a chat yet references an earlier doc it would be marked alphabetically ie say we are seq at doc 10 yet the next doc pertains to 1, it would be marked 1a."

"Also timestamps. Maybe in the footer or top right corner mark topic or theme, help track pivots."

"Any chance of all conversations starting with an opening doc, includes a pre-formatted header opening statement timestamp and this is a big ask table of contents that gets updated not recreated through the thread."

"Also I have somewhere a formatted after action review to be filled out when closing out full threads or pivots in a chat."

## Requirements Broken Down

### 1. Sequential Numbering
- **Asked:** Every doc numbered sequentially (1, 2, 3 or I, II, III)
- **Clarified:** Every file Claude creates, not just strategic docs
- **Scope:** Within a single conversation thread only

### 2. Cross-Reference Suffixes
- **Asked:** When doc 10 references doc 1, mark it as 1a
- **Logic:** Alphabetical suffix (a, b, c) on the parent doc's number
- **Purpose:** Track which docs relate to which without breaking sequence
- **Important clarification from Luthen:** This is for file naming/numbering only — NOT for contextually linking document content in real-time. The numbering creates order in the downloads folder. Content linking is a separate future concern.

### 3. Versioning
- **Asked:** "Versions where applicable"
- **Logic:** When a doc is directly revised, mark v2, v3
- **Distinction:** v2 = same doc updated. 1a = new doc referencing old doc.

### 4. Timestamps
- **Asked:** On every doc
- **Placement:** "Maybe in the footer or top right corner"
- **Built:** In a header block at the top of each doc

### 5. Topic / Theme Tags
- **Asked:** "Mark topic or theme, help track pivots"
- **Purpose:** When scrolling through downloads, you can see what each doc was about and where the conversation pivoted
- **Built:** In the header block alongside timestamp

### 6. Session Header (First Doc)
- **Asked:** "All conversations starting with an opening doc"
- **Contents requested:**
  - Pre-formatted header
  - Opening statement
  - Timestamp
  - Table of contents
- **Big ask flag:** TOC that gets UPDATED not RECREATED through the thread

### 7. Updating TOC (Not Recreating)
- **Asked:** TOC updates as new docs are added, not rewritten from scratch
- **Reality check built in:** In claude.ai, files can't be edited after creation. The skill notes this limitation and falls back to maintaining a running TOC that gets finalized in the AAR.

### 8. After Action Review (Final Doc)
- **Asked:** Formatted AAR template filled out when closing threads or at pivots
- **Note:** Luthen mentioned having an existing AAR template somewhere but didn't provide it in this conversation
- **Built:** Default AAR template with: accomplishments, document index, pivots, carry-forward items, key decisions
- **TODO:** Swap in Luthen's actual AAR template when located

### 9. Pivot Tracking
- **Asked:** Track when conversations change direction
- **Built:** Pivot tag in doc headers + pivot section in AAR

## What Was NOT Asked For

- Content linking between documents (explicitly clarified as out of scope)
- Cross-conversation numbering (realistic — only within threads)
- Hooks into document content (clarified as "impossible and unnecessary" for now)
- Automatic categorization or filing
- Integration with external tools or file systems

## What Was Built

### Memory Edit (#4)
```
Every document/file Claude creates in a conversation thread must be
sequentially numbered with a 3-digit prefix: 001_, 002_, 003_. If a
later doc references or extends an earlier doc, use alphabetical
suffix: 001a_, 001b_. Each doc gets a timestamp and topic/theme tag.
First doc in a thread should be a session header with updating TOC.
Final doc should be an After Action Review. Versions marked when
applicable (v2, v3).
```

**Where it fires:** Every conversation, everywhere (claude.ai, Claude Code, Cowork)
**Limitation:** Compressed to 500 chars. Carries the rule but not the detailed spec.

### Skill (doc-numbering/SKILL.md)
- Full naming format spec: `[SEQ]_[descriptive-name].[ext]`
- Cross-reference logic with examples
- Version marking rules
- Document header template with timestamp + topic + thread
- Session Header template (DOC 001) with TOC structure
- TOC update rules (update, don't recreate) with fallback for claude.ai
- After Action Review template with all sections
- Pivot tracking with header tags

**Where it fires:** Claude Code with plugin installed. Auto-activates on file creation.
**Limitation:** Only available in Claude Code. Not active in claude.ai conversations.

### Slash Command (/docs)
- `/docs` — show document index
- `/docs next` — show next doc number
- `/docs aar` — produce After Action Review
- `/docs header` — produce Session Header

**Where it fires:** Claude Code with plugin installed.

## Coverage Map

| Requirement | Memory Edit | Skill | /docs Command |
|---|---|---|---|
| Sequential numbering | ✓ core rule | ✓ full spec | ✓ shows index |
| Cross-reference suffix | ✓ core rule | ✓ full spec + examples | — |
| Versioning | ✓ mentioned | ✓ full spec | — |
| Timestamps | ✓ mentioned | ✓ header template | — |
| Topic/theme tags | ✓ mentioned | ✓ header template | ✓ shows in index |
| Session header | ✓ mentioned | ✓ full template | ✓ /docs header |
| Updating TOC | ✓ mentioned | ✓ rules + fallback | ✓ /docs shows TOC |
| After Action Review | ✓ mentioned | ✓ full template | ✓ /docs aar |
| Pivot tracking | — (not in 500 chars) | ✓ header tags + AAR | — |

## Gaps / Future Work

1. **Luthen's actual AAR template** — needs to be located and swapped in for the default
2. **Cross-conversation indexing** — Luthen mentioned building an index of chats separately; this system handles within-thread only
3. **Content linking** — explicitly deferred. The numbering creates filing order. Content relationships are a separate system.
4. **Claude.ai TOC updating** — limited by platform (can't edit files after creation). Workaround: final TOC in AAR.
5. **Roman numerals (I, II, III)** — mentioned as an option but built with Arabic numerals (001, 002, 003) for file sorting. Could be added as a toggle.
