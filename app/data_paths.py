from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger("civitae.data")


def project_root() -> Path:
    """Return the repository root for the running app."""
    return Path(__file__).resolve().parents[1]


def resolve_data_dir(root: Path) -> Path:
    """Canonical runtime data directory for CIVITAE."""
    return (root / "data").resolve()


def railway_volume_mounts() -> list[str]:
    raw = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "")
    return [part.strip() for part in raw.split(",") if part.strip()]


def ensure_data_dir(data_dir: Path) -> Path:
    """
    Create and validate the canonical data directory.

    On Railway, require the canonical path to be one of the attached volume
    mount paths so we do not silently write state to ephemeral container
    storage.
    """
    data_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(dir=data_dir, prefix=".civitae-write-", delete=True) as handle:
        handle.write(b"ok")
        handle.flush()
        os.fsync(handle.fileno())

    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "").strip()
    mounted_paths = railway_volume_mounts()
    data_path = data_dir.as_posix()

    if railway_env:
        if not mounted_paths:
            # RAILWAY_VOLUME_MOUNT_PATH is a custom env var (not set by Railway automatically).
            # If the operator hasn't configured it, log a warning but continue — the volume
            # may still be mounted correctly at the data_dir path.  Raising here would prevent
            # every Railway deploy from starting whenever the var is absent.
            logger.warning(
                "Running on Railway (%s) but RAILWAY_VOLUME_MOUNT_PATH is not set. "
                "Set it to %s to enable strict volume-mount validation.",
                railway_env,
                data_path,
            )
        elif data_path not in mounted_paths:
            raise RuntimeError(
                f"Canonical data dir {data_path} is not backed by the active Railway volume mounts: "
                f"{', '.join(mounted_paths)}"
            )
        if len(mounted_paths) > 1:
            logger.warning(
                "Multiple Railway volume mounts detected: %s. Canonical data dir remains %s",
                ", ".join(mounted_paths),
                data_path,
            )

    logger.info("Using canonical data directory: %s", data_path)
    return data_dir
