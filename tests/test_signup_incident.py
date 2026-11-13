from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import uuid

import pytest

from app.deps import state
from app.routes import provision
from tests.conftest import signup_agent


@pytest.fixture(autouse=True)
def isolated_registry(client):
    original = state.runtime.registry
    state.runtime.registry = []
    state.runtime.persist_registry()
    provision._rate_stores.clear()
    yield
    state.runtime.registry = original
    state.runtime.persist_registry()
    provision._rate_stores.clear()


def register(client, i):
    return signup_agent(client, name=f"ir-{uuid.uuid4().hex}", ip=f"192.0.2.{i + 1}")


def test_rotating_origins_share_persisted_signup_budget(client):
    assert provision.GLOBAL_SIGNUP_MAX == 5
    for i in range(5):
        assert register(client, i).status_code == 200
    provision._rate_stores.clear()
    state.runtime.registry = []
    blocked = register(client, 5)
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0
    assert len(state.runtime.registry) == 5


def test_old_registrations_do_not_consume_current_budget(client):
    old = (datetime.now(timezone.utc) - timedelta(seconds=301)).isoformat()
    state.runtime.registry = [
        {"agent_id": f"old-{i}", "type": "agent", "provisioned": old}
        for i in range(20)
    ]
    state.runtime.persist_registry()
    assert register(client, 0).status_code == 200


def test_suspension_does_not_reopen_signup_budget(client):
    now = datetime.now(timezone.utc).isoformat()
    state.runtime.registry = [
        {"agent_id": f"suspended-{i}", "type": "agent", "status": "suspended", "provisioned": now}
        for i in range(5)
    ]
    state.runtime.persist_registry()
    assert register(client, 0).status_code == 429


def test_concurrent_origins_cannot_overfill_budget(client):
    with client:
        with ThreadPoolExecutor(max_workers=6) as pool:
            statuses = list(pool.map(lambda i: register(client, i).status_code, range(15)))
    assert statuses.count(200) == 5
    assert statuses.count(429) == 10
    assert len(state.runtime.registry) == 5
