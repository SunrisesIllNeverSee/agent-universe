from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def freeze_run(
    *,
    input_path: str | Path,
    run_output: str | Path,
    archive_root: str | Path,
    thread_id: str,
    parser_version: str,
    schema_version: str,
    source_meta: dict[str, Any] | None = None,
) -> Path:
    """Freeze one parse run without mutating the source or parser output.

    Layout:
      <archive_root>/<YYYY-MM-DD>/<thread_id>/<UTC timestamp>/
        raw/source.<ext>
        output/...
        manifest.json

    Existing frozen runs are never overwritten.
    """
    source = Path(input_path).expanduser().resolve()
    output = Path(run_output).expanduser().resolve()
    root = Path(archive_root).expanduser().resolve()
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    destination = root / now.strftime("%Y-%m-%d") / thread_id / stamp
    suffix = 1
    while destination.exists():
        destination = root / now.strftime("%Y-%m-%d") / thread_id / f"{stamp}-{suffix}"
        suffix += 1

    raw_dir = destination / "raw"
    frozen_output = destination / "output"
    raw_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(source, raw_dir / f"source{source.suffix or '.txt'}")
    shutil.copytree(output, frozen_output)

    files: list[dict[str, Any]] = []
    for path in sorted(destination.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files.append({
                "path": str(path.relative_to(destination)),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            })

    manifest = {
        "archive_schema": "0.1.0",
        "thread_id": thread_id,
        "created_at": now.isoformat(),
        "immutable": True,
        "parser_version": parser_version,
        "parser_schema": schema_version,
        "input": {
            "original_path": str(source),
            "sha256": _sha256(source),
            "source_platform": (source_meta or {}).get("source_platform", "unknown"),
            "source_conversation_id": (source_meta or {}).get("source_conversation_id", ""),
        },
        "files": files,
        "archive_policy": "append-only; new parser versions create new runs rather than replacing prior outputs",
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return destination
