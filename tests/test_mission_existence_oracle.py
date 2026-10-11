"""Mission existence oracle: an ordinary agent must not distinguish an unknown
mission id from an existing mission it does not own. Uniform 404, byte-identical
body, no state mutation. Admin keeps real results. Runs on the tmp root."""
import json
import uuid

import pytest

from tests.conftest import signup_agent
from tests.test_mission_principal_binding import (
    ADMIN, VERBS, _agent, _legacy, _mission, _snap, verbs,
)


def _body(r):
    return r.status_code, r.content


def _unknown():
    return f"mission-nope-{uuid.uuid4().hex[:8]}"


def _same_shape(r_unknown, r_other, mid_unknown, mid_other):
    assert r_unknown.status_code == r_other.status_code == 404
    a = r_unknown.content.replace(mid_unknown.encode(), b"<ID>")
    b = r_other.content.replace(mid_other.encode(), b"<ID>")
    assert a == b
    assert json.loads(r_other.content) == {"error": "Mission not found", "mission_id": mid_other}


@verbs
def test_other_owner_indistinguishable_from_unknown(client, verb):
    _, owner_h = _agent(client)
    _, other_h = _agent(client)
    mid = _mission(client, owner_h)["id"]
    ghost = _unknown()
    before = _snap()
    _same_shape(VERBS[verb](client, ghost, other_h), VERBS[verb](client, mid, other_h), ghost, mid)
    assert _snap() == before


@verbs
def test_legacy_ownerless_indistinguishable_from_unknown(client, verb):
    mid = f"mission-legacy-{uuid.uuid4().hex[:6]}"
    _legacy(mid)
    _, h = _agent(client)
    ghost = _unknown()
    before = _snap()
    _same_shape(VERBS[verb](client, ghost, h), VERBS[verb](client, mid, h), ghost, mid)
    assert _snap() == before


@verbs
def test_operator_created_indistinguishable_from_unknown(client, admin_client, verb):
    mid = admin_client.post("/api/missions", json={"label": "op"}).json()["id"]
    _, h = _agent(client)
    ghost = _unknown()
    before = _snap()
    _same_shape(VERBS[verb](client, ghost, h), VERBS[verb](client, mid, h), ghost, mid)
    assert _snap() == before


@verbs
def test_forged_key_same_for_unknown_and_existing(client, verb):
    """Bad credential is rejected before any existence result is revealed."""
    _, owner_h = _agent(client)
    mid = _mission(client, owner_h)["id"]
    forged = {"Authorization": "Bearer forged-" + uuid.uuid4().hex}
    before = _snap()
    a = VERBS[verb](client, _unknown(), forged)
    b = VERBS[verb](client, mid, forged)
    assert a.status_code == b.status_code and a.status_code in (401, 403)
    assert _snap() == before


@verbs
def test_anonymous_rejected_for_unknown_and_existing(client, verb):
    _, owner_h = _agent(client)
    mid = _mission(client, owner_h)["id"]
    a = VERBS[verb](client, _unknown(), {})
    b = VERBS[verb](client, mid, {})
    assert a.status_code == b.status_code and a.status_code in (401, 403)
    assert a.content != b'' and "Mission not found" not in a.text + b.text


@verbs
def test_admin_keeps_distinct_diagnostics(client, verb):
    _, h = _agent(client)
    mid = _mission(client, h)["id"]
    assert VERBS[verb](client, _unknown(), ADMIN).status_code == 404
    assert VERBS[verb](client, mid, ADMIN).status_code == 200


@verbs
def test_owner_still_allowed(client, verb):
    _, h = _agent(client)
    mid = _mission(client, h)["id"]
    assert VERBS[verb](client, mid, h).status_code == 200


def test_authorize_helper_denies_with_404_never_200(client):
    from fastapi import HTTPException
    from starlette.requests import Request
    from app.routes import missions as m
    with pytest.raises(HTTPException) as e:
        # owner mismatch resolved without a live principal: patch resolver
        orig = m._acting_agent_id
        m._acting_agent_id = lambda req: "agent-other"
        try:
            m._authorize_mission_mutation(None, {"owner_agent_id": "agent-owner"})
        finally:
            m._acting_agent_id = orig
    assert e.value.status_code == 404
