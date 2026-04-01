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
