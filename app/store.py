from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock

from .models import MessageRecord


class MessageStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._messages: list[MessageRecord] = []
        self._observers: list = []
        self._next_id = 1
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = MessageRecord.model_validate_json(line)
            self._messages.append(record)
            self._next_id = max(self._next_id, record.id + 1)

    def observe(self, callback) -> None:
        self._observers.append(callback)

    def add(self, record: MessageRecord) -> MessageRecord:
        with self._lock:
            saved = record.model_copy(update={"id": self._next_id})
            self._next_id += 1
            self._messages.append(saved)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(saved.model_dump_json())
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        for observer in self._observers:
            observer(saved)
        return saved

    def recent(self, limit: int = 50) -> list[MessageRecord]:
        return self._messages[-limit:]

    def since(self, message_id: int) -> list[MessageRecord]:
        return [message for message in self._messages if message.id > message_id]

    def all(self) -> list[MessageRecord]:
        return list(self._messages)
