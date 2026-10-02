# SIGNOMY Release Verification & Rollback Runbook

This runbook validates the **public product path**, not merely process health.

## 1. Pre-merge

- Run repository CI.
- Confirm MCP contract tests pass:
  - runtime tool set == public server card
  - 30 tools
  - 7 resources
  - hosted contract versions aligned
- Confirm no change reintroduces a conditional Vercel rewrite for `/mcp`.
- Confirm `app.mount("", _mcp_app)` remains unchanged unless a dedicated mount-contract test proves otherwise.
- Confirm Railway stays single-worker unless ST-014 has been explicitly reopened and passed.

## 2. Confirm production deployments

After merge, identify the exact `main` commit.

### Vercel

Verify the production `agent-universe` deployment is **READY** and its Git SHA equals the intended `main` commit.

### Railway

Verify the backend deployment completed for the same intended application revision when backend files changed.

A green deployment badge is necessary but not sufficient.

## 3. Public HTTP/discovery probes

Run:

```bash
python scripts/verify_public_mcp.py
```

The verifier checks:

- `https://signomy.xyz/health`
- `https://signomy.xyz/.well-known/mcp-server-card.json`
- a real MCP Streamable HTTP connection to `https://signomy.xyz/mcp`
- exactly 30 public tools
- critical lifecycle/discovery tools are present

If the verifier fails, the release is not considered healthy.

## 4. State-changing smoke tests

Do **not** create posts, votes, payouts, or registrations as part of the default release probe.

If a release specifically changes a state-changing tool, use an isolated test identity/fixture and reconcile/clean up the result explicitly.

## 5. External registry/discovery checks

After the public contract is healthy:

- refresh/retest Glama or other registries that cache the endpoint
- distinguish registry cache/staleness from a live Signomy transport failure
- compare the registry's advertised tool count/version with the public server card

## 6. Rollback decision

Rollback/revert immediately for:

- protocol 404/redirect/HTML on `/mcp`
- initialize/list-tools failure
- contract mismatch
- authentication bypass/regression
- state corruption
- sustained production 5xx on critical paths

For a documentation/cache mismatch with a healthy protocol, repair metadata/registry state rather than rolling back functioning runtime code.

## 7. Rollback execution

Because SIGNOMY is split-deployed, roll back the failing layer:

- **Vercel/frontend/proxy:** promote/redeploy the last known-good production deployment or revert the offending `main` commit.
- **Railway/backend:** roll back to the last known-good Railway deployment/application revision using the Railway deployment controls.
- **Both:** if the release changed both layers and compatibility is uncertain, restore both to their last known-good paired state.

Never roll back authoritative data files blindly. Code rollback and data rollback are separate operations.

## 8. Post-rollback verification

Re-run:

```bash
python scripts/verify_public_mcp.py
```

Then verify the specific endpoint/action that triggered the rollback.

Record:
- bad commit/deployment
- observed failure
- rollback target
- verification result
- follow-up stress-test ID
