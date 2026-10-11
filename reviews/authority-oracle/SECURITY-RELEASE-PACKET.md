# SIGNOMY security-only release packet (NO DEPLOY)

Status: DRAFT for coordinator. Production is UNOBSERVED; nothing here was
verified against production. No push, merge, deploy, or network action was
taken. Exploit detail is intentionally generic (classes only).

## 1. Fix sequence

| Fix | SHA | Class closed |
|---|---|---|
| H1 availability owner credential | `3036503` | anonymous write to per-agent availability state |
| P3 guard tests (shell authority fixtures) | `e191028` / `73894b7` (integration), `3cc50c4` | regression canaries; test/doc only, no runtime change |
| D-B mission owner binding | `572b39b` | any agent could end/update/create slots on another agent's mission |
| D-C unknown mission id fails closed | `102c7e9` | slot creation against non-existent mission wrote orphan state |
| P4 repair (mint resolvable mission) | `df8f540` | orphan mission ids from slot create |
| Integration (D-B + D-C + others) | `03e521c` | merge of the above |
| Existence oracle (this specialist) | `696912a` on `claude/authority-oracle-release` (`7ccc8a4` as picked onto hotfix candidate) | owned-vs-unknown mission distinguishable by 403 vs 404 |
| Task guards | PLACEHOLDER (coordinator) | |
| Campaign guards | PLACEHOLDER (coordinator) | |
| Deploy-dash guards | PLACEHOLDER (coordinator) | |

## 2. Can a security-only hotfix avoid Phase 4 / P3 shell?

Verdict: YES, with a six-commit cherry-pick and one trivial, deterministic conflict resolution.

Facts (local git only): `main` = `292d3ba` (equals `origin/main` locally; may lag the real remote). `03e521c` is
28 non-merge commits ahead (`git log main..03e521c`), 44 files, +2345/-45. Runtime code differences vs main:
`availability.py`, `missions.py`, `server.py` (security), plus `pages.py` (`/shell` route), `provision.py`
(X-Agent-Key header transport, mixed into a P3 shell commit `0f038d6`), `frontend/shell.html` (P3 shell). The rest is
docs, roadmap/controller workflow files, and tests.

Security-only: `3036503`, `572b39b`, `102c7e9`, `df8f540` (+ test pin `ba60574`), oracle fix.
Feature/docs (excluded): `7b8eec1`, `98fc256`, `0f038d6` (P3 shell; `provision.py` change is hardening but mixed with
shell work, excluded), all `docs(...)`/`chore(roadmap)` commits, `3cc50c4`/`73894b7`/`e191028`/`22d3b19`/`8f7f7e8`
(P3 shell tests/evidence).

Recipe (tried, local only, branch `claude/security-hotfix-candidate` off `main`, worktree
`/Users/dericmchenry/Developer/_5_Signomy/1_agent-universe-wt/security-hotfix-candidate`):

```
git switch -c <hotfix> main
git cherry-pick 3036503 ba60574 df8f540 572b39b 102c7e9 696912a
```
Conflicts met:
1. `572b39b`: modify/delete on `tests/test_p3_shell_authority_fixtures.py` (file only exists on the P3 branch).
   Resolution: `git rm` that file, continue. The commit's hunk there is a test touch-up, not runtime.
2. `102c7e9`: content conflict in `app/routes/missions.py` `create_slots_from_formation`: main-side picks D-B, D-C
   wants fail-closed. Resolution = the integration form already at `03e521c` (resolve principal, 404 on unknown id,
   then owner check). Result is identical to the integration file except three comment lines.
Tests: hotfix candidate full suite 624 passed. Oracle branch (`03e521c` + oracle) 700 passed. Test count differs
because P3-shell/controller tests are intentionally absent from the hotfix.
Note: `ba60574` adds a strict-xfail baseline that `df8f540` converts; both are required in order. Task/campaign/deploy-dash
fixes from the current mission must be added to the recipe once SHAs exist (re-run suite).

## 3. Production vs branch uncertainty

Unknown: which commit production runs, whether Railway builds from `main`, from a tag, or from a manual CLI upload;
whether the real `origin/main` is ahead of the local ref `292d3ba`; Vercel static copies of `frontend/` may drift from Railway.
Before any release, the owner should state the deployed SHA out of band (Railway deployment record), then
`git diff <deployed>..<hotfix>` must be reviewed; the cherry-pick list above assumes the deployed tree is `292d3ba`.
No probe of production was made.

## 4. Secret-safe delivery of private patches

The repo is public. Pushing security commits (and tests/falsifiers that describe the exploit class) to a public
remote discloses the vulnerabilities before production is patched. Recommendation, in preference order:
1. Deploy from a PRIVATE remote/fork that Railway is pointed at for the release window (owner action), then publish
   the commits publicly only after production is verified fixed.
2. Railway CLI deploy from the local hotfix tree (`railway up`), with `reviews/` falsifier files excluded from the
   upload (or removed in the deploy commit). Owner-executed; not run here.
3. Avoid: pushing a branch/PR to the public repo before the release.
Sanitize before any public release: drop `reviews/authority-oracle/falsifier_oracle.py` and exploit-specific evidence
docs; keep regression tests with generic names.

## 5. Environment / config checks (names only)

- `CIVITAE_ADMIN_KEY`: must be set on Railway (it is the operator gate; fix assumes it is non-empty. Empty admin key
  makes `_acting_agent_id` treat callers as operator in no-admin-key dev path).
- `CIVITAE_DEV_MODE`: must be UNSET on Railway.
- `RAILWAY_ENVIRONMENT`: set automatically; confirm present.
- `KASSA_JWT_SECRET` (and `JWT_SECRET` fallback, `KASSA_JWT_SECRET_PREV` if rotating): set.
- Persistent volume at `/app/data` mounted; `data/missions.json` legacy records have no `owner_agent_id` (see 6).
- `OPERATOR_EMAIL`, `RESEND_API_KEY`: unaffected, confirm per existing checklist.

## 6. Backwards-compatibility impact

- Availability mutations: callers must send their own live, non-revoked Bearer api_key (or operator key); anonymous and
  JWT-only callers now get 401/403. Public GETs unchanged. Any frontend or agent that wrote availability anonymously breaks.
- Mission end/update/slot-create with a supplied mission_id: only the recorded owner agent or operator succeeds.
  Ordinary agents acting on a foreign, ownerless-legacy, or operator-created mission now receive a uniform
  404 `{"error":"Mission not found","mission_id":...}` (previously 403). Clients that branched on 403 must treat 404 as
  denial. Forged/revoked keys still get 401 (credential checked before lookup, so no existence signal).
- Legacy missions (no `owner_agent_id`) become operator-only for agent mutation. If agents legitimately manage legacy
  missions, the operator must backfill `owner_agent_id` before release.
- `/api/slots/create` with an unknown supplied mission_id: 404, no write (previously wrote orphan slots).
- Public `GET /api/missions` and `GET /api/missions/{id}` remain public by design, so mission existence and owner id are
  still discoverable through those reads; the oracle fix closes the mutation-path signal only (residual).
- Placeholders: task guards, campaign guards, deploy-dash guards (coordinator to fill).

## 7. Staging validation plan

1. Build hotfix in a staging Railway service with a COPY of production data (or synthetic equivalent), staging env vars per section 5.
2. Run the full suite on the exact release tree; require green (candidate: 624).
3. In-process/staging checks (synthetic agents only): availability write with owner key succeeds; anonymous/other-agent fails;
   owner vs other-agent vs unknown mission id responses on end/update/slot-create: identical status and body for non-owners.
4. Legacy-data pass: list missions lacking `owner_agent_id`; decide backfill.
5. Smoke public pages and `/api/health`; confirm no 5xx.

## 8. Rollback

Release = single revert-able change set. Rollback: redeploy the previously recorded deployment (Railway "redeploy previous")
or `git revert` the cherry-picked range in reverse order (oracle, D-C, D-B, P4 repair, H1). No schema or data migration
is introduced; data files are not rewritten by these fixes (backfill, if done, is a separate reversible data step: back up
`missions.json` first). Rollback re-opens the vulnerability classes, so rollback only for availability emergencies.

## 9. Alerts / telemetry to watch

- 401/403/404 rate on `POST /api/availability/*`, `/api/missions/*/end|update`, `/api/slots/create` (expect a step change:
  availability 401/403 up, mission 403 -> 404).
- Spike of 404 on mission mutation routes from one principal (probing for ids) after release.
- `data/audit.jsonl` governance events for denied vs allowed mission mutations; seeds count per mutation route stays flat on denials.
- Agent complaints of "Mission not found" for their own missions (would indicate owner-binding gaps / legacy records).
- Timing residual: unknown-id and foreign-owner paths both do one mission-store read and no extra I/O; a coarse timing
  difference from list scan position is theoretically possible and not mitigated.

## 10. GO / NO-GO checklist (owner approval required)

Owner R_LIVE approval is REQUIRED before any production release. Nothing below authorizes a deploy by itself.
- [ ] Owner R_LIVE approval recorded (explicit, for this SHA).
- [ ] Deployed production SHA identified by owner; diff vs hotfix reviewed.
- [ ] Task/campaign/deploy-dash fix SHAs added to the cherry-pick list; suite green on the final tree.
- [ ] Section 5 env/config verified by owner on Railway.
- [ ] Delivery route chosen (private fork/CLI), public push explicitly deferred until after verification.
- [ ] Legacy mission ownership decision made (backfill or accept operator-only).
- [ ] Staging validation (section 7) passed; rollback target recorded.
- [ ] Alerts in section 9 in place for the first 24h.
NO-GO if any box is unchecked.
