from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Attachment:
    name: str
    kind: str = "document"
    uri: str | None = None
    content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NormalizedTurn:
    turn_id: str
    speaker: str
    content: str
    timestamp: str | None = None
    attachments: list[Attachment] = field(default_factory=list)
    raw_index: int = 0


@dataclass
class ExtractedItem:
    item_id: str
    category: str
    statement: str
    introduced_at: str
    authority: str
    authority_weight: float
    status: str
    confidence: float
    source_turns: list[str] = field(default_factory=list)
    related_turns: list[str] = field(default_factory=list)
    supersedes: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class TurnRecord:
    turn_id: str
    speaker: str
    timestamp: str | None
    summary: str
    categories: list[str]
    authority: str
    authority_weight: float
    items: list[str] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    raw_text: str = ""


@dataclass
class FlowRecord:
    from_turn: str
    to_turn: str
    relation: str
    confidence: float
    elapsed_seconds: float | None = None
    temporal_signal: str | None = None
    evidence: list[str] = field(default_factory=list)


@dataclass
class DocumentRecord:
    document_id: str
    name: str
    introduced_at: str
    introduced_by: str
    kind: str
    status: str = "INTRODUCED"
    roles: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    uri: str | None = None
    content_hash: str | None = None
    content_excerpt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ThreadFoundation:
    purpose: str
    initial_goal: str
    starting_state: list[str]
    initial_requests: list[str]
    initial_scope: dict[str, list[str]]
    key_entities: list[str]
    source_turns: list[str]


@dataclass
class ThreadLedger:
    schema_version: str
    thread_id: str
    title: str
    foundation: ThreadFoundation
    turns: list[TurnRecord]
    flows: list[FlowRecord]
    items: list[ExtractedItem]
    documents: list[DocumentRecord]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
