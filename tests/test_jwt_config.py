from __future__ import annotations

import os
import unittest
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from unittest.mock import patch

import jwt as pyjwt

from app.jwt_config import (
    JWT_AUDIENCE,
    JWT_ISSUER,
    JWT_LEGACY_IAT_CUTOFF,
    get_kassa_jwt_secret,
    issue_agent_jwt,
    verify_jwt,
)


class JwtConfigTests(unittest.TestCase):
    def test_prefers_kassa_secret(self) -> None:
        # Exercise the uncached implementation so the test does not disturb the
        # process-wide secret already consumed by application modules.
        raw_get_secret = get_kassa_jwt_secret.__wrapped__
        with patch.dict(
            os.environ,
            {"KASSA_JWT_SECRET": "kassa-secret", "JWT_SECRET": "jwt-secret"},
            clear=True,
        ):
            self.assertEqual(raw_get_secret(), "kassa-secret")

    def test_falls_back_to_jwt_secret(self) -> None:
        raw_get_secret = get_kassa_jwt_secret.__wrapped__
        with patch.dict(os.environ, {"JWT_SECRET": "jwt-secret"}, clear=True):
            self.assertEqual(raw_get_secret(), "jwt-secret")

    def test_issued_token_has_scope_and_verifies(self) -> None:
        token = issue_agent_jwt("agent-test", "Test Agent")
        claims = verify_jwt(token)
        self.assertIsNotNone(claims)
        self.assertEqual(claims["sub"], "agent-test")
        self.assertEqual(claims["iss"], JWT_ISSUER)
        self.assertEqual(claims["aud"], JWT_AUDIENCE)

    def test_wrong_issuer_or_audience_is_rejected(self) -> None:
        now = datetime.now(UTC)
        secret = get_kassa_jwt_secret()
        token = pyjwt.encode(
            {
                "sub": "agent-test",
                "name": "Test Agent",
                "iss": "https://wrong.example",
                "aud": "wrong-audience",
                "iat": now,
                "exp": now + timedelta(hours=1),
            },
            secret,
            algorithm="HS256",
        )
        self.assertIsNone(verify_jwt(token))

    def test_pre_migration_legacy_token_is_temporarily_accepted(self) -> None:
        secret = get_kassa_jwt_secret()
        issued_at = datetime(2026, 10, 2, 0, 0, 0, tzinfo=UTC)
        token = pyjwt.encode(
            {
                "sub": "agent-legacy",
                "name": "Legacy",
                "iat": issued_at,
                "exp": datetime.now(UTC) + timedelta(hours=1),
            },
            secret,
            algorithm="HS256",
        )
        claims = verify_jwt(token)
        self.assertIsNotNone(claims)
        self.assertEqual(claims["sub"], "agent-legacy")

    def test_post_cutoff_unscoped_token_is_rejected(self) -> None:
        secret = get_kassa_jwt_secret()
        issued_at = datetime.fromtimestamp(JWT_LEGACY_IAT_CUTOFF + 60, UTC)
        token = pyjwt.encode(
            {
                "sub": "agent-unscoped",
                "name": "Unscoped",
                "iat": issued_at,
                "exp": issued_at + timedelta(hours=1),
            },
            secret,
            algorithm="HS256",
        )
        self.assertIsNone(verify_jwt(token))

    def test_ephemeral_secret_is_shared_within_process(self) -> None:
        # Give the underlying implementation a private cache for this test.
        # Clearing the application's real cache would invalidate module-level
        # JWT signers already initialized during test collection.
        isolated_get_secret = lru_cache(maxsize=1)(get_kassa_jwt_secret.__wrapped__)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertLogs("civitae", level="WARNING") as logs:
                first = isolated_get_secret()
                second = isolated_get_secret()
        self.assertEqual(first, second)
        self.assertEqual(len(logs.output), 1)
        self.assertTrue(any("KASSA_JWT_SECRET and JWT_SECRET not set" in line for line in logs.output))


if __name__ == "__main__":
    unittest.main()
