# H1 — Revoked-Key Deny-List: Independent Falsifier Review

Verdict (initial): CONDITIONAL — bounded corrections
Verdict (post-correction re-verify): PASS

## Scope verified by falsifier

Deny-list consulted on all builder-claimed surfaces (middleware bearer,
require_agent_claim sites, per-agent guard, provision login, MCP key path)
— all confirmed in code.

## Broken by falsification, corrected

- H1F-01 (HIGH): outstanding JWTs outlived the revoked credential — fixed
  via `token_epoch` credential-liveness binding (issue carries epoch;
  revoke/rotate/decommission bump it; `agent_token_alive` enforced at every
  JWT↔registry junction incl. /ws/thread and kassa posts).
- H1F-02 (HIGH): money paths (economy pay/payout, connect mpp_pay/cashout)
  accepted JWTs with no registry lookup at all — decommissioned agent's
  token could still move funds. Registry+liveness gate added to all four.
- H1F-03 (MED): kassa login + inbox key auth deny-parity.
- H1F-04 (MED): fail-closed deny-list load (strict validation; reload
  keeps last-good rather than silently un-revoking).
- H1F-05 (LOW): deny-list refresh on reload_registry.

## Carried advisories

- H1F-06: MCP chat.* binds no credential at all (bare sender name) —
  pre-existing design question, not this lane's scope.
- H1F-07: standard bearer TOCTOU on in-flight requests — accepted.

## Verified clean

No plaintext key or digest leakage in audit/seeds/events; suspend ≠
revoke (403 vs 401 paths distinct); revoke-twice → 409; unknown → 404;
restart persistence; REST/MCP parity on all key-auth tools.

## Re-verification

Builder corrections verified in `tests/test_h1_key_revocation.py`
(+5 reproducer tests). Suite: 502/502.
