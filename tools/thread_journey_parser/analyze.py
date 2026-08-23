from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .models import (
    DocumentRecord,
    ExtractedItem,
    FlowRecord,
    NormalizedTurn,
    ThreadFoundation,
    ThreadLedger,
    TurnRecord,
)


CATEGORY_PATTERNS: dict[str, list[str]] = {
    "ACTION": [r"\bplease\b", r"\bbuild\b", r"\bimplement\b", r"\bcheck\b", r"\baudit\b", r"\bfix\b", r"\bcreate\b", r"\bmake\b", r"\bneed to\b", r"\bshould do\b"],
    "IMPLEMENTED": [r"\bimplemented\b", r"\bmerged\b", r"\bpushed\b", r"\bdeployed\b", r"\bcreated\b", r"\bupdated\b", r"\bremoved\b", r"\badded\b", r"\blanded\b"],
    "IDEA": [r"\bidea\b", r"\bwhat if\b", r"\bmaybe\b", r"\bcould we\b", r"\bthinking of\b", r"\bcurious\b", r"\bi wonder\b"],
    "DECISION": [r"\blet'?s\b", r"\bwe(?:'ll| will)\b", r"\bgoing with\b", r"\bdo that\b", r"\bkeep that\b", r"\buse that\b", r"\bthat works\b"],
    "CANON_UPDATE": [r"\bfrom now on\b", r"\bclarif(?:y|ication)\b", r"\bactually\b", r"\bmeans?\b", r"\bthe point is\b", r"\bimportant distinction\b"],
    "DIRECTION_CHANGE": [r"\bnew topic\b", r"\bnew direction\b", r"\bsidebar\b", r"\bback to\b", r"\bforget that\b", r"\binstead\b", r"\bpivot\b"],
    "ERROR": [r"\bwrong\b", r"\bincorrect\b", r"\berror\b", r"\bbroken\b", r"\bfailed\b", r"\bmissed\b", r"\bforgot\b"],
    "MISDIRECTION": [r"\bnot what i (?:asked|wanted|meant)\b", r"\bwent off (?:track|course)\b", r"\bdrift(?:ed|ing)?\b", r"\bwrong direction\b", r"\bwe got off track\b"],
    "CORRECTION": [r"^\s*no[,\s]", r"\bthat'?s not\b", r"\bi meant\b", r"\byou misunderstood\b", r"\bcorrection\b", r"\bnot what i\b"],
    "CODE": [r"```", r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+/", r"\b[a-zA-Z0-9_./-]+\.(?:py|js|ts|tsx|json|ya?ml|md|html|toml)\b"],
    "VERIFICATION": [r"\bverified\b", r"\bconfirmed\b", r"\bchecked\b", r"\bfound\b", r"\blive .*returns?\b", r"\btest(?:ed|s pass| passed)\b"],
    "OPEN_QUESTION": [r"\?", r"\bunresolved\b", r"\bneed to decide\b", r"\bopen question\b"],
    "ARTIFACT": [r"\b[a-zA-Z0-9_.-]+\.(?:md|pdf|docx|txt|json|ya?ml|py|js|html|zip|tar\.gz)\b", r"https?://"],
}

PIVOT_PATTERNS = [r"\bnew topic\b", r"\bnew direction\b", r"\bsidebar\b", r"\bback to\b", r"\bforget that\b", r"\bswitch(?:ing)? to\b"]
DEFER_PATTERNS = [r"\bdeal with (?:it|that) later\b", r"\bleave (?:it|that) for (?:now|later)\b", r"\bnot now\b", r"\bkeep going\b", r"\bdon'?t (?:fix|stop)\b", r"\bpreserve (?:the )?flow\b"]
NEGATIVE_PATTERNS = [r"\bwrong\b", r"\bno\b", r"\bnot right\b", r"\bmisunderstood\b", r"\bmissed\b", r"\bincorrect\b"]
BUILD_PATTERNS = [r"\bthen\b", r"\balso\b", r"\bwhat about\b", r"\badd\b", r"\bfrom there\b", r"\bnext\b", r"\bgo on\b", r"\bbuild (?:on|that|it)\b", r"\band if\b"]
EXPLICIT_ACCEPT_PATTERNS = [r"^\s*(?:yes|yeah|yep|correct|exactly|perfect|good|great)\b", r"\bdo that\b", r"\bthat works\b", r"\bkeep it\b"]
SUGGESTION_PATTERNS = [r"\bi would\b", r"\bi recommend\b", r"\bwe should\b", r"\bcould\b", r"\bconsider\b", r"\bprobably\b"]

DOC_RE = re.compile(r"(?<![\w/.-])([A-Za-z0-9_./-]+\.(?:md|pdf|docx|txt|json|ya?ml|py|js|html|zip|tar\.gz))(?![\w-])", re.I)
ENTITY_RE = re.compile(r"\b(?:Signomy|CIVITAE|KA§§A|KASSA|MO§ES|SignalAF|SigRank|GitHub|Vercel|Railway|OpenAI|Claude|Gemini|Codex)\b", re.I)


def _has(patterns: Iterable[str], text: str) -> bool:
    return any(re.search(p, text, flags=re.I | re.M) for p in patterns)


def _summary(text: str, limit: int = 220) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def _authority(speaker: str, categories: list[str]) -> tuple[str, float]:
    if speaker == "USER":
        if "CORRECTION" in categories or "DECISION" in categories or "CANON_UPDATE" in categories:
            return "USER_EXPLICIT", 1.0
        return "USER_STATEMENT", 0.80
    if speaker == "TOOL":
        return "TOOL_EVIDENCE", 0.90
    if speaker == "SYSTEM":
        return "SYSTEM_CONTEXT", 0.85
    if speaker == "ASSISTANT":
        if "VERIFICATION" in categories or "IMPLEMENTED" in categories:
            return "ASSISTANT_REPORTED_EVIDENCE", 0.65
        if "SUGGESTION" in categories:
            return "ASSISTANT_PROPOSED", 0.30
        return "ASSISTANT_INFERRED", 0.15
    return f"{speaker}_STATEMENT", 0.40


def _categories(turn: NormalizedTurn) -> tuple[list[str], list[str]]:
    text = turn.content
    categories: set[str] = set()
    signals: list[str] = []
    for category, patterns in CATEGORY_PATTERNS.items():
        if _has(patterns, text):
            categories.add(category)
    if turn.speaker == "ASSISTANT" and _has(SUGGESTION_PATTERNS, text):
        categories.add("SUGGESTION")
    if _has(DEFER_PATTERNS, text) and _has(NEGATIVE_PATTERNS, text):
        categories.add("DEFERRED_ERROR")
        signals.append("explicit_defer_after_objection")
    if not categories:
        categories.add("FOUNDATION" if turn.turn_id == "T001" else "COMMENTARY")
    return sorted(categories), signals


def _parse_dt(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _flow(prev: NormalizedTurn, curr: NormalizedTurn, prev_record: TurnRecord) -> FlowRecord:
    text = curr.content
    relation = "CONTINUATION"
    confidence = 0.55
    evidence: list[str] = []

    if _has(PIVOT_PATTERNS, text):
        relation, confidence = "PIVOT", 0.98
        evidence.append("explicit pivot language")
    elif _has(DEFER_PATTERNS, text) and _has(NEGATIVE_PATTERNS, text):
        relation, confidence = "DEFERRED_ERROR", 0.95
        evidence.append("objection explicitly deferred to preserve flow")
    elif _has(NEGATIVE_PATTERNS, text) or _has(CATEGORY_PATTERNS["CORRECTION"], text):
        relation, confidence = "CORRECTION", 0.90
        evidence.append("explicit correction/negative signal")
    elif curr.speaker == "USER" and _has(EXPLICIT_ACCEPT_PATTERNS, text):
        relation, confidence = "CONTINUATION", 0.95
        evidence.append("explicit acceptance")
    elif curr.speaker == "USER" and prev.speaker == "ASSISTANT" and _has(BUILD_PATTERNS, text) and not _has(NEGATIVE_PATTERNS, text):
        if "SUGGESTION" in prev_record.categories or "IDEA" in prev_record.categories:
            relation, confidence = "ACCEPT_BY_CONTINUATION", 0.84
            evidence.append("user builds on prior assistant proposal without objection")
        else:
            relation, confidence = "BUILD_ON", 0.82
            evidence.append("user extends prior result")
    elif curr.speaker == "USER" and prev.speaker == "ASSISTANT" and not _has(NEGATIVE_PATTERNS, text):
        relation, confidence = "CONTINUATION", 0.62
        evidence.append("same conversational flow; no acceptance inferred")

    pdt, cdt = _parse_dt(prev.timestamp), _parse_dt(curr.timestamp)
    elapsed: float | None = None
    temporal_signal: str | None = None
    if pdt and cdt:
        elapsed = max(0.0, (cdt - pdt).total_seconds())
        if elapsed <= 300:
            temporal_signal = "rapid"
        elif elapsed >= 86400:
            temporal_signal = "multi_day_gap"
        elif elapsed >= 8 * 3600:
            temporal_signal = "session_break"
        else:
            temporal_signal = "same_session_likely"
        if temporal_signal in {"session_break", "multi_day_gap"} and relation == "CONTINUATION":
            relation = "RETURN"
            confidence = max(confidence, 0.66)
            evidence.append("long temporal gap supports return/resumption")

    return FlowRecord(
        from_turn=prev.turn_id,
        to_turn=curr.turn_id,
        relation=relation,
        confidence=confidence,
        elapsed_seconds=elapsed,
        temporal_signal=temporal_signal,
        evidence=evidence,
    )


def _foundation(turns: list[NormalizedTurn]) -> ThreadFoundation:
    # Freeze foundation from the opening exchange. Later turns cannot rewrite where the thread started.
    opening_user_turns: list[NormalizedTurn] = []
    started = False
    for t in turns:
        if t.speaker == "USER":
            if not started or opening_user_turns:
                opening_user_turns.append(t)
                started = True
                continue
        if started:
            break
    if not opening_user_turns:
        opening_user_turns = [turns[0]]
    sources = [t.turn_id for t in opening_user_turns]
    first = opening_user_turns[0].content
    initial_requests = [_summary(t.content, 180) for t in opening_user_turns if "?" in t.content or _has(CATEGORY_PATTERNS["ACTION"], t.content)]
    entities: list[str] = []
    for t in turns[: min(6, len(turns))]:
        for m in ENTITY_RE.findall(t.content):
            canonical = "KA§§A" if m.lower() == "kassa" else m
            if canonical not in entities:
                entities.append(canonical)
    starting = [_summary(t.content, 160) for t in opening_user_turns[1:]]
    return ThreadFoundation(
        purpose=_summary(first, 260),
        initial_goal=_summary(first, 180),
        starting_state=starting,
        initial_requests=initial_requests[:5],
        initial_scope={"in_scope": entities[:8], "out_of_scope": []},
        key_entities=entities[:12],
        source_turns=sources,
    )


def _document_candidates(turn: NormalizedTurn) -> list[tuple[str, str | None, str | None, dict]]:
    found: list[tuple[str, str | None, str | None, dict]] = [(a.name, a.uri, a.content, a.metadata) for a in turn.attachments]
    for name in DOC_RE.findall(turn.content):
        if not any(existing[0] == name for existing in found):
            found.append((name.strip(), None, None, {}))
    return found


STOPWORDS = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "that", "this", "it", "i", "we", "you", "is", "are", "be", "then", "add", "build", "implemented", "verified", "please"}


def _keywords(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9§]+", text.lower()) if len(w) > 2 and w not in STOPWORDS}


def _overlap(a: str, b: str) -> float:
    ka, kb = _keywords(a), _keywords(b)
    if not ka or not kb:
        return 0.0
    return len(ka & kb) / max(1, min(len(ka), len(kb)))


def _resolve_recent_actions(items: list[ExtractedItem], turn_records: list[TurnRecord], turn: NormalizedTurn, cats: list[str]) -> None:
    if turn.speaker != "ASSISTANT" or not ({"IMPLEMENTED", "VERIFICATION"} & set(cats)):
        return
    current_num = int(turn.turn_id[1:])
    candidates = [
        i for i in items
        if i.category == "ACTION" and i.status == "OPEN" and 0 < current_num - int(i.introduced_at[1:]) <= 4
    ]
    if not candidates:
        return
    ranked = sorted(((_overlap(i.statement, turn.content), i) for i in candidates), key=lambda x: x[0], reverse=True)
    score, best = ranked[0]
    if score >= 0.18 or len(candidates) == 1:
        best.status = "VERIFIED" if "VERIFICATION" in cats else "IMPLEMENTED_REPORTED"
        best.related_turns.append(turn.turn_id)
        best.notes.append(f"Lifecycle advanced by implementation/verification evidence at {turn.turn_id}; lexical overlap={score:.2f}.")


def analyze_thread(title: str, turns: list[NormalizedTurn], thread_id: str | None = None) -> ThreadLedger:
    if not turns:
        raise ValueError("Thread has no turns")
    if thread_id is None:
        digest = hashlib.sha256((title + turns[0].content).encode()).hexdigest()[:10]
        thread_id = f"THREAD-{digest}"

    turn_records: list[TurnRecord] = []
    items: list[ExtractedItem] = []
    documents: list[DocumentRecord] = []
    doc_by_name: dict[str, str] = {}
    item_counter = 0
    doc_counter = 0

    for turn in turns:
        cats, signals = _categories(turn)
        authority, weight = _authority(turn.speaker, cats)
        _resolve_recent_actions(items, turn_records, turn, cats)
        turn_item_ids: list[str] = []
        for cat in cats:
            if cat in {"COMMENTARY", "FOUNDATION", "ARTIFACT", "CODE", "OPEN_QUESTION"}:
                continue
            item_counter += 1
            status = "PROPOSED"
            if cat in {"DECISION", "CANON_UPDATE", "CORRECTION"} and turn.speaker == "USER":
                status = "ACCEPTED"
            elif cat in {"IMPLEMENTED", "VERIFICATION"}:
                status = "VERIFIED" if cat == "VERIFICATION" else "IMPLEMENTED_REPORTED"
            elif cat in {"ERROR", "MISDIRECTION", "DEFERRED_ERROR"}:
                status = "OPEN" if cat == "DEFERRED_ERROR" else "IDENTIFIED"
            elif cat == "ACTION":
                status = "OPEN"
            item_id = f"I-{item_counter:04d}"
            items.append(ExtractedItem(
                item_id=item_id,
                category=cat,
                statement=_summary(turn.content, 300),
                introduced_at=turn.turn_id,
                authority=authority,
                authority_weight=weight,
                status=status,
                confidence=0.88 if turn.speaker == "USER" else 0.70,
                source_turns=[turn.turn_id],
            ))
            turn_item_ids.append(item_id)

        turn_doc_ids: list[str] = []
        for name, uri, doc_content, doc_meta in _document_candidates(turn):
            key = name.lower()
            if key not in doc_by_name:
                doc_counter += 1
                doc_id = f"DOC-{doc_counter:03d}"
                doc_by_name[key] = doc_id
                documents.append(DocumentRecord(
                    document_id=doc_id,
                    name=name,
                    introduced_at=turn.turn_id,
                    introduced_by=turn.speaker,
                    kind=Path(name).suffix.lower().lstrip(".") or "document",
                    roles=["evidence" if turn.speaker == "USER" else "reference"],
                    references=[turn.turn_id],
                    uri=uri,
                    content_hash=hashlib.sha256(doc_content.encode()).hexdigest() if doc_content else None,
                    content_excerpt=_summary(doc_content, 500) if doc_content else None,
                    metadata=doc_meta,
                ))
            else:
                doc_id = doc_by_name[key]
                doc = next(d for d in documents if d.document_id == doc_id)
                if turn.turn_id not in doc.references:
                    doc.references.append(turn.turn_id)
            turn_doc_ids.append(doc_id)

        turn_records.append(TurnRecord(
            turn_id=turn.turn_id,
            speaker=turn.speaker,
            timestamp=turn.timestamp,
            summary=_summary(turn.content),
            categories=cats,
            authority=authority,
            authority_weight=weight,
            items=turn_item_ids,
            documents=turn_doc_ids,
            signals=signals,
            raw_text=turn.content,
        ))

    flows: list[FlowRecord] = []
    for idx in range(1, len(turns)):
        f = _flow(turns[idx - 1], turns[idx], turn_records[idx - 1])
        flows.append(f)
        if f.relation in {"ACCEPT_BY_CONTINUATION", "BUILD_ON"} and turns[idx].speaker == "USER":
            prior_ids = turn_records[idx - 1].items
            for item in items:
                if item.item_id in prior_ids and item.authority.startswith("ASSISTANT") and item.status == "PROPOSED":
                    item.status = "IMPLICITLY_ACCEPTED"
                    item.authority = "USER_BUILDS_ON_ASSISTANT_PROPOSAL"
                    item.authority_weight = 0.85 if f.relation == "ACCEPT_BY_CONTINUATION" else 0.75
                    item.related_turns.append(turns[idx].turn_id)
                    item.notes.append(f"Implicit acceptance inferred from {f.relation} at {turns[idx].turn_id}; scoped to this item, not whole prior turn.")
        elif f.relation == "CORRECTION" and turns[idx].speaker == "USER":
            for item in items:
                if item.item_id in turn_records[idx - 1].items and item.authority.startswith("ASSISTANT") and item.status in {"PROPOSED", "IMPLICITLY_ACCEPTED"}:
                    item.status = "CHALLENGED"
                    item.related_turns.append(turns[idx].turn_id)
        elif f.relation == "DEFERRED_ERROR":
            for item in items:
                if item.introduced_at == turns[idx].turn_id and item.category == "DEFERRED_ERROR":
                    item.notes.append("User preserved flow while leaving this issue unresolved.")

    for idx in range(1, len(flows)):
        previous = flows[idx - 1]
        current = flows[idx]
        target_record = turn_records[idx + 1]
        if previous.relation == "CORRECTION" and current.relation == "CONTINUATION" and target_record.speaker == "ASSISTANT":
            if {"VERIFICATION", "IMPLEMENTED", "CORRECTION"} & set(target_record.categories):
                current.relation = "RECOVERY"
                current.confidence = max(current.confidence, 0.82)
                current.evidence.append("assistant response after correction reports repair/verification")

    return ThreadLedger(
        schema_version="0.1.0",
        thread_id=thread_id,
        title=title,
        foundation=_foundation(turns),
        turns=turn_records,
        flows=flows,
        items=items,
        documents=documents,
        metadata={"turn_count": len(turns), "parser": "thread-journey-parser-v1"},
    )
