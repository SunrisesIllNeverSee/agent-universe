from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.data_paths import ensure_data_dir, resolve_data_dir


class DataPathTests(unittest.TestCase):
    def test_resolve_data_dir_uses_repo_style_root_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(resolve_data_dir(root), (root / "data").resolve())

    def test_railway_requires_canonical_mount(self) -> None:
        """When RAILWAY_VOLUME_MOUNT_PATH is set but doesn't include the data dir, raise."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = resolve_data_dir(root)
            with patch.dict(
                os.environ,
                {"RAILWAY_ENVIRONMENT": "production", "RAILWAY_VOLUME_MOUNT_PATH": "/data"},
                clear=False,
            ):
                with self.assertRaises(RuntimeError):
                    ensure_data_dir(data_dir)

    def test_railway_no_mount_path_warns_but_does_not_crash(self) -> None:
        """When RAILWAY_ENVIRONMENT is set but RAILWAY_VOLUME_MOUNT_PATH is absent, warn — do NOT crash.

        Railway sets RAILWAY_ENVIRONMENT automatically but does not set
        RAILWAY_VOLUME_MOUNT_PATH.  The app must start successfully even when
        the operator has not configured that custom env var.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = resolve_data_dir(root)
            # Ensure the custom var is absent for this test
            env_without_mount = {k: v for k, v in os.environ.items() if k != "RAILWAY_VOLUME_MOUNT_PATH"}
            env_without_mount["RAILWAY_ENVIRONMENT"] = "production"
            with patch.dict(os.environ, env_without_mount, clear=True):
                with self.assertLogs("civitae.data", level="WARNING") as logs:
                    ensured = ensure_data_dir(data_dir)
            self.assertEqual(ensured, data_dir)
            self.assertTrue(
                any("RAILWAY_VOLUME_MOUNT_PATH is not set" in line for line in logs.output),
                f"Expected warning about missing RAILWAY_VOLUME_MOUNT_PATH, got: {logs.output}",
            )

    def test_railway_warns_when_multiple_mounts_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = resolve_data_dir(root)
            mounts = f"{data_dir.as_posix()},/data"
            with patch.dict(
                os.environ,
                {"RAILWAY_ENVIRONMENT": "production", "RAILWAY_VOLUME_MOUNT_PATH": mounts},
                clear=False,
            ):
                with self.assertLogs("civitae.data", level="WARNING") as logs:
                    ensured = ensure_data_dir(data_dir)
            self.assertEqual(ensured, data_dir)
            self.assertTrue(any("Multiple Railway volume mounts detected" in line for line in logs.output))


if __name__ == "__main__":
    unittest.main()
