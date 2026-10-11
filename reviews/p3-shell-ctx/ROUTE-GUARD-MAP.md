# Route -> guard map (consequential endpoints exercised by the shell authority suite)

Line numbers are for branch claude/p3-shell-ctx @ 81eb3d1 and are REPO-VERIFIED by reading source.

Layer 1 = `admin_key_guard` middleware, app/server.py:349-412. For POST/DELETE/PATCH/PUT it exempts any
path under `_PUBLIC_WRITE_PREFIXES` (server.py:289-312); otherwise requires X-Admin-Key, or (only for
`_OPERATOR_WRITE_PREFIXES`, server.py:320-334) a valid active-agent Bearer api_key (`_agent_bearer_ok`, :336).
Layer 2 = handler guard. Principal helpers: app/auth.py `require_agent_claim` :79, `agent_token_alive` :106,
`admin_key_matches` :32, `active_agent_from_bearer` :38; kassa JWT: `_get_agent_from_token` app/routes/kassa.py:102.

| Endpoint | Route | Layer 1 | Layer 2 (handler) | Denies pre-mutation |
|---|---|---|---|---|
| POST /api/kassa/posts/{id}/stake | kassa.py:291 | public prefix `/api/kassa/posts` (exempt) | `_get_agent_from_token` kassa.py:294 (JWT + `agent_token_alive`) before post lookup/insert | yes |
| DELETE /api/kassa/stakes/{id} | kassa.py:443 | public prefix `/api/kassa/stakes/` | `_get_agent_from_token` :446; owner check `stake.agent_id` :452 | yes (wrong agent 403) |
| POST /api/kassa/posts | kassa.py:896 | public prefix | admin key OR JWT + `agent_token_alive` :897-906 | yes |
| POST /api/kassa/posts/{id}/upvote | kassa.py:989 | public prefix | NONE (rate limit only, :991) | n/a: public by design |
| POST /api/kassa/threads/{id}/messages | kassa.py:683 | public prefix `/api/kassa/threads/` | Bearer JWT must equal thread.agent_id + alive :703-706, else magic token, else 401 | yes |
| POST /api/kassa/threads/{id}/close | kassa.py:648 | public prefix | admin key OR JWT sub == thread.agent_id + alive :660-666 | yes |
| POST /api/slots/fill | missions.py:833 | public prefix `/api/slots/fill` | `require_agent_claim` :843 | yes |
| POST /api/slots/leave | missions.py:927 | public prefix `/api/slots/leave` | `require_agent_claim` :934 + occupant check | yes |
| POST /api/slots/create | missions.py:750 | operator prefix `/api/slots/`: admin or agent Bearer | none (no ownership) | yes vs anon/forged |
| POST /api/slots/bounty | missions.py:982 | operator prefix | `require_agent_claim` :989 | yes (wrong agent 403) |
| POST /api/missions | missions.py:243 | operator prefix `/api/missions` | none | yes vs anon/forged |
| POST /api/missions/{id}/end | missions.py:313 | operator prefix | none | yes vs anon/forged |
| POST /api/missions/{id}/update | missions.py:368 | operator prefix | none | yes vs anon/forged |
| POST /api/governance/meeting/{id}/vote | governance.py:282 | operator prefix `/api/governance` | `require_agent_claim` :290 | yes (wrong agent 403) |
| POST /api/economy/withdraw | economy.py:435 | NOT public, NOT operator prefix: admin key only | none (no per-agent claim) | yes; denial-only |
| POST /api/forums/threads | forums.py:91 | public prefix `/api/forums/threads` | `_get_agent_from_token` forums.py:94 | yes |

Notes
- "yes vs anon/forged" rows are protected only by layer 1; if the middleware were bypassed there is no
  handler check (see falsifier: patching `server.admin_key_matches` turns these RED).
- Gaps reported, not fixed (out of lane): any ACTIVE agent api_key passes layer 1 for missions/slots
  operator verbs and no handler binds ownership, so agent B can end/update agent A's mission and create
  slots on it (verified 200 in a probe; JWT is rejected 403). /api/availability write is the known xfail.
