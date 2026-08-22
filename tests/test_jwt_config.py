from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.jwt_config import clear_kassa_jwt_secret_cache, get_kassa_jwt_secret


class JwtConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        # The application imports JWT configuration during test collection and
        # may populate the lru_cache before this test module runs. Each case
        # must start from an empty cache so environment patches are authoritative.
        clear_kassa_jwt_secret_cache()

    def tearDown(self) -> None:
        clear_kassa_jwt_secret_cache()

    def test_prefers_kassa_secret(self) -> None:
        with patch.dict(
            os.environ,
            {"KASSA_JWT_SECRET": "kassa-secret", "JWT_SECRET": "jwt-secret"},
            clear=True,
        ):
            self.assertEqual(get_kassa_jwt_secret(), "kassa-secret")

    def test_falls_back_to_jwt_secret(self) -> None:
        with patch.dict(os.environ, {"JWT_SECRET": "jwt-secret"}, clear=True):
            self.assertEqual(get_kassa_jwt_secret(), "jwt-secret")

    def test_ephemeral_secret_is_shared_within_process(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertLogs("civitae", level="WARNING") as logs:
                first = get_kassa_jwt_secret()
                second = get_kassa_jwt_secret()
        self.assertEqual(first, second)
        self.assertEqual(len(logs.output), 1)
        self.assertTrue(any("KASSA_JWT_SECRET and JWT_SECRET not set" in line for line in logs.output))


if __name__ == "__main__":
    unittest.main()
