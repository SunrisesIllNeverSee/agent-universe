# COMMAND — Build Recipe

How to build the full COMMAND system from scratch, integrating everything learned from agentchattr. Each step produces something testable. Governance and execution are woven in together at every step — never bolted on after.

---

## Step 0: Prep

**Get your tools ready.**

- Python 3.11+
- Node.js (you already have this for Netlify)
- VS Code + Live Server extension
- Your current index.html (the working demo)
- A terminal

**Install once:**

```
pip install fastapi uvicorn mcp
```

That's the entire dependency list. Three packages.

**Create the project folder:**

```
command/
  index.html          ← your existing demo (copy it here)
  run.py              ← entry point
  app.py              ← server core
  store.py            ← message persistence
  context.py          ← governance assembler (YOUR IP)
  sequence.py         ← constitutional routing
  mcp_bridge.py       ← agent-facing tools
  audit.py            ← integrity spine
  vault.py            ← document engine
  config.toml         ← system configuration
  data/               ← runtime state (auto-created)
  vault/              ← governance documents
```

---

## Step 1: The Store

**Build first because everything depends on it.**

This is the simplest piece. A list of messages in memory backed by a JSONL file on disk. But from day one, every message carries governance metadata — not just text.

**What a message looks like:**

```json
{
  "id": 1,
  "sender": "user",
  "text": "analyze this dataset",
  "timestamp": "2026-03-07T14:30:00Z",
  "governance": {
    "mode": "High Security",
    "posture": "DEFENSE",
    "reasoning": "Deductive"
  },
  "vault_loaded": ["Security Protocol v3"],
  "role_context": "Primary",
  "channel": "general"
}
```

Notice: governance is baked into the message from the start. Not tagged on later. When you scroll back through history, you can see what governance was active when each message was sent. That's audit by design.

**What it does:**
- `add(sender, text, governance_state)` → saves to memory + appends to file
- `get_recent(n)` → returns last n messages
- `get_since(msg_id)` → returns messages after a given ID (for agent cursor tracking)
- Observer callback so the server knows when to broadcast

**Test it:** Write a 5-line Python script that creates a store, adds 3 messages, kills the process, restarts, and confirms the messages survived.

**Lesson from agentchattr:** His store.py is 324 lines because it handles todos, deletion, attachments, per-channel filtering, upload directories. You don't need any of that yet. ~100 lines. But his observer pattern is worth copying — it's how the store tells the server "new message arrived, broadcast it."

---

## Step 2: The Audit Spine

**Build second because it hooks into everything that follows.**

Not a monitoring layer that sits on top. A function library that every other component calls when something happens. If audit doesn't exist yet when you build the server, you'll have to retrofit it. Building it now means every component integrates it from line one.

**What it does:**
- `hash_state(config, governance, systems)` → SHA-256 fingerprint of current config (this is your Session Hash ① from the UI)
- `hash_content(messages)` → SHA-256 of conversation content (Session Hash ②)
- `log_event(component, action, detail)` → append to audit log
- `get_log(since)` → return events for the SYSTEM ACTIVITY panel

**Every component calls audit:**
- Store calls `log_event("store", "message_added", {sender, id})`
- Server calls `log_event("server", "governance_changed", {old_mode, new_mode})`
- MCP bridge calls `log_event("mcp", "agent_read", {agent, msg_count})`
- Vault calls `log_event("vault", "document_loaded", {doc_name})`
- Sequence calls `log_event("sequence", "route_decision", {from, to, reason})`

**Test it:** Add 5 messages to the store, call `hash_content()`, add a 6th, confirm the hash changes. Call `get_log()` and confirm all events are there.

**Lesson from agentchattr:** He doesn't have this. His JSONL log is message-only. No config hashing, no governance tracking, no integrity verification. This is a COMMAND-only component.

---

## Step 3: The Config

**Build the configuration file that defines your systems and defaults.**

```toml
[server]
port = 8300
host = "127.0.0.1"
data_dir = "./data"

[governance]
default_mode = "None (Unrestricted)"
default_posture = "SCOUT"
default_reasoning = "Deductive"
default_depth = "MODERATE"

[systems.claude]
provider = "Anthropic"
model = "claude-sonnet-4-20250514"
codename = "Signal Analyst"
class = "Recursive Reasoner"
role = "Primary"
color = "#da7756"

[systems.gpt]
provider = "OpenAI"
model = "gpt-4o"
codename = "Bridge Strategist"
class = "Architect-Transmitter"
role = "Secondary"
color = "#10a37f"

[sequence]
max_rounds = 4
enforce_order = true

[mcp]
port = 8200

[vault]
directory = "./vault"
```

**Lesson from agentchattr:** His config.toml is clean and simple. Steal the format. But your config has governance defaults and sequence enforcement — his doesn't.

---

## Step 4: The Server Core

**The switchboard. Every component talks through this.**

FastAPI app with two responsibilities:
1. Serve the frontend (your index.html)
2. WebSocket hub for real-time communication

**What it does:**
- Serves `index.html` at `/`
- WebSocket endpoint at `/ws` — browser connects here
- REST endpoints:
  - `GET /api/state` → returns full current state (governance, systems, vault, messages)
  - `POST /api/governance` → update governance mode/posture/profile (triggers audit log + broadcast)
  - `POST /api/vault/load` → load a vault document (triggers audit log)
  - `GET /api/audit` → returns audit log for SYSTEM ACTIVITY panel
  - `GET /api/hash` → returns current session hashes
- On new message (via store observer): broadcast to all WebSocket clients
- On governance change: broadcast to all clients + update state for MCP bridge

**The key design choice:** The server holds governance state in memory. When the frontend changes governance mode, it POSTs to the server. When the MCP bridge needs to build a governed payload, it reads from the server. Single source of truth.

**Test it:** Start the server, open browser to localhost:8300, confirm your index.html loads. Open browser console, connect WebSocket, send a message, see it echo back. Change governance mode via REST, confirm the broadcast arrives.

**Lesson from agentchattr:** His app.py is 1,842 lines because it handles everything — image uploads, todo cycling, settings persistence, channel management, hat SVGs. Your server is just the switchboard. ~300 lines.

---

## Step 5: The Frontend Wiring

**This is where your existing HTML connects to the backend.**

Your demo currently manages everything in browser memory. This step replaces local state with server communication. The UI doesn't change. The data source does.

**Changes needed (this is where I need your actual index.html to be precise):**

1. **WebSocket connection** — on page load, connect to `ws://localhost:8300/ws`. All messages flow through this instead of local arrays.

2. **Send message** — instead of pushing to a local array, send via WebSocket. Server broadcasts it back to all clients (including you).

3. **Governance changes** — when user selects a governance mode, POST to `/api/governance`. Server stores it, broadcasts the change, MCP bridge picks it up.

4. **Vault loading** — when user selects a vault document, POST to `/api/vault/load`. Server stores it in active context.

5. **System Activity** — poll `/api/audit` or receive audit events via WebSocket. Populate the SYSTEM ACTIVITY panel with real data.

6. **Session Hash** — call `/api/hash` to get real SHA-256 hashes instead of placeholder dashes.

7. **Initial load** — on page load, GET `/api/state` to hydrate the UI with current governance state, loaded vault docs, active systems, and recent messages.

**What doesn't change:** All your CSS, all your HTML structure, all your governance controls, all your COMMAND bar logic, all your vault UI, all your popup system. Those stay exactly as they are.

**Test it:** Open two browser tabs to localhost:8300. Send a message in one, see it appear in the other. Change governance mode in one, see the SYSTEM ACTIVITY log update in the other.

**Lesson from agentchattr:** His static/chat.js is 205K — that's the entire frontend logic. Massive. But the WebSocket pattern is simple: connect, listen for messages, render them. His `onmessage` handler is the pattern to follow.

---

## Step 6: The Vault Engine

**Document storage and retrieval for governance context injection.**

Your vault already exists in the UI — DOCS, ARCHIVE tabs with protocols, personas, prompts. This step gives it a backend so documents persist and can be injected into agent context.

**What it does:**
- Read vault documents from `./vault/` directory
- Categorize by type (Protocol, Persona, Prompt, Personal, Professional, Business)
- Track which documents are currently loaded/active
- When Context Assembler asks "what's loaded?", return the active docs
- Audit log every load and unload

**Directory structure:**

```
vault/
  protocols/
    security-protocol-v3.md
    audit-requirements.md
  personas/
    signal-analyst.md
    bridge-strategist.md
  prompts/
    deep-analysis.md
    adversarial-review.md
```

**Test it:** Drop a markdown file in `vault/protocols/`, call the vault engine, confirm it returns the content with the right category. Load it, confirm audit logs the event.

**Lesson from agentchattr:** He doesn't have a vault. His agents get raw chat history and that's it. This is COMMAND-only.

---

## Step 7: The Context Assembler

**THE CORE. This is the most important file in the entire system. This is your IP at the code level.**

When an agent calls `chat_read`, they don't get raw messages. They get a governed payload assembled by this component. It reads everything — governance mode, posture, user profile, vault docs, sequence position, message history — and builds the single object that defines what the agent sees and how it should behave.

**What it does:**

```python
def assemble_context(agent_name, governance, vault, messages, sequence_state):
    return {
        "constitutional_governance": {
            "mode": governance.mode,
            "mode_constraints": translate_mode(governance.mode),
            "posture": governance.posture,
            "reasoning_mode": governance.reasoning,
            "reasoning_depth": governance.depth,
            "response_style": governance.style,
            "output_format": governance.format,
            "narrative_strength": governance.narrative
        },
        "role_assignment": {
            "role": sequence_state.get_role(agent_name),
            "sequence_position": sequence_state.get_position(agent_name),
            "total_in_sequence": sequence_state.total_active(),
            "instruction": role_instruction(agent_name, sequence_state)
        },
        "user_profile": {
            "expertise": governance.expertise,
            "interaction_mode": governance.interaction_mode,
            "domain": governance.domain,
            "communication_pref": governance.comm_pref,
            "goal": governance.goal
        },
        "vault_context": [
            {"name": doc.name, "category": doc.category, "content": doc.content}
            for doc in vault.get_active()
        ],
        "messages": [
            format_message(m) for m in messages
        ]
    }
```

**The `translate_mode()` function is where governance becomes behavioral constraint:**

```python
def translate_mode(mode):
    if mode == "High Security":
        return {
            "constraints": [
                "Verify all claims before stating them",
                "Flag any data exposure risks",
                "Require explicit confirmation before destructive actions",
                "Log reasoning chain for audit"
            ],
            "prohibited": [
                "Speculative responses without evidence",
                "Accessing external resources without approval"
            ]
        }
    elif mode == "High Integrity":
        return { ... }
    elif mode == "Creative":
        return { ... }
    # ... etc
```

**The `role_instruction()` function is where hierarchy becomes behavior:**

```python
def role_instruction(agent_name, sequence):
    role = sequence.get_role(agent_name)
    pos = sequence.get_position(agent_name)
    
    if role == "Primary":
        return "You are the Primary system. Respond first. Set the analytical direction. Other systems will build on your response."
    elif role == "Secondary":
        primary_response = sequence.get_response("Primary")
        return f"You are Secondary. The Primary system has responded: [see messages]. Build on, challenge, or extend their analysis. Do not repeat."
    elif role == "Observer":
        return "You are Observer. Read all responses. Flag inconsistencies, gaps, or risks. Do not generate original analysis."
```

**Test it:** Set governance to "High Security" + "DEFENSE" posture. Load a security protocol from vault. Call `assemble_context()` for an agent named "claude" with role "Primary". Inspect the output. Confirm every governance setting is translated into behavioral constraints.

**Lesson from agentchattr:** He doesn't have this. His agents get `{"messages": [...]}`. Yours get constitutional orders. This is the 250 lines that justify everything.

---

## Step 8: The Sequence Engine

**Constitutional routing. Not @mention parsing — hierarchy enforcement.**

When a user sends a message, the sequence engine decides who responds and in what order, based on the roles and sequence set in the UI.

**What it does:**
- Track which systems are active and their roles (Primary, Secondary, Observer)
- Track sequence order (1, 2, 3...)
- When user sends a message: trigger Primary first
- When Primary responds: trigger Secondary
- When Secondary responds: trigger Observer (if Observer is set to respond, not just watch)
- Loop guard: after max_rounds, pause and wait for user
- Broadcast mode: trigger all simultaneously, collect responses in parallel

**The difference from agentchattr's router:**

His router parses @mentions from message text:
```python
# His: who did the user name?
mentions = re.findall(r"@(\w+)", text)
```

Your sequence engine reads constitutional hierarchy:
```python
# Yours: who's next in the chain of command?
next_agent = sequence.next_in_order(last_responder)
role = sequence.get_role(next_agent)
```

**Test it:** Set up three systems — Primary (Claude), Secondary (GPT), Observer (Gemini). Send a message. Confirm the engine returns Claude first, then GPT after Claude responds, then Gemini last. Confirm the loop guard fires after max_rounds.

---

## Step 9: The MCP Bridge

**Agent-facing tools. This is where agents connect.**

A FastMCP server running on port 8200. Agents connect to this and get tools they can call. The critical difference from agentchattr: every tool call runs through the Context Assembler.

**Tools:**

1. `command_read(agent_name)` — returns governed context assembled by context.py. Not raw messages.

2. `command_send(agent_name, message)` — agent posts a response. Server validates it came from the expected agent in sequence. Audit logs it.

3. `command_join(agent_name)` — agent announces presence. Server checks if this agent is in the active system list. If not configured, reject.

4. `command_status()` — returns current governance state, active systems, sequence position. Agents can check where they stand.

**The instructions string (equivalent to agentchattr's _MCP_INSTRUCTIONS):**

This is where you tell agents how to behave within COMMAND. Unlike agentchattr's generic chat instructions, yours reference governance:

```
"COMMAND — Constitutional AI Governance Console.
You are operating under governance constraints.
Every read returns your role, sequence position,
and behavioral parameters. Follow them.
Do not deviate from your assigned role.
Do not respond out of sequence unless in
broadcast mode. Your output will be audited."
```

**Test it:** Start the MCP server. Use a test script to call `command_read("claude")`. Confirm the response includes governance constraints, vault context, role assignment, and messages. This is the moment the whole system becomes real.

**Lesson from agentchattr:** His MCP bridge is 885 lines because it handles presence heartbeats, cursor persistence, identity claiming, multi-instance naming, job integration, summary management, hat assignment, channel switching. Yours is ~200 lines because the complexity lives in context.py, not in the tools.

---

## Step 10: Integration Test

**The full loop. This is the demo that sells.**

1. Start the server: `python run.py`
2. Open browser to `localhost:8300` — COMMAND loads
3. Set governance mode to "High Security"
4. Set posture to "DEFENSE"
5. Load a security protocol from vault
6. Activate Claude as Primary, GPT as Secondary
7. Set sequence: Claude → GPT
8. Send a message: "Evaluate the security implications of this API design"
9. Claude reads — gets High Security constraints, DEFENSE posture, security protocol, Primary role instruction
10. Claude responds under governance
11. GPT reads — gets same governance + Claude's response + Secondary role instruction ("build on, challenge, or extend")
12. GPT responds under governance
13. Both responses visible in COMMAND with full audit trail
14. Session hash reflects the entire governed conversation
15. SYSTEM ACTIVITY shows every event

**That's the demo. That's what nobody else has.**

---

## Build Order Summary

| Step | Component | Lines | Depends On | Test |
|------|-----------|-------|------------|------|
| 1 | store.py | ~100 | nothing | Messages survive restart |
| 2 | audit.py | ~100 | nothing | Hash changes on state change |
| 3 | config.toml | ~40 | nothing | Loads without error |
| 4 | app.py + run.py | ~350 | store, audit | Two browser tabs see same messages |
| 5 | index.html changes | ~200 | app | UI talks to server instead of local state |
| 6 | vault.py | ~150 | audit | Documents load and categorize |
| 7 | context.py | ~250 | vault, audit, store | Governed payload assembles correctly |
| 8 | sequence.py | ~120 | audit | Primary→Secondary→Observer fires in order |
| 9 | mcp_bridge.py | ~200 | context, sequence, store, audit | Agent reads return governed context |
| 10 | Integration | — | everything | Full governed loop runs end to end |

**Total: ~1,510 lines of new code across 8 files + 200 lines of changes to existing HTML.**

---

## What You Can Skip From agentchattr

Things he built that you don't need:

- **Terminal injection wrappers** (wrapper.py, wrapper_windows.py, wrapper_unix.py) — 800+ lines of keystroke injection. Only needed for auto-waking CLI agents. Not needed for demo.
- **Multi-instance naming** (registry.py) — 600 lines. You control which systems are active via the UI. No need for auto-naming claude-1, claude-2.
- **Channel system** — You have broadcast mode instead. Simpler, more governed.
- **Todo/pin system** — Your audit log covers this.
- **Image sharing** — Not relevant to governance demo.
- **Voice input** — Nice to have, not needed.
- **Hat SVGs** — Cosmetic.
- **Summary system** — Your vault + context assembler handles this better.

## What You Should Take From agentchattr

Patterns worth copying:

- **Observer callback pattern** (store.py) — how the store notifies the server of new messages
- **FastMCP server setup** (mcp_bridge.py lines 856-883) — 30 lines to create an MCP server, that's it
- **TOML config loading** (config_loader.py) — clean and simple
- **Session token security** (run.py lines 31-32, app.py security middleware) — good practice even for localhost
- **Queue file pattern** (agents.py) — if you later want auto-trigger, this is the simplest approach
