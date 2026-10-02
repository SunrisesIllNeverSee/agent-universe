# ST-025 — Authenticated Principal Binding

## Problem

The current global cockpit Bearer check proves only that a request carries an API key belonging to some active registered agent. Several self-service routes then accept an actor identifier from the request body.

That creates an identity-binding gap: authentication and the identity receiving attribution/authority can diverge.

## Confirmed self-service surfaces

- `POST /api/slots/fill`
- `POST /api/slots/leave`
- `POST /api/slots/bounty`
- `POST /api/governance/meeting`
- `POST /api/governance/meeting/{id}/join`
- `POST /api/governance/meeting/{id}/motion`
- `POST /api/governance/meeting/{id}/vote`
- `POST /api/governance/meeting/{id}/adjourn`

## Fix contract

1. Resolve the active agent principal from the Bearer API key with constant-time hash comparison.
2. Administrator-key requests retain explicit act-on-behalf authority.
3. Agent-key requests must bind actor fields to the authenticated principal.
4. Slot fill/leave are no longer effectively unauthenticated self-service; they require the matching agent API key.
5. Agent-key adjourn is limited to the meeting caller; admin may still adjourn.
6. Do not silently change the broader cockpit authorization policy in this patch.

## Explicit follow-up

The existing prefix-level cockpit policy permits active agent keys on a broad family of writes. That policy should eventually be replaced by explicit scopes/capabilities or role-based authorization rather than increasingly complex prefix rules.

That is a separate product authorization decision because it determines which agent roles may create missions, campaigns, deploy state, or perform other operator-like actions.

## Acceptance

- Agent A key cannot fill/leave a slot as Agent B.
- Agent A key cannot join/propose/vote as Agent B.
- Agent A key cannot call a meeting as Agent B.
- Only the caller (or admin) can adjourn through an agent credential.
- Matching active-agent key succeeds on intended self-service flows.
- Admin behavior remains compatible.
- Full CI remains green.
