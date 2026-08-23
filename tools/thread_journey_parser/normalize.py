from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Attachment, NormalizedTurn


ROLE_MAP = {
    "user": "USER",
    "assistant": "ASSISTANT",
    "system": "SYSTEM",
    "tool": "TOOL",
    "developer": "DEVELOPER",
}


def _timestamp(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    return str(value)


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_content_to_text(x) for x in content if x is not None)
    if isinstance(content, dict):
        if "parts" in content:
            return _content_to_text(content.get("parts"))
        for key in ("text", "content", "value"):
            if key in content:
                return _content_to_text(content[key])
    return str(content)


def _extract_attachments(message: dict[str, Any], text: str) -> list[Attachment]:
    out: list[Attachment] = []
    seen: set[str] = set()
    metadata = message.get("metadata") or {}
    candidates = []
    for key in ("attachments", "files"):
        value = message.get(key) or metadata.get(key)
        if isinstance(value, list):
            candidates.extend(value)
    for item in candidates:
        if isinstance(item, str):
            name, uri = Path(item).name, item
            content = None
            meta = {}
        elif isinstance(item, dict):
            name = str(item.get("name") or item.get("filename") or item.get("file_name") or item.get("title") or "attachment")
            uri = item.get("url") or item.get("uri") or item.get("path")
            content = item.get("content") or item.get("text")
            meta = {k: v for k, v in item.items() if k not in {"name", "filename", "file_name", "title", "url", "uri", "path", "content", "text"}}
        else:
            continue
        if name not in seen:
            seen.add(name)
            out.append(Attachment(name=name, uri=uri, content=str(content) if content is not None else None, metadata=meta))

    for match in re.finditer(r'<<File name=["\']([^"\']+)["\']>>', text, flags=re.I):
        name = match.group(1).strip()
        if name and name not in seen:
            seen.add(name)
            out.append(Attachment(name=name))
    return out


def _generic_messages(data: Any) -> tuple[str, list[dict[str, Any]]]:
    if isinstance(data, list):
        return "Untitled thread", data
    if isinstance(data, dict):
        for key in ("messages", "turns", "conversation"):
            if isinstance(data.get(key), list):
                return str(data.get("title") or "Untitled thread"), data[key]
    raise ValueError("Unsupported generic JSON thread format")


def _chatgpt_export(data: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    mapping = data.get("mapping")
    if not isinstance(mapping, dict):
        raise ValueError("Not a ChatGPT export conversation")

    ordered_nodes: list[dict[str, Any]] = []
    current = data.get("current_node")
    if current and current in mapping:
        seen: set[str] = set()
        chain: list[dict[str, Any]] = []
        node_id = current
        while node_id and node_id in mapping and node_id not in seen:
            seen.add(node_id)
            node = mapping[node_id]
            chain.append(node)
            node_id = node.get("parent")
        ordered_nodes = list(reversed(chain))
    else:
        ordered_nodes = sorted(
            mapping.values(),
            key=lambda n: ((n.get("message") or {}).get("create_time") or 0),
        )

    messages: list[dict[str, Any]] = []
    for node in ordered_nodes:
        msg = node.get("message")
        if not isinstance(msg, dict):
            continue
        author = msg.get("author") or {}
        role = author.get("role") or "unknown"
        text = _content_to_text(msg.get("content"))
        if not text.strip() and role not in {"tool", "system"}:
            continue
        messages.append({
            "role": role,
            "content": text,
            "timestamp": msg.get("create_time"),
            "metadata": msg.get("metadata") or {},
        })
    return str(data.get("title") or "Untitled thread"), messages


def load_thread(path: str | Path) -> tuple[str, list[NormalizedTurn]]:
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    if p.suffix.lower() in {".json", ".jsonl"}:
        data = json.loads(raw)
        if isinstance(data, dict) and isinstance(data.get("mapping"), dict):
            title, messages = _chatgpt_export(data)
        else:
            title, messages = _generic_messages(data)
        return title, normalize_messages(messages)
    return p.stem, parse_markdown_transcript(raw)


def normalize_messages(messages: list[dict[str, Any]]) -> list[NormalizedTurn]:
    turns: list[NormalizedTurn] = []
    for idx, msg in enumerate(messages, start=1):
        author = msg.get("role") or msg.get("speaker") or msg.get("author") or "unknown"
        if isinstance(author, dict):
            author = author.get("role") or author.get("name") or "unknown"
        speaker = ROLE_MAP.get(str(author).lower(), str(author).upper())
        text = _content_to_text(msg.get("content") if "content" in msg else msg.get("text"))
        turn_id = f"T{len(turns)+1:03d}"
        turns.append(NormalizedTurn(
            turn_id=turn_id,
            speaker=speaker,
            content=text.strip(),
            timestamp=_timestamp(msg.get("timestamp") or msg.get("create_time") or msg.get("created_at")),
            attachments=_extract_attachments(msg, text),
            raw_index=idx,
        ))
    return turns


TRANSCRIPT_HEADER = re.compile(
    r"^(?:\[(?P<ts>[^\]]+)\]\s*)?(?P<role>User|Assistant|System|Tool|Developer)\s*:\s*(?P<body>.*)$",
    re.I,
)


def parse_markdown_transcript(raw: str) -> list[NormalizedTurn]:
    messages: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in raw.splitlines():
        m = TRANSCRIPT_HEADER.match(line)
        if m:
            if current:
                messages.append(current)
            current = {
                "role": m.group("role").lower(),
                "content": m.group("body"),
                "timestamp": m.group("ts"),
            }
        elif current is not None:
            current["content"] += "\n" + line
    if current:
        messages.append(current)
    if not messages:
        raise ValueError("Markdown transcript must contain 'User:'/'Assistant:' turn headers")
    return normalize_messages(messages)
