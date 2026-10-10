# T0 Independent Falsifier Verdict

Identity: independent falsifier (separate agent from builder lane DREP2).
The prior probe was NOT trusted — all route→guard chains were re-traced
in app/ and new counterexamples invented.

VERDICT (initial): **FAIL — invariant broken**
VERDICT (post bounded corrections + dynamic rerun): **PASS — invariant holds**

## Broken invariant — found & confirmed

`GET /api/advisory/seats` was unauthenticated and returned pending applicant
records verbatim (name, email, message).
- Write path: `POST /api/advisory/apply` (public prefix) stores applicant PII.
- Read path: `GET /api/advisory/seats` absent from `_ADMIN_GET_PREFIXES`
  and carried no `require_admin`.
- Dynamic proof: `reviews/t0_independent_rerun.py` → RED with canary PII
  in a 200 body.

## Bounded corrections applied

1. `advisory.py get_council_seats` — `applicant` field stripped from the
   public projection (seat status + message_count stay public).
2. Advisory audit entry no longer logs applicant NAME into the public
   `/api/audit` chain (seat_id + type only).
3. `POST /api/provision/key` — now `require_admin` at route level
   (was middleware-only; unauthenticated under DEV_MODE).
4. `POST /api/inbox/{id}/review` — now `require_admin` at route level.

## Rerun

`reviews/t0_independent_rerun.py` → **GREEN** after corrections.
Full suite 521/521.

## Coverage extension (what the original probe missed)

/api/agent/inbox, /api/inbox/{id}, all /api/operator/* reads,
/api/provision/registry, provision status, agent directory, advisory
surfaces, magic-link endpoints, middleware-only writes, public audit PII.

## Clean (verified)

/api/agent/inbox (Bearer→401), /api/inbox[/{id}] (403 anon/forged),
/api/operator/* (403), /api/provision/registry (403), magic-token
endpoints (403, no reflection), public_kassa_post strips PII,
MCP tools strip key material, /api/agents email is generated label.

## Limitations

Static trace + one dynamic probe script; WS subscription content and
email-body content reviewed earlier under H5, not re-probed here.
