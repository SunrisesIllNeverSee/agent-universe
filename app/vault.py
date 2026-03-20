from __future__ import annotations

from collections.abc import Iterable


class VaultState:
    def __init__(self, manifest: dict[str, list[str]]) -> None:
        self.manifest = manifest
        self.loaded: list[str] = []

    def contains(self, filename: str) -> bool:
        return any(filename in files for files in self.manifest.values())

    def load(self, filename: str) -> list[str]:
        if self.contains(filename) and filename not in self.loaded:
            self.loaded.append(filename)
        return self.loaded

    def unload(self, filename: str) -> list[str]:
        if filename in self.loaded:
            self.loaded.remove(filename)
        return self.loaded

    def set_loaded(self, filenames: Iterable[str]) -> None:
        self.loaded = [filename for filename in filenames if self.contains(filename)]
