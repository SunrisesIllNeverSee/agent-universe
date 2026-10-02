# ST-023 Result — create_app Modularization Value vs Regression Risk

**Status:** DISPROVED AS A HARDENING PRIORITY / DEFERRED REFACTOR  
**Area:** architecture / maintainability

## Review claim

The external review described `app/server.py` as a large application monolith and proposed splitting it into:

- `app/app_factory.py`
- `app/middleware.py`
- `app/startup.py`
- `app/health.py`

## Current repository state

That description reflects an older architecture.

Current `app/server.py` is approximately 500 lines and is already primarily infrastructure:

- construct shared stores/runtime/economy
- populate `app.deps.state`
- initialize OTel
- build FastMCP
- configure lifespan
- configure exception/security/auth middleware
- include already-extracted domain routers
- register API fallback
- root-mount the FastMCP sub-application

Business/domain routes already live in modules such as:

- `routes/provision.py`
- `routes/kassa.py`
- `routes/forums.py`
- `routes/economy.py`
- `routes/missions.py`
- `routes/governance.py`
- `routes/operator.py`
- `routes/connect.py`

Historical archive documents describing a 2,000–4,500-line `create_app()` are no longer representative of current main.

## Regression risk of a cosmetic split

Ordering in `server.py` is operationally significant:

- shared state must exist before route execution
- FastMCP must be built once
- middleware ordering affects auth/security
- API fallback must come after real API routes
- FastMCP root mount must remain after FastAPI routes

Splitting these merely to reduce file length creates a real chance of reintroducing the exact routing/mount defects recently repaired.

## Remaining maintainability debt

There is still useful *pattern* consolidation to consider:

- repeated route-local admin-key helpers
- repeated rate-limit helpers
- security/auth logging policy

Those should be extracted only when the associated security tests define their behavior.

## Decision

**DISPROVED as an immediate hardening refactor.**

Do not reorganize `create_app()` in this program. Prefer narrow behavior-preserving extraction where it removes duplicated security logic and is regression-tested.

## Closure

**Final status:** DISPROVED / DEFERRED

**Implementation/evidence:** no demonstrated hardening defect required a broad `create_app` split, so the proposed refactor was not performed.

**Decision:** preserve current structure. Revisit only when a concrete coupling/testability defect justifies the regression cost.
