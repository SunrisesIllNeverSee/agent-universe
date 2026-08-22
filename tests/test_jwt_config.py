from __future__ import annotations

import os
import unittest
from functools import lru_cache
from unittest.mock import patch

from app.jwt_config import get_kassa_jwt_secret


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
