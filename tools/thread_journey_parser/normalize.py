from __future__ import annotations

import hashlib
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


def _active_node_ids(mapping: dict[str, Any], current: str | None) -> set[str]:
    active: set[str] = set()
    node_id = current
    while node_id and node_id in mapping and node_id not in active:
        active.add(node_id)
        node_id = mapping[node_id].get("parent")
    return active


def _branch_id(mapping: dict[str, Any], node_id: str, active: set[str]) -> str:
    if node_id in active:
        return "active"
    cursor = node_id
    branch_root = node_id
    seen: set[str] = set()
    while cursor and cursor in mapping and cursor not in seen:
        seen.add(cursor)
        parent = mapping[cursor].get("parent")
        branch_root = cursor
        if parent in active or not parent:
            break
        cursor = parent
    return f"branch-{branch_root[:8]}"


def _nearest_materialized_parent(
    mapping: dict[str, Any], node_id: str, materialized: set[str]
) -> str | None:
    cursor = mapping.get(node_id, {}).get("parent")
    seen: set[str] = set()
    while cursor and cursor in mapping and cursor not in seen:
        seen.add(cursor)
        if cursor in materialized:
            return cursor
        cursor = mapping[cursor].get("parent")
    return None


def _topology_safe_candidates(
    mapping: dict[str, Any], candidates: list[tuple[str, dict[str, Any]]], order: dict[str, int]
) -> list[tuple[str, dict[str, Any]]]:
    """Topologically order materialized nodes while using timestamps only as a tie-breaker.

    ChatGPT exports can omit create_time on a node. Timestamp-only sorting would assign
    that node time zero and can place a child before its parent. This Kahn-style ordering
    guarantees the nearest materialized ancestor is emitted first; among currently-ready
    nodes, real timestamps and original mapping order preserve chronology as far as the
    source permits.
    """
    by_id = {node_id: node for node_id, node in candidates}
    materialized = set(by_id)
    parent_of = {
        node_id: _nearest_materialized_parent(mapping, node_id, materialized)
        for node_id in materialized
    }
    children: dict[str, list[str]] = {node_id: [] for node_id in materialized}
    indegree = {node_id: 0 for node_id in materialized}
    for child, parent in parent_of.items():
        if parent:
            children[parent].append(child)
            indegree[child] += 1

    def ready_key(node_id: str) -> tuple[int, float, int]:
        msg = (by_id[node_id].get("message") or {})
        created = msg.get("create_time")
        if isinstance(created, (int, float)):
            return (0, float(created), order[node_id])
        return (1, float("inf"), order[node_id])

    ready = sorted((node_id for node_id, degree in indegree.items() if degree == 0), key=ready_key)
    output: list[tuple[str, dict[str, Any]]] = []
    emitted: set[str] = set()
    while ready:
        node_id = ready.pop(0)
        if node_id in emitted:
            continue
        emitted.add(node_id)
        output.append((node_id, by_id[node_id]))
        for child in sorted(children[node_id], key=ready_key):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
        ready.sort(key=ready_key)

    # Malformed/cyclic mappings should still remain inspectable rather than disappear.
    for node_id, node in candidates:
        if node_id not in emitted:
            output.append((node_id, node))
    return output


def _chatgpt_export_messages(data: dict[str, Any]) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    mapping = data.get("mapping")
    if not isinstance(mapping, dict):
        raise ValueError("Not a ChatGPT export conversation")

    current = data.get("current_node")
    active = _active_node_ids(mapping, current if isinstance(current, str) else None)
    order = {node_id: idx for idx, node_id in enumerate(mapping.keys())}
    candidates: list[tuple[str, dict[str, Any]]] = []
    for node_id, node in mapping.items():
        msg = node.get("message")
        if not isinstance(msg, dict):
            continue
        author = msg.get("author") or {}
        role = author.get("role") or "unknown"
        text = _content_to_text(msg.get("content"))
        if not text.strip() and role not in {"tool", "system", "developer"}:
            continue
        candidates.append((node_id, node))

    candidates = _topology_safe_candidates(mapping, candidates, order)
    messages: list[dict[str, Any]] = []
    for node_id, node in candidates:
        msg = node["message"]
        author = msg.get("author") or {}
        role = author.get("role") or "unknown"
        messages.append({
            "role": role,
            "content": _content_to_text(msg.get("content")),
            "timestamp": msg.get("create_time"),
            "metadata": msg.get("metadata") or {},
            "_source_node_id": node_id,
            "_parent_source_node_id": node.get("parent"),
            "_child_source_node_ids": list(node.get("children") or []),
            "_branch_id": _branch_id(mapping, node_id, active),
            "_is_active_path": node_id in active,
        })

    meta = {
        "source_platform": "chatgpt",
        "source_conversation_id": data.get("id") or data.get("conversation_id"),
        "active_leaf_source_node_id": current,
        "source_node_count": len(mapping),
        "materialized_turn_count": len(messages),
        "branch_count": len({m["_branch_id"] for m in messages if m["_branch_id"] != "active"}),
        "node_parents": {node_id: node.get("parent") for node_id, node in mapping.items()},
    }
    return str(data.get("title") or "Untitled thread"), messages, meta


def normalize_messages(messages: list[dict[str, Any]]) -> list[NormalizedTurn]:
    turns: list[NormalizedTurn] = []
    for idx, msg in enumerate(messages, start=1):
        author = msg.get("role") or msg.get("speaker") or msg.get("author") or "unknown"
        if isinstance(author, dict):
            author = author.get("role") or author.get("name") or "unknown"
        speaker = ROLE_MAP.get(str(author).lower(), str(author).upper())
        text = _content_to_text(msg.get("content") if "content" in msg else msg.get("text"))
        turn_id = str(msg.get("_turn_id") or f"T{idx:03d}")
        turns.append(NormalizedTurn(
            turn_id=turn_id,
            speaker=speaker,
            content=text.strip(),
            timestamp=_timestamp(msg.get("timestamp") or msg.get("create_time") or msg.get("created_at")),
            attachments=_extract_attachments(msg, text),
            raw_index=idx,
            source_node_id=msg.get("_source_node_id") or msg.get("node_id") or msg.get("id"),
            parent_source_node_id=msg.get("_parent_source_node_id") or msg.get("parent_node_id") or msg.get("parent_id"),
            child_source_node_ids=list(msg.get("_child_source_node_ids") or msg.get("child_node_ids") or []),
            branch_id=str(msg.get("_branch_id") or "active"),
            is_active_path=bool(msg.get("_is_active_path", True)),
            sequence_index=idx,
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


def _load_json_or_jsonl(path: Path, raw: str) -> Any:
    if path.suffix.lower() == ".jsonl":
        records: list[Any] = []
        for line_number, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL record at line {line_number}: {exc.msg}") from exc
        return records
    return json.loads(raw)


def load_thread_with_archive(path: str | Path) -> tuple[str, list[NormalizedTurn], list[NormalizedTurn], dict[str, Any]]:
    """Load a thread for analysis while retaining the complete source topology.

    The primary parser analyzes the active ChatGPT path so abandoned branches cannot
    accidentally influence continuation/authority. The canonical CSV layer receives
    all materialized turns and preserves their parent/child topology separately.
    """
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    source_meta: dict[str, Any] = {
        "raw_source_path": str(p),
        "raw_source_hash": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "source_platform": "markdown" if p.suffix.lower() not in {".json", ".jsonl"} else "generic_json",
    }

    if p.suffix.lower() in {".json", ".jsonl"}:
        data = _load_json_or_jsonl(p, raw)
        if isinstance(data, dict) and isinstance(data.get("mapping"), dict):
            title, messages, chatgpt_meta = _chatgpt_export_messages(data)
            source_meta.update(chatgpt_meta)
            all_turns = normalize_messages(messages)
            active_turns = [turn for turn in all_turns if turn.is_active_path]
            if not active_turns:
                active_turns = all_turns
            return title, active_turns, all_turns, source_meta
        title, messages = _generic_messages(data)
        all_turns = normalize_messages(messages)
        source_meta["materialized_turn_count"] = len(all_turns)
        source_meta["branch_count"] = 0
        return title, all_turns, all_turns, source_meta

    all_turns = parse_markdown_transcript(raw)
    source_meta["materialized_turn_count"] = len(all_turns)
    source_meta["branch_count"] = 0
    return p.stem, all_turns, all_turns, source_meta


def load_thread(path: str | Path) -> tuple[str, list[NormalizedTurn]]:
    """Backward-compatible loader returning the active analytical path."""
    title, active_turns, _all_turns, _meta = load_thread_with_archive(path)
    return title, active_turns
