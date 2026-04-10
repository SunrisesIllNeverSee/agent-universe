"""
metrics_io.py — Shared metrics I/O helpers for CIVITAE route modules.

Consolidates _atomic_write and _load_metrics/_save_metrics which were
previously duplicated across 6-7 route files. Single source of truth means
bug fixes (e.g. corruption guard) apply everywhere automatically.

Usage:
    from app.metrics_io import atomic_write, load_metrics, save_metrics
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from app.deps import state

_METRICS_DEFAULT = {
    "agents": {},
    "missions": {},
    "financial": {"revenue": 0, "costs": 0, "transactions": []},
}


def atomic_write(path: Path, data: str) -> None:
    """Write data to a file atomically via tmp-then-rename.

    Creates parent directories if needed. Guarantees the file is either
    fully written or unchanged — no partial writes visible to readers.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _get_metrics_path() -> Path:
    return state.data_path("metrics.json")


def load_metrics() -> dict:
    """Load metrics.json with corruption guard and default key backfill.

    Returns a dict with guaranteed top-level keys: agents, missions, financial.
    Falls back to defaults on missing file, JSON decode error, or any exception.
    """
    p = _get_metrics_path()
    if p.exists():
        try:
            m = json.loads(p.read_text())
            # Ensure required top-level keys exist — guards against corruption
            for key, val in _METRICS_DEFAULT.items():
                m.setdefault(key, val)
            return m
        except Exception:
            return dict(_METRICS_DEFAULT)
    return dict(_METRICS_DEFAULT)


def save_metrics(m: dict) -> None:
    """Save metrics dict atomically."""
    atomic_write(_get_metrics_path(), json.dumps(m, indent=2))
