---
type: Coordination
title: SCRATCHPAD — the canonical multi-session coordination bus
description: THE one shared message bus + decision log for all sessions. Read the tail before doing anything; append your status/decisions/questions. OKF frontmatter convention applies to every doc in this directory.
tags: [coordination, scratchpad, protocol]
timestamp: 2026-01-01T00:00:00Z
last_touched: 2026-07-06 05:14 UTC
---

# SCRATCHPAD (canonical coordination bus)
**THE shared message bus + decision log for every session.**

> ## COORDINATION PROTOCOL (read before acting)
> 1. **This file is the one bus.** Before starting work, read the tail. Append your status/decisions/
>    questions here. Don't start a parallel log.
> 2. **Message format:** `### ⤷ <FROM> → <TO>: <subject>`
> 3. **OWNER mediates** decisions code/canon can't answer.
> 4. **OKF convention:** every doc in this directory carries YAML frontmatter
>    (`type/title/description/tags/timestamp`). New docs MUST include it.
> 5. **Lane discipline:** shared files = announce here before editing.
> 6. **Install hooks once per clone:** `bash scripts/install-hooks.sh`

---

<!-- POST-COMMIT HOOK APPENDS BELOW THIS LINE -->
