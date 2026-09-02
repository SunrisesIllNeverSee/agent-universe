from __future__ import annotations

import re
from dataclasses import dataclass

from .models import ExtractedItem, ThreadLedger


@dataclass(frozen=True)
class Rule:
    category: str
    patterns: tuple[str, ...]
    user_only: bool = True
    confidence: float = 0.82


RULES = (
    Rule("PREFERENCE", (
        r"\bi prefer\b", r"\bi like\b", r"\bi don't like\b", r"\bi do not like\b",
        r"\bi would rather\b", r"\bi rather\b",
    )),
    Rule("CONSTRAINT", (
        r"\bmust\b", r"\bmust not\b", r"\bdo not\b", r"\bdon't\b", r"\bcannot\b",
        r"\bcan't\b", r"\bonly\b", r"\bnon-negotiable\b", r"\bimportant rule\b",
    )),
    Rule("DEFINITION", (
        r"\bmeans\b", r"\bdefine(?:d|s)?\b", r"\bby .* i mean\b", r"\bthe distinction is\b",
        r"\bthe point is\b",
    )),
    Rule("FACT", (
        r"\bi have\b", r"\bwe have\b", r"\bi use\b", r"\bwe use\b",
        r"\bthe repo is\b", r"\bthe repository is\b", r"\bthe file is\b",
        r"\bis located (?:at|in)\b", r"\blives (?:at|in|under)\b",
    ), confidence=0.76),
    Rule("OBJECTIVE", (
        r"\bi want\b", r"\bwe want\b", r"\bmy goal is\b", r"\bour goal is\b",
        r"\bthe goal is\b", r"\bthe objective is\b", r"\bi need\b", r"\bwe need\b",
    ), confidence=0.80),
    Rule("CONTEXT", (
        r"\bfor context\b", r"\bbackground\b", r"\bcurrently\b", r"\bright now\b",
        r"\bthe situation is\b", r"\bwhere we are\b",
    ), confidence=0.72),
)


def _sentence_candidates(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    pieces = re.split(r"(?<=[.!?])\s+|\n+", compact)
    return [piece.strip() for piece in pieces if piece.strip()]


def _authority_for_turn(ledger: ThreadLedger, turn_id: str) -> tuple[str, float]:
    record = next((turn for turn in ledger.turns if turn.turn_id == turn_id), None)
    if record is None:
        return "UNKNOWN", 0.0
    return record.authority, record.authority_weight


def enrich_context_records(ledger: ThreadLedger) -> ThreadLedger:
    """Add conservative Rethread-style descriptive records without changing canon.

    Facts, preferences, constraints, definitions, objectives, and context remain
    source-bound observations. They never become decisions/canon merely because the
    enrichment layer detected them. The operation is idempotent.
    """
    existing = {(item.category, item.introduced_at, item.statement) for item in ledger.items}
    max_id = 0
    for item in ledger.items:
        try:
            max_id = max(max_id, int(item.item_id.split("-")[-1]))
        except ValueError:
            continue

    raw_turns = {turn.turn_id: turn.raw_text for turn in ledger.turns}
    speakers = {turn.turn_id: turn.speaker for turn in ledger.turns}
    for turn_id, text in raw_turns.items():
        speaker = speakers.get(turn_id, "UNKNOWN")
        for sentence in _sentence_candidates(text):
            for rule in RULES:
                if rule.user_only and speaker != "USER":
                    continue
                if not any(re.search(pattern, sentence, flags=re.I) for pattern in rule.patterns):
                    continue
                statement = sentence[:500]
                signature = (rule.category, turn_id, statement)
                if signature in existing:
                    continue
                max_id += 1
                authority, weight = _authority_for_turn(ledger, turn_id)
                ledger.items.append(ExtractedItem(
                    item_id=f"I-{max_id:04d}",
                    category=rule.category,
                    statement=statement,
                    introduced_at=turn_id,
                    authority=authority,
                    authority_weight=weight,
                    status="OBSERVED",
                    confidence=rule.confidence,
                    source_turns=[turn_id],
                    notes=[
                        "Context enrichment record; descriptive only. It does not become a decision or canon update without independent evidence."
                    ],
                ))
                existing.add(signature)
                break

    ledger.metadata["context_enrichment"] = True
    ledger.metadata["context_categories"] = [rule.category for rule in RULES]
    return ledger
