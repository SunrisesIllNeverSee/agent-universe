"""ST-004/ST-024 tests for shared operator authentication primitives."""
from __future__ import annotations

import logging
import uuid

from app.auth import secret_matches


def _ip() -> str:
    return f"10.66.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"


def test_secret_comparison_fails_closed():
    assert secret_matches("same-secret", "same-secret")
    assert not secret_matches("wrong-secret", "same-secret")
    assert not secret_matches("", "same-secret")
    assert not secret_matches("same-secret", "")
    assert not secret_matches("", "")


def test_global_admin_rejection_is_logged_without_secret(client, caplog):
    wrong = f"wrong-{uuid.uuid4().hex}"
    ip = _ip()
    caplog.set_level(logging.WARNING, logger="civitae.security")

    response = client.get(
        "/api/operator/stats",
        headers={"X-Admin-Key": wrong, "x-forwarded-for": ip},
    )

    assert response.status_code == 403
    messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "civitae.security"
    ]
    assert any("admin_auth_rejected" in message for message in messages)
    assert all(wrong not in message for message in messages)
    assert all(ip not in message for message in messages)


def test_route_local_admin_rejection_uses_shared_security_log(client, caplog):
    wrong = f"wrong-{uuid.uuid4().hex}"
    ip = _ip()
    caplog.set_level(logging.WARNING, logger="civitae.security")

    response = client.patch(
        "/api/forums/threads/nonexistent-thread/pin",
        json={"pinned": True},
        headers={"X-Admin-Key": wrong, "x-forwarded-for": ip},
    )

    assert response.status_code == 403
    messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "civitae.security"
    ]
    assert any("admin_auth_rejected" in message for message in messages)
    assert all(wrong not in message for message in messages)
    assert all(ip not in message for message in messages)
