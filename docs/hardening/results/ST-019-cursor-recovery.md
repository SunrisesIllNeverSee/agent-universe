# ST-019 Result — Chat Cursor Loss and Recovery

**Status:** DISPROVED / EXISTING SERVER-SIDE RECOVERY  
**Area:** MCP chat continuity

## Review claim

The review suggested that a client losing its local `since_id` cursor would have to re-fetch the entire chat history and proposed new server-side cursor storage.

## Verified behavior

Server-side cursor storage already exists.

- `RuntimeState.cursors` tracks cursor by agent + channel.
- `update_cursor()` persists cursors to `data/mcp_cursors.json`.
- `_load_cursors()` reloads that file on runtime startup.
- `chat.read` uses an explicit positive `since_id` when supplied; otherwise it resumes from `runtime.get_cursor(name, channel)`.
- after returning messages, `chat.read` advances and persists the server cursor.

## Decision

**DISPROVED.** Do not add a second cursor store.

Add a regression test proving:
1. first read advances cursor
2. second read without a client cursor does not replay the same messages
3. the cursor exists in the persisted cursor file.
