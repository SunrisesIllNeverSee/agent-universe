# COMMAND — What's Missing to Go Live

Everything below is what sits between the current demo and a live operating console.
Mapped against agentchattr's architecture so you can see exactly what each piece looks like.

---

## PIECE 1: A Server

**What it does:** Sits between COMMAND's frontend and the AI systems. Receives messages from the browser, routes them to the right agent, receives responses, pushes them back to the UI.

**His version:** `app.py` (FastAPI + WebSocket) + `run.py` (entry point). ~1,900 lines total but most of that is features you don't need — channels, jobs panel, todos, settings persistence. The core server logic (receive message, broadcast to connected clients) is maybe 200 lines.

**Your version needs:**
- A FastAPI or Flask app
- One WebSocket endpoint (browser connects here)
- REST endpoints for config (systems, vault, governance state)
- Serves your existing index.html as the frontend
- Runs on localhost for development, deployable to a VPS for demo

**Size:** ~300 lines of Python. One file.

---

## PIECE 2: A Message Store

**What it does:** Saves messages so they survive page refresh. His uses JSONL (one JSON object per line in a flat file). Simple, no database needed.

**His version:** `store.py` — 324 lines. Thread-safe, observer callbacks, JSONL persistence.

**Your version needs:**
- A list of messages in memory
- Append to a .jsonl file on every new message
- Load from file on server start
- Observer callback so the server knows when to broadcast

**Size:** ~80 lines. One file. His is 324 because of todos, deletion, attachments — you don't need any of that yet.

---

## PIECE 3: An MCP Bridge

**What it does:** Exposes tools that AI agents can call. When Claude Code or any MCP-compatible agent connects, it sees tools like `chat_send` and `chat_read` and uses them to participate in the conversation.

**His version:** `mcp_bridge.py` — 885 lines. But the actual tool surface is 5 functions:
- `chat_send(sender, message)` — agent posts a message
- `chat_read(sender)` — agent reads new messages since last read
- `chat_join(name)` — agent announces presence
- `chat_who()` — agent checks who's online
- `chat_rules(action)` — agent reads/proposes rules

**Your version needs:**
- Same 5 tools (or fewer — send/read/join is the minimum viable set)
- BUT: your `chat_send` injects governance context. Every message an agent reads comes wrapped in your governance mode, loaded vault docs, and active posture settings. This is where COMMAND's IP lives at the execution layer.
- Uses the `mcp` Python package: `pip install mcp`
- FastMCP server on a separate port (e.g., 8200)

**Size:** ~150 lines for the tools. Another ~50 for server setup. One file.

**This is the piece where your governance becomes real.** agentchattr's MCP bridge just passes messages. Yours injects constitutional governance into every read.

---

## PIECE 4: A Router

**What it does:** Decides which agent gets triggered when a message arrives. His parses @mentions with regex and has a loop guard.

**His version:** `router.py` — 96 lines. That's it. Regex for @mentions, hop counter, pause/resume.

**Your version needs:**
- Sequence ordering (your Primary/Secondary/Observer hierarchy) instead of @mention parsing
- When user sends a message, route to Primary first, then Secondary, then Observer — in the order set in the UI
- Loop guard equivalent — max rounds before pausing
- Broadcast mode routes to all active systems simultaneously

**Size:** ~100 lines. One file. Yours is actually simpler than his because you have explicit ordering instead of parsing @mentions.

---

## PIECE 5: A Bridge Between Frontend and Backend

**What it does:** Your existing index.html currently manages everything in browser memory. It needs to talk to the server instead.

**What changes in your HTML:**
- Chat messages: instead of pushing to a local array, send via WebSocket to the server. Server broadcasts back to all connected clients (including the UI).
- System config: instead of hardcoded SYSTEMS array, fetch from server on load.
- Governance state: POST governance changes to server so they're available to the MCP bridge when agents read messages.
- Vault documents: upload to server storage, server injects them into agent context.

**Size:** Maybe 200 lines of JS changes scattered across your existing code. Replacing local state management with fetch/WebSocket calls.

---

## PIECE 6: Agent Trigger (OPTIONAL FOR DEMO)

**What it does:** Automatically wakes up agents when they're @mentioned or when it's their turn in sequence.

**His version:** `agents.py` (79 lines) writes to a queue file. `wrapper.py` (793 lines) watches the queue and injects keystrokes into the agent's terminal.

**Why it's optional:** For your demo, the buyer doesn't need to see agents auto-wake. They need to see governance injection working — that when an agent reads from COMMAND, it gets the constitutional context, the posture settings, the vault docs. The auto-trigger is plumbing. The governance injection is the product.

**If you want it:** The wrapper pattern is straightforward — watch a queue file, inject text into a terminal. But this only matters for CLI agents running locally.

---

## THE MAP — Minimum Viable Live COMMAND

```
┌─────────────────────┐
│   COMMAND Frontend   │  ← Your existing index.html with WebSocket added
│   (browser)          │
└──────────┬──────────┘
           │ WebSocket (port 8300)
           │
┌──────────▼──────────┐
│   COMMAND Server     │  ← NEW: ~300 lines Python (FastAPI + uvicorn)
│   app.py + run.py    │
│                      │
│  ┌────────────────┐  │
│  │  Message Store  │  │  ← NEW: ~80 lines (JSONL persistence)
│  │  store.py       │  │
│  └────────────────┘  │
│                      │
│  ┌────────────────┐  │
│  │  Router         │  │  ← NEW: ~100 lines (sequence ordering)
│  │  router.py      │  │
│  └────────────────┘  │
│                      │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   MCP Bridge         │  ← NEW: ~200 lines (governance-injected tools)
│   mcp_bridge.py      │
│   port 8200          │
│                      │
│   chat_send()        │
│   chat_read() ← injects governance + vault + posture
│   chat_join()        │
└──────────┬──────────┘
           │ MCP protocol
           │
┌──────────▼──────────┐
│   AI Agents          │  ← Claude Code, Codex, Gemini, etc.
│   (connect via MCP)  │
└─────────────────────┘
```

---

## TOTAL NEW CODE

| File | Lines | Purpose |
|------|-------|---------|
| run.py | ~50 | Entry point, wires everything together |
| app.py | ~300 | FastAPI server, WebSocket, REST endpoints |
| store.py | ~80 | JSONL message persistence |
| router.py | ~100 | Sequence-based routing with governance hierarchy |
| mcp_bridge.py | ~200 | MCP tools with governance injection |
| **Total** | **~730** | **Five files. That's the whole backend.** |

Plus ~200 lines of JS changes in your existing index.html to wire WebSocket.

---

## WHAT MAKES YOURS DIFFERENT FROM HIS

His `chat_read` returns raw messages:
```
[{"sender": "user", "text": "analyze this dataset", "id": 3}]
```

Your `chat_read` returns governed messages:
```
{
  "governance": {
    "mode": "High Security",
    "posture": "DEFENSE",
    "reasoning": "Deductive",
    "depth": "DEEP"
  },
  "vault_context": [
    {"name": "Security Protocol v3", "content": "..."},
    {"name": "Audit Requirements", "content": "..."}
  ],
  "role": "Primary",
  "sequence_position": 1,
  "messages": [
    {"sender": "user", "text": "analyze this dataset", "id": 3}
  ]
}
```

That's the difference. That's the product. Every agent that reads from COMMAND gets constitutional governance injected. His agents get chat messages. Your agents get orders.

---

## BUILD ORDER

1. **Server + Store** — get messages flowing through a backend instead of browser-only
2. **MCP Bridge** — the governance injection layer (this is where the IP lives)
3. **Router** — sequence ordering, Primary/Secondary/Observer enforcement
4. **Frontend wiring** — swap local state for WebSocket calls
5. **Agent trigger** — optional, only if you want auto-wake for the demo
