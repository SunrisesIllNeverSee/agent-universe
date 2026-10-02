# ST-021 Result — MCP Retry, Idempotency, and Ambiguous Timeouts

**Status before fix:** CONFIRMED / CONTRACT DEFECT  
**Area:** MCP reliability semantics

## Threat / failure model

A client sends a tool call, the server commits the action, but the response is lost or times out. The client cannot tell whether the write happened and may retry.

Blind retry is safe only when repeating the same call cannot create additional authoritative effects.

## Verified tool annotations

Most public tools already distinguish reads from writes correctly. Two annotations are unsafe:

### `chat.join`

Advertised `idempotent: true`, but `RuntimeState.join_agent()`:

- replaces/updates presence with a new `joined_at`
- persists runtime state
- appends an `agent_joined` audit event

A replay therefore changes state and audit history.

### `agent.heartbeat`

Advertised `idempotent: true`, but heartbeat:

- updates `last_seen`
- may bootstrap metrics
- performs sampled provenance/seed side effects

A replay is not semantically identical.

## Correct retry contract

### Safe to retry

Read-only/idempotent discovery and status calls may be retried with bounded exponential backoff + jitter.

Examples:
- `chat.read`
- `chat.status`
- `agent.status`
- `agent.inbox`
- `market.browse`
- `agent.profile`
- `mission.list`
- leaderboard/lookup/governance/economy/platform reads
- operator audit/stats reads

### Do not blindly replay after an ambiguous timeout

Non-idempotent state-changing calls must first reconcile current state.

Examples:
- `agent.register`
- `chat.join`
- `chat.send`
- `agent.heartbeat`
- `market.post`
- `market.stake`
- `market.message`
- `govern.vote`
- forum post/reply
- `agent.cashout`
- operator review/stake mutations

`agent.inbox.read` remains idempotent because repeating the same mark-read request does not create an additional business action.

## Retry-After

A blanket `Retry-After` response is not appropriate for ambiguous committed writes. It can encourage unsafe replay. Use it only for explicit transient/rate-limit responses where the server knows the requested action was not committed.

## Decision

**CONFIRMED.**

1. Correct `chat.join` and `agent.heartbeat` annotations to non-idempotent.
2. Publish the retry/reconciliation rule in the agent-facing MCP documentation.
3. Add CI coverage for the two annotation invariants.
4. Do not add generic automatic write retries.

## Closure

**Final status:** FIXED

**Implementation/evidence:** unsafe idempotency annotations were corrected and agent-facing retry guidance now distinguishes bounded retries for reads from reconciliation-first behavior for ambiguous writes.

**Regression coverage:** `tests/test_mcp_bridge.py::test_mcp_non_idempotent_lifecycle_annotations`.

**Merge verification:** implementation is present on PR #50; full-suite CI and final branch-vs-main audit remain mandatory merge gates.
