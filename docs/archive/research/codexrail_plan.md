# Railway Service Split Resolution Memo

## Summary
Create a new ops memo at `docs/railcodex_review.md` that becomes the canonical handoff document for this Railway incident. The memo should do two jobs at once:
- capture the exact current failure state with concrete Railway evidence
- define the recovery decision tree so the next implementation pass can safely consolidate the app onto one canonical service and one canonical persistent volume

The memo should not pretend the system is ready for execution yet. It should explicitly show that the root issue is a two-service split:
- `web` is failing because it has no `/app/data` volume
- `agent-universe` is healthy because it owns `agent-universe-data` at `/app/data`

## Implementation Changes
- Add `docs/railcodex_review.md` as a fresh incident/recovery memo, separate from the historical transcript in `docs/rail_review.md`.
- Structure the memo as a clean handoff document, not a chat log:
  - Title and timestamp
  - Current Railway topology
  - Confirmed failure mode
  - Why healthchecks fail on `web`
  - Why `agent-universe` still boots
  - Source-of-truth risk
  - Recovery options
  - Required decisions
  - Recommended next execution sequence once decisions are made
- Record these concrete facts in the memo:
  - `web` latest failed deployment: `70484540-785d-48a8-a3ef-37f1d5c2c8f3`
  - `agent-universe` latest successful deployment: `afb06184-d997-46f6-91be-abc1c5a9a11f`
  - attached persistent volume: `agent-universe-data` on `/app/data` for `agent-universe`
  - failing startup line: `RuntimeError: Running on Railway (production) without an attached volume for /app/data.`
  - the app’s boot path expects one canonical `/app/data` mount via `app/data_paths.py` and `app/server.py`
- Make the memo explicitly distinguish three recovery paths:
  - Consolidate on `web`
  - Consolidate on `agent-universe`
  - Keep both services intentionally
- Mark “Keep both” as the highest-risk option because it preserves split persistence and repeated deploy confusion.
- Include a recommendation section that says the safe long-term target is one canonical service plus one canonical `/app/data` volume, but do not hard-choose `web` vs `agent-universe` inside the memo unless product ownership confirms it.
- Include a decision gate section listing the exact questions that must be answered before any mutating Railway work:
  - Which service is the canonical production app?
  - Which data store is the source of truth?
  - Which public domain must survive?
  - Is a maintenance window acceptable for data migration?

## Public Interfaces / Types
- No app API/interface changes in this step.
- New artifact only: `docs/railcodex_review.md`
- The memo should reference, but not modify, the runtime contract:
  - app requires `/app/data` on Railway
  - healthcheck path is `/health`
  - two-service state is currently invalid for reliable persistence

## Test Cases And Validation
- Verify the memo is self-contained and can be understood without reading `docs/rail_review.md`.
- Verify all deployment IDs, service names, and volume names in the memo match current Railway state.
- Verify the memo clearly separates:
  - historical failed deployments
  - current active service state
  - unresolved architectural decisions
- Verify the memo names the exact blocking failure for `web` and does not describe the issue as a generic healthcheck problem.

## Assumptions And Defaults
- Default documentation target is `docs/railcodex_review.md`.
- The memo is an incident/recovery handoff, not an execution transcript.
- The memo should recommend consolidation onto one service, but leave the final canonical-service choice open until ownership confirms whether `web` or `agent-universe` is the real production identity.
- `docs/rail_review.md` remains the raw historical log; `docs/railcodex_review.md` becomes the cleaned operational summary.
