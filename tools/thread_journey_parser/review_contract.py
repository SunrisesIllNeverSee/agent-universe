from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import ThreadLedger


REVIEW_CONTRACT_VERSION = "0.1.0"
HIGH_IMPACT_CATEGORIES = {
    "DECISION", "CANON_UPDATE", "CORRECTION", "DEFERRED_ERROR",
    "ACTION", "IMPLEMENTED", "VERIFICATION", "ERROR", "MISDIRECTION",
}
HIGH_IMPACT_FLOWS = {
    "ACCEPT_BY_CONTINUATION", "BUILD_ON", "PIVOT", "CORRECTION",
    "DEFERRED_ERROR", "RECOVERY", "RETURN",
}


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_moses_review_packet(ledger: ThreadLedger, raw_source_hash: str = "") -> dict[str, Any]:
    """Create a read-only third-party review packet.

    MO§ES is deliberately outside the parser's authority path. It receives the parser's
    claims plus source lineage, reviews the transformation under the Six Fold Flame, and
    returns annotations. It must not rewrite parser records or promote canon.
    """
    high_impact_items = [
        {
            "item_id": item.item_id,
            "category": item.category,
            "statement": item.statement,
            "status": item.status,
            "authority": item.authority,
            "authority_weight": item.authority_weight,
            "source_turns": item.source_turns,
            "related_turns": item.related_turns,
            "supersedes": item.supersedes,
            "evolution": [event.__dict__ for event in item.evolution],
        }
        for item in ledger.items
        if item.category in HIGH_IMPACT_CATEGORIES
        or item.status in {"IMPLICITLY_ACCEPTED", "SUPERSEDED", "CHALLENGED"}
    ]
    flows = [
        {
            "from_turn": flow.from_turn,
            "to_turn": flow.to_turn,
            "relation": flow.relation,
            "confidence": flow.confidence,
            "temporal_signal": flow.temporal_signal,
            "evidence": flow.evidence,
        }
        for flow in ledger.flows
        if flow.relation in HIGH_IMPACT_FLOWS
    ]
    turn_ids = {
        turn_id
        for item in high_impact_items
        for turn_id in item.get("source_turns", []) + item.get("related_turns", [])
    }
    for flow in flows:
        turn_ids.add(flow["from_turn"])
        turn_ids.add(flow["to_turn"])
    source_turns = [
        {
            "turn_id": turn.turn_id,
            "speaker": turn.speaker,
            "timestamp": turn.timestamp,
            "authority": turn.authority,
            "categories": turn.categories,
            "raw_text": turn.raw_text,
        }
        for turn in ledger.turns
        if turn.turn_id in turn_ids
    ]

    target = {
        "thread_id": ledger.thread_id,
        "parser_schema": ledger.schema_version,
        "foundation": ledger.foundation.__dict__,
        "items": high_impact_items,
        "flows": flows,
        "source_turns": source_turns,
        "raw_source_hash": raw_source_hash,
    }
    return {
        "review_contract_version": REVIEW_CONTRACT_VERSION,
        "reviewer_requested": "MO§ES",
        "relationship": "independent_third_party_review",
        "read_only": True,
        "review_target_hash": _stable_hash(target),
        "review_target": target,
        "constitutional_questions": {
            "sovereignty": "Is every material parser claim traceable to the actor/source turn that can legitimately support it?",
            "compression": "Did the parse/report preserve the material commitment and distinctions while compressing the thread?",
            "purpose": "Does each high-impact interpretation serve the stated thread-analysis purpose rather than introduce unrelated inference?",
            "modularity": "Are parser inference, source evidence, authority, and third-party review kept as separate layers?",
            "verifiability": "Can each material conclusion be checked against cited turns/documents/evidence?",
            "reciprocal_resonance": "Would an independent reviewer reconstruct substantially the same state transition from the supplied evidence?",
        },
        "required_review_rules": [
            "Do not mutate parser output.",
            "Do not promote parser or reviewer inference into canon.",
            "Flag contested authority lifts, missing lineage, over-compression, and unresolved objections.",
            "Return one or more review records using the response schema below.",
        ],
        "response_schema": {
            "reviews": [{
                "review_id": "REV-0001",
                "reviewer": "MO§ES",
                "target_type": "item|flow|thread_parse|final_report",
                "target_id": "I-0001|T001->T002|THREAD-...",
                "review_version": "string",
                "review_timestamp": "ISO-8601",
                "sovereignty": "SOUND|WARNING|CONTESTED|UNVERIFIABLE",
                "compression": "SOUND|WARNING|CONTESTED|UNVERIFIABLE",
                "purpose": "SOUND|WARNING|CONTESTED|UNVERIFIABLE",
                "modularity": "SOUND|WARNING|CONTESTED|UNVERIFIABLE",
                "verifiability": "SOUND|WARNING|CONTESTED|UNVERIFIABLE",
                "reciprocal_resonance": "SOUND|WARNING|CONTESTED|UNVERIFIABLE",
                "overall_disposition": "SOUND|WARNING|CONTESTED|UNVERIFIABLE",
                "concern": "string",
                "recommendation": "string",
                "review_evidence": ["T001", "T002"],
            }]
        },
    }


def write_moses_review_packet(ledger: ThreadLedger, path: str | Path, raw_source_hash: str = "") -> Path:
    output = Path(path)
    output.write_text(
        json.dumps(build_moses_review_packet(ledger, raw_source_hash=raw_source_hash), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output


def load_review_response(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("reviews"), list):
        raise ValueError("MO§ES review response must be a JSON object containing a 'reviews' array")
    reviews: list[dict[str, Any]] = []
    for review in data["reviews"]:
        if isinstance(review, dict):
            normalized = dict(review)
            normalized.setdefault("reviewer", "MO§ES")
            reviews.append(normalized)
    return reviews
