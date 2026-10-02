# ST-012 Result — Startup State Validation

**Status:** PARTIAL / CORE FAIL-FAST ALREADY PRESENT  
**Area:** deployment startup

## Review claim

The external review said the app has no pre-start validation and suggested adding a new startup validator that reparses state and rebuilds MCP.

## Verified boot path

`create_app()` already constructs critical dependencies synchronously before the FastAPI app is returned:

1. data directory resolution
2. message/KA§§A/inbox/forum stores
3. audit ledger
4. `RuntimeState`
5. economy
6. production JWT secret
7. shared state
8. OpenTelemetry setup
9. FastMCP build + streamable HTTP app

`RuntimeState.__init__` directly parses core provision and vault JSON. Malformed critical JSON therefore fails app creation rather than producing a superficially healthy server.

`get_kassa_jwt_secret()` raises in Railway production when no persistent JWT secret is configured.

FastMCP is also built during app creation; registration/build failures prevent normal startup.

## Remaining boundary

Some domain JSON files are intentionally loaded by their owning route/store rather than globally at boot. Treating every optional/domain file as a deploy-blocking dependency could turn an isolated subsystem problem into a total outage.

## Decision

**PARTIAL. Preserve the existing fail-fast boot path.**

Do not add a second validator that reparses the same state or constructs another FastMCP instance. Add targeted startup tests for truly authoritative dependencies and document optional/degraded state separately.

## Closure

**Final status:** PARTIAL

**Implementation/evidence:** existing fail-fast startup behavior was preserved rather than duplicated. Targeted tests now prove corrupt authoritative configuration fails startup and Railway production refuses an ephemeral JWT secret.

**Regression coverage:** `tests/test_startup_hardening.py`.

**Remaining work:** classify any newly added startup dependency as authoritative vs optional before deciding whether failure should block boot.
